"""Chat rooms (group chats): stored in thrive.db, so rooms, members and history survive restarts.

Roles, lowest to highest: guest, member (stored as "user"), moderator, admin, owner.
Every function takes the database path first and raises RoomError with a message safe to show people.
Python 3.6 compatible (the live server's interpreter)."""

import json
import re
import sqlite3
import time
import uuid

ROLE_RANK = {"guest": 0, "user": 1, "moderator": 2, "admin": 3, "owner": 4}
ROLE_ALIASES = {"member": "user"}
ROLE_LABELS = {"guest": "guest", "user": "member", "moderator": "moderator", "admin": "admin", "owner": "owner"}
DEFAULT_PERMISSIONS = {
    "view": ["guest", "user", "moderator", "admin", "owner"],
    "send_messages": ["guest", "user", "moderator", "admin", "owner"],
    "send_files": ["user", "moderator", "admin", "owner"],
    "send_voice": ["user", "moderator", "admin", "owner"],
    "join_voice": ["user", "moderator", "admin", "owner"],
    "invite": ["user", "moderator", "admin", "owner"],
    "set_topic": ["moderator", "admin", "owner"],
    "moderate_messages": ["moderator", "admin", "owner"],
    "moderate_members": ["moderator", "admin", "owner"],
    "manage_members": ["admin", "owner"],
    "manage_room": ["owner"],
}
EXPIRATION_SECONDS = {"day": 86400, "week": 7 * 86400, "month": 30 * 86400, "year": 365 * 86400}
MAX_MESSAGE = 4000
MENTION_RE = re.compile(r"(?<![\w@])@([A-Za-z0-9_.-]{2,64})")


class RoomError(ValueError):
    """A problem that can be shown to the person who asked."""


def _con(db):
    con = sqlite3.connect(str(db), timeout=15)
    con.row_factory = sqlite3.Row
    con.execute("PRAGMA foreign_keys=ON")
    return con


def _role(value):
    value = str(value or "").strip().lower()
    return ROLE_ALIASES.get(value, value)


def init_schema(db):
    con = _con(db)
    try:
        con.executescript("""
            CREATE TABLE IF NOT EXISTS group_rooms (
                room_id TEXT PRIMARY KEY,
                name TEXT NOT NULL COLLATE NOCASE UNIQUE,
                owner TEXT NOT NULL,
                description TEXT NOT NULL DEFAULT '',
                topic TEXT NOT NULL DEFAULT '',
                visibility TEXT NOT NULL DEFAULT 'public',
                permissions_json TEXT NOT NULL,
                created_at REAL NOT NULL,
                expires_at REAL,
                expire_when_empty INTEGER NOT NULL DEFAULT 0
            );
            CREATE TABLE IF NOT EXISTS group_room_members (
                room_id TEXT NOT NULL,
                username TEXT NOT NULL COLLATE NOCASE,
                role TEXT NOT NULL,
                joined_at REAL NOT NULL,
                last_read_at REAL NOT NULL DEFAULT 0,
                muted_until REAL NOT NULL DEFAULT 0,
                PRIMARY KEY(room_id, username),
                FOREIGN KEY(room_id) REFERENCES group_rooms(room_id) ON DELETE CASCADE
            );
            CREATE TABLE IF NOT EXISTS group_room_messages (
                message_id TEXT PRIMARY KEY,
                room_id TEXT NOT NULL,
                sender TEXT NOT NULL,
                body TEXT NOT NULL DEFAULT '',
                kind TEXT NOT NULL DEFAULT 'text',
                filename TEXT NOT NULL DEFAULT '',
                sent_at REAL NOT NULL,
                deleted INTEGER NOT NULL DEFAULT 0,
                edited_at REAL,
                edited_by TEXT,
                voice_path TEXT,
                voice_duration REAL,
                mentions_json TEXT NOT NULL DEFAULT '[]',
                client_id TEXT NOT NULL DEFAULT '',
                transcript TEXT,
                FOREIGN KEY(room_id) REFERENCES group_rooms(room_id) ON DELETE CASCADE
            );
            CREATE INDEX IF NOT EXISTS idx_group_messages_room_time ON group_room_messages(room_id, sent_at);
            CREATE TABLE IF NOT EXISTS group_room_bans (
                room_id TEXT NOT NULL,
                username TEXT NOT NULL COLLATE NOCASE,
                banned_by TEXT NOT NULL,
                reason TEXT NOT NULL DEFAULT '',
                banned_at REAL NOT NULL,
                PRIMARY KEY(room_id, username),
                FOREIGN KEY(room_id) REFERENCES group_rooms(room_id) ON DELETE CASCADE
            );
        """)
        msg_cols = [row[1] for row in con.execute("PRAGMA table_info(group_room_messages)")]
        if "transcript" not in msg_cols:
            con.execute("ALTER TABLE group_room_messages ADD COLUMN transcript TEXT")
        con.commit()
    finally:
        con.close()


