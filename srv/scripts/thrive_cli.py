#!/usr/bin/env python3
"""Command-line client and admin helper for Thrive Messenger.

This CLI is intentionally boring: JSON-over-TCP for normal bot/client work and
local SQLite access only for server-side admin maintenance.
"""

import argparse
import base64
import configparser
import getpass
import json
import mimetypes
import os
import secrets
import socket
import re
import uuid
import sqlite3
import ssl
import subprocess
import sys
import time
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional

try:
    from argon2 import PasswordHasher
except Exception:  # pragma: no cover - optional server dependency
    PasswordHasher = None  # type: ignore


# Bump this whenever a meaningful CLI feature/fix lands, so `thrive-cli version`
# and `thrive-cli self-update` have something real to compare against.
CLI_VERSION = "2026.10.02-contact-admin-cmds"
REPO_ROOT = Path(__file__).resolve().parents[2]  # .../apps/ThriveMessenger


DEFAULT_CONFIG_PATH = Path(__file__).resolve().parents[1] / "srv.conf"
DEFAULT_DB_PATH = Path(__file__).resolve().parents[1] / "thrive.db"
DEFAULT_AGENT_ENV = Path.home() / ".config" / "thrive-messenger" / "agent-bots.env"


def emit(payload: Dict[str, Any], json_mode: bool) -> None:
    if json_mode:
        print(json.dumps(payload, indent=2, sort_keys=True))
        return
    status = payload.get("status", "ok")
    message = payload.get("message") or payload.get("reason") or status
    print(message)


def fail(message: str, json_mode: bool, code: int = 1, **extra: Any) -> None:
    payload = {"status": "error", "reason": message}
    payload.update(extra)
    emit(payload, json_mode)
    raise SystemExit(code)


def load_config(path: Path) -> configparser.ConfigParser:
    cfg = configparser.ConfigParser()
    cfg.read(path)
    return cfg


def config_bot_names(cfg: configparser.ConfigParser) -> List[str]:
    raw = cfg.get("bots", "names", fallback="Clawdia,Sapphire,Sophia")
    seen = set()
    out = []
    for item in raw.split(","):
        name = item.strip()
        if not name or name.lower() in seen:
            continue
        seen.add(name.lower())
        out.append(name)
    return out


def env_key_for_bot(bot_name: str) -> str:
    safe = "".join(ch if ch.isalnum() else "_" for ch in bot_name.upper()).strip("_")
    return f"THRIVE_BOT_{safe}_PASSWORD"


def quote_env(value: str) -> str:
    return "'" + value.replace("'", "'\"'\"'") + "'"


def read_agent_env(path: Path) -> Dict[str, str]:
    data: Dict[str, str] = {}
    if not path.exists():
        return data
    for line in path.read_text(encoding="utf-8").splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("#") or "=" not in stripped:
            continue
        key, val = stripped.split("=", 1)
        val = val.strip()
        if (val.startswith("'") and val.endswith("'")) or (val.startswith('"') and val.endswith('"')):
            val = val[1:-1]
        data[key.strip()] = val
    return data


