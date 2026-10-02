"""Safe, portable backups and personal data exports for Thrive.

Archives are kept outside the application/web directory. A database is always
read with SQLite's online backup API; copying a live WAL database is not safe.
"""
import datetime as dt
import hashlib
import html
import io
import json
import os
import shutil
import sqlite3
import subprocess
import tempfile
import zipfile
from pathlib import Path
from typing import Any, Iterable, Optional

try:
    from cryptography.fernet import Fernet
except Exception:  # optional, so non-encrypted backups can still be made
    Fernet = None

FORMAT, VERSION = "thrive-backup", 1
DEFAULT_ROOT = Path(os.environ.get("THRIVE_BACKUP_DIR", "/var/lib/thrive/backups"))
USER_TABLES = ("users", "contacts", "direct_message_history", "group_rooms", "group_room_members", "group_room_messages", "message_reactions", "server_settings")

def _now():
    return dt.datetime.now(dt.timezone.utc).replace(microsecond=0).isoformat()

def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()

def online_sqlite_snapshot(db_path: Path, destination: Path) -> None:
    """Consistent snapshot; does not copy a live database file."""
    destination.parent.mkdir(parents=True, exist_ok=True)
    src = sqlite3.connect("file:%s?mode=ro" % db_path.resolve(), uri=True)
    try:
        if hasattr(src, "backup"):
            dst = sqlite3.connect(str(destination))
            try: src.backup(dst, pages=256, sleep=0.01)
            finally: dst.close()
        else:
            # Python 3.6 lacks Connection.backup. sqlite3's .backup command calls
            # the same SQLite online-backup API and is intentionally never a file copy.
            result = subprocess.run(["sqlite3", str(db_path), ".backup %s" % str(destination)], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            if result.returncode: raise RuntimeError("SQLite online backup failed")
        check = sqlite3.connect(str(destination))
        try:
            if check.execute("PRAGMA integrity_check").fetchone()[0] != "ok": raise RuntimeError("SQLite backup integrity check failed")
        finally: check.close()
    finally: src.close()

def _tables(con):
    return {row[0] for row in con.execute("SELECT name FROM sqlite_master WHERE type='table'")}

def _rows(con, table, where="", values=()):
    if table not in _tables(con): return []
    cur = con.execute(f"SELECT * FROM {table} {where}", values)
    keys = [d[0] for d in cur.description]
    return [dict(zip(keys, row)) for row in cur.fetchall()]

def _scope(scope: Optional[Iterable[str]]):
    allowed = {"settings", "users", "rooms", "messages", "files", "all"}
    result = {str(x).lower() for x in (scope or ("all",))}
    if not result <= allowed: raise ValueError("scope: settings, users, rooms, messages, files, all")
    return result

def _json(zf, name, value):
    zf.writestr(name, json.dumps(value, ensure_ascii=False, indent=2, default=str))

def _selected_data(snapshot: Path, scope, user=None, since=None):
    con = sqlite3.connect(str(snapshot))
    try:
        wanted = set(USER_TABLES)
        if "all" not in scope:
            if "settings" not in scope: wanted.discard("server_settings")
            if "users" not in scope: wanted -= {"users", "contacts"}
            if "rooms" not in scope: wanted -= {"group_rooms", "group_room_members"}
            if "messages" not in scope: wanted -= {"direct_message_history", "group_room_messages", "message_reactions"}
        result = {"scope": sorted(scope), "user": user, "since": since, "tables": {}}
        for table in wanted:
            where, values = "", ()
            if user:
                filters = {
                    "users": ("WHERE username=?", (user,)), "contacts": ("WHERE owner=? OR contact=?", (user, user)),
                    "direct_message_history": ("WHERE frm=? OR to_user=?", (user, user)),
                    "group_room_members": ("WHERE username=?", (user,)),
                    "group_rooms": ("WHERE id IN (SELECT room_id FROM group_room_members WHERE username=?)", (user,)),
                    "group_room_messages": ("WHERE room_id IN (SELECT room_id FROM group_room_members WHERE username=?)", (user,)),
                }
                if table == "message_reactions": continue
                where, values = filters.get(table, ("", ()))
            if since and table in {"direct_message_history", "group_room_messages"}:
                where += (" AND " if where else "WHERE ") + "created_at>=?"; values += (since,)
            result["tables"][table] = _rows(con, table, where, values)
        if user:
            for row in result["tables"].get("users", []):
                for secret in ("password", "reset_code", "verification_code"): row.pop(secret, None)
        return result
    finally: con.close()

def create_backup(*, db_path: Path, storage_root: Path = DEFAULT_ROOT, voice_dir: Optional[Path] = None,
                  requested_by: str, scope: Optional[Iterable[str]] = None, user: Optional[str] = None,
                  since: Optional[str] = None, encryption_key: str = "") -> Path:
    """Create full, partial, or per-user backup. Fernet encryption is optional."""
    scope = _scope(scope); full = "all" in scope and not user
    stamp = dt.datetime.now(dt.timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    kind = "full" if full else ("user-" + user if user else "partial")
    out_dir = storage_root / dt.datetime.now(dt.timezone.utc).strftime("%Y/%m")
    out_dir.mkdir(parents=True, mode=0o700, exist_ok=True); os.chmod(out_dir, 0o700)
    archive = out_dir / f"thrive-{kind}-{stamp}.thrive-backup"
    temp = Path(tempfile.mkdtemp(prefix="thrive-backup-", dir=out_dir))
    try:
        snapshot = temp / "thrive.db"; online_sqlite_snapshot(db_path, snapshot)
        data = _selected_data(snapshot, scope, user, since)
        with zipfile.ZipFile(archive, "w", zipfile.ZIP_DEFLATED) as zf:
            if full: zf.write(snapshot, "database/thrive.db")
            _json(zf, "data/export.json", data)
            if voice_dir and (full or "files" in scope) and voice_dir.exists():
                for source in voice_dir.rglob("*"):
                    if source.is_file() and (not user or user in source.parts):
                        zf.write(source, "files/voice/" + str(source.relative_to(voice_dir)))
            _json(zf, "manifest.json", {"format": FORMAT, "format_version": VERSION, "created_at": _now(), "requested_by": requested_by, "scope": sorted(scope), "user": user, "since": since, "encrypted": bool(encryption_key), "contents": [i.filename for i in zf.infolist()]})
        final = archive
        if encryption_key:
            if Fernet is None: raise RuntimeError("encryption needs the cryptography package")
            key = encryption_key.encode("ascii")
            if len(key) != 44: raise ValueError("encryption key must be a Fernet key")
            final = archive.with_suffix(archive.suffix + ".enc")
            final.write_bytes(Fernet(key).encrypt(archive.read_bytes())); archive.unlink()
        final.with_suffix(final.suffix + ".sha256").write_text(_sha256(final) + "  " + final.name + "\n")
        os.chmod(final, 0o600)
        return final
    finally: shutil.rmtree(temp, ignore_errors=True)

def verify_archive(path: Path, encryption_key=""):
    raw = path.read_bytes()
    if path.suffix == ".enc":
        if not encryption_key or Fernet is None: raise ValueError("encrypted archive needs its encryption key")
        raw = Fernet(encryption_key.encode("ascii")).decrypt(raw)
    with zipfile.ZipFile(io.BytesIO(raw)) as zf:
        manifest = json.loads(zf.read("manifest.json"))
        if manifest.get("format") != FORMAT or int(manifest.get("format_version", 0)) > VERSION: raise ValueError("unsupported Thrive archive")
        if zf.testzip(): raise ValueError("archive checksum failed")
    return {"ok": True, "sha256": _sha256(path), "created_at": manifest["created_at"], "scope": manifest["scope"], "user": manifest.get("user")}

def export_user_readable(*, db_path: Path, output: Path, username: str):
    """Readable personal data archive: JSON, simple HTML, and text."""
    temp = Path(tempfile.mkdtemp(prefix="thrive-user-export-"))
    try:
        source = create_backup(db_path=db_path, storage_root=temp, requested_by=username, scope=("settings", "users", "rooms", "messages"), user=username)
        with zipfile.ZipFile(source) as zf: data = json.loads(zf.read("data/export.json"))
        title = f"Thrive data export for {username}"
        lines = [title, "Generated: " + _now(), "", "This includes your profile, contacts, messages, visible rooms and settings.", ""]
        for table, rows in data["tables"].items(): lines += [table.replace("_", " ").title() + f" ({len(rows)})"] + [json.dumps(r, ensure_ascii=False, default=str) for r in rows] + [""]
        text = "\n".join(lines); output.parent.mkdir(parents=True, exist_ok=True)
        with zipfile.ZipFile(output, "w", zipfile.ZIP_DEFLATED) as zf:
            _json(zf, "data.json", data); zf.writestr("read-me.txt", text)
            zf.writestr("read-me.html", "<!doctype html><html lang='en'><meta charset='utf-8'><title>" + html.escape(title) + "</title><body><h1>" + html.escape(title) + "</h1><pre>" + html.escape(text) + "</pre></body></html>")
        os.chmod(output, 0o600); return output
    finally: shutil.rmtree(temp, ignore_errors=True)