def set_transcript(db, message_id, transcript):
    """Cache a voice message's transcript once (server.py calls this from a background thread)."""
    con = _con(db)
    try:
        con.execute("UPDATE group_room_messages SET transcript=? WHERE message_id=?", (transcript or "", message_id))
        con.commit()
    finally:
        con.close()


def _permissions(raw):
    out = {k: list(v) for k, v in DEFAULT_PERMISSIONS.items()}
    for action, roles in (raw or {}).items():
        if action in out and isinstance(roles, list):
            out[action] = [r for r in (_role(x) for x in roles) if r in ROLE_RANK]
            if "owner" not in out[action]:
                out[action].append("owner")  # the owner can always do everything
    return out


def _room_dict(row, member_count=0, role="", unread=0, last_activity=None):
    return {
        "room_id": row["room_id"], "name": row["name"], "owner": row["owner"],
        "description": row["description"], "topic": row["topic"], "visibility": row["visibility"],
        "permissions": _permissions(json.loads(row["permissions_json"] or "{}")),
        "created_at": row["created_at"], "expires_at": row["expires_at"],
        "expire_when_empty": bool(row["expire_when_empty"]), "member_count": member_count,
        "role": role, "role_label": ROLE_LABELS.get(role, ""), "unread": unread, "last_activity": last_activity,
    }


def purge_expired(db, now=None):
    now = time.time() if now is None else now
    con = _con(db)
    try:
        ids = [r[0] for r in con.execute("SELECT room_id FROM group_rooms WHERE expires_at IS NOT NULL AND expires_at<=?", (now,))]
        for room_id in ids:
            con.execute("DELETE FROM group_rooms WHERE room_id=?", (room_id,))
        con.commit()
    finally:
        con.close()
    return ids


def create_room(db, owner, name, description="", topic="", visibility="public", expiration="never", permissions=None):
    name = re.sub(r"\s+", " ", str(name or "")).strip()
    if not name or len(name) > 80:
        raise RoomError("Room name must be 1 to 80 characters.")
    visibility = visibility if visibility in ("public", "private") else "public"
    expiration = str(expiration or "never").lower()
    if expiration not in EXPIRATION_SECONDS and expiration not in ("never", "empty"):
        raise RoomError("Expiration must be day, week, month, year, empty or never.")
    expires_at = time.time() + EXPIRATION_SECONDS[expiration] if expiration in EXPIRATION_SECONDS else None
    room_id = str(uuid.uuid4())
    now = time.time()
    con = _con(db)
    try:
        con.execute("INSERT INTO group_rooms (room_id, name, owner, description, topic, visibility, permissions_json, created_at, "
                    "expires_at, expire_when_empty) VALUES (?,?,?,?,?,?,?,?,?,?)",
                    (room_id, name, owner, str(description or "")[:1000], str(topic or "")[:300], visibility,
                     json.dumps(_permissions(permissions)), now, expires_at, int(expiration == "empty")))
        con.execute("INSERT INTO group_room_members (room_id, username, role, joined_at, last_read_at) VALUES (?,?,?,?,?)",
                    (room_id, owner, "owner", now, now))
        con.commit()
    except sqlite3.IntegrityError:
        raise RoomError("A room with that name already exists.")
    finally:
        con.close()
    return get_room(db, room_id, owner)