def write_agent_env(path: Path, values: Dict[str, str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    existing = read_agent_env(path)
    existing.update(values)
    lines = [
        "# Thrive Messenger service-owned bot credentials.",
        "# Keep this file private. Do not paste these values into chat or tickets.",
    ]
    for key in sorted(existing):
        lines.append(f"{key}={quote_env(existing[key])}")
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    try:
        os.chmod(path, 0o600)
    except Exception:
        pass


def hash_password(password: str) -> str:
    """Hash for storage. Uses the server's own hasher so formats always match; never stores plain text."""
    srv_dir = str(Path(__file__).resolve().parent.parent)
    if srv_dir not in sys.path:
        sys.path.insert(0, srv_dir)
    import server as thrive_server  # noqa: WPS433 (local import keeps CLI start-up light)
    return thrive_server._hash_password(password)


def connect(host: str, port: int, use_ssl: bool, cafile: str = "", timeout: float = 12.0, insecure: bool = False) -> socket.socket:
    raw = socket.create_connection((host, port), timeout=timeout)
    if not use_ssl:
        return raw
    if insecure:
        context = ssl._create_unverified_context()
    else:
        context = ssl.create_default_context(cafile=cafile or None)
    return context.wrap_socket(raw, server_hostname=host)


def send_json(sock: socket.socket, payload: Dict[str, Any]) -> None:
    sock.sendall((json.dumps(payload) + "\n").encode("utf-8"))


def recv_json_line(sock: socket.socket) -> Dict[str, Any]:
    buf = bytearray()
    while True:
        chunk = sock.recv(1)
        if not chunk:
            if not buf:
                raise ConnectionError("connection closed")
            break
        if chunk == b"\n":
            break
        buf.extend(chunk)
    if not buf:
        return {}
    return json.loads(buf.decode("utf-8", errors="replace"))


def recv_until_action(sock: socket.socket, wanted_actions: Iterable[str], timeout: float = 5.0) -> Dict[str, Any]:
    wanted = {str(v) for v in wanted_actions}
    prior_timeout = sock.gettimeout()
    sock.settimeout(timeout)
    startup_events = []
    try:
        while True:
            event = recv_json_line(sock)
            if event.get("action") in wanted:
                if startup_events:
                    event["_startup_events"] = startup_events
                return event
            startup_events.append(event)
    finally:
        sock.settimeout(prior_timeout)


def safe_filename(name: str) -> str:
    cleaned = os.path.basename(str(name or "").strip())
    if not cleaned or cleaned in (".", ".."):
        cleaned = "attachment.bin"
    return cleaned


def unique_output_path(directory: Path, filename: str) -> Path:
    directory.mkdir(parents=True, exist_ok=True)
    base = safe_filename(filename)
    candidate = directory / base
    if not candidate.exists():
        return candidate
    stem = candidate.stem or "attachment"
    suffix = candidate.suffix
    for idx in range(1, 10000):
        alt = directory / f"{stem}-{idx}{suffix}"
        if not alt.exists():
            return alt
    raise FileExistsError(f"Could not choose unique output path for {base}")


def read_file_payload(path: Path) -> Dict[str, Any]:
    data = path.read_bytes()
    mime = mimetypes.guess_type(path.name)[0] or "application/octet-stream"
    return {
        "filename": path.name,
        "size": len(data),
        "mime": mime,
        "data": base64.b64encode(data).decode("ascii"),
    }


def save_file_payload(file_info: Dict[str, Any], output_dir: Path) -> Dict[str, Any]:
    filename = safe_filename(str(file_info.get("filename") or "attachment.bin"))
    raw = file_info.get("data") or ""
    if not isinstance(raw, str) or not raw:
        raise ValueError(f"Missing file data for {filename}")
    data = base64.b64decode(raw.encode("ascii"), validate=False)
    out = unique_output_path(output_dir, filename)
    out.write_bytes(data)
    return {
        "filename": filename,
        "path": str(out),
        "size": len(data),
        "mime": str(file_info.get("mime") or ""),
    }


def login(args: argparse.Namespace, password: Optional[str] = None) -> socket.socket:
    pwd = password or args.password or os.environ.get("THRIVE_PASSWORD")
    if not pwd and getattr(args, "username", ""):
        env_values = read_agent_env(args.agent_env)
        pwd = env_values.get(env_key_for_bot(args.username))
    if not pwd and not args.no_prompt:
        pwd = getpass.getpass(f"Password for {args.username}: ")
    if not pwd:
        fail("Missing password. Use --password, THRIVE_PASSWORD, or an interactive prompt.", args.json)
    sock = connect(args.host, args.port, args.ssl, args.cafile, args.timeout, args.insecure)
    send_json(sock, {"action": "login", "user": args.username, "pass": pwd})
    response = recv_json_line(sock)
    if response.get("status") != "ok":
        sock.close()
        fail("Login failed.", args.json, response=response)
    return sock


def cmd_doctor(args: argparse.Namespace) -> None:
    cfg = load_config(args.config)
    payload = {
        "status": "ok",
        "config": str(args.config),
        "config_exists": args.config.exists(),
        "host": args.host,
        "port": args.port,
        "ssl": args.ssl,
        "db": str(args.db),
        "db_exists": args.db.exists(),
        "bots_configured": config_bot_names(cfg),
        "agent_env": str(args.agent_env),
        "agent_env_exists": args.agent_env.exists(),
        "argon2_available": PasswordHasher is not None,
    }
    try:
        sock = connect(args.host, args.port, args.ssl, args.cafile, timeout=min(args.timeout, 5), insecure=args.insecure)
        sock.close()
        payload["server_reachable"] = True
    except Exception as exc:
        payload["server_reachable"] = False
        payload["server_error"] = str(exc)
    emit(payload, args.json)


def sqlite_conn(path: Path, *, write: bool = False) -> sqlite3.Connection:
    if not path.exists():
        raise FileNotFoundError(f"Database not found: {path}")
    mode = "rwc" if write else "ro"
    con = sqlite3.connect(f"file:{path.as_posix()}?mode={mode}", uri=True)
    con.row_factory = sqlite3.Row
    return con


def cmd_users_list(args: argparse.Namespace) -> None:
    con = sqlite_conn(args.db)
    try:
        rows = con.execute(
            "SELECT username, email, is_verified, banned_until FROM users ORDER BY lower(username)"
        ).fetchall()
    finally:
        con.close()
    users = [
        {
            "username": row["username"],
            "email_set": bool(row["email"]),
            "is_verified": bool(row["is_verified"]),
            "banned_until": row["banned_until"] or "",
        }
        for row in rows
    ]
    emit({"status": "ok", "users": users, "count": len(users)}, args.json)


def ensure_bot_user(con: sqlite3.Connection, bot_name: str, env_values: Dict[str, str]) -> Dict[str, Any]:
    row = con.execute("SELECT username FROM users WHERE username=? COLLATE NOCASE LIMIT 1", (bot_name,)).fetchone()
    key = env_key_for_bot(bot_name)
    created = False
    password_created = False
    canonical = row["username"] if row else bot_name
    if not row:
        password = env_values.get(key) or secrets.token_urlsafe(36)
        env_values[key] = password
        con.execute(
            "INSERT INTO users(username, password, email, is_verified) VALUES(?,?,?,1)",
            (bot_name, hash_password(password), f"{bot_name.lower()}@tappedin.fm"),
        )
        created = True
        password_created = True
        canonical = bot_name
    elif key not in env_values:
        password = secrets.token_urlsafe(36)
        env_values[key] = password
        con.execute("UPDATE users SET password=?, is_verified=1 WHERE username=?", (hash_password(password), canonical))
        password_created = True
    else:
        con.execute("UPDATE users SET is_verified=1 WHERE username=?", (canonical,))
    return {"bot": canonical, "created": created, "password_stored": password_created}


def configured_human_users(con: sqlite3.Connection, bots: Iterable[str]) -> List[str]:
    bot_lowers = {b.lower() for b in bots}
    return [
        row["username"]
        for row in con.execute("SELECT username FROM users ORDER BY lower(username)").fetchall()
        if row["username"].lower() not in bot_lowers
    ]


def add_contact(con: sqlite3.Connection, owner: str, contact: str) -> bool:
    cur = con.execute("INSERT OR IGNORE INTO contacts(owner, contact) VALUES(?,?)", (owner, contact))
    return cur.rowcount > 0


def cmd_admin_ensure_bots(args: argparse.Namespace) -> None:
    cfg = load_config(args.config)
    bots = args.bots or config_bot_names(cfg)
    if not bots:
        fail("No bot names supplied or configured.", args.json)
    env_values = read_agent_env(args.agent_env)
    con = sqlite_conn(args.db, write=True)
    results = []
    try:
        for bot in bots:
            results.append(ensure_bot_user(con, bot, env_values))
        con.commit()
    finally:
        con.close()
    write_agent_env(args.agent_env, env_values)
    emit(
        {
            "status": "ok",
            "message": f"Ensured {len(results)} bot account(s). Credentials were written only to the private env file.",
            "bots": results,
            "agent_env": str(args.agent_env),
        },
        args.json,
    )


def cmd_admin_link_bot_contacts(args: argparse.Namespace) -> None:
    cfg = load_config(args.config)
    bots = args.bots or config_bot_names(cfg)
    hidden = {name.lower() for name in args.hidden_bots}
    visible_bots = [bot for bot in bots if bot.lower() not in hidden]
    if not bots:
        fail("No bot names supplied or configured.", args.json)
    con = sqlite_conn(args.db, write=True)
    added = 0
    removed_hidden = 0
    try:
        if args.users == ["all"]:
            users = configured_human_users(con, bots)
        else:
            users = args.users
        for user in users:
            for hidden_bot in bots:
                if hidden_bot.lower() in hidden:
                    cur = con.execute("DELETE FROM contacts WHERE owner=? AND contact=?", (user, hidden_bot))
                    removed_hidden += cur.rowcount
            for bot in visible_bots:
                if user.lower() == bot.lower():
                    continue
                added += 1 if add_contact(con, user, bot) else 0
                if args.mutual:
                    added += 1 if add_contact(con, bot, user) else 0
        if args.bot_mesh_contacts:
            for bot in bots:
                for other in bots:
                    if bot.lower() != other.lower():
                        added += 1 if add_contact(con, bot, other) else 0
        con.commit()
    finally:
        con.close()
    emit(
        {
            "status": "ok",
            "message": f"Linked bot contacts. Added {added} contact row(s).",
            "bots": bots,
            "visible_bots": visible_bots,
            "hidden_bots": sorted(hidden),
            "users": users,
            "mutual": args.mutual,
            "bot_mesh_contacts": args.bot_mesh_contacts,
            "added": added,
            "removed_hidden_user_contacts": removed_hidden,
        },
        args.json,
    )


def split_message(text: str, max_chars: int) -> List[str]:
    """Split long text on paragraph/sentence/word boundaries, labelled for screen readers."""
    if max_chars <= 0 or len(text) <= max_chars:
        return [text]
    chunks: List[str] = []
    remaining = text
    while len(remaining) > max_chars:
        window = remaining[:max_chars]
        cut = max(window.rfind(sep) for sep in ("\n\n", "\n", ". ", "! ", "? ", "; ", ", ", " "))
        cut = max_chars if cut < max_chars // 2 else cut + 1
        chunk = remaining[:cut].strip()
        if chunk:
            chunks.append(chunk)
        remaining = remaining[cut:].lstrip()
    if remaining.strip():
        chunks.append(remaining.strip())
    total = len(chunks)
    return [f"Part {idx} of {total}: {chunk}" for idx, chunk in enumerate(chunks, start=1)]


def cmd_read_status(args: argparse.Namespace) -> None:
    """Delivered/read status of messages one user sent another (read from the local server database).
    Agents use this before re-sending a reminder: if it's read, don't send it again."""
    srv_dir = str(Path(__file__).resolve().parent.parent)
    if srv_dir not in sys.path:
        sys.path.insert(0, srv_dir)
    import server as thrive_server
    thrive_server.DB = str(args.db)
    since = args.since
    if args.minutes:
        from datetime import timedelta
        since = (datetime.now(timezone.utc).replace(tzinfo=None) - timedelta(minutes=args.minutes)).isoformat()
    rows = thrive_server._read_status(args.sender, args.to, since=since, limit=args.limit if not args.ids else 500)
    if args.ids:
        wanted = set(args.ids)
        rows = [r for r in rows if r["id"] in wanted]
    # Reactions on these messages (a thumbs up from the recipient is an acknowledgement; see REACTION_MEANINGS).
    found = thrive_server._reactions_for("dm", [r["id"] for r in rows])
    for r in rows:
        r["reactions"] = found.get(r["id"], [])
    emit({"status": "ok", "from": args.sender, "to": args.to, "messages": rows,
          "unread": sum(1 for r in rows if not r["read"])}, args.json)


REACTION_NAMES = {"\U0001F44D": "thumbs up", "\U0001F44E": "thumbs down", "\u2764\ufe0f": "heart", "\U0001F602": "laugh",
                  "\U0001F62E": "wow", "\U0001F622": "sad", "\U0001F389": "celebrate", "\u2705": "check mark", "\U0001F440": "seen"}
REACTION_ALIASES = {v.replace(" ", ""): k for k, v in REACTION_NAMES.items()}
REACTION_ALIASES.update({"like": "\U0001F44D", "+1": "\U0001F44D", "-1": "\U0001F44E", "eyes": "\U0001F440", "check": "\u2705", "love": "\u2764\ufe0f"})


def cmd_react(args: argparse.Namespace) -> None:
    """React to a message (DM with --to, or in a room with --room). Emoji or a name: thumbsup, heart, seen, check..."""
    emoji = REACTION_ALIASES.get(args.emoji.lower().replace(" ", "").replace("_", ""), args.emoji)
    sock = login(args)
    try:
        payload = {"action": "react", "message_id": args.message_id, "emoji": emoji, "on": not args.off, "scope": "dm"}
        if args.room:
            payload.update(scope="room", room_id=_resolve_room(sock, args.room)["room_id"])
        send_json(sock, payload)
        ev = recv_until_action(sock, ["reaction_update", "reaction_failed"], timeout=8.0)
        if ev.get("action") == "reaction_failed":
            fail(ev.get("reason") or "Reaction refused.", args.json)
        emit({"status": "ok", "message_id": args.message_id, "emoji": emoji, "on": not args.off, "reactions": ev.get("reactions")}, args.json)
    finally:
        sock.close()


def cmd_contact(args: argparse.Namespace) -> None:
    """Manage your own contact list like the GUI does: add, remove, block, unblock."""
    sock = login(args)
    try:
        act = args.contact_action
        if act == "add":
            send_json(sock, {"action": "add_contact", "to": args.username_target})
            ev = recv_until_action(sock, ["add_contact_success", "add_contact_failed"], timeout=8.0)
            if ev.get("action") == "add_contact_failed":
                fail(ev.get("reason") or "Could not add contact.", args.json,
                     suggest_invite=ev.get("suggest_invite"), invite_methods=ev.get("invite_methods"))
            emit({"status": "ok", "added": args.username_target, "contact": ev.get("contact")}, args.json)
        elif act in ("remove", "delete"):
            send_json(sock, {"action": "delete_contact", "to": args.username_target})
            time.sleep(0.3)
            emit({"status": "ok", "removed": args.username_target}, args.json)
        elif act in ("block", "unblock"):
            send_json(sock, {"action": f"{act}_contact", "to": args.username_target})
            time.sleep(0.3)
            emit({"status": "ok", act + "ed": args.username_target}, args.json)
    finally:
        sock.close()


def cmd_version(args: argparse.Namespace) -> None:
    """Show the running CLI version and, if this is a git checkout, the current commit."""
    info: Dict[str, Any] = {"status": "ok", "version": CLI_VERSION, "path": str(Path(__file__).resolve())}
    if (REPO_ROOT / ".git").exists():
        try:
            commit = subprocess.run(["git", "-C", str(REPO_ROOT), "rev-parse", "--short", "HEAD"],
                                     capture_output=True, text=True, timeout=10, check=True).stdout.strip()
            branch = subprocess.run(["git", "-C", str(REPO_ROOT), "rev-parse", "--abbrev-ref", "HEAD"],
                                     capture_output=True, text=True, timeout=10, check=True).stdout.strip()
            info.update(commit=commit, branch=branch, repo=str(REPO_ROOT))
        except Exception as exc:
            info["git_error"] = str(exc)
    emit(info, args.json)


def cmd_self_update(args: argparse.Namespace) -> None:
    """Pull the latest thrive_cli.py (and the rest of the repo) from git, so every user/agent stays on the
    same version as the live server. Safe no-op if already up to date; refuses on a dirty tree unless --force."""
    if not (REPO_ROOT / ".git").exists():
        fail(f"{REPO_ROOT} is not a git checkout; can't self-update. Pull manually or reinstall from the repo.", args.json)

    def run(cmd: List[str]) -> subprocess.CompletedProcess:
        return subprocess.run(cmd, cwd=str(REPO_ROOT), capture_output=True, text=True, timeout=60)

    before = run(["git", "rev-parse", "HEAD"]).stdout.strip()
    status = run(["git", "status", "--porcelain"]).stdout
    dirty = [ln for ln in status.splitlines() if not re.match(r"^\?\? .*\.bak", ln)]
    if dirty and not args.force:
        fail("Local changes present in the repo; refusing to update. Re-run with --force to stash and update anyway, "
             "or commit/discard your changes first.", args.json, dirty_files=[ln.strip() for ln in dirty])
    stashed = False
    if dirty and args.force:
        run(["git", "stash", "push", "-u", "-m", "thrive-cli self-update auto-stash"])
        stashed = True
    branch = run(["git", "rev-parse", "--abbrev-ref", "HEAD"]).stdout.strip()
    fetch = run(["git", "fetch", "--all", "--prune"])
    if fetch.returncode != 0:
        fail(f"git fetch failed: {fetch.stderr.strip()}", args.json)
    pull = run(["git", "pull", "--ff-only"])
    after = run(["git", "rev-parse", "HEAD"]).stdout.strip()
    if pull.returncode != 0:
        fail(f"git pull --ff-only failed (branch may have diverged): {pull.stderr.strip()}", args.json,
             before=before, branch=branch)
    emit({"status": "ok", "branch": branch, "before": before, "after": after,
          "updated": before != after, "stashed_local_changes": stashed,
          "note": "Restart any running thrive_cli listeners/bots so they load the new code."}, args.json)


def cmd_admin_cmd(args: argparse.Namespace) -> None:
    """Run any server admin console slash-command (same ones the GUI's admin console has): help, alert, create,
    invite, accountlimit, ban, unban, del, admin, unadmin, banfile, unbanfile, gpolicy, restart, exit."""
    sock = login(args)
    try:
        send_json(sock, {"action": "admin_cmd", "cmd": args.cmdline})
        ev = recv_until_action(sock, ["admin_response"], timeout=10.0)
        emit({"status": "ok", "response": ev.get("response")}, args.json)
    finally:
        sock.close()


def cmd_send(args: argparse.Namespace) -> None:
    message = args.message
    if message == "-":
        message = sys.stdin.read()
    sock = login(args)
    try:
        for part in split_message(message, args.split_at):
            send_json(sock, {"action": "msg", "from": args.username, "to": args.to, "msg": part, "time": datetime.now().isoformat()})
            time.sleep(0.15)
        sock.settimeout(args.wait)
        responses = []
        try:
            while True:
                responses.append(recv_json_line(sock))
        except socket.timeout:
            pass
        emit({"status": "ok", "sent": True, "to": args.to, "responses": responses}, args.json)
    finally:
        sock.close()


def cmd_set_status(args: argparse.Namespace) -> None:
    """Set an agent/user presence without sending a chat message."""
    sock = login(args)
    try:
        expires_at = ""
        if args.clear_after:
            expires_at = (datetime.now(timezone.utc) + timedelta(minutes=args.clear_after)).isoformat().replace("+00:00", "Z")
        send_json(sock, {"action": "set_status", "presence": args.presence, "custom_status": args.text or "", "expires_at": expires_at})
        event = recv_until_action(sock, ["set_status_result"], timeout=8.0)
        if not event.get("ok", False):
            fail(event.get("reason") or "Status was refused.", args.json)
        emit({"status": "ok", "presence": event.get("kind", args.presence), "text": event.get("custom_text", args.text or ""),
              "expires_at": event.get("expires_at", expires_at)}, args.json)
    finally:
        sock.close()


def cmd_send_file(args: argparse.Namespace) -> None:
    files = []
    payload_files = []
    for raw in args.files:
        path = Path(raw).expanduser().resolve()
        if not path.is_file():
            fail(f"File not found: {path}", args.json)
        payload = read_file_payload(path)
        files.append({k: payload[k] for k in ("filename", "size", "mime")})
        payload_files.append(payload)
    sock = login(args)
    try:
        transfer_id = secrets.token_hex(12)
        send_json(sock, {"action": "file_offer", "to": args.to, "files": files, "transfer_id": transfer_id})
        response = recv_until_action(sock, ["file_accepted", "file_offer_failed", "file_declined"], timeout=args.wait)
        if response.get("action") != "file_accepted":
            emit({"status": "error", "sent": False, "to": args.to, "response": response}, args.json)
            return
        server_transfer_id = response.get("transfer_id")
        send_json(sock, {"action": "file_data", "transfer_id": server_transfer_id, "files": payload_files})
        emit({"status": "ok", "sent": True, "to": args.to, "files": files, "transfer_id": server_transfer_id, "response": response}, args.json)
    finally:
        sock.close()


def cmd_bot_store_file(args: argparse.Namespace) -> None:
    path = Path(args.file).expanduser().resolve()
    if not path.is_file():
        fail(f"File not found: {path}", args.json)
    payload = read_file_payload(path)
    if args.mime:
        payload["mime"] = args.mime
    sock = login(args)
    try:
        request_id = args.request_id or secrets.token_hex(12)
        send_json(sock, {
            "action": "bot_mesh_store_file",
            "to": args.to,
            "filename": payload["filename"],
            "mime": payload["mime"],
            "data": payload["data"],
            "request_id": request_id,
        })
        response = recv_until_action(sock, ["bot_mesh_file_stored"], timeout=args.wait)
        emit({"status": "ok" if response.get("ok") else "error", "response": response}, args.json)
    finally:
        sock.close()


def cmd_bot_fetch_file(args: argparse.Namespace) -> None:
    sock = login(args)
    try:
        send_json(sock, {"action": "bot_mesh_fetch_file", "file_id": args.file_id, "consume": args.consume})
        response = recv_until_action(sock, ["bot_mesh_file_data"], timeout=args.wait)
        saved = None
        if response.get("ok"):
            saved = save_file_payload(response, args.output_dir)
            if not args.include_data:
                response = dict(response)
                response.pop("data", None)
        emit({"status": "ok" if response.get("ok") else "error", "saved": saved, "response": response}, args.json)
    finally:
        sock.close()


def _maybe_handle_voice_call_event(sock: socket.socket, event: Dict[str, Any], args: argparse.Namespace) -> bool:
    action = event.get("action")
    if action != "voice_call_request" or not getattr(args, "auto_decline_calls", False):
        return False
    call_id = str(event.get("call_id", "") or "").strip()
    caller = str(event.get("from", event.get("caller", "")) or "").strip()
    if call_id:
        send_json(sock, {"action": "voice_call_decline", "call_id": call_id})
    message = str(getattr(args, "call_decline_message", "") or "").strip()
    if message and caller:
        send_json(sock, {"action": "msg", "to": caller, "from": args.username, "msg": message, "time": datetime.now().isoformat()})
    return True


def cmd_listen(args: argparse.Namespace) -> None:
    sock = login(args)
    try:
        emit({"status": "ok", "message": f"Listening as {args.username}. Press Ctrl+C to stop."}, args.json)
        while True:
            event = recv_json_line(sock)
            saved_files = []
            action = event.get("action", "event")
            if _maybe_handle_voice_call_event(sock, event, args):
                event = dict(event)
                event["handled"] = "auto_declined"
            elif action == "msg" and getattr(args, "mark_read", False) and event.get("id") and not event.get("echo"):
                # Tell the sender their message was read, so Thrive shows it as read (like a person's client).
                send_json(sock, {"action": "msg_read", "ids": [event.get("id")]})
            elif action == "file_offer" and args.auto_accept_files:
                send_json(sock, {"action": "file_accept", "transfer_id": event.get("transfer_id")})
            elif action == "file_data" and args.save_dir:
                for file_info in event.get("files", []) if isinstance(event.get("files"), list) else []:
                    try:
                        saved_files.append(save_file_payload(file_info, args.save_dir))
                    except Exception as exc:
                        saved_files.append({"error": str(exc), "filename": file_info.get("filename", "") if isinstance(file_info, dict) else ""})
                event = dict(event)
                event["saved_files"] = saved_files
                if not args.include_data:
                    for file_info in event.get("files", []) if isinstance(event.get("files"), list) else []:
                        if isinstance(file_info, dict):
                            file_info.pop("data", None)
            elif action == "bot_mesh_file_available" and args.save_dir and args.auto_fetch_bot_files:
                send_json(sock, {"action": "bot_mesh_fetch_file", "file_id": event.get("file_id"), "consume": args.consume_bot_files})
            elif action == "bot_mesh_file_data" and args.save_dir and event.get("ok"):
                try:
                    saved_files.append(save_file_payload(event, args.save_dir))
                except Exception as exc:
                    saved_files.append({"error": str(exc), "filename": event.get("filename", "")})
                event = dict(event)
                event["saved_files"] = saved_files
                if not args.include_data:
                    event.pop("data", None)
            if args.json:
                print(json.dumps(event, sort_keys=True), flush=True)
            else:
                sender = event.get("from", "")
                body = event.get("msg", event.get("reason", ""))
                if action == "group_room_message":
                    item = event.get("message") or {}
                    sender = f"[room {item.get('room_id', '')}] {item.get('sender', '')}"
                    body = item.get("body", "")
                if saved_files:
                    body = f"saved {len(saved_files)} file(s): " + ", ".join(str(item.get("path", item.get("error", ""))) for item in saved_files)
                print(f"{datetime.now().isoformat()} {action} {sender}: {body}", flush=True)
    except KeyboardInterrupt:
        pass
    finally:
        sock.close()


ROOM_ACTIONS = ("list", "create", "join", "leave", "post", "history", "members", "invite", "topic", "read-status", "mark-read")


def _room_request(sock, payload, wanted, timeout=8.0):
    send_json(sock, payload)
    event = recv_until_action(sock, list(wanted) + ["group_room_result"], timeout=timeout)
    if event.get("action") == "group_room_result" and event.get("ok") is False:
        raise RuntimeError(event.get("reason") or "Room action failed.")
    return event


def _resolve_room(sock, ref):
    """A room by id or by name (ignoring case), among public rooms and rooms you're in."""
    rooms = _room_request(sock, {"action": "group_room_list"}, ["group_room_list_response"]).get("rooms") or []
    ref_l = str(ref or "").strip().lower()
    for room in rooms:
        if room.get("room_id") == ref or str(room.get("name", "")).lower() == ref_l:
            return room
    raise RuntimeError(f"No room called {ref!r} that you can see.")


def cmd_room(args: argparse.Namespace) -> None:
    """Chat rooms for agents: list/search, create, join, leave, post, read history, members, invite, topic, read status."""
    sock = login(args)
    try:
        act = args.room_action
        if act == "list":
            rooms = _room_request(sock, {"action": "group_room_list", "query": args.query or ""}, ["group_room_list_response"]).get("rooms") or []
            if args.json:
                emit({"status": "ok", "rooms": rooms}, True)
            else:
                for r in rooms:
                    print(f"{r['name']}  ({r.get('role_label') or 'not joined'}, {r.get('member_count', 0)} members, {r.get('unread', 0)} unread)"
                          f"  id {r['room_id']}" + (f"  topic: {r['topic']}" if r.get("topic") else ""))
            return
        if act == "create":
            ev = _room_request(sock, {"action": "group_room_create", "name": args.room, "topic": args.topic or "",
                                      "description": args.description or "", "visibility": "private" if args.private else "public"},
                               ["group_room_result"])
            emit({"status": "ok", "room": ev.get("room")}, args.json)
            return
        if act == "join":
            ev = _room_request(sock, {"action": "group_room_join", "name": args.room} if not re.match(r"^[0-9a-f-]{36}$", args.room)
                               else {"action": "group_room_join", "room_id": args.room}, ["group_room_result"])
            emit({"status": "ok", "room": ev.get("room")}, args.json)
            return
        room = _resolve_room(sock, args.room)
        rid = room["room_id"]
        if act == "leave":
            ev = _room_request(sock, {"action": "group_room_leave", "room_id": rid}, ["group_room_result"])
            emit({"status": "ok", "left": room["name"], "deleted": ev.get("deleted", False)}, args.json)
        elif act == "post":
            text = sys.stdin.read() if args.text == "-" else args.text
            client_id = uuid.uuid4().hex
            for part in split_message(text, args.split_at):
                send_json(sock, {"action": "group_room_message", "room_id": rid, "body": part, "client_id": client_id})
                ev = recv_until_action(sock, ["group_room_message", "group_room_result"], timeout=8.0)
                if ev.get("action") == "group_room_result" and ev.get("ok") is False:
                    raise RuntimeError(ev.get("reason"))
            emit({"status": "ok", "room": room["name"], "posted": True, "message_id": (ev.get("message") or {}).get("message_id")}, args.json)
        elif act == "history":
            ev = _room_request(sock, {"action": "group_room_history", "room_id": rid, "limit": args.limit}, ["group_room_history_response"])
            msgs = ev.get("messages") or []
            if args.json:
                emit({"status": "ok", "room": room["name"], "messages": msgs}, True)
            else:
                for m in msgs:
                    when = datetime.fromtimestamp(float(m.get("sent_at") or 0)).strftime("%Y-%m-%d %H:%M")
                    print(f"{when} {m.get('sender')}: {'(deleted)' if m.get('deleted') else m.get('body')}  [{m.get('message_id')}]")
        elif act == "members":
            ev = _room_request(sock, {"action": "group_room_open", "room_id": rid, "limit": 1}, ["group_room_open_response"])
            emit({"status": "ok", "room": room["name"], "members": ev.get("members")}, args.json)
        elif act == "invite":
            ev = _room_request(sock, {"action": "group_room_add_member", "room_id": rid, "username": args.text, "role": args.role},
                               ["group_room_result"])
            emit({"status": "ok", "room": room["name"], "invited": ev.get("username")}, args.json)
        elif act == "topic":
            send_json(sock, {"action": "group_room_topic", "room_id": rid, "topic": args.text or ""})
            ev = recv_until_action(sock, ["group_room_event", "group_room_result"], timeout=8.0)
            if ev.get("ok") is False:
                raise RuntimeError(ev.get("reason"))
            emit({"status": "ok", "room": room["name"], "topic": (ev.get("room") or {}).get("topic")}, args.json)
        elif act == "read-status":
            ev = _room_request(sock, {"action": "group_room_read_status", "room_id": rid, "message_id": args.text}, ["group_room_read_status"])
            emit({"status": "ok", "room": room["name"], "read_by": ev.get("read_by"), "total": ev.get("total"),
                  "summary": f"read by {len(ev.get('read_by') or [])} of {ev.get('total')}"}, args.json)
        elif act == "mark-read":
            send_json(sock, {"action": "group_room_read", "room_id": rid, "message_id": args.text})
            emit({"status": "ok", "room": room["name"], "marked_read": args.text}, args.json)
    except RuntimeError as exc:
        fail(str(exc), args.json)
    finally:
        sock.close()



def cmd_register_bot_session(args: argparse.Namespace) -> None:
    sock = login(args)
    session_id = f"{args.username}:{args.host_label}:{os.getpid()}:{secrets.token_hex(8)}"
    heartbeat_interval = max(10.0, min(60.0, float(args.wait or 5.0) * 3.0))
    payload = {
        "action": "register_bot_session",
        "session_id": session_id,
        "auth_type": args.auth_type,
        "runtime": args.runtime,
        "host_label": args.host_label,
        "platform": args.platform,
        "capabilities": args.capabilities,
        "transports": args.transports,
        "accepts_files": args.accepts_files,
        "supports_delegation": not args.no_delegation,
        "background": args.background,
        "moderation": {
            "enabled": args.moderation,
            "kinds": args.moderation_kinds,
            "auto_report": True,
            "notify_user": args.notify_user,
        },
    }
    try:
        send_json(sock, payload)
        response = recv_until_action(sock, ["bot_session_registered"], timeout=args.wait)
        emit({"status": "ok" if response.get("ok") else "error", "response": response}, args.json)
        if response.get("ok") and args.provider_health:
            send_json(sock, {"action": "get_agent_provider_health"})
            try:
                health = recv_until_action(sock, ["agent_provider_health"], timeout=args.wait)
                emit({"status": "ok" if health.get("ok") else "error", "response": health}, args.json)
            except Exception as exc:
                emit({"status": "warning", "message": "Provider health response was not received before timeout.", "reason": str(exc)}, args.json)
        if args.listen and response.get("ok"):
            sock.settimeout(heartbeat_interval)
            while True:
                try:
                    event = recv_json_line(sock)
                except socket.timeout:
                    send_json(sock, {
                        "action": "bot_session_heartbeat",
                        "session_id": session_id,
                        "host_label": args.host_label,
                    })
                    continue
                if event.get("action") == "bot_catchup_messages":
                    messages = event.get("messages") if isinstance(event.get("messages"), list) else []
                    actionable = sum(1 for item in messages if isinstance(item, dict) and item.get("actionable"))
                    summary = {
                        "action": "bot_catchup_summary",
                        "bot": event.get("bot", args.username),
                        "channel": event.get("channel", "thrive"),
                        "missed_count": len(messages),
                        "actionable_count": actionable,
                    }
                    if args.json:
                        print(json.dumps(summary, sort_keys=True), flush=True)
                    else:
                        print(json.dumps(summary, ensure_ascii=False), flush=True)
                    continue
                if event.get("action") == "bot_session_heartbeat":
                    continue
                if _maybe_handle_voice_call_event(sock, event, args):
                    event = dict(event)
                    event["handled"] = "auto_declined"
                if args.json:
                    print(json.dumps(event, sort_keys=True), flush=True)
                else:
                    print(json.dumps(event, ensure_ascii=False), flush=True)
    except KeyboardInterrupt:
        pass
    finally:
        sock.close()


# ---------------------------------------------------------------------------
# agent-inbox: reliable DM hand-off for external agents (e.g. Adam on Muse).
# Each incoming DM becomes a file in INBOX/new/. The agent handles it, then moves it to INBOX/done/
# (or runs `agent-inbox-ack`); only then is the read receipt sent, so "read" means the agent saw it.
# Replies go out through this same connection via INBOX/outbox/*.json, so a second login can't
# steal the session. Unread DMs are caught up from server history on every (re)connect, the
# connection is re-established forever with backoff, and a bot-session heartbeat keeps the
# agent's presence visible to the server (and to System Monitor's watcher).

class _LineReader:
    """Buffered JSON-lines reader: a timeout never loses a half-received line (important behind slow proxies)."""

    def __init__(self, sock: socket.socket) -> None:
        self.sock = sock
        self.buf = bytearray()

    def read(self, timeout: float) -> Dict[str, Any]:
        """Next event, or {} if nothing complete arrived within `timeout`. Raises ConnectionError on close."""
        deadline = time.time() + timeout
        while b"\n" not in self.buf:
            left = deadline - time.time()
            if left <= 0:
                return {}
            self.sock.settimeout(left)
            try:
                chunk = self.sock.recv(65536)
            except socket.timeout:
                return {}
            if not chunk:
                raise ConnectionError("connection closed")
            self.buf.extend(chunk)
        line, _, rest = bytes(self.buf).partition(b"\n")
        self.buf = bytearray(rest)
        if not line.strip():
            return {}
        return json.loads(line.decode("utf-8", errors="replace"))


def _inbox_dirs(root: Path) -> Dict[str, Path]:
    dirs = {name: root / name for name in ("new", "done", "outbox", "sent", "state")}
    for d in dirs.values():
        d.mkdir(parents=True, exist_ok=True)
    return dirs


def _inbox_msg_path(dirs: Dict[str, Path], msg_id: str, sub: str = "new") -> Path:
    return dirs[sub] / (safe_filename(str(msg_id)) + ".json")


def _inbox_write_atomic(path: Path, payload: Dict[str, Any]) -> None:
    tmp = path.with_name("." + path.name + ".tmp")
    tmp.write_text(json.dumps(payload, ensure_ascii=False, indent=1), encoding="utf-8")
    os.replace(tmp, path)


def _inbox_known(dirs: Dict[str, Path], msg_id: str) -> bool:
    return any(_inbox_msg_path(dirs, msg_id, sub).exists() for sub in ("new", "done"))


def _inbox_store(dirs: Dict[str, Path], item: Dict[str, Any], args: argparse.Namespace, source: str) -> bool:
    msg_id = str(item.get("id") or "")
    if not msg_id or _inbox_known(dirs, msg_id):
        return False
    voice = item.get("voice") if isinstance(item.get("voice"), dict) else None
    transcript = str(item.get("transcript") or "")
    record = {
        "id": msg_id,
        "from": item.get("from", ""),
        "to": item.get("to", args.username),
        # A voice message's transcript (once ready) replaces the placeholder text so it reads like any other DM.
        "msg": transcript or item.get("msg", ""),
        "time": item.get("time", ""),
        "received_at": datetime.now(timezone.utc).isoformat(),
        "source": source,
        "how_to_reply": f"write a JSON file into {dirs['outbox']} with to, msg and reply_to={msg_id}",
        "how_to_mark_handled": f"move this file into {dirs['done']}",
    }
    path = _inbox_msg_path(dirs, msg_id)
    if voice is not None:
        record["voice"] = True
        record["transcribed"] = bool(transcript)
        if not transcript:
            record["note"] = f"Voice message; the transcript follows shortly, or run: thrive_cli voice-get {msg_id}"
        b64 = voice.get("b64")
        if b64:
            try:
                audio_path = path.with_suffix(".mp3")
                audio_path.write_bytes(base64.b64decode(b64))
                record["audio_file"] = audio_path.name
            except Exception as exc:
                emit({"status": "warning", "event": "inbox_voice_save_failed", "id": msg_id, "reason": str(exc)}, args.json)
        else:
            record["audio_file"] = None  # not delivered inline (e.g. caught up while offline); fetch with voice-get
    _inbox_write_atomic(path, record)
    emit({"status": "ok", "event": "inbox_new", "id": msg_id, "from": record["from"], "source": source,
          "voice": voice is not None}, args.json)
    if args.on_message:
        try:
            import subprocess
            env = dict(os.environ, THRIVE_MSG_FILE=str(path), THRIVE_MSG_FROM=str(record["from"]), THRIVE_MSG_ID=msg_id)
            env.pop("THRIVE_PASSWORD", None)
            subprocess.Popen(args.on_message, shell=True, env=env, stdin=subprocess.DEVNULL,
                             stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, start_new_session=True)
        except Exception as exc:
            emit({"status": "warning", "event": "on_message_failed", "reason": str(exc)}, args.json)
    return True


def _inbox_catch_up(sock: socket.socket, reader: "_LineReader", dirs: Dict[str, Path], args: argparse.Namespace, backlog: List[Dict[str, Any]]) -> int:
    """Ask the server for recent history with each contact and file any DM to us that is still unread."""
    found = 0
    for contact in [c.strip() for c in (args.catch_up_with or "").split(",") if c.strip()]:
        rid = uuid.uuid4().hex[:12]
        send_json(sock, {"action": "history_request", "with": contact, "limit": 50, "request_id": rid})
        deadline = time.time() + 15
        while time.time() < deadline:
            event = reader.read(2.0)
            if not event:
                continue
            if event.get("action") == "history" and event.get("request_id") == rid:
                for item in event.get("messages") or []:
                    if (str(item.get("to", "")).lower() == args.username.lower() and not item.get("read_at")
                            and _inbox_store(dirs, item, args, "catch_up")):
                        found += 1
                break
            backlog.append(event)
    return found


def _inbox_flush(sock: socket.socket, dirs: Dict[str, Path], args: argparse.Namespace) -> None:
    # Handled messages -> read receipts.
    acked = []
    for f in sorted(dirs["done"].glob("*.json")):
        try:
            rec = json.loads(f.read_text(encoding="utf-8"))
        except Exception:
            continue
        if rec.get("read_sent"):
            continue
        acked.append(str(rec.get("id") or f.stem))
        rec["read_sent"] = datetime.now(timezone.utc).isoformat()
        _inbox_write_atomic(f, rec)
    if acked:
        send_json(sock, {"action": "msg_read", "ids": acked})
        emit({"status": "ok", "event": "inbox_read_sent", "ids": acked}, args.json)
    # Outbox -> messages. A reply only counts as sent once the server confirms it (msg_sent); if the
    # recipient is offline the server refuses it, so it stays in the outbox and is retried every minute.
    now = time.time()
    for f in sorted(dirs["outbox"].glob("*.json")):
        key = f.name
        state = _OUTBOX_STATE.get(key)
        if state and state.get("waiting"):
            if now - state["sent_at"] > 15:
                state["waiting"] = False
                state["retry_at"] = now + 60
                emit({"status": "warning", "event": "inbox_send_unconfirmed", "file": key,
                      "note": "recipient probably offline; will retry"}, args.json)
            continue
        if state and now < state.get("retry_at", 0):
            continue
        try:
            out = json.loads(f.read_text(encoding="utf-8"))
        except Exception:
            continue
        to, text = str(out.get("to") or "").strip(), str(out.get("msg") or "")
        reply_to = str(out.get("reply_to") or "")
        if not to and reply_to:
            src = _inbox_msg_path(dirs, reply_to)
            if not src.exists():
                src = _inbox_msg_path(dirs, reply_to, "done")
            try:
                to = json.loads(src.read_text(encoding="utf-8")).get("from", "")
            except Exception:
                to = ""
        if not to or not text:
            os.replace(f, dirs["sent"] / (f.stem + ".invalid.json"))
            continue
        ids = []
        for part in split_message(text, 3500):
            cid = uuid.uuid4().hex
            ids.append(cid)
            send_json(sock, {"action": "msg", "to": to, "from": args.username, "msg": part,
                             "time": datetime.now().isoformat(), "client_id": cid})
        _OUTBOX_STATE[key] = {"waiting": True, "sent_at": now, "ids": set(ids), "to": to, "reply_to": reply_to}


_OUTBOX_STATE: Dict[str, Dict[str, Any]] = {}


def _inbox_on_msg_sent(dirs: Dict[str, Path], event: Dict[str, Any], args: argparse.Namespace) -> None:
    cid = str(event.get("client_id") or "")
    for key, state in list(_OUTBOX_STATE.items()):
        if cid in state.get("ids", set()):
            state["ids"].discard(cid)
            if state["ids"]:
                return
            f = dirs["outbox"] / key
            if f.exists():
                os.replace(f, dirs["sent"] / key)
            _OUTBOX_STATE.pop(key, None)
            emit({"status": "ok", "event": "inbox_sent", "to": state["to"], "reply_to": state["reply_to"]}, args.json)
            reply_to = state.get("reply_to")
            if reply_to:
                src = _inbox_msg_path(dirs, reply_to)
                if src.exists():
                    os.replace(src, _inbox_msg_path(dirs, reply_to, "done"))
            return

def _inbox_apply_voice_transcript(dirs: Dict[str, Path], msg_id: str, transcript: str, fallback: str, args: argparse.Namespace) -> bool:
    """A voice DM's transcript usually arrives a few seconds after the message itself (server.py transcribes it
    off its own socket thread); patch the inbox file in place wherever it still sits (new/ or done/)."""
    for sub in ("new", "done"):
        path = _inbox_msg_path(dirs, msg_id, sub)
        if not path.exists():
            continue
        try:
            rec = json.loads(path.read_text(encoding="utf-8"))
        except Exception:
            continue
        rec["msg"] = transcript or fallback
        rec["transcribed"] = bool(transcript)
        rec.pop("note", None)
        _inbox_write_atomic(path, rec)
        emit({"status": "ok", "event": "inbox_voice_transcript", "id": msg_id, "transcribed": bool(transcript)}, args.json)
        return True
    return False


def _inbox_heartbeat_file(dirs: Dict[str, Path], connected: bool, note: str = "") -> None:
    pending = len(list(dirs["new"].glob("*.json")))
    _inbox_write_atomic(dirs["state"] / "heartbeat.json", {
        "time": datetime.now(timezone.utc).isoformat(), "connected": connected, "pending": pending,
        "pid": os.getpid(), "note": note})


def cmd_agent_inbox(args: argparse.Namespace) -> None:
    try:
        sys.stdout.reconfigure(line_buffering=True)  # type: ignore[attr-defined]
    except Exception:
        pass
    dirs = _inbox_dirs(args.inbox.expanduser())
    backoff = 5.0
    while True:
        sock = None
        try:
            try:
                sock = login(args)
            except SystemExit:
                raise ConnectionError("login failed")
            backoff = 5.0
            session_id = f"{args.username}:{args.host_label}:{os.getpid()}:{secrets.token_hex(6)}"
            send_json(sock, {"action": "register_bot_session", "session_id": session_id, "auth_type": "agent",
                             "runtime": "agent-inbox", "host_label": args.host_label, "platform": sys.platform,
                             "capabilities": ["chat"], "transports": ["thrive"], "accepts_files": False,
                             "supports_delegation": False, "background": True})
            for st in _OUTBOX_STATE.values():
                st["waiting"] = False
                st["retry_at"] = 0
            reader = _LineReader(sock)
            backlog: List[Dict[str, Any]] = []
            caught = _inbox_catch_up(sock, reader, dirs, args, backlog)
            emit({"status": "ok", "event": "inbox_connected", "caught_up": caught,
                  "pending": len(list(dirs["new"].glob("*.json")))}, args.json)
            _inbox_heartbeat_file(dirs, True, "connected")
            last_beat = 0.0
            while True:
                event = backlog.pop(0) if backlog else reader.read(2.0)
                action = event.get("action", "")
                if action == "msg" and not event.get("echo") and str(event.get("from", "")).lower() != args.username.lower():
                    _inbox_store(dirs, event, args, "live")
                elif action == "msg_sent":
                    _inbox_on_msg_sent(dirs, event, args)
                elif action == "voice_transcript" and event.get("id"):
                    _inbox_apply_voice_transcript(dirs, str(event["id"]), event.get("transcript") or "",
                                                  event.get("fallback") or "", args)
                elif action and args.verbose:
                    emit({"status": "ok", "event": action}, args.json)
                _inbox_flush(sock, dirs, args)
                if time.time() - last_beat >= args.heartbeat:
                    send_json(sock, {"action": "bot_session_heartbeat", "session_id": session_id, "host_label": args.host_label})
                    _inbox_heartbeat_file(dirs, True, "heartbeat")
                    last_beat = time.time()
        except KeyboardInterrupt:
            _inbox_heartbeat_file(dirs, False, "stopped")
            return
        except Exception as exc:
            _inbox_heartbeat_file(dirs, False, f"disconnected: {exc}")
            emit({"status": "warning", "event": "inbox_disconnected", "reason": str(exc), "retry_in": backoff}, args.json)
        finally:
            if sock is not None:
                try:
                    sock.close()
                except Exception:
                    pass
        time.sleep(backoff)
        backoff = min(60.0, backoff * 2)


def cmd_voice_get(args: argparse.Namespace) -> None:
    """Fetch a voice message's audio by id (works for DMs whether or not the inline copy arrived, e.g. after
    catch-up delivered only the transcript). Saved next to its inbox record when --inbox is given."""
    sock = login(args)
    try:
        rid = uuid.uuid4().hex[:12]
        send_json(sock, {"action": "voice_fetch", "id": args.id, "request_id": rid})
        try:
            event = recv_until_action(sock, ("voice_data",), timeout=args.wait)
        except socket.timeout:
            event = {}
    finally:
        sock.close()
    if not event or not event.get("ok") or not event.get("b64"):
        fail("Voice audio isn't available (message not found, deleted, or you weren't a participant).", args.json)
    raw = base64.b64decode(event["b64"])
    if args.out:
        out_path = Path(args.out).expanduser()
    elif args.inbox:
        dirs = _inbox_dirs(args.inbox.expanduser())
        base_dir = dirs["new"]
        for sub in ("new", "done"):
            if _inbox_msg_path(dirs, args.id, sub).exists():
                base_dir = dirs[sub]
                break
        out_path = base_dir / f"{safe_filename(args.id)}.mp3"
    else:
        out_path = Path.cwd() / f"{safe_filename(args.id)}.mp3"
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_bytes(raw)
    emit({"status": "ok", "id": args.id, "saved": str(out_path), "bytes": len(raw)}, args.json)


def cmd_agent_inbox_ack(args: argparse.Namespace) -> None:
    dirs = _inbox_dirs(args.inbox.expanduser())
    moved = []
    for msg_id in args.ids:
        src = _inbox_msg_path(dirs, msg_id)
        if src.exists():
            os.replace(src, _inbox_msg_path(dirs, msg_id, "done"))
            moved.append(msg_id)
    emit({"status": "ok", "handled": moved, "note": "read receipts go out from the running agent-inbox listener"}, args.json)


def cmd_agent_inbox_reply(args: argparse.Namespace) -> None:
    dirs = _inbox_dirs(args.inbox.expanduser())
    out = {"reply_to": args.id, "msg": args.message if args.message != "-" else sys.stdin.read()}
    if args.to:
        out["to"] = args.to
    path = dirs["outbox"] / f"{int(time.time() * 1000)}-{uuid.uuid4().hex[:6]}.json"
    _inbox_write_atomic(path, out)
    emit({"status": "ok", "queued": str(path), "note": "the running agent-inbox listener sends it and marks the message handled"}, args.json)


def add_common(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--json", action="store_true", help="Print stable JSON output.")
    parser.add_argument("--config", type=Path, default=DEFAULT_CONFIG_PATH, help="Path to srv.conf.")
    parser.add_argument("--db", type=Path, default=DEFAULT_DB_PATH, help="Path to thrive.db for local admin commands.")
    parser.add_argument("--agent-env", type=Path, default=DEFAULT_AGENT_ENV, help="Private env file for service bot passwords.")
    parser.add_argument("--host", default=os.environ.get("THRIVE_HOST", "127.0.0.1"), help="Thrive server host.")
    parser.add_argument("--port", type=int, default=int(os.environ.get("THRIVE_PORT", "2005")), help="Thrive server port.")
    parser.add_argument("--ssl", action="store_true", default=os.environ.get("THRIVE_SSL", "").lower() in ("1", "true", "yes"), help="Use TLS.")
    parser.add_argument("--cafile", default=os.environ.get("THRIVE_CAFILE", ""), help="Optional CA file for TLS.")
    parser.add_argument("--insecure", action="store_true", default=os.environ.get("THRIVE_INSECURE", "").lower() in ("1", "true", "yes"), help="Skip TLS verification for trusted loopback/admin probes.")
    parser.add_argument("--timeout", type=float, default=float(os.environ.get("THRIVE_TIMEOUT", "12")), help="Connection timeout seconds.")


def add_login_args(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--username", "-u", required=True, help="Thrive username.")
    parser.add_argument("--password", help="Password. Prefer THRIVE_PASSWORD or prompt to avoid shell history.")
    parser.add_argument("--no-prompt", action="store_true", help="Fail instead of prompting for password.")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="thrive-cli", description="Thrive Messenger CLI for admins, agents, and CLI users.")
    add_common(parser)
    sub = parser.add_subparsers(dest="command")
    sub.required = True

    p = sub.add_parser("doctor", help="Check config, local DB, and server reachability.")
    p.set_defaults(func=cmd_doctor)

    p = sub.add_parser("users", help="List local server users from thrive.db.")
    p.set_defaults(func=cmd_users_list)

    admin = sub.add_parser("ensure-bots", help="Create or repair service-owned bot accounts in local thrive.db.")
    admin.add_argument("bots", nargs="*", help="Bot names. Defaults to [bots] names from srv.conf.")
    admin.set_defaults(func=cmd_admin_ensure_bots)

    contacts = sub.add_parser("link-bot-contacts", help="Add bot contacts for users and bot-to-bot coordination.")
    contacts.add_argument("--bots", nargs="*", default=[], help="Bot names. Defaults to [bots] names from srv.conf.")
    contacts.add_argument("--users", nargs="+", default=["all"], help="Users to link, or 'all'.")
    contacts.add_argument("--hidden-bots", nargs="*", default=["roomhelper"], help="Internal bots to keep out of normal user contact lists.")
    contacts.add_argument("--mutual", action="store_true", help="Also add users as contacts for each bot.")
    contacts.add_argument("--bot-mesh-contacts", action="store_true", help="Add each bot as a contact for each other bot.")
    contacts.set_defaults(func=cmd_admin_link_bot_contacts)

    rs = sub.add_parser("read-status", help="Show whether messages one user sent another were delivered and read.")
    rs.add_argument("--from", dest="sender", required=True, help="Who sent the messages (e.g. SystemMonitor).")
    rs.add_argument("--to", required=True, help="Who they were sent to (e.g. tappedinfm).")
    rs.add_argument("--since", help="Only messages sent at or after this UTC time (ISO).")
    rs.add_argument("--minutes", type=int, help="Only messages from the last N minutes.")
    rs.add_argument("--limit", type=int, default=20, help="How many recent messages (default 20).")
    rs.add_argument("--ids", nargs="*", default=[], help="Only these message ids.")
    rs.set_defaults(func=cmd_read_status)

    send = sub.add_parser("send", help="Send a direct message.")
    add_login_args(send)
    send.add_argument("--to", required=True, help="Recipient username or bot.")
    send.add_argument("message", help="Message body, or - to read it from stdin.")
    send.add_argument("--wait", type=float, default=1.5, help="Seconds to wait for immediate server replies.")
    send.add_argument("--split-at", type=int, default=20000, help="Split longer messages into labelled parts (0 disables).")
    send.set_defaults(func=cmd_send)

    status = sub.add_parser("set-status", help="Set Available/Away/Busy/Do not disturb/Invisible status.")
    add_login_args(status)
    status.add_argument("presence", choices=["available", "away", "busy", "dnd", "invisible"])
    status.add_argument("--text", default="", help="Optional custom text shown after the status.")
    status.add_argument("--clear-after", type=int, default=0, metavar="MINUTES", help="Clear back to Available after this many minutes.")
    status.set_defaults(func=cmd_set_status)

    react = sub.add_parser("react", help="Add (or with --off remove) a reaction on a message: DM with --to, or --room.")
    add_login_args(react)
    react.add_argument("message_id")
    react.add_argument("emoji", help="An emoji, or a name: thumbsup, thumbsdown, heart, laugh, wow, sad, celebrate, check, seen.")
    react.add_argument("--room", help="Room name or id (for room messages).")
    react.add_argument("--off", action="store_true", help="Remove the reaction instead.")
    react.set_defaults(func=cmd_react)

    room = sub.add_parser("room", help="Chat rooms: list, create, join, leave, post, history, members, invite, topic, read-status, mark-read.")
    add_login_args(room)
    room.add_argument("room_action", choices=ROOM_ACTIONS)
    room.add_argument("room", nargs="?", default="", help="Room name or id (not needed for list).")
    room.add_argument("text", nargs="?", default="", help="Message (- for stdin), username to invite, topic, or message id.")
    room.add_argument("--query", help="Words to search for (list).")
    room.add_argument("--topic", help="Topic for a new room (create).")
    room.add_argument("--description", help="Description for a new room (create).")
    room.add_argument("--private", action="store_true", help="Create a private (invite-only) room.")
    room.add_argument("--role", default="user", help="Role for invite: guest, member, moderator or admin.")
    room.add_argument("--limit", type=int, default=30, help="How many messages (history).")
    room.add_argument("--split-at", type=int, default=4000, help="Split longer posts into labelled parts.")
    room.set_defaults(func=cmd_room)

    contact = sub.add_parser("contact", help="Manage your own contact list like the GUI: add, remove, block, unblock.")
    add_login_args(contact)
    contact.add_argument("contact_action", choices=["add", "remove", "delete", "block", "unblock"])
    contact.add_argument("username_target", help="The username to add, remove, block, or unblock.")
    contact.set_defaults(func=cmd_contact)

    admin_cmd = sub.add_parser("admin-cmd", help="Run any server admin console slash-command, same as the GUI's admin console (admin account required).")
    add_login_args(admin_cmd)
    admin_cmd.add_argument("cmdline", help="The slash-command text, e.g. 'help' or 'ban someuser 12/31/2026 spam'.")
    admin_cmd.set_defaults(func=cmd_admin_cmd)

    version = sub.add_parser("version", help="Show the CLI version and current git commit/branch.")
    version.add_argument("--json", action="store_true")
    version.set_defaults(func=cmd_version, json=False)

    self_update = sub.add_parser("self-update", help="git pull the repo this CLI lives in, so it matches the latest server/CLI version.")
    self_update.add_argument("--json", action="store_true")
    self_update.add_argument("--force", action="store_true", help="Stash local changes and update anyway.")
    self_update.set_defaults(func=cmd_self_update, json=False)

    send_file = sub.add_parser("send-file", help="Offer one or more files to a user and send after acceptance.")
    add_login_args(send_file)
    send_file.add_argument("--to", required=True, help="Recipient username or bot.")
    send_file.add_argument("files", nargs="+", help="File path(s) to send.")
    send_file.add_argument("--wait", type=float, default=30.0, help="Seconds to wait for recipient acceptance.")
    send_file.set_defaults(func=cmd_send_file)

    bot_store = sub.add_parser("bot-store-file", help="Store a file in the bot mesh and notify the target bot.")
    add_login_args(bot_store)
    bot_store.add_argument("--to", required=True, help="Target bot username.")
    bot_store.add_argument("file", help="File path to store.")
    bot_store.add_argument("--mime", default="", help="Override MIME type.")
    bot_store.add_argument("--request-id", default="", help="Optional request id to correlate with a bot task.")
    bot_store.add_argument("--wait", type=float, default=10.0, help="Seconds to wait for server response.")
    bot_store.set_defaults(func=cmd_bot_store_file)

    bot_fetch = sub.add_parser("bot-fetch-file", help="Fetch a bot-mesh file by id and save it locally.")
    add_login_args(bot_fetch)
    bot_fetch.add_argument("file_id", help="Bot mesh file id.")
    bot_fetch.add_argument("--output-dir", type=Path, default=Path.cwd(), help="Directory to save the fetched file.")
    bot_fetch.add_argument("--consume", action="store_true", help="Remove the bot-mesh temp file after fetching.")
    bot_fetch.add_argument("--include-data", action="store_true", help="Include base64 data in JSON output.")
    bot_fetch.add_argument("--wait", type=float, default=10.0, help="Seconds to wait for server response.")
    bot_fetch.set_defaults(func=cmd_bot_fetch_file)

    listen = sub.add_parser("listen", help="Log in and print incoming events.")
    add_login_args(listen)
    listen.add_argument("--save-dir", type=Path, default=None, help="Directory for received file_data or bot-mesh files.")
    listen.add_argument("--auto-accept-files", action="store_true", help="Automatically accept incoming direct file offers.")
    listen.add_argument("--mark-read", action="store_true", help="Send read receipts for incoming direct messages as they arrive.")
    listen.add_argument("--auto-fetch-bot-files", action="store_true", help="Automatically fetch bot-mesh file_available events.")
    listen.add_argument("--consume-bot-files", action="store_true", help="Consume bot-mesh files after auto-fetching.")
    listen.add_argument("--include-data", action="store_true", help="Include base64 file data in JSON output.")
    listen.add_argument("--auto-decline-calls", action="store_true", help="Decline incoming direct voice calls instead of leaving them ringing.")
    listen.add_argument("--call-decline-message", default="", help="Optional direct message sent to the caller after auto-declining.")
    listen.set_defaults(func=cmd_listen)

    reg = sub.add_parser("register-bot-session", help="Log in as a bot and advertise bot-mesh capabilities.")
    add_login_args(reg)
    reg.add_argument("--auth-type", default="bot", help="Auth/runtime type label such as ollama, codex, claude, openclaw.")
    reg.add_argument("--runtime", default="cli", help="Runtime label.")
    reg.add_argument("--host-label", default=socket.gethostname(), help="Human-readable host label.")
    reg.add_argument("--platform", default=sys.platform, help="Platform label.")
    reg.add_argument("--capabilities", nargs="*", default=["chat", "delegate", "status"], help="Capability labels.")
    reg.add_argument("--transports", nargs="*", default=["thrive"], help="Transport labels.")
    reg.add_argument("--accepts-files", action="store_true", help="Advertise file support.")
    reg.add_argument("--no-delegation", action="store_true", help="Disable delegation support.")
    reg.add_argument("--background", action="store_true", help="Advertise this as a background bot session.")
    reg.add_argument("--moderation", action="store_true", help="Enable moderation event watch if policy allows.")
    reg.add_argument("--moderation-kinds", nargs="*", default=["direct_message", "file_offer"], help="Moderation event kinds.")
    reg.add_argument("--notify-user", default="", help="User to notify for moderation events.")
    reg.add_argument("--wait", type=float, default=5.0, help="Seconds to wait for the bot session registration response.")
    reg.add_argument("--provider-health", action="store_true", help="Ask the server for redacted agent provider health after registration.")
    reg.add_argument("--listen", action="store_true", help="Keep listening after registration.")
    reg.add_argument("--auto-decline-calls", action="store_true", help="Decline incoming direct voice calls instead of leaving them ringing.")
    reg.add_argument("--call-decline-message", default="", help="Optional direct message sent to the caller after auto-declining.")
    reg.set_defaults(func=cmd_register_bot_session)

    voice_get = sub.add_parser("voice-get", help="Fetch a voice message's audio by id (a DM you sent or received).")
    add_login_args(voice_get)
    voice_get.add_argument("id", help="Message id (the inbox record's \"id\" field).")
    voice_get.add_argument("--out", help="Save path. Default: next to the inbox record (--inbox), or ID.mp3 in the current directory.")
    voice_get.add_argument("--inbox", type=Path, help="Inbox folder to save next to (matches agent-inbox's --inbox).")
    voice_get.add_argument("--wait", type=float, default=10.0, help="Seconds to wait for the server response.")
    voice_get.set_defaults(func=cmd_voice_get)

    inbox = sub.add_parser("agent-inbox", help="Reliable DM hand-off for agents: inbox files, read receipts only after the agent handles a message, replies via outbox, catch-up, auto-reconnect, heartbeat.")
    add_login_args(inbox)
    inbox.add_argument("--inbox", type=Path, required=True, help="Persistent inbox folder (new/, done/, outbox/, sent/, state/). Never under /tmp.")
    inbox.add_argument("--catch-up-with", default="tappedinfm,SystemMonitor,Clawdia", help="Comma-separated contacts whose unread DMs are fetched on every (re)connect.")
    inbox.add_argument("--on-message", default="", help="Shell command run (detached) for each new DM; gets THRIVE_MSG_FILE, THRIVE_MSG_FROM, THRIVE_MSG_ID. Use it to wake the agent.")
    inbox.add_argument("--heartbeat", type=float, default=30.0, help="Seconds between presence heartbeats.")
    inbox.add_argument("--host-label", default=socket.gethostname(), help="Host label shown in the bot session.")
    inbox.add_argument("--verbose", action="store_true", help="Print every server event, not just inbox events.")
    inbox.set_defaults(func=cmd_agent_inbox)

    ack = sub.add_parser("agent-inbox-ack", help="Mark inbox messages handled (moves new/ID.json to done/); the running listener then sends the read receipts.")
    ack.add_argument("--inbox", type=Path, required=True)
    ack.add_argument("ids", nargs="+")
    ack.set_defaults(func=cmd_agent_inbox_ack)

    rep = sub.add_parser("agent-inbox-reply", help="Queue a reply for the running agent-inbox listener to send (and mark the message handled).")
    rep.add_argument("--inbox", type=Path, required=True)
    rep.add_argument("--id", required=True, help="Inbox message id being answered.")
    rep.add_argument("--to", default="", help="Recipient (default: the sender of --id).")
    rep.add_argument("message", help="Reply text, or - for stdin.")
    rep.set_defaults(func=cmd_agent_inbox_reply)

    return parser


def main(argv: Optional[List[str]] = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        args.func(args)
        return 0
    except BrokenPipeError:
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
