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
import sqlite3
import ssl
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional

try:
    from argon2 import PasswordHasher
except Exception:  # pragma: no cover - optional server dependency
    PasswordHasher = None  # type: ignore


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
    if PasswordHasher is None:
        return password
    return PasswordHasher().hash(password)


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


def cmd_send(args: argparse.Namespace) -> None:
    sock = login(args)
    try:
        send_json(sock, {"action": "msg", "from": args.username, "to": args.to, "msg": args.message})
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
        send_json(sock, {"action": "msg", "to": caller, "from": args.username, "msg": message})
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
                if saved_files:
                    body = f"saved {len(saved_files)} file(s): " + ", ".join(str(item.get("path", item.get("error", ""))) for item in saved_files)
                print(f"{datetime.now().isoformat()} {action} {sender}: {body}", flush=True)
    except KeyboardInterrupt:
        pass
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

    send = sub.add_parser("send", help="Send a direct message.")
    add_login_args(send)
    send.add_argument("--to", required=True, help="Recipient username or bot.")
    send.add_argument("message", help="Message body.")
    send.add_argument("--wait", type=float, default=1.5, help="Seconds to wait for immediate server replies.")
    send.set_defaults(func=cmd_send)

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