def _find_room(con, room_id):
    row = con.execute("SELECT * FROM group_rooms WHERE room_id=?", (str(room_id or ""),)).fetchone()
    if not row:
        raise RoomError("That room wasn't found. It may have been deleted or expired.")
    return row


def get_room(db, room_id, username=""):
    purge_expired(db)
    con = _con(db)
    try:
        row = _find_room(con, room_id)
        count = con.execute("SELECT COUNT(*) FROM group_room_members WHERE room_id=?", (room_id,)).fetchone()[0]
        me = con.execute("SELECT role, last_read_at FROM group_room_members WHERE room_id=? AND username=?", (room_id, username)).fetchone()
        unread = 0
        if me:
            unread = con.execute("SELECT COUNT(*) FROM group_room_messages WHERE room_id=? AND deleted=0 AND sent_at>? AND sender<>? COLLATE NOCASE",
                                 (room_id, me["last_read_at"], username)).fetchone()[0]
    finally:
        con.close()
    return _room_dict(row, count, me["role"] if me else "", unread)


def room_by_name(db, name, username=""):
    con = _con(db)
    try:
        row = con.execute("SELECT room_id FROM group_rooms WHERE name=? COLLATE NOCASE", (str(name or "").strip(),)).fetchone()
    finally:
        con.close()
    if not row:
        raise RoomError("No room has that name.")
    return get_room(db, row[0], username)


def list_rooms(db, username, query=""):
    """Public rooms plus private rooms you're in, optionally filtered by words in the name, topic or description."""
    purge_expired(db)
    con = _con(db)
    try:
        rows = con.execute(
            """SELECT r.*, (SELECT COUNT(*) FROM group_room_members m WHERE m.room_id=r.room_id) AS member_count,
                      COALESCE(me.role, '') AS my_role, COALESCE(me.last_read_at, 0) AS my_read,
                      (SELECT MAX(sent_at) FROM group_room_messages x WHERE x.room_id=r.room_id AND x.deleted=0) AS last_activity
               FROM group_rooms r
               LEFT JOIN group_room_members me ON me.room_id=r.room_id AND me.username=?
               WHERE r.visibility='public' OR me.username IS NOT NULL
               ORDER BY lower(r.name)""", (username,)).fetchall()
        out = []
        words = [w for w in str(query or "").lower().split() if w]
        for row in rows:
            hay = " ".join((row["name"], row["topic"], row["description"])).lower()
            if words and not all(w in hay for w in words):
                continue
            unread = 0
            if row["my_role"]:
                unread = con.execute("SELECT COUNT(*) FROM group_room_messages WHERE room_id=? AND deleted=0 AND sent_at>? AND sender<>? COLLATE NOCASE",
                                     (row["room_id"], row["my_read"], username)).fetchone()[0]
            out.append(_room_dict(row, row["member_count"], row["my_role"], unread, row["last_activity"]))
    finally:
        con.close()
    return out


def rooms_for_user(db, username):
    con = _con(db)
    try:
        return [r[0] for r in con.execute("SELECT room_id FROM group_room_members WHERE username=?", (username,))]
    finally:
        con.close()


def member_role(db, room_id, username):
    con = _con(db)
    try:
        row = con.execute("SELECT role FROM group_room_members WHERE room_id=? AND username=?", (room_id, username)).fetchone()
    finally:
        con.close()
    return row[0] if row else ""


def can(db, room_id, username, action):
    room = get_room(db, room_id, username)
    return bool(room["role"] and room["role"] in room["permissions"].get(action, []))


def _require(db, room_id, username, action, message):
    if not can(db, room_id, username, action):
        raise RoomError(message)


def is_banned(db, room_id, username):
    con = _con(db)
    try:
        return con.execute("SELECT 1 FROM group_room_bans WHERE room_id=? AND username=?", (room_id, username)).fetchone() is not None
    finally:
        con.close()


def join_room(db, room_id, username):
    room = get_room(db, room_id, username)
    if room["role"]:
        return room
    if is_banned(db, room_id, username):
        raise RoomError("You've been banned from this room.")
    if room["visibility"] != "public":
        raise RoomError("This private room needs an invitation from a member.")
    now = time.time()
    con = _con(db)
    try:
        con.execute("INSERT INTO group_room_members (room_id, username, role, joined_at, last_read_at) VALUES (?,?,?,?,?)",
                    (room_id, username, "user", now, now))
        con.commit()
    finally:
        con.close()
    return get_room(db, room_id, username)


def leave_room(db, room_id, username):
    """Returns True if the room was deleted because it's set to expire when empty."""
    room = get_room(db, room_id, username)
    if not room["role"]:
        raise RoomError("You're not in this room.")
    con = _con(db)
    try:
        if room["role"] == "owner":
            if room["member_count"] > 1:
                raise RoomError("As the owner, make someone else the owner (or delete the room) before leaving.")
            if room["expire_when_empty"]:
                con.execute("DELETE FROM group_rooms WHERE room_id=?", (room_id,))
                con.commit()
                return True
            raise RoomError("You're the only member and the owner. Delete the room instead, or invite someone and hand it over.")
        con.execute("DELETE FROM group_room_members WHERE room_id=? AND username=?", (room_id, username))
        remaining = con.execute("SELECT COUNT(*) FROM group_room_members WHERE room_id=?", (room_id,)).fetchone()[0]
        deleted = bool(not remaining and room["expire_when_empty"])
        if deleted:
            con.execute("DELETE FROM group_rooms WHERE room_id=?", (room_id,))
        con.commit()
        return deleted
    finally:
        con.close()


def delete_room(db, room_id, actor, server_admin=False):
    room = get_room(db, room_id, actor)
    if room["role"] != "owner" and not server_admin:
        raise RoomError("Only the room owner can delete the room.")
    con = _con(db)
    try:
        con.execute("DELETE FROM group_rooms WHERE room_id=?", (room_id,))
        con.commit()
    finally:
        con.close()
    return room


def add_member(db, room_id, actor, target, role="user", actor_is_server_admin=False):
    """Invite someone. Anyone allowed to invite can add members; making them moderator or admin needs a higher role."""
    target = str(target or "").strip()
    role = _role(role or "user")
    if not target:
        raise RoomError("Say who to invite.")
    if role not in ROLE_RANK or role == "owner":
        raise RoomError("Invite someone as guest, member, moderator or admin.")
    actor_role = member_role(db, room_id, actor)
    if not actor_is_server_admin:
        _require(db, room_id, actor, "invite", "Your room role can't invite people.")
        if ROLE_RANK[role] > ROLE_RANK["user"] and ROLE_RANK[role] >= ROLE_RANK.get(actor_role, -1):
            raise RoomError("You can only give people a role lower than your own.")
    if member_role(db, room_id, target):
        raise RoomError(f"{target} is already in this room.")
    now = time.time()
    con = _con(db)
    try:
        con.execute("DELETE FROM group_room_bans WHERE room_id=? AND username=?", (room_id, target))
        con.execute("INSERT INTO group_room_members (room_id, username, role, joined_at, last_read_at) VALUES (?,?,?,?,?)",
                    (room_id, target, role, now, now))
        con.commit()
    finally:
        con.close()


def update_room(db, room_id, actor, changes):
    room = get_room(db, room_id, actor)
    changes = changes or {}
    only_topic = set(changes) <= {"topic"}
    if only_topic:
        _require(db, room_id, actor, "set_topic", "Your room role can't change the topic.")
    elif room["role"] != "owner":
        raise RoomError("Only the room owner can change room settings.")
    visibility = str(changes.get("visibility", room["visibility"]))
    if visibility not in ("public", "private"):
        raise RoomError("Visibility must be public or private.")
    expires_at, expire_when_empty = room["expires_at"], room["expire_when_empty"]
    expiration = str(changes.get("expiration", "unchanged"))
    if expiration != "unchanged":
        if expiration not in EXPIRATION_SECONDS and expiration not in ("never", "empty"):
            raise RoomError("That expiration isn't valid.")
        expire_when_empty = expiration == "empty"
        expires_at = time.time() + EXPIRATION_SECONDS[expiration] if expiration in EXPIRATION_SECONDS else None
    name = re.sub(r"\s+", " ", str(changes.get("name", room["name"]))).strip()
    if not name or len(name) > 80:
        raise RoomError("Room name must be 1 to 80 characters.")
    con = _con(db)
    try:
        con.execute("UPDATE group_rooms SET name=?, description=?, topic=?, visibility=?, permissions_json=?, expires_at=?, expire_when_empty=? "
                    "WHERE room_id=?",
                    (name, str(changes.get("description", room["description"]))[:1000], str(changes.get("topic", room["topic"]))[:300],
                     visibility, json.dumps(_permissions(changes.get("permissions", room["permissions"]))), expires_at,
                     int(expire_when_empty), room_id))
        con.commit()
    except sqlite3.IntegrityError:
        raise RoomError("A room with that name already exists.")
    finally:
        con.close()
    return get_room(db, room_id, actor)


def list_members(db, room_id):
    con = _con(db)
    try:
        rows = con.execute(
            "SELECT username, role, last_read_at, muted_until FROM group_room_members WHERE room_id=? ORDER BY CASE role WHEN 'owner' THEN 0 "
            "WHEN 'admin' THEN 1 WHEN 'moderator' THEN 2 WHEN 'user' THEN 3 ELSE 4 END, lower(username)", (room_id,)).fetchall()
    finally:
        con.close()
    now = time.time()
    return [{"username": r["username"], "role": r["role"], "role_label": ROLE_LABELS.get(r["role"], r["role"]),
             "last_read_at": r["last_read_at"], "muted": r["muted_until"] > now, "muted_until": r["muted_until"] if r["muted_until"] > now else 0}
            for r in rows]


def list_bans(db, room_id):
    con = _con(db)
    try:
        return [dict(r) for r in con.execute("SELECT username, banned_by, reason, banned_at FROM group_room_bans WHERE room_id=? ORDER BY banned_at DESC",
                                             (room_id,))]
    finally:
        con.close()


def _outranks(db, room_id, actor, target, action, actor_is_server_admin=False):
    """actor may act on target: has the permission and a strictly higher role (server admins always may, except on the owner)."""
    target_role = member_role(db, room_id, target)
    if actor_is_server_admin:
        if target_role == "owner":
            raise RoomError("The room owner can't be changed this way.")
        return target_role
    actor_role = member_role(db, room_id, actor)
    if not actor_role or actor_role not in get_room(db, room_id, actor)["permissions"].get(action, []):
        raise RoomError("Your room role can't do that.")
    if target_role and ROLE_RANK[target_role] >= ROLE_RANK[actor_role]:
        raise RoomError("You can't do that to someone with the same or a higher role.")
    return target_role


def set_member_role(db, room_id, actor, target, role, actor_is_server_admin=False):
    role = _role(role)
    if role == "owner":
        return transfer_ownership(db, room_id, actor, target)
    if role not in ROLE_RANK:
        raise RoomError("Role must be guest, member, moderator or admin.")
    target_role = _outranks(db, room_id, actor, target, "manage_members", actor_is_server_admin)
    if not target_role:
        raise RoomError(f"{target} isn't in this room.")
    if not actor_is_server_admin and ROLE_RANK[role] >= ROLE_RANK[member_role(db, room_id, actor)]:
        raise RoomError("You can only give people a role lower than your own.")
    con = _con(db)
    try:
        con.execute("UPDATE group_room_members SET role=? WHERE room_id=? AND username=?", (role, room_id, target))
        con.commit()
    finally:
        con.close()


def transfer_ownership(db, room_id, actor, target):
    if member_role(db, room_id, actor) != "owner":
        raise RoomError("Only the owner can hand the room over.")
    if not member_role(db, room_id, target):
        raise RoomError(f"{target} isn't in this room.")
    con = _con(db)
    try:
        con.execute("UPDATE group_room_members SET role='admin' WHERE room_id=? AND username=?", (room_id, actor))
        con.execute("UPDATE group_room_members SET role='owner' WHERE room_id=? AND username=?", (room_id, target))
        con.execute("UPDATE group_rooms SET owner=? WHERE room_id=?", (target, room_id))
        con.commit()
    finally:
        con.close()


def kick(db, room_id, actor, target, actor_is_server_admin=False):
    if not _outranks(db, room_id, actor, target, "moderate_members", actor_is_server_admin):
        raise RoomError(f"{target} isn't in this room.")
    con = _con(db)
    try:
        con.execute("DELETE FROM group_room_members WHERE room_id=? AND username=?", (room_id, target))
        con.commit()
    finally:
        con.close()


def mute(db, room_id, actor, target, minutes, actor_is_server_admin=False):
    """Mute for this many minutes (0 unmutes). Muted people can read but not post."""
    if not _outranks(db, room_id, actor, target, "moderate_members", actor_is_server_admin):
        raise RoomError(f"{target} isn't in this room.")
    minutes = max(0, min(int(minutes or 0), 60 * 24 * 365))
    until = time.time() + minutes * 60 if minutes else 0
    con = _con(db)
    try:
        con.execute("UPDATE group_room_members SET muted_until=? WHERE room_id=? AND username=?", (until, room_id, target))
        con.commit()
    finally:
        con.close()
    return until


def ban(db, room_id, actor, target, reason="", actor_is_server_admin=False):
    target = str(target or "").strip()
    if not target:
        raise RoomError("Say who to ban.")
    _outranks(db, room_id, actor, target, "moderate_members", actor_is_server_admin)
    con = _con(db)
    try:
        con.execute("DELETE FROM group_room_members WHERE room_id=? AND username=?", (room_id, target))
        con.execute("INSERT OR REPLACE INTO group_room_bans (room_id, username, banned_by, reason, banned_at) VALUES (?,?,?,?,?)",
                    (room_id, target, actor, str(reason or "")[:300], time.time()))
        con.commit()
    finally:
        con.close()


def unban(db, room_id, actor, target, actor_is_server_admin=False):
    if not actor_is_server_admin:
        _require(db, room_id, actor, "moderate_members", "Your room role can't do that.")
    con = _con(db)
    try:
        n = con.execute("DELETE FROM group_room_bans WHERE room_id=? AND username=?", (room_id, target)).rowcount
        con.commit()
    finally:
        con.close()
    if not n:
        raise RoomError(f"{target} isn't banned here.")


def mentions_in(db, room_id, body):
    """Room members named with @username in the text (matched ignoring case, using their stored spelling)."""
    wanted = {m.lower() for m in MENTION_RE.findall(str(body or ""))}
    if not wanted:
        return []
    return [m["username"] for m in list_members(db, room_id) if m["username"].lower() in wanted]


def _message_dict(row):
    d = dict(row)
    d["deleted"] = bool(d.get("deleted"))
    d["mentions"] = json.loads(d.pop("mentions_json", None) or "[]")
    path = d.pop("voice_path", None)
    duration = d.pop("voice_duration", None)
    if d.get("kind") == "voice":
        d["voice"] = {"duration": duration or 0, "stored": bool(path)}
    if d["deleted"]:
        d["body"] = ""
        d["transcript"] = None
    elif not d.get("transcript"):
        d.pop("transcript", None)
    return d


def add_message(db, room_id, sender, body, kind="text", filename="", client_id="", voice_path=None, voice_duration=None):
    action = {"file": "send_files", "voice": "send_voice"}.get(kind, "send_messages")
    _require(db, room_id, sender, action, "Your room role can't " + action.replace("_", " ") + " here.")
    con = _con(db)
    try:
        muted = con.execute("SELECT muted_until FROM group_room_members WHERE room_id=? AND username=?", (room_id, sender)).fetchone()
    finally:
        con.close()
    if muted and muted[0] > time.time():
        raise RoomError("You're muted in this room for now, so you can read but not post.")
    body = str(body or "")
    if kind == "text" and (not body.strip() or len(body) > MAX_MESSAGE):
        raise RoomError("Messages must be 1 to %d characters." % MAX_MESSAGE)
    mentions = mentions_in(db, room_id, body)
    msg = {"message_id": uuid.uuid4().hex, "room_id": room_id, "sender": sender, "body": body, "kind": kind,
           "filename": str(filename or "")[:255], "sent_at": time.time(), "client_id": str(client_id or "")[:64]}
    con = _con(db)
    try:
        con.execute("INSERT INTO group_room_messages (message_id, room_id, sender, body, kind, filename, sent_at, voice_path, voice_duration, "
                    "mentions_json, client_id) VALUES (?,?,?,?,?,?,?,?,?,?,?)",
                    (msg["message_id"], room_id, sender, body, kind, msg["filename"], msg["sent_at"], voice_path, voice_duration,
                     json.dumps(mentions), msg["client_id"]))
        # Posting counts as having read everything up to your own message.
        con.execute("UPDATE group_room_members SET last_read_at=MAX(last_read_at, ?) WHERE room_id=? AND username=?",
                    (msg["sent_at"], room_id, sender))
        con.commit()
        row = con.execute("SELECT * FROM group_room_messages WHERE message_id=?", (msg["message_id"],)).fetchone()
    finally:
        con.close()
    return _message_dict(row)


def get_message(db, room_id, message_id):
    con = _con(db)
    try:
        row = con.execute("SELECT * FROM group_room_messages WHERE room_id=? AND message_id=?", (room_id, str(message_id or ""))).fetchone()
    finally:
        con.close()
    if not row:
        raise RoomError("That message wasn't found.")
    return row


def edit_message(db, room_id, actor, message_id, body):
    row = get_message(db, room_id, message_id)
    if row["deleted"]:
        raise RoomError("That message was deleted.")
    if row["sender"].lower() != str(actor).lower() and not can(db, room_id, actor, "moderate_messages"):
        raise RoomError("Only the sender or a room moderator can edit that message.")
    body = str(body or "")
    if not body.strip() or len(body) > MAX_MESSAGE:
        raise RoomError("Messages must be 1 to %d characters." % MAX_MESSAGE)
    now = time.time()
    con = _con(db)
    try:
        con.execute("UPDATE group_room_messages SET body=?, edited_at=?, edited_by=?, mentions_json=? WHERE message_id=?",
                    (body, now, actor, json.dumps(mentions_in(db, room_id, body)), message_id))
        con.commit()
        return _message_dict(con.execute("SELECT * FROM group_room_messages WHERE message_id=?", (message_id,)).fetchone())
    finally:
        con.close()


def delete_message(db, room_id, actor, message_id):
    """Returns the voice file path to remove, if any."""
    row = get_message(db, room_id, message_id)
    if row["sender"].lower() != str(actor).lower() and not can(db, room_id, actor, "moderate_messages"):
        raise RoomError("Only the sender or a room moderator can delete that message.")
    con = _con(db)
    try:
        con.execute("UPDATE group_room_messages SET deleted=1, body='', voice_path=NULL, transcript=NULL, edited_at=?, edited_by=? WHERE message_id=?",
                    (time.time(), actor, message_id))
        con.commit()
    finally:
        con.close()
    return row["voice_path"]


def voice_path(db, room_id, username, message_id):
    _require(db, room_id, username, "view", "Join the room to hear its voice messages.")
    row = get_message(db, room_id, message_id)
    return None if row["deleted"] else row["voice_path"]


def mark_read(db, room_id, username, message_id):
    """Move your read point up to this message (never backwards). Returns the new read time, or None if unchanged."""
    row = get_message(db, room_id, message_id)
    con = _con(db)
    try:
        me = con.execute("SELECT last_read_at FROM group_room_members WHERE room_id=? AND username=?", (room_id, username)).fetchone()
        if not me:
            raise RoomError("You're not in this room.")
        if row["sent_at"] <= me[0]:
            return None
        con.execute("UPDATE group_room_members SET last_read_at=? WHERE room_id=? AND username=?", (row["sent_at"], room_id, username))
        con.commit()
    finally:
        con.close()
    return row["sent_at"]


def history(db, room_id, username, limit=100, before=None):
    """Messages oldest first, up to `limit`, optionally only older than `before` (a sent_at time). Returns (messages, has_more)."""
    _require(db, room_id, username, "view", "Join the room to read its messages.")
    limit = max(1, min(int(limit or 100), 500))
    con = _con(db)
    try:
        if before:
            rows = con.execute("SELECT * FROM group_room_messages WHERE room_id=? AND sent_at<? ORDER BY sent_at DESC LIMIT ?",
                               (room_id, float(before), limit + 1)).fetchall()
        else:
            rows = con.execute("SELECT * FROM group_room_messages WHERE room_id=? ORDER BY sent_at DESC LIMIT ?",
                               (room_id, limit + 1)).fetchall()
    finally:
        con.close()
    has_more = len(rows) > limit
    return [_message_dict(r) for r in reversed(rows[:limit])], has_more


def read_by(db, room_id, message_id):
    """Who has read a message (not counting its sender), and how many could have."""
    row = get_message(db, room_id, message_id)
    members = [m for m in list_members(db, room_id) if m["username"].lower() != row["sender"].lower()]
    readers = [m["username"] for m in members if m["last_read_at"] >= row["sent_at"]]
    return readers, len(members)


def remove_links(db, room_id, actor, items, find_links):
    """Take links out of room messages: [{"message_id", "raw": [...] or omitted}]. Sender or moderator only.
    Returns (changed message dicts, refused ids)."""
    changed, denied = [], []
    for item in list(items or [])[:500]:
        mid = str((item or {}).get("message_id") or "")
        try:
            row = get_message(db, room_id, mid)
        except RoomError:
            denied.append(mid)
            continue
        if row["deleted"] or (row["sender"].lower() != str(actor).lower() and not can(db, room_id, actor, "moderate_messages")):
            denied.append(mid)
            continue
        wanted = item.get("raw")
        if isinstance(wanted, str):
            wanted = [wanted]
        targets = [l["raw"] for l in find_links(row["body"]) if wanted is None or l["raw"] in wanted]
        if not targets:
            continue
        body = row["body"]
        for raw in sorted(targets, key=len, reverse=True):
            body = body.replace(raw, "[link removed]")
        msg = edit_message(db, room_id, actor, mid, body)
        msg["links_removed"] = len(targets)
        changed.append(msg)
    return changed, denied


def remove_user_everywhere(db, username):
    """Account deletion: rooms they own are deleted, their messages and memberships removed."""
    con = _con(db)
    try:
        for (room_id,) in con.execute("SELECT room_id FROM group_rooms WHERE owner=? COLLATE NOCASE", (username,)).fetchall():
            con.execute("DELETE FROM group_rooms WHERE room_id=?", (room_id,))
        con.execute("DELETE FROM group_room_messages WHERE sender=? COLLATE NOCASE", (username,))
        con.execute("DELETE FROM group_room_members WHERE username=?", (username,))
        con.execute("DELETE FROM group_room_bans WHERE username=?", (username,))
        con.commit()
    finally:
        con.close()
