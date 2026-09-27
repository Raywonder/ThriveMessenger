import wx, socket, json, threading, datetime, wx.adv, configparser, ssl, sys, os, base64, uuid, subprocess, tempfile, re, random, shutil, time, secrets, queue, array
import urllib.request, urllib.parse
import traceback, platform
import hashlib
import keyring
try:
    import sounddevice
except Exception:
    sounddevice = None
try:
    import wx.media as wxmedia
except Exception:
    wxmedia = None
import unicodedata, wave, io
try:
    import wx.html2 as wxhtml2
except Exception:
    wxhtml2 = None

VERSION_TAG = "v2026-alpha15.12"
URL_REGEX = re.compile(r'((?:https?|ipfs|ipns|web3)://[^\s<>()]+)', re.IGNORECASE)
BARE_DOMAIN_REGEX = re.compile(
    r'\b((?:[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?\.)+[a-z]{2,63}(?::\d{1,5})?(?:/[^\s<>()]*)?)\b',
    re.IGNORECASE,
)
KEYRING_SERVICE = "ThriveMessenger"
PASSKEY_KEYRING_SERVICE = "ThriveMessengerPasskey"
DEFAULT_SOUNDPACK_BASE_URL = "https://im.tappedin.fm/thrive/sounds"
DEFAULT_LOG_SUBMIT_URL = "https://im.tappedin.fm/thrive/logs"
TYPING_IDLE_STOP_MS = 6000
LOGIN_RESPONSE_TIMEOUT = 20
IDLE_KEEPALIVE_SECONDS = 15 * 60
KEEPALIVE_CHECK_INTERVAL = 30
KEEPALIVE_RESPONSE_TIMEOUT = 10
DEMO_VIDEOS = {
    "onboarding": {
        "filename": "promo-onboarding.mp4",
        "title": "Onboarding Demo",
        "description": "Shows the first-run experience: launching the app, signing in, and landing on the contact list."
    },
    "chat_files": {
        "filename": "promo-chat-files.mp4",
        "title": "Chat and File Demo",
        "description": "Shows selecting a contact, sending a message, and sending files with transfer confirmation."
    },
    "admin_tools": {
        "filename": "promo-admin-tools.mp4",
        "title": "Admin Tools Demo",
        "description": "Shows opening Server Manager, reviewing multiple servers, and updating primary server settings."
    },
}

# Legacy-safe fallback when a server does not implement feature capability APIs.
# Core chat/login remains available; advanced controls stay disabled by default.
LEGACY_SAFE_FEATURE_CAPS = {
    "bots": {"enabled": False, "ui_visible": False, "scope": "all", "can_use": False},
    "bot_mesh": {"enabled": False, "ui_visible": False, "scope": "all", "can_use": False},
    "bot_moderation": {"enabled": False, "ui_visible": False, "scope": "admin", "can_use": False},
    "bot_rules": {"enabled": False, "ui_visible": False, "scope": "admin", "can_use": False},
    "group_chat": {"enabled": False, "ui_visible": False, "scope": "all", "can_use": False},
    "group_call": {"enabled": False, "ui_visible": False, "scope": "all", "can_use": False},
    "group_policy": {"enabled": False, "ui_visible": False, "scope": "admin", "can_use": False},
    "admin_console": {"enabled": False, "ui_visible": False, "scope": "admin", "can_use": False},
    "voice_call": {"enabled": False, "ui_visible": False, "scope": "all", "can_use": False},
    "server_manager": {"enabled": True, "ui_visible": True, "scope": "all", "can_use": True},
}
_KEYRING_WRITE_CACHE = {}
_SOUND_DOWNLOAD_NOTICE_CACHE = set()
_SOUND_DOWNLOAD_FAILURE_CACHE = set()
UPDATE_CONTEXT = {}

def scale_pcm16(data, gain):
    """Scale little-endian signed 16-bit PCM without deprecated audioop."""
    if gain == 1.0:
        return data
    samples = array.array("h")
    samples.frombytes(data)
    for index, sample in enumerate(samples):
        samples[index] = max(-32768, min(32767, int(sample * gain)))
    return samples.tobytes()

def _use_keyring_runtime():
    # Credentials always live in the OS keychain (Windows Credential Manager, macOS Keychain).
    # Keychain calls run behind a timeout (_kr_call) so a slow or locked keychain can't freeze the app.
    return not _KEYRING_UNAVAILABLE[0]

_KEYRING_UNAVAILABLE = [False]

def _kr_call(fn, *args, timeout=8.0):
    """Run one keyring call with a timeout. A hang marks the keychain unavailable for this session."""
    if _KEYRING_UNAVAILABLE[0]:
        raise RuntimeError("keychain unavailable")
    result = {}
    def run():
        try:
            result["value"] = fn(*args)
        except Exception as e:
            result["error"] = e
    t = threading.Thread(target=run, daemon=True)
    t.start()
    t.join(timeout)
    if t.is_alive():
        _KEYRING_UNAVAILABLE[0] = True
        raise TimeoutError("keychain did not respond")
    if "error" in result:
        raise result["error"]
    return result.get("value")
_WinNotification = None
_plyer_notification = None
if sys.platform == 'win32':
    try:
        from winotify import Notification as _WinNotification
    except Exception:
        _WinNotification = None
try:
    from plyer import notification as _plyer_notification
except Exception:
    _plyer_notification = None

def show_notification(title, message, timeout=5):
    try:
        if sys.platform == 'win32' and _WinNotification is not None:
            toast = _WinNotification(app_id="Thrive Messenger", title=title, msg=message, duration="short")
            toast.show()
        elif _plyer_notification is not None:
            _plyer_notification.notify(title, message, timeout=timeout)
    except Exception as e:
        print(f"Error showing notification: {e}")

def apply_voiceover_hint(control, hint):
    if not control or not hint:
        return
    try:
        control.SetToolTip(str(hint))
    except Exception:
        pass

class F3SearchTextCtrl(wx.TextCtrl):
    """A search field reached explicitly with F3 instead of normal Tab order."""
    def AcceptsFocusFromKeyboard(self):
        return False
    try:
        control.SetHelpText(str(hint))
    except Exception:
        pass
    try:
        label = ""
        if hasattr(control, "GetLabel"):
            label = str(control.GetLabel() or "").strip()
        if label and hasattr(control, "SetName"):
            control.SetName(label)
    except Exception:
        pass

# --- Dark Mode for MSW ---
try:
    import ctypes
    from ctypes import wintypes
    import winreg

    class WxMswDarkMode:
        _instance = None
        def __new__(cls):
            if cls._instance is None:
                cls._instance = super(WxMswDarkMode, cls).__new__(cls)
                try:
                    cls.dwmapi = ctypes.WinDLL("dwmapi")
                    cls.DWMWA_USE_IMMERSIVE_DARK_MODE = 20
                except (AttributeError, OSError):
                    cls.dwmapi = None
            return cls._instance

        def enable(self, window: wx.Window, enable: bool = True):
            if not self.dwmapi: return False
            try:
                hwnd = window.GetHandle()
                value = wintypes.BOOL(enable)
                hr = self.dwmapi.DwmSetWindowAttribute(hwnd, self.DWMWA_USE_IMMERSIVE_DARK_MODE, ctypes.byref(value), ctypes.sizeof(value))
                if hr != 0:
                    self.DWMWA_USE_IMMERSIVE_DARK_MODE = 19
                    hr = self.dwmapi.DwmSetWindowAttribute(hwnd, self.DWMWA_USE_IMMERSIVE_DARK_MODE, ctypes.byref(value), ctypes.sizeof(value))
                return hr == 0
            except Exception: return False

    def is_windows_dark_mode():
        try:
            key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, r'Software\Microsoft\Windows\CurrentVersion\Themes\Personalize')
            value, _ = winreg.QueryValueEx(key, 'AppsUseLightTheme')
            winreg.CloseKey(key)
            return value == 0
        except (FileNotFoundError, OSError): return False

except (ImportError, ModuleNotFoundError):
    class WxMswDarkMode:
        def enable(self, window: wx.Window, enable: bool = True): return False
    def is_windows_dark_mode(): return False
# --- End of Dark Mode Logic ---

if sys.platform == 'win32':
    try: ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID('Thrive.Thrive_Messenger')
    except Exception: pass

def load_server_config():
    # Now reading connection details from client.conf instead of srv.conf
    config = load_client_config()
    return {
        'host': config.get('server', 'host', fallback='msg.thecubed.cc'),
        'port': config.getint('server', 'port', fallback=2005),
        'cafile': config.get('server', 'cafile', fallback=None),
    }

def load_server_entries_from_client_conf():
    config = load_client_config()
    entries = []
    if config.has_section('server'):
        entries.append({
            'name': config.get('server', 'name', fallback='Default Server'),
            'host': config.get('server', 'host', fallback='msg.thecubed.cc'),
            'port': config.getint('server', 'port', fallback=2005),
            'cafile': config.get('server', 'cafile', fallback=''),
            'primary': config.getboolean('server', 'primary', fallback=False),
        })
    for section in config.sections():
        if section == 'server':
            continue
        if section.startswith('server ') or section.startswith('server:'):
            entries.append({
                'name': config.get(section, 'name', fallback=section.replace('server', '', 1).strip(' :') or 'Server'),
                'host': config.get(section, 'host', fallback='msg.thecubed.cc'),
                'port': config.getint(section, 'port', fallback=2005),
                'cafile': config.get(section, 'cafile', fallback=''),
                'primary': config.getboolean(section, 'primary', fallback=False),
            })
    return dedupe_server_entries(entries)

def normalize_server_entry(entry):
    host = str(entry.get('host', '')).strip()
    name = str(entry.get('name', '')).strip() or host or 'Server'
    cafile = str(entry.get('cafile', '')).strip()
    try:
        port = int(entry.get('port', 2005))
    except Exception:
        port = 2005
    if port <= 0:
        port = 2005
    primary = bool(entry.get('primary', False))
    return {'name': name, 'host': host, 'port': port, 'cafile': cafile, 'primary': primary}

def dedupe_server_entries(entries):
    out = []
    seen = set()
    for entry in entries:
        normalized = normalize_server_entry(entry)
        if not normalized['host']:
            continue
        key = (normalized['host'].lower(), normalized['port'])
        if key in seen:
            continue
        seen.add(key)
        out.append(normalized)
    if out and not any(e.get('primary') for e in out):
        out[0]['primary'] = True
    return out

def get_config_dir():
    if sys.platform == 'win32':
        base = os.environ.get('APPDATA', os.path.expanduser('~'))
    elif sys.platform == 'darwin':
        base = os.path.join(os.path.expanduser('~'), 'Library', 'Application Support')
    else:
        base = os.environ.get('XDG_CONFIG_HOME', os.path.join(os.path.expanduser('~'), '.config'))
    config_dir = os.path.join(base, 'ThriveMessenger')
    os.makedirs(config_dir, exist_ok=True)
    return config_dir

def get_settings_path():
    return os.path.join(get_config_dir(), 'user_settings.json')

def _resolve_server_for_credentials(settings):
    entries = dedupe_server_entries(settings.get('server_entries', []))
    if not entries:
        entries = [normalize_server_entry(load_server_config())]
    preferred_name = settings.get('last_server_name') or settings.get('primary_server_name', '')
    for entry in entries:
        if entry.get('name') == preferred_name:
            return normalize_server_entry(entry)
    return normalize_server_entry(entries[0])

def _keyring_account_for(username, settings):
    server = _resolve_server_for_credentials(settings)
    return f"{username}@{server.get('host', '').lower()}:{server.get('port', 2005)}"

def _load_password_from_keyring(username, settings):
    if not username:
        return ''
    account = _keyring_account_for(username, settings)
    # Server-aware key first, then legacy account for backward compatibility.
    candidates = [(KEYRING_SERVICE, account), (KEYRING_SERVICE, username)]
    for service, key_account in candidates:
        try:
            value = _kr_call(keyring.get_password, service, key_account)
            if value:
                return value
        except Exception as e:
            print(f"Keyring error (load): {type(e).__name__}")
            return ''
    return ''

def _save_password_to_keyring(username, password, settings):
    if not username or not password:
        return False
    try:
        _kr_call(keyring.set_password, KEYRING_SERVICE, _keyring_account_for(username, settings), password)
        return True
    except Exception as e:
        print(f"Keyring error (save): {type(e).__name__}")
        log_event("warn", "keychain_save_failed", {"error": type(e).__name__})
        return False

def _delete_password_from_keyring(username, settings):
    if not username:
        return
    account = _keyring_account_for(username, settings)
    for service, key_account in ((KEYRING_SERVICE, account), (KEYRING_SERVICE, username)):
        try:
            if _kr_call(keyring.get_password, service, key_account):
                _kr_call(keyring.delete_password, service, key_account)
        except Exception:
            pass

def _encode_password_fallback(password):
    if not password:
        return ''
    try:
        return base64.b64encode(password.encode('utf-8')).decode('ascii')
    except Exception:
        return ''

def _decode_password_fallback(value):
    if not value:
        return ''
    try:
        return base64.b64decode(value.encode('ascii')).decode('utf-8')
    except Exception:
        return ''

def _passkey_account_for(username, settings=None, server_entry=None):
    if not username:
        return ""
    if server_entry is not None:
        server = normalize_server_entry(server_entry)
    else:
        server = _resolve_server_for_credentials(settings or {})
    return f"{username}@{server.get('host', '').lower()}:{server.get('port', 2005)}"

def _load_passkey_from_keyring(username, settings=None, server_entry=None):
    account = _passkey_account_for(username, settings=settings, server_entry=server_entry)
    if not account:
        return ""
    try:
        return _kr_call(keyring.get_password, PASSKEY_KEYRING_SERVICE, account) or ""
    except Exception as e:
        print(f"Keyring error (passkey load): {type(e).__name__}")
        return ""

def _save_passkey_to_keyring(username, passkey_token, settings=None, server_entry=None):
    account = _passkey_account_for(username, settings=settings, server_entry=server_entry)
    if not account:
        return False
    token_value = str(passkey_token or "")
    if not token_value:
        return False
    try:
        _kr_call(keyring.set_password, PASSKEY_KEYRING_SERVICE, account, token_value)
        return True
    except Exception as e:
        print(f"Keyring error (passkey save): {type(e).__name__}")
        return False

def _delete_passkey_from_keyring(username, settings=None, server_entry=None):
    account = _passkey_account_for(username, settings=settings, server_entry=server_entry)
    if not account:
        return
    cfg = settings if isinstance(settings, dict) else None
    if cfg is not None and isinstance(cfg.get("passkey_tokens"), dict):
        cfg["passkey_tokens"].pop(account, None)
    try:
        if _kr_call(keyring.get_password, PASSKEY_KEYRING_SERVICE, account):
            _kr_call(keyring.delete_password, PASSKEY_KEYRING_SERVICE, account)
    except Exception:
        pass

def _migrate_settings():
    old_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'user_settings.json')
    new_path = get_settings_path()
    if os.path.exists(old_path) and not os.path.exists(new_path):
        try:
            import shutil
            shutil.move(old_path, new_path)
            print(f"Migrated user_settings.json to {new_path}")
        except Exception as e:
            print(f"Could not migrate settings: {e}")

_migrate_settings()

def load_user_config():
    """
    Loads user preferences from user_settings.json and password from OS Keyring.
    """
    file_entries = load_server_entries_from_client_conf()
    fallback_entry = normalize_server_entry(load_server_config())
    if not file_entries:
        file_entries = [fallback_entry]

    settings = {
        'remember': False,
        'autologin': False,
        'autologin_mode': 'password',
        'username': '',
        'password': '',
        'soundpack': 'default',
        'default_soundpack': 'default',
        'soundpack_base_url': DEFAULT_SOUNDPACK_BASE_URL,
        'log_submit_url': DEFAULT_LOG_SUBMIT_URL,
        'sound_volume': 80,
        'call_soundpack': 'flexpbx',
        'auto_play_voice_messages': False,
        'call_input_volume': 80,
        'call_output_volume': 80,
        'show_main_action_buttons': True,
        'chat_logging': {},
        'server_entries': file_entries,
        'last_server_name': file_entries[0]['name'] if file_entries else 'Default Server',
        'primary_server_name': next((e['name'] for e in file_entries if e.get('primary')), file_entries[0]['name'] if file_entries else 'Default Server'),
        'auto_open_received_files': True,
        'read_messages_aloud': False,
        'interrupt_speech': True,
        'typing_indicators': True,
        'announce_typing': True,
        'prefer_contact_display_names': False,
        'contact_display_names': {},
        'enter_key_action': 'none',
        'escape_main_action': 'none',
        'double_escape_to_close_chat': True,
        'chat_tabs': True,
        'keep_contact_list_open': True,
        'save_chat_history_default': False,
        'message_edit_window_seconds': 300,
        'message_undo_window_seconds': 15,
        'delete_messages_for_everyone': True,
        'delete_attached_files_with_message': False,
        'allow_cross_server_directory_message': True,
        'directory_dm_defaults': {},
        'incoming_popup_on_message': False,
        'incoming_alert_on_message': False,
        'incoming_message_behavior': 'silent_count',
        'notify_on_other_device_login': False,
        'message_timestamp_mode': 'start',
        'saved_history_date_order': 'mdy',
        'bot_mesh_agent_enabled': False,
        'bot_mesh_agent_moderation': True,
        'bot_mesh_agent_backend': 'ollama',
        'bot_mesh_agent_auth_type': 'codex',
        'bot_mesh_agent_delegate_to': 'helper-bot',
        'bot_mesh_agent_notify_user': '',
        'bot_mesh_agent_user': '',
        'bot_mesh_agent_host_label': platform.node() or 'local',
        'passkey_ids': {},
        'passkey_tokens': {},
        'device_id': str(uuid.uuid4()),
        'device_name': platform.node() or 'This device',
        'session_duration': 'month',
    }

    # 1. Load non-sensitive preferences from JSON
    settings_path = get_settings_path()
    if os.path.exists(settings_path):
        try:
            with open(settings_path, 'r') as f:
                data = json.load(f)
                settings.update(data)
        except (json.JSONDecodeError, OSError):
            print("Could not load user_settings.json, using defaults.")

    # 2. Normalize and merge server entries from both user settings and client.conf
    user_entries = settings.get('server_entries', []) if isinstance(settings.get('server_entries', []), list) else []
    merged_entries = dedupe_server_entries(file_entries + user_entries)
    if not merged_entries:
        merged_entries = [fallback_entry]
    settings['server_entries'] = merged_entries
    if settings.get('primary_server_name') not in [e['name'] for e in merged_entries]:
        primary = next((e['name'] for e in merged_entries if e.get('primary')), merged_entries[0]['name'])
        settings['primary_server_name'] = primary
    if settings.get('last_server_name') not in [e['name'] for e in merged_entries]:
        settings['last_server_name'] = settings.get('primary_server_name') or merged_entries[0]['name']
    enter_action = str(settings.get('enter_key_action', 'none') or 'none')
    if enter_action not in ('send', 'place_call', 'none'):
        settings['enter_key_action'] = 'none'
    try:
        settings['message_edit_window_seconds'] = max(0, int(settings.get('message_edit_window_seconds', 300)))
    except Exception:
        settings['message_edit_window_seconds'] = 300
    try:
        settings['message_undo_window_seconds'] = max(0, int(settings.get('message_undo_window_seconds', 15)))
    except Exception:
        settings['message_undo_window_seconds'] = 15
    settings['allow_cross_server_directory_message'] = bool(settings.get('allow_cross_server_directory_message', True))
    settings['double_escape_to_close_chat'] = bool(settings.get('double_escape_to_close_chat', True))
    settings['delete_messages_for_everyone'] = bool(settings.get('delete_messages_for_everyone', True))
    settings['chat_tabs'] = bool(settings.get('chat_tabs', True))
    settings['keep_contact_list_open'] = bool(settings.get('keep_contact_list_open', True))
    settings['delete_attached_files_with_message'] = bool(settings.get('delete_attached_files_with_message', False))
    settings['interrupt_speech'] = bool(settings.get('interrupt_speech', True))
    settings['prefer_contact_display_names'] = bool(settings.get('prefer_contact_display_names', False))
    if not isinstance(settings.get('contact_display_names', {}), dict):
        settings['contact_display_names'] = {}
    if not isinstance(settings.get('directory_dm_defaults', {}), dict):
        settings['directory_dm_defaults'] = {}
    settings['incoming_popup_on_message'] = bool(settings.get('incoming_popup_on_message', False))
    settings['incoming_alert_on_message'] = bool(settings.get('incoming_alert_on_message', False))
    settings['notify_on_other_device_login'] = bool(settings.get('notify_on_other_device_login', False))
    settings['bot_mesh_agent_enabled'] = bool(settings.get('bot_mesh_agent_enabled', False))
    settings['bot_mesh_agent_moderation'] = bool(settings.get('bot_mesh_agent_moderation', True))
    settings['bot_mesh_agent_backend'] = str(settings.get('bot_mesh_agent_backend', 'ollama') or 'ollama').strip().lower()
    if settings['bot_mesh_agent_backend'] not in ('ollama', 'command', 'auto', 'echo'):
        settings['bot_mesh_agent_backend'] = 'ollama'
    settings['bot_mesh_agent_auth_type'] = str(settings.get('bot_mesh_agent_auth_type', 'codex') or 'codex').strip().lower()
    settings['bot_mesh_agent_delegate_to'] = str(settings.get('bot_mesh_agent_delegate_to', 'helper-bot') or 'helper-bot').strip()
    settings['bot_mesh_agent_notify_user'] = str(settings.get('bot_mesh_agent_notify_user', '') or '').strip()
    settings['bot_mesh_agent_user'] = str(settings.get('bot_mesh_agent_user', '') or '').strip()
    settings['bot_mesh_agent_host_label'] = str(settings.get('bot_mesh_agent_host_label', platform.node() or 'local') or (platform.node() or 'local')).strip()
    incoming_behavior = str(settings.get('incoming_message_behavior', '') or '').strip().lower()
    valid_incoming_behaviors = ('popup', 'notify', 'do_nothing', 'play_sound', 'silent_count')
    if incoming_behavior not in valid_incoming_behaviors:
        if settings['incoming_popup_on_message']:
            incoming_behavior = 'popup'
        elif settings['incoming_alert_on_message']:
            incoming_behavior = 'notify'
        else:
            incoming_behavior = 'silent_count'
    settings['incoming_message_behavior'] = incoming_behavior
    settings['incoming_popup_on_message'] = (incoming_behavior == 'popup')
    settings['incoming_alert_on_message'] = incoming_behavior in ('notify', 'play_sound')
    timestamp_mode = str(settings.get('message_timestamp_mode', 'start') or 'start').strip().lower()
    if timestamp_mode not in ('start', 'end', 'off'):
        timestamp_mode = 'start'
    settings['message_timestamp_mode'] = timestamp_mode
    date_order = str(settings.get('saved_history_date_order', 'mdy') or 'mdy').strip().lower()
    if date_order not in ('mdy', 'dmy', 'ymd', 'ydm'):
        date_order = 'mdy'
    settings['saved_history_date_order'] = date_order
    if str(settings.get('autologin_mode', 'password') or 'password') not in ('password', 'passkey'):
        settings['autologin_mode'] = 'password'
    if not isinstance(settings.get('passkey_ids', {}), dict):
        settings['passkey_ids'] = {}
    if not isinstance(settings.get('passkey_tokens', {}), dict):
        settings['passkey_tokens'] = {}
    settings['device_id'] = str(settings.get('device_id') or uuid.uuid4())
    settings['device_name'] = str(settings.get('device_name') or platform.node() or 'This device')[:200]
    if settings.get('session_duration') not in ('hour', 'day', 'week', 'month', 'year', 'forever'):
        settings['session_duration'] = 'month'

    # 3. Load password from Keyring if "Remember me" is active
    if settings.get('username') and settings.get('remember'):
        stored_pass = _load_password_from_keyring(settings['username'], settings)
        if stored_pass:
            settings['password'] = stored_pass
        elif settings.get('password_fallback'):
            settings['password'] = _decode_password_fallback(settings.get('password_fallback', ''))
    _migrate_file_secrets_to_keychain(settings)

    return settings

def _migrate_file_secrets_to_keychain(settings):
    """Older builds kept the saved password (and on macOS passkey tokens) base64-encoded in user_settings.json.
    Move them into the OS keychain, then remove them from the file. If the keychain can't take them, leave them."""
    changed = False
    fallback = settings.get('password_fallback')
    if fallback:
        username = settings.get('username', '')
        password = _decode_password_fallback(fallback)
        if username and password and settings.get('remember'):
            if _save_password_to_keyring(username, password, settings):
                settings.pop('password_fallback', None); changed = True
        else:
            settings.pop('password_fallback', None); changed = True
    tokens = settings.get('passkey_tokens')
    if isinstance(tokens, dict) and tokens:
        for account, encoded in list(tokens.items()):
            token = _decode_password_fallback(encoded)
            try:
                if token:
                    _kr_call(keyring.set_password, PASSKEY_KEYRING_SERVICE, account, token)
                tokens.pop(account, None); changed = True
            except Exception as e:
                print(f"Keyring error (passkey migrate): {type(e).__name__}")
    if changed:
        _write_settings_file(settings)
        log_event("info", "credentials_moved_to_keychain")
    return changed

def _write_settings_file(settings):
    data = dict(settings)
    data.pop('password', None)
    if not data.get('password_fallback'):
        data.pop('password_fallback', None)
    try:
        with open(get_settings_path(), 'w') as f:
            json.dump(data, f, indent=4)
    except Exception as e:
        print(f"Error saving settings file: {e}")

def save_user_config(settings):
    """
    Saves user preferences to user_settings.json and password to OS Keyring.
    """
    username = settings.get('username', '')
    password = settings.get('password', '')
    remember = settings.get('remember', False)
    
    # 1. The saved password goes only to the OS keychain; the settings file never holds it.
    settings.pop('password_fallback', None)
    if isinstance(settings.get('passkey_tokens'), dict):
        settings['passkey_tokens'] = {}
    if username and remember and password:
        cache_key = (KEYRING_SERVICE, _keyring_account_for(username, settings))
        if _KEYRING_WRITE_CACHE.get(cache_key) != password and _save_password_to_keyring(username, password, settings):
            _KEYRING_WRITE_CACHE[cache_key] = password
    elif username and not remember:
        _delete_password_from_keyring(username, settings)
        _KEYRING_WRITE_CACHE.pop((KEYRING_SERVICE, _keyring_account_for(username, settings)), None)
    # 2. Non-sensitive preferences to JSON.
    _write_settings_file(settings)

def _device_login_fields(settings):
    return {
        "device_id": str(settings.get("device_id") or uuid.uuid4()),
        "device_name": str(settings.get("device_name") or platform.node() or "This device")[:200],
        "platform": platform.system() or sys.platform,
        "client_version": VERSION_TAG,
        "session_duration": str(settings.get("session_duration") or "month"),
    }

_IPC_PORT = 48951
_LOG_FILE_NAME = "thrive_client.log"

def get_logs_dir():
    p = os.path.join(os.path.dirname(get_settings_path()), "logs")
    os.makedirs(p, exist_ok=True)
    return p

def get_log_path():
    return os.path.join(get_logs_dir(), _LOG_FILE_NAME)

def _trim_log_file(path, max_bytes=2 * 1024 * 1024):
    try:
        if os.path.getsize(path) <= max_bytes:
            return
        with open(path, "rb") as f:
            f.seek(-max_bytes, os.SEEK_END)
            tail = f.read()
        with open(path, "wb") as f:
            f.write(tail)
    except Exception:
        pass

def log_event(level, message, extra=None):
    try:
        payload = {
            "ts": datetime.datetime.utcnow().isoformat() + "Z",
            "level": str(level).lower(),
            "message": str(message),
        }
        if extra is not None:
            payload["extra"] = extra
        with open(get_log_path(), "a", encoding="utf-8") as f:
            f.write(json.dumps(payload, ensure_ascii=True) + "\n")
        _trim_log_file(get_log_path())
    except Exception:
        pass

def _read_log_tail(path, max_bytes=256 * 1024):
    try:
        size = os.path.getsize(path)
        with open(path, "rb") as f:
            if size > max_bytes:
                f.seek(-max_bytes, os.SEEK_END)
            data = f.read()
        return data.decode("utf-8", errors="replace")
    except Exception:
        return ""

def submit_logs_payload(config_dict, reason="manual"):
    base_url = str(config_dict.get("log_submit_url", DEFAULT_LOG_SUBMIT_URL) or "").strip().rstrip("/")
    if not base_url:
        return False, "Log submit URL is not configured."
    payload = {
        "app": "Thrive Messenger",
        "version": VERSION_TAG,
        "reason": reason,
        "timestamp": datetime.datetime.utcnow().isoformat() + "Z",
        "username": str(config_dict.get("username", "") or ""),
        "server": normalize_server_entry(config_dict.get("server_entries", [{}])[0] if config_dict.get("server_entries") else SERVER_CONFIG).get("name", "unknown"),
        "platform": platform.platform(),
        "log_tail": _read_log_tail(get_log_path()),
    }
    body = json.dumps(payload).encode("utf-8")
    file_name = f"log-{datetime.datetime.utcnow().strftime('%Y%m%dT%H%M%SZ')}-{uuid.uuid4().hex[:8]}.json"
    url = f"{base_url}/{urllib.parse.quote(file_name)}"
    req = urllib.request.Request(
        url,
        data=body,
        method="PUT",
        headers={
            "Content-Type": "application/json",
            "User-Agent": f"ThriveMessenger/{VERSION_TAG} ({sys.platform})",
            "X-Thrive-Client": "desktop",
        },
    )
    try:
        with urllib.request.urlopen(req, timeout=12) as resp:
            code = int(getattr(resp, "status", 200))
        if 200 <= code < 300:
            return True, None
        return False, f"Server returned status {code}"
    except Exception as e:
        return False, str(e)

def prompt_submit_logs(parent, config_dict, reason, intro="A diagnostic report can be submitted to help troubleshoot this issue. Submit now?"):
    res = wx.MessageBox(intro, "Submit Diagnostics", wx.YES_NO | wx.ICON_QUESTION, parent)
    if res != wx.YES:
        return False
    ok, err = submit_logs_payload(config_dict, reason=reason)
    if ok:
        show_notification("Diagnostics", "Logs submitted successfully.", timeout=4)
        wx.MessageBox("Diagnostic logs submitted successfully.", "Logs Submitted", wx.OK | wx.ICON_INFORMATION, parent)
        log_event("info", "logs_submitted_prompted", {"reason": reason})
        return True
    wx.MessageBox(f"Could not submit logs:\n{err}", "Log Submit Failed", wx.OK | wx.ICON_ERROR, parent)
    log_event("error", "logs_submit_failed", {"reason": reason, "error": str(err)})
    return False

def set_active_server_config(server_entry):
    global SERVER_CONFIG, ADDR
    normalized = normalize_server_entry(server_entry)
    SERVER_CONFIG = {
        'host': normalized['host'],
        'port': normalized['port'],
        'cafile': normalized['cafile'] or None,
    }
    ADDR = (SERVER_CONFIG['host'], SERVER_CONFIG['port'])

def resolve_default_server_entry(user_config):
    entries = dedupe_server_entries(user_config.get('server_entries', []))
    if not entries:
        entries = [normalize_server_entry(load_server_config())]
    preferred_name = user_config.get('primary_server_name') or user_config.get('last_server_name', '')
    for entry in entries:
        if entry['name'] == preferred_name:
            return entry
    return entries[0]

def fetch_server_welcome(server_entry):
    try:
        ssock = create_secure_socket(server_entry)
        ssock.settimeout(6.0)
        ssock.sendall((json.dumps({"action": "get_welcome"}) + "\n").encode())
        line = ssock.makefile().readline()
        ssock.close()
        payload = json.loads(line or "{}")
        if payload.get("action") == "welcome_info":
            return payload
    except Exception:
        pass
    return {"enabled": False, "pre_login": "", "post_login": ""}

def _format_uptime(value):
    if value is None:
        return "Unknown"
    try:
        if isinstance(value, (int, float)):
            total = int(value)
        else:
            text = str(value).strip()
            if text.isdigit():
                total = int(text)
            else:
                return text or "Unknown"
        days, rem = divmod(total, 86400)
        hours, rem = divmod(rem, 3600)
        mins, secs = divmod(rem, 60)
        parts = []
        if days:
            parts.append(f"{days}d")
        if hours or days:
            parts.append(f"{hours}h")
        if mins or hours or days:
            parts.append(f"{mins}m")
        parts.append(f"{secs}s")
        return " ".join(parts)
    except Exception:
        return "Unknown"

def fetch_server_snapshot(server_entry):
    snapshot = {
        "status": "Unreachable",
        "online_users": "Unknown",
        "online_admin_users": "Unknown",
        "total_users": "Unknown",
        "uptime": "Unknown",
    }
    try:
        ssock = create_secure_socket(server_entry)
        ssock.settimeout(6.0)
        ssock.sendall((json.dumps({"action": "server_info"}) + "\n").encode())
        line = ssock.makefile().readline()
        ssock.close()
        payload = json.loads(line or "{}")
        if payload.get("action") == "server_info_response":
            snapshot["status"] = "Online"
            snapshot["online_users"] = str(payload.get("online_users", "Unknown"))
            snapshot["online_admin_users"] = str(payload.get("online_admin_users", "Unknown"))
            snapshot["total_users"] = str(payload.get("total_users", "Unknown"))
            uptime_raw = (
                payload.get("uptime")
                or payload.get("server_uptime")
                or payload.get("uptime_seconds")
            )
            snapshot["uptime"] = _format_uptime(uptime_raw)
            return snapshot
    except Exception:
        pass
    return snapshot

def parse_invite_context_from_args(argv=None):
    args = list(argv if argv is not None else sys.argv[1:])
    pending_invite_flag = False
    for raw in args:
        candidate = str(raw or "").strip()
        if not candidate:
            continue
        if pending_invite_flag:
            pending_invite_flag = False
            token = candidate.strip()
            if token:
                return {"invite_token": token, "invite_user": "", "invite_email": "", "source": "--invite"}
            continue
        if candidate == "--invite":
            pending_invite_flag = True
            continue
        if candidate.startswith("--invite="):
            token = candidate.split("=", 1)[1].strip()
            if token:
                return {"invite_token": token, "invite_user": "", "invite_email": "", "source": "--invite"}
            continue
        parsed = urllib.parse.urlsplit(candidate)
        query = urllib.parse.parse_qs(parsed.query if parsed.query else candidate if "=" in candidate and "://" not in candidate else "")
        token = str((query.get("invite") or [""])[0] or "").strip()
        if not token:
            continue
        return {
            "invite_token": token,
            "invite_user": str((query.get("user") or [""])[0] or "").strip(),
            "invite_email": str((query.get("email") or [""])[0] or "").strip(),
            "source": candidate,
        }
    return {}

def fetch_invite_validation(server_entry, invite_token):
    token = str(invite_token or "").strip()
    if not token:
        return {"status": "error", "reason": "Missing invite token."}
    try:
        ssock = create_secure_socket(server_entry)
        ssock.settimeout(6.0)
        payload = {"action": "validate_invite", "invite_token": token}
        ssock.sendall((json.dumps(payload) + "\n").encode())
        line = ssock.makefile().readline()
        ssock.close()
        resp = json.loads(line or "{}")
        if resp.get("action") == "invite_validation":
            return resp
    except Exception as e:
        return {"status": "error", "reason": str(e)}
    return {"status": "error", "reason": "Invite validation failed."}

def extract_urls(text):
    if not text:
        return []
    out = []
    seen = set()
    for raw in URL_REGEX.findall(text):
        candidate = str(raw or "").strip().rstrip(".,;:!?")
        if candidate and candidate.lower() not in seen:
            seen.add(candidate.lower())
            out.append(candidate)
    for raw in BARE_DOMAIN_REGEX.findall(text):
        candidate = str(raw or "").strip().rstrip(".,;:!?")
        if not candidate:
            continue
        if candidate.lower().startswith(("http://", "https://", "ipfs://", "ipns://", "web3://")):
            continue
        normalized = f"https://{candidate}"
        if normalized.lower() in seen:
            continue
        seen.add(normalized.lower())
        out.append(normalized)
    return out

def _normalize_url_target(target):
    t = str(target or "").strip()
    if not t:
        return t
    # Keep file paths as-is.
    if os.path.exists(t):
        return t
    if re.match(r'^[a-zA-Z][a-zA-Z0-9+.-]*://', t):
        return t
    # Bare domains (including Web3 DNS names like *.eth, *.crypto, *.nft, Freename-managed names, etc.).
    if BARE_DOMAIN_REGEX.fullmatch(t):
        return f"https://{t}"
    return t

def open_path_or_url(target):
    target = _normalize_url_target(target)
    try:
        if sys.platform == 'win32':
            os.startfile(target)
        elif sys.platform == 'darwin':
            subprocess.Popen(['open', target])
        else:
            subprocess.Popen(['xdg-open', target])
        return True
    except Exception as e:
        print(f"Could not open target '{target}': {e}")
        return False

def get_help_doc_path():
    candidates = [
        os.path.join(get_program_dir(), "F1_HELP.md"),
        os.path.join(get_program_dir(), "README.md"),
    ]
    for candidate in candidates:
        if os.path.exists(candidate):
            return candidate
    return ""

def open_help_docs():
    open_help_docs_for_context("general", None)

def _help_docs_dir():
    path = os.path.join(get_config_dir(), "help_docs")
    os.makedirs(path, exist_ok=True)
    return path

def _help_templates_candidates():
    candidates = []
    resources_dir = get_bundle_resources_dir()
    if resources_dir:
        candidates.append(os.path.join(resources_dir, "assets", "help", "help_docs.json"))
    candidates.extend([
        os.path.join(get_program_dir(), "assets", "help", "help_docs.json"),
        os.path.join(os.getcwd(), "assets", "help", "help_docs.json"),
        os.path.join(get_config_dir(), "help_docs.json"),
    ])
    return candidates

def _load_generated_help_templates():
    for path in _help_templates_candidates():
        try:
            if not os.path.isfile(path):
                continue
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)
            if isinstance(data, dict):
                return data
        except Exception as e:
            print(f"Could not load help templates from {path}: {e}")
    return {}

def ensure_help_docs():
    docs = {
        "general": "<h1>Thrive Messenger Help</h1><p>Press F1 in each window for contextual help. Press Escape or Command+W to close this help window and return.</p>",
        "login": "<h1>Login Help</h1><p>Use Server dropdown to pick a server. Use Manage Servers to add/edit endpoints. Use Set as Primary to choose your default server. Then enter username and password and sign in.</p><p>Server host supports normal DNS and Web3-style domains (including Freename/ENS/Unstoppable-style names).</p>",
        "main": "<h1>Contacts Window Help</h1><p>Manage contacts, statuses, files, and chats. Default action is Start Chat for the focused contact. User actions are available from User and context menus. File Transfers window shows sent/received files and their saved locations.</p>",
        "chat": "<h1>Chat Window Help</h1><p>Enter sends message, Ctrl+Enter sends file, and Cmd+Enter inserts a new line. Message history is keyboard navigable and links can be activated from selected items. Typing indicators and readout can be toggled in Settings.</p>",
        "directory": "<h1>User Directory Help</h1><p>Shows users from current and configured servers with server labels. Use Sort and Filter options for contacts. If a selected server does not support a feature, the related action is dimmed and explains why.</p>",
        "admin": "<h1>Admin Commands Help</h1><p>Commands start with '/'. Example: /alert message, /create username password, /admin username.</p><p>To get more help in the command text box, type ? or help (with or without a leading slash).</p>",
        "settings": "<h1>Settings Help</h1><p>Configure sound pack, default sound pack selection, sound volume, call input/output levels, and chat accessibility options. Settings are remembered by the app.</p><p>Administration server host supports standard DNS hostnames and Web3-style domains.</p>",
        "server_info": "<h1>Server Info Help</h1><p>Shows active server host, port, encryption state, user counts, and file policy limits.</p>",
        "bot_rules": "<h1>Bot Rules Help</h1><p>Admins can load, edit, save, and reset bot rules. Non-admin users can view active rules but cannot edit.</p>",
    }
    generated = _load_generated_help_templates()
    for key in list(docs.keys()):
        val = generated.get(key)
        if isinstance(val, str) and val.strip():
            docs[key] = val.strip()
    out = {}
    for key, html in docs.items():
        path = os.path.join(_help_docs_dir(), f"{key}.html")
        body = html.strip()
        if "<html" in body.lower():
            final_html = body
        else:
            final_html = f"<!doctype html><html><head><meta charset='utf-8'><title>Help</title></head><body>{body}</body></html>"
        with open(path, "w", encoding="utf-8") as f:
            f.write(final_html)
        out[key] = path
    return out

_nvda_controller = None

def _nvda_controller_candidates():
    exe_dir = os.path.dirname(os.path.abspath(sys.executable if getattr(sys, "frozen", False) else sys.argv[0]))
    source_dir = os.path.dirname(os.path.abspath(__file__))
    roots = [exe_dir, getattr(sys, "_MEIPASS", None), source_dir, os.path.join(source_dir, "native", "windows"), os.getcwd()]
    bits = "64" if sys.maxsize > 2**32 else "32"
    names = [f"nvdaControllerClient{bits}.dll", "nvdaControllerClient.dll"]
    for root in [r for r in roots if r]:
        for name in names:
            yield os.path.join(root, name)

def _speak_with_nvda_controller(text, interrupt=False):
    """Speak through the running NVDA via its controller client; False if NVDA or the DLL isn't available."""
    global _nvda_controller
    try:
        import ctypes
        if _nvda_controller is False:
            return False
        if _nvda_controller is None:
            for candidate in _nvda_controller_candidates():
                if not os.path.exists(candidate):
                    continue
                try:
                    dll = ctypes.WinDLL(candidate)
                    dll.nvdaController_speakText.argtypes = [ctypes.c_wchar_p]
                    dll.nvdaController_speakText.restype = ctypes.c_int
                    dll.nvdaController_testIfRunning.restype = ctypes.c_int
                    dll.nvdaController_cancelSpeech.restype = ctypes.c_int
                    _nvda_controller = dll
                    break
                except Exception:
                    continue
            if _nvda_controller is None:
                _nvda_controller = False
                return False
        if _nvda_controller.nvdaController_testIfRunning() != 0:
            return False
        if interrupt:
            _nvda_controller.nvdaController_cancelSpeech()
        return _nvda_controller.nvdaController_speakText(str(text)) == 0
    except Exception:
        return False

def _voiceover_enabled():
    try:
        from AppKit import NSWorkspace
        return bool(NSWorkspace.sharedWorkspace().isVoiceOverEnabled())
    except Exception:
        return False

def _speak_with_voiceover(text, interrupt=False):
    """macOS: hand the text to VoiceOver as an accessibility announcement (like NVDA on Windows).
    False when VoiceOver is off or AppKit isn't available, so the caller can fall back to 'say'."""
    try:
        from AppKit import (NSApplication, NSWorkspace, NSAccessibilityPostNotificationWithUserInfo,
                            NSAccessibilityAnnouncementRequestedNotification, NSAccessibilityAnnouncementKey,
                            NSAccessibilityPriorityKey, NSAccessibilityPriorityHigh, NSAccessibilityPriorityMedium)
    except Exception:
        return False
    try:
        if not NSWorkspace.sharedWorkspace().isVoiceOverEnabled():
            return False
        app = NSApplication.sharedApplication()
        element = app.keyWindow() or app.mainWindow() or app
        info = {NSAccessibilityAnnouncementKey: str(text),
                NSAccessibilityPriorityKey: NSAccessibilityPriorityHigh if interrupt else NSAccessibilityPriorityMedium}
        NSAccessibilityPostNotificationWithUserInfo(element, NSAccessibilityAnnouncementRequestedNotification, info)
        return True
    except Exception:
        return False

def speak_text(text, interrupt=None):
    try:
        if not text:
            return
        app = wx.GetApp() if wx.GetApp() else None
        if sys.platform == 'win32':
            nvda_interrupt = bool(getattr(app, "user_config", {}).get('interrupt_speech', True)) if (app and interrupt is None) else bool(interrupt)
            if _speak_with_nvda_controller(text, interrupt=nvda_interrupt):
                return
        if interrupt is None:
            interrupt = bool(getattr(app, "user_config", {}).get('interrupt_speech', True)) if app else True
        if interrupt and app:
            previous = getattr(app, "_tts_process", None)
            if previous and previous.poll() is None:
                try:
                    previous.terminate()
                except Exception:
                    pass
        if sys.platform == 'darwin':
            vo_interrupt = bool(interrupt) if interrupt is not None else bool(getattr(app, "user_config", {}).get('interrupt_speech', True)) if app else True
            if threading.current_thread() is threading.main_thread():
                if _speak_with_voiceover(text, interrupt=vo_interrupt):
                    return
            elif _voiceover_enabled():
                wx.CallAfter(_speak_with_voiceover, text, vo_interrupt)
                return
            if interrupt:
                subprocess.Popen(['killall', 'say'], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            proc = subprocess.Popen(['say', text])
        elif sys.platform == 'win32':
            safe_text = text.replace("'", "''")
            cmd = (
                "Add-Type -AssemblyName System.Speech; "
                "$s=New-Object System.Speech.Synthesis.SpeechSynthesizer; "
                "$s.Speak('{0}')"
            ).format(safe_text)
            proc = subprocess.Popen(["powershell", "-NoProfile", "-Command", cmd], creationflags=0x08000000)
        else:
            proc = None
        if app and proc:
            app._tts_process = proc
    except Exception as e:
        print(f"TTS speak failed: {e}")

def _received_files_dir():
    return os.path.join(os.path.expanduser('~'), 'Documents', 'ThriveMessenger', 'files')

def _move_to_trash(path):
    """Recoverable delete: Recycle Bin on Windows, Trash on macOS."""
    if sys.platform == 'win32':
        import ctypes
        from ctypes import wintypes
        class SHFILEOPSTRUCTW(ctypes.Structure):
            _fields_ = [("hwnd", wintypes.HWND), ("wFunc", wintypes.UINT), ("pFrom", wintypes.LPCWSTR),
                        ("pTo", wintypes.LPCWSTR), ("fFlags", ctypes.c_ushort), ("fAnyOperationsAborted", wintypes.BOOL),
                        ("hNameMappings", ctypes.c_void_p), ("lpszProgressTitle", wintypes.LPCWSTR)]
        FO_DELETE, FOF_SILENT, FOF_NOCONFIRMATION, FOF_ALLOWUNDO, FOF_NOERRORUI = 3, 0x4, 0x10, 0x40, 0x400
        op = SHFILEOPSTRUCTW(None, FO_DELETE, os.path.abspath(path) + "\0", None,
                             FOF_ALLOWUNDO | FOF_NOCONFIRMATION | FOF_SILENT | FOF_NOERRORUI, False, None, None)
        return ctypes.windll.shell32.SHFileOperationW(ctypes.byref(op)) == 0 and not os.path.exists(path)
    if sys.platform == 'darwin':
        trash = os.path.join(os.path.expanduser('~'), '.Trash')
        if os.path.isdir(trash):
            dest = os.path.join(trash, os.path.basename(path))
            if os.path.exists(dest):
                name, ext = os.path.splitext(os.path.basename(path))
                dest = os.path.join(trash, f"{name} {int(time.time())}{ext}")
            shutil.move(path, dest)
            return True
    return False

def voice_cache_dir():
    return os.path.join(get_config_dir(), "voice_messages")

def remove_received_files(paths):
    """Move files this app saved (received transfers, cached voice messages) to the trash. Never touches anything else."""
    roots = [os.path.realpath(_received_files_dir()), os.path.realpath(voice_cache_dir())]
    removed = 0
    for path in paths or []:
        try:
            real = os.path.realpath(str(path))
            if not any(real.startswith(r + os.sep) for r in roots) or not os.path.isfile(real):
                continue
            if _move_to_trash(real):
                removed += 1
        except Exception as e:
            print(f"Could not remove received file {path}: {e}")
    return removed

def play_tts_audio_from_message(msg):
    if isinstance(msg.get("voice"), dict):
        return False  # shown as a playable voice message instead
    try:
        b64 = str(msg.get("tts_audio_b64", "") or "").strip()
        if not b64:
            return False
        audio = base64.b64decode(b64)
        if not audio:
            return False
        tts_dir = os.path.join(get_config_dir(), "tts_cache")
        os.makedirs(tts_dir, exist_ok=True)
        voice_name = str(msg.get("tts_voice", "bot")).strip().replace("/", "_")
        path = os.path.join(tts_dir, f"{voice_name}-{uuid.uuid4().hex}.wav")
        with open(path, "wb") as f:
            f.write(audio)
        sound = wx.adv.Sound(path)
        if sound.IsOk():
            sound.Play(wx.adv.SOUND_ASYNC)
            threading.Timer(25.0, lambda: os.path.exists(path) and os.remove(path)).start()
            return True
        try:
            os.remove(path)
        except Exception:
            pass
        return False
    except Exception as e:
        print(f"Bot TTS playback failed: {e}")
        return False

def open_help_docs_for_context(context, parent):
    docs = ensure_help_docs()
    target = docs.get(context) or docs.get("general")
    if wxhtml2 is not None:
        try:
            dlg = wx.Dialog(parent, title="Help", size=(760, 560))
            def _on_key(event):
                key = event.GetKeyCode()
                if key == wx.WXK_ESCAPE or (event.CmdDown() and key == ord('W')):
                    dlg.EndModal(wx.ID_OK)
                    return
                event.Skip()
            dlg.Bind(wx.EVT_CHAR_HOOK, _on_key)
            web = wxhtml2.WebView.New(dlg)
            web.LoadURL("file://" + target)
            s = wx.BoxSizer(wx.VERTICAL)
            s.Add(web, 1, wx.EXPAND | wx.ALL, 0)
            dlg.SetSizer(s)
            dlg.ShowModal()
            dlg.Destroy()
            return
        except Exception as e:
            print(f"WebView help fallback: {e}")
    open_path_or_url(target)

def parse_github_tag(tag):
    m = re.match(r'^v(\d{4})-alpha(\d+)(?:\.(\d+))?$', tag)
    if not m: return None
    return (int(m.group(1)) - 2000, 0, int(m.group(2)), int(m.group(3)) if m.group(3) else 0)

def parse_update_feed(feed_data, local_tag, platform):
    """Normalize current and legacy update-feed keys for one client platform."""
    local = parse_github_tag(local_tag)
    # A platform-specific tag (win_tag / mac_tag) wins, so a Windows-only release never re-offers the old Mac build.
    platform_tag = feed_data.get("mac_tag") if platform == "darwin" else (feed_data.get("win_tag") if platform == "win32" else None)
    tag = str(platform_tag or feed_data.get("tag") or feed_data.get("tag_name") or "").strip()
    remote = parse_github_tag(tag)
    if local is None or remote is None or remote <= local:
        return None
    mac_zip = (
        feed_data.get("mac_zip_url")
        or feed_data.get("mac_url")
        or feed_data.get("mac_x86_64_url")
    )
    win_zip = feed_data.get("win_zip_url") or feed_data.get("windows_zip_url")
    generic_zip = feed_data.get("zip_url")
    if platform == "darwin":
        preferred_zip = mac_zip or generic_zip or win_zip
    elif platform == "win32":
        preferred_zip = win_zip or generic_zip or mac_zip
    else:
        preferred_zip = generic_zip or win_zip or mac_zip
    hashes = feed_data.get("sha256") if isinstance(feed_data.get("sha256"), dict) else {}
    return {
        "source": "feed",
        "tag": tag,
        "remote": remote,
        "zip_url": preferred_zip,
        "mac_zip_url": mac_zip,
        "win_zip_url": win_zip,
        "installer_url": feed_data.get("installer_url") or feed_data.get("win_installer_url"),
        "win_zip_sha256": hashes.get("win_zip") or hashes.get("zip"),
        "installer_sha256": hashes.get("installer"),
        "mac_zip_sha256": hashes.get("mac_x86_64") or hashes.get("mac"),
        "repo": feed_data.get("repo"),
    }

def _load_update_settings():
    cfg = load_client_config()
    update_feed_url = cfg.get('updates', 'feed_url', fallback='').strip()
    preferred_repo = cfg.get('updates', 'preferred_repo', fallback='Raywonder/ThriveMessenger').strip()
    fallback_repos = [x.strip() for x in cfg.get('updates', 'fallback_repos', fallback='').split(',') if x.strip()]
    repos = []
    for candidate in [preferred_repo] + fallback_repos:
        if '/' in candidate and candidate not in repos:
            repos.append(candidate)
    return {
        "feed_url": update_feed_url,
        "repos": repos or ["Raywonder/ThriveMessenger"],
    }

def get_program_dir():
    if getattr(sys, 'frozen', False): return os.path.dirname(sys.executable)
    return os.path.dirname(os.path.abspath(__file__))

def get_program_client_conf_path():
    return os.path.join(get_program_dir(), 'client.conf')

def get_user_client_conf_path():
    return os.path.join(get_config_dir(), 'client.conf')

def get_client_conf_read_paths():
    paths = []
    for candidate in (
        get_program_client_conf_path(),
        os.path.join(os.getcwd(), 'client.conf'),
        get_user_client_conf_path(),
    ):
        if candidate not in paths and os.path.isfile(candidate):
            paths.append(candidate)
    return paths

def get_client_conf_path():
    user_config = get_user_client_conf_path()
    if os.path.isfile(user_config):
        return user_config
    paths = get_client_conf_read_paths()
    if paths:
        return paths[0]
    return user_config

def load_client_config():
    config = configparser.ConfigParser(interpolation=None)
    config.read(get_client_conf_read_paths())
    return config

SERVER_CONFIG = load_server_config()
ADDR = (SERVER_CONFIG['host'], SERVER_CONFIG['port'])

def get_macos_app_bundle_path():
    if sys.platform != 'darwin':
        return None
    cur = os.path.abspath(sys.executable)
    while True:
        if cur.lower().endswith('.app') and os.path.isdir(cur):
            return cur
        parent = os.path.dirname(cur)
        if parent == cur:
            break
        cur = parent
    return None

def get_bundle_resources_dir():
    if not getattr(sys, 'frozen', False):
        return None
    exe_dir = os.path.dirname(sys.executable)
    if sys.platform == 'darwin':
        # PyInstaller macOS app bundle: Contents/MacOS/<binary> and Contents/Resources/<assets>.
        resources = os.path.abspath(os.path.join(exe_dir, '..', 'Resources'))
        if os.path.isdir(resources):
            return resources
    # Windows one-folder build typically places assets next to the executable.
    return exe_dir

def is_installer_install():
    return os.path.exists(os.path.join(get_program_dir(), 'unins000.exe'))

def get_sounds_dir():
    resources_dir = get_bundle_resources_dir()
    if resources_dir:
        bundled = os.path.join(resources_dir, 'sounds')
        if os.path.isdir(bundled):
            return bundled
    local_sounds = os.path.join(get_program_dir(), 'sounds')
    if os.path.isdir(local_sounds):
        return local_sounds
    return os.path.join(os.getcwd(), 'sounds')

def get_downloaded_sounds_dir():
    sounds_dir = os.path.join(os.path.dirname(get_settings_path()), 'sounds')
    os.makedirs(sounds_dir, exist_ok=True)
    return sounds_dir

def get_demo_videos_dir():
    resources_dir = get_bundle_resources_dir()
    if resources_dir:
        bundled = os.path.join(resources_dir, 'assets', 'videos')
        if os.path.isdir(bundled):
            return bundled
    local_videos = os.path.join(get_program_dir(), 'assets', 'videos')
    if os.path.isdir(local_videos):
        return local_videos
    fallback = os.path.join(os.getcwd(), 'assets', 'videos')
    os.makedirs(fallback, exist_ok=True)
    return fallback

def get_soundpack_base_url(config_dict):
    base = str(config_dict.get('soundpack_base_url', DEFAULT_SOUNDPACK_BASE_URL) or DEFAULT_SOUNDPACK_BASE_URL).strip()
    return base.rstrip('/')

def get_sound_fetch_headers():
    return {
        "User-Agent": f"ThriveMessenger/{VERSION_TAG} ({sys.platform})",
        "X-Thrive-Client": "desktop",
        "Accept": "application/json, audio/wav, application/octet-stream, */*",
    }

def _safe_sound_name(name):
    return bool(re.match(r'^[A-Za-z0-9._ -]+$', str(name or '')))

def get_remote_sound_manifest(config_dict):
    base = get_soundpack_base_url(config_dict)
    url = f"{base}/index.json"
    req = urllib.request.Request(url, headers=get_sound_fetch_headers())
    try:
        with urllib.request.urlopen(req, timeout=4) as resp:
            data = json.loads(resp.read().decode('utf-8', errors='replace'))
        packs = data.get('packs', {})
        return packs if isinstance(packs, dict) else {}
    except Exception:
        # Fallback to autoindex parsing so newly added packs/files appear without manifest updates.
        result = {}
        try:
            root_req = urllib.request.Request(f"{base}/", headers=get_sound_fetch_headers())
            with urllib.request.urlopen(root_req, timeout=5) as resp:
                listing = resp.read().decode('utf-8', errors='replace')
            pack_names = []
            for href in re.findall(r'href="([^"]+)"', listing):
                if href in ('../', '/'):
                    continue
                name = href.strip('/').strip()
                if name and _safe_sound_name(name):
                    pack_names.append(name)
            for pack in sorted(set(pack_names)):
                try:
                    pack_req = urllib.request.Request(f"{base}/{urllib.parse.quote(pack)}/", headers=get_sound_fetch_headers())
                    with urllib.request.urlopen(pack_req, timeout=5) as presp:
                        p_listing = presp.read().decode('utf-8', errors='replace')
                    wavs = []
                    for href in re.findall(r'href="([^"]+)"', p_listing):
                        candidate = href.split('?', 1)[0].strip()
                        if candidate.lower().endswith('.wav'):
                            fname = os.path.basename(candidate)
                            if _safe_sound_name(fname):
                                wavs.append(fname)
                    if wavs:
                        result[pack] = sorted(set(wavs))
                except Exception:
                    continue
        except Exception:
            return {}
        return result

def list_available_sound_packs(config_dict):
    packs = {'none', 'default'}
    for root in (get_sounds_dir(), get_downloaded_sounds_dir()):
        if not os.path.isdir(root):
            continue
        try:
            for d in os.listdir(root):
                if os.path.isdir(os.path.join(root, d)):
                    packs.add(d)
        except Exception:
            pass
    for pack_name in get_remote_sound_manifest(config_dict).keys():
        if _safe_sound_name(pack_name):
            packs.add(pack_name)
    return sorted(packs)

def find_local_sound_path(pack, sound_file):
    for root in (get_sounds_dir(), get_downloaded_sounds_dir()):
        p = os.path.join(root, pack, sound_file)
        if os.path.exists(p):
            return p
    return None

def download_sound_file_if_missing(config_dict, pack, sound_file):
    if not (_safe_sound_name(pack) and _safe_sound_name(sound_file)):
        return None
    existing = find_local_sound_path(pack, sound_file)
    if existing:
        return existing
    base = get_soundpack_base_url(config_dict)
    url = f"{base}/{urllib.parse.quote(pack)}/{urllib.parse.quote(sound_file)}"
    req = urllib.request.Request(url, headers=get_sound_fetch_headers())
    key = f"{pack}/{sound_file}"
    if key not in _SOUND_DOWNLOAD_NOTICE_CACHE:
        _SOUND_DOWNLOAD_NOTICE_CACHE.add(key)
        show_notification("Sound pack", f"Downloading sound: {pack}/{sound_file}", timeout=3)
    try:
        with urllib.request.urlopen(req, timeout=8) as resp:
            blob = resp.read()
        if not blob:
            return None
        out_dir = os.path.join(get_downloaded_sounds_dir(), pack)
        os.makedirs(out_dir, exist_ok=True)
        out_path = os.path.join(out_dir, sound_file)
        tmp_path = out_path + ".part"
        with open(tmp_path, 'wb') as f:
            f.write(blob)
        os.replace(tmp_path, out_path)
        show_notification("Sound pack", f"Downloaded sound: {pack}/{sound_file}", timeout=3)
        return out_path
    except Exception:
        if key not in _SOUND_DOWNLOAD_FAILURE_CACHE:
            _SOUND_DOWNLOAD_FAILURE_CACHE.add(key)
            show_notification("Sound pack", f"Could not download sound: {pack}/{sound_file}", timeout=4)
        return None

def check_for_update(callback):
    def _check():
        import urllib.request
        try:
            local = parse_github_tag(VERSION_TAG)
            if local is None:
                wx.CallAfter(callback, None, None, f"Unrecognized local version tag: {VERSION_TAG}")
                return
            settings = _load_update_settings()
            UPDATE_CONTEXT.clear()

            feed_url = settings.get("feed_url")
            if feed_url:
                try:
                    feed_req = urllib.request.Request(feed_url, headers={"User-Agent": f"ThriveMessenger/{VERSION_TAG} ({sys.platform})", "Accept": "application/json"})
                    with urllib.request.urlopen(feed_req, timeout=15) as resp:
                        feed_data = json.loads(resp.read().decode())
                    update = parse_update_feed(feed_data, VERSION_TAG, sys.platform)
                    if update:
                        update["feed_url"] = feed_url
                        UPDATE_CONTEXT.update(update)
                        wx.CallAfter(callback, update["tag"], ".".join(str(x) for x in update["remote"]), None)
                        return
                except Exception as feed_err:
                    print(f"Update feed check failed: {feed_err}")

            best = None
            for repo in settings.get("repos", []):
                url = f"https://api.github.com/repos/{repo}/releases/latest"
                req = urllib.request.Request(url, headers={"Accept": "application/vnd.github+json", "User-Agent": f"ThriveMessenger/{VERSION_TAG} ({sys.platform})"})
                try:
                    with urllib.request.urlopen(req, timeout=15) as resp:
                        data = json.loads(resp.read().decode())
                except Exception as repo_err:
                    print(f"Update check failed for {repo}: {repo_err}")
                    continue
                tag = data.get("tag_name", "")
                remote = parse_github_tag(tag)
                if remote is None:
                    continue
                if best is None or remote > best["remote"]:
                    best = {"repo": repo, "tag": tag, "remote": remote}
            if best and best["remote"] > local:
                UPDATE_CONTEXT.update({"source": "repo", "repo": best["repo"], "tag": best["tag"]})
                wx.CallAfter(callback, best["tag"], ".".join(str(x) for x in best["remote"]), None)
                return
            wx.CallAfter(callback, None, None, None)
        except Exception as e:
            wx.CallAfter(callback, None, None, str(e))
    threading.Thread(target=_check, daemon=True).start()

def download_update(url, dest, progress_dlg, callback, expected_sha256=None):
    def _download():
        import urllib.request
        try:
            req = urllib.request.Request(url, headers={"User-Agent": f"ThriveMessenger/{VERSION_TAG} ({sys.platform})"})
            with urllib.request.urlopen(req, timeout=120) as resp:
                total = int(resp.headers.get('Content-Length', 0))
                downloaded = 0
                digest = hashlib.sha256()
                with open(dest, 'wb') as f:
                    while True:
                        chunk = resp.read(65536)
                        if not chunk: break
                        f.write(chunk)
                        digest.update(chunk)
                        downloaded += len(chunk)
                        if total > 0:
                            pct = min(int(downloaded * 100 / total), 100)
                            wx.CallAfter(progress_dlg.Update, pct, f"Downloaded {downloaded // 1024} KB of {total // 1024} KB")
                if total > 0 and downloaded != total:
                    raise RuntimeError(f"Update download was incomplete: received {downloaded} of {total} bytes.")
                if expected_sha256 and digest.hexdigest().lower() != str(expected_sha256).lower():
                    raise RuntimeError("Update download failed SHA-256 verification.")
            wx.CallAfter(callback, True, None)
        except Exception as e:
            try:
                if os.path.exists(dest): os.remove(dest)
            except OSError:
                pass
            wx.CallAfter(callback, False, str(e))
    threading.Thread(target=_download, daemon=True).start()

def apply_installer_update(installer_path):
    program_dir = get_program_dir()
    exe_path = os.path.join(program_dir, 'thrive_messenger.exe')
    batch_path = os.path.join(tempfile.gettempdir(), 'thrive_update.cmd')
    with open(batch_path, 'w') as f:
        f.write(f'@echo off\r\n')
        f.write(f'start /wait "" "{installer_path}" /VERYSILENT /CLOSEAPPLICATIONS /NORESTART\r\n')
        f.write(f'start "" "{exe_path}"\r\n')
        f.write(f'del "{installer_path}"\r\n')
        f.write(f'del "%~f0"\r\n')
    subprocess.Popen(['cmd', '/c', batch_path], creationflags=0x08000000)

def build_windows_zip_update_batch(zip_path, program_dir, exe_path, pid, temp_extract):
    return (
        "@echo off\r\n"
        "setlocal\r\n"
        f'set "UPDATE_LOG={os.path.join(tempfile.gettempdir(), "thrive_update.log")}"\r\n'
        f':waitloop\r\n'
        f'tasklist /fi "PID eq {pid}" 2>NUL | find /i "{pid}" >NUL\r\n'
        "if not errorlevel 1 (\r\n"
        "    timeout /t 1 /nobreak >NUL\r\n"
        "    goto waitloop\r\n"
        ")\r\n"
        f'if exist "{temp_extract}" rmdir /s /q "{temp_extract}"\r\n'
        f'powershell -NoProfile -Command "Expand-Archive -LiteralPath \'{zip_path}\' -DestinationPath \'{temp_extract}\' -Force" >> "%UPDATE_LOG%" 2>&1\r\n'
        "if errorlevel 1 goto failed\r\n"
        f'set "SOURCE_DIR={temp_extract}"\r\n'
        f'if exist "{temp_extract}\\thrive_messenger\\thrive_messenger.exe" set "SOURCE_DIR={temp_extract}\\thrive_messenger"\r\n'
        'if not exist "%SOURCE_DIR%\\thrive_messenger.exe" goto failed\r\n'
        f'xcopy /s /e /y /q "%SOURCE_DIR%\\*" "{program_dir}\\" >> "%UPDATE_LOG%" 2>&1\r\n'
        "if errorlevel 1 goto failed\r\n"
        f'rmdir /s /q "{temp_extract}"\r\n'
        f'del "{zip_path}"\r\n'
        f'start "" "{exe_path}"\r\n'
        'del "%~f0"\r\n'
        "exit /b 0\r\n"
        ":failed\r\n"
        'echo Update failed. See "%UPDATE_LOG%". >> "%UPDATE_LOG%"\r\n'
        "exit /b 1\r\n"
    )

def apply_zip_update(zip_path):
    if sys.platform == 'darwin':
        target_app = get_macos_app_bundle_path()
        if not target_app:
            raise RuntimeError("Could not determine installed app bundle path for macOS update.")
        pid = os.getpid()
        temp_extract = os.path.join(tempfile.gettempdir(), 'thrive_update_extract')
        script_path = os.path.join(tempfile.gettempdir(), 'thrive_update.sh')
        target_parent = os.path.dirname(target_app)
        with open(script_path, 'w', encoding='utf-8') as f:
            f.write("#!/bin/sh\n")
            f.write("set -e\n")
            f.write(f"PID='{pid}'\n")
            f.write(f"ZIP='{zip_path}'\n")
            f.write(f"TEMP_EXTRACT='{temp_extract}'\n")
            f.write(f"TARGET_APP='{target_app}'\n")
            f.write(f"TARGET_PARENT='{target_parent}'\n")
            f.write("while kill -0 \"$PID\" 2>/dev/null; do sleep 1; done\n")
            f.write("/bin/rm -rf \"$TEMP_EXTRACT\"\n")
            f.write("/bin/mkdir -p \"$TEMP_EXTRACT\"\n")
            f.write("/usr/bin/ditto -x -k \"$ZIP\" \"$TEMP_EXTRACT\"\n")
            f.write("NEW_APP=$(/usr/bin/find \"$TEMP_EXTRACT\" -maxdepth 4 -type d -name '*.app' | /usr/bin/head -n 1)\n")
            f.write("if [ -z \"$NEW_APP\" ]; then exit 1; fi\n")
            f.write("/bin/rm -rf \"$TARGET_APP\"\n")
            f.write("/usr/bin/ditto \"$NEW_APP\" \"$TARGET_APP\"\n")
            f.write("/bin/rm -rf \"$TEMP_EXTRACT\"\n")
            f.write("/bin/rm -f \"$ZIP\"\n")
            f.write("/usr/bin/open -a \"$TARGET_APP\"\n")
            f.write("/bin/rm -f \"$0\"\n")
        os.chmod(script_path, 0o755)
        subprocess.Popen(['/bin/sh', script_path], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, close_fds=True)
        return

    program_dir = get_program_dir()
    exe_path = os.path.join(program_dir, 'thrive_messenger.exe')
    pid = os.getpid()
    temp_extract = os.path.join(tempfile.gettempdir(), 'thrive_update_extract')
    batch_path = os.path.join(tempfile.gettempdir(), 'thrive_update.cmd')
    with open(batch_path, 'w') as f:
        f.write(build_windows_zip_update_batch(zip_path, program_dir, exe_path, pid, temp_extract))
    subprocess.Popen(['cmd', '/c', batch_path], creationflags=0x08000000)

class ThriveTaskBarIcon(wx.adv.TaskBarIcon):
    def __init__(self, frame):
        super().__init__(); self.frame = frame; icon = wx.Icon(wx.ArtProvider.GetIcon(wx.ART_INFORMATION, wx.ART_OTHER, (16, 16))); self.SetIcon(icon, "Thrive Messenger"); self.Bind(wx.adv.EVT_TASKBAR_LEFT_DCLICK, self.on_restore); self.Bind(wx.EVT_MENU, self.on_restore, id=1); self.Bind(wx.EVT_MENU, self.on_exit, id=2)
    def CreatePopupMenu(self): menu = wx.Menu(); menu.Append(1, "&Restore"); menu.Append(2, "E&xit"); return menu
    def on_restore(self, event): self.frame.restore_from_tray()
    def on_exit(self, event): self.frame.on_exit(None)

class AuthenticatedDevicesDialog(wx.Dialog):
    """Server-backed inventory of authenticated devices and locations."""
    def __init__(self, parent):
        super().__init__(parent, title="Authenticated Devices", size=(700, 460))
        self.devices = []
        panel = wx.Panel(self); sizer = wx.BoxSizer(wx.VERTICAL)
        self.summary = wx.StaticText(panel, label="Loading authenticated devices…")
        self.device_list = wx.ListBox(panel, name="Authenticated device list")
        row = wx.BoxSizer(wx.HORIZONTAL)
        refresh_btn = wx.Button(panel, label="&Refresh")
        self.revoke_btn = wx.Button(panel, label="&Sign Out Selected Device")
        close_btn = wx.Button(panel, wx.ID_CLOSE, "&Close")
        row.Add(refresh_btn, 0, wx.RIGHT, 8); row.Add(self.revoke_btn, 0, wx.RIGHT, 8); row.Add(close_btn)
        sizer.Add(self.summary, 0, wx.EXPAND | wx.ALL, 10)
        sizer.Add(self.device_list, 1, wx.EXPAND | wx.LEFT | wx.RIGHT | wx.BOTTOM, 10)
        sizer.Add(row, 0, wx.ALIGN_RIGHT | wx.LEFT | wx.RIGHT | wx.BOTTOM, 10)
        panel.SetSizer(sizer)
        refresh_btn.Bind(wx.EVT_BUTTON, self.refresh)
        self.revoke_btn.Bind(wx.EVT_BUTTON, self.revoke_selected)
        close_btn.Bind(wx.EVT_BUTTON, lambda _: self.EndModal(wx.ID_CLOSE))
        self.device_list.Bind(wx.EVT_LISTBOX, lambda _: self.revoke_btn.Enable(self.device_list.GetSelection() != wx.NOT_FOUND))
        self.revoke_btn.Disable(); wx.CallAfter(self.refresh, None)

    @property
    def frame(self): return self.GetParent()

    def refresh(self, _):
        self.frame.sock.sendall((json.dumps({"action": "list_authenticated_devices"}) + "\n").encode())

    def update_devices(self, message):
        self.devices = list(message.get("devices", []))
        self.summary.SetLabel(f"You are currently authenticated on {len(self.devices)} device(s) or locations.")
        labels = []
        for item in self.devices:
            current = " — current device" if item.get("current") else ""
            expiry = item.get("expires_at") or "never"
            labels.append(f"{item.get('device_name', 'Unknown device')} | {item.get('platform', 'unknown')} | authenticated {item.get('authenticated_at', '')} | expires {expiry}{current}")
        self.device_list.Set(labels); self.revoke_btn.Disable()

    def revoke_selected(self, _):
        index = self.device_list.GetSelection()
        if index == wx.NOT_FOUND or index >= len(self.devices): return
        item = self.devices[index]; label = item.get('device_name', 'selected device')
        if wx.MessageBox(f"Sign out {label}?", "Confirm Device Sign Out", wx.YES_NO | wx.ICON_QUESTION, self) != wx.YES: return
        self.frame.sock.sendall((json.dumps({"action": "deauthenticate_device", "session_id": item.get("session_id", "")}) + "\n").encode())

def apply_toggle_semantics(window):
    """Every on/off control is a wx.CheckBox (NVDA: "check box, checked"). On macOS, mark them as switches so
    VoiceOver says "switch, on/off" (the AXSwitch subrole NSSwitch uses); the control stays a native checkbox."""
    if sys.platform != 'darwin':
        return
    try:
        import objc
    except Exception:
        return
    def walk(w):
        for child in w.GetChildren():
            if isinstance(child, wx.CheckBox):
                try:
                    view = objc.objc_object(c_void_p=child.GetHandle())
                    if view.respondsToSelector_("setAccessibilitySubrole:"):
                        view.setAccessibilitySubrole_("AXSwitch")
                except Exception:
                    pass
            walk(child)
    walk(window)

class SettingsDialog(wx.Dialog):
    def __init__(self, parent, current_config, can_admin=False):
        super().__init__(parent, title="Settings", size=(560, 650)); self.config = current_config
        self._can_admin = bool(can_admin)
        self.Bind(wx.EVT_CHAR_HOOK, self.on_key)
        panel = wx.Panel(self); main_sizer = wx.BoxSizer(wx.VERTICAL)
        notebook = wx.Notebook(panel)
        tab_general = wx.Panel(notebook)
        tab_audio = wx.Panel(notebook)
        tab_admin = wx.Panel(notebook)
        notebook.AddPage(tab_general, "General")
        notebook.AddPage(tab_audio, "Audio")
        if self._can_admin:
            notebook.AddPage(tab_admin, "Administration")
        sound_box = wx.StaticBoxSizer(wx.VERTICAL, tab_audio, "&Sound Pack")
        call_audio_box = wx.StaticBoxSizer(wx.VERTICAL, tab_audio, "Call Audio Levels")
        accessibility_box = wx.StaticBoxSizer(wx.VERTICAL, tab_general, "&Chat Behavior")
        admin_box = wx.StaticBoxSizer(wx.VERTICAL, tab_admin, "Server and Updater Configuration")
        
        dark_mode_on = is_windows_dark_mode()
        if dark_mode_on:
            dark_color = wx.Colour(40, 40, 40); light_text_color = wx.WHITE
            WxMswDarkMode().enable(self); self.SetBackgroundColour(dark_color); panel.SetBackgroundColour(dark_color)
            tab_general.SetBackgroundColour(dark_color)
            tab_audio.SetBackgroundColour(dark_color)
            tab_admin.SetBackgroundColour(dark_color)
            sound_box.GetStaticBox().SetForegroundColour(light_text_color)
            sound_box.GetStaticBox().SetBackgroundColour(dark_color)
            call_audio_box.GetStaticBox().SetForegroundColour(light_text_color)
            call_audio_box.GetStaticBox().SetBackgroundColour(dark_color)
            accessibility_box.GetStaticBox().SetForegroundColour(light_text_color)
            accessibility_box.GetStaticBox().SetBackgroundColour(dark_color)
            admin_box.GetStaticBox().SetForegroundColour(light_text_color)
            admin_box.GetStaticBox().SetBackgroundColour(dark_color)
        
        sound_packs = list_available_sound_packs(self.config)
        self.choice = wx.Choice(sound_box.GetStaticBox(), choices=sound_packs)
        current_pack = self.config.get('soundpack', 'default')
        if not current_pack:
            current_pack = 'none'
        if current_pack in sound_packs:
            self.choice.SetStringSelection(current_pack)
        else:
            self.choice.SetStringSelection('default')
        self.default_soundpack_label = wx.StaticText(sound_box.GetStaticBox(), label=f"Current default pack: {self.config.get('default_soundpack', 'default')}")
        self.set_selected_default_cb = wx.CheckBox(sound_box.GetStaticBox(), label="Set selected pack as default sound pack")
        self.choice.Bind(wx.EVT_CHOICE, self.on_sound_pack_changed)
        self.call_pack_label = wx.StaticText(sound_box.GetStaticBox(), label="Call and &voicemail sounds:")
        self.call_pack_choice = wx.Choice(sound_box.GetStaticBox(), choices=["Same as sound pack"] + [p for p in sound_packs if p != "none"], name="Call and voicemail sounds")
        current_call_pack = str(self.config.get('call_soundpack', 'flexpbx') or 'flexpbx')
        if current_call_pack in ("same", "") or not self.call_pack_choice.SetStringSelection(current_call_pack):
            self.call_pack_choice.SetSelection(0)
        self.auto_play_voice_cb = wx.CheckBox(sound_box.GetStaticBox(), label="Play voice messages automatically in the open chat")
        self.auto_play_voice_cb.SetValue(bool(self.config.get('auto_play_voice_messages', False)))
        self.sound_volume_label = wx.StaticText(sound_box.GetStaticBox(), label="Sound pack volume")
        self.sound_volume_slider = wx.Slider(sound_box.GetStaticBox(), value=int(self.config.get('sound_volume', 80)), minValue=0, maxValue=100, style=wx.SL_HORIZONTAL | wx.SL_LABELS)

        self.call_in_label = wx.StaticText(call_audio_box.GetStaticBox(), label="Call input volume")
        self.call_input_slider = wx.Slider(call_audio_box.GetStaticBox(), value=int(self.config.get('call_input_volume', 80)), minValue=0, maxValue=100, style=wx.SL_HORIZONTAL | wx.SL_LABELS)
        self.call_out_label = wx.StaticText(call_audio_box.GetStaticBox(), label="Call output volume")
        self.call_output_slider = wx.Slider(call_audio_box.GetStaticBox(), value=int(self.config.get('call_output_volume', 80)), minValue=0, maxValue=100, style=wx.SL_HORIZONTAL | wx.SL_LABELS)
        self.call_input_devices = [(None, "System default microphone")]
        self.call_output_devices = [(None, "System default speakers")]
        if sounddevice is not None:
            try:
                for index, device in enumerate(sounddevice.query_devices()):
                    if int(device.get("max_input_channels", 0)) > 0: self.call_input_devices.append((index, str(device.get("name", index))))
                    if int(device.get("max_output_channels", 0)) > 0: self.call_output_devices.append((index, str(device.get("name", index))))
            except Exception:
                pass
        self.call_input_device_label = wx.StaticText(call_audio_box.GetStaticBox(), label="Microphone device:")
        self.call_input_device_choice = wx.Choice(call_audio_box.GetStaticBox(), choices=[item[1] for item in self.call_input_devices])
        self.call_output_device_label = wx.StaticText(call_audio_box.GetStaticBox(), label="Speaker device:")
        self.call_output_device_choice = wx.Choice(call_audio_box.GetStaticBox(), choices=[item[1] for item in self.call_output_devices])
        input_id = self.config.get("call_input_device")
        output_id = self.config.get("call_output_device")
        self.call_input_device_choice.SetSelection(next((i for i, item in enumerate(self.call_input_devices) if item[0] == input_id), 0))
        self.call_output_device_choice.SetSelection(next((i for i, item in enumerate(self.call_output_devices) if item[0] == output_id), 0))
        self.auto_open_files_cb = wx.CheckBox(accessibility_box.GetStaticBox(), label="Auto-open received files after save")
        self.auto_open_files_cb.SetValue(bool(self.config.get('auto_open_received_files', True)))
        self.read_aloud_cb = wx.CheckBox(accessibility_box.GetStaticBox(), label="Read incoming chat messages aloud")
        self.read_aloud_cb.SetValue(bool(self.config.get('read_messages_aloud', False)))
        self.interrupt_speech_cb = wx.CheckBox(accessibility_box.GetStaticBox(), label="Interrupt speech when new messages are read aloud")
        self.interrupt_speech_cb.SetValue(bool(self.config.get('interrupt_speech', True)))
        self.global_chat_logging_cb = wx.CheckBox(accessibility_box.GetStaticBox(), label="Save chat history by default")
        self.global_chat_logging_cb.SetValue(bool(self.config.get('save_chat_history_default', False)))
        self.show_main_actions_cb = wx.CheckBox(accessibility_box.GetStaticBox(), label="Show action buttons in main window")
        self.show_main_actions_cb.SetValue(bool(self.config.get('show_main_action_buttons', True)))
        self.typing_indicator_cb = wx.CheckBox(accessibility_box.GetStaticBox(), label="Show typing indicators")
        self.typing_indicator_cb.SetValue(bool(self.config.get('typing_indicators', True)))
        self.announce_typing_cb = wx.CheckBox(accessibility_box.GetStaticBox(), label="Announce typing start/stop")
        self.announce_typing_cb.SetValue(bool(self.config.get('announce_typing', True)))
        self.prefer_display_names_cb = wx.CheckBox(accessibility_box.GetStaticBox(), label="Prefer contact display names in chat and contacts")
        self.prefer_display_names_cb.SetValue(bool(self.config.get('prefer_contact_display_names', False)))
        self.notify_other_device_login_cb = wx.CheckBox(
            accessibility_box.GetStaticBox(),
            label="Notify me when this account signs in from another device",
        )
        self.notify_other_device_login_cb.SetValue(bool(self.config.get('notify_on_other_device_login', False)))
        session_row = wx.BoxSizer(wx.HORIZONTAL)
        session_row.Add(wx.StaticText(accessibility_box.GetStaticBox(), label="Keep this device authenticated for:"), 0, wx.ALIGN_CENTER_VERTICAL | wx.RIGHT, 6)
        self.session_duration_choice = wx.Choice(accessibility_box.GetStaticBox(), choices=["One hour", "One day", "One week", "One month", "One year", "Forever"])
        duration_values = ['hour', 'day', 'week', 'month', 'year', 'forever']
        self.session_duration_choice.SetSelection(duration_values.index(self.config.get('session_duration', 'month')) if self.config.get('session_duration', 'month') in duration_values else 3)
        session_row.Add(self.session_duration_choice, 1, wx.EXPAND)
        incoming_row = wx.BoxSizer(wx.HORIZONTAL)
        incoming_row.Add(wx.StaticText(accessibility_box.GetStaticBox(), label="Incoming message behavior:"), 0, wx.ALIGN_CENTER_VERTICAL | wx.RIGHT, 6)
        self.incoming_behavior_choice = wx.Choice(accessibility_box.GetStaticBox(), choices=[
            "Pop up chat window automatically",
            "Show notification with username",
            "Do nothing",
            "Play sound only",
            "Stay silent and update unread count only",
        ])
        incoming_val = str(self.config.get('incoming_message_behavior', 'silent_count') or 'silent_count').strip().lower()
        incoming_idx_map = {'popup': 0, 'notify': 1, 'do_nothing': 2, 'play_sound': 3, 'silent_count': 4}
        self.incoming_behavior_choice.SetSelection(incoming_idx_map.get(incoming_val, 4))
        incoming_row.Add(self.incoming_behavior_choice, 1, wx.EXPAND)
        timestamp_row = wx.BoxSizer(wx.HORIZONTAL)
        timestamp_row.Add(wx.StaticText(accessibility_box.GetStaticBox(), label="Message timestamps:"), 0, wx.ALIGN_CENTER_VERTICAL | wx.RIGHT, 6)
        self.timestamp_mode_choice = wx.Choice(accessibility_box.GetStaticBox(), choices=[
            "Show at start of message",
            "Append at end of message",
            "Hide timestamps",
        ])
        ts_val = str(self.config.get('message_timestamp_mode', 'start') or 'start').strip().lower()
        ts_idx_map = {'start': 0, 'end': 1, 'off': 2}
        self.timestamp_mode_choice.SetSelection(ts_idx_map.get(ts_val, 0))
        timestamp_row.Add(self.timestamp_mode_choice, 1, wx.EXPAND)
        date_group_row = wx.BoxSizer(wx.HORIZONTAL)
        date_group_row.Add(wx.StaticText(accessibility_box.GetStaticBox(), label="Saved message date order:"), 0, wx.ALIGN_CENTER_VERTICAL | wx.RIGHT, 6)
        self.saved_date_order_choice = wx.Choice(accessibility_box.GetStaticBox(), choices=[
            "Month Day Year (MDY)",
            "Day Month Year (DMY)",
            "Year Month Day (YMD)",
            "Year Day Month (YDM)",
        ])
        order_val = str(self.config.get('saved_history_date_order', 'mdy') or 'mdy').strip().lower()
        order_idx_map = {'mdy': 0, 'dmy': 1, 'ymd': 2, 'ydm': 3}
        self.saved_date_order_choice.SetSelection(order_idx_map.get(order_val, 0))
        date_group_row.Add(self.saved_date_order_choice, 1, wx.EXPAND)
        enter_row = wx.BoxSizer(wx.HORIZONTAL)
        enter_row.Add(wx.StaticText(accessibility_box.GetStaticBox(), label="Enter key action:"), 0, wx.ALIGN_CENTER_VERTICAL | wx.RIGHT, 6)
        self.enter_action_choice = wx.Choice(accessibility_box.GetStaticBox(), choices=[
            "Do nothing (default)",
            "Send message",
            "Place call",
        ])
        enter_val = str(self.config.get('enter_key_action', 'none') or 'none')
        self.enter_action_choice.SetSelection(0 if enter_val == 'none' else (1 if enter_val == 'send' else 2))
        enter_row.Add(self.enter_action_choice, 1, wx.EXPAND)
        escape_row = wx.BoxSizer(wx.HORIZONTAL)
        escape_row.Add(wx.StaticText(accessibility_box.GetStaticBox(), label="Escape in main window:"), 0, wx.ALIGN_CENTER_VERTICAL | wx.RIGHT, 6)
        self.escape_action_choice = wx.Choice(accessibility_box.GetStaticBox(), choices=[
            "Do nothing (recommended)",
            "Minimize to tray/status menu",
            "Quit app",
        ])
        esc_val = str(self.config.get('escape_main_action', 'none') or 'none')
        self.escape_action_choice.SetSelection(0 if esc_val == 'none' else (1 if esc_val == 'minimize' else 2))
        escape_row.Add(self.escape_action_choice, 1, wx.EXPAND)
        self.double_escape_chat_cb = wx.CheckBox(accessibility_box.GetStaticBox(), label="Require double Escape to dismiss chat windows")
        self.double_escape_chat_cb.SetValue(bool(self.config.get('double_escape_to_close_chat', True)))
        self.chat_tabs_cb = wx.CheckBox(accessibility_box.GetStaticBox(), label="Open chats in tabs in one chat window")
        self.chat_tabs_cb.SetValue(bool(self.config.get('chat_tabs', True)))
        self.chat_tabs_cb.SetToolTip("Each conversation is a tab in one Chats window. Ctrl+Tab switches, Ctrl+W closes a tab. Applies to chats opened after saving.")
        self.keep_contact_list_cb = wx.CheckBox(accessibility_box.GetStaticBox(), label="Keep the contact list open when a chat opens")
        self.keep_contact_list_cb.SetValue(bool(self.config.get('keep_contact_list_open', True)))
        self.keep_contact_list_cb.SetToolTip("Chat windows get their own taskbar and Alt+Tab entry, so the contact list stays available. Ctrl+0 in a chat returns to it.")
        self.delete_for_everyone_cb = wx.CheckBox(accessibility_box.GetStaticBox(), label="Delete messages for everyone")
        self.delete_for_everyone_cb.SetValue(bool(self.config.get('delete_messages_for_everyone', True)))
        self.delete_for_everyone_cb.SetToolTip("When you delete a message you sent (or any message, if you are an admin), it is removed for both people in the conversation.")
        self.delete_attached_files_cb = wx.CheckBox(accessibility_box.GetStaticBox(), label="Also delete attached files when deleting a message")
        self.delete_attached_files_cb.SetValue(bool(self.config.get('delete_attached_files_with_message', False)))
        self.delete_attached_files_cb.SetToolTip("Files you received with that message are moved to the Recycle Bin on this computer.")

        cfg = load_client_config()
        self.client_conf_path = get_user_client_conf_path()
        self.admin_hint = wx.StaticText(
            admin_box.GetStaticBox(),
            label=f"Advanced connection and update settings are saved to your user profile at {self.client_conf_path}."
        )
        self.admin_hint.Wrap(500)
        host_row = wx.BoxSizer(wx.HORIZONTAL)
        host_row.Add(wx.StaticText(admin_box.GetStaticBox(), label="Server host:"), 0, wx.ALIGN_CENTER_VERTICAL | wx.RIGHT, 6)
        self.admin_host_txt = wx.TextCtrl(admin_box.GetStaticBox(), value=cfg.get('server', 'host', fallback='msg.thecubed.cc'))
        host_row.Add(self.admin_host_txt, 1, wx.EXPAND)
        port_row = wx.BoxSizer(wx.HORIZONTAL)
        port_row.Add(wx.StaticText(admin_box.GetStaticBox(), label="Server port:"), 0, wx.ALIGN_CENTER_VERTICAL | wx.RIGHT, 6)
        self.admin_port_txt = wx.TextCtrl(admin_box.GetStaticBox(), value=str(cfg.getint('server', 'port', fallback=2005)))
        port_row.Add(self.admin_port_txt, 1, wx.EXPAND)
        cafile_row = wx.BoxSizer(wx.HORIZONTAL)
        cafile_row.Add(wx.StaticText(admin_box.GetStaticBox(), label="TLS CA file:"), 0, wx.ALIGN_CENTER_VERTICAL | wx.RIGHT, 6)
        self.admin_cafile_txt = wx.TextCtrl(admin_box.GetStaticBox(), value=cfg.get('server', 'cafile', fallback=''))
        cafile_row.Add(self.admin_cafile_txt, 1, wx.EXPAND)
        feed_row = wx.BoxSizer(wx.HORIZONTAL)
        feed_row.Add(wx.StaticText(admin_box.GetStaticBox(), label="Update feed URL:"), 0, wx.ALIGN_CENTER_VERTICAL | wx.RIGHT, 6)
        self.admin_feed_txt = wx.TextCtrl(admin_box.GetStaticBox(), value=cfg.get('updates', 'feed_url', fallback=''))
        feed_row.Add(self.admin_feed_txt, 1, wx.EXPAND)
        pref_row = wx.BoxSizer(wx.HORIZONTAL)
        pref_row.Add(wx.StaticText(admin_box.GetStaticBox(), label="Preferred repo:"), 0, wx.ALIGN_CENTER_VERTICAL | wx.RIGHT, 6)
        self.admin_pref_repo_txt = wx.TextCtrl(admin_box.GetStaticBox(), value=cfg.get('updates', 'preferred_repo', fallback='Raywonder/ThriveMessenger'))
        pref_row.Add(self.admin_pref_repo_txt, 1, wx.EXPAND)
        fallback_row = wx.BoxSizer(wx.HORIZONTAL)
        fallback_row.Add(wx.StaticText(admin_box.GetStaticBox(), label="Fallback repos:"), 0, wx.ALIGN_CENTER_VERTICAL | wx.RIGHT, 6)
        self.admin_fallback_txt = wx.TextCtrl(admin_box.GetStaticBox(), value=cfg.get('updates', 'fallback_repos', fallback=''))
        fallback_row.Add(self.admin_fallback_txt, 1, wx.EXPAND)
        self.restart_after_save_cb = wx.CheckBox(admin_box.GetStaticBox(), label="Restart server after saving admin settings")
        self.restart_after_save_cb.SetValue(False)
        restart_row = wx.BoxSizer(wx.HORIZONTAL)
        restart_row.Add(wx.StaticText(admin_box.GetStaticBox(), label="Restart delay (seconds):"), 0, wx.ALIGN_CENTER_VERTICAL | wx.RIGHT, 6)
        self.restart_delay_txt = wx.TextCtrl(admin_box.GetStaticBox(), value="10")
        restart_row.Add(self.restart_delay_txt, 1, wx.EXPAND)
        self.btn_open_admin_console = wx.Button(admin_box.GetStaticBox(), label="Open Server Command Console")
        self.btn_open_admin_console.Bind(wx.EVT_BUTTON, self.on_open_admin_console)
        self.btn_open_bot_rules = wx.Button(admin_box.GetStaticBox(), label="Open Bot Rules Manager")
        self.btn_open_bot_rules.Bind(wx.EVT_BUTTON, self.on_open_bot_rules)
        self.btn_open_group_policy = wx.Button(admin_box.GetStaticBox(), label="Open Group Policy Manager")
        self.btn_open_group_policy.Bind(wx.EVT_BUTTON, self.on_open_group_policy)
        self.btn_open_modules = wx.Button(admin_box.GetStaticBox(), label="Manage Server Modules")
        self.btn_open_modules.Bind(wx.EVT_BUTTON, self.on_open_modules)
        self.bot_mesh_hint = wx.StaticText(admin_box.GetStaticBox(), label="Bot mesh lets local or remote bot accounts delegate work, monitor moderation events, and relay temp files through the server.")
        self.bot_mesh_hint.Wrap(500)
        bot_agent_row = wx.BoxSizer(wx.HORIZONTAL)
        bot_agent_row.Add(wx.StaticText(admin_box.GetStaticBox(), label="Bot agent user:"), 0, wx.ALIGN_CENTER_VERTICAL | wx.RIGHT, 6)
        self.bot_agent_user_txt = wx.TextCtrl(admin_box.GetStaticBox(), value=str(self.config.get('bot_mesh_agent_user', '') or ''))
        self.bot_agent_user_txt.SetName("Bot agent user")
        self.bot_agent_user_txt.SetToolTip("Bot account username that will connect to this server.")
        bot_agent_row.Add(self.bot_agent_user_txt, 1, wx.EXPAND)
        backend_row = wx.BoxSizer(wx.HORIZONTAL)
        backend_row.Add(wx.StaticText(admin_box.GetStaticBox(), label="Agent backend:"), 0, wx.ALIGN_CENTER_VERTICAL | wx.RIGHT, 6)
        self.bot_agent_backend_choice = wx.Choice(admin_box.GetStaticBox(), choices=["ollama", "auto", "command", "echo"])
        self.bot_agent_backend_choice.SetStringSelection(str(self.config.get('bot_mesh_agent_backend', 'ollama') or 'ollama'))
        self.bot_agent_backend_choice.SetName("Agent backend")
        self.bot_agent_backend_choice.SetToolTip("Local backend used by the bot mesh agent.")
        backend_row.Add(self.bot_agent_backend_choice, 1, wx.EXPAND)
        auth_row = wx.BoxSizer(wx.HORIZONTAL)
        auth_row.Add(wx.StaticText(admin_box.GetStaticBox(), label="Auth type:"), 0, wx.ALIGN_CENTER_VERTICAL | wx.RIGHT, 6)
        self.bot_agent_auth_choice = wx.Choice(admin_box.GetStaticBox(), choices=["codex", "opencode", "openclaw", "claude", "ollama", "assistant"])
        self.bot_agent_auth_choice.SetStringSelection(str(self.config.get('bot_mesh_agent_auth_type', 'codex') or 'codex'))
        self.bot_agent_auth_choice.SetName("Auth type")
        self.bot_agent_auth_choice.SetToolTip("Identity label advertised by the bot mesh agent.")
        auth_row.Add(self.bot_agent_auth_choice, 1, wx.EXPAND)
        delegate_row = wx.BoxSizer(wx.HORIZONTAL)
        delegate_row.Add(wx.StaticText(admin_box.GetStaticBox(), label="Delegate to:"), 0, wx.ALIGN_CENTER_VERTICAL | wx.RIGHT, 6)
        self.bot_agent_delegate_txt = wx.TextCtrl(admin_box.GetStaticBox(), value=str(self.config.get('bot_mesh_agent_delegate_to', 'helper-bot') or 'helper-bot'))
        self.bot_agent_delegate_txt.SetName("Delegate to")
        self.bot_agent_delegate_txt.SetToolTip("Optional bot username that receives delegated work if this agent cannot handle it.")
        delegate_row.Add(self.bot_agent_delegate_txt, 1, wx.EXPAND)
        notify_row = wx.BoxSizer(wx.HORIZONTAL)
        notify_row.Add(wx.StaticText(admin_box.GetStaticBox(), label="Notify user:"), 0, wx.ALIGN_CENTER_VERTICAL | wx.RIGHT, 6)
        self.bot_agent_notify_txt = wx.TextCtrl(admin_box.GetStaticBox(), value=str(self.config.get('bot_mesh_agent_notify_user', '') or ''))
        self.bot_agent_notify_txt.SetName("Notify user")
        self.bot_agent_notify_txt.SetToolTip("Optional username that receives moderation summaries from this bot.")
        notify_row.Add(self.bot_agent_notify_txt, 1, wx.EXPAND)
        host_label_row = wx.BoxSizer(wx.HORIZONTAL)
        host_label_row.Add(wx.StaticText(admin_box.GetStaticBox(), label="Host label:"), 0, wx.ALIGN_CENTER_VERTICAL | wx.RIGHT, 6)
        self.bot_agent_host_label_txt = wx.TextCtrl(admin_box.GetStaticBox(), value=str(self.config.get('bot_mesh_agent_host_label', platform.node() or 'local') or (platform.node() or 'local')))
        self.bot_agent_host_label_txt.SetName("Host label")
        self.bot_agent_host_label_txt.SetToolTip("Short label for the computer or server running the bot agent.")
        host_label_row.Add(self.bot_agent_host_label_txt, 1, wx.EXPAND)
        self.bot_agent_enabled_cb = wx.CheckBox(admin_box.GetStaticBox(), label="Enable local background bot agent profile")
        self.bot_agent_enabled_cb.SetValue(bool(self.config.get('bot_mesh_agent_enabled', False)))
        self.bot_agent_moderation_cb = wx.CheckBox(admin_box.GetStaticBox(), label="Enable moderation watch for guest logins, spam, and file offers")
        self.bot_agent_moderation_cb.SetValue(bool(self.config.get('bot_mesh_agent_moderation', True)))
        self.btn_copy_bot_agent_cmd = wx.Button(admin_box.GetStaticBox(), label="Copy Bot Agent Command")
        self.btn_copy_bot_agent_cmd.Bind(wx.EVT_BUTTON, self.on_copy_bot_agent_command)
        self.btn_open_bot_agent_guide = wx.Button(admin_box.GetStaticBox(), label="Open Bot Mesh Agent Guide")
        self.btn_open_bot_agent_guide.Bind(wx.EVT_BUTTON, self.on_open_bot_agent_guide)
        self.allow_cross_server_dm_cb = wx.CheckBox(admin_box.GetStaticBox(), label="Allow direct messaging from Directory to users on other configured servers")
        self.allow_cross_server_dm_cb.SetValue(bool(self.config.get('allow_cross_server_directory_message', True)))
        edit_window_row = wx.BoxSizer(wx.HORIZONTAL)
        edit_window_row.Add(wx.StaticText(admin_box.GetStaticBox(), label="Edit window (seconds):"), 0, wx.ALIGN_CENTER_VERTICAL | wx.RIGHT, 6)
        self.message_edit_window_txt = wx.TextCtrl(admin_box.GetStaticBox(), value=str(self.config.get('message_edit_window_seconds', 300)))
        edit_window_row.Add(self.message_edit_window_txt, 1, wx.EXPAND)
        undo_window_row = wx.BoxSizer(wx.HORIZONTAL)
        undo_window_row.Add(wx.StaticText(admin_box.GetStaticBox(), label="Undo delete window (seconds):"), 0, wx.ALIGN_CENTER_VERTICAL | wx.RIGHT, 6)
        self.message_undo_window_txt = wx.TextCtrl(admin_box.GetStaticBox(), value=str(self.config.get('message_undo_window_seconds', 15)))
        undo_window_row.Add(self.message_undo_window_txt, 1, wx.EXPAND)
        sound_box.Add(self.choice, 0, wx.EXPAND | wx.ALL, 5)
        sound_box.Add(self.default_soundpack_label, 0, wx.LEFT | wx.RIGHT | wx.BOTTOM, 5)
        sound_box.Add(self.set_selected_default_cb, 0, wx.LEFT | wx.RIGHT | wx.BOTTOM, 5)
        sound_box.Add(self.call_pack_label, 0, wx.LEFT | wx.RIGHT | wx.TOP, 5)
        sound_box.Add(self.call_pack_choice, 0, wx.EXPAND | wx.LEFT | wx.RIGHT | wx.BOTTOM, 5)
        sound_box.Add(self.auto_play_voice_cb, 0, wx.ALL, 5)
        sound_box.Add(self.sound_volume_label, 0, wx.LEFT | wx.RIGHT | wx.TOP, 5)
        sound_box.Add(self.sound_volume_slider, 0, wx.EXPAND | wx.LEFT | wx.RIGHT | wx.BOTTOM, 5)
        call_audio_box.Add(self.call_in_label, 0, wx.LEFT | wx.RIGHT | wx.TOP, 5)
        call_audio_box.Add(self.call_input_slider, 0, wx.EXPAND | wx.LEFT | wx.RIGHT | wx.BOTTOM, 5)
        call_audio_box.Add(self.call_out_label, 0, wx.LEFT | wx.RIGHT | wx.TOP, 5)
        call_audio_box.Add(self.call_output_slider, 0, wx.EXPAND | wx.LEFT | wx.RIGHT | wx.BOTTOM, 5)
        call_audio_box.Add(self.call_input_device_label, 0, wx.LEFT | wx.RIGHT | wx.TOP, 5)
        call_audio_box.Add(self.call_input_device_choice, 0, wx.EXPAND | wx.LEFT | wx.RIGHT | wx.BOTTOM, 5)
        call_audio_box.Add(self.call_output_device_label, 0, wx.LEFT | wx.RIGHT | wx.TOP, 5)
        call_audio_box.Add(self.call_output_device_choice, 0, wx.EXPAND | wx.LEFT | wx.RIGHT | wx.BOTTOM, 5)
        accessibility_box.Add(self.auto_open_files_cb, 0, wx.ALL, 5)
        accessibility_box.Add(self.read_aloud_cb, 0, wx.ALL, 5)
        accessibility_box.Add(self.interrupt_speech_cb, 0, wx.ALL, 5)
        accessibility_box.Add(self.global_chat_logging_cb, 0, wx.ALL, 5)
        accessibility_box.Add(self.show_main_actions_cb, 0, wx.ALL, 5)
        accessibility_box.Add(self.typing_indicator_cb, 0, wx.ALL, 5)
        accessibility_box.Add(self.announce_typing_cb, 0, wx.ALL, 5)
        accessibility_box.Add(self.prefer_display_names_cb, 0, wx.ALL, 5)
        accessibility_box.Add(self.notify_other_device_login_cb, 0, wx.ALL, 5)
        accessibility_box.Add(session_row, 0, wx.EXPAND | wx.ALL, 5)
        accessibility_box.Add(incoming_row, 0, wx.EXPAND | wx.ALL, 5)
        accessibility_box.Add(timestamp_row, 0, wx.EXPAND | wx.ALL, 5)
        accessibility_box.Add(date_group_row, 0, wx.EXPAND | wx.ALL, 5)
        accessibility_box.Add(enter_row, 0, wx.EXPAND | wx.ALL, 5)
        accessibility_box.Add(escape_row, 0, wx.EXPAND | wx.ALL, 5)
        accessibility_box.Add(self.double_escape_chat_cb, 0, wx.ALL, 5)
        accessibility_box.Add(self.chat_tabs_cb, 0, wx.ALL, 5)
        accessibility_box.Add(self.keep_contact_list_cb, 0, wx.ALL, 5)
        accessibility_box.Add(self.delete_for_everyone_cb, 0, wx.ALL, 5)
        accessibility_box.Add(self.delete_attached_files_cb, 0, wx.ALL, 5)
        audio_sizer = wx.BoxSizer(wx.VERTICAL)
        audio_sizer.Add(sound_box, 0, wx.EXPAND | wx.ALL, 8)
        audio_sizer.Add(call_audio_box, 0, wx.EXPAND | wx.LEFT | wx.RIGHT | wx.BOTTOM, 8)
        tab_audio.SetSizer(audio_sizer)

        general_sizer = wx.BoxSizer(wx.VERTICAL)
        general_sizer.Add(accessibility_box, 0, wx.EXPAND | wx.ALL, 8)
        self.btn_chpass = wx.Button(tab_general, label="C&hange Password...")
        self.btn_chpass.Bind(wx.EVT_BUTTON, self.on_change_password)
        general_sizer.Add(self.btn_chpass, 0, wx.EXPAND | wx.LEFT | wx.RIGHT | wx.BOTTOM, 10)
        self.btn_authenticated_devices = wx.Button(tab_general, label="Manage &Authenticated Devices...")
        self.btn_authenticated_devices.SetToolTip("View all authenticated locations and devices and sign out individual devices.")
        self.btn_authenticated_devices.Bind(wx.EVT_BUTTON, lambda _: self.GetParent().show_authenticated_devices())
        general_sizer.Add(self.btn_authenticated_devices, 0, wx.EXPAND | wx.LEFT | wx.RIGHT | wx.BOTTOM, 10)
        self.btn_delete_account = wx.Button(tab_general, label="&Delete Account from This Server...")
        self.btn_delete_account.SetToolTip("Permanently delete this account and unlink its connected identities from the current Thrive server.")
        self.btn_delete_account.Bind(wx.EVT_BUTTON, self.on_delete_account)
        general_sizer.Add(self.btn_delete_account, 0, wx.EXPAND | wx.LEFT | wx.RIGHT | wx.BOTTOM, 10)
        tab_general.SetSizer(general_sizer)

        admin_box.Add(self.admin_hint, 0, wx.EXPAND | wx.ALL, 5)
        admin_box.Add(host_row, 0, wx.EXPAND | wx.LEFT | wx.RIGHT | wx.BOTTOM, 5)
        admin_box.Add(port_row, 0, wx.EXPAND | wx.LEFT | wx.RIGHT | wx.BOTTOM, 5)
        admin_box.Add(cafile_row, 0, wx.EXPAND | wx.LEFT | wx.RIGHT | wx.BOTTOM, 5)
        admin_box.Add(feed_row, 0, wx.EXPAND | wx.LEFT | wx.RIGHT | wx.BOTTOM, 5)
        admin_box.Add(pref_row, 0, wx.EXPAND | wx.LEFT | wx.RIGHT | wx.BOTTOM, 5)
        admin_box.Add(fallback_row, 0, wx.EXPAND | wx.LEFT | wx.RIGHT | wx.BOTTOM, 5)
        admin_box.Add(self.restart_after_save_cb, 0, wx.EXPAND | wx.LEFT | wx.RIGHT | wx.BOTTOM, 5)
        admin_box.Add(restart_row, 0, wx.EXPAND | wx.LEFT | wx.RIGHT | wx.BOTTOM, 5)
        admin_box.Add(edit_window_row, 0, wx.EXPAND | wx.LEFT | wx.RIGHT | wx.BOTTOM, 5)
        admin_box.Add(undo_window_row, 0, wx.EXPAND | wx.LEFT | wx.RIGHT | wx.BOTTOM, 5)
        admin_box.Add(self.allow_cross_server_dm_cb, 0, wx.EXPAND | wx.LEFT | wx.RIGHT | wx.BOTTOM, 5)
        admin_box.Add(self.bot_mesh_hint, 0, wx.EXPAND | wx.LEFT | wx.RIGHT | wx.BOTTOM, 5)
        admin_box.Add(bot_agent_row, 0, wx.EXPAND | wx.LEFT | wx.RIGHT | wx.BOTTOM, 5)
        admin_box.Add(backend_row, 0, wx.EXPAND | wx.LEFT | wx.RIGHT | wx.BOTTOM, 5)
        admin_box.Add(auth_row, 0, wx.EXPAND | wx.LEFT | wx.RIGHT | wx.BOTTOM, 5)
        admin_box.Add(delegate_row, 0, wx.EXPAND | wx.LEFT | wx.RIGHT | wx.BOTTOM, 5)
        admin_box.Add(notify_row, 0, wx.EXPAND | wx.LEFT | wx.RIGHT | wx.BOTTOM, 5)
        admin_box.Add(host_label_row, 0, wx.EXPAND | wx.LEFT | wx.RIGHT | wx.BOTTOM, 5)
        admin_box.Add(self.bot_agent_enabled_cb, 0, wx.EXPAND | wx.LEFT | wx.RIGHT | wx.BOTTOM, 5)
        admin_box.Add(self.bot_agent_moderation_cb, 0, wx.EXPAND | wx.LEFT | wx.RIGHT | wx.BOTTOM, 5)
        admin_box.Add(self.btn_copy_bot_agent_cmd, 0, wx.EXPAND | wx.LEFT | wx.RIGHT | wx.BOTTOM, 5)
        admin_box.Add(self.btn_open_bot_agent_guide, 0, wx.EXPAND | wx.LEFT | wx.RIGHT | wx.BOTTOM, 5)
        admin_box.Add(self.btn_open_admin_console, 0, wx.EXPAND | wx.ALL, 5)
        admin_box.Add(self.btn_open_bot_rules, 0, wx.EXPAND | wx.LEFT | wx.RIGHT | wx.BOTTOM, 5)
        admin_box.Add(self.btn_open_group_policy, 0, wx.EXPAND | wx.LEFT | wx.RIGHT | wx.BOTTOM, 5)
        admin_box.Add(self.btn_open_modules, 0, wx.EXPAND | wx.LEFT | wx.RIGHT | wx.BOTTOM, 5)
        admin_sizer = wx.BoxSizer(wx.VERTICAL)
        admin_sizer.Add(admin_box, 1, wx.EXPAND | wx.ALL, 8)
        tab_admin.SetSizer(admin_sizer)

        main_sizer.Add(notebook, 1, wx.EXPAND | wx.ALL, 6)
        btn_sizer = wx.StdDialogButtonSizer()
        ok_btn = wx.Button(panel, wx.ID_OK, label="OK"); ok_btn.SetDefault(); cancel_btn = wx.Button(panel, wx.ID_CANCEL)
        self.apply_btn = wx.Button(panel, wx.ID_APPLY, label="&Apply")
        self.apply_btn.SetToolTip("Save these settings and keep Settings open.")
        self.apply_btn.Bind(wx.EVT_BUTTON, self.on_apply)
        self.SetEscapeId(wx.ID_CANCEL)
        
        if dark_mode_on:
            self.choice.SetBackgroundColour(dark_color); self.choice.SetForegroundColour(light_text_color)
            self.default_soundpack_label.SetForegroundColour(light_text_color)
            self.set_selected_default_cb.SetForegroundColour(light_text_color)
            self.sound_volume_label.SetForegroundColour(light_text_color)
            self.call_in_label.SetForegroundColour(light_text_color)
            self.call_out_label.SetForegroundColour(light_text_color)
            self.admin_hint.SetForegroundColour(light_text_color)
            self.bot_mesh_hint.SetForegroundColour(light_text_color)
            for cb in [self.auto_open_files_cb, self.read_aloud_cb, self.interrupt_speech_cb, self.global_chat_logging_cb, self.show_main_actions_cb, self.typing_indicator_cb, self.announce_typing_cb, self.prefer_display_names_cb, self.double_escape_chat_cb, self.chat_tabs_cb, self.keep_contact_list_cb, self.delete_for_everyone_cb, self.delete_attached_files_cb]:
                cb.SetForegroundColour(light_text_color)
            self.restart_after_save_cb.SetForegroundColour(light_text_color)
            self.allow_cross_server_dm_cb.SetForegroundColour(light_text_color)
            self.bot_agent_enabled_cb.SetForegroundColour(light_text_color)
            self.bot_agent_moderation_cb.SetForegroundColour(light_text_color)
            for ctrl in [self.admin_host_txt, self.admin_port_txt, self.admin_cafile_txt, self.admin_feed_txt, self.admin_pref_repo_txt, self.admin_fallback_txt, self.message_edit_window_txt, self.message_undo_window_txt, self.bot_agent_user_txt, self.bot_agent_delegate_txt, self.bot_agent_notify_txt, self.bot_agent_host_label_txt]:
                ctrl.SetBackgroundColour(dark_color); ctrl.SetForegroundColour(light_text_color)
            self.restart_delay_txt.SetBackgroundColour(dark_color); self.restart_delay_txt.SetForegroundColour(light_text_color)
            self.enter_action_choice.SetBackgroundColour(dark_color); self.enter_action_choice.SetForegroundColour(light_text_color)
            self.escape_action_choice.SetBackgroundColour(dark_color); self.escape_action_choice.SetForegroundColour(light_text_color)
            self.incoming_behavior_choice.SetBackgroundColour(dark_color); self.incoming_behavior_choice.SetForegroundColour(light_text_color)
            self.timestamp_mode_choice.SetBackgroundColour(dark_color); self.timestamp_mode_choice.SetForegroundColour(light_text_color)
            self.saved_date_order_choice.SetBackgroundColour(dark_color); self.saved_date_order_choice.SetForegroundColour(light_text_color)
            self.bot_agent_backend_choice.SetBackgroundColour(dark_color); self.bot_agent_backend_choice.SetForegroundColour(light_text_color)
            self.bot_agent_auth_choice.SetBackgroundColour(dark_color); self.bot_agent_auth_choice.SetForegroundColour(light_text_color)
            self.btn_chpass.SetBackgroundColour(dark_color); self.btn_chpass.SetForegroundColour(light_text_color)
            self.btn_delete_account.SetBackgroundColour(dark_color); self.btn_delete_account.SetForegroundColour(light_text_color)
            self.btn_open_admin_console.SetBackgroundColour(dark_color); self.btn_open_admin_console.SetForegroundColour(light_text_color)
            self.btn_open_bot_rules.SetBackgroundColour(dark_color); self.btn_open_bot_rules.SetForegroundColour(light_text_color)
            self.btn_open_group_policy.SetBackgroundColour(dark_color); self.btn_open_group_policy.SetForegroundColour(light_text_color)
            self.btn_copy_bot_agent_cmd.SetBackgroundColour(dark_color); self.btn_copy_bot_agent_cmd.SetForegroundColour(light_text_color)
            self.btn_open_bot_agent_guide.SetBackgroundColour(dark_color); self.btn_open_bot_agent_guide.SetForegroundColour(light_text_color)
            ok_btn.SetBackgroundColour(dark_color); ok_btn.SetForegroundColour(light_text_color)
            cancel_btn.SetBackgroundColour(dark_color); cancel_btn.SetForegroundColour(light_text_color)
            
        btn_sizer.AddButton(ok_btn); btn_sizer.AddButton(self.apply_btn); btn_sizer.AddButton(cancel_btn); btn_sizer.Realize(); main_sizer.Add(btn_sizer, 0, wx.ALIGN_CENTER | wx.ALL, 10); panel.SetSizer(main_sizer)
        apply_toggle_semantics(self)
        self.on_sound_pack_changed(None)
    def on_sound_pack_changed(self, _):
        selected = self.choice.GetStringSelection().strip().lower()
        self.set_selected_default_cb.Enable(selected not in ("none", "default"))
    def on_key(self, event):
        if event.GetKeyCode() == wx.WXK_F1:
            open_help_docs_for_context("settings", self)
            return
        event.Skip()
    def on_change_password(self, _):
        with ChangePasswordDialog(self) as dlg:
            if dlg.ShowModal() == wx.ID_OK:
                cur = dlg.cur_ctrl.GetValue(); new = dlg.new_ctrl.GetValue()
                frame = self.GetParent()
                try: frame.sock.sendall((json.dumps({"action": "change_password", "current_pass": cur, "new_pass": new}) + "\n").encode())
                except Exception as e: wx.MessageBox(f"Failed to send request: {e}", "Error", wx.ICON_ERROR)
    def on_delete_account(self, _):
        frame = self.GetParent()
        username = str(getattr(frame, "user", "") or "").strip()
        server = normalize_server_entry(getattr(wx.GetApp(), "active_server_entry", SERVER_CONFIG))
        host = server.get("host", "the current server")
        warning = (
            f"This permanently deletes the account '{username}' from {host}, revokes its signed-in devices, "
            "and unlinks connected identities such as Mastodon or WordPress. It does not delete those external accounts.\n\n"
            f"Type {username} to confirm."
        )
        with wx.TextEntryDialog(self, warning, "Permanently Delete Account") as dlg:
            if dlg.ShowModal() != wx.ID_OK:
                return
            confirmation = dlg.GetValue().strip()
        if confirmation.casefold() != username.casefold():
            wx.MessageBox("The username did not match. The account was not deleted.", "Deletion Cancelled", wx.OK | wx.ICON_INFORMATION, self)
            return
        final = wx.MessageBox(
            f"Delete '{username}' permanently from {host}? This cannot be undone.",
            "Final Account Deletion Confirmation",
            wx.YES_NO | wx.NO_DEFAULT | wx.ICON_WARNING,
            self,
        )
        if final != wx.YES:
            return
        try:
            frame.sock.sendall((json.dumps({"action": "delete_account", "confirm_username": confirmation}) + "\n").encode())
            self.EndModal(wx.ID_CANCEL)
        except Exception as e:
            wx.MessageBox(f"Could not request account deletion: {e}", "Account Deletion Failed", wx.OK | wx.ICON_ERROR, self)
    def on_open_admin_console(self, _):
        frame = self.GetParent()
        if frame and hasattr(frame, "on_admin"):
            frame.on_admin(None)
    def on_open_bot_rules(self, _):
        frame = self.GetParent()
        if frame and hasattr(frame, "on_manage_bot_rules"):
            frame.on_manage_bot_rules(None)
    def on_open_group_policy(self, _):
        frame = self.GetParent()
        if frame and hasattr(frame, "on_manage_group_policy"):
            frame.on_manage_group_policy(None)
    def on_open_modules(self, _):
        frame = self.GetParent()
        if frame and hasattr(frame, "on_manage_modules"):
            frame.on_manage_modules(None)
    def build_bot_agent_command(self):
        script_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "scripts", "thrive_bot_mesh_agent.py")
        host = self.admin_host_txt.GetValue().strip() or "msg.thecubed.cc"
        port = self.admin_port_txt.GetValue().strip() or "2005"
        bot_user = self.bot_agent_user_txt.GetValue().strip() or "<bot-user>"
        auth_type = self.bot_agent_auth_choice.GetStringSelection().strip() or "codex"
        backend = self.bot_agent_backend_choice.GetStringSelection().strip() or "ollama"
        delegate_to = self.bot_agent_delegate_txt.GetValue().strip()
        notify_user = self.bot_agent_notify_txt.GetValue().strip()
        host_label = self.bot_agent_host_label_txt.GetValue().strip() or (platform.node() or "local")
        parts = [
            sys.executable,
            script_path,
            "--host", host,
            "--port", port,
            "--user", bot_user,
            "--password", "<bot-password>",
            "--backend", backend,
            "--auth-type", auth_type,
            "--host-label", host_label,
            "--background",
        ]
        cafile = self.admin_cafile_txt.GetValue().strip()
        if cafile:
            parts.extend(["--ssl", "--cafile", cafile])
        if self.bot_agent_moderation_cb.IsChecked():
            parts.append("--moderation")
        if notify_user:
            parts.extend(["--notify-user", notify_user])
        if delegate_to:
            parts.extend(["--delegate-to", delegate_to])
        return subprocess.list2cmdline(parts)
    def on_copy_bot_agent_command(self, _):
        command = self.build_bot_agent_command()
        if wx.TheClipboard.Open():
            wx.TheClipboard.SetData(wx.TextDataObject(command))
            wx.TheClipboard.Close()
        wx.MessageBox("Bot agent command copied to the clipboard.", "Bot Mesh Agent", wx.OK | wx.ICON_INFORMATION, self)
    def on_open_bot_agent_guide(self, _):
        guide = os.path.join(os.path.dirname(os.path.abspath(__file__)), "scripts", "BOT_MESH_AGENT.md")
        try:
            if sys.platform == "win32":
                os.startfile(guide)
            elif sys.platform == "darwin":
                subprocess.Popen(["open", guide])
            else:
                subprocess.Popen(["xdg-open", guide])
        except Exception as e:
            wx.MessageBox(f"Could not open bot mesh guide: {e}", "Bot Mesh Agent", wx.OK | wx.ICON_ERROR, self)
    def apply_admin_config(self):
        cfg = configparser.ConfigParser(interpolation=None)
        cfg.read(get_client_conf_read_paths())
        if not cfg.has_section('server'):
            cfg.add_section('server')
        if not cfg.has_section('updates'):
            cfg.add_section('updates')
        try:
            port = int(self.admin_port_txt.GetValue().strip())
        except Exception:
            return False, "Server port must be a valid number."
        cfg.set('server', 'host', self.admin_host_txt.GetValue().strip())
        cfg.set('server', 'port', str(port))
        cfg.set('server', 'cafile', self.admin_cafile_txt.GetValue().strip())
        cfg.set('updates', 'feed_url', self.admin_feed_txt.GetValue().strip())
        cfg.set('updates', 'preferred_repo', self.admin_pref_repo_txt.GetValue().strip())
        cfg.set('updates', 'fallback_repos', self.admin_fallback_txt.GetValue().strip())
        try:
            os.makedirs(os.path.dirname(self.client_conf_path), exist_ok=True)
            with open(self.client_conf_path, 'w', encoding='utf-8') as f:
                cfg.write(f)
        except Exception as e:
            return False, str(e)
        return True, None
    def on_apply(self, _):
        parent = self.GetParent()
        if parent and hasattr(parent, "apply_settings_dialog"):
            parent.apply_settings_dialog(self)
    def restart_requested(self):
        if not self.restart_after_save_cb.IsChecked():
            return False, 0
        try:
            delay = int(self.restart_delay_txt.GetValue().strip() or "10")
        except Exception:
            delay = 10
        return True, max(1, delay)
    def message_policy(self):
        try:
            edit_window = max(0, int(self.message_edit_window_txt.GetValue().strip() or "300"))
        except Exception:
            edit_window = 300
        try:
            undo_window = max(0, int(self.message_undo_window_txt.GetValue().strip() or "15"))
        except Exception:
            undo_window = 15
        return edit_window, undo_window

class ReconnectDialog(wx.Dialog):
    def __init__(self):
        super().__init__(None, title="Connection Lost", style=wx.DEFAULT_DIALOG_STYLE | wx.STAY_ON_TOP)
        self.cancelled = False
        panel = wx.Panel(self); sizer = wx.BoxSizer(wx.VERTICAL)

        dark_mode_on = is_windows_dark_mode()
        if dark_mode_on:
            dark_color = wx.Colour(40, 40, 40); light_text_color = wx.WHITE
            WxMswDarkMode().enable(self); self.SetBackgroundColour(dark_color); panel.SetBackgroundColour(dark_color)

        self.status_label = wx.StaticText(panel, label="Connection to the server was lost.")
        give_up_btn = wx.Button(panel, label="Give Up")
        give_up_btn.Bind(wx.EVT_BUTTON, self.on_give_up)

        if dark_mode_on:
            self.status_label.SetForegroundColour(light_text_color); self.status_label.SetBackgroundColour(dark_color)
            give_up_btn.SetBackgroundColour(dark_color); give_up_btn.SetForegroundColour(light_text_color)

        sizer.Add(self.status_label, 0, wx.ALL, 15)
        sizer.Add(give_up_btn, 0, wx.ALIGN_CENTER | wx.BOTTOM, 10)
        panel.SetSizer(sizer); self.Fit(); self.Centre()

    def set_status(self, text):
        self.status_label.SetLabel(text); self.Layout(); self.Fit()

    def on_give_up(self, _):
        self.cancelled = True; self.EndModal(wx.ID_CANCEL)

class ChangePasswordDialog(wx.Dialog):
    def __init__(self, parent):
        super().__init__(parent, title="Change Password", size=(300, 220))
        panel = wx.Panel(self); sizer = wx.BoxSizer(wx.VERTICAL)
        dark_mode_on = is_windows_dark_mode()
        if dark_mode_on:
            dark_color = wx.Colour(40, 40, 40); light_text_color = wx.WHITE
            WxMswDarkMode().enable(self); self.SetBackgroundColour(dark_color); panel.SetBackgroundColour(dark_color)
        cur_box = wx.StaticBoxSizer(wx.VERTICAL, panel, "&Current Password")
        self.cur_ctrl = wx.TextCtrl(cur_box.GetStaticBox(), style=wx.TE_PASSWORD)
        new_box = wx.StaticBoxSizer(wx.VERTICAL, panel, "&New Password")
        self.new_ctrl = wx.TextCtrl(new_box.GetStaticBox(), style=wx.TE_PASSWORD)
        conf_box = wx.StaticBoxSizer(wx.VERTICAL, panel, "Con&firm New Password")
        self.conf_ctrl = wx.TextCtrl(conf_box.GetStaticBox(), style=wx.TE_PASSWORD)
        btn_sizer = wx.StdDialogButtonSizer()
        ok_btn = wx.Button(panel, wx.ID_OK, label="&Change"); ok_btn.SetDefault()
        cancel_btn = wx.Button(panel, wx.ID_CANCEL)
        ok_btn.Bind(wx.EVT_BUTTON, self.on_ok)
        if dark_mode_on:
            for box in [cur_box, new_box, conf_box]:
                box.GetStaticBox().SetForegroundColour(light_text_color); box.GetStaticBox().SetBackgroundColour(dark_color)
            for ctrl in [self.cur_ctrl, self.new_ctrl, self.conf_ctrl]:
                ctrl.SetBackgroundColour(dark_color); ctrl.SetForegroundColour(light_text_color)
            ok_btn.SetBackgroundColour(dark_color); ok_btn.SetForegroundColour(light_text_color)
            cancel_btn.SetBackgroundColour(dark_color); cancel_btn.SetForegroundColour(light_text_color)
        cur_box.Add(self.cur_ctrl, 0, wx.EXPAND | wx.ALL, 5)
        new_box.Add(self.new_ctrl, 0, wx.EXPAND | wx.ALL, 5)
        conf_box.Add(self.conf_ctrl, 0, wx.EXPAND | wx.ALL, 5)
        sizer.Add(cur_box, 0, wx.EXPAND | wx.ALL, 5)
        sizer.Add(new_box, 0, wx.EXPAND | wx.ALL, 5)
        sizer.Add(conf_box, 0, wx.EXPAND | wx.ALL, 5)
        btn_sizer.AddButton(ok_btn); btn_sizer.AddButton(cancel_btn); btn_sizer.Realize()
        sizer.Add(btn_sizer, 0, wx.ALIGN_CENTER | wx.ALL, 5)
        panel.SetSizer(sizer)
    def on_ok(self, _):
        if not self.cur_ctrl.GetValue():
            wx.MessageBox("Please enter your current password.", "Error", wx.ICON_ERROR); return
        if not self.new_ctrl.GetValue():
            wx.MessageBox("Please enter a new password.", "Error", wx.ICON_ERROR); return
        if self.new_ctrl.GetValue() != self.conf_ctrl.GetValue():
            wx.MessageBox("New passwords do not match.", "Error", wx.ICON_ERROR); return
        self.EndModal(wx.ID_OK)

STATUS_PRESETS = ["online", "offline", "busy", "away", "on the phone", "doing homework", "in the shower", "watching TV", "hiding from the parents", "fixing my PC", "battery about to die"]

class StatusDialog(wx.Dialog):
    def __init__(self, parent, current_status="online"):
        super().__init__(parent, title="Set Status")
        self.panel = panel = wx.Panel(self); self.sizer = s = wx.BoxSizer(wx.VERTICAL)
        self.dark_mode_on = is_windows_dark_mode()
        if self.dark_mode_on:
            self.dark_color = wx.Colour(40, 40, 40); self.light_text_color = wx.WHITE
            WxMswDarkMode().enable(self); self.SetBackgroundColour(self.dark_color); panel.SetBackgroundColour(self.dark_color)
        status_box = wx.StaticBoxSizer(wx.VERTICAL, panel, "&Preset")
        self.choice = wx.Choice(status_box.GetStaticBox(), choices=STATUS_PRESETS + ["Custom..."])
        is_custom = current_status not in STATUS_PRESETS
        if is_custom: self.choice.SetStringSelection("Custom...")
        else: self.choice.SetStringSelection(current_status)
        status_box.Add(self.choice, 0, wx.EXPAND | wx.ALL, 5)
        self.custom_box = wx.StaticBoxSizer(wx.VERTICAL, panel, "S&tatus Text")
        self.status_text = wx.TextCtrl(self.custom_box.GetStaticBox())
        self.status_text.SetValue(current_status if is_custom else "")
        self.custom_box.Add(self.status_text, 0, wx.EXPAND | wx.ALL, 5)
        self.choice.Bind(wx.EVT_CHOICE, self._on_choice)
        s.Add(status_box, 0, wx.EXPAND | wx.ALL, 5); s.Add(self.custom_box, 0, wx.EXPAND | wx.ALL, 5)
        btn_sizer = wx.StdDialogButtonSizer()
        ok_btn = wx.Button(panel, wx.ID_OK, label="&Apply"); ok_btn.SetDefault()
        cancel_btn = wx.Button(panel, wx.ID_CANCEL)
        if self.dark_mode_on:
            for box in [status_box, self.custom_box]:
                box.GetStaticBox().SetForegroundColour(self.light_text_color); box.GetStaticBox().SetBackgroundColour(self.dark_color)
            self.choice.SetBackgroundColour(self.dark_color); self.choice.SetForegroundColour(self.light_text_color)
            self.status_text.SetBackgroundColour(self.dark_color); self.status_text.SetForegroundColour(self.light_text_color)
            ok_btn.SetBackgroundColour(self.dark_color); ok_btn.SetForegroundColour(self.light_text_color)
            cancel_btn.SetBackgroundColour(self.dark_color); cancel_btn.SetForegroundColour(self.light_text_color)
        btn_sizer.AddButton(ok_btn); btn_sizer.AddButton(cancel_btn); btn_sizer.Realize()
        s.Add(btn_sizer, 0, wx.ALIGN_CENTER | wx.ALL, 10); panel.SetSizer(s)
        if not is_custom: self.sizer.Hide(self.custom_box)
        self.panel.Layout()
        self.SetSize((350, 220 if is_custom else 150))
    def _on_choice(self, event):
        sel = self.choice.GetStringSelection()
        if sel == "Custom...":
            self.status_text.SetValue(""); self.sizer.Show(self.custom_box); self.panel.Layout()
            self.SetSize((350, 220)); self.status_text.SetFocus()
        else:
            self.status_text.SetValue(sel); self.sizer.Hide(self.custom_box); self.panel.Layout()
            self.SetSize((350, 150))

def create_secure_socket(server_entry=None):
    active = SERVER_CONFIG if server_entry is None else {
        'host': normalize_server_entry(server_entry)['host'],
        'port': normalize_server_entry(server_entry)['port'],
        'cafile': normalize_server_entry(server_entry)['cafile'] or None,
    }
    addr = (active['host'], active['port'])
    sock = socket.create_connection(addr, timeout=6.0)
    if active['cafile'] and os.path.exists(active['cafile']):
        context = ssl.create_default_context(ssl.Purpose.SERVER_AUTH, cafile=active['cafile'])
    else: context = ssl.create_default_context(ssl.Purpose.SERVER_AUTH)
    try:
        wrapped = context.wrap_socket(sock, server_hostname=active['host'])
        wrapped.settimeout(None)
        return wrapped
    except ssl.SSLCertVerificationError:
        sock.close(); sock = socket.create_connection(addr, timeout=6.0)
        context = ssl.create_default_context(); context.check_hostname = False; context.verify_mode = ssl.CERT_NONE
        wrapped = context.wrap_socket(sock, server_hostname=active['host'])
        wrapped.settimeout(None)
        return wrapped
    except (ssl.SSLError, OSError):
        sock.close()
        plain = socket.create_connection(addr, timeout=6.0)
        plain.settimeout(None)
        return plain

class ClientApp(wx.App):
    def _startup_window_watchdog(self):
        if getattr(self, "frame", None):
            return
        if getattr(self, "_startup_ui_started", False):
            return
        try:
            for win in wx.GetTopLevelWindows():
                if isinstance(win, LoginDialog) and win.IsShown():
                    return
        except Exception:
            pass
        log_event("warn", "startup_window_watchdog_retry")
        wx.CallAfter(self._bootstrap_startup_ui)

    def _bootstrap_startup_ui(self):
        if getattr(self, "_startup_ui_started", False):
            return True
        self._startup_ui_started = True
        try:
            ok = self.show_login_dialog()
        except Exception as e:
            log_event("error", "startup_ui_exception", {"error": str(e)})
            traceback.print_exc()
            ok = False
        if not ok:
            self.ExitMainLoop()
        return ok

    def _signal_existing_instance(self):
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            s.settimeout(1.0)
            s.connect(('127.0.0.1', _IPC_PORT))
            s.sendall(b'restore')
            s.close()
            return True
        except Exception:
            return False

    def _activate_existing_app(self):
        if sys.platform != 'darwin':
            return False
        try:
            p = subprocess.run(
                ["osascript", "-e", 'tell application "Thrive Messenger" to activate'],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                check=False,
            )
            return p.returncode == 0
        except Exception:
            return False

    def OnInit(self):
        log_event("info", "app_start")
        self._startup_ui_started = False
        self.instance_checker = wx.SingleInstanceChecker("ThriveMessenger-%s" % wx.GetUserId())
        if self.instance_checker.IsAnotherRunning():
            # Only trust the IPC restore path. AppleScript activation can
            # succeed even when no usable UI instance is available.
            if sys.platform != 'darwin' and self._signal_existing_instance():
                return False
            # Stale lock or crashed/background state: continue startup to recover.
            print("Detected stale single-instance state; launching a fresh visible window.")
            log_event("warn", "stale_single_instance_lock_recovered")
        try:
            self._ipc_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self._ipc_sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            self._ipc_sock.bind(('127.0.0.1', _IPC_PORT))
            self._ipc_sock.listen(1)
            threading.Thread(target=self._ipc_listener, daemon=True).start()
        except Exception:
            # If IPC binding fails, first try to restore an existing instance.
            # If restore fails, continue startup without IPC to avoid being stuck unable to open.
            self._ipc_sock = None
            if sys.platform != 'darwin' and self._signal_existing_instance():
                return False
            print("IPC port unavailable and no active instance responded; continuing without IPC listener.")
            log_event("warn", "ipc_bind_unavailable_continuing")
        self.user_config = load_user_config()
        self.launch_invite_context = parse_invite_context_from_args()
        self.session_password = ""
        self.reconnect_in_progress = False
        self.reconnect_stop_event = threading.Event()
        self._last_activity = time.time()
        self._keepalive_stop = threading.Event()
        self.active_server_entry = resolve_default_server_entry(self.user_config)
        self.connected_server_names = set()
        self.transfer_history = []
        self.pending_rerequests = {}
        self.load_transfer_history()
        self.outbox, self.pending_acks = [], {}
        has_invite_launch = bool(self.launch_invite_context.get("invite_token"))
        if self.user_config.get('autologin') and self.user_config.get('username') and not has_invite_launch:
            print("Attempting auto-login...")
            selected_server = resolve_default_server_entry(self.user_config)
            mode = str(self.user_config.get('autologin_mode', 'password') or 'password')
            if mode == 'passkey':
                success, sock, sf, reason = self.perform_passkey_login(self.user_config['username'], selected_server)
            else:
                if not self.user_config.get('password'):
                    success, sock, sf, reason = False, None, None, "Saved password is missing."
                else:
                    success, sock, sf, reason = self.perform_login(self.user_config['username'], self.user_config['password'], selected_server)
            if success: self.start_main_session(self.user_config['username'], sock, sf); return True
            else:
                wx.MessageBox(f"Auto-login failed: {reason}", "Login Failed", wx.ICON_ERROR)
                log_event("error", "auto_login_failed", {"reason": str(reason)})
                # Keep autologin enabled for transient network/server issues.
                if "invalid credentials" in str(reason).lower():
                    self.user_config['autologin'] = False
                save_user_config(self.user_config)
        # On macOS, opening modal dialogs directly in OnInit can result in a
        # running process with no visible windows. Defer startup UI until the
        # event loop is active.
        if sys.platform == 'darwin':
            # Startup creates the login dialog with CallAfter. Keep the app
            # alive until that first top-level window exists.
            self.SetExitOnFrameDelete(False)
            wx.CallAfter(self._bootstrap_startup_ui)
            wx.CallLater(2000, self._startup_window_watchdog)
            return True
        # Elsewhere, with no window yet MainLoop would return at once and the app would quit
        # silently (fresh installs, or anyone not using auto-login). Show the login UI now.
        return bool(self._bootstrap_startup_ui())

    def _transfer_history_path(self):
        return os.path.join(get_config_dir(), "transfer_history.json")
    def load_transfer_history(self):
        try:
            with open(self._transfer_history_path(), encoding="utf-8") as fh:
                data = json.load(fh)
            self.transfer_history = [e for e in data if isinstance(e, dict)][-2000:]
        except Exception:
            self.transfer_history = []
    def save_transfer_history(self):
        try:
            os.makedirs(get_config_dir(), exist_ok=True)
            tmp = self._transfer_history_path() + ".tmp"
            with open(tmp, "w", encoding="utf-8") as fh:
                json.dump(self.transfer_history[-2000:], fh, ensure_ascii=False)
            os.replace(tmp, self._transfer_history_path())
        except Exception as e:
            print(f"Could not save transfer history: {e}")
    def add_transfer_history(self, direction, user, filename, path="", status="ok", size=None, kind="file", extra=None):
        entry = {
            "time": datetime.datetime.now().isoformat(),
            "direction": direction,
            "user": user,
            "filename": filename,
            "path": path,
            "status": status,
            "kind": kind,
        }
        if size is None and path and os.path.isfile(path):
            try:
                size = os.path.getsize(path)
            except OSError:
                size = None
        if size is not None:
            entry["size"] = int(size)
        if extra:
            entry.update(extra)
        self.transfer_history.append(entry)
        self.save_transfer_history()
        chat = self.frame.get_chat(user) if getattr(self, "frame", None) else None
        if chat and hasattr(chat, "transfers_page"):
            chat.transfers_page.refresh()
        return entry
    # --- "Get again": ask the other person's device to re-send a file it still has -------------
    def request_file_again(self, contact, entry):
        request_id = uuid.uuid4().hex
        self.pending_rerequests[request_id] = {"entry": entry, "contact": contact, "offer_seen": False}
        entry["status"] = "requested"
        self.save_transfer_history()
        try:
            self.sock.sendall((json.dumps({"action": "file_rerequest", "to": contact, "filename": entry.get("filename", ""),
                                           "size": entry.get("size"), "request_id": request_id}) + "\n").encode())
            speak_text(f"Asked {contact} for {entry.get('filename', 'the file')} again", interrupt=True)
        except Exception as e:
            entry["status"] = "unavailable"
            self.save_transfer_history()
            speak_text(f"Could not ask for the file again: {e}", interrupt=True)
    def on_file_rerequest(self, msg):
        """The other person wants a file again. Answer automatically only if it's a file between us that still exists here."""
        requester = str(msg.get("from") or "")
        filename = str(msg.get("filename") or "")
        request_id = str(msg.get("request_id") or "")
        size = msg.get("size")
        match = None
        for e in reversed(self.transfer_history):
            if str(e.get("user", "")).lower() != requester.lower() or e.get("filename") != filename:
                continue
            path = e.get("path") or ""
            if not path or not os.path.isfile(path):
                continue
            if size and e.get("size") and int(e.get("size")) != int(size):
                continue
            match = path
            break
        if match:
            self._offer_files(requester, [match], extra={"rerequest_id": request_id})
            chat = self.frame.get_chat(requester)
            if chat:
                chat.append(f"{requester} asked for {filename} again; sending it.", "System", time.time())
        else:
            try:
                self.sock.sendall((json.dumps({"action": "file_rerequest_result", "to": requester, "request_id": request_id,
                                               "ok": False, "filename": filename}) + "\n").encode())
            except Exception:
                pass
    def on_file_rerequest_result(self, msg):
        pending = self.pending_rerequests.get(str(msg.get("request_id") or ""))
        if not pending or pending.get("offer_seen") or msg.get("ok"):
            return
        entry = pending["entry"]
        entry["status"] = "unavailable"
        self.save_transfer_history()
        who = msg.get("from") or pending.get("contact")
        text = f"{entry.get('filename', 'That file')} is no longer available from {who}."
        chat = self.frame.get_chat(pending.get("contact"))
        if chat:
            chat.append(text, "System", time.time())
            chat.transfers_page.refresh()
        speak_text(text, interrupt=False)
    
    def _ipc_listener(self):
        while True:
            try:
                conn, _ = self._ipc_sock.accept()
                data = conn.recv(1024)
                conn.close()
                if data == b'restore':
                    wx.CallAfter(self._restore_window)
            except Exception:
                break

    def _restore_window(self):
        if hasattr(self, 'frame') and self.frame:
            if not self.frame.IsShown():
                self.frame.restore_from_tray()
            if sys.platform == 'win32':
                hwnd = self.frame.GetHandle()
                ctypes.windll.user32.ShowWindow(hwnd, 9)  # SW_RESTORE
                ctypes.windll.user32.SetForegroundWindow(hwnd)
            else:
                self.frame.Raise()
                self.frame.SetFocus()

    def show_login_dialog(self):
        while True:
            dlg = LoginDialog(None, self.user_config, invite_context=self.launch_invite_context)
            result = dlg.ShowModal()
            if result == wx.ID_OK:
                if getattr(dlg, "login_mode", "password") == "passkey":
                    success, sock, sf, _ = self.perform_passkey_login(dlg.username, dlg.selected_server)
                else:
                    success, sock, sf, _ = self.perform_login(dlg.username, dlg.password, dlg.selected_server)
                if success:
                    self.user_config['server_entries'] = dlg.server_entries
                    self.user_config['last_server_name'] = dlg.selected_server.get('name', '')
                    self.user_config['primary_server_name'] = dlg.primary_server_name
                    if dlg.remember_checked:
                        self.user_config['username'] = dlg.username
                        self.user_config['password'] = dlg.password
                        self.user_config['remember'] = True
                        self.user_config['autologin'] = dlg.autologin_checked
                        self.user_config['autologin_mode'] = getattr(dlg, "login_mode", "password")
                    else:
                        # Clear sensitive data but keep generic settings
                        self.user_config.update({'username': '', 'password': '', 'remember': False, 'autologin': False, 'autologin_mode': 'password'})

                    save_user_config(self.user_config)
                    self.start_main_session(dlg.username, sock, sf)
                    return True
            elif result == wx.ID_ABORT:
                success, sock, sf, _ = self.perform_login(dlg.new_username, dlg.new_password, dlg.selected_server)
                if success:
                    self.user_config = {
                        'username': dlg.new_username,
                        'password': dlg.new_password,
                        'remember': True,
                        'autologin': True,
                        'autologin_mode': 'password',
                        'soundpack': 'default',
                        'chat_logging': {},
                        'server_entries': dlg.server_entries,
                        'last_server_name': dlg.selected_server.get('name', ''),
                        'primary_server_name': dlg.primary_server_name
                    }
                    save_user_config(self.user_config); self.start_main_session(dlg.new_username, sock, sf); return True
            else: return False
    
    def perform_login(self, username, password, server_entry=None, suppress_errors=False, show_post_login=True):
        try:
            if server_entry:
                set_active_server_config(server_entry)
            ssock = create_secure_socket(server_entry)
            login_request = {"action":"login","user":username,"pass":password, **_device_login_fields(self.user_config)}
            # Never wait forever for a server that accepts the connection but doesn't answer.
            ssock.settimeout(LOGIN_RESPONSE_TIMEOUT)
            ssock.sendall(json.dumps(login_request).encode()+b"\n")
            sf = ssock.makefile()
            try:
                resp = json.loads(sf.readline() or "{}")
            except (socket.timeout, TimeoutError):
                resp = {"status": "error", "reason": "The server didn't answer the sign-in request. Check the server address in Server Manager."}
            ssock.settimeout(None)
            if resp.get("status") == "ok":
                self.session_password = password
                self.active_server_entry = normalize_server_entry(server_entry or SERVER_CONFIG)
                info = fetch_server_welcome(server_entry or SERVER_CONFIG)
                post_login = str(info.get('post_login', '') or '').strip()
                if show_post_login and info.get('enabled') and post_login:
                    show_notification("Server Message", post_login, timeout=8)
                return True, ssock, sf, "Success"
            else:
                reason = resp.get("reason", "Unknown error")
                log_event("error", "login_failed", {"reason": reason})
                if not suppress_errors:
                    wx.MessageBox("Login failed: " + reason, "Login Failed", wx.ICON_ERROR)
                ssock.close()
                return False, None, None, reason
        except Exception as e:
            log_event("error", "login_connection_error", {"error": str(e)})
            if not suppress_errors:
                wx.MessageBox(f"A connection error occurred: {e}", "Connection Error", wx.ICON_ERROR)
                try:
                    prompt_submit_logs(None, self.user_config, reason="login_connection_error")
                except Exception:
                    pass
            return False, None, None, str(e)

    def perform_passkey_login(self, username, server_entry=None, suppress_errors=False, show_post_login=True):
        try:
            if server_entry:
                set_active_server_config(server_entry)
            token = _load_passkey_from_keyring(username, settings=self.user_config, server_entry=server_entry or SERVER_CONFIG)
            if not token:
                reason = "No passkey is saved for this account on the selected server."
                if not suppress_errors:
                    wx.MessageBox(reason, "Passkey Login Failed", wx.ICON_ERROR)
                return False, None, None, reason
            ssock = create_secure_socket(server_entry)
            login_request = {"action": "login_passkey", "user": username, "passkey_token": token, **_device_login_fields(self.user_config)}
            ssock.sendall(json.dumps(login_request).encode() + b"\n")
            sf = ssock.makefile()
            resp = json.loads(sf.readline() or "{}")
            if resp.get("status") == "ok":
                self.session_password = ""
                self.active_server_entry = normalize_server_entry(server_entry or SERVER_CONFIG)
                info = fetch_server_welcome(server_entry or SERVER_CONFIG)
                post_login = str(info.get('post_login', '') or '').strip()
                if show_post_login and info.get('enabled') and post_login:
                    show_notification("Server Message", post_login, timeout=8)
                return True, ssock, sf, "Success"
            reason = resp.get("reason", "Unknown error")
            log_event("error", "passkey_login_failed", {"reason": reason})
            if not suppress_errors:
                wx.MessageBox("Passkey login failed: " + reason, "Login Failed", wx.ICON_ERROR)
            ssock.close()
            return False, None, None, reason
        except Exception as e:
            log_event("error", "passkey_login_connection_error", {"error": str(e)})
            if not suppress_errors:
                wx.MessageBox(f"A connection error occurred: {e}", "Connection Error", wx.ICON_ERROR)
            return False, None, None, str(e)

    def _current_server_label(self):
        active = normalize_server_entry(getattr(self, "active_server_entry", SERVER_CONFIG))
        return active.get("name") or active.get("host") or "Server"

    def _set_socket_for_open_windows(self, sock):
        if not getattr(self, 'frame', None):
            return
        self.frame.set_socket(sock)

    def _apply_reconnected_session(self, sock, sf):
        self.sock = sock
        self.sockfile = sf
        self.reconnect_in_progress = False
        self.reconnect_stop_event.clear()
        self._last_activity = time.time()
        self._start_keepalive_monitor()
        self.intentional_disconnect = False
        self._set_socket_for_open_windows(sock)
        if getattr(self, 'frame', None):
            self.frame.refresh_connection_title(connected=True)
        show_notification("Reconnected", f"Connected to {self._current_server_label()}.", timeout=5)
        self.play_sound("reconnected.wav")
        speak_text("Reconnected", interrupt=False)
        try:
            if getattr(self, 'frame', None) and self.frame.current_status != "online":
                self.sock.sendall((json.dumps({"action": "set_status", "status_text": self.frame.current_status}) + "\n").encode())
        except Exception:
            pass
        threading.Thread(target=self.listen_loop, daemon=True).start()
        try:
            self.sock.sendall((json.dumps({"action": "get_feature_caps"}) + "\n").encode())
        except Exception:
            pass
        wx.CallLater(800, self._flush_outbox)

    def _start_reconnect_loop(self):
        if self.intentional_disconnect or self.reconnect_in_progress:
            return
        self.reconnect_in_progress = True
        self.reconnect_stop_event.clear()
        threading.Thread(target=self._reconnect_worker, daemon=True).start()

    def _reconnect_worker(self):
        username = getattr(self, "username", "") or self.user_config.get("username", "")
        mode = str(self.user_config.get("autologin_mode", "password") or "password")
        password = self.session_password or self.user_config.get("password", "")
        if not username:
            self.reconnect_in_progress = False
            wx.CallAfter(show_notification, "Reconnect paused", "Saved login is not available. Sign in again when ready.", 7)
            return
        attempt = 0
        while not self.intentional_disconnect and not self.reconnect_stop_event.is_set():
            attempt += 1
            if mode == "passkey":
                success, sock, sf, reason = self.perform_passkey_login(
                    username,
                    self.active_server_entry,
                    suppress_errors=True,
                    show_post_login=False,
                )
            else:
                if not password:
                    success, sock, sf, reason = False, None, None, "Saved password is missing."
                else:
                    success, sock, sf, reason = self.perform_login(
                        username,
                        password,
                        self.active_server_entry,
                        suppress_errors=True,
                        show_post_login=False,
                    )
            if success:
                wx.CallAfter(self._apply_reconnected_session, sock, sf)
                return
            if attempt == 1 or attempt % 3 == 0:
                wx.CallAfter(show_notification, "Reconnecting", f"Connection lost. Retrying ({attempt})...", 5)
            if attempt == 4:
                waiting = len(getattr(self, "outbox", []))
                note = f" {waiting} message{'s' if waiting != 1 else ''} will be sent when it's back." if waiting else ""
                wx.CallAfter(speak_text, f"Still reconnecting.{note}", False)
            delay = min(30, max(2, attempt * 2))
            for _ in range(delay):
                if self.intentional_disconnect or self.reconnect_stop_event.is_set():
                    self.reconnect_in_progress = False
                    return
                time.sleep(1)
        self.reconnect_in_progress = False

    def fetch_directory_for_server(self, server_entry, username, password):
        try:
            ssock = create_secure_socket(server_entry)
            ssock.sendall(json.dumps({"action":"login","user":username,"pass":password}).encode()+b"\n")
            sf = ssock.makefile()
            resp = json.loads(sf.readline() or "{}")
            if resp.get("status") != "ok":
                ssock.close()
                return []
            ssock.sendall((json.dumps({"action": "user_directory"}) + "\n").encode())
            directory_resp = json.loads(sf.readline() or "{}")
            try:
                ssock.sendall(json.dumps({"action":"logout"}).encode()+b"\n")
            except Exception:
                pass
            ssock.close()
            if directory_resp.get("action") != "user_directory_response":
                return []
            users = directory_resp.get("users", [])
            normalized = normalize_server_entry(server_entry)
            tag = normalized.get("name", "Server")
            for u in users:
                if "server" not in u:
                    u["server"] = tag
                u["display_name"] = pick_user_display_name(u)
                u["server_host"] = normalized.get("host", "")
                u["server_port"] = int(normalized.get("port", 0) or 0)
            return users
        except Exception as e:
            print(f"Directory fetch failed for {server_entry}: {e}")
            return []

    def resolve_server_entry_by_name(self, server_name):
        target = str(server_name or "").strip().lower()
        active = normalize_server_entry(getattr(self, "active_server_entry", {}))
        if not target:
            return active
        if active.get("name", "").strip().lower() == target:
            return active
        for entry in dedupe_server_entries(self.user_config.get("server_entries", [])):
            normalized = normalize_server_entry(entry)
            if normalized.get("name", "").strip().lower() == target:
                return normalized
        return None

    def send_directory_direct_message(self, server_entry, from_user, to_user, text):
        try:
            normalized = normalize_server_entry(server_entry)
            password = self.session_password or self.user_config.get("password", "")
            if not password:
                return False, "No saved session password is available for this server message."
            ssock = create_secure_socket(normalized)
            ssock.sendall(json.dumps({"action":"login","user":from_user,"pass":password}).encode()+b"\n")
            sf = ssock.makefile()
            resp = json.loads(sf.readline() or "{}")
            if resp.get("status") != "ok":
                try:
                    ssock.close()
                except Exception:
                    pass
                return False, f"Login failed on {normalized.get('name')}: {resp.get('reason', 'unknown error')}"
            payload = {
                "action": "msg",
                "from": from_user,
                "to": to_user,
                "msg": text,
                "time": datetime.datetime.now().isoformat(),
            }
            ssock.sendall((json.dumps(payload) + "\n").encode())
            # Optional immediate error response from server.
            ssock.settimeout(1.2)
            try:
                line = sf.readline()
                if line:
                    msg = json.loads(line or "{}")
                    if msg.get("action") == "msg_failed":
                        reason = msg.get("reason", "Message failed.")
                        try:
                            ssock.sendall(json.dumps({"action":"logout"}).encode()+b"\n")
                        except Exception:
                            pass
                        ssock.close()
                        return False, reason
            except Exception:
                pass
            try:
                ssock.sendall(json.dumps({"action":"logout"}).encode()+b"\n")
            except Exception:
                pass
            try:
                ssock.close()
            except Exception:
                pass
            return True, None
        except Exception as e:
            return False, str(e)
    
    def start_main_session(self, username, sock, sf):
        self.username = username; self.sock = sock; self.sockfile = sf; self.pending_file_paths = {}
        self.intentional_disconnect = False
        self._last_activity = time.time()
        self._start_keepalive_monitor()
        active = normalize_server_entry(getattr(self, "active_server_entry", SERVER_CONFIG))
        self.connected_server_names = {active.get("name") or active.get("host") or "Server"}
        self.frame = MainFrame(self.username, self.sock); self.frame.Show()
        if self.frame.current_status != "online":
            try: self.sock.sendall((json.dumps({"action": "set_status", "status_text": self.frame.current_status}) + "\n").encode())
            except Exception: pass
        wx.CallLater(250, self.play_startup_sound)
        threading.Thread(target=self.listen_loop, daemon=True).start()
        try:
            self.sock.sendall((json.dumps({"action": "get_feature_caps"}) + "\n").encode())
        except Exception:
            pass
        self.sync_session_preferences()
        self.frame.on_check_updates(silent=True)

    def _start_keepalive_monitor(self):
        stop_event = getattr(self, "_keepalive_stop", None)
        if stop_event:
            stop_event.set()
        self._keepalive_stop = threading.Event()
        monitored_sock = getattr(self, "sock", None)
        threading.Thread(target=self._keepalive_monitor, args=(self._keepalive_stop, monitored_sock), daemon=True).start()

    def _keepalive_monitor(self, stop_event, monitored_sock):
        while not stop_event.wait(KEEPALIVE_CHECK_INTERVAL):
            sock = getattr(self, "sock", None)
            if not sock or sock is not monitored_sock or self.intentional_disconnect:
                continue
            idle_for = time.time() - getattr(self, "_last_activity", time.time())
            if idle_for < IDLE_KEEPALIVE_SECONDS:
                continue
            previous_activity = self._last_activity
            try:
                sock.sendall((json.dumps({"action": "get_feature_caps"}) + "\n").encode())
            except Exception:
                if not self.intentional_disconnect and getattr(self, "sock", None) is monitored_sock:
                    wx.CallAfter(self.on_server_disconnect)
                return
            if stop_event.wait(KEEPALIVE_RESPONSE_TIMEOUT):
                return
            if (getattr(self, "_last_activity", previous_activity) <= previous_activity
                    and not self.intentional_disconnect
                    and getattr(self, "sock", None) is monitored_sock):
                wx.CallAfter(self.on_server_disconnect)
                return

    def sync_session_preferences(self):
        sock = getattr(self, "sock", None)
        if not sock:
            return
        try:
            sock.sendall((json.dumps({
                "action": "set_session_pref",
                "notify_on_other_device_login": bool(self.user_config.get("notify_on_other_device_login", False)),
            }) + "\n").encode())
        except Exception:
            pass

    def _resolved_sound_pack(self):
        selected = str(self.user_config.get('soundpack', 'default') or 'default').strip().lower()
        if selected == 'none':
            return 'none'
        if selected == 'default':
            preferred = str(self.user_config.get('default_soundpack', 'default') or 'default').strip().lower()
            return preferred if preferred and preferred != 'none' else 'default'
        return selected

    def _play_path_with_volume(self, path):
        vol = int(self.user_config.get('sound_volume', 80) or 80)
        vol = max(0, min(100, vol))
        if vol == 0:
            return
        self.stop_current_sound()
        if sys.platform == 'darwin':
            afplay = shutil.which('afplay')
            if afplay:
                # afplay accepts linear gain in 0.0-1.0
                self._sound_process = subprocess.Popen([afplay, '-v', f"{vol / 100.0:.2f}", path], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                return
        wx.adv.Sound.PlaySound(path, wx.adv.SOUND_ASYNC)

    def stop_current_sound(self):
        process = getattr(self, "_sound_process", None)
        if process is not None and process.poll() is None:
            try: process.terminate()
            except OSError: pass
        self._sound_process = None
        try: wx.adv.Sound.Stop()
        except Exception: pass

    def play_sound(self, sound_file):
        pack = self._resolved_sound_pack()
        if pack == 'none':
            return
        if sound_file in CALL_SOUND_EVENTS:
            call_pack = str(self.user_config.get('call_soundpack', 'flexpbx') or 'flexpbx').strip().lower()
            if call_pack not in ('', 'same', 'none'):
                pack = call_pack
        path = find_local_sound_path(pack, sound_file) or download_sound_file_if_missing(self.user_config, pack, sound_file)
        if path and os.path.exists(path):
            self._play_path_with_volume(path)
            return
        default_path = find_local_sound_path('default', sound_file) or download_sound_file_if_missing(self.user_config, 'default', sound_file)
        if default_path and os.path.exists(default_path):
            self._play_path_with_volume(default_path)

    def play_startup_sound(self):
        pack = self._resolved_sound_pack()
        if pack == 'none':
            return
        sounds_root = get_sounds_dir()
        try:
            root_wavs = [os.path.join(sounds_root, n) for n in os.listdir(sounds_root) if n.lower().endswith('.wav')]
        except Exception:
            root_wavs = []
        if root_wavs:
            self._play_path_with_volume(random.choice(root_wavs))
            return
        # Final fallback: play standard login sound from selected/default pack.
        self.play_sound("login.wav")
    
    def listen_loop(self):
        sock = self.sock
        handled = False
        try:
            for line in self.sockfile:
                try:
                    msg = json.loads(line)
                except Exception:
                    continue
                self._last_activity = time.time()
                act = msg.get("action")
                try:
                    if act == "contact_list": wx.CallAfter(self.frame.load_contacts, msg.get("contacts", []))
                    elif act == "contact_status": wx.CallAfter(self.frame.update_contact_status, msg.get("user"), msg.get("online"), msg.get("status_text"))
                    elif act == "msg": wx.CallAfter(self.frame.receive_message, msg)
                    elif act == "msg_failed": wx.CallAfter(self.frame.on_message_failed, msg.get("to"), msg.get("reason", "Message could not be delivered."))
                    elif act == "add_contact_failed": wx.CallAfter(self.frame.on_add_contact_failed, msg)
                    elif act == "add_contact_success":
                        contact = msg.get("contact")
                        if isinstance(contact, dict):
                            wx.CallAfter(self.frame.on_add_contact_success, contact)
                    elif act == "admin_response": wx.CallAfter(self.frame.on_admin_response, msg.get("response", ""))
                    elif act == "server_info_response": wx.CallAfter(self.frame.on_server_info_response, msg)
                    elif act == "user_directory_response": wx.CallAfter(self.frame.on_user_directory_response, msg)
                    elif act == "admin_status_change": wx.CallAfter(self.frame.on_admin_status_change, msg.get("user"), msg.get("is_admin"))
                    elif act == "server_alert": wx.CallAfter(self.frame.on_server_alert, msg.get("message", ""))
                    elif act == "other_device_login": wx.CallAfter(self.frame.on_other_device_login, msg)
                    elif act == "typing": wx.CallAfter(self.frame.on_typing_event, msg)
                    elif act == "file_offer": wx.CallAfter(self.on_file_offer, msg)
                    elif act == "file_rerequest": wx.CallAfter(self.on_file_rerequest, msg)
                    elif act == "file_rerequest_result": wx.CallAfter(self.on_file_rerequest_result, msg)
                    elif act == "file_offer_failed": wx.CallAfter(self.on_file_offer_failed, msg)
                    elif act == "file_accepted": wx.CallAfter(self.on_file_accepted, msg)
                    elif act == "file_declined": wx.CallAfter(self.on_file_declined, msg)
                    elif act == "file_data": wx.CallAfter(self.on_file_data, msg)
                    elif act == "invite_result": wx.CallAfter(self.frame.on_invite_result, msg)
                    elif act == "change_password_result": wx.CallAfter(self.frame.on_change_password_result, msg)
                    elif act in ("passkey_register_result", "passkey_list", "passkey_revoke_result"):
                        self.frame.on_passkey_response(msg)
                    elif act == "delete_account_result": wx.CallAfter(self.frame.on_delete_account_result, msg)
                    elif act == "authenticated_devices": wx.CallAfter(self.frame.on_authenticated_devices, msg)
                    elif act == "deauthenticate_device_result": wx.CallAfter(self.frame.on_deauthenticate_device_result, msg)
                    elif act == "bot_token_revoked": wx.CallAfter(self.frame.on_bot_token_revoked, msg.get("bot", "bot"))
                    elif act == "bot_rules": wx.CallAfter(self.frame.on_bot_rules, msg)
                    elif act == "bot_rules_update": wx.CallAfter(self.frame.on_bot_rules_update, msg)
                    elif act == "group_policy": wx.CallAfter(self.frame.on_group_policy, msg)
                    elif act == "group_policy_update": wx.CallAfter(self.frame.on_group_policy_update, msg)
                    elif act in ("group_room_list_response", "group_room_open_response", "group_room_result", "group_room_event", "group_room_message", "group_room_file", "group_room_members"):
                        wx.CallAfter(self.frame.on_group_room_action, msg)
                    elif act in ("module_list_response", "module_result"):
                        wx.CallAfter(self.frame.on_module_action, msg)
                    elif act == "group_call_list_response": wx.CallAfter(self.frame.on_group_call_list_response, msg)
                    elif act == "group_call_event": wx.CallAfter(self.frame.on_group_call_event, msg)
                    elif act == "group_call_result": wx.CallAfter(self.frame.on_group_call_result, msg)
                    elif act == "group_call_signal": wx.CallAfter(self.frame.on_group_call_signal, msg)
                    elif act == "group_call_signal_result": wx.CallAfter(self.frame.on_group_call_signal_result, msg)
                    elif act == "group_call_audio":
                        wx.CallAfter(self.frame.on_group_call_audio, msg)
                    elif act == "voice_call_incoming": wx.CallAfter(self.frame.on_voice_call_incoming, msg)
                    elif act == "voice_call_event": wx.CallAfter(self.frame.on_voice_call_event, msg)
                    elif act == "feature_caps":
                        wx.CallAfter(self.frame.set_feature_caps, msg.get("caps", {}))
                        if "is_admin" in msg:
                            wx.CallAfter(setattr, self.frame, "am_admin", bool(msg.get("is_admin")))
                    elif act == "msg_sent": wx.CallAfter(self.frame.on_message_sent_ack, msg)
                    elif act == "voicemail_saved": wx.CallAfter(self.frame.on_voicemail_saved, msg)
                    elif act in ("msg_edited", "msg_deleted"): wx.CallAfter(self.frame.on_message_changed, msg)
                    elif act in ("msg_edit_result", "msg_delete_result"): wx.CallAfter(self.frame.on_message_change_result, msg)
                    elif act == "banned_kick": wx.CallAfter(self.on_banned); handled = True; break
                except Exception as dispatch_err:
                    print(f"Warning: failed to process server action '{act}': {dispatch_err}")
        except (IOError, json.JSONDecodeError, ValueError):
            print("Disconnected from server.")
            if self.sock is sock and not self.intentional_disconnect: wx.CallAfter(self.on_server_disconnect); handled = True
            else: handled = True
        if not handled and self.sock is sock and not self.intentional_disconnect:
            print("Server closed connection.")
            wx.CallAfter(self.on_server_disconnect)
    
    def on_banned(self):
        self._return_to_login("You have been banned.", "Banned")

    # --- message delivery: queue while offline, confirm by server ack ------------------------
    ACK_TIMEOUT_SECONDS = 12
    def send_chat_payload(self, panel, payload):
        """Send a chat message, or queue it while reconnecting. Returns 'sent' or 'queued'."""
        if not hasattr(self, "outbox"):
            self.outbox, self.pending_acks = [], {}
        cid = payload.get("client_id")
        if self.reconnect_in_progress or not getattr(self, "sock", None):
            self.outbox.append({"panel": panel, "payload": payload})
            return "queued"
        try:
            self.sock.sendall((json.dumps(payload) + "\n").encode())
        except Exception:
            self.outbox.append({"panel": panel, "payload": payload})
            wx.CallAfter(self.on_server_disconnect)
            return "queued"
        if cid:
            self.pending_acks[cid] = {"panel": panel, "payload": payload, "sent_at": time.time()}
            self._ensure_ack_watchdog()
        return "sent"
    def message_acknowledged(self, client_id):
        getattr(self, "pending_acks", {}).pop(str(client_id or ""), None)
    def message_rejected(self, to):
        """The server answered msg_failed for this recipient: its oldest unconfirmed message isn't lost, it failed."""
        pend = getattr(self, "pending_acks", {})
        for cid, item in sorted(pend.items(), key=lambda kv: kv[1]["sent_at"]):
            if str(item["payload"].get("to", "")).lower() == str(to or "").lower():
                pend.pop(cid, None)
                return
    def _ensure_ack_watchdog(self):
        if not getattr(self, "_ack_watchdog_running", False):
            self._ack_watchdog_running = True
            wx.CallLater(3000, self._ack_watchdog)
    def _ack_watchdog(self):
        pend = getattr(self, "pending_acks", {})
        now = time.time()
        stale = [cid for cid, item in pend.items() if now - item["sent_at"] > self.ACK_TIMEOUT_SECONDS]
        if stale and not self.reconnect_in_progress and not self.intentional_disconnect:
            # The server never confirmed these: the connection is dead even if the socket didn't say so.
            for cid in sorted(stale, key=lambda c: pend[c]["sent_at"]):
                item = pend.pop(cid)
                self.outbox.append({"panel": item["panel"], "payload": item["payload"]})
                if item["panel"]:
                    item["panel"].mark_row_queued(cid, True)
            log_event("warn", "message_ack_timeout", {"count": len(stale)})
            self.on_server_disconnect()
        if pend:
            wx.CallLater(3000, self._ack_watchdog)
        else:
            self._ack_watchdog_running = False
    def _flush_outbox(self):
        queued, self.outbox = list(getattr(self, "outbox", [])), []
        sent = 0
        for item in queued:
            payload = item["payload"]
            panel = item["panel"]
            if self.send_chat_payload(panel, payload) == "sent":
                sent += 1
                if panel:
                    panel.mark_row_queued(payload.get("client_id"), False)
        if sent:
            speak_text(f"Sent {sent} message{'s' if sent != 1 else ''} that were waiting", interrupt=False)

    def on_server_disconnect(self):
        if self.intentional_disconnect or self.reconnect_in_progress:
            return
        try:
            self._keepalive_stop.set()
        except Exception:
            pass
        try:
            self.sock.close()
        except Exception:
            pass
        if getattr(self, 'frame', None):
            self.frame.refresh_connection_title(connected=False)
        show_notification("Connection lost", "Reconnecting in the background...", timeout=6)
        self.play_sound("connection_lost.wav")
        speak_text("Reconnecting", interrupt=False)
        self._start_reconnect_loop()

    def _return_to_login(self, message, title):
        if self.intentional_disconnect: return
        self.intentional_disconnect = True
        try: self.sock.close()
        except: pass
        self.SetExitOnFrameDelete(False)
        old_frame = None
        if hasattr(self, 'frame') and self.frame:
            old_frame = self.frame; old_frame.Hide()
            if old_frame.task_bar_icon: old_frame.task_bar_icon.Destroy(); old_frame.task_bar_icon = None
        wx.MessageBox(message, title, wx.ICON_ERROR)
        self.intentional_disconnect = False
        result = self.show_login_dialog()
        if old_frame: old_frame.is_exiting = True; old_frame.Destroy()
        if not result: self.ExitMainLoop()

    def on_file_offer(self, msg):
        sender = msg["from"]; files = msg["files"]; transfer_id = msg["transfer_id"]
        pending = self.pending_rerequests.get(str(msg.get("rerequest_id") or ""))
        if pending is not None:
            if pending.get("offer_seen"):
                # Another of their devices already answered; decline the duplicate quietly.
                self.sock.sendall((json.dumps({"action": "file_decline", "transfer_id": transfer_id}) + "\n").encode())
                return
            pending["offer_seen"] = True
            self.sock.sendall((json.dumps({"action": "file_accept", "transfer_id": transfer_id}) + "\n").encode())
            speak_text(f"Getting {files[0].get('filename', 'the file') if files else 'the file'} again from {sender}", interrupt=False)
            return
        self.play_sound("file_receive.wav")
        parent = self.frame.get_chat(sender) or self.frame
        if len(files) == 1:
            f = files[0]; size = f.get("size", 0)
            prompt = f"{sender} wants to send you a file:\n\n{f['filename']} ({format_size(size)})\n\nDo you want to accept?"
        else:
            total_size = sum(f.get("size", 0) for f in files)
            file_list = "\n".join(f"  {f['filename']} ({format_size(f.get('size', 0))})" for f in files)
            prompt = f"{sender} wants to send you {len(files)} files ({format_size(total_size)} total):\n\n{file_list}\n\nDo you want to accept?"
        result = wx.MessageBox(prompt, "File Transfer Request", wx.YES_NO | wx.ICON_QUESTION, parent)
        if result == wx.YES:
            self.sock.sendall((json.dumps({"action": "file_accept", "transfer_id": transfer_id}) + "\n").encode())
            chat = self.frame.get_chat(sender)
            if chat:
                names = ", ".join(f["filename"] for f in files)
                chat.append(f"Accepting {len(files)} file(s): {names}...", "System", time.time())
        else:
            self.sock.sendall((json.dumps({"action": "file_decline", "transfer_id": transfer_id}) + "\n").encode())
            chat = self.frame.get_chat(sender)
            if chat: chat.append(f"Declined {len(files)} file(s) from {sender}", "System", time.time())

    def on_file_offer_failed(self, msg):
        self.play_sound("file_error.wav")
        to = msg.get("to", ""); reason = msg.get("reason", "Unknown error")
        chat = self.frame.get_chat(to)
        if chat: chat.append_error(f"File transfer failed: {reason}")
        else: wx.MessageBox(f"File transfer failed: {reason}", "File Transfer Error", wx.ICON_ERROR)

    def on_file_accepted(self, msg):
        transfer_id = msg["transfer_id"]; to = msg["to"]; files_info = msg["files"]
        file_token = msg.get("file_token", "")
        client_tid = msg.get("client_transfer_id") or transfer_id
        file_paths = self.pending_file_paths.pop(client_tid, None)
        if not file_paths:
            chat = self.frame.get_chat(to)
            if chat: chat.append_error("File transfer error: files no longer available.")
            return
        def _send():
            try:
                files_data = []
                for fp in file_paths:
                    with open(fp, 'rb') as f: files_data.append({"filename": os.path.basename(fp), "data": base64.b64encode(f.read()).decode('ascii')})
                # Keep large payloads off the live messaging socket so normal
                # chat and server commands remain responsive during uploads.
                xfer_sock = create_secure_socket()
                try:
                    xfer_sock.sendall((json.dumps({"action": "file_data", "transfer_id": transfer_id, "file_token": file_token, "to": to, "files": files_data}) + "\n").encode())
                    response = json.loads(xfer_sock.makefile().readline() or "{}")
                finally:
                    xfer_sock.close()
                if response.get("status") != "ok":
                    raise RuntimeError(response.get("reason", "Server rejected file data"))
                names = [os.path.basename(fp) for fp in file_paths]
                wx.CallAfter(self._on_files_sent, to, names, file_paths)
            except Exception as e:
                wx.CallAfter(self._on_file_send_error, to, e)
        threading.Thread(target=_send, daemon=True).start()

    def _on_files_sent(self, to, filenames, file_paths=None):
        self.play_sound("file_send.wav")
        path_map = {os.path.basename(p): p for p in (file_paths or [])}
        for name in filenames:
            wx.GetApp().add_transfer_history("sent", to, name, path_map.get(name, ""), "sent")
        chat = self.frame.get_chat(to)
        if chat:
            names = ", ".join(filenames)
            chat.append(f"{len(filenames)} file(s) sent: {names}", "System", time.time())

    def _on_file_send_error(self, to, error):
        self.play_sound("file_error.wav")
        chat = self.frame.get_chat(to)
        if chat: chat.append_error(f"Failed to send file(s): {error}")

    def on_file_declined(self, msg):
        transfer_id = msg["transfer_id"]; to = msg["to"]; files = msg["files"]
        client_tid = msg.get("client_transfer_id") or transfer_id
        self.pending_file_paths.pop(client_tid, None)
        self.play_sound("file_error.wav")
        names = ", ".join(f["filename"] for f in files)
        chat = self.frame.get_chat(to)
        if chat: chat.append(f"{to} declined your file(s): {names}", "System", time.time())
        else: wx.MessageBox(f"{to} declined your file(s): {names}", "File Declined", wx.ICON_INFORMATION)

    def on_file_data(self, msg):
        sender = msg["from"]; files = msg["files"]
        docs_path = os.path.join(os.path.expanduser('~'), 'Documents')
        save_dir = os.path.join(docs_path, 'ThriveMessenger', 'files')
        os.makedirs(save_dir, exist_ok=True)
        saved = []
        saved_paths = []
        for finfo in files:
            filename = finfo["filename"]; data = finfo["data"]
            try:
                save_path = os.path.join(save_dir, filename)
                if os.path.exists(save_path):
                    name, ext = os.path.splitext(filename)
                    counter = 1
                    while os.path.exists(save_path):
                        save_path = os.path.join(save_dir, f"{name} ({counter}){ext}")
                        counter += 1
                with open(save_path, 'wb') as f: f.write(base64.b64decode(data))
                saved.append(os.path.basename(save_path))
                saved_paths.append(save_path)
                wx.GetApp().add_transfer_history("received", sender, os.path.basename(save_path), save_path, "received")
                for rid, pend in list(self.pending_rerequests.items()):
                    ent = pend.get("entry") or {}
                    if pend.get("offer_seen") and str(pend.get("contact", "")).lower() == str(sender).lower() and ent.get("filename") == filename:
                        ent["path"] = save_path; ent["status"] = "received"
                        self.pending_rerequests.pop(rid, None)
                        self.save_transfer_history()
            except Exception as e:
                self.play_sound("file_error.wav")
                chat = self.frame.get_chat(sender)
                if chat: chat.append_error(f"Failed to save file '{filename}': {e}")
        if saved:
            self.play_sound("file_receive.wav")
            chat = self.frame.get_chat(sender)
            names = ", ".join(saved)
            if chat: chat.append(f"{len(saved)} file(s) received and saved: {names}", "System", time.time(), files=saved_paths)
            else:
                show_notification("Files Received", f"{sender} sent you {len(saved)} file(s)")
            if self.user_config.get('auto_open_received_files', True):
                for path in saved_paths:
                    open_path_or_url(path)

    def send_file_to(self, contact, parent=None):
        if parent is None: parent = self.frame.get_chat(contact) or self.frame
        with wx.FileDialog(parent, "Choose file(s) to send", wildcard="All files (*.*)|*.*", style=wx.FD_OPEN | wx.FD_FILE_MUST_EXIST | wx.FD_MULTIPLE) as dlg:
            if dlg.ShowModal() == wx.ID_CANCEL: return
            file_paths = dlg.GetPaths()
        files = []; valid_paths = []
        for file_path in file_paths:
            filename = os.path.basename(file_path)
            try: size = os.path.getsize(file_path)
            except OSError as e:
                wx.MessageBox(f"Cannot read file '{filename}': {e}", "File Error", wx.ICON_ERROR); continue
            files.append({"filename": filename, "size": size})
            valid_paths.append(file_path)
        if not files: return
        self._offer_files(contact, valid_paths)
    def _offer_files(self, contact, paths, extra=None):
        files = []; valid_paths = []
        for path in paths:
            try:
                files.append({"filename": os.path.basename(path), "size": os.path.getsize(path)})
                valid_paths.append(path)
            except OSError:
                continue
        if not files:
            return False
        transfer_id = str(uuid.uuid4())
        self.pending_file_paths[transfer_id] = valid_paths
        payload = {"action": "file_offer", "to": contact, "files": files, "transfer_id": transfer_id}
        if extra:
            payload.update(extra)
        self.sock.sendall((json.dumps(payload) + "\n").encode())
        chat = self.frame.get_chat(contact)
        if chat:
            names = ", ".join(f["filename"] for f in files)
            chat.append(f"Sending file offer ({len(files)} file(s)): {names}...", "System", time.time())
        return True

class VerificationDialog(wx.Dialog):
    def __init__(self, parent, username):
        super().__init__(parent, title="Account Verification", size=(300, 180)); self.username = username
        panel = wx.Panel(self); s = wx.BoxSizer(wx.VERTICAL)
        dark_mode_on = is_windows_dark_mode()
        if dark_mode_on:
            dark_color = wx.Colour(40, 40, 40); light_text_color = wx.WHITE
            WxMswDarkMode().enable(self); self.SetBackgroundColour(dark_color); panel.SetBackgroundColour(dark_color)
        
        lbl = wx.StaticText(panel, label=f"Enter the code sent to your email:"); s.Add(lbl, 0, wx.ALL, 10)
        self.code_txt = wx.TextCtrl(panel); s.Add(self.code_txt, 0, wx.EXPAND | wx.LEFT | wx.RIGHT, 10)
        btn_sizer = wx.StdDialogButtonSizer(); ok_btn = wx.Button(panel, wx.ID_OK, label="&Verify"); ok_btn.SetDefault(); cancel_btn = wx.Button(panel, wx.ID_CANCEL)
        
        if dark_mode_on:
            lbl.SetForegroundColour(light_text_color); self.code_txt.SetBackgroundColour(dark_color); self.code_txt.SetForegroundColour(light_text_color)
            ok_btn.SetBackgroundColour(dark_color); ok_btn.SetForegroundColour(light_text_color); cancel_btn.SetBackgroundColour(dark_color); cancel_btn.SetForegroundColour(light_text_color)
            
        btn_sizer.AddButton(ok_btn); btn_sizer.AddButton(cancel_btn); btn_sizer.Realize(); s.Add(btn_sizer, 0, wx.ALIGN_CENTER | wx.ALL, 10); panel.SetSizer(s)

class ForgotPasswordDialog(wx.Dialog):
    def __init__(self, parent):
        super().__init__(parent, title="Reset Password", size=(350, 250)); panel = wx.Panel(self); self.sizer = wx.BoxSizer(wx.VERTICAL)
        self.panel = panel
        self.dark_mode_on = is_windows_dark_mode()
        if self.dark_mode_on:
            self.dark_color = wx.Colour(40, 40, 40); self.light_text_color = wx.WHITE
            WxMswDarkMode().enable(self); self.SetBackgroundColour(self.dark_color); panel.SetBackgroundColour(self.dark_color)
        
        self.step1_sizer = wx.BoxSizer(wx.VERTICAL)
        lbl1 = wx.StaticText(panel, label="Enter your registered Email or Username:"); self.email_txt = wx.TextCtrl(panel)
        btn_req = wx.Button(panel, label="Request Reset Code"); btn_req.Bind(wx.EVT_BUTTON, self.on_request)
        self.step1_sizer.Add(lbl1, 0, wx.ALL, 5); self.step1_sizer.Add(self.email_txt, 0, wx.EXPAND | wx.ALL, 5); self.step1_sizer.Add(btn_req, 0, wx.ALIGN_CENTER | wx.ALL, 5)
        
        self.step2_sizer = wx.BoxSizer(wx.VERTICAL)
        lbl2 = wx.StaticText(panel, label="Enter Reset Code:"); self.code_txt = wx.TextCtrl(panel)
        lbl3 = wx.StaticText(panel, label="New Password:"); self.pass_txt = wx.TextCtrl(panel, style=wx.TE_PASSWORD)
        btn_reset = wx.Button(panel, label="Change Password"); btn_reset.Bind(wx.EVT_BUTTON, self.on_reset)
        self.step2_sizer.Add(lbl2, 0, wx.ALL, 5); self.step2_sizer.Add(self.code_txt, 0, wx.EXPAND | wx.ALL, 5)
        self.step2_sizer.Add(lbl3, 0, wx.ALL, 5); self.step2_sizer.Add(self.pass_txt, 0, wx.EXPAND | wx.ALL, 5)
        self.step2_sizer.Add(btn_reset, 0, wx.ALIGN_CENTER | wx.ALL, 5)
        
        self.sizer.Add(self.step1_sizer, 1, wx.EXPAND | wx.ALL, 5); self.sizer.Add(self.step2_sizer, 1, wx.EXPAND | wx.ALL, 5)
        self.sizer.Hide(self.step2_sizer)
        
        if self.dark_mode_on:
            for c in [lbl1, lbl2, lbl3, self.email_txt, self.code_txt, self.pass_txt, btn_req, btn_reset]:
                c.SetForegroundColour(self.light_text_color); 
                if isinstance(c, (wx.TextCtrl, wx.Button)): c.SetBackgroundColour(self.dark_color)

        panel.SetSizer(self.sizer)

    def on_request(self, e):
        ident = self.email_txt.GetValue().strip()
        if not ident: wx.MessageBox("Please enter email or username.", "Error"); return
        try:
            sock = create_secure_socket()
            sock.sendall(json.dumps({"action":"request_reset", "identifier":ident}).encode()+b"\n")
            resp = json.loads(sock.makefile().readline() or "{}"); sock.close()
            if resp.get("status") == "ok":
                wx.MessageBox("If that account exists, a code has been sent.", "Code Sent", wx.ICON_INFORMATION)
                self.username_cache = resp.get("user", ident) 
                self.sizer.Hide(self.step1_sizer); self.sizer.Show(self.step2_sizer); self.panel.Layout()
            else: wx.MessageBox(resp.get("reason", "Error"), "Failed", wx.ICON_ERROR)
        except Exception as ex: wx.MessageBox(str(ex), "Connection Error")

    def on_reset(self, e):
        code = self.code_txt.GetValue().strip(); new_p = self.pass_txt.GetValue()
        if not code or not new_p: return
        try:
            sock = create_secure_socket()
            sock.sendall(json.dumps({"action":"reset_password", "user": self.username_cache, "code": code, "new_pass": new_p}).encode()+b"\n")
            resp = json.loads(sock.makefile().readline() or "{}"); sock.close()
            if resp.get("status") == "ok": wx.MessageBox("Password changed successfully!", "Success"); self.EndModal(wx.ID_OK)
            else: wx.MessageBox(resp.get("reason", "Error"), "Failed", wx.ICON_ERROR)
        except Exception as ex: wx.MessageBox(str(ex), "Connection Error")

class CreateAccountDialog(wx.Dialog):
    def __init__(self, parent, invite_context=None):
        super().__init__(parent, title="Create New Account", size=(300, 330)); panel = wx.Panel(self); s = wx.BoxSizer(wx.VERTICAL)
        self.invite_context = invite_context or {}

        dark_mode_on = is_windows_dark_mode()
        if dark_mode_on:
            dark_color = wx.Colour(40, 40, 40); light_text_color = wx.WHITE
            WxMswDarkMode().enable(self); self.SetBackgroundColour(dark_color); panel.SetBackgroundColour(dark_color)

        user_box = wx.StaticBoxSizer(wx.VERTICAL, panel, "&Username"); self.u_text = wx.TextCtrl(user_box.GetStaticBox()); user_box.Add(self.u_text, 0, wx.EXPAND | wx.ALL, 5)
        email_box = wx.StaticBoxSizer(wx.VERTICAL, panel, "&Email (Optional but recommended)"); self.e_text = wx.TextCtrl(email_box.GetStaticBox()); email_box.Add(self.e_text, 0, wx.EXPAND | wx.ALL, 5)
        pass_box = wx.StaticBoxSizer(wx.VERTICAL, panel, "&Password"); self.p1_text = wx.TextCtrl(pass_box.GetStaticBox(), style=wx.TE_PASSWORD); pass_box.Add(self.p1_text, 0, wx.EXPAND | wx.ALL, 5)
        confirm_box = wx.StaticBoxSizer(wx.VERTICAL, panel, "&Confirm Password"); self.p2_text = wx.TextCtrl(confirm_box.GetStaticBox(), style=wx.TE_PASSWORD); confirm_box.Add(self.p2_text, 0, wx.EXPAND | wx.ALL, 5)
        self.autologin_cb = wx.CheckBox(panel, label="&Log in automatically upon creation"); self.autologin_cb.SetValue(True)
        btn_sizer = wx.StdDialogButtonSizer(); ok_btn = wx.Button(panel, wx.ID_OK, label="&Create"); ok_btn.SetDefault(); ok_btn.Bind(wx.EVT_BUTTON, self.on_create)
        cancel_btn = wx.Button(panel, wx.ID_CANCEL)

        if dark_mode_on:
            for box in [user_box, email_box, pass_box, confirm_box]:
                box.GetStaticBox().SetForegroundColour(light_text_color)
                box.GetStaticBox().SetBackgroundColour(dark_color)
            for ctrl in [self.u_text, self.e_text, self.p1_text, self.p2_text]: ctrl.SetBackgroundColour(dark_color); ctrl.SetForegroundColour(light_text_color)
            ok_btn.SetBackgroundColour(dark_color); ok_btn.SetForegroundColour(light_text_color)
            cancel_btn.SetBackgroundColour(dark_color); cancel_btn.SetForegroundColour(light_text_color)
            self.autologin_cb.SetForegroundColour(light_text_color)

        invite_user = str(self.invite_context.get("invite_user", "") or "").strip()
        invite_email = str(self.invite_context.get("invite_email", "") or "").strip()
        invite_token = str(self.invite_context.get("invite_token", "") or "").strip()
        if invite_token:
            invite_lbl = wx.StaticText(panel, label="Invite link detected. Account fields are prefilled when provided.")
            invite_lbl.Wrap(270)
            if dark_mode_on:
                invite_lbl.SetForegroundColour(light_text_color)
            s.Add(invite_lbl, 0, wx.EXPAND | wx.LEFT | wx.RIGHT | wx.TOP, 8)
        if invite_user:
            self.u_text.SetValue(invite_user)
        if invite_email:
            self.e_text.SetValue(invite_email)

        s.Add(user_box, 0, wx.EXPAND | wx.ALL, 5); s.Add(email_box, 0, wx.EXPAND | wx.ALL, 5); s.Add(pass_box, 0, wx.EXPAND | wx.ALL, 5); s.Add(confirm_box, 0, wx.EXPAND | wx.ALL, 5)
        s.Add(self.autologin_cb, 0, wx.ALL, 10)
        btn_sizer.AddButton(ok_btn); btn_sizer.AddButton(cancel_btn); btn_sizer.Realize(); s.Add(btn_sizer, 0, wx.ALIGN_CENTER | wx.ALL, 5); panel.SetSizer(s)
    
    def on_create(self, event):
        u = self.u_text.GetValue().strip(); p1 = self.p1_text.GetValue(); p2 = self.p2_text.GetValue()
        if not u or not p1: wx.MessageBox("Username and password cannot be blank.", "Validation Error", wx.ICON_ERROR); return
        if p1 != p2: wx.MessageBox("Passwords do not match.", "Validation Error", wx.ICON_ERROR); return
        self.EndModal(wx.ID_OK)

class ServerManagerDialog(wx.Dialog):
    def __init__(self, parent, server_entries, primary_server_name=""):
        super().__init__(parent, title="Server Manager", size=(520, 360))
        self.entries = [normalize_server_entry(e) for e in server_entries]
        entry_names = [e.get('name', '') for e in self.entries]
        if primary_server_name in entry_names:
            self.primary_server_name = primary_server_name
        else:
            self.primary_server_name = self.entries[0]['name'] if self.entries else ""

        panel = wx.Panel(self)
        s = wx.BoxSizer(wx.VERTICAL)

        self.list = wx.ListBox(panel, style=wx.LB_SINGLE)
        self._refresh_list()
        s.Add(self.list, 1, wx.EXPAND | wx.ALL, 8)

        form = wx.FlexGridSizer(2, 4, 6, 6)
        form.AddGrowableCol(1, 1)
        form.AddGrowableCol(3, 1)
        self.name_txt = wx.TextCtrl(panel)
        self.host_txt = wx.TextCtrl(panel)
        self.port_txt = wx.TextCtrl(panel, value="2005")
        self.cafile_txt = wx.TextCtrl(panel)
        form.Add(wx.StaticText(panel, label="Name"), 0, wx.ALIGN_CENTER_VERTICAL)
        form.Add(self.name_txt, 1, wx.EXPAND)
        form.Add(wx.StaticText(panel, label="Host"), 0, wx.ALIGN_CENTER_VERTICAL)
        form.Add(self.host_txt, 1, wx.EXPAND)
        form.Add(wx.StaticText(panel, label="Port"), 0, wx.ALIGN_CENTER_VERTICAL)
        form.Add(self.port_txt, 1, wx.EXPAND)
        form.Add(wx.StaticText(panel, label="CA file (optional)"), 0, wx.ALIGN_CENTER_VERTICAL)
        form.Add(self.cafile_txt, 1, wx.EXPAND)
        s.Add(form, 0, wx.EXPAND | wx.LEFT | wx.RIGHT | wx.BOTTOM, 8)

        btn_row = wx.BoxSizer(wx.HORIZONTAL)
        add_btn = wx.Button(panel, label="Add / Update")
        del_btn = wx.Button(panel, label="Delete")
        primary_btn = wx.Button(panel, label="Set Primary")
        close_btn = wx.Button(panel, wx.ID_OK, label="Done")
        add_btn.Bind(wx.EVT_BUTTON, self.on_add_or_update)
        del_btn.Bind(wx.EVT_BUTTON, self.on_delete)
        primary_btn.Bind(wx.EVT_BUTTON, self.on_set_primary)
        self.list.Bind(wx.EVT_LISTBOX, self.on_select)
        btn_row.Add(add_btn, 0, wx.RIGHT, 6)
        btn_row.Add(del_btn, 0, wx.RIGHT, 6)
        btn_row.Add(primary_btn, 0, wx.RIGHT, 6)
        btn_row.AddStretchSpacer()
        btn_row.Add(close_btn, 0)
        s.Add(btn_row, 0, wx.EXPAND | wx.LEFT | wx.RIGHT | wx.BOTTOM, 8)

        panel.SetSizer(s)

    def _refresh_list(self):
        self.list.Clear()
        for entry in self.entries:
            suffix = " [Primary]" if entry.get('name') == self.primary_server_name else ""
            self.list.Append(f"{entry['name']}{suffix}  |  {entry['host']}:{entry['port']}")

    def on_select(self, event):
        index = event.GetSelection()
        if index < 0 or index >= len(self.entries):
            return
        entry = self.entries[index]
        self.name_txt.SetValue(entry['name'])
        self.host_txt.SetValue(entry['host'])
        self.port_txt.SetValue(str(entry['port']))
        self.cafile_txt.SetValue(entry.get('cafile', ''))

    def on_add_or_update(self, _):
        name = self.name_txt.GetValue().strip()
        host = self.host_txt.GetValue().strip()
        port_text = self.port_txt.GetValue().strip() or "2005"
        cafile = self.cafile_txt.GetValue().strip()
        if not name or not host:
            wx.MessageBox("Name and host are required.", "Validation Error", wx.ICON_ERROR)
            return
        try:
            port = int(port_text)
        except Exception:
            wx.MessageBox("Port must be a valid number.", "Validation Error", wx.ICON_ERROR)
            return
        updated = False
        for i, entry in enumerate(self.entries):
            if entry['name'].lower() == name.lower():
                self.entries[i] = {'name': name, 'host': host, 'port': port, 'cafile': cafile}
                updated = True
                break
        if not updated:
            self.entries.append({'name': name, 'host': host, 'port': port, 'cafile': cafile})
        self.entries = dedupe_server_entries(self.entries)
        self._refresh_list()

    def on_delete(self, _):
        idx = self.list.GetSelection()
        if idx == wx.NOT_FOUND:
            return
        if idx < len(self.entries):
            deleted_name = self.entries[idx].get('name', '')
            del self.entries[idx]
            if deleted_name == self.primary_server_name:
                self.primary_server_name = self.entries[0]['name'] if self.entries else ""
            self._refresh_list()

    def on_set_primary(self, _):
        idx = self.list.GetSelection()
        if idx == wx.NOT_FOUND or idx >= len(self.entries):
            return
        self.primary_server_name = self.entries[idx]['name']
        self._refresh_list()

    def get_entries(self):
        return dedupe_server_entries(self.entries)

    def get_primary_server_name(self):
        names = [e.get('name', '') for e in self.entries]
        if self.primary_server_name in names:
            return self.primary_server_name
        return self.entries[0]['name'] if self.entries else ""

class LoginDialog(wx.Dialog):
    def __init__(self, parent, user_config, invite_context=None):
        super().__init__(parent, title="Login", size=(390, 470)); self.user_config = user_config
        self.invite_context = invite_context or {}
        self.invite_validation = None
        self.login_mode = "password"
        self.Bind(wx.EVT_CHAR_HOOK, self.on_key)
        panel = wx.Panel(self); s = wx.BoxSizer(wx.VERTICAL)
        self.server_entries = dedupe_server_entries(self.user_config.get('server_entries', []))
        if not self.server_entries:
            self.server_entries = [normalize_server_entry(load_server_config())]
        self.primary_server_name = self.user_config.get('primary_server_name', '')
        if self.primary_server_name not in [e['name'] for e in self.server_entries]:
            self.primary_server_name = next((e['name'] for e in self.server_entries if e.get('primary')), self.server_entries[0]['name'])
        self.selected_server = self.server_entries[0]
        
        dark_mode_on = is_windows_dark_mode()
        if dark_mode_on:
            dark_color = wx.Colour(40, 40, 40); light_text_color = wx.WHITE
            WxMswDarkMode().enable(self); self.SetBackgroundColour(dark_color); panel.SetBackgroundColour(dark_color)
            
        server_box = wx.StaticBoxSizer(wx.VERTICAL, panel, "&Server")
        self.server_choice = wx.Choice(server_box.GetStaticBox(), choices=[])
        self.server_choice.Bind(wx.EVT_CHOICE, self.on_server_choice)
        manage_servers_btn = wx.Button(server_box.GetStaticBox(), label="Manage Servers...")
        manage_servers_btn.Bind(wx.EVT_BUTTON, self.on_manage_servers)
        set_primary_btn = wx.Button(server_box.GetStaticBox(), label="Set as Primary")
        set_primary_btn.Bind(wx.EVT_BUTTON, self.on_set_primary_server)
        server_row = wx.BoxSizer(wx.HORIZONTAL)
        server_row.Add(self.server_choice, 1, wx.EXPAND | wx.RIGHT, 4)
        server_row.Add(manage_servers_btn, 0, wx.EXPAND | wx.RIGHT, 4)
        server_row.Add(set_primary_btn, 0, wx.EXPAND)
        server_box.Add(server_row, 0, wx.EXPAND | wx.ALL, 5)
        self.welcome_preview = wx.StaticText(server_box.GetStaticBox(), label="Welcome: (loading...)")
        self.welcome_preview.Wrap(330)
        server_box.Add(self.welcome_preview, 0, wx.EXPAND | wx.LEFT | wx.RIGHT | wx.BOTTOM, 5)
        self.invite_preview = wx.StaticText(server_box.GetStaticBox(), label="")
        self.invite_preview.Wrap(330)
        server_box.Add(self.invite_preview, 0, wx.EXPAND | wx.LEFT | wx.RIGHT | wx.BOTTOM, 5)

        user_box = wx.StaticBoxSizer(wx.VERTICAL, panel, "&Username")
        self.u = wx.TextCtrl(user_box.GetStaticBox()); user_box.Add(self.u, 0, wx.EXPAND | wx.ALL, 5)
        pass_box = wx.StaticBoxSizer(wx.VERTICAL, panel, "&Password"); self.p = wx.TextCtrl(pass_box.GetStaticBox(), style=wx.TE_PASSWORD | wx.TE_PROCESS_ENTER)
        pass_box.Add(self.p, 0, wx.EXPAND | wx.ALL, 5); self.u.SetValue(self.user_config.get('username', ''));
        if self.user_config.get('remember'): self.p.SetValue(self.user_config.get('password', ''))
        self.remember_cb = wx.CheckBox(panel, label="&Remember me")
        self.autologin_cb = wx.CheckBox(panel, label="Log in &automatically")
        remember_default = self.user_config.get('remember', True)
        autologin_default = self.user_config.get('autologin', True)
        self.remember_cb.SetValue(remember_default)
        self.autologin_cb.SetValue(autologin_default if remember_default else False)
        self.remember_cb.Bind(wx.EVT_CHECKBOX, self.on_check_remember)
        
        login_btn = wx.Button(panel, label="&Login"); login_btn.Bind(wx.EVT_BUTTON, self.on_login)
        passkey_btn = wx.Button(panel, label="Login with Passkey")
        passkey_btn.Bind(wx.EVT_BUTTON, self.on_login_passkey)
        create_btn = wx.Button(panel, label="&Create Account..."); create_btn.Bind(wx.EVT_BUTTON, self.on_create_account)
        forgot_btn = wx.Button(panel, label="&Forgot Password?"); forgot_btn.Bind(wx.EVT_BUTTON, self.on_forgot)

        if dark_mode_on:
            for box in [server_box, user_box, pass_box]:
                box.GetStaticBox().SetForegroundColour(light_text_color)
                box.GetStaticBox().SetBackgroundColour(dark_color)
            for ctrl in [self.server_choice, self.u, self.p]:
                ctrl.SetBackgroundColour(dark_color); ctrl.SetForegroundColour(light_text_color)
            for btn in [manage_servers_btn, set_primary_btn, login_btn, passkey_btn, create_btn, forgot_btn]:
                btn.SetBackgroundColour(dark_color); btn.SetForegroundColour(light_text_color)
            self.remember_cb.SetForegroundColour(light_text_color); self.autologin_cb.SetForegroundColour(light_text_color)

        self.populate_server_choice()
        self.welcome_preview.SetLabel("Welcome: loading server information...")
        self.invite_preview.SetLabel("")
        wx.CallAfter(self.schedule_refresh_previews)
        s.Add(server_box, 0, wx.EXPAND | wx.ALL, 5)
        s.Add(user_box, 0, wx.EXPAND | wx.ALL, 5); s.Add(pass_box, 0, wx.EXPAND | wx.ALL, 5)
        s.Add(self.remember_cb, 0, wx.LEFT | wx.RIGHT | wx.BOTTOM, 10); s.Add(self.autologin_cb, 0, wx.LEFT | wx.RIGHT | wx.BOTTOM, 10)
        btn_sizer = wx.BoxSizer(wx.HORIZONTAL); 
        btn_sizer.Add(login_btn, 1, wx.EXPAND | wx.ALL, 2); btn_sizer.Add(passkey_btn, 1, wx.EXPAND | wx.ALL, 2)
        btn_sizer2 = wx.BoxSizer(wx.HORIZONTAL)
        btn_sizer2.Add(create_btn, 1, wx.EXPAND | wx.ALL, 2)
        s.Add(btn_sizer, 0, wx.EXPAND | wx.LEFT | wx.RIGHT, 5)
        s.Add(btn_sizer2, 0, wx.EXPAND | wx.LEFT | wx.RIGHT, 5)
        s.Add(forgot_btn, 0, wx.ALIGN_CENTER | wx.ALL, 5)
        self.p.Bind(wx.EVT_TEXT_ENTER, self.on_login); panel.SetSizer(s); self.on_check_remember(None)

    def populate_server_choice(self):
        self.server_choice.Clear()
        labels = []
        for e in self.server_entries:
            suffix = " [Primary]" if e['name'] == self.primary_server_name else ""
            labels.append(f"{e['name']}{suffix} ({e['host']}:{e['port']})")
        for label in labels:
            self.server_choice.Append(label)
        preferred_name = self.user_config.get('last_server_name', '') or self.primary_server_name
        index = 0
        for i, entry in enumerate(self.server_entries):
            if entry['name'] == preferred_name:
                index = i
                break
        self.server_choice.SetSelection(index if self.server_entries else wx.NOT_FOUND)
        self.selected_server = self.server_entries[index] if self.server_entries else normalize_server_entry(load_server_config())

    def on_server_choice(self, _):
        idx = self.server_choice.GetSelection()
        if 0 <= idx < len(self.server_entries):
            self.selected_server = self.server_entries[idx]
            self.schedule_refresh_previews()

    def on_manage_servers(self, _):
        with ServerManagerDialog(self, self.server_entries, self.primary_server_name) as dlg:
            if dlg.ShowModal() == wx.ID_OK:
                entries = dlg.get_entries()
                if not entries:
                    wx.MessageBox("At least one server entry is required.", "Server Manager", wx.ICON_INFORMATION)
                    return
                self.server_entries = entries
                self.user_config['server_entries'] = self.server_entries
                updated_primary = dlg.get_primary_server_name()
                if updated_primary:
                    self.primary_server_name = updated_primary
                if self.primary_server_name not in [e['name'] for e in self.server_entries]:
                    self.primary_server_name = self.server_entries[0]['name']
                # Keep selection stable where possible
                current_name = self.selected_server.get('name', '')
                self.user_config['last_server_name'] = current_name if any(e['name'] == current_name for e in self.server_entries) else self.server_entries[0]['name']
                self.populate_server_choice()
                self.schedule_refresh_previews()

    def on_set_primary_server(self, _):
        if not self.selected_server:
            return
        self.primary_server_name = self.selected_server.get('name', self.primary_server_name)
        self.populate_server_choice()
        wx.MessageBox(f"{self.primary_server_name} is now your default server.", "Primary Server Updated", wx.OK | wx.ICON_INFORMATION)

    def schedule_refresh_previews(self):
        server_entry = normalize_server_entry(self.selected_server)
        server_key = f"{server_entry.get('host','')}:{server_entry.get('port',0)}"
        self.welcome_preview.SetLabel("Welcome: loading server information...")
        self.invite_preview.SetLabel("Checking invite token..." if self.invite_context.get("invite_token") else "")
        def _worker():
            info = fetch_server_welcome(server_entry)
            snapshot = fetch_server_snapshot(server_entry)
            token = str(self.invite_context.get("invite_token", "") or "").strip()
            validation = fetch_invite_validation(server_entry, token) if token else None
            wx.CallAfter(self._apply_preview_payload, server_key, info, snapshot, validation)
        threading.Thread(target=_worker, daemon=True).start()

    def _apply_preview_payload(self, server_key, info, snapshot, validation):
        current = normalize_server_entry(self.selected_server)
        current_key = f"{current.get('host','')}:{current.get('port',0)}"
        if server_key != current_key:
            return
        pre = str(info.get('pre_login', '') or '').strip()
        guide = (
            "Connection help: Use Manage Servers to add more servers. "
            "Set one as Primary for default login. You can switch servers any time from this menu."
        )
        motd = pre if (info.get('enabled') and pre) else "Welcome to Thrive Messenger."
        stats = (
            f"Server status: {snapshot.get('status', 'Unknown')}\n"
            f"Users online: {snapshot.get('online_users', 'Unknown')}\n"
            f"Admins online: {snapshot.get('online_admin_users', 'Unknown')}\n"
            f"Total users: {snapshot.get('total_users', 'Unknown')}\n"
            f"Server uptime: {snapshot.get('uptime', 'Unknown')}"
        )
        self.welcome_preview.SetLabel(f"{motd}\n\n{stats}\n\n{guide}")
        token = str(self.invite_context.get("invite_token", "") or "").strip()
        if not token:
            self.invite_validation = None
            self.invite_preview.SetLabel("")
        else:
            validation = validation or {"status": "error", "reason": "Invite check failed."}
            if validation.get("status") == "ok":
                self.invite_validation = validation
                invite_user = str(validation.get("invite_user", "") or "").strip()
                invite_email = str(validation.get("invite_email", "") or "").strip()
                who = invite_user or "this account"
                details = f" ({invite_email})" if invite_email else ""
                self.invite_preview.SetLabel(f"Invite ready for {who}{details}. Use Create Account to continue.")
            else:
                self.invite_validation = None
                reason = str(validation.get("reason", "Unknown invite error.") or "Unknown invite error.").strip()
                self.invite_preview.SetLabel(f"Invite link is not valid on this server: {reason}")
        self.Layout()

    def refresh_welcome_preview(self):
        self.schedule_refresh_previews()

    def refresh_invite_preview(self):
        self.schedule_refresh_previews()
    
    def on_forgot(self, event):
        set_active_server_config(self.selected_server)
        with ForgotPasswordDialog(self) as dlg: dlg.ShowModal()

    def on_create_account(self, event):
        set_active_server_config(self.selected_server)
        invite_data = {}
        if self.invite_context and self.invite_context.get("invite_token"):
            invite_data = dict(self.invite_context)
            if self.invite_validation and self.invite_validation.get("status") == "ok":
                invite_data["invite_user"] = self.invite_validation.get("invite_user", invite_data.get("invite_user", ""))
                invite_data["invite_email"] = self.invite_validation.get("invite_email", invite_data.get("invite_email", ""))
        with CreateAccountDialog(self, invite_context=invite_data) as dlg:
            if dlg.ShowModal() == wx.ID_OK:
                u, p, em, auto = dlg.u_text.GetValue(), dlg.p1_text.GetValue(), dlg.e_text.GetValue(), dlg.autologin_cb.IsChecked()
                try:
                    ssock = create_secure_socket()
                    payload = {"action":"create_account","user":u,"pass":p,"email":em}
                    invite_token = str(invite_data.get("invite_token", "") or "").strip()
                    if invite_token:
                        payload["invite_token"] = invite_token
                    ssock.sendall(json.dumps(payload).encode()+b"\n")
                    resp = json.loads(ssock.makefile().readline() or "{}")
                    ssock.close()
                    
                    if resp.get("action") == "verify_pending":
                        wx.MessageBox("A verification code has been sent to your email.", "Verification Required", wx.ICON_INFORMATION)
                        while True:
                            with VerificationDialog(self, u) as vdlg:
                                if vdlg.ShowModal() != wx.ID_OK: break
                                code = vdlg.code_txt.GetValue().strip()
                            sock2 = create_secure_socket()
                            sock2.sendall(json.dumps({"action":"verify_account", "user":u, "code":code}).encode()+b"\n")
                            vresp = json.loads(sock2.makefile().readline() or "{}"); sock2.close()
                            if vresp.get("status") == "ok":
                                wx.MessageBox("Account verified!", "Success")
                                if auto: self.new_username = u; self.new_password = p; self.EndModal(wx.ID_ABORT)
                                break
                            wx.MessageBox("Verification failed: " + vresp.get("reason", "Unknown error"), "Error", wx.ICON_ERROR)
                    elif resp.get("action") == "create_account_success":
                        wx.MessageBox("Account created successfully!", "Success", wx.OK | wx.ICON_INFORMATION)
                        if auto: self.new_username = u; self.new_password = p; self.EndModal(wx.ID_ABORT)
                        else: self.u.SetValue(u); self.p.SetValue("")
                    else: wx.MessageBox("Failed to create account: " + resp.get("reason", "Unknown error"), "Creation Failed", wx.ICON_ERROR)
                except Exception as e: wx.MessageBox(f"A connection error occurred: {e}", "Connection Error", wx.ICON_ERROR)
    
    def on_check_remember(self, event):
        if self.remember_cb.IsChecked(): self.autologin_cb.Enable()
        else: self.autologin_cb.SetValue(False); self.autologin_cb.Disable()
    
    def on_login(self, _):
        u, p = self.u.GetValue(), self.p.GetValue()
        if not u or not p: wx.MessageBox("Username and password cannot be empty.", "Login Error", wx.ICON_ERROR); return
        self.login_mode = "password"
        self.username = u
        self.password = p
        self.remember_checked = self.remember_cb.IsChecked()
        self.autologin_checked = self.autologin_cb.IsChecked()
        for entry in self.server_entries:
            entry['primary'] = (entry.get('name') == self.primary_server_name)
        self.user_config['server_entries'] = self.server_entries
        self.user_config['last_server_name'] = self.selected_server.get('name', '')
        self.user_config['primary_server_name'] = self.primary_server_name
        self.EndModal(wx.ID_OK)

    def on_login_passkey(self, _):
        u = self.u.GetValue().strip()
        if not u:
            wx.MessageBox("Username is required for passkey login.", "Login Error", wx.ICON_ERROR)
            return
        token = _load_passkey_from_keyring(u, settings=self.user_config, server_entry=self.selected_server)
        if not token:
            wx.MessageBox("No passkey is saved for this user on the selected server.", "Passkey Not Found", wx.ICON_ERROR)
            return
        self.login_mode = "passkey"
        self.username = u
        self.password = ""
        self.remember_checked = self.remember_cb.IsChecked()
        self.autologin_checked = self.autologin_cb.IsChecked()
        for entry in self.server_entries:
            entry['primary'] = (entry.get('name') == self.primary_server_name)
        self.user_config['server_entries'] = self.server_entries
        self.user_config['last_server_name'] = self.selected_server.get('name', '')
        self.user_config['primary_server_name'] = self.primary_server_name
        self.EndModal(wx.ID_OK)

    def on_key(self, event):
        if event.GetKeyCode() == wx.WXK_F1:
            open_help_docs_for_context("login", self)
            return
        event.Skip()

def format_size(size_bytes):
    if size_bytes <= 0: return "No limit"
    if size_bytes < 1024: return f"{size_bytes} bytes"
    elif size_bytes < 1048576: return f"{size_bytes / 1024:.1f} KB"
    elif size_bytes < 1073741824: return f"{size_bytes / 1048576:.1f} MB"
    else: return f"{size_bytes / 1073741824:.1f} GB"

def format_duration(total_seconds):
    total_seconds = max(0, int(total_seconds or 0))
    days, rem = divmod(total_seconds, 86400)
    hours, rem = divmod(rem, 3600)
    minutes, seconds = divmod(rem, 60)
    parts = []
    if days:
        parts.append(f"{days}d")
    if hours or parts:
        parts.append(f"{hours}h")
    if minutes or parts:
        parts.append(f"{minutes}m")
    parts.append(f"{seconds}s")
    return " ".join(parts)

def is_chat_logging_enabled(config, username):
    per_user = config.get('chat_logging', {}) if isinstance(config.get('chat_logging', {}), dict) else {}
    if username in per_user:
        return bool(per_user.get(username))
    return bool(config.get('save_chat_history_default', False))

class ServerInfoDialog(wx.Dialog):
    def __init__(self, parent, details_text):
        super().__init__(parent, title="Server Information", size=(560, 420))
        dark_mode_on = is_windows_dark_mode()
        if dark_mode_on:
            dark_color = wx.Colour(40, 40, 40); light_text_color = wx.WHITE
            WxMswDarkMode().enable(self); self.SetBackgroundColour(dark_color)
        s = wx.BoxSizer(wx.VERTICAL)
        self.details = wx.TextCtrl(self, style=wx.TE_MULTILINE | wx.TE_READONLY | wx.TE_RICH2)
        self.details.SetValue(details_text)
        if dark_mode_on:
            self.details.SetBackgroundColour(dark_color); self.details.SetForegroundColour(light_text_color)
        btn = wx.Button(self, wx.ID_OK, label="&Close")
        if dark_mode_on:
            btn.SetBackgroundColour(dark_color); btn.SetForegroundColour(light_text_color)
        self.details.SetToolTip("Server details view. Read-only information about the connected server.")
        s.Add(self.details, 1, wx.EXPAND | wx.ALL, 8); s.Add(btn, 0, wx.ALIGN_CENTER | wx.ALL, 6); self.SetSizer(s)
        self.Bind(wx.EVT_CHAR_HOOK, self.on_key)
    def on_key(self, event):
        if event.GetKeyCode() == wx.WXK_F1:
            open_help_docs_for_context("server_info", self)
        elif event.GetKeyCode() == wx.WXK_ESCAPE: self.Close()
        else: event.Skip()

class FileTransfersDialog(wx.Dialog):
    def __init__(self, parent, history):
        super().__init__(parent, title="File Transfers", size=(760, 420))
        self.history = list(history or [])
        self.panel = wx.Panel(self)
        s = wx.BoxSizer(wx.VERTICAL)
        self.lv = wx.ListCtrl(self.panel, style=wx.LC_REPORT | wx.LC_SINGLE_SEL)
        self.lv.InsertColumn(0, "Time", width=170)
        self.lv.InsertColumn(1, "Direction", width=80)
        self.lv.InsertColumn(2, "User", width=130)
        self.lv.InsertColumn(3, "File", width=160)
        self.lv.InsertColumn(4, "Status", width=90)
        self.lv.InsertColumn(5, "Path", width=260)
        for row in reversed(self.history):
            idx = self.lv.InsertItem(self.lv.GetItemCount(), format_timestamp(row.get("time")))
            self.lv.SetItem(idx, 1, str(row.get("direction", "")))
            self.lv.SetItem(idx, 2, str(row.get("user", "")))
            self.lv.SetItem(idx, 3, str(row.get("filename", "")))
            self.lv.SetItem(idx, 4, str(row.get("status", "")))
            self.lv.SetItem(idx, 5, str(row.get("path", "")))
        s.Add(self.lv, 1, wx.EXPAND | wx.ALL, 8)
        btns = wx.BoxSizer(wx.HORIZONTAL)
        self.btn_open = wx.Button(self.panel, label="Open File")
        self.btn_folder = wx.Button(self.panel, label="Open Folder")
        self.btn_close = wx.Button(self.panel, wx.ID_CLOSE, label="Close")
        self.btn_open.Bind(wx.EVT_BUTTON, self.on_open_file)
        self.btn_folder.Bind(wx.EVT_BUTTON, self.on_open_folder)
        self.btn_close.Bind(wx.EVT_BUTTON, lambda e: self.Close())
        self.lv.Bind(wx.EVT_LIST_ITEM_SELECTED, self.on_select)
        btns.Add(self.btn_open, 0, wx.RIGHT, 6)
        btns.Add(self.btn_folder, 0, wx.RIGHT, 6)
        btns.AddStretchSpacer()
        btns.Add(self.btn_close, 0)
        s.Add(btns, 0, wx.EXPAND | wx.LEFT | wx.RIGHT | wx.BOTTOM, 8)
        self.panel.SetSizer(s)
        self.on_select(None)

    def _selected_path(self):
        idx = self.lv.GetFirstSelected()
        if idx == -1:
            return ""
        return self.lv.GetItemText(idx, 5).strip()

    def on_select(self, _):
        p = self._selected_path()
        exists = bool(p and os.path.exists(p))
        self.btn_open.Enable(exists and os.path.isfile(p))
        self.btn_folder.Enable(exists)

    def on_open_file(self, _):
        p = self._selected_path()
        if p and os.path.isfile(p):
            open_path_or_url(p)

    def on_open_folder(self, _):
        p = self._selected_path()
        if p and os.path.exists(p):
            open_path_or_url(os.path.dirname(p) if os.path.isfile(p) else p)

class SavedMessagesDialog(wx.Dialog):
    def __init__(self, parent, contact_name, grouped_entries):
        super().__init__(parent, title=f"Chat Archive: {contact_name}", size=(760, 500))
        self.panel = wx.Panel(self)
        s = wx.BoxSizer(wx.VERTICAL)
        self.view = wx.TextCtrl(self.panel, style=wx.TE_MULTILINE | wx.TE_READONLY | wx.TE_RICH2)
        self.view.SetToolTip("Chat Archive: saved messages grouped by day.")
        output = []
        for group in grouped_entries:
            output.append(f"=== {group.get('title', 'Unknown Date')} ===")
            for line in group.get('lines', []):
                output.append(str(line))
            output.append("")
        if not output:
            output = ["Nothing in the Chat Archive for this contact yet."]
        self.view.SetValue("\n".join(output).strip() + "\n")
        s.Add(self.view, 1, wx.EXPAND | wx.ALL, 8)
        btn = wx.Button(self.panel, wx.ID_CLOSE, label="Close")
        btn.Bind(wx.EVT_BUTTON, lambda e: self.Close())
        s.Add(btn, 0, wx.ALIGN_CENTER | wx.LEFT | wx.RIGHT | wx.BOTTOM, 8)
        self.panel.SetSizer(s)

class MessageViewerDialog(wx.Dialog):
    """Read-only full view of one chat message, so long or multi-line messages can be read line by line."""
    def __init__(self, parent, sender_label, text, time_label=""):
        title = f"Message from {sender_label}" if sender_label else "Message"
        super().__init__(parent, title=title, size=(760, 520), style=wx.DEFAULT_DIALOG_STYLE | wx.RESIZE_BORDER)
        self.panel = wx.Panel(self)
        s = wx.BoxSizer(wx.VERTICAL)
        heading = f"{sender_label}, {time_label}" if time_label else sender_label
        lbl = wx.StaticText(self.panel, label=f"&Message text ({heading}, {len(text)} characters):")
        s.Add(lbl, 0, wx.LEFT | wx.RIGHT | wx.TOP, 8)
        self.view = wx.TextCtrl(self.panel, style=wx.TE_MULTILINE | wx.TE_READONLY | wx.TE_RICH2)
        self.view.SetName("Message text")
        self.view.SetValue(str(text or ""))
        self.view.SetInsertionPoint(0)
        s.Add(self.view, 1, wx.EXPAND | wx.ALL, 8)
        btn = wx.Button(self.panel, wx.ID_CLOSE, label="Close")
        btn.Bind(wx.EVT_BUTTON, lambda e: self.EndModal(wx.ID_CLOSE))
        self.SetEscapeId(wx.ID_CLOSE)
        s.Add(btn, 0, wx.ALIGN_CENTER | wx.LEFT | wx.RIGHT | wx.BOTTOM, 8)
        self.panel.SetSizer(s)
        self.view.SetFocus()

class UserDirectoryDialog(wx.Dialog):
    def __init__(self, parent_frame, users, my_username, contact_states):
        super().__init__(parent_frame, title="User Directory", size=(550, 500), style=wx.DEFAULT_DIALOG_STYLE | wx.RESIZE_BORDER)
        self.Bind(wx.EVT_CHAR_HOOK, self.on_key)
        self.parent_frame = parent_frame; self.my_username = my_username; self.contact_states = contact_states
        self._all_users = users; self._selected_user = None
        panel = wx.Panel(self)
        dark_mode_on = is_windows_dark_mode()
        if dark_mode_on:
            dc = wx.Colour(40, 40, 40); lt = wx.WHITE
            WxMswDarkMode().enable(self); self.SetBackgroundColour(dc); panel.SetBackgroundColour(dc)
        s = wx.BoxSizer(wx.VERTICAL)
        search_label = wx.StaticText(panel, label="Searc&h:")
        self.search_box = wx.TextCtrl(panel, style=wx.TE_PROCESS_ENTER)
        self.search_box.Bind(wx.EVT_TEXT, self.on_search)
        if dark_mode_on:
            search_label.SetForegroundColour(lt); self.search_box.SetBackgroundColour(dc); self.search_box.SetForegroundColour(lt)
        search_sizer = wx.BoxSizer(wx.HORIZONTAL)
        search_sizer.Add(search_label, 0, wx.ALIGN_CENTER_VERTICAL | wx.RIGHT, 5)
        search_sizer.Add(self.search_box, 1, wx.EXPAND)
        s.Add(search_sizer, 0, wx.EXPAND | wx.ALL, 5)
        sort_sizer = wx.BoxSizer(wx.HORIZONTAL)
        sort_label = wx.StaticText(panel, label="S&ort:")
        self.sort_choice = wx.Choice(panel, choices=["Name (A-Z)", "Name (Z-A)", "Status (Online first)"])
        self.sort_choice.SetSelection(0)
        self.sort_choice.Bind(wx.EVT_CHOICE, self.on_sort_changed)
        filter_label = wx.StaticText(panel, label="Filter:")
        self.filter_choice = wx.Choice(panel, choices=["All users", "In my contacts", "Not in my contacts"])
        self.filter_choice.SetSelection(0)
        self.filter_choice.Bind(wx.EVT_CHOICE, self.on_sort_changed)
        sort_sizer.Add(sort_label, 0, wx.ALIGN_CENTER_VERTICAL | wx.RIGHT, 5)
        sort_sizer.Add(self.sort_choice, 0, wx.RIGHT, 8)
        sort_sizer.Add(filter_label, 0, wx.ALIGN_CENTER_VERTICAL | wx.RIGHT, 5)
        sort_sizer.Add(self.filter_choice, 0, wx.RIGHT, 8)
        s.Add(sort_sizer, 0, wx.LEFT | wx.RIGHT | wx.BOTTOM, 5)
        self.notebook = wx.Notebook(panel)
        self.tabs = {}
        self.tab_display_map = {}
        for tab_name in ["Everyone", "Online", "Offline", "Admins", "Bots"]:
            lv = wx.ListBox(self.notebook, style=wx.LB_SINGLE)
            lv.Bind(wx.EVT_LISTBOX, self.on_selection_changed)
            lv.Bind(wx.EVT_LISTBOX_DCLICK, self.on_item_activated)
            lv.Bind(wx.EVT_CHAR_HOOK, self.on_list_key)
            lv.Bind(wx.EVT_CONTEXT_MENU, self.on_list_context_menu)
            if dark_mode_on: lv.SetBackgroundColour(dc); lv.SetForegroundColour(lt)
            self.notebook.AddPage(lv, tab_name)
            self.tabs[tab_name] = lv
            self.tab_display_map[tab_name] = []
        self.notebook.Bind(wx.EVT_NOTEBOOK_PAGE_CHANGED, self.on_tab_changed)
        if dark_mode_on: self.notebook.SetBackgroundColour(dc); self.notebook.SetForegroundColour(lt)
        s.Add(self.notebook, 1, wx.EXPAND | wx.ALL, 5)
        self.btn_chat = wx.Button(panel, label="&Start Chat"); self.btn_file = wx.Button(panel, label="Send &File")
        self.btn_block = wx.Button(panel, label="&Block"); self.btn_add = wx.Button(panel, label="&Add to Contacts")
        self.btn_close = wx.Button(panel, label="&Close")
        self.btn_chat.Bind(wx.EVT_BUTTON, self.on_start_chat); self.btn_file.Bind(wx.EVT_BUTTON, self.on_send_file)
        self.btn_block.Bind(wx.EVT_BUTTON, self.on_block_toggle); self.btn_add.Bind(wx.EVT_BUTTON, self.on_add_to_contacts)
        self.btn_close.Bind(wx.EVT_BUTTON, lambda e: self.Close())
        if dark_mode_on:
            for btn in [self.btn_chat, self.btn_file, self.btn_block, self.btn_add, self.btn_close]:
                btn.SetBackgroundColour(dc); btn.SetForegroundColour(lt)
        btn_sizer = wx.BoxSizer(wx.HORIZONTAL)
        btn_sizer.Add(self.btn_chat, 1, wx.EXPAND | wx.ALL, 2); btn_sizer.Add(self.btn_file, 1, wx.EXPAND | wx.ALL, 2)
        btn_sizer.Add(self.btn_block, 1, wx.EXPAND | wx.ALL, 2); btn_sizer.Add(self.btn_add, 1, wx.EXPAND | wx.ALL, 2)
        btn_sizer.Add(self.btn_close, 1, wx.EXPAND | wx.ALL, 2)
        s.Add(btn_sizer, 0, wx.EXPAND | wx.ALL, 5)
        panel.SetSizer(s)
        esc_id = wx.NewIdRef()
        self.Bind(wx.EVT_MENU, lambda e: self.Close(), id=esc_id)
        self.SetAcceleratorTable(wx.AcceleratorTable([(wx.ACCEL_NORMAL, wx.WXK_ESCAPE, esc_id)]))
        self.Bind(wx.EVT_CLOSE, self.on_close)
        apply_voiceover_hint(self.search_box, "Search all users in the current directory tab.")
        apply_voiceover_hint(self.sort_choice, "Sort users by name or online status.")
        apply_voiceover_hint(self.filter_choice, "Filter directory users by contact state.")
        apply_voiceover_hint(self.notebook, "Directory tabs for Everyone, Online, Offline, Admins, and Bots.")
        apply_voiceover_hint(self.btn_chat, "Start chat with selected user.")
        apply_voiceover_hint(self.btn_file, "Send a file to selected user.")
        apply_voiceover_hint(self.btn_block, "Block or unblock selected contact.")
        apply_voiceover_hint(self.btn_add, "Send a contact request to selected user.")
        apply_voiceover_hint(self.btn_close, "Close directory window.")
        self._populate_all_tabs(); self.update_button_states()
    def _cross_server_dm_enabled(self):
        return bool(wx.GetApp().user_config.get("allow_cross_server_directory_message", True))
    def _is_current_server_user(self, entry):
        app = wx.GetApp()
        active = normalize_server_entry(getattr(app, "active_server_entry", {}))
        active_host = str(active.get("host", "") or "").strip().lower()
        active_port = int(active.get("port", 0) or 0)
        entry_host = str(entry.get("server_host", "") or "").strip().lower()
        try:
            entry_port = int(entry.get("server_port", 0) or 0)
        except Exception:
            entry_port = 0
        if active_host and entry_host:
            return entry_host == active_host and entry_port == active_port
        active_name = str(active.get("name", "") or "").strip().lower()
        entry_name = str(entry.get("server", "") or "").strip().lower()
        return bool(active_name and entry_name and active_name == entry_name)
    def _get_active_list(self):
        page = self.notebook.GetSelection()
        return self.notebook.GetPage(page) if page != wx.NOT_FOUND else None
    def _get_selected_user(self):
        lv = self._get_active_list()
        if not lv:
            self._selected_user = None
            return None
        sel = lv.GetSelection()
        tab_name = self.notebook.GetPageText(self.notebook.GetSelection())
        mapping = self.tab_display_map.get(tab_name, [])
        if sel != wx.NOT_FOUND and 0 <= sel < len(mapping):
            self._selected_user = mapping[sel].get("user")
            return self._selected_user
        self._selected_user = None
        return None
    def _selected_entry(self):
        lv = self._get_active_list()
        if not lv:
            return None
        sel = lv.GetSelection()
        tab_name = self.notebook.GetPageText(self.notebook.GetSelection())
        mapping = self.tab_display_map.get(tab_name, [])
        if sel != wx.NOT_FOUND and 0 <= sel < len(mapping):
            return mapping[sel]
        return None
    def _ensure_actionable_selection(self):
        lv = self._get_active_list()
        if not lv:
            return
        tab_name = self.notebook.GetPageText(self.notebook.GetSelection())
        mapping = self.tab_display_map.get(tab_name, [])
        sel = lv.GetSelection()
        if sel != wx.NOT_FOUND and 0 <= sel < len(mapping):
            current_user = str(mapping[sel].get("user", "")).strip()
            if current_user and current_user != self.my_username:
                return
        for idx, entry in enumerate(mapping):
            candidate = str(entry.get("user", "")).strip()
            if candidate and candidate != self.my_username:
                lv.SetSelection(idx)
                try:
                    lv.EnsureVisible(idx)
                except Exception:
                    pass
                return
    def _is_selected_external_server(self):
        entry = self._selected_entry()
        if not entry:
            return False
        active = normalize_server_entry(getattr(wx.GetApp(), "active_server_entry", {}))
        active_host = str(active.get("host", "") or "").strip().lower()
        active_port = int(active.get("port", 0) or 0)
        entry_host = str(entry.get("server_host", "") or "").strip().lower()
        try:
            entry_port = int(entry.get("server_port", 0) or 0)
        except Exception:
            entry_port = 0
        if active_host and entry_host:
            return not (entry_host == active_host and entry_port == active_port)
        current_server = str(active.get("name", "") or "").strip().lower()
        selected_server = str(entry.get("server", current_server) or "").strip().lower()
        return bool(selected_server and current_server and selected_server != current_server)
    def _resolve_dm_target_entry(self):
        entry = self._selected_entry()
        if not entry:
            return None
        username = str(entry.get("user", "")).strip()
        if not username:
            return None
        same_user_entries = [u for u in self._all_users if str(u.get("user", "")).strip() == username]
        if len(same_user_entries) <= 1:
            return entry
        app = wx.GetApp()
        defaults = app.user_config.get("directory_dm_defaults", {})
        if not isinstance(defaults, dict):
            defaults = {}
        selected_server = str(entry.get("server", "")).strip()
        preferred_server = str(defaults.get(username, "")).strip()
        # If the user explicitly focused another server row, treat that as selecting a new default.
        if selected_server and selected_server != preferred_server:
            defaults[username] = selected_server
            app.user_config["directory_dm_defaults"] = defaults
            save_user_config(app.user_config)
            return entry
        if preferred_server:
            for u in same_user_entries:
                if str(u.get("server", "")).strip() == preferred_server:
                    return u
        choices = [f"{username} on {u.get('server', 'Current')} ({u.get('status_text', 'unknown')})" for u in same_user_entries]
        with wx.SingleChoiceDialog(self, f"Multiple users named '{username}' were found. Choose who to message.", "Choose User", choices) as dlg:
            if dlg.ShowModal() != wx.ID_OK:
                return None
            idx = dlg.GetSelection()
        if idx < 0 or idx >= len(same_user_entries):
            return None
        chosen = same_user_entries[idx]
        defaults[username] = str(chosen.get("server", "")).strip()
        app.user_config["directory_dm_defaults"] = defaults
        save_user_config(app.user_config)
        return chosen
    def _populate_all_tabs(self):
        query = self.search_box.GetValue().strip().lower()
        filter_mode = self.filter_choice.GetSelection() if hasattr(self, "filter_choice") else 0
        previous_selection_by_tab = {}
        for tab_name, lv in self.tabs.items():
            sel = lv.GetSelection()
            mapping = self.tab_display_map.get(tab_name, [])
            if sel != wx.NOT_FOUND and 0 <= sel < len(mapping):
                previous_selection_by_tab[tab_name] = str(mapping[sel].get("user", "")).strip()

        def _is_online(entry):
            status_text = str(entry.get("status_text", "") or "").strip().lower()
            if status_text.startswith("offline"):
                return False
            return bool(entry.get("online", False))

        for tab_name, lv in self.tabs.items():
            lv.Clear()
            self.tab_display_map[tab_name] = []
            tab_users = []
            for u in self._all_users:
                user_l = u["user"].lower()
                display_name_l = str(pick_user_display_name(u) or "").lower()
                if query and (query not in user_l and query not in display_name_l): continue
                online_now = _is_online(u)
                if tab_name == "Online" and not online_now: continue
                if tab_name == "Offline" and online_now: continue
                if tab_name == "Admins" and not u["is_admin"]: continue
                if tab_name == "Bots":
                    if not bool(u.get("is_bot", False)):
                        continue
                    if not self._is_current_server_user(u):
                        continue
                if filter_mode == 1 and not u.get("is_contact", False): continue
                if filter_mode == 2 and u.get("is_contact", False): continue
                tab_users.append(u)
            mode = self.sort_choice.GetSelection()
            if mode == 1:
                tab_users = sorted(tab_users, key=lambda u: u["user"].lower(), reverse=True)
            elif mode == 2:
                tab_users = sorted(tab_users, key=lambda u: (not _is_online(u), u["user"].lower()))
            else:
                tab_users = sorted(tab_users, key=lambda u: u["user"].lower())
            for u in tab_users:
                info_parts = []
                if u["user"] == self.my_username: info_parts.append("You")
                if u["is_admin"]: info_parts.append("Admin")
                if u["is_contact"]: info_parts.append("Contact")
                if u["is_blocked"]: info_parts.append("Blocked")
                info_text = ", ".join(info_parts)
                display_name = pick_user_display_name(u)
                if not display_name and self.parent_frame and hasattr(self.parent_frame, "get_contact_display_name"):
                    display_name = self.parent_frame.get_contact_display_name(u['user'])
                left = u['user']
                if display_name:
                    left = f"{u['user']} ({display_name})"
                display = f"{left}  |  {u['status_text']}  |  {u.get('server', 'Current')}"
                if info_text:
                    display += f"  |  {info_text}"
                lv.Append(display)
                self.tab_display_map[tab_name].append(u)
            preferred_user = previous_selection_by_tab.get(tab_name, "")
            selected_index = wx.NOT_FOUND
            if preferred_user:
                for i, entry in enumerate(self.tab_display_map[tab_name]):
                    if str(entry.get("user", "")).strip() == preferred_user:
                        selected_index = i
                        break
            if selected_index == wx.NOT_FOUND and lv.GetCount() > 0:
                selected_index = 0
            if selected_index != wx.NOT_FOUND:
                lv.SetSelection(selected_index)
                try:
                    lv.EnsureVisible(selected_index)
                except Exception:
                    pass
        self.update_button_states()
    def on_sort_changed(self, _):
        self._populate_all_tabs()
    def update_button_states(self):
        self._ensure_actionable_selection()
        user = self._get_selected_user()
        external = self._is_selected_external_server()
        allow_cross = self._cross_server_dm_enabled()
        if not user or user == self.my_username:
            self.btn_chat.Disable(); self.btn_file.Disable(); self.btn_block.Disable(); self.btn_add.Disable()
            self.btn_block.SetLabel("&Block"); return
        self.btn_chat.Enable((not external) or allow_cross)
        self.btn_file.Enable(not external)
        is_contact = user in self.contact_states
        self.btn_add.Enable(not is_contact); self.btn_add.SetLabel("&Add to Contacts")
        self.btn_block.Enable(is_contact and (not external))
        if external:
            if allow_cross:
                apply_voiceover_hint(self.btn_chat, "Start chat with this user on their server.")
            else:
                apply_voiceover_hint(self.btn_chat, "Cross-server direct messaging is disabled by admin settings.")
            apply_voiceover_hint(self.btn_file, "This server does not support cross-server file transfer from the current connection.")
            apply_voiceover_hint(self.btn_add, "Add contact will use this username on your current server connection.")
            apply_voiceover_hint(self.btn_block, "This server does not support cross-server contact blocking from the current connection.")
        else:
            apply_voiceover_hint(self.btn_chat, "Start chat with selected user.")
            apply_voiceover_hint(self.btn_file, "Send a file to selected user.")
            apply_voiceover_hint(self.btn_add, "Send a contact request to selected user.")
            apply_voiceover_hint(self.btn_block, "Block or unblock selected contact.")
        if is_contact:
            blocked = self.contact_states.get(user, 0) == 1
            self.btn_block.SetLabel("&Unblock" if blocked else "&Block")
        else:
            self.btn_block.SetLabel("&Block")
    def on_search(self, event): self._populate_all_tabs()
    def on_tab_changed(self, event):
        self._selected_user = None
        lv = self._get_active_list()
        if lv and lv.GetCount() > 0 and lv.GetSelection() == wx.NOT_FOUND:
            lv.SetSelection(0)
            try:
                lv.EnsureVisible(0)
            except Exception:
                pass
        self._ensure_actionable_selection()
        self.update_button_states()
        event.Skip()
    def on_selection_changed(self, event): self.update_button_states(); event.Skip()
    def on_item_activated(self, event):
        self.on_selection_changed(event)
        self.on_start_chat(None)
    def on_start_chat(self, _):
        entry = self._resolve_dm_target_entry()
        if not entry:
            return
        user = str(entry.get("user", "")).strip()
        if not user or user == self.my_username:
            return
        app = wx.GetApp()
        is_logging_enabled = is_chat_logging_enabled(app.user_config, user)
        is_external = False
        current_server = normalize_server_entry(getattr(app, "active_server_entry", {})).get("name", "")
        target_server_name = str(entry.get("server", current_server)).strip()
        if target_server_name and current_server and target_server_name != current_server:
            is_external = True
        if is_external and not self._cross_server_dm_enabled():
            wx.MessageBox("Cross-server direct messaging is disabled by admin settings.", "Feature Disabled", wx.OK | wx.ICON_INFORMATION)
            return
        if is_external:
            target_server_entry = app.resolve_server_entry_by_name(target_server_name)
            if not target_server_entry:
                wx.MessageBox(f"Could not resolve server '{target_server_name}' from configured servers.", "Server Not Found", wx.OK | wx.ICON_ERROR)
                return
            chat_key = f"{user} @ {target_server_name}"
            dlg = self.parent_frame.get_chat(chat_key) or ChatDialog(
                self.parent_frame,
                chat_key,
                self.parent_frame.sock,
                self.parent_frame.user,
                is_logging_enabled,
                is_contact=True,
                remote_server_entry=target_server_entry,
                remote_target_user=user,
                can_call=False,
                show_call=False,
            )
        else:
            is_contact = user in self.contact_states
            dlg = self.parent_frame.get_chat(user) or ChatDialog(
                self.parent_frame,
                user,
                self.parent_frame.sock,
                self.parent_frame.user,
                is_logging_enabled,
                is_contact=is_contact,
                can_call=self.parent_frame.can_use_voice_call(),
                show_call=self.parent_frame.is_voice_call_visible(),
            )
        dlg.open_chat()
    def on_send_file(self, _):
        self._selected_user = self._get_selected_user()
        if self._is_selected_external_server():
            wx.MessageBox("This server does not support cross-server file transfer from the current connection.", "Feature Not Supported", wx.OK | wx.ICON_INFORMATION)
            return
        if self._selected_user: wx.GetApp().send_file_to(self._selected_user)
    def on_block_toggle(self, _):
        user = self._get_selected_user()
        if self._is_selected_external_server():
            wx.MessageBox("This server does not support cross-server contact blocking from the current connection.", "Feature Not Supported", wx.OK | wx.ICON_INFORMATION)
            return
        if not user or user not in self.contact_states: return
        blocked = self.contact_states.get(user, 0) == 1
        action = "unblock_contact" if blocked else "block_contact"
        try:
            self.parent_frame.sock.sendall(json.dumps({"action": action, "to": user}).encode() + b"\n")
        except Exception as e:
            wx.MessageBox(f"Could not update block state for {user}:\n{e}", "Connection Error", wx.OK | wx.ICON_ERROR)
            return
        self.contact_states[user] = 0 if blocked else 1
        for entry in self.parent_frame._all_contacts:
            if entry["user"] == user: entry["blocked"] = 0 if blocked else 1; break
        self.parent_frame._apply_search_filter()
        for u in self._all_users:
            if u["user"] == user: u["is_blocked"] = not blocked; break
        self._populate_all_tabs()
    def on_add_to_contacts(self, _):
        entry = self._selected_entry()
        user = self._get_selected_user()
        if not user: return
        if entry is not None:
            pending_display_name = pick_user_display_name(entry)
            if pending_display_name and self.parent_frame and hasattr(self.parent_frame, "_pending_display_names"):
                self.parent_frame._pending_display_names[user] = pending_display_name
        app = wx.GetApp()
        active = normalize_server_entry(getattr(app, "active_server_entry", {}))
        me = self.parent_frame.user
        def _send_add():
            try:
                self.parent_frame.sock.sendall(json.dumps({"action": "add_contact", "to": user}).encode() + b"\n")
            except Exception as e:
                self.btn_add.Enable()
                self.btn_add.SetLabel("&Add to Contacts")
                show_notification("Add contact failed", f"Could not add {user}: {e}", timeout=6)
                return
            self.btn_add.Disable()
            self.btn_add.SetLabel("Adding...")
        if getattr(app, "session_password", ""):
            self.btn_add.Disable()
            self.btn_add.SetLabel("Checking...")
            def _worker():
                try:
                    users = app.fetch_directory_for_server(active, me, app.session_password)
                    exists = any(str(u.get("user", "")).strip().lower() == user.lower() for u in users)
                except Exception:
                    exists = True
                def _finish():
                    if exists:
                        _send_add()
                    else:
                        self.btn_add.Enable()
                        self.btn_add.SetLabel("&Add to Contacts")
                        show_notification(
                            "Contact tip",
                            f"{user} is not on the current server yet. Open Server Directory to find available users.",
                            timeout=8,
                        )
                wx.CallAfter(_finish)
            threading.Thread(target=_worker, daemon=True).start()
            return
        _send_add()
    def _select_user_from_context_event(self, event):
        lv = self._get_active_list()
        if not lv:
            return
        try:
            pos = event.GetPosition()
        except Exception:
            pos = wx.DefaultPosition
        try:
            if isinstance(pos, wx.Point) and pos.x >= 0 and pos.y >= 0:
                idx = lv.HitTest(lv.ScreenToClient(pos))
                if idx != wx.NOT_FOUND:
                    lv.SetSelection(idx)
        except Exception:
            pass
        if lv.GetSelection() == wx.NOT_FOUND and lv.GetCount() > 0:
            lv.SetSelection(0)
    def on_list_context_menu(self, event):
        self._select_user_from_context_event(event)
        self._selected_user = self._get_selected_user()
        selected = bool(self._selected_user and self._selected_user != self.my_username)
        external = self._is_selected_external_server()
        allow_cross = self._cross_server_dm_enabled()
        is_contact = bool(self._selected_user and self._selected_user in self.contact_states)
        menu = wx.Menu()
        mi_chat = menu.Append(wx.ID_ANY, "Start Chat")
        mi_add = menu.Append(wx.ID_ANY, "Add to Contacts")
        mi_block = menu.Append(wx.ID_ANY, "Block/Unblock")
        mi_file = menu.Append(wx.ID_ANY, "Send File")
        menu.AppendSeparator()
        mi_refresh = menu.Append(wx.ID_ANY, "Refresh Directory")
        mi_chat.Enable(selected and ((not external) or allow_cross))
        mi_add.Enable(selected and (not is_contact))
        mi_block.Enable(selected and is_contact and not external)
        mi_file.Enable(selected and not external)
        self.Bind(wx.EVT_MENU, self.on_start_chat, id=mi_chat.GetId())
        self.Bind(wx.EVT_MENU, self.on_add_to_contacts, id=mi_add.GetId())
        self.Bind(wx.EVT_MENU, self.on_block_toggle, id=mi_block.GetId())
        self.Bind(wx.EVT_MENU, self.on_send_file, id=mi_file.GetId())
        self.Bind(wx.EVT_MENU, lambda e: self.parent_frame.on_user_directory(None), id=mi_refresh.GetId())
        self.PopupMenu(menu)
        menu.Destroy()
    def on_list_key(self, event):
        if event.GetKeyCode() == wx.WXK_F1:
            open_help_docs_for_context("directory", self)
            return
        if event.GetKeyCode() in (wx.WXK_RETURN, wx.WXK_NUMPAD_ENTER):
            self.on_start_chat(None)
            return
        if event.GetKeyCode() == wx.WXK_TAB:
            if event.ShiftDown():
                self.notebook.SetFocus()
            else:
                self.btn_chat.SetFocus()
            return
        event.Skip()
    def on_close(self, event):
        if self.parent_frame: self.parent_frame._directory_dlg = None
        self.Destroy()
    def on_key(self, event):
        if event.GetKeyCode() == wx.WXK_F1:
            open_help_docs_for_context("directory", self)
            return
        if event.GetKeyCode() in (wx.WXK_RETURN, wx.WXK_NUMPAD_ENTER):
            focused = wx.Window.FindFocus()
            if isinstance(focused, wx.Button):
                click_evt = wx.CommandEvent(wx.EVT_BUTTON.typeId, focused.GetId())
                focused.GetEventHandler().ProcessEvent(click_evt)
                return
        event.Skip()

    def merge_external_users(self, users):
        merged = {(u.get("user"), u.get("server", "Current")): u for u in self._all_users}
        for u in users:
            key = (u.get("user"), u.get("server", "External"))
            if key not in merged:
                merged[key] = u
        self._all_users = list(merged.values())
        self._populate_all_tabs()

class InviteUserDialog(wx.Dialog):
    def __init__(self, parent, username, methods=None):
        super().__init__(parent, title=f"Invite {username}", size=(460, 260))
        self.username = username
        panel = wx.Panel(self)
        s = wx.BoxSizer(wx.VERTICAL)
        s.Add(wx.StaticText(panel, label=f"Invite '{username}' to this server"), 0, wx.ALL, 8)
        row2 = wx.BoxSizer(wx.HORIZONTAL)
        row2.Add(wx.StaticText(panel, label="Email or phone:"), 0, wx.ALIGN_CENTER_VERTICAL | wx.RIGHT, 6)
        self.target = wx.TextCtrl(panel)
        row2.Add(self.target, 1, wx.EXPAND)
        s.Add(row2, 0, wx.EXPAND | wx.LEFT | wx.RIGHT | wx.BOTTOM, 8)
        self.include_link = wx.CheckBox(panel, label="Include setup link in invite message")
        self.include_link.SetValue(True)
        s.Add(self.include_link, 0, wx.LEFT | wx.RIGHT | wx.BOTTOM, 8)
        hint = wx.StaticText(panel, label="Enter an email address or phone number. The app sends the invite automatically.")
        s.Add(hint, 0, wx.LEFT | wx.RIGHT | wx.BOTTOM, 8)
        buttons = wx.StdDialogButtonSizer()
        ok_btn = wx.Button(panel, wx.ID_OK, label="Send Invite")
        cancel_btn = wx.Button(panel, wx.ID_CANCEL)
        ok_btn.SetDefault()
        buttons.AddButton(ok_btn)
        buttons.AddButton(cancel_btn)
        buttons.Realize()
        s.Add(buttons, 0, wx.ALIGN_CENTER | wx.ALL, 8)
        panel.SetSizer(s)

    def get_method(self):
        target = self.get_target()
        return "email" if "@" in target else "sms"

    def get_target(self):
        return self.target.GetValue().strip()

    def should_include_link(self):
        return self.include_link.IsChecked()

class MainFrame(wx.Frame):
    def _display_name_map(self):
        app = wx.GetApp()
        mapping = app.user_config.get("contact_display_names", {})
        if not isinstance(mapping, dict):
            mapping = {}
            app.user_config["contact_display_names"] = mapping
        return mapping

    def get_contact_display_name(self, username):
        if not username:
            return ""
        return str(self._display_name_map().get(username, "") or "").strip()

    def set_contact_display_name(self, username, display_name):
        if not username:
            return
        mapping = self._display_name_map()
        if display_name:
            mapping[username] = str(display_name).strip()
        else:
            mapping.pop(username, None)
        wx.GetApp().user_config["contact_display_names"] = mapping
        save_user_config(wx.GetApp().user_config)

    def format_user_label(self, username, include_username=False):
        name = str(username or "").strip()
        if not name:
            return ""
        if name == "System":
            return "System"
        prefer = bool(wx.GetApp().user_config.get("prefer_contact_display_names", False))
        display_name = self.get_contact_display_name(name)
        if display_name and prefer:
            return f"{display_name} ({name})" if include_username else display_name
        return name

    def _build_connection_title(self):
        app = wx.GetApp()
        active_server = normalize_server_entry(getattr(app, "active_server_entry", {}))
        server_name = active_server.get("name") or active_server.get("host") or SERVER_CONFIG.get("host", "Server")
        connected_names = set(getattr(app, "connected_server_names", set()) or {server_name})
        others = max(0, len(connected_names) - 1)
        suffix = f", and {others} other server{'s' if others != 1 else ''}" if others > 0 else ""
        return f"Thrive Messenger – {self.user} – connected to {server_name}{suffix}"

    def refresh_connection_title(self, connected=True):
        base = self._build_connection_title()
        if connected:
            self.SetTitle(base)
        else:
            self.SetTitle(f"{base} (reconnecting...)")

    def set_socket(self, sock):
        self.sock = sock
        for panel in self.all_chats():
            panel._sock = sock
        for child in self.GetChildren():
            if hasattr(child, 'sock'):
                try:
                    child.sock = sock
                except Exception:
                    pass
        if self._directory_dlg and hasattr(self._directory_dlg, 'sock'):
            try:
                self._directory_dlg.sock = sock
            except Exception:
                pass

    def update_contact_status(self, user, online, status_text=None):
        was_online = False
        for c in self._all_contacts:
            if c["user"] == user:
                was_online = c["status"] != "offline" and not c["status"].startswith("offline")
                is_admin = "(Admin)" in c["status"]
                new_status = status_text if status_text else ("online" if online else "offline")
                if not online: new_status = "offline"
                if is_admin: new_status += " (Admin)"
                c["status"] = new_status
                break
        self._apply_search_filter()
        if online and not was_online:
            wx.GetApp().play_sound("contact_online.wav")
            show_notification("Contact online", f"{self.format_user_label(user)} has come online.")
        elif not online and was_online:
            wx.GetApp().play_sound("contact_offline.wav")
            show_notification("Contact offline", f"{self.format_user_label(user)} has gone offline.")

    def __init__(self, user, sock):
        super().__init__(None, title="", size=(1000,650)); self.user, self.sock = user, sock; self.task_bar_icon = None; self.is_exiting = False; self._directory_dlg = None; self._bot_rules_dlg = None; self._group_policy_dlg = None; self._group_call_dlg = None; self._module_dialog = None
        self.refresh_connection_title(connected=True)
        self.current_status = wx.GetApp().user_config.get('status', 'online')
        self.feature_caps = {}
        self.feature_caps_supported = False
        self._empty_prompt_shown = False
        self._empty_contacts_tip_scheduled = False
        self._sort_mode = "name_asc"
        self._unread_counts = {}
        self._pending_display_names = {}
        self._passkey_response_lock = threading.Lock()
        self._passkey_request_lock = threading.Lock()
        self._passkey_response_events = {}
        self._passkey_responses = {}
        self.notifications = []; self.Bind(wx.EVT_CLOSE, self.on_close_window)
        self._chat_panels = []; self._tabs_window = None
        self.main_notebook = wx.Notebook(self)
        panel = wx.Panel(self.main_notebook)

        dark_mode_on = is_windows_dark_mode()
        if dark_mode_on:
            dark_color = wx.Colour(40, 40, 40); light_text_color = wx.WHITE
            WxMswDarkMode().enable(self); self.SetBackgroundColour(dark_color); panel.SetBackgroundColour(dark_color)

        self._all_contacts = []
        self.contact_states = {}
        self._contact_display_map = []
        box_contacts = wx.StaticBoxSizer(wx.VERTICAL, panel, "&Contacts")
        search_label = wx.StaticText(box_contacts.GetStaticBox(), label="Searc&h contacts:")
        self.search_box = F3SearchTextCtrl(box_contacts.GetStaticBox(), style=wx.TE_PROCESS_ENTER)
        self.search_box.Bind(wx.EVT_TEXT, self.on_search)
        self.lv = wx.ListBox(box_contacts.GetStaticBox(), style=wx.LB_SINGLE)
        self.lv.Bind(wx.EVT_CHAR_HOOK, self.on_key)
        self.lv.Bind(wx.EVT_LISTBOX, self.update_button_states)
        self.lv.Bind(wx.EVT_LISTBOX_DCLICK, self.on_contact_activated)
        self.lv.Bind(wx.EVT_CONTEXT_MENU, self.on_contact_context_menu)

        if dark_mode_on:
            box_contacts.GetStaticBox().SetForegroundColour(light_text_color)
            box_contacts.GetStaticBox().SetBackgroundColour(dark_color)
            search_label.SetForegroundColour(light_text_color)
            self.search_box.SetBackgroundColour(dark_color); self.search_box.SetForegroundColour(light_text_color)
            self.lv.SetBackgroundColour(dark_color); self.lv.SetForegroundColour(light_text_color)

        # Keep search controls stacked so assistive tech presents list navigation clearly.
        box_contacts.Add(search_label, 0, wx.LEFT | wx.RIGHT | wx.TOP, 5)
        box_contacts.Add(self.search_box, 0, wx.EXPAND | wx.LEFT | wx.RIGHT | wx.BOTTOM, 5)
        box_contacts.Add(self.lv, 1, wx.EXPAND|wx.ALL, 5)
        self.btn_block = wx.Button(panel, label="&Block"); self.btn_add = wx.Button(panel, label="&Add Contact"); self.btn_send = wx.Button(panel, label="&Start Chat"); self.btn_delete = wx.Button(panel, label="&Delete Contact")
        self.btn_send_file = wx.Button(panel, label="Send &File")
        self.btn_info = wx.Button(panel, label="Server &Info")
        self.btn_status = wx.Button(panel, label="Set Stat&us...")
        self.btn_directory = wx.Button(panel, label="User Director&y")
        self.btn_admin = wx.Button(panel, label="Use Ser&ver Side Commands"); self.btn_settings = wx.Button(panel, label="Se&ttings...")
        self.btn_update = wx.Button(panel, label="Check for U&pdates")
        self.btn_logout = wx.Button(panel, label="L&ogout"); self.btn_exit = wx.Button(panel, label="E&xit")

        if dark_mode_on:
            buttons = [self.btn_block, self.btn_add, self.btn_send, self.btn_delete, self.btn_send_file, self.btn_info, self.btn_status, self.btn_directory, self.btn_admin, self.btn_settings, self.btn_update, self.btn_logout, self.btn_exit]
            for btn in buttons:
                btn.SetBackgroundColour(dark_color)
                btn.SetForegroundColour(light_text_color)
                
        self.btn_block.Bind(wx.EVT_BUTTON, self.on_block_toggle); self.btn_add.Bind(wx.EVT_BUTTON, self.on_add); self.btn_send.Bind(wx.EVT_BUTTON, self.on_send); self.btn_delete.Bind(wx.EVT_BUTTON, self.on_delete)
        self.btn_send_file.Bind(wx.EVT_BUTTON, self.on_send_file)
        self.btn_info.Bind(wx.EVT_BUTTON, self.on_server_info)
        self.btn_status.Bind(wx.EVT_BUTTON, self.on_set_status)
        self.btn_directory.Bind(wx.EVT_BUTTON, self.on_user_directory)
        self.btn_admin.Bind(wx.EVT_BUTTON, self.on_admin); self.btn_settings.Bind(wx.EVT_BUTTON, self.on_settings)
        self.btn_update.Bind(wx.EVT_BUTTON, self.on_check_updates)
        self.btn_logout.Bind(wx.EVT_BUTTON, self.on_logout); self.btn_exit.Bind(wx.EVT_BUTTON, self.on_exit)
        self.search_command_id = wx.NewIdRef()
        accel_entries = [(wx.ACCEL_NORMAL, wx.WXK_F3, int(self.search_command_id)), (wx.ACCEL_ALT, ord('B'), self.btn_block.GetId()), (wx.ACCEL_ALT, ord('A'), self.btn_add.GetId()), (wx.ACCEL_ALT, ord('S'), self.btn_send.GetId()), (wx.ACCEL_ALT, ord('D'), self.btn_delete.GetId()), (wx.ACCEL_ALT, ord('F'), self.btn_send_file.GetId()), (wx.ACCEL_ALT, ord('I'), self.btn_info.GetId()), (wx.ACCEL_ALT, ord('U'), self.btn_status.GetId()), (wx.ACCEL_ALT, ord('Y'), self.btn_directory.GetId()), (wx.ACCEL_ALT, ord('V'), self.btn_admin.GetId()), (wx.ACCEL_ALT, ord('T'), self.btn_settings.GetId()), (wx.ACCEL_ALT, ord('P'), self.btn_update.GetId()), (wx.ACCEL_ALT, ord('O'), self.btn_logout.GetId()), (wx.ACCEL_ALT, ord('X'), self.btn_exit.GetId()),]
        accel_tbl = wx.AcceleratorTable(accel_entries); self.SetAcceleratorTable(accel_tbl)
        self.Bind(wx.EVT_MENU, self.on_focus_contact_search, id=int(self.search_command_id))
        self.gs_main = wx.GridSizer(1, 5, 5, 5); self.gs_main.Add(self.btn_block, 0, wx.EXPAND); self.gs_main.Add(self.btn_add, 0, wx.EXPAND); self.gs_main.Add(self.btn_send, 0, wx.EXPAND); self.gs_main.Add(self.btn_send_file, 0, wx.EXPAND); self.gs_main.Add(self.btn_delete, 0, wx.EXPAND)
        self.gs_util = wx.GridSizer(1, 8, 5, 5); self.gs_util.Add(self.btn_info, 0, wx.EXPAND); self.gs_util.Add(self.btn_status, 0, wx.EXPAND); self.gs_util.Add(self.btn_directory, 0, wx.EXPAND); self.gs_util.Add(self.btn_admin, 0, wx.EXPAND); self.gs_util.Add(self.btn_settings, 0, wx.EXPAND); self.gs_util.Add(self.btn_update, 0, wx.EXPAND); self.gs_util.Add(self.btn_logout, 0, wx.EXPAND); self.gs_util.Add(self.btn_exit, 0, wx.EXPAND)
        s = wx.BoxSizer(wx.VERTICAL); s.Add(box_contacts, 1, wx.EXPAND|wx.ALL, 5); s.Add(self.gs_main, 0, wx.CENTER|wx.ALL, 5); s.Add(self.gs_util, 0, wx.CENTER|wx.ALL, 5); panel.SetSizer(s)
        self.groups_panel = GroupRoomsPanel(self.main_notebook, self, self.sock, self.user)
        self.main_notebook.AddPage(panel, "Contacts")
        self.main_notebook.AddPage(self.groups_panel, "Groups")
        frame_sizer = wx.BoxSizer(wx.VERTICAL)
        frame_sizer.Add(self.main_notebook, 1, wx.EXPAND)
        self.SetSizer(frame_sizer)
        self._root_sizer = s
        self._build_menu_bar()
        self._apply_voiceover_hints(search_label)
        self.Bind(wx.EVT_CHAR_HOOK, self.on_key)
        self.apply_action_button_layout()
        self.update_button_states()
        self.apply_feature_visibility()
        wx.CallAfter(self.groups_panel.refresh_rooms)

    def on_group_room_action(self, msg):
        if self.groups_panel:
            self.groups_panel.handle_server_action(msg)
    def on_manage_modules(self, _):
        if self._module_dialog and self._module_dialog.IsShown():
            self._module_dialog.Raise(); return
        self._module_dialog = ModuleManagerDialog(self, self.sock)
        self._module_dialog.Show()
        self.sock.sendall((json.dumps({"action": "module_list"}) + "\n").encode())
    def on_module_action(self, msg):
        if self._module_dialog and self._module_dialog.IsShown():
            self._module_dialog.handle_server_action(msg)

    def open_direct_chat(self, username):
        username = str(username or "").strip()
        if not username or username == self.user:
            return
        app = wx.GetApp()
        dlg = self.get_chat(username) or ChatDialog(
            self, username, self.sock, self.user,
            is_chat_logging_enabled(app.user_config, username),
            is_contact=username in getattr(self, "contact_states", {}),
            can_call=self.can_use_voice_call(), show_call=self.is_voice_call_visible(),
        )
        dlg.open_chat()

    def _feature(self, key):
        if self.feature_caps_supported:
            return self.feature_caps.get(key, {})
        return LEGACY_SAFE_FEATURE_CAPS.get(key, {"enabled": False, "ui_visible": False, "scope": "all", "can_use": False})

    def _feature_any(self, keys):
        for key in keys:
            cap = self._feature(key)
            if cap:
                return cap
        return {}

    def _feature_can_use(self, key):
        cap = self._feature(key)
        if not cap:
            return True
        return bool(cap.get("enabled", False) and cap.get("can_use", False))

    def _feature_ui_visible(self, key):
        cap = self._feature(key)
        if not cap:
            return True
        return bool(cap.get("enabled", False) and cap.get("ui_visible", True))

    def can_use_voice_call(self):
        # Support capability naming variants while enforcing role/capability gating.
        cap = self._feature_any(("voice_call", "call", "calls"))
        if not cap:
            return False
        return bool(cap.get("enabled", False) and cap.get("can_use", False))

    def is_voice_call_visible(self):
        cap = self._feature_any(("voice_call", "call", "calls"))
        if not cap:
            return False
        return bool(cap.get("enabled", False) and cap.get("ui_visible", True))

    def set_feature_caps(self, caps):
        if not isinstance(caps, dict):
            return
        self.feature_caps = caps
        self.feature_caps_supported = bool(caps)
        self.apply_feature_visibility()
        self._refresh_open_chat_permissions()

    def apply_feature_visibility(self):
        group_calls_visible = self._feature_ui_visible("group_call")
        group_calls_enabled = self._feature_can_use("group_call")
        self.mi_group_calls.Enable(group_calls_enabled and group_calls_visible)
        if group_calls_visible:
            self.mi_group_calls.SetItemLabel("Group Calls")
        else:
            hidden_reason = "server policy" if self.feature_caps_supported else "server compatibility mode"
            self.mi_group_calls.SetItemLabel(f"Group Calls (Hidden by {hidden_reason})")

        server_mgr_visible = self._feature_ui_visible("server_manager")
        server_mgr_enabled = self._feature_can_use("server_manager")
        self.mi_server_manager.Enable(server_mgr_enabled and server_mgr_visible)

        bot_rules_visible = self._feature_ui_visible("bot_rules")
        bot_rules_enabled = self._feature_can_use("bot_rules")
        self.mi_bot_rules.Enable(bot_rules_enabled and bot_rules_visible)

        group_policy_visible = self._feature_ui_visible("group_policy")
        group_policy_enabled = self._feature_can_use("group_policy")
        self.mi_group_policy.Enable(group_policy_enabled and group_policy_visible)

        admin_visible = self._feature_ui_visible("admin_console")
        admin_enabled = self._feature_can_use("admin_console")
        self.mi_admin_visible = admin_visible
        self.btn_admin.Show(admin_visible)
        self.btn_admin.Enable(admin_enabled and admin_visible)
        if hasattr(self, "btn_settings"):
            self.btn_settings.Refresh()
        self.Layout()

    def _refresh_open_chat_permissions(self):
        can_call = self.can_use_voice_call()
        show_call = self.is_voice_call_visible()
        for child in self.all_chats():
            child.apply_call_permissions(can_call, show_call)

    def apply_action_button_layout(self):
        show_actions = bool(wx.GetApp().user_config.get('show_main_action_buttons', True))
        for btn in [self.btn_block, self.btn_send, self.btn_send_file, self.btn_delete, self.btn_info, self.btn_status, self.btn_directory, self.btn_settings, self.btn_update, self.btn_logout, self.btn_exit]:
            btn.Show(show_actions)
        # Keep add contact visible for keyboard/tab workflow.
        self.btn_add.Show(True)
        self.btn_admin.Show(bool(show_actions and getattr(self, "mi_admin_visible", False)))
        self.btn_admin.Enable(bool(getattr(self, "mi_admin_visible", False) and self._feature_can_use("admin_console")))
        if self._root_sizer:
            self._root_sizer.Layout()

    def _build_menu_bar(self):
        menubar = wx.MenuBar()
        file_menu = wx.Menu()
        self.mi_start_chat = file_menu.Append(wx.ID_ANY, "Start Chat\tReturn")
        self.mi_add_contact = file_menu.Append(wx.ID_ANY, "Add Contact\tAlt+A")
        self.mi_delete_contact = file_menu.Append(wx.ID_ANY, "Delete Contact\tDelete")
        self.mi_send_file = file_menu.Append(wx.ID_ANY, "Send File\tAlt+F")
        self.mi_file_transfers = file_menu.Append(wx.ID_ANY, "File Transfers")
        self.mi_voicemail = file_menu.Append(wx.ID_ANY, "&Voicemail...")
        self.mi_group_calls = file_menu.Append(wx.ID_ANY, "Group Calls")
        file_menu.AppendSeparator()
        self.mi_user_directory = file_menu.Append(wx.ID_ANY, "User Directory\tAlt+Y")
        self.mi_server_info = file_menu.Append(wx.ID_ANY, "Server Info\tAlt+I")
        self.mi_server_manager = file_menu.Append(wx.ID_ANY, "Server Manager")
        self.mi_bot_rules = file_menu.Append(wx.ID_ANY, "Manage Bot Rules")
        self.mi_group_policy = file_menu.Append(wx.ID_ANY, "Manage Group Policy")
        self.mi_settings = file_menu.Append(wx.ID_PREFERENCES, "Settings\tCmd+,")
        self.mi_register_passkey = file_menu.Append(wx.ID_ANY, "Register Passkey For This Device")
        self.mi_manage_devices = file_menu.Append(wx.ID_ANY, "Manage Signed-In Devices")
        file_menu.AppendSeparator()
        self.mi_logout = file_menu.Append(wx.ID_ANY, "Logout\tAlt+O")
        self.mi_exit = file_menu.Append(wx.ID_ANY, "Exit\tAlt+X")

        contacts_menu = wx.Menu()
        self.mi_block_toggle = contacts_menu.Append(wx.ID_ANY, "Block/Unblock\tAlt+B")
        self.mi_toggle_chat_log = contacts_menu.Append(wx.ID_ANY, "Toggle Chat History For Selected Contact")
        self.mi_refresh_directory = contacts_menu.Append(wx.ID_ANY, "Refresh Directory")
        user_menu = wx.Menu()
        self.mi_user_start_chat = user_menu.Append(wx.ID_ANY, "Start Chat")
        self.mi_user_send_file = user_menu.Append(wx.ID_ANY, "Send File")
        self.mi_user_transfers = user_menu.Append(wx.ID_ANY, "File Transfers")
        self.mi_user_add_contact = user_menu.Append(wx.ID_ANY, "Add Contact")
        self.mi_user_toggle_block = user_menu.Append(wx.ID_ANY, "Block/Unblock")
        self.mi_user_toggle_history = user_menu.Append(wx.ID_ANY, "Toggle Chat History")
        self.mi_user_delete_contact = user_menu.Append(wx.ID_ANY, "Delete Contact")

        view_menu = wx.Menu()
        self.mi_sort_name_asc = view_menu.AppendRadioItem(wx.ID_ANY, "Sort: Name (A-Z)")
        self.mi_sort_name_desc = view_menu.AppendRadioItem(wx.ID_ANY, "Sort: Name (Z-A)")
        self.mi_sort_status = view_menu.AppendRadioItem(wx.ID_ANY, "Sort: Status (Online first)")
        self.mi_sort_name_asc.Check(True)

        help_menu = wx.Menu()
        self.mi_help = help_menu.Append(wx.ID_ANY, "Help\tF1")
        demo_menu = wx.Menu()
        self.mi_demo_onboarding = demo_menu.Append(wx.ID_ANY, "Watch Onboarding Demo")
        self.mi_demo_chat_files = demo_menu.Append(wx.ID_ANY, "Watch Chat and File Demo")
        self.mi_demo_admin_tools = demo_menu.Append(wx.ID_ANY, "Watch Admin Tools Demo")
        demo_menu.AppendSeparator()
        self.mi_demo_videos = demo_menu.Append(wx.ID_ANY, "Open Demo Videos Folder")
        help_menu.AppendSubMenu(demo_menu, "Watch Demo Videos")
        self.mi_submit_logs = help_menu.Append(wx.ID_ANY, "Submit Diagnostic Logs")

        menubar.Append(file_menu, "&File")
        menubar.Append(contacts_menu, "&Contacts")
        menubar.Append(user_menu, "&User")
        menubar.Append(view_menu, "&View")
        menubar.Append(help_menu, "&Help")
        self.SetMenuBar(menubar)

        self.Bind(wx.EVT_MENU, self.on_send, self.mi_start_chat)
        self.Bind(wx.EVT_MENU, self.on_add, self.mi_add_contact)
        self.Bind(wx.EVT_MENU, self.on_delete, self.mi_delete_contact)
        self.Bind(wx.EVT_MENU, self.on_send_file, self.mi_send_file)
        self.Bind(wx.EVT_MENU, self.on_file_transfers, self.mi_file_transfers)
        self.Bind(wx.EVT_MENU, self.on_voicemail_list, self.mi_voicemail)
        self.Bind(wx.EVT_MENU, self.on_group_calls, self.mi_group_calls)
        self.Bind(wx.EVT_MENU, self.on_user_directory, self.mi_user_directory)
        self.Bind(wx.EVT_MENU, self.on_server_info, self.mi_server_info)
        self.Bind(wx.EVT_MENU, self.on_server_manager, self.mi_server_manager)
        self.Bind(wx.EVT_MENU, self.on_manage_bot_rules, self.mi_bot_rules)
        self.Bind(wx.EVT_MENU, self.on_manage_group_policy, self.mi_group_policy)
        self.Bind(wx.EVT_MENU, self.on_settings, self.mi_settings)
        self.Bind(wx.EVT_MENU, self.on_register_passkey, self.mi_register_passkey)
        self.Bind(wx.EVT_MENU, self.on_manage_devices, self.mi_manage_devices)
        self.Bind(wx.EVT_MENU, self.on_logout, self.mi_logout)
        self.Bind(wx.EVT_MENU, self.on_exit, self.mi_exit)
        self.Bind(wx.EVT_MENU, self.on_block_toggle, self.mi_block_toggle)
        self.Bind(wx.EVT_MENU, self.on_toggle_selected_chat_logging, self.mi_toggle_chat_log)
        self.Bind(wx.EVT_MENU, self.on_user_directory, self.mi_refresh_directory)
        self.Bind(wx.EVT_MENU, self.on_send, self.mi_user_start_chat)
        self.Bind(wx.EVT_MENU, self.on_send_file, self.mi_user_send_file)
        self.Bind(wx.EVT_MENU, self.on_file_transfers, self.mi_user_transfers)
        self.Bind(wx.EVT_MENU, self.on_add, self.mi_user_add_contact)
        self.Bind(wx.EVT_MENU, self.on_block_toggle, self.mi_user_toggle_block)
        self.Bind(wx.EVT_MENU, self.on_toggle_selected_chat_logging, self.mi_user_toggle_history)
        self.Bind(wx.EVT_MENU, self.on_delete, self.mi_user_delete_contact)
        self.Bind(wx.EVT_MENU, lambda e: self._set_sort_mode("name_asc"), self.mi_sort_name_asc)
        self.Bind(wx.EVT_MENU, lambda e: self._set_sort_mode("name_desc"), self.mi_sort_name_desc)
        self.Bind(wx.EVT_MENU, lambda e: self._set_sort_mode("status"), self.mi_sort_status)
        self.Bind(wx.EVT_MENU, lambda e: open_help_docs_for_context("main", self), self.mi_help)
        self.Bind(wx.EVT_MENU, lambda e: self.on_watch_demo_video("onboarding"), self.mi_demo_onboarding)
        self.Bind(wx.EVT_MENU, lambda e: self.on_watch_demo_video("chat_files"), self.mi_demo_chat_files)
        self.Bind(wx.EVT_MENU, lambda e: self.on_watch_demo_video("admin_tools"), self.mi_demo_admin_tools)
        self.Bind(wx.EVT_MENU, self.on_open_demo_videos, self.mi_demo_videos)
        self.Bind(wx.EVT_MENU, self.on_submit_logs, self.mi_submit_logs)

    def _apply_voiceover_hints(self, search_label):
        apply_voiceover_hint(search_label, "Press F3 to search contacts.")
        apply_voiceover_hint(self.search_box, "Contact search. Use plain text or filters such as status:online, role:admin, type:bot, and name:text. Escape returns to the contact list.")
        apply_voiceover_hint(self.lv, "Contacts list. Use arrow keys to select a contact, then press Return to chat.")
        apply_voiceover_hint(self.btn_add, "Add a contact by username.")
        apply_voiceover_hint(self.btn_send, "Start chat with selected contact.")
        apply_voiceover_hint(self.btn_send_file, "Send a file to selected contact.")
        apply_voiceover_hint(self.btn_delete, "Remove selected contact.")
        apply_voiceover_hint(self.btn_block, "Block or unblock selected contact.")
        apply_voiceover_hint(self.btn_directory, "Browse all users and add contacts from the directory.")
        apply_voiceover_hint(self.btn_settings, "Open preferences and accessibility options.")
        apply_voiceover_hint(self.btn_admin, "Open server-side command console if you are an admin.")
        apply_voiceover_hint(self.btn_status, "Set your current status message.")
        apply_voiceover_hint(self.btn_update, "Check for client updates.")
        apply_voiceover_hint(self.btn_logout, "Sign out and return to login.")
        apply_voiceover_hint(self.btn_exit, "Quit the app.")

    def _set_sort_mode(self, mode):
        self._sort_mode = mode
        self._apply_search_filter()

    def _show_add_contact_prompt(self):
        result = wx.MessageBox(
            "No contacts are available yet. Would you like to add a contact now?",
            "No Contacts",
            wx.YES_NO | wx.ICON_INFORMATION,
            self
        )
        if result == wx.YES:
            self.on_add(None)
    def _schedule_empty_contacts_tip(self):
        if self._empty_contacts_tip_scheduled:
            return
        self._empty_contacts_tip_scheduled = True
        delay_ms = random.randint(5 * 60 * 1000, 10 * 60 * 1000)
        def _tip():
            show_notification(
                "Contacts tip",
                "Use Server Directory (Alt+Y) to add contacts quickly.",
                timeout=8,
            )
            self._empty_contacts_tip_scheduled = False
        wx.CallLater(delay_ms, _tip)

    def _selected_contact_name(self):
        sel = self.lv.GetSelection()
        if sel == wx.NOT_FOUND or sel >= len(self._contact_display_map):
            # macOS ListBox can occasionally drop selection after focus/menu transitions.
            # Keep actions usable by selecting the first valid contact row.
            for idx, name in enumerate(self._contact_display_map):
                if name:
                    self.lv.SetSelection(idx)
                    return name
            return None
        return self._contact_display_map[sel]
    def _clear_unread(self, contact):
        if contact in self._unread_counts:
            self._unread_counts.pop(contact, None)
            self._apply_search_filter()
    def _mark_unread(self, contact):
        self._unread_counts[contact] = int(self._unread_counts.get(contact, 0) or 0) + 1
        self._apply_search_filter()
    def on_submit_logs(self, _):
        app = wx.GetApp()
        ok, err = submit_logs_payload(app.user_config, reason="manual_submit")
        if ok:
            show_notification("Diagnostics", "Logs submitted successfully.", timeout=4)
            wx.MessageBox("Diagnostic logs submitted successfully.", "Logs Submitted", wx.OK | wx.ICON_INFORMATION)
            log_event("info", "logs_submitted_manual")
        else:
            wx.MessageBox(f"Could not submit logs:\n{err}", "Log Submit Failed", wx.OK | wx.ICON_ERROR)
            log_event("error", "logs_submit_failed", {"error": str(err)})

    def on_open_demo_videos(self, _):
        open_path_or_url(get_demo_videos_dir())

    def on_watch_demo_video(self, key):
        meta = DEMO_VIDEOS.get(key)
        if not meta:
            return
        demo_dir = get_demo_videos_dir()
        clip_path = os.path.join(demo_dir, meta["filename"])
        description = meta["description"]
        if wx.GetApp().user_config.get('read_messages_aloud', False):
            speak_text(f"{meta['title']}. {description}")
        if not os.path.isfile(clip_path):
            wx.MessageBox(
                f"{meta['title']} is not available yet.\n\nExpected file:\n{clip_path}\n\nDescription:\n{description}",
                "Demo Video Missing",
                wx.OK | wx.ICON_INFORMATION,
                self,
            )
            return
        choice = wx.MessageBox(
            f"{meta['title']}\n\nDescription:\n{description}\n\nOpen this video now?",
            "Watch Demo Video",
            wx.YES_NO | wx.ICON_QUESTION,
            self,
        )
        if choice == wx.YES:
            open_path_or_url(clip_path)

    def _passkey_map_key(self):
        app = wx.GetApp()
        active = normalize_server_entry(getattr(app, "active_server_entry", SERVER_CONFIG))
        return _passkey_account_for(self.user, settings=app.user_config, server_entry=active)

    def on_passkey_response(self, msg):
        action = str(msg.get("action", "") or "")
        if not action:
            return
        with self._passkey_response_lock:
            event = self._passkey_response_events.get(action)
            if not event:
                return
            self._passkey_responses[action] = msg
            event.set()

    def _send_passkey_request(self, payload, expected_action, timeout=12):
        expected_action = str(expected_action or "")
        if not expected_action:
            return None, "Internal passkey request error."
        with self._passkey_request_lock:
            last_error = ""
            for attempt in range(2):
                app = wx.GetApp()
                if getattr(app, "reconnect_in_progress", False):
                    deadline = time.time() + min(timeout, 8)
                    while getattr(app, "reconnect_in_progress", False) and time.time() < deadline:
                        time.sleep(0.2)
                current_socket = getattr(app, "sock", None) or self.sock
                self.sock = current_socket
                event = threading.Event()
                with self._passkey_response_lock:
                    self._passkey_response_events[expected_action] = event
                    self._passkey_responses.pop(expected_action, None)
                try:
                    current_socket.sendall((json.dumps(payload) + "\n").encode())
                except OSError:
                    last_error = "The connection was changing while Thrive sent the passkey request."
                    with self._passkey_response_lock:
                        self._passkey_response_events.pop(expected_action, None)
                        self._passkey_responses.pop(expected_action, None)
                    if attempt == 0:
                        time.sleep(0.5)
                        continue
                    return None, last_error + " Thrive is reconnecting; try again after the contact list is back online."
                except Exception as e:
                    with self._passkey_response_lock:
                        self._passkey_response_events.pop(expected_action, None)
                        self._passkey_responses.pop(expected_action, None)
                    return None, f"Could not send the passkey request: {e}"
                if not event.wait(timeout):
                    with self._passkey_response_lock:
                        self._passkey_response_events.pop(expected_action, None)
                        self._passkey_responses.pop(expected_action, None)
                    return None, "The server did not answer the passkey request in time. The connection may be reconnecting; try again in a moment."
                with self._passkey_response_lock:
                    self._passkey_response_events.pop(expected_action, None)
                    response = self._passkey_responses.pop(expected_action, None)
                return response, ""
            return None, last_error or "The passkey request could not be sent."

    def _list_passkeys(self):
        resp, _ = self._send_passkey_request({"action": "list_passkeys"}, "passkey_list")
        if resp and resp.get("action") == "passkey_list":
            return resp.get("passkeys", [])
        return []

    def on_register_passkey(self, _):
        app = wx.GetApp()
        default_label = f"Thrive Messenger - {self.user}"
        with wx.TextEntryDialog(
            self,
            "Enter a name for this device passkey.\nLeave blank to use the default.",
            "Register Passkey",
            value=default_label,
        ) as dlg:
            if dlg.ShowModal() != wx.ID_OK:
                return
            label = dlg.GetValue().strip() or default_label
        token = secrets.token_urlsafe(48)
        resp, error = self._send_passkey_request({
            "action": "register_passkey",
            "label": label,
            "passkey_token": token,
        }, "passkey_register_result")
        if error:
            wx.MessageBox(f"Could not register passkey. {error}", "Passkey Error", wx.OK | wx.ICON_ERROR, self)
            return
        if not resp:
            wx.MessageBox("Could not register passkey. The server response was empty.", "Passkey Error", wx.OK | wx.ICON_ERROR, self)
            return
        if not resp.get("ok"):
            wx.MessageBox(resp.get("reason", "Unknown error"), "Passkey Error", wx.OK | wx.ICON_ERROR, self)
            return
        if not _save_passkey_to_keyring(self.user, token, settings=app.user_config, server_entry=app.active_server_entry):
            wx.MessageBox("Passkey was registered on server but could not be saved in keychain.", "Passkey Warning", wx.OK | wx.ICON_WARNING, self)
            return
        passkey_ids = app.user_config.get("passkey_ids", {})
        passkey_ids[self._passkey_map_key()] = str(resp.get("passkey_id", "") or "")
        app.user_config["passkey_ids"] = passkey_ids
        app.user_config["autologin_mode"] = "passkey"
        save_user_config(app.user_config)
        show_notification("Passkey Ready", f"Passkey registered for {label}.", timeout=6)
        wx.MessageBox("Passkey registered. You can now use Login with Passkey.", "Passkey Ready", wx.OK | wx.ICON_INFORMATION, self)

    def on_manage_devices(self, _):
        app = wx.GetApp()
        entries = self._list_passkeys()
        if not entries:
            wx.MessageBox("No registered devices were found for this account.", "Manage Devices", wx.OK | wx.ICON_INFORMATION, self)
            return
        count = len([e for e in entries if not e.get("revoked")])
        labels = [f"{e.get('label', 'Device')} | created {e.get('created_at', '')}" for e in entries if not e.get("revoked")]
        if not labels:
            wx.MessageBox("All devices are already revoked.", "Manage Devices", wx.OK | wx.ICON_INFORMATION, self)
            return
        choice = wx.GetSingleChoiceIndex(
            f"You are signed in on {count} device(s). Choose one to sign out, or cancel to keep all.",
            "Manage Signed-In Devices",
            labels,
            self,
        )
        if choice == -1:
            res_all = wx.MessageBox(
                "Do you want to sign out all devices for this account?",
                "Sign Out All Devices",
                wx.YES_NO | wx.ICON_QUESTION,
                self,
            )
            if res_all != wx.YES:
                return
            for entry in entries:
                if entry.get("revoked"):
                    continue
                self._send_passkey_request(
                    {"action": "revoke_passkey", "passkey_id": entry.get("id", "")},
                    "passkey_revoke_result",
                )
            _delete_passkey_from_keyring(self.user, settings=app.user_config, server_entry=app.active_server_entry)
            show_notification("Devices Updated", "Signed out all devices.", timeout=5)
            wx.MessageBox("All devices were signed out.", "Manage Devices", wx.OK | wx.ICON_INFORMATION, self)
            return
        target = [e for e in entries if not e.get("revoked")][choice]
        resp, error = self._send_passkey_request(
            {"action": "revoke_passkey", "passkey_id": target.get("id", "")},
            "passkey_revoke_result",
        )
        if error:
            wx.MessageBox(f"Could not revoke selected device. {error}", "Manage Devices", wx.OK | wx.ICON_ERROR, self)
            return
        if not resp:
            wx.MessageBox("Could not revoke selected device. The server response was empty.", "Manage Devices", wx.OK | wx.ICON_ERROR, self)
            return
        if not resp.get("ok"):
            wx.MessageBox(resp.get("reason", "Unknown revoke error"), "Manage Devices", wx.OK | wx.ICON_ERROR, self)
            return
        if str(target.get("id", "")) == str(app.user_config.get("passkey_ids", {}).get(self._passkey_map_key(), "")):
            _delete_passkey_from_keyring(self.user, settings=app.user_config, server_entry=app.active_server_entry)
        show_notification("Device Signed Out", f"{target.get('label', 'Device')} was signed out.", timeout=5)
        wx.MessageBox("Selected device was signed out.", "Manage Devices", wx.OK | wx.ICON_INFORMATION, self)

    def on_settings(self, event):
        app = wx.GetApp()
        can_admin_settings = self._feature_can_use("admin_console") and self._feature_ui_visible("admin_console")
        came_from = wx.Window.FindFocus()
        with SettingsDialog(self, app.user_config, can_admin=can_admin_settings) as dlg:
            if dlg.ShowModal() == wx.ID_OK:
                self.apply_settings_dialog(dlg)
        wx.CallAfter(self._return_focus, came_from)
    def _return_focus(self, window):
        """After Settings closes, put focus back in the chat, contact list or other window it was opened from."""
        try:
            if window and window.IsShownOnScreen():
                top = window.GetTopLevelParent()
                if top:
                    top.Raise()
                window.SetFocus()
                return
        except Exception:
            pass
        self.focus_contact_list(announce=False)
    def apply_settings_dialog(self, dlg):
        """Save everything in the Settings dialog (used by OK and by Apply)."""
        app = wx.GetApp()
        can_admin = bool(getattr(dlg, "_can_admin", False))
        selected_pack = dlg.choice.GetStringSelection()
        app.user_config['soundpack'] = selected_pack
        app.user_config['call_soundpack'] = "same" if dlg.call_pack_choice.GetSelection() <= 0 else dlg.call_pack_choice.GetStringSelection()
        app.user_config['auto_play_voice_messages'] = dlg.auto_play_voice_cb.IsChecked()
        if dlg.set_selected_default_cb.IsChecked() and selected_pack not in ("default", "none"):
            app.user_config['default_soundpack'] = selected_pack
        app.user_config['sound_volume'] = int(dlg.sound_volume_slider.GetValue())
        app.user_config['call_input_volume'] = int(dlg.call_input_slider.GetValue())
        app.user_config['call_output_volume'] = int(dlg.call_output_slider.GetValue())
        app.user_config['call_input_device'] = dlg.call_input_devices[dlg.call_input_device_choice.GetSelection()][0]
        app.user_config['call_output_device'] = dlg.call_output_devices[dlg.call_output_device_choice.GetSelection()][0]
        app.user_config['auto_open_received_files'] = dlg.auto_open_files_cb.IsChecked()
        app.user_config['read_messages_aloud'] = dlg.read_aloud_cb.IsChecked()
        app.user_config['interrupt_speech'] = dlg.interrupt_speech_cb.IsChecked()
        app.user_config['save_chat_history_default'] = dlg.global_chat_logging_cb.IsChecked()
        app.user_config['show_main_action_buttons'] = dlg.show_main_actions_cb.IsChecked()
        app.user_config['typing_indicators'] = dlg.typing_indicator_cb.IsChecked()
        app.user_config['announce_typing'] = dlg.announce_typing_cb.IsChecked()
        app.user_config['prefer_contact_display_names'] = dlg.prefer_display_names_cb.IsChecked()
        app.user_config['notify_on_other_device_login'] = dlg.notify_other_device_login_cb.IsChecked()
        app.user_config['session_duration'] = ['hour', 'day', 'week', 'month', 'year', 'forever'][dlg.session_duration_choice.GetSelection()]
        incoming_behavior_map = {0: 'popup', 1: 'notify', 2: 'do_nothing', 3: 'play_sound', 4: 'silent_count'}
        incoming_behavior = incoming_behavior_map.get(dlg.incoming_behavior_choice.GetSelection(), 'silent_count')
        app.user_config['incoming_message_behavior'] = incoming_behavior
        app.user_config['incoming_popup_on_message'] = (incoming_behavior == 'popup')
        app.user_config['incoming_alert_on_message'] = incoming_behavior in ('notify', 'play_sound')
        ts_mode_map = {0: 'start', 1: 'end', 2: 'off'}
        app.user_config['message_timestamp_mode'] = ts_mode_map.get(dlg.timestamp_mode_choice.GetSelection(), 'start')
        date_order_map = {0: 'mdy', 1: 'dmy', 2: 'ymd', 3: 'ydm'}
        app.user_config['saved_history_date_order'] = date_order_map.get(dlg.saved_date_order_choice.GetSelection(), 'mdy')
        enter_map = {0: 'none', 1: 'send', 2: 'place_call'}
        app.user_config['enter_key_action'] = enter_map.get(dlg.enter_action_choice.GetSelection(), 'none')
        app.user_config['escape_main_action'] = ('none' if dlg.escape_action_choice.GetSelection() == 0 else ('minimize' if dlg.escape_action_choice.GetSelection() == 1 else 'quit'))
        app.user_config['double_escape_to_close_chat'] = dlg.double_escape_chat_cb.IsChecked()
        app.user_config['delete_messages_for_everyone'] = dlg.delete_for_everyone_cb.IsChecked()
        app.user_config['chat_tabs'] = dlg.chat_tabs_cb.IsChecked()
        app.user_config['keep_contact_list_open'] = dlg.keep_contact_list_cb.IsChecked()
        app.user_config['delete_attached_files_with_message'] = dlg.delete_attached_files_cb.IsChecked()
        edit_window, undo_window = dlg.message_policy()
        app.user_config['message_edit_window_seconds'] = edit_window
        app.user_config['message_undo_window_seconds'] = undo_window
        app.user_config['allow_cross_server_directory_message'] = dlg.allow_cross_server_dm_cb.IsChecked()
        app.user_config['bot_mesh_agent_enabled'] = dlg.bot_agent_enabled_cb.IsChecked()
        app.user_config['bot_mesh_agent_moderation'] = dlg.bot_agent_moderation_cb.IsChecked()
        app.user_config['bot_mesh_agent_backend'] = dlg.bot_agent_backend_choice.GetStringSelection().strip().lower() or 'ollama'
        app.user_config['bot_mesh_agent_auth_type'] = dlg.bot_agent_auth_choice.GetStringSelection().strip().lower() or 'codex'
        app.user_config['bot_mesh_agent_delegate_to'] = dlg.bot_agent_delegate_txt.GetValue().strip()
        app.user_config['bot_mesh_agent_notify_user'] = dlg.bot_agent_notify_txt.GetValue().strip()
        app.user_config['bot_mesh_agent_user'] = dlg.bot_agent_user_txt.GetValue().strip()
        app.user_config['bot_mesh_agent_host_label'] = dlg.bot_agent_host_label_txt.GetValue().strip()
        ok_admin, admin_err = (True, None)
        if can_admin:
            ok_admin, admin_err = dlg.apply_admin_config()
        save_user_config(app.user_config)
        app.sync_session_preferences()
        self.apply_action_button_layout()
        self._apply_search_filter()
        restart_req, restart_delay = dlg.restart_requested()
        if restart_req:
            try:
                self.sock.sendall((json.dumps({"action": "schedule_restart", "seconds": int(restart_delay)}) + "\n").encode())
            except Exception:
                pass
        if restart_req:
            # Only schedule once, even if Apply is followed by OK.
            try:
                dlg.restart_after_save_cb.SetValue(False)
            except Exception:
                pass
        if not ok_admin:
            wx.MessageBox(f"Settings saved, but advanced client config could not be written:\n{admin_err}", "Settings Saved With Warning", wx.OK | wx.ICON_WARNING, dlg)
        else:
            app.play_sound("copied.wav")
            speak_text("Settings saved", interrupt=True)

    def show_authenticated_devices(self):
        dialog = getattr(self, "_authenticated_devices_dialog", None)
        if dialog and dialog.IsShown():
            dialog.Raise(); dialog.SetFocus(); dialog.refresh(None); return
        dialog = AuthenticatedDevicesDialog(self)
        self._authenticated_devices_dialog = dialog
        try: dialog.ShowModal()
        finally:
            self._authenticated_devices_dialog = None
            dialog.Destroy()

    def on_authenticated_devices(self, msg):
        dialog = getattr(self, "_authenticated_devices_dialog", None)
        if dialog:
            dialog.update_devices(msg)

    def on_deauthenticate_device_result(self, msg):
        if not msg.get("ok"):
            wx.MessageBox(msg.get("reason", "Could not sign out that device."), "Device Sign Out Failed", wx.OK | wx.ICON_ERROR, self)
            return
        dialog = getattr(self, "_authenticated_devices_dialog", None)
        if dialog:
            dialog.refresh(None)

    def on_change_password_result(self, msg):
        if msg.get("ok"):
            wx.MessageBox("Password changed successfully.", "Success", wx.OK | wx.ICON_INFORMATION)
        else:
            reason = msg.get("reason", "Unknown error.")
            wx.MessageBox(f"Could not change password: {reason}", "Error", wx.ICON_ERROR)
    def on_delete_account_result(self, msg):
        if not msg.get("ok"):
            wx.MessageBox(msg.get("reason", "Account deletion failed."), "Account Deletion Failed", wx.OK | wx.ICON_ERROR, self)
            return
        app = wx.GetApp()
        username = self.user
        _delete_password_from_keyring(username, app.user_config)
        _delete_passkey_from_keyring(username, settings=app.user_config, server_entry=app.active_server_entry)
        app.user_config["username"] = ""
        app.user_config["password"] = ""
        app.user_config["password_fallback"] = ""
        app.user_config["remember"] = False
        save_user_config(app.user_config)
        wx.MessageBox("Your account and its linked identities were deleted from this Thrive server.", "Account Deleted", wx.OK | wx.ICON_INFORMATION, self)
        self.on_logout(None)
    def on_user_directory(self, _):
        if self._directory_dlg:
            self._directory_dlg.Raise(); self._directory_dlg.SetFocus(); return
        self.sock.sendall(json.dumps({"action": "user_directory"}).encode() + b"\n")
    def on_user_directory_response(self, msg):
        app = wx.GetApp()
        active = normalize_server_entry(getattr(app, "active_server_entry", {}))
        current_server_name = active.get("name", "Current Server")
        users = msg.get("users", [])
        if not self._feature_can_use("bots"):
            users = [u for u in users if not bool(u.get("is_bot"))]
        for u in users:
            u["server"] = u.get("server", current_server_name)
            u["display_name"] = pick_user_display_name(u)
            u["server_host"] = str(u.get("server_host", active.get("host", "")) or "").strip().lower()
            try:
                u["server_port"] = int(u.get("server_port", active.get("port", 0)) or 0)
            except Exception:
                u["server_port"] = int(active.get("port", 0) or 0)
        dlg = UserDirectoryDialog(self, users, self.user, self.contact_states)
        self._directory_dlg = dlg
        dlg.Show()
        if app.user_config.get("server_entries") and app.session_password:
            def merge_later():
                extras = []
                active = normalize_server_entry(getattr(app, "active_server_entry", {}))
                for entry in app.user_config.get("server_entries", []):
                    normalized = normalize_server_entry(entry)
                    if normalized["host"].lower() == active.get("host", "").lower() and normalized["port"] == active.get("port", 0):
                        continue
                    extras.extend(app.fetch_directory_for_server(normalized, self.user, app.session_password))
                if extras and self._directory_dlg:
                    wx.CallAfter(self._directory_dlg.merge_external_users, extras)
            threading.Thread(target=merge_later, daemon=True).start()
    def on_server_info(self, _):
        self.sock.sendall(json.dumps({"action": "server_info"}).encode() + b"\n")

    def on_server_manager(self, _):
        if not self._feature_can_use("server_manager"):
            wx.MessageBox("Server Manager is disabled for your account on this server.", "Feature Disabled", wx.OK | wx.ICON_INFORMATION)
            return
        app = wx.GetApp()
        entries = dedupe_server_entries(app.user_config.get('server_entries', []))
        if not entries:
            entries = [normalize_server_entry(getattr(app, "active_server_entry", SERVER_CONFIG))]
        primary_name = app.user_config.get('primary_server_name', '')
        with ServerManagerDialog(self, entries, primary_name) as dlg:
            if dlg.ShowModal() != wx.ID_OK:
                return
            updated_entries = dlg.get_entries()
            if not updated_entries:
                wx.MessageBox("At least one server entry is required.", "Server Manager", wx.OK | wx.ICON_INFORMATION)
                return
            app.user_config['server_entries'] = updated_entries
            selected_primary = dlg.get_primary_server_name()
            if selected_primary:
                app.user_config['primary_server_name'] = selected_primary
            if app.user_config.get('last_server_name') not in [e.get('name') for e in updated_entries]:
                app.user_config['last_server_name'] = app.user_config.get('primary_server_name') or updated_entries[0].get('name', '')
            save_user_config(app.user_config)
            wx.MessageBox("Server list updated. Changes apply on next login.", "Server Manager", wx.OK | wx.ICON_INFORMATION)
    def _known_bot_names(self):
        names = {"openclaw-bot", "assistant-bot", "helper-bot", "codex-bot", "opencode-bot", "ollama-bot", "claude-bot"}
        for c in self._all_contacts:
            uname = str(c.get("user", "")).strip()
            if not uname:
                continue
            if uname.lower().endswith("-bot") or uname in names:
                names.add(uname)
        return sorted(names, key=lambda x: x.lower())
    def on_manage_bot_rules(self, _):
        if not self._feature_can_use("bot_rules"):
            wx.MessageBox("Bot rules are disabled for your account on this server.", "Feature Disabled", wx.OK | wx.ICON_INFORMATION)
            return
        dlg = self._bot_rules_dlg
        if dlg and dlg.IsShown():
            dlg.Raise()
            dlg.SetFocus()
            return
        self._bot_rules_dlg = BotRulesDialog(self, self.sock, self._known_bot_names())
        self._bot_rules_dlg.Show()
    def on_manage_group_policy(self, _):
        if not self._feature_can_use("group_policy"):
            wx.MessageBox("Group policy management is disabled for your account on this server.", "Feature Disabled", wx.OK | wx.ICON_INFORMATION)
            return
        dlg = self._group_policy_dlg
        if dlg and dlg.IsShown():
            dlg.Raise()
            dlg.SetFocus()
            return
        self._group_policy_dlg = GroupPolicyDialog(self, self.sock)
        self._group_policy_dlg.Show()
    def on_bot_rules(self, msg):
        dlg = self._bot_rules_dlg
        if dlg and dlg.IsShown():
            dlg.handle_rules_payload(msg)
            return
        if not msg.get("ok"):
            wx.MessageBox(msg.get("reason", "Could not fetch bot rules."), "Bot Rules", wx.OK | wx.ICON_WARNING)
    def on_bot_rules_update(self, msg):
        dlg = self._bot_rules_dlg
        if dlg and dlg.IsShown():
            dlg.handle_update_payload(msg)
            return
        if not msg.get("ok"):
            wx.MessageBox(msg.get("reason", "Bot rules update failed."), "Bot Rules", wx.OK | wx.ICON_WARNING)
    def on_group_policy(self, msg):
        dlg = self._group_policy_dlg
        if dlg and dlg.IsShown():
            dlg.handle_policy_payload(msg)
            return
        if not msg.get("ok"):
            wx.MessageBox(msg.get("reason", "Could not fetch group policy."), "Group Policy", wx.OK | wx.ICON_WARNING)
    def on_group_policy_update(self, msg):
        dlg = self._group_policy_dlg
        if dlg and dlg.IsShown():
            dlg.handle_update_payload(msg)
            return
        if not msg.get("ok"):
            wx.MessageBox(msg.get("reason", "Group policy update failed."), "Group Policy", wx.OK | wx.ICON_WARNING)
    def on_server_info_response(self, msg):
        encrypted = isinstance(self.sock, ssl.SSLSocket)
        app = wx.GetApp()
        active = normalize_server_entry(getattr(app, "active_server_entry", {}))
        size_limit = msg.get("size_limit", 0)
        size_str = format_size(size_limit) if size_limit > 0 else "No limit"
        blackfiles = msg.get("blackfiles", [])
        blackfiles_str = ", ".join(f".{ext}" for ext in blackfiles) if blackfiles else "None"
        max_status_len = msg.get("max_status_length", "N/A")
        lines = [
            "Connected Server",
            f"Name: {active.get('name', 'Current Server')}",
            f"Host: {active.get('host', SERVER_CONFIG.get('host', 'Unknown'))}",
            f"Port: {msg.get('port', active.get('port', SERVER_CONFIG.get('port', 'N/A')))}",
            f"Encryption: {'Yes' if encrypted else 'No'}",
            "",
            "Server Status",
            f"Registered users: {msg.get('total_users', 'N/A')}",
            f"Users online: {msg.get('online_users', 'N/A')}",
            f"Admins online: {msg.get('online_admin_users', 'N/A')}",
            f"Uptime: {format_duration(int(msg.get('uptime_seconds', 0) or 0))}",
            "",
            "File Policy",
            f"File size limit: {size_str}",
            f"Blocked file extensions: {blackfiles_str}",
            f"Max status length: {max_status_len}",
        ]
        with ServerInfoDialog(self, "\n".join(lines)) as dlg: dlg.ShowModal()
    def update_button_states(self, event=None):
        selected_contact = self._selected_contact_name()
        if selected_contact is None and self.lv.GetCount() > 0 and self._contact_display_map:
            for idx, name in enumerate(self._contact_display_map):
                if name:
                    self.lv.SetSelection(idx)
                    selected_contact = name
                    break
        is_selection = selected_contact is not None
        is_contact_selection = selected_contact is not None and selected_contact in self.contact_states
        self.btn_send.Enable(is_contact_selection)
        self.btn_delete.Enable(is_contact_selection)
        self.btn_block.Enable(is_contact_selection)
        self.btn_send_file.Enable(is_contact_selection)
        if is_selection:
            contact_name = selected_contact
            is_blocked = self.contact_states.get(contact_name, 0); self.btn_block.SetLabel("&Unblock" if is_blocked else "&Block")
        else: self.btn_block.SetLabel("&Block")
        if hasattr(self, "mi_delete_contact"):
            self.mi_delete_contact.Enable(is_contact_selection)
        if hasattr(self, "mi_user_delete_contact"):
            self.mi_user_delete_contact.Enable(is_contact_selection)
        if selected_contact and is_contact_selection:
            shown_name = self.format_user_label(selected_contact, include_username=True)
            self.btn_send.SetLabel(f"&Start Chat with {shown_name}")
            self.btn_send_file.SetLabel(f"Send &File to {shown_name}")
            self.btn_block.SetLabel(f"{'&Unblock' if self.contact_states.get(selected_contact, 0) else '&Block'} {shown_name}")
            self.btn_delete.SetLabel(f"&Delete {shown_name}")
        else:
            self.btn_send.SetLabel("&Start Chat")
            self.btn_send_file.SetLabel("Send &File")
            self.btn_delete.SetLabel("&Delete Contact")
            if not is_selection:
                self.btn_block.SetLabel("&Block")
        if event: event.Skip()
    def on_set_status(self, event):
        menu = wx.Menu()
        app = wx.GetApp()
        status_preset = app.user_config.get('status_preset', 'online')
        status_custom_by_preset = app.user_config.get('status_custom_by_preset', {})
        if not isinstance(status_custom_by_preset, dict):
            status_custom_by_preset = {}
        status_global_custom = app.user_config.get('status_global_custom', '')

        def _compose_status_text(preset):
            preset_custom = str(status_custom_by_preset.get(preset, '') or '').strip()
            global_custom = str(status_global_custom or '').strip()
            if preset_custom:
                return f"{preset} status, {preset_custom}"
            if global_custom:
                return f"{preset} status, {global_custom}"
            return preset

        current_line = menu.Append(wx.ID_ANY, f"Currently: {_compose_status_text(status_preset)}")
        current_line.Enable(False)
        menu.AppendSeparator()

        preset_items = {}
        for preset in STATUS_PRESETS:
            label = preset
            if preset == status_preset:
                label += " (Selected)"
            mi = menu.Append(wx.ID_ANY, label)
            preset_items[mi.GetId()] = preset

        menu.AppendSeparator()
        mi_custom_selected = menu.Append(wx.ID_ANY, f"Set custom text for selected status ({status_preset})")
        mi_custom_global = menu.Append(wx.ID_ANY, "Set global custom text")
        mi_clear_selected = menu.Append(wx.ID_ANY, f"Clear custom text for selected status ({status_preset})")
        mi_clear_global = menu.Append(wx.ID_ANY, "Clear global custom text")

        def _send_status_text(text):
            self.current_status = text
            app.user_config['status'] = text
            save_user_config(app.user_config)
            try:
                self.sock.sendall((json.dumps({"action": "set_status", "status_text": text}) + "\n").encode())
            except Exception as e:
                print(f"Error setting status: {e}")

        def _on_pick_preset(evt):
            nonlocal status_preset
            preset = preset_items.get(evt.GetId())
            if not preset:
                return
            status_preset = preset
            app.user_config['status_preset'] = preset
            _send_status_text(_compose_status_text(preset))

        def _on_set_custom_selected(_):
            nonlocal status_custom_by_preset
            with wx.TextEntryDialog(self, f"Custom text for '{status_preset}' (leave blank to clear):", "Custom Status") as dlg:
                if dlg.ShowModal() != wx.ID_OK:
                    return
                txt = dlg.GetValue().strip()
                if txt:
                    status_custom_by_preset[status_preset] = txt
                else:
                    status_custom_by_preset.pop(status_preset, None)
                app.user_config['status_custom_by_preset'] = status_custom_by_preset
                _send_status_text(_compose_status_text(status_preset))

        def _on_set_custom_global(_):
            nonlocal status_global_custom
            with wx.TextEntryDialog(self, "Global custom text (used when selected status has no custom text):", "Global Custom Status") as dlg:
                if dlg.ShowModal() != wx.ID_OK:
                    return
                status_global_custom = dlg.GetValue().strip()
                app.user_config['status_global_custom'] = status_global_custom
                _send_status_text(_compose_status_text(status_preset))

        def _on_clear_selected(_):
            status_custom_by_preset.pop(status_preset, None)
            app.user_config['status_custom_by_preset'] = status_custom_by_preset
            _send_status_text(_compose_status_text(status_preset))

        def _on_clear_global(_):
            nonlocal status_global_custom
            status_global_custom = ""
            app.user_config['status_global_custom'] = ""
            _send_status_text(_compose_status_text(status_preset))

        for item_id in preset_items:
            menu.Bind(wx.EVT_MENU, _on_pick_preset, id=item_id)
        menu.Bind(wx.EVT_MENU, _on_set_custom_selected, mi_custom_selected)
        menu.Bind(wx.EVT_MENU, _on_set_custom_global, mi_custom_global)
        menu.Bind(wx.EVT_MENU, _on_clear_selected, mi_clear_selected)
        menu.Bind(wx.EVT_MENU, _on_clear_global, mi_clear_global)
        self.PopupMenu(menu)
        menu.Destroy()
    def on_check_updates(self, event=None, silent=False):
        self.btn_update.Disable()
        def _callback(tag, version_str, error):
            self.btn_update.Enable()
            if tag:
                result = wx.MessageBox(
                    f"A new version is available: {tag}\nYou are currently running {VERSION_TAG}.\n\nWould you like to download and install it?",
                    "Update Available", wx.YES_NO | wx.ICON_INFORMATION, self)
                if result == wx.YES:
                    self._start_update_download(tag)
            elif error and not silent:
                wx.MessageBox(f"Could not check for updates:\n{error}", "Update Check Failed", wx.ICON_ERROR)
            elif not error and not silent:
                wx.MessageBox(f"You are running the latest version, {VERSION_TAG}.", "No Updates", wx.ICON_INFORMATION)
        check_for_update(_callback)
    def _start_update_download(self, tag):
        import urllib.request
        use_installer = is_installer_install()
        if sys.platform == 'darwin':
            target_candidates = [
                "thrive_messenger-macos-universal2.zip",
                "thrive_messenger-macos-arm64.zip",
                "thrive_messenger-macos-x86_64.zip",
                "thrive_messenger-macos.zip",
                "ThriveMessenger-macOS.zip",
                "thrive_messenger.zip",
            ]
        else:
            target_candidates = ["thrive_messenger_installer.exe"] if use_installer else ["thrive_messenger.zip"]
        asset_url = None

        if UPDATE_CONTEXT.get("source") == "feed":
            if sys.platform == 'darwin':
                asset_url = UPDATE_CONTEXT.get("mac_zip_url") or UPDATE_CONTEXT.get("zip_url")
            else:
                asset_url = UPDATE_CONTEXT.get("installer_url") if use_installer else (UPDATE_CONTEXT.get("win_zip_url") or UPDATE_CONTEXT.get("zip_url"))

        if not asset_url:
            repo = UPDATE_CONTEXT.get("repo") if UPDATE_CONTEXT.get("repo") else "Raywonder/ThriveMessenger"
            api_url = f"https://api.github.com/repos/{repo}/releases/tags/{tag}"
            try:
                req = urllib.request.Request(api_url, headers={"Accept": "application/vnd.github+json", "User-Agent": f"ThriveMessenger/{VERSION_TAG} ({sys.platform})"})
                with urllib.request.urlopen(req, timeout=15) as resp:
                    data = json.loads(resp.read().decode())
            except Exception as e:
                wx.MessageBox(f"Failed to fetch release info:\n{e}", "Update Error", wx.ICON_ERROR); return
            assets = data.get("assets", [])
            for name in target_candidates:
                for a in assets:
                    if a["name"] == name:
                        asset_url = a.get("browser_download_url")
                        break
                if asset_url:
                    break
            if not asset_url and sys.platform == 'darwin':
                for a in assets:
                    n = str(a.get("name", "")).lower()
                    if n.endswith(".zip") and "mac" in n:
                        asset_url = a.get("browser_download_url")
                        break
        if not asset_url:
            wx.MessageBox(f"Could not find a matching update archive in release assets.", "Update Error", wx.ICON_ERROR); return
        ext = ".exe" if use_installer else ".zip"
        dest = os.path.join(tempfile.gettempdir(), f"thrive_update{ext}")
        progress = wx.ProgressDialog("Downloading Update", "Starting download...", maximum=100, parent=self,
            style=wx.PD_APP_MODAL | wx.PD_AUTO_HIDE | wx.PD_CAN_ABORT | wx.PD_SMOOTH)
        def _done(success, error):
            progress.Destroy()
            if success:
                try:
                    if use_installer and sys.platform == 'win32':
                        apply_installer_update(dest)
                    else:
                        apply_zip_update(dest)
                except Exception as apply_err:
                    wx.MessageBox(f"Failed to install update:\n{apply_err}", "Update Error", wx.ICON_ERROR)
                    return
                app = wx.GetApp(); app.intentional_disconnect = True
                try: self.sock.sendall(json.dumps({"action":"logout"}).encode()+b"\n")
                except: pass
                try: self.sock.close()
                except: pass
                if self.task_bar_icon: self.task_bar_icon.Destroy()
                self.is_exiting = True; self.Destroy()
                app.ExitMainLoop()
            else:
                wx.MessageBox(f"Download failed:\n{error}", "Update Error", wx.ICON_ERROR)
        expected_sha256 = None
        if UPDATE_CONTEXT.get("source") == "feed":
            if sys.platform == "darwin": expected_sha256 = UPDATE_CONTEXT.get("mac_zip_sha256")
            elif use_installer: expected_sha256 = UPDATE_CONTEXT.get("installer_sha256")
            else: expected_sha256 = UPDATE_CONTEXT.get("win_zip_sha256")
        download_update(asset_url, dest, progress, _done, expected_sha256=expected_sha256)
    def _prompt_invite_user(self, username, methods=None):
        with InviteUserDialog(self, username, methods=methods) as dlg:
            if dlg.ShowModal() == wx.ID_OK:
                payload = {
                    "action": "invite_user",
                    "username": username,
                    "method": dlg.get_method(),
                    "target": dlg.get_target(),
                    "include_link": dlg.should_include_link(),
                }
                try:
                    self.sock.sendall((json.dumps(payload) + "\n").encode())
                except Exception as e:
                    wx.MessageBox(f"Could not send invite request: {e}", "Invite Failed", wx.OK | wx.ICON_ERROR)
    def on_add_contact_failed(self, payload):
        if isinstance(payload, dict):
            reason = payload.get("reason", "Add contact failed.")
            invite_methods = payload.get("invite_methods", [])
            suggest_invite = bool(payload.get("suggest_invite"))
        else:
            reason = str(payload)
            invite_methods = []
            suggest_invite = False
        show_notification("Add contact failed", str(reason), timeout=7)
        match = re.search(r"User '([^']+)' does not exist", str(reason))
        if not match:
            return
        missing_user = match.group(1)
        if not suggest_invite and not invite_methods:
            invite_methods = ["email", "sms"]
        show_notification(
            "Invite tip",
            f"{missing_user} is not on this server yet. Use Invite User from the menu if needed.",
            timeout=8,
        )
    def on_invite_result(self, msg):
        ok = bool(msg.get("ok"))
        method = msg.get("method", "invite")
        target = msg.get("target", "")
        reason = msg.get("reason", "")
        if ok:
            show_notification("Invite Sent", f"{method.upper()} invite sent to {target or 'recipient'}.", timeout=8)
        else:
            wx.MessageBox(reason or "Invite could not be sent.", "Invite Failed", wx.OK | wx.ICON_ERROR)
    def on_add_contact_success(self, contact_data):
        c = contact_data; self.contact_states[c["user"]] = c["blocked"]
        display_name = str(c.get("display_name", "") or "").strip()
        if not display_name:
            display_name = str(self._pending_display_names.pop(c["user"], "") or "").strip()
        if display_name and not self.get_contact_display_name(c["user"]):
            self.set_contact_display_name(c["user"], display_name)
        status = c.get("status_text", "online") if c["online"] and not c["blocked"] else "offline"
        if c.get("is_admin"): status += " (Admin)"
        updated = False
        for row in self._all_contacts:
            if row.get("user") == c["user"]:
                row["status"] = status
                row["blocked"] = c["blocked"]
                if display_name:
                    row["display_name"] = display_name
                updated = True
                break
        if not updated:
            self._all_contacts.append({"user": c["user"], "status": status, "blocked": c["blocked"], "display_name": display_name})
        bot_token = str(c.get("bot_auth_token", "") or "").strip()
        if bot_token:
            bot_auth_type = str(c.get("bot_auth_type", "") or "bot").strip() or "bot"
            show_notification("Bot Token Issued", f"{c['user']} token created for this client session.", timeout=8)
            chat = self.get_chat(c["user"])
            if chat:
                chat.append(f"{bot_auth_type} bot auth token issued for this client session. The token is hidden for safety.", "System", time.time())
        self._apply_search_filter()
        chat = self.get_chat(c["user"])
        if chat:
            chat.hide_add_button()
            chat.send_pending_after_contact_added()
        if self._directory_dlg:
            for u in self._directory_dlg._all_users:
                if u["user"] == c["user"]: u["is_contact"] = True; u["is_blocked"] = c["blocked"] == 1; break
            self._directory_dlg._populate_all_tabs(); self._directory_dlg.update_button_states()
    def on_bot_token_revoked(self, bot_name):
        show_notification("Bot Token Revoked", f"{bot_name} token removed for this client.", timeout=6)
        chat = self.get_chat(bot_name)
        if chat:
            chat.append("Bot auth token was revoked after contact removal.", "System", time.time())
    def on_server_alert(self, message):
        wx.GetApp().play_sound("receive.wav")
        show_notification("Server Alert", message, timeout=8)
    def on_other_device_login(self, msg):
        ip = str(msg.get("ip", "") or "").strip()
        suffix = f" (IP: {ip})" if ip else ""
        wx.GetApp().play_sound("receive.wav")
        show_notification("Account Sign-In Alert", f"This account signed in from another device{suffix}.", timeout=8)
    def on_file_transfers(self, _):
        with FileTransfersDialog(self, wx.GetApp().transfer_history) as dlg:
            dlg.ShowModal()
    def on_group_calls(self, _):
        if not self._feature_can_use("group_call"):
            wx.MessageBox("Group calls are disabled for your account on this server.", "Feature Disabled", wx.OK | wx.ICON_INFORMATION)
            return
        dlg = self._group_call_dlg
        if dlg and dlg.IsShown():
            dlg.Raise()
            dlg.SetFocus()
            try:
                self.sock.sendall((json.dumps({"action": "group_call_list"}) + "\n").encode())
            except Exception:
                pass
            return
        self._group_call_dlg = GroupCallDialog(self, self.sock, self.user)
        self._group_call_dlg.Show()
        try:
            self.sock.sendall((json.dumps({"action": "group_call_list"}) + "\n").encode())
        except Exception:
            pass
    def on_group_call_list_response(self, msg):
        if self._group_call_dlg and self._group_call_dlg.IsShown():
            self._group_call_dlg.set_calls(msg.get("calls", []))
    def on_group_call_event(self, msg):
        if self._group_call_dlg and self._group_call_dlg.IsShown():
            self._group_call_dlg.handle_call_event(msg)
    def on_group_call_result(self, msg):
        if self._group_call_dlg and self._group_call_dlg.IsShown():
            self._group_call_dlg.handle_call_result(msg)
    def on_group_call_signal(self, msg):
        if self._group_call_dlg and self._group_call_dlg.IsShown():
            self._group_call_dlg.handle_call_signal(msg)
    def on_group_call_signal_result(self, msg):
        if self._group_call_dlg and self._group_call_dlg.IsShown():
            self._group_call_dlg.handle_signal_result(msg)
    def on_group_call_audio(self, msg):
        if self._group_call_dlg and self._group_call_dlg.IsShown():
            self._group_call_dlg.handle_audio(msg)
    def on_voice_call_incoming(self, msg):
        caller = str(msg.get("from", "")); call_id = str(msg.get("call_id", ""))
        wx.GetApp().play_sound("incoming_call.wav")
        answer = wx.MessageBox(f"{caller} is calling. Answer this voice call?", "Incoming Voice Call", wx.YES_NO | wx.ICON_QUESTION, self)
        wx.GetApp().stop_current_sound()
        action = "voice_call_accept" if answer == wx.YES else "voice_call_decline"
        self.sock.sendall((json.dumps({"action": action, "call_id": call_id}) + "\n").encode())
    def on_voice_call_event(self, msg):
        event = msg.get("event", ""); call_id = str(msg.get("call_id", "")); other = str(msg.get("with", ""))
        if event == "ringing": wx.GetApp().play_sound("outgoing_call.wav"); show_notification("Voice call", f"Calling {other}...", timeout=5); return
        if event == "failed": wx.GetApp().play_sound("call_ended.wav"); wx.MessageBox(msg.get("reason", "Call failed."), "Voice Call", wx.OK | wx.ICON_WARNING, self); return
        if event == "accepted":
            wx.GetApp().play_sound("call_connected.wav")
            if self._group_call_dlg and self._group_call_dlg.IsShown(): self._group_call_dlg._close_sound_played = True; self._group_call_dlg.Close()
            self._group_call_dlg = GroupCallDialog(self, self.sock, self.user)
            self._group_call_dlg.configure_direct_call(call_id, other)
            self._group_call_dlg.Show(); self._group_call_dlg.start_audio(); return
        if event in ("declined", "ended"):
            wx.GetApp().play_sound("call_ended.wav")
            if self._group_call_dlg and self._group_call_dlg.direct_call_id == call_id: self._group_call_dlg._close_sound_played = True; self._group_call_dlg.Close()
            show_notification("Voice call", "Call declined." if event == "declined" else "Call ended.", timeout=4)
    def on_add(self, _):
        with wx.TextEntryDialog(self, "Enter the username of the contact you wish to add:", "Add Contact") as dlg:
            if dlg.ShowModal() == wx.ID_OK:
                c = dlg.GetValue().strip()
                if not c: wx.MessageBox("Username cannot be blank.", "Input Error", wx.ICON_ERROR); return
                if c == self.user: wx.MessageBox("You cannot add yourself as a contact.", "Input Error", wx.ICON_ERROR); return
                try:
                    self.sock.sendall(json.dumps({"action":"add_contact","to":c}).encode()+b"\n")
                except Exception as e:
                    wx.MessageBox(f"Could not add contact {c}:\n{e}", "Connection Error", wx.OK | wx.ICON_ERROR)
    def load_contacts(self, contacts):
        deduped = {}
        for c in contacts:
            deduped[c["user"]] = c
        contacts = list(deduped.values())
        self.contact_states = {c["user"]: c["blocked"] for c in contacts}
        self._all_contacts = []
        for c in contacts:
            status = c.get("status_text", "online") if c["online"] and not c["blocked"] else "offline"
            if c.get("is_admin"): status += " (Admin)"
            display_name = str(c.get("display_name", "") or "").strip()
            if display_name and not self.get_contact_display_name(c["user"]):
                self.set_contact_display_name(c["user"], display_name)
            self._all_contacts.append({"user": c["user"], "status": status, "blocked": c["blocked"], "display_name": display_name})
        self._apply_search_filter()
        if not self._all_contacts and not self._empty_prompt_shown:
            self._empty_prompt_shown = True
            self._schedule_empty_contacts_tip()
            wx.CallLater(500, self.on_user_directory, None)
    def _apply_search_filter(self):
        query = self.search_box.GetValue().strip().lower()
        tokens = query.split()
        filters = {"status": [], "role": [], "type": [], "name": []}
        plain = []
        for token in tokens:
            key, separator, value = token.partition(":")
            if separator and key in filters and value: filters[key].append(value)
            else: plain.append(token)
        self.lv.Clear()
        self._contact_display_map = []
        first_real_idx = -1
        contacts = list(self._all_contacts)
        if self._sort_mode == "name_desc":
            contacts = sorted(contacts, key=lambda c: c["user"].lower(), reverse=True)
        elif self._sort_mode == "status":
            contacts = sorted(contacts, key=lambda c: (c["status"].startswith("offline"), c["user"].lower()))
        else:
            contacts = sorted(contacts, key=lambda c: c["user"].lower())
        for c in contacts:
            display_name = str(c.get("display_name", "") or self.get_contact_display_name(c["user"]) or "").strip()
            searchable_name = f"{c['user']} {display_name}".lower()
            status = c["status"].lower()
            is_admin = "(admin)" in status
            is_bot = c["user"].lower().endswith("-bot")
            if plain and not all(term in searchable_name or term in status for term in plain):
                continue
            if filters["name"] and not all(term in searchable_name for term in filters["name"]):
                continue
            if filters["status"] and not all((term == "online" and not status.startswith("offline")) or (term == "offline" and status.startswith("offline")) or term in status for term in filters["status"]):
                continue
            if filters["role"] and not all((term == "admin" and is_admin) or (term == "user" and not is_admin) for term in filters["role"]):
                continue
            if filters["type"] and not all((term == "bot" and is_bot) or (term == "user" and not is_bot) for term in filters["type"]):
                continue
            unread = int(self._unread_counts.get(c["user"], 0) or 0)
            user_label = self.format_user_label(c["user"], include_username=True)
            unread_text = f"  |  {user_label} has {unread} new message{'s' if unread != 1 else ''}" if unread > 0 else ""
            display = f"{user_label}  |  {c['status']}{unread_text}"
            self.lv.Append(display)
            idx = self.lv.GetCount() - 1
            self._contact_display_map.append(c["user"])
            if first_real_idx == -1:
                first_real_idx = idx
        if self.lv.GetCount() == 0:
            self.lv.Append("(No contacts)  |  Press Alt+A to add a contact")
            self._contact_display_map.append(None)
        elif first_real_idx >= 0:
            self.lv.SetSelection(first_real_idx)
        self.update_button_states()
    def _select_contact_from_context_event(self, event):
        try:
            pos = event.GetPosition()
        except Exception:
            pos = wx.DefaultPosition
        try:
            if isinstance(pos, wx.Point) and pos.x >= 0 and pos.y >= 0:
                idx = self.lv.HitTest(self.lv.ScreenToClient(pos))
                if idx != wx.NOT_FOUND:
                    self.lv.SetSelection(idx)
        except Exception:
            pass
        if self.lv.GetSelection() == wx.NOT_FOUND and self.lv.GetCount() > 0:
            self.lv.SetSelection(0)
        self.update_button_states()
    def on_contact_context_menu(self, event):
        self._select_contact_from_context_event(event)
        selected = self._selected_contact_name()
        has_contact = bool(selected and selected in self.contact_states)
        menu = wx.Menu()
        mi_chat = menu.Append(wx.ID_ANY, "Start Chat")
        mi_add = menu.Append(wx.ID_ANY, "Add Contact")
        mi_file = menu.Append(wx.ID_ANY, "Send File")
        mi_log = menu.Append(wx.ID_ANY, "Toggle Chat History")
        mi_display_name = menu.Append(wx.ID_ANY, "Set Display Name")
        mi_block = menu.Append(wx.ID_ANY, "Block/Unblock")
        mi_delete = menu.Append(wx.ID_ANY, "Delete Contact")
        menu.AppendSeparator()
        mi_dir = menu.Append(wx.ID_ANY, "Open User Directory")
        mi_chat.Enable(bool(selected))
        mi_add.Enable(True)
        mi_file.Enable(bool(selected))
        mi_log.Enable(bool(selected))
        mi_display_name.Enable(has_contact)
        mi_block.Enable(has_contact)
        mi_delete.Enable(has_contact)
        self.Bind(wx.EVT_MENU, self.on_send, id=mi_chat.GetId())
        self.Bind(wx.EVT_MENU, self.on_add, id=mi_add.GetId())
        self.Bind(wx.EVT_MENU, self.on_send_file, id=mi_file.GetId())
        self.Bind(wx.EVT_MENU, self.on_toggle_selected_chat_logging, id=mi_log.GetId())
        self.Bind(wx.EVT_MENU, self.on_set_contact_display_name, id=mi_display_name.GetId())
        self.Bind(wx.EVT_MENU, self.on_block_toggle, id=mi_block.GetId())
        self.Bind(wx.EVT_MENU, self.on_delete, id=mi_delete.GetId())
        self.Bind(wx.EVT_MENU, self.on_user_directory, id=mi_dir.GetId())
        self.PopupMenu(menu)
        menu.Destroy()
    def on_toggle_selected_chat_logging(self, _):
        c = self._selected_contact_name()
        if not c:
            return
        app = wx.GetApp()
        if 'chat_logging' not in app.user_config or not isinstance(app.user_config.get('chat_logging'), dict):
            app.user_config['chat_logging'] = {}
        current = is_chat_logging_enabled(app.user_config, c)
        app.user_config['chat_logging'][c] = not current
        save_user_config(app.user_config)
        chat = self.get_chat(c)
        if chat:
            chat.logging_enabled = bool(app.user_config['chat_logging'].get(c, not current))
        state = "enabled" if not current else "disabled"
        show_notification("Chat history", f"Chat history {state} for {c}.", timeout=5)
    def on_set_contact_display_name(self, _):
        c = self._selected_contact_name()
        if not c or c not in self.contact_states:
            return
        current = self.get_contact_display_name(c)
        with wx.TextEntryDialog(
            self,
            f"Set display name for {c} (leave blank to clear):",
            "Contact Display Name",
            value=current,
        ) as dlg:
            if dlg.ShowModal() != wx.ID_OK:
                return
            chosen = dlg.GetValue().strip()
        self.set_contact_display_name(c, chosen)
        for entry in self._all_contacts:
            if entry.get("user") == c:
                entry["display_name"] = chosen
                break
        self._apply_search_filter()
    def on_search(self, event):
        self._apply_search_filter()
    def on_focus_contact_search(self, _):
        self.main_notebook.SetSelection(0)
        self.search_box.SetFocus()
        self.search_box.SelectAll()
    def on_admin_status_change(self, user, is_admin):
        for c in self._all_contacts:
            if c["user"] == user:
                base_status = c["status"].replace(" (Admin)", "")
                c["status"] = base_status + " (Admin)" if is_admin else base_status; break
        self._apply_search_filter()
    def on_admin(self, _):
        if not self._feature_can_use("admin_console"):
            wx.MessageBox("Admin console is disabled for your account on this server.", "Feature Disabled", wx.OK | wx.ICON_INFORMATION)
            return
        dlg = self.get_admin_dialog() or AdminDialog(self, self.sock)
        dlg.Show()
        dlg.input_ctrl.SetFocus()
    def get_admin_dialog(self):
        for child in self.GetChildren():
            if isinstance(child, AdminDialog): return child
        return None
    def on_admin_response(self, response_text):
        dlg = self.get_admin_dialog()
        if dlg: dlg.append_response(response_text)
    def on_close_window(self, event):
        if self.is_exiting: event.Skip()
        else:
            if sys.platform == 'win32':
                # While we are still the foreground process, hand focus to the
                # topmost visible window belonging to another process.  This
                # prevents Windows from promoting any of our owned windows when
                # we hide, because focus already belongs to someone else.
                # We intentionally skip the IsWindowEnabled check because apps
                # like VMware Workstation report as disabled when the VM has
                # input capture, but can still legitimately receive foreground.
                our_pid = ctypes.windll.kernel32.GetCurrentProcessId()
                found = ctypes.c_void_p(0)
                EnumWindowsProc = ctypes.WINFUNCTYPE(ctypes.c_bool, ctypes.c_void_p, ctypes.c_void_p)
                def _find_other(hwnd, _):
                    if not ctypes.windll.user32.IsWindowVisible(hwnd): return True
                    pid = ctypes.c_ulong(0)
                    ctypes.windll.user32.GetWindowThreadProcessId(hwnd, ctypes.byref(pid))
                    if pid.value != our_pid:
                        found.value = hwnd
                        return False
                    return True
                ctypes.windll.user32.EnumWindows(EnumWindowsProc(_find_other), None)
                # Set focus only after EnumWindows releases its window-list
                # lock; doing this in the callback can deadlock NVDA hooks.
                if found.value:
                    ctypes.windll.user32.SetForegroundWindow(found.value)
            for win in self.chat_windows():
                if win.IsShown():
                    win._restore_from_tray = True; win.Hide()
            self.Hide(); self.task_bar_icon = ThriveTaskBarIcon(self)
    def restore_from_tray(self):
        if self.task_bar_icon: self.task_bar_icon.Destroy(); self.task_bar_icon = None
        self.Show(); self.Raise()
        if self._directory_dlg and self._directory_dlg.IsShown(): self._directory_dlg.Raise()
        for win in self.chat_windows():
            if getattr(win, '_restore_from_tray', False):
                win._restore_from_tray = False; win.ShowWithoutActivating()
        for child in self.GetChildren():
            if isinstance(child, AdminDialog) and child.IsShown(): child.Raise()
    def on_exit(self, _):
        print("Exiting application...");
        app = wx.GetApp(); app.intentional_disconnect = True
        app.reconnect_stop_event.set(); app.reconnect_in_progress = False
        try: self.sock.sendall(json.dumps({"action":"logout"}).encode()+b"\n")
        except: pass
        try: self.sock.close()
        except: pass
        if self._directory_dlg: self._directory_dlg.Destroy(); self._directory_dlg = None
        if self.task_bar_icon: self.task_bar_icon.Destroy()
        self.is_exiting = True; self.Destroy()
        app.ExitMainLoop()
    def on_logout(self, _):
        self.is_exiting = True; app = wx.GetApp(); app.intentional_disconnect = True
        app.reconnect_stop_event.set(); app.reconnect_in_progress = False
        try: self.sock.sendall(json.dumps({"action":"logout"}).encode()+b"\n")
        except: pass
        try: self.sock.close()
        except: pass
        if self._directory_dlg: self._directory_dlg.Destroy(); self._directory_dlg = None
        app.play_sound("logout.wav"); self.Destroy()
        app.show_login_dialog()
    def on_key(self, evt):
        if evt.GetKeyCode() == wx.WXK_F1:
            open_help_docs_for_context("main", self)
        elif evt.CmdDown() and evt.GetKeyCode() == ord(','):
            self.on_settings(None)
            return
        elif evt.GetKeyCode() == wx.WXK_ESCAPE:
            if wx.Window.FindFocus() is self.search_box:
                self.lv.SetFocus()
                return
            action = str(wx.GetApp().user_config.get('escape_main_action', 'none') or 'none')
            if action == 'quit':
                self.on_exit(None)
            elif action == 'minimize':
                self.minimize_to_tray()
            return
        elif evt.GetKeyCode() in (wx.WXK_RETURN, wx.WXK_NUMPAD_ENTER):
            focused = wx.Window.FindFocus()
            if focused is self.lv:
                self.on_contact_activated(None)
                return
            if isinstance(focused, wx.Button):
                click_evt = wx.CommandEvent(wx.EVT_BUTTON.typeId, focused.GetId())
                focused.GetEventHandler().ProcessEvent(click_evt)
                return
            self.on_send(None)
            return
        elif evt.GetKeyCode() == wx.WXK_DELETE: self.on_delete(None)
        else: evt.Skip()
    def on_block_toggle(self, _):
        c = self._selected_contact_name()
        if not c: return
        blocked = self.contact_states.get(c,0) == 1
        action = "unblock_contact" if blocked else "block_contact"
        try:
            self.sock.sendall(json.dumps({"action":action,"to":c}).encode()+b"\n")
        except Exception as e:
            wx.MessageBox(f"Could not update block state for {c}:\n{e}", "Connection Error", wx.OK | wx.ICON_ERROR)
            return
        self.contact_states[c] = 0 if blocked else 1
        for entry in self._all_contacts:
            if entry["user"] == c: entry["blocked"] = 0 if blocked else 1; break
        self._apply_search_filter()
    def on_delete(self, _):
        c = self._selected_contact_name()
        if not c or c not in self.contact_states:
            return
        try:
            self.sock.sendall(json.dumps({"action":"delete_contact","to":c}).encode()+b"\n")
        except Exception as e:
            wx.MessageBox(f"Could not delete contact {c}:\n{e}", "Connection Error", wx.OK | wx.ICON_ERROR)
            return
        self.contact_states.pop(c, None)
        self.set_contact_display_name(c, "")
        self._all_contacts = [entry for entry in self._all_contacts if entry["user"] != c]
        self._apply_search_filter()
    def on_send(self, _):
        c = self._selected_contact_name()
        if not c:
            if not self._all_contacts:
                self._show_add_contact_prompt()
            return
        app = wx.GetApp(); is_logging_enabled = is_chat_logging_enabled(app.user_config, c)
        dlg = self.get_chat(c) or ChatDialog(
            self,
            c,
            self.sock,
            self.user,
            is_logging_enabled,
            can_call=self.can_use_voice_call(),
            show_call=self.is_voice_call_visible(),
        )
        dlg.open_chat()
        self._clear_unread(c)
    def on_send_file(self, _):
        c = self._selected_contact_name()
        if not c: return
        wx.GetApp().send_file_to(c)
    def on_contact_activated(self, event):
        idx = self.lv.GetSelection()
        if idx == wx.NOT_FOUND:
            return
        contact = self._selected_contact_name()
        if contact not in self.contact_states:
            self._show_add_contact_prompt()
            return
        status = next((c["status"] for c in self._all_contacts if c["user"] == contact), "")
        urls = extract_urls(status)
        if urls:
            open_path_or_url(urls[0])
            return
        self.on_send(None)
    def receive_message(self, msg):
        app = wx.GetApp()
        sender = str(msg.get("from") or "").strip()
        if not sender:
            return
        text = str(msg.get("msg", "") or "")
        # Some senders (relays, CLI tools) omit "time"; use the local receive time instead of dropping the message.
        ts = msg.get("time") or datetime.datetime.now().isoformat()
        if parse_timestamp_value(ts) is None:
            ts = datetime.datetime.now().isoformat()
        is_logging_enabled = is_chat_logging_enabled(app.user_config, sender)
        is_contact = sender in self.contact_states
        dlg = self.get_chat(sender)
        if not dlg:
            dlg = ChatDialog(
                self,
                sender,
                self.sock,
                self.user,
                is_logging_enabled,
                is_contact=is_contact,
                can_call=self.can_use_voice_call(),
                show_call=self.is_voice_call_visible(),
            )
        incoming_behavior = str(app.user_config.get('incoming_message_behavior', 'silent_count') or 'silent_count').strip().lower()
        if incoming_behavior == 'popup':
            # Show it, but never take focus or switch away from the tab being read.
            dlg.open_chat(activate=False, select=False)
        elif dlg.window and dlg.window.tabbed and dlg.window.IsShown() and not dlg.is_chat_visible():
            # The chat window is open: a new conversation appears as an unread tab without switching to it.
            dlg.open_chat(activate=False, select=False)
        voice = msg.get("voice") if isinstance(msg.get("voice"), dict) else None
        voice_row = None
        if voice and voice.get("b64"):
            try:
                os.makedirs(voice_cache_dir(), exist_ok=True)
                vpath = os.path.join(voice_cache_dir(), f"{re.sub(r'[^A-Za-z0-9_-]', '', str(msg.get('id') or uuid.uuid4().hex))}.mp3")
                with open(vpath, "wb") as fh:
                    fh.write(base64.b64decode(voice["b64"]))
                voice_row = {"path": vpath, "duration": float(voice.get("duration") or 0), "voicemail": bool(voice.get("voicemail"))}
                kind = "voicemail" if voice_row["voicemail"] else "voice"
                app.add_transfer_history("received", sender, f"{'Voicemail' if kind == 'voicemail' else 'Voice message'} "
                                         f"{datetime.datetime.now().strftime('%Y-%m-%d %H-%M')}.mp3", vpath, "received", kind=kind)
            except Exception as e:
                print(f"Could not save voice message: {e}")
                voice_row = None
        if voice_row:
            label = f"{'Voicemail' if voice_row['voicemail'] else 'Voice message'} ({format_seconds(voice_row['duration'])})"
            if text and not re.match(r"^(Voice message|Voicemail) \(\d+:\d\d\)$", text):
                dlg.append(text, sender, ts, announce=False, msg_id=str(msg.get("id") or "") or None)
                dlg.append(label, sender, ts, announce=False, voice=voice_row)
            else:
                dlg.append(label, sender, ts, announce=False, msg_id=str(msg.get("id") or "") or None, voice=voice_row)
            app.play_sound("voicemail_new.wav" if voice_row["voicemail"] else "voice_message_receive.wav")
        else:
            dlg.append(text, sender, ts, announce=False, msg_id=str(msg.get("id") or "") or None)
        dlg.set_typing_label(sender, False)
        self.clear_typing_state(sender)
        is_focused_chat = dlg.is_active_chat()
        if not is_focused_chat:
            dlg.mark_tab_unread()
            self._mark_unread(sender)
            if incoming_behavior == 'notify':
                show_notification("New message", f"New message from {sender}.", timeout=5)
            elif incoming_behavior == 'play_sound':
                app.play_sound("receive.wav")
        else:
            self._clear_unread(sender)
        played_bot_tts = play_tts_audio_from_message(msg)
        if voice_row:
            sender_label = self.format_user_label(sender)
            kind = "a voicemail" if voice_row["voicemail"] else "a voice message"
            speak_text(f"{sender_label} sent {kind}, {format_seconds(voice_row['duration'])}. Press Enter on it to play.", interrupt=False)
            if app.user_config.get('auto_play_voice_messages', False) and is_focused_chat:
                dlg.voice_player.play(voice_row["path"], dlg._voice_label(dlg._history_rows[-1]))
            played_bot_tts = True
        # Speak once here (append() is told not to), and not over a bot's own voice audio.
        if app.user_config.get('read_messages_aloud', False) and not played_bot_tts:
            sender_label = self.format_user_label(sender)
            speak_text(f"{sender_label} says {text}")
    am_admin = False
    def _chat_for_message_event(self, msg):
        me = str(self.user or "").lower()
        frm = str(msg.get("from") or "")
        to = str(msg.get("to") or "")
        other = to if frm.lower() == me else frm
        return self.get_chat(other)
    def on_message_sent_ack(self, msg):
        wx.GetApp().message_acknowledged(msg.get("client_id"))
        chat = self.get_chat(msg.get("to"))
        if chat:
            chat.set_row_message_id(str(msg.get("client_id") or ""), str(msg.get("id") or ""))
    def on_message_changed(self, msg):
        chat = self._chat_for_message_event(msg)
        if not chat:
            return
        actor = str(msg.get("edited_by") or msg.get("deleted_by") or "")
        by_me = actor.lower() == str(self.user or "").lower()
        label = self.format_user_label(actor) if actor else "Someone"
        if msg.get("action") == "msg_edited":
            if chat.apply_remote_edit(str(msg.get("id") or ""), str(msg.get("msg", "") or "")) and not by_me:
                speak_text(f"{label} edited a message", interrupt=False)
        else:
            if chat.apply_remote_delete(str(msg.get("id") or "")) and not by_me:
                speak_text(f"{label} deleted a message", interrupt=False)
    def on_message_change_result(self, msg):
        is_edit = msg.get("action") == "msg_edit_result"
        chat = None
        for child in self.all_chats():
            if child.has_message_id(str(msg.get("id") or "")):
                chat = child
                break
        if msg.get("ok"):
            wx.GetApp().play_sound("message_edited.wav" if is_edit else "message_deleted.wav")
            speak_text("Message edited" if is_edit else "Deleted for everyone", interrupt=True)
            return
        reason = str(msg.get("reason") or ("The message could not be edited." if is_edit else "The message could not be deleted."))
        if chat:
            chat.append_error(reason)
        else:
            speak_text(reason, interrupt=True)
    TYPING_STOP_ANNOUNCE_DELAY_MS = 2500
    def _typing_states(self):
        if not hasattr(self, "_typing_state_by_user"):
            self._typing_state_by_user = {}
        return self._typing_state_by_user
    def on_typing_event(self, msg):
        from_user = str(msg.get("from") or "").strip()
        if not from_user:
            return
        is_typing = bool(msg.get("typing", False))
        app = wx.GetApp()
        key = from_user.lower()
        state = self._typing_states().setdefault(key, {"typing": False, "stop_call": None})
        pending_stop = state.get("stop_call")
        if pending_stop:
            try:
                pending_stop.Stop()
            except Exception:
                pass
            state["stop_call"] = None
        chat = self.get_chat(from_user)
        if chat:
            chat.set_typing_label(from_user, is_typing)
        if not app.user_config.get('typing_indicators', True):
            state["typing"] = False
            return
        announce = bool(app.user_config.get('announce_typing', True))
        label = self.format_user_label(from_user)
        if is_typing:
            # Announce only the change to "typing"; repeats while they keep typing stay quiet.
            if not state["typing"] and announce:
                speak_text(f"{label} is typing", interrupt=False)
            state["typing"] = True
        elif state["typing"]:
            # Wait briefly: if their message or more typing arrives first, "stopped typing" is just noise.
            def _announce_stop():
                state["stop_call"] = None
                if state["typing"]:
                    state["typing"] = False
                    if announce:
                        speak_text(f"{label} stopped typing", interrupt=False)
            state["stop_call"] = wx.CallLater(self.TYPING_STOP_ANNOUNCE_DELAY_MS, _announce_stop)
    def clear_typing_state(self, username):
        """A message from this user means they're done typing; drop any pending "stopped typing"."""
        state = self._typing_states().get(str(username or "").strip().lower())
        if not state:
            return
        pending_stop = state.get("stop_call")
        if pending_stop:
            try:
                pending_stop.Stop()
            except Exception:
                pass
        state["stop_call"] = None
        state["typing"] = False
    def on_message_failed(self, to, reason):
        wx.GetApp().message_rejected(to)
        if "offline" in str(reason).lower():
            reason = f"{reason} Press Control Shift R to leave a voicemail they'll get when they sign in."
        chat_dlg = self.get_chat(to)
        (chat_dlg.append_error(reason) if chat_dlg else wx.MessageBox(reason, "Message Failed", wx.OK | wx.ICON_ERROR))
    def on_voicemail_saved(self, msg):
        chat = self.get_chat(msg.get("to"))
        text = f"Voicemail saved. {msg.get('to')} will get it when they sign in."
        wx.GetApp().play_sound("voicemail_left.wav")
        if chat:
            chat.append(text, "System", time.time())
        speak_text(text, interrupt=False)
    def on_voicemail_list(self, _=None):
        entries = [e for e in reversed(wx.GetApp().transfer_history) if e.get("kind") == "voicemail" and e.get("direction") == "received"]
        if not entries:
            wx.MessageBox("You have no voicemail.", "Voicemail", wx.OK | wx.ICON_INFORMATION, self)
            return
        choices = [f"{e.get('user')}, {format_timestamp(e.get('time'))}" for e in entries]
        with wx.SingleChoiceDialog(self, "Choose a voicemail to open in its chat (File Transfers tab, Voicemail filter):",
                                   "Voicemail", choices) as dlg:
            if dlg.ShowModal() != wx.ID_OK:
                return
            entry = entries[dlg.GetSelection()]
        self.open_direct_chat(entry.get("user"))
        chat = self.get_chat(entry.get("user"))
        if chat:
            chat.transfers_page.filter_choice.SetSelection(2)
            chat.show_inner_tab(2)
    def register_chat(self, panel):
        self._chat_panels = [p for p in getattr(self, "_chat_panels", []) if p] + [panel]
    def all_chats(self):
        self._chat_panels = [p for p in getattr(self, "_chat_panels", []) if p]
        return list(self._chat_panels)
    def chat_windows(self):
        wins = []
        for p in self.all_chats():
            if p.window and p.window not in wins:
                wins.append(p.window)
        tabs = getattr(self, "_tabs_window", None)
        if tabs and tabs not in wins:
            wins.append(tabs)
        return [w for w in wins if w]
    def chat_window_for_new_chat(self):
        cfg = wx.GetApp().user_config
        tabbed = bool(cfg.get('chat_tabs', True))
        owned = not bool(cfg.get('keep_contact_list_open', True))
        if not tabbed:
            return ChatWindow(self, tabbed=False, owned=owned)
        tabs = getattr(self, "_tabs_window", None)
        if not tabs or tabs.owned != owned:
            tabs = ChatWindow(self, tabbed=True, owned=owned)
            self._tabs_window = tabs
        return tabs
    def focus_contact_list(self, announce=True):
        if self.IsIconized():
            self.Iconize(False)
        if not self.IsShown():
            self.Show()
        self.Raise()
        try:
            self.main_notebook.SetSelection(0)
        except Exception:
            pass
        target = getattr(self, "lv", None)
        if target:
            target.SetFocus()
        if announce:
            speak_text("Contact list", interrupt=True)
    def Destroy(self):
        # Chat windows are separate top-level windows (so the contact list stays in Alt+Tab); close them with it.
        self._destroy_chat_windows()
        return super().Destroy()
    def _destroy_chat_windows(self, event=None):
        for win in self.chat_windows():
            try:
                win.Destroy()
            except Exception:
                pass
        self._chat_panels = []
        self._tabs_window = None
    def get_chat(self, contact):
        wanted = str(contact or "").strip().lower()
        if not wanted:
            return None
        for child in self.all_chats():
            if str(child.contact or "").strip().lower() == wanted: return child
        return None

def get_day_with_suffix(d): return str(d) + "th" if 11 <= d <= 13 else str(d) + {1: "st", 2: "nd", 3: "rd"}.get(d % 10, "th")
def parse_timestamp_value(ts):
    try:
        if isinstance(ts, (int, float)):
            return datetime.datetime.fromtimestamp(ts)
        try:
            return datetime.datetime.fromtimestamp(float(ts))
        except (ValueError, TypeError):
            return datetime.datetime.fromisoformat(str(ts))
    except (ValueError, TypeError, OSError):
        return None

def format_timestamp(ts):
    try:
        dt = parse_timestamp_value(ts)
        if dt is None:
            return str(ts)
        day_with_suffix = get_day_with_suffix(dt.day)
        formatted_hour = dt.strftime('%I:%M %p').lstrip('0')
        return dt.strftime(f'%A, %B {day_with_suffix}, %Y at {formatted_hour}')
    except (ValueError, TypeError, OSError): return str(ts)

def format_saved_group_date(date_obj, order='mdy'):
    if not isinstance(date_obj, (datetime.date, datetime.datetime)):
        return "Unknown Date"
    d = date_obj.date() if isinstance(date_obj, datetime.datetime) else date_obj
    month = d.strftime("%B")
    if order == 'dmy':
        return f"{d.day} {month} {d.year}"
    if order == 'ymd':
        return f"{d.year} {month} {d.day}"
    if order == 'ydm':
        return f"{d.year} {d.day} {month}"
    return f"{month} {d.day} {d.year}"

def pick_user_display_name(entry):
    if not isinstance(entry, dict):
        return ""
    for key in ("display_name", "full_name", "name", "nickname"):
        val = str(entry.get(key, "") or "").strip()
        if val:
            return val
    return ""

class ModuleManagerDialog(wx.Dialog):
    def __init__(self, parent, sock):
        super().__init__(parent, title="Server Modules", size=(720, 430))
        self.sock, self.modules = sock, []
        self.Bind(wx.EVT_CLOSE, self.on_close)
        panel = wx.Panel(self); s = wx.BoxSizer(wx.VERTICAL)
        s.Add(wx.StaticText(panel, label="Modules for this server. Each one has a checkbox: press Space to turn it on or off."), 0, wx.EXPAND | wx.ALL, 8)
        self.list = wx.ListCtrl(panel, style=wx.LC_REPORT | wx.LC_SINGLE_SEL, name="Server modules")
        self._populating = False
        try:
            self.list.EnableCheckBoxes(True)
        except Exception:
            pass
        self.list.InsertColumn(0, "Module", width=170); self.list.InsertColumn(1, "State", width=90); self.list.InsertColumn(2, "Description", width=410)
        self.list.Bind(wx.EVT_LIST_ITEM_ACTIVATED, self.on_toggle)
        self.list.Bind(wx.EVT_LIST_ITEM_CHECKED, self.on_checked)
        self.list.Bind(wx.EVT_LIST_ITEM_UNCHECKED, self.on_checked)
        s.Add(self.list, 1, wx.EXPAND | wx.LEFT | wx.RIGHT | wx.BOTTOM, 8)
        row = wx.BoxSizer(wx.HORIZONTAL)
        refresh = wx.Button(panel, label="&Refresh"); refresh.Bind(wx.EVT_BUTTON, self.on_refresh)
        close = wx.Button(panel, wx.ID_CLOSE); close.Bind(wx.EVT_BUTTON, lambda event: self.Close())
        for button in (refresh, close): row.Add(button, 1, wx.RIGHT, 5)
        s.Add(row, 0, wx.EXPAND | wx.LEFT | wx.RIGHT | wx.BOTTOM, 8); panel.SetSizer(s)
    def on_close(self, event):
        parent = self.GetParent()
        if parent: parent._module_dialog = None
        event.Skip()
    def on_refresh(self, _): self.sock.sendall((json.dumps({"action": "module_list"}) + "\n").encode())
    def on_checked(self, event):
        if self._populating:
            return
        self._toggle_index(event.GetIndex())
    def on_toggle(self, _):
        index = self.list.GetFirstSelected()
        if index < 0 or index >= len(self.modules): return
        self._toggle_index(index)
    def _toggle_index(self, index):
        if index < 0 or index >= len(self.modules): return
        module = self.modules[index]
        if not module.get("installed", False):
            show_notification("Server modules", f"Installing {module.get('name', module['module_id'])} on the connected Thrive server...", timeout=6)
            self.sock.sendall((json.dumps({"action": "module_install", "module_id": module["module_id"]}) + "\n").encode())
        else:
            self.sock.sendall((json.dumps({"action": "module_set_enabled", "module_id": module["module_id"], "enabled": not module.get("enabled", False)}) + "\n").encode())
    def handle_server_action(self, msg):
        if msg.get("action") == "module_result":
            if not msg.get("ok"): wx.MessageBox(msg.get("reason", "Module update failed."), "Server Modules", wx.OK | wx.ICON_WARNING, self)
            elif msg.get("event") == "installed": show_notification("Server modules", "Module installed. Restart the Thrive server to load it.", timeout=7)
            self.on_refresh(None); return
        if not msg.get("ok"): return
        self.modules = list(msg.get("modules", [])); self._populating = True
        try:
            self.list.DeleteAllItems()
            for module in self.modules:
                index = self.list.InsertItem(self.list.GetItemCount(), module.get("name", module.get("module_id", "")))
                state = "not installed" if not module.get("installed") else ("enabled" if module.get("enabled") else "disabled")
                if module.get("experimental"): state += ", experimental"
                self.list.SetItem(index, 1, state)
                self.list.SetItem(index, 2, module.get("description", ""))
                try:
                    self.list.CheckItem(index, bool(module.get("installed") and module.get("enabled")))
                except Exception:
                    pass
        finally:
            self._populating = False


class AdminDialog(wx.Dialog):
    def __init__(self, parent, sock):
        super().__init__(parent, title="Server Side Commands", size=(450, 300)); self.sock = sock; self.Bind(wx.EVT_CHAR_HOOK, self.on_key); s = wx.BoxSizer(wx.VERTICAL)
        
        dark_mode_on = is_windows_dark_mode()
        if dark_mode_on:
            dark_color = wx.Colour(40, 40, 40); light_text_color = wx.WHITE
            WxMswDarkMode().enable(self); self.SetBackgroundColour(dark_color)
            
        # Use a single ListBox for better screen-reader navigation.
        self.hist = wx.ListBox(self, style=wx.LB_SINGLE)
        self.hist.SetToolTip("Command responses history. Use arrow keys to review responses.")
        template_row = wx.BoxSizer(wx.HORIZONTAL)
        template_row.Add(wx.StaticText(self, label="&Command template:"), 0, wx.ALIGN_CENTER_VERTICAL | wx.RIGHT, 6)
        self.command_templates = wx.Choice(self, choices=[
            "Help", "Show account limit", "Show global group policy", "List group policy keys",
            "Create account", "Invite user", "Send server alert", "Ban user", "Schedule restart",
        ])
        self.command_templates.SetSelection(0)
        self.command_templates.SetToolTip("Choose a command to insert. Review and edit it before sending.")
        template_row.Add(self.command_templates, 1, wx.RIGHT, 6)
        insert_btn = wx.Button(self, label="&Insert")
        insert_btn.SetToolTip("Insert the selected command without running it.")
        insert_btn.Bind(wx.EVT_BUTTON, self.on_insert_template)
        template_row.Add(insert_btn, 0)
        box_msg = wx.StaticBoxSizer(wx.VERTICAL, self, "&Enter command (e.g., /create user pass or /help)"); self.input_ctrl = wx.TextCtrl(box_msg.GetStaticBox(), style=wx.TE_PROCESS_ENTER)
        self.input_ctrl.SetToolTip("To get more help, type ? or help! You can also use /help or /?.")
        btn = wx.Button(self, label="&Send Command")
        btn_rules = wx.Button(self, label="Manage Bot Rules")
        btn_group_policy = wx.Button(self, label="Manage Group Policy")
        
        if dark_mode_on:
            self.hist.SetBackgroundColour(dark_color); self.hist.SetForegroundColour(light_text_color)
            box_msg.GetStaticBox().SetForegroundColour(light_text_color)
            box_msg.GetStaticBox().SetBackgroundColour(dark_color)
            self.input_ctrl.SetBackgroundColour(dark_color); self.input_ctrl.SetForegroundColour(light_text_color)
            btn.SetBackgroundColour(dark_color); btn.SetForegroundColour(light_text_color)
            btn_rules.SetBackgroundColour(dark_color); btn_rules.SetForegroundColour(light_text_color)
            btn_group_policy.SetBackgroundColour(dark_color); btn_group_policy.SetForegroundColour(light_text_color)
            
        s.Add(self.hist, 1, wx.EXPAND|wx.ALL, 5); s.Add(template_row, 0, wx.EXPAND|wx.LEFT|wx.RIGHT|wx.TOP, 5); self.input_ctrl.Bind(wx.EVT_TEXT_ENTER, self.on_send); box_msg.Add(self.input_ctrl, 0, wx.EXPAND|wx.ALL, 5)
        s.Add(box_msg, 0, wx.EXPAND|wx.ALL, 5); btn.Bind(wx.EVT_BUTTON, self.on_send); btn_rules.Bind(wx.EVT_BUTTON, self.on_bot_rules); btn_group_policy.Bind(wx.EVT_BUTTON, self.on_group_policy)
        btn_row = wx.BoxSizer(wx.HORIZONTAL)
        btn_row.Add(btn, 1, wx.RIGHT, 5)
        btn_row.Add(btn_rules, 1, wx.LEFT | wx.RIGHT, 5)
        btn_row.Add(btn_group_policy, 1, wx.LEFT, 5)
        s.Add(btn_row, 0, wx.EXPAND | wx.LEFT | wx.RIGHT | wx.BOTTOM, 5); self.SetSizer(s)
    def on_insert_template(self, _):
        templates = {
            "Help": "/help",
            "Show account limit": "/accountlimit show",
            "Show global group policy": "/gpolicy show",
            "List group policy keys": "/gpolicy keys",
            "Create account": "/create username password email@example.com",
            "Invite user": "/invite username email@example.com",
            "Send server alert": "/alert message",
            "Ban user": "/ban username MM/DD/YYYY reason",
            "Schedule restart": "/restart",
        }
        self.input_ctrl.SetValue(templates[self.command_templates.GetStringSelection()])
        self.input_ctrl.SetFocus()
        self.input_ctrl.SetInsertionPointEnd()
    def on_key(self, event):
        if event.GetKeyCode() == wx.WXK_F1:
            open_help_docs_for_context("admin", self)
        elif event.AltDown() and event.GetKeyCode() == ord('H'):
            self.hist.SetFocus()
        elif event.GetKeyCode() == wx.WXK_ESCAPE: self.Close()
        else: event.Skip()
    def on_send(self, _):
        cmd = self.input_ctrl.GetValue().strip()
        if not cmd:
            return
        raw = cmd
        if raw.startswith("/"):
            raw = raw[1:].strip()
        lower_raw = raw.lower()
        if lower_raw in ("help", "?"):
            raw = "help"
        # Allow both slash and non-slash command entry styles.
        # The server parser expects command text without leading slash.
        msg = {"action":"admin_cmd", "cmd": raw}
        self.sock.sendall(json.dumps(msg).encode()+b"\n"); self.input_ctrl.Clear(); self.input_ctrl.SetFocus()
    def on_bot_rules(self, _):
        parent = self.GetParent()
        if parent and hasattr(parent, "on_manage_bot_rules"):
            parent.on_manage_bot_rules(None)
    def on_group_policy(self, _):
        parent = self.GetParent()
        if parent and hasattr(parent, "on_manage_group_policy"):
            parent.on_manage_group_policy(None)
    def append_response(self, text):
        ts = format_timestamp(time.time())
        line = f"{ts} | {text}"
        self.hist.Append(line)
        self.hist.SetSelection(self.hist.GetCount() - 1)
        if wx.GetApp().user_config.get('read_messages_aloud', False):
            speak_text(text)

class BotRulesDialog(wx.Dialog):
    def __init__(self, parent, sock, bot_names=None):
        super().__init__(parent, title="Bot Rules Manager", size=(700, 520))
        self.sock = sock
        self.current_bot = ""
        self.Bind(wx.EVT_CLOSE, self.on_close)
        self.Bind(wx.EVT_CHAR_HOOK, self.on_key)
        panel = wx.Panel(self)
        s = wx.BoxSizer(wx.VERTICAL)

        dark_mode_on = is_windows_dark_mode()
        if dark_mode_on:
            dark_color = wx.Colour(40, 40, 40)
            light_text_color = wx.WHITE
            WxMswDarkMode().enable(self)
            self.SetBackgroundColour(dark_color)
            panel.SetBackgroundColour(dark_color)

        top_row = wx.BoxSizer(wx.HORIZONTAL)
        top_row.Add(wx.StaticText(panel, label="Bot username:"), 0, wx.ALIGN_CENTER_VERTICAL | wx.RIGHT, 6)
        self.bot_choice = wx.ComboBox(panel, style=wx.CB_DROPDOWN)
        for bot in bot_names or []:
            self.bot_choice.Append(bot)
        if self.bot_choice.GetCount() == 0:
            self.bot_choice.Append("openclaw-bot")
        self.bot_choice.SetSelection(0)
        top_row.Add(self.bot_choice, 1, wx.EXPAND | wx.RIGHT, 8)
        self.btn_load = wx.Button(panel, label="Load Rules")
        self.btn_save = wx.Button(panel, label="Save Rules")
        self.btn_reset = wx.Button(panel, label="Reset to Global")
        top_row.Add(self.btn_load, 0, wx.RIGHT, 4)
        top_row.Add(self.btn_save, 0, wx.RIGHT, 4)
        top_row.Add(self.btn_reset, 0)

        self.info = wx.StaticText(panel, label="Load a bot to view active rules. Admins can edit and save overrides.")
        self.info.Wrap(640)
        self.rules_txt = wx.TextCtrl(panel, style=wx.TE_MULTILINE)

        close_row = wx.BoxSizer(wx.HORIZONTAL)
        self.btn_close = wx.Button(panel, wx.ID_CLOSE, "Close")
        close_row.AddStretchSpacer(1)
        close_row.Add(self.btn_close, 0)

        s.Add(top_row, 0, wx.EXPAND | wx.ALL, 8)
        s.Add(self.info, 0, wx.EXPAND | wx.LEFT | wx.RIGHT | wx.BOTTOM, 8)
        s.Add(self.rules_txt, 1, wx.EXPAND | wx.LEFT | wx.RIGHT | wx.BOTTOM, 8)
        s.Add(close_row, 0, wx.EXPAND | wx.LEFT | wx.RIGHT | wx.BOTTOM, 8)
        panel.SetSizer(s)

        if dark_mode_on:
            panel.SetForegroundColour(light_text_color)
            self.bot_choice.SetBackgroundColour(dark_color); self.bot_choice.SetForegroundColour(light_text_color)
            self.rules_txt.SetBackgroundColour(dark_color); self.rules_txt.SetForegroundColour(light_text_color)
            for b in (self.btn_load, self.btn_save, self.btn_reset, self.btn_close):
                b.SetBackgroundColour(dark_color); b.SetForegroundColour(light_text_color)
            self.info.SetForegroundColour(light_text_color)

        self.btn_load.Bind(wx.EVT_BUTTON, self.on_load)
        self.btn_save.Bind(wx.EVT_BUTTON, self.on_save)
        self.btn_reset.Bind(wx.EVT_BUTTON, self.on_reset)
        self.btn_close.Bind(wx.EVT_BUTTON, lambda _: self.Close())
        self.on_load(None)

    def on_key(self, event):
        if event.GetKeyCode() == wx.WXK_F1:
            open_help_docs_for_context("bot_rules", self)
            return
        if event.GetKeyCode() == wx.WXK_ESCAPE:
            self.Close()
            return
        event.Skip()

    def on_close(self, event):
        parent = self.GetParent()
        if parent and hasattr(parent, "_bot_rules_dlg"):
            parent._bot_rules_dlg = None
        event.Skip()

    def _selected_bot(self):
        bot = self.bot_choice.GetValue().strip()
        if not bot:
            bot = "openclaw-bot"
            self.bot_choice.SetValue(bot)
        self.current_bot = bot
        return bot

    def on_load(self, _):
        bot = self._selected_bot()
        try:
            self.sock.sendall((json.dumps({"action": "get_bot_rules", "bot": bot}) + "\n").encode())
            self.info.SetLabel(f"Loading rules for {bot}...")
        except Exception as e:
            wx.MessageBox(f"Failed to request bot rules: {e}", "Bot Rules", wx.OK | wx.ICON_ERROR, self)

    def on_save(self, _):
        bot = self._selected_bot()
        rules = self.rules_txt.GetValue()
        try:
            self.sock.sendall((json.dumps({"action": "set_bot_rules", "bot": bot, "rules": rules}) + "\n").encode())
            self.info.SetLabel(f"Saving rules for {bot}...")
        except Exception as e:
            wx.MessageBox(f"Failed to save bot rules: {e}", "Bot Rules", wx.OK | wx.ICON_ERROR, self)

    def on_reset(self, _):
        bot = self._selected_bot()
        try:
            self.sock.sendall((json.dumps({"action": "reset_bot_rules", "bot": bot}) + "\n").encode())
            self.info.SetLabel(f"Resetting rules for {bot}...")
        except Exception as e:
            wx.MessageBox(f"Failed to reset bot rules: {e}", "Bot Rules", wx.OK | wx.ICON_ERROR, self)

    def handle_rules_payload(self, msg):
        ok = bool(msg.get("ok"))
        if not ok:
            reason = msg.get("reason", "Could not load bot rules.")
            self.info.SetLabel(reason)
            wx.MessageBox(reason, "Bot Rules", wx.OK | wx.ICON_WARNING, self)
            return
        bot = str(msg.get("bot", self.current_bot) or self.current_bot)
        rules = str(msg.get("rules", "") or "")
        editable = bool(msg.get("editable", False))
        scope = str(msg.get("scope", "global") or "global")
        self.current_bot = bot
        self.bot_choice.SetValue(bot)
        self.rules_txt.ChangeValue(rules)
        self.rules_txt.SetEditable(editable)
        self.btn_save.Enable(editable)
        self.btn_reset.Enable(editable)
        self.info.SetLabel(f"Loaded {scope} rules for {bot}. {'Editable' if editable else 'Read-only for non-admins.'}")

    def handle_update_payload(self, msg):
        ok = bool(msg.get("ok"))
        bot = str(msg.get("bot", self.current_bot) or self.current_bot)
        if not ok:
            reason = msg.get("reason", "Bot rules update failed.")
            self.info.SetLabel(reason)
            wx.MessageBox(reason, "Bot Rules", wx.OK | wx.ICON_WARNING, self)
            return
        self.info.SetLabel(f"Rules updated for {bot}. Reloading...")
        self.on_load(None)

class GroupPolicyDialog(wx.Dialog):
    def __init__(self, parent, sock):
        super().__init__(parent, title="Group Policy Manager", size=(780, 560))
        self.sock = sock
        self.current_group = "__global__"
        self.schema = {}
        self.Bind(wx.EVT_CLOSE, self.on_close)
        self.Bind(wx.EVT_CHAR_HOOK, self.on_key)
        panel = wx.Panel(self)
        s = wx.BoxSizer(wx.VERTICAL)

        top = wx.BoxSizer(wx.HORIZONTAL)
        top.Add(wx.StaticText(panel, label="Group name (blank = global):"), 0, wx.ALIGN_CENTER_VERTICAL | wx.RIGHT, 6)
        self.group_txt = wx.TextCtrl(panel, value="")
        top.Add(self.group_txt, 1, wx.EXPAND | wx.RIGHT, 8)
        self.btn_load = wx.Button(panel, label="Load")
        self.btn_save = wx.Button(panel, label="Save")
        self.btn_reset = wx.Button(panel, label="Reset")
        top.Add(self.btn_load, 0, wx.RIGHT, 4)
        top.Add(self.btn_save, 0, wx.RIGHT, 4)
        top.Add(self.btn_reset, 0)

        self.info = wx.StaticText(panel, label="Edit advanced group chat/call controls as JSON policy.")
        self.info.Wrap(740)
        splitter = wx.SplitterWindow(panel, style=wx.SP_LIVE_UPDATE)
        self.schema_list = wx.ListBox(splitter, style=wx.LB_SINGLE)
        self.policy_txt = wx.TextCtrl(splitter, style=wx.TE_MULTILINE)
        splitter.SplitVertically(self.schema_list, self.policy_txt, 320)
        splitter.SetMinimumPaneSize(220)

        close_row = wx.BoxSizer(wx.HORIZONTAL)
        close_row.AddStretchSpacer(1)
        self.btn_close = wx.Button(panel, wx.ID_CLOSE, "Close")
        close_row.Add(self.btn_close, 0)

        s.Add(top, 0, wx.EXPAND | wx.ALL, 8)
        s.Add(self.info, 0, wx.EXPAND | wx.LEFT | wx.RIGHT | wx.BOTTOM, 8)
        s.Add(splitter, 1, wx.EXPAND | wx.LEFT | wx.RIGHT | wx.BOTTOM, 8)
        s.Add(close_row, 0, wx.EXPAND | wx.LEFT | wx.RIGHT | wx.BOTTOM, 8)
        panel.SetSizer(s)

        self.btn_load.Bind(wx.EVT_BUTTON, self.on_load)
        self.btn_save.Bind(wx.EVT_BUTTON, self.on_save)
        self.btn_reset.Bind(wx.EVT_BUTTON, self.on_reset)
        self.btn_close.Bind(wx.EVT_BUTTON, lambda _: self.Close())
        self.schema_list.SetToolTip("Policy keys and descriptions.")
        self.policy_txt.SetToolTip("Editable JSON policy payload. Save sends all keys shown.")
        self.on_load(None)

    def on_key(self, event):
        if event.GetKeyCode() == wx.WXK_F1:
            open_help_docs_for_context("settings", self)
            return
        if event.GetKeyCode() == wx.WXK_ESCAPE:
            self.Close()
            return
        event.Skip()

    def on_close(self, event):
        parent = self.GetParent()
        if parent and hasattr(parent, "_group_policy_dlg"):
            parent._group_policy_dlg = None
        event.Skip()

    def _group_value(self):
        g = self.group_txt.GetValue().strip()
        return g if g else "__global__"

    def on_load(self, _):
        group = self._group_value()
        payload = {"action": "get_group_policy"}
        if group != "__global__":
            payload["group"] = group
        try:
            self.sock.sendall((json.dumps(payload) + "\n").encode())
            self.info.SetLabel(f"Loading group policy for {group}...")
        except Exception as e:
            wx.MessageBox(f"Failed to request group policy: {e}", "Group Policy", wx.OK | wx.ICON_ERROR, self)

    def on_save(self, _):
        group = self._group_value()
        raw = self.policy_txt.GetValue().strip()
        try:
            updates = json.loads(raw) if raw else {}
            if not isinstance(updates, dict):
                raise ValueError("Policy JSON must be an object.")
        except Exception as e:
            wx.MessageBox(f"Invalid policy JSON: {e}", "Group Policy", wx.OK | wx.ICON_ERROR, self)
            return
        payload = {"action": "set_group_policy", "updates": updates}
        if group != "__global__":
            payload["group"] = group
        try:
            self.sock.sendall((json.dumps(payload) + "\n").encode())
            self.info.SetLabel(f"Saving policy for {group}...")
        except Exception as e:
            wx.MessageBox(f"Failed to save group policy: {e}", "Group Policy", wx.OK | wx.ICON_ERROR, self)

    def on_reset(self, _):
        group = self._group_value()
        payload = {"action": "reset_group_policy"}
        if group != "__global__":
            payload["group"] = group
        try:
            self.sock.sendall((json.dumps(payload) + "\n").encode())
            self.info.SetLabel(f"Resetting policy for {group}...")
        except Exception as e:
            wx.MessageBox(f"Failed to reset group policy: {e}", "Group Policy", wx.OK | wx.ICON_ERROR, self)

    def handle_policy_payload(self, msg):
        if not msg.get("ok"):
            reason = msg.get("reason", "Failed to load group policy.")
            self.info.SetLabel(reason)
            wx.MessageBox(reason, "Group Policy", wx.OK | wx.ICON_WARNING, self)
            return
        group = str(msg.get("group", "__global__") or "__global__")
        policy = msg.get("policy", {}) or {}
        self.schema = msg.get("schema", {}) or {}
        self.current_group = group
        self.group_txt.SetValue("" if group == "__global__" else group)
        try:
            self.policy_txt.ChangeValue(json.dumps(policy, indent=2, ensure_ascii=False))
        except Exception:
            self.policy_txt.ChangeValue(str(policy))
        self.schema_list.Clear()
        for key in sorted(self.schema.keys()):
            meta = self.schema.get(key, {})
            t = meta.get("type", "any")
            d = meta.get("default", "")
            desc = meta.get("description", "")
            self.schema_list.Append(f"{key} ({t}, default={d}) - {desc}")
        editable = bool(msg.get("editable", False))
        self.policy_txt.SetEditable(editable)
        self.btn_save.Enable(editable)
        self.btn_reset.Enable(editable)
        self.info.SetLabel(f"Loaded policy for {group}. {'Editable' if editable else 'Read-only (admin required).'}")

    def handle_update_payload(self, msg):
        ok = bool(msg.get("ok"))
        if not ok:
            reason = msg.get("reason", "Group policy update failed.")
            self.info.SetLabel(reason)
            wx.MessageBox(reason, "Group Policy", wx.OK | wx.ICON_WARNING, self)
            return
        self.info.SetLabel("Policy updated. Reloading...")
        self.on_load(None)

class CreateGroupRoomDialog(wx.Dialog):
    def __init__(self, parent):
        super().__init__(parent, title="Create Group Room")
        panel = wx.Panel(self)
        s = wx.BoxSizer(wx.VERTICAL)
        for label, ctrl in (
            ("Room name:", wx.TextCtrl(panel)),
            ("Description:", wx.TextCtrl(panel)),
        ):
            s.Add(wx.StaticText(panel, label=label), 0, wx.LEFT | wx.RIGHT | wx.TOP, 8)
            s.Add(ctrl, 0, wx.EXPAND | wx.LEFT | wx.RIGHT | wx.BOTTOM, 8)
            if label.startswith("Room"):
                self.name_ctrl = ctrl
            else:
                self.description_ctrl = ctrl
        s.Add(wx.StaticText(panel, label="Visibility:"), 0, wx.LEFT | wx.RIGHT | wx.TOP, 8)
        self.visibility = wx.Choice(panel, choices=["public", "private"])
        self.visibility.SetSelection(0)
        s.Add(self.visibility, 0, wx.EXPAND | wx.LEFT | wx.RIGHT | wx.BOTTOM, 8)
        s.Add(wx.StaticText(panel, label="Expiration:"), 0, wx.LEFT | wx.RIGHT | wx.TOP, 8)
        self.expiration = wx.Choice(panel, choices=["never", "day", "week", "month", "year", "empty"])
        self.expiration.SetSelection(0)
        self.expiration.SetToolTip("Empty deletes the room immediately after its last member leaves.")
        s.Add(self.expiration, 0, wx.EXPAND | wx.LEFT | wx.RIGHT | wx.BOTTOM, 8)
        buttons = self.CreateStdDialogButtonSizer(wx.OK | wx.CANCEL)
        s.Add(buttons, 0, wx.EXPAND | wx.ALL, 8)
        panel.SetSizer(s)
        outer = wx.BoxSizer(wx.VERTICAL); outer.Add(panel, 1, wx.EXPAND); self.SetSizerAndFit(outer)
        self.name_ctrl.SetFocus()

    def values(self):
        return {
            "name": self.name_ctrl.GetValue().strip(),
            "description": self.description_ctrl.GetValue().strip(),
            "visibility": self.visibility.GetStringSelection(),
            "expiration": self.expiration.GetStringSelection(),
        }


class GroupRoomSettingsDialog(wx.Dialog):
    ACTIONS = ("view", "send_messages", "send_files", "join_voice", "invite", "moderate_messages", "manage_members", "manage_room")
    ROLES = ("guest", "user", "moderator", "admin", "owner")
    def __init__(self, parent, room):
        super().__init__(parent, title=f"Room Settings — {room.get('name', '')}", size=(620, 600))
        self.room = room; panel = wx.Panel(self); s = wx.BoxSizer(wx.VERTICAL)
        s.Add(wx.StaticText(panel, label="Description:"), 0, wx.LEFT | wx.RIGHT | wx.TOP, 8)
        self.description = wx.TextCtrl(panel, value=room.get("description", ""))
        s.Add(self.description, 0, wx.EXPAND | wx.LEFT | wx.RIGHT | wx.BOTTOM, 8)
        s.Add(wx.StaticText(panel, label="Visibility:"), 0, wx.LEFT | wx.RIGHT | wx.TOP, 8)
        self.visibility = wx.Choice(panel, choices=["public", "private"]); self.visibility.SetStringSelection(room.get("visibility", "public"))
        s.Add(self.visibility, 0, wx.EXPAND | wx.LEFT | wx.RIGHT | wx.BOTTOM, 8)
        s.Add(wx.StaticText(panel, label="New expiration policy:"), 0, wx.LEFT | wx.RIGHT | wx.TOP, 8)
        self.expiration = wx.Choice(panel, choices=["unchanged", "never", "day", "week", "month", "year", "empty"]); self.expiration.SetSelection(0)
        s.Add(self.expiration, 0, wx.EXPAND | wx.LEFT | wx.RIGHT | wx.BOTTOM, 8)
        s.Add(wx.StaticText(panel, label="Allowed room actions by role. Space toggles a selected permission:"), 0, wx.LEFT | wx.RIGHT | wx.TOP, 8)
        choices = [f"{action.replace('_', ' ')} — {role}" for action in self.ACTIONS for role in self.ROLES]
        self.permission_list = wx.CheckListBox(panel, choices=choices)
        permissions = room.get("permissions", {})
        for index, (action, role) in enumerate((a, r) for a in self.ACTIONS for r in self.ROLES): self.permission_list.Check(index, role in permissions.get(action, []))
        s.Add(self.permission_list, 1, wx.EXPAND | wx.LEFT | wx.RIGHT | wx.BOTTOM, 8)
        s.Add(self.CreateStdDialogButtonSizer(wx.OK | wx.CANCEL), 0, wx.EXPAND | wx.ALL, 8)
        panel.SetSizer(s); outer = wx.BoxSizer(wx.VERTICAL); outer.Add(panel, 1, wx.EXPAND); self.SetSizer(outer)
    def changes(self):
        permissions = {action: [] for action in self.ACTIONS}
        index = 0
        for action in self.ACTIONS:
            for role in self.ROLES:
                if self.permission_list.IsChecked(index): permissions[action].append(role)
                index += 1
        return {"description": self.description.GetValue(), "visibility": self.visibility.GetStringSelection(), "expiration": self.expiration.GetStringSelection(), "permissions": permissions}


class GroupRoomsPanel(wx.Panel):
    def __init__(self, parent, frame, sock, username):
        super().__init__(parent)
        self.frame, self.sock, self.username = frame, sock, username
        self.rooms, self.members, self.current_room = [], [], None
        root = wx.BoxSizer(wx.HORIZONTAL)
        left = wx.BoxSizer(wx.VERTICAL)
        left.Add(wx.StaticText(self, label="Group rooms:"), 0, wx.BOTTOM, 4)
        self.room_list = wx.ListCtrl(self, style=wx.LC_REPORT | wx.LC_SINGLE_SEL)
        self.room_list.InsertColumn(0, "Room", width=180); self.room_list.InsertColumn(1, "Role", width=90); self.room_list.InsertColumn(2, "Members", width=75)
        self.room_list.Bind(wx.EVT_LIST_ITEM_ACTIVATED, self.on_open_room)
        self.room_list.Bind(wx.EVT_LIST_ITEM_SELECTED, self.on_room_selected)
        left.Add(self.room_list, 1, wx.EXPAND | wx.BOTTOM, 6)
        room_buttons = wx.BoxSizer(wx.HORIZONTAL)
        for label, handler in (("&Create", self.on_create), ("&Join", self.on_join), ("&Leave", self.on_leave), ("&Refresh", self.refresh_rooms), ("Room se&ttings", self.on_room_settings)):
            button = wx.Button(self, label=label); button.Bind(wx.EVT_BUTTON, handler); room_buttons.Add(button, 1, wx.RIGHT, 4)
        left.Add(room_buttons, 0, wx.EXPAND)

        center = wx.BoxSizer(wx.VERTICAL)
        self.room_heading = wx.StaticText(self, label="No room selected")
        center.Add(self.room_heading, 0, wx.BOTTOM, 4)
        self.messages = wx.ListBox(self, style=wx.LB_SINGLE)
        self.messages.SetToolTip("Room message history. Use arrow keys to review messages.")
        center.Add(self.messages, 1, wx.EXPAND | wx.BOTTOM, 6)
        center.Add(wx.StaticText(self, label="Message:"), 0, wx.BOTTOM, 3)
        self.message_ctrl = wx.TextCtrl(self, style=wx.TE_PROCESS_ENTER)
        self.message_ctrl.Bind(wx.EVT_TEXT_ENTER, self.on_send_message)
        center.Add(self.message_ctrl, 0, wx.EXPAND | wx.BOTTOM, 5)
        send_row = wx.BoxSizer(wx.HORIZONTAL)
        send_btn = wx.Button(self, label="&Send message"); send_btn.Bind(wx.EVT_BUTTON, self.on_send_message)
        file_btn = wx.Button(self, label="Send &file"); file_btn.Bind(wx.EVT_BUTTON, self.on_send_file)
        call_btn = wx.Button(self, label="Join &voice"); call_btn.Bind(wx.EVT_BUTTON, self.on_join_voice)
        for button in (send_btn, file_btn, call_btn): send_row.Add(button, 1, wx.RIGHT, 5)
        center.Add(send_row, 0, wx.EXPAND)

        right = wx.BoxSizer(wx.VERTICAL)
        right.Add(wx.StaticText(self, label="Room members:"), 0, wx.BOTTOM, 4)
        self.member_list = wx.ListCtrl(self, style=wx.LC_REPORT | wx.LC_SINGLE_SEL)
        self.member_list.InsertColumn(0, "User", width=140); self.member_list.InsertColumn(1, "Role", width=90)
        self.member_list.Bind(wx.EVT_LIST_ITEM_ACTIVATED, self.on_direct_message)
        self.member_list.Bind(wx.EVT_CONTEXT_MENU, self.on_member_menu)
        right.Add(self.member_list, 1, wx.EXPAND)
        invite_btn = wx.Button(self, label="&Invite member"); invite_btn.Bind(wx.EVT_BUTTON, self.on_invite_member); right.Add(invite_btn, 0, wx.EXPAND | wx.TOP, 6)
        right.Add(wx.StaticText(self, label="Activate a member or use the context menu to send a direct message."), 0, wx.TOP, 6)
        root.Add(left, 1, wx.EXPAND | wx.ALL, 8); root.Add(center, 2, wx.EXPAND | wx.ALL, 8); root.Add(right, 1, wx.EXPAND | wx.ALL, 8)
        self.SetSizer(root)

    def _send(self, payload):
        try: self.sock.sendall((json.dumps(payload) + "\n").encode())
        except Exception as exc: wx.MessageBox(str(exc), "Group Rooms", wx.OK | wx.ICON_ERROR, self)

    def refresh_rooms(self, _=None): self._send({"action": "group_room_list"})
    def _selected_room(self):
        index = self.room_list.GetFirstSelected()
        return self.rooms[index] if 0 <= index < len(self.rooms) else None
    def on_room_selected(self, _):
        room = self._selected_room()
        if room and room.get("role"): self._send({"action": "group_room_open", "room_id": room["room_id"]})
    def on_open_room(self, _): self.on_room_selected(None)
    def on_create(self, _):
        with CreateGroupRoomDialog(self) as dlg:
            if dlg.ShowModal() == wx.ID_OK: self._send({"action": "group_room_create", **dlg.values()})
    def on_join(self, _):
        room = self._selected_room()
        if room: self._send({"action": "group_room_join", "room_id": room["room_id"]})
    def on_leave(self, _):
        if self.current_room: self._send({"action": "group_room_leave", "room_id": self.current_room["room_id"]})
    def on_room_settings(self, _):
        if not self.current_room: return
        with GroupRoomSettingsDialog(self, self.current_room) as dlg:
            if dlg.ShowModal() == wx.ID_OK: self._send({"action": "group_room_update", "room_id": self.current_room["room_id"], "changes": dlg.changes()})
    def on_invite_member(self, _):
        if not self.current_room: return
        with wx.TextEntryDialog(self, "Username to add:", "Invite Room Member") as dlg:
            if dlg.ShowModal() != wx.ID_OK: return
            username = dlg.GetValue().strip()
        if username: self._send({"action": "group_room_add_member", "room_id": self.current_room["room_id"], "username": username, "role": "user"})
    def on_send_message(self, _):
        body = self.message_ctrl.GetValue().strip()
        if self.current_room and body:
            self._send({"action": "group_room_message", "room_id": self.current_room["room_id"], "body": body}); self.message_ctrl.Clear(); self.message_ctrl.SetFocus()
    def on_send_file(self, _):
        if not self.current_room: return
        with wx.FileDialog(self, "Send file to room", style=wx.FD_OPEN | wx.FD_FILE_MUST_EXIST) as dlg:
            if dlg.ShowModal() != wx.ID_OK: return
            path = dlg.GetPath()
        try:
            with open(path, "rb") as stream: encoded = base64.b64encode(stream.read()).decode("ascii")
            self._send({"action": "group_room_file", "room_id": self.current_room["room_id"], "room_name": self.current_room["name"], "filename": os.path.basename(path), "data": encoded})
        except Exception as exc: wx.MessageBox(str(exc), "Room File", wx.OK | wx.ICON_ERROR, self)
    def on_join_voice(self, _):
        if not self.current_room: return
        self.frame.on_group_calls(None)
        if self.frame._group_call_dlg:
            self.frame._group_call_dlg.group_txt.SetValue(self.current_room["name"]); self.frame._group_call_dlg.on_join(None)
    def _selected_member(self):
        index = self.member_list.GetFirstSelected(); return self.members[index] if 0 <= index < len(self.members) else None
    def on_direct_message(self, _):
        member = self._selected_member()
        if member: self.frame.open_direct_chat(member["username"])
    def on_member_menu(self, _):
        member = self._selected_member()
        if not member: return
        menu = wx.Menu(); dm = menu.Append(wx.ID_ANY, "Direct message")
        self.Bind(wx.EVT_MENU, self.on_direct_message, dm)
        role_menu = wx.Menu()
        for role in ("guest", "user", "moderator", "admin"):
            item = role_menu.Append(wx.ID_ANY, f"Set role: {role}")
            self.Bind(wx.EVT_MENU, lambda event, value=role, target=member["username"]: self._send({"action": "group_room_set_role", "room_id": self.current_room["room_id"], "username": target, "role": value}), item)
        menu.AppendSubMenu(role_menu, "Change role")
        self.PopupMenu(menu); menu.Destroy()
    def _show_rooms(self, rooms):
        self.rooms = list(rooms or []); self.room_list.DeleteAllItems()
        for room in self.rooms:
            index = self.room_list.InsertItem(self.room_list.GetItemCount(), room.get("name", "")); self.room_list.SetItem(index, 1, room.get("role") or "not joined"); self.room_list.SetItem(index, 2, str(room.get("member_count", 0)))
    def _show_open_room(self, msg):
        self.current_room = msg["room"]; self.members = list(msg.get("members", [])); self.room_heading.SetLabel(f"{self.current_room['name']} — role: {self.current_room.get('role', '')}")
        self.messages.Clear()
        for item in msg.get("messages", []): self._append_message(item)
        self.member_list.DeleteAllItems()
        for member in self.members:
            index = self.member_list.InsertItem(self.member_list.GetItemCount(), member["username"]); self.member_list.SetItem(index, 1, member["role"])
        self.message_ctrl.SetFocus()
    def _append_message(self, item):
        label = f"{item.get('sender', '')}: " + (f"sent file {item.get('filename', '')}" if item.get("kind") == "file" else item.get("body", "")); self.messages.Append(label); self.messages.SetSelection(self.messages.GetCount() - 1)
    def handle_server_action(self, msg):
        action = msg.get("action")
        if action == "group_room_list_response" and msg.get("ok"): self._show_rooms(msg.get("rooms", []))
        elif action == "group_room_open_response" and msg.get("ok"): self._show_open_room(msg)
        elif action == "group_room_message": self._append_message(msg.get("message", {}))
        elif action == "group_room_file":
            item = msg.get("message", {}); self._append_message(item)
            try:
                save_dir = os.path.join(os.path.expanduser("~"), "Documents", "ThriveMessenger", "group-files"); os.makedirs(save_dir, exist_ok=True)
                path = os.path.join(save_dir, os.path.basename(item.get("filename", "room-file")))
                if os.path.exists(path):
                    stem, extension = os.path.splitext(path)
                    counter = 1
                    while os.path.exists(f"{stem}_{counter}{extension}"):
                        counter += 1
                    path = f"{stem}_{counter}{extension}"
                with open(path, "wb") as stream: stream.write(base64.b64decode(msg.get("data", "")))
            except Exception as exc: wx.MessageBox(str(exc), "Room File", wx.OK | wx.ICON_ERROR, self)
        elif action == "group_room_members" and self.current_room and msg.get("room_id") == self.current_room.get("room_id"):
            self._send({"action": "group_room_open", "room_id": self.current_room["room_id"]})
        elif action in ("group_room_result", "group_room_event"):
            if action == "group_room_result" and not msg.get("ok"): wx.MessageBox(msg.get("reason", "Room action failed."), "Group Rooms", wx.OK | wx.ICON_WARNING, self)
            self.refresh_rooms()
            room = msg.get("room")
            if room and room.get("role"): self._send({"action": "group_room_open", "room_id": room["room_id"]})


class GroupCallDialog(wx.Dialog):
    def __init__(self, parent, sock, username):
        super().__init__(parent, title="Group Voice", size=(820, 540))
        self.parent_frame = parent
        self.sock = sock
        self.username = username
        self.calls = []
        self.current_group = ""
        self.audio_active = False
        self.audio_stop = threading.Event()
        self.capture_queue = queue.Queue(maxsize=32)
        self.playback_queue = queue.Queue(maxsize=64)
        self.input_stream = None
        self.output_stream = None
        self.direct_call_id = None
        self._close_sound_played = False
        self.muted = False
        self.deafened = False
        self.Bind(wx.EVT_CLOSE, self.on_close)
        panel = wx.Panel(self)
        s = wx.BoxSizer(wx.VERTICAL)
        preview_notice = wx.StaticText(
            panel,
            label="Live voice is relayed securely through this Thrive server. Headphones are recommended to prevent echo.",
        )
        preview_notice.Wrap(680)
        s.Add(preview_notice, 0, wx.EXPAND | wx.ALL, 8)

        top = wx.BoxSizer(wx.HORIZONTAL)
        top.Add(wx.StaticText(panel, label="Group:"), 0, wx.ALIGN_CENTER_VERTICAL | wx.RIGHT, 6)
        self.group_txt = wx.TextCtrl(panel)
        top.Add(self.group_txt, 1, wx.EXPAND | wx.RIGHT, 8)
        top.Add(wx.StaticText(panel, label="Mode:"), 0, wx.ALIGN_CENTER_VERTICAL | wx.RIGHT, 6)
        self.mode_choice = wx.Choice(panel, choices=["voice"])
        self.mode_choice.SetSelection(0)
        top.Add(self.mode_choice, 0)

        btn_row = wx.BoxSizer(wx.HORIZONTAL)
        self.btn_join = wx.Button(panel, label="Join")
        self.btn_leave = wx.Button(panel, label="Leave")
        self.btn_refresh = wx.Button(panel, label="Refresh")
        self.btn_ping = wx.Button(panel, label="Send Test Signal")
        # On/off controls are checkboxes, so screen readers say "checked" / "not checked" (switches on macOS).
        self.btn_mute = wx.CheckBox(panel, label="&Mute microphone")
        self.btn_deafen = wx.CheckBox(panel, label="&Deafen speakers")
        for b in [self.btn_join, self.btn_leave, self.btn_refresh, self.btn_ping, self.btn_mute, self.btn_deafen]:
            btn_row.Add(b, 1, wx.EXPAND | wx.ALL, 3)
        self.btn_join.Bind(wx.EVT_BUTTON, self.on_join)
        self.btn_leave.Bind(wx.EVT_BUTTON, self.on_leave)
        self.btn_refresh.Bind(wx.EVT_BUTTON, self.on_refresh)
        self.btn_ping.Bind(wx.EVT_BUTTON, self.on_ping)
        self.btn_mute.Bind(wx.EVT_CHECKBOX, self.on_toggle_mute)
        self.btn_deafen.Bind(wx.EVT_CHECKBOX, self.on_toggle_deafen)
        apply_toggle_semantics(self)

        self.calls_list = wx.ListBox(panel, style=wx.LB_SINGLE)
        self.calls_list.Bind(wx.EVT_LISTBOX, self.on_select_call)
        self.log = wx.ListBox(panel, style=wx.LB_SINGLE)

        s.Add(top, 0, wx.EXPAND | wx.ALL, 8)
        s.Add(btn_row, 0, wx.EXPAND | wx.LEFT | wx.RIGHT | wx.BOTTOM, 8)
        s.Add(wx.StaticText(panel, label="Active Group Calls"), 0, wx.LEFT | wx.RIGHT | wx.BOTTOM, 4)
        s.Add(self.calls_list, 0, wx.EXPAND | wx.LEFT | wx.RIGHT | wx.BOTTOM, 8)
        s.Add(wx.StaticText(panel, label="Call Events"), 0, wx.LEFT | wx.RIGHT | wx.BOTTOM, 4)
        s.Add(self.log, 1, wx.EXPAND | wx.LEFT | wx.RIGHT | wx.BOTTOM, 8)
        panel.SetSizer(s)

    def on_close(self, event):
        self.stop_audio()
        group = self.current_group or self.group_txt.GetValue().strip()
        if not self._close_sound_played:
            wx.GetApp().play_sound("call_ended.wav" if self.direct_call_id else "group_call_leave.wav")
            self._close_sound_played = True
        if self.direct_call_id:
            try: self.sock.sendall((json.dumps({"action": "voice_call_end", "call_id": self.direct_call_id}) + "\n").encode())
            except Exception: pass
        elif group:
            try:
                self.sock.sendall((json.dumps({"action": "group_call_leave", "group": group}) + "\n").encode())
            except Exception:
                pass
        if self.parent_frame:
            self.parent_frame._group_call_dlg = None
        event.Skip()

    def _append_log(self, text):
        self.log.Append(f"[{format_timestamp(time.time())}] {text}")
        self.log.SetSelection(self.log.GetCount() - 1)

    def set_calls(self, calls):
        self.calls = list(calls or [])
        self.calls_list.Clear()
        for c in self.calls:
            group = c.get("group", "")
            mode = c.get("mode", "voice")
            count = c.get("count", 0)
            self.calls_list.Append(f"{group} | {mode} | participants: {count}")
        if self.calls_list.GetCount() == 0:
            self.calls_list.Append("(No active group calls)")

    def on_select_call(self, _):
        idx = self.calls_list.GetSelection()
        if idx == wx.NOT_FOUND or idx < 0 or idx >= len(self.calls):
            return
        call = self.calls[idx]
        self.current_group = str(call.get("group", "") or "")
        self.group_txt.SetValue(self.current_group)
        mode = str(call.get("mode", "voice"))
        self.mode_choice.SetStringSelection("voice")

    def on_refresh(self, _):
        try:
            self.sock.sendall((json.dumps({"action": "group_call_list"}) + "\n").encode())
        except Exception as e:
            self._append_log(f"Refresh failed: {e}")

    def on_join(self, _):
        group = self.group_txt.GetValue().strip()
        if not group:
            wx.MessageBox("Enter a group name first.", "Group Calls", wx.OK | wx.ICON_INFORMATION, self)
            return
        self.current_group = group
        mode = self.mode_choice.GetStringSelection() or "voice"
        try:
            self.sock.sendall((json.dumps({"action": "group_call_join", "group": group, "mode": mode}) + "\n").encode())
        except Exception as e:
            self._append_log(f"Join failed: {e}")

    def on_leave(self, _):
        if self.direct_call_id:
            try: self.sock.sendall((json.dumps({"action": "voice_call_end", "call_id": self.direct_call_id}) + "\n").encode())
            except Exception as exc: self._append_log(f"Leave failed: {exc}")
            wx.GetApp().play_sound("call_ended.wav"); self._close_sound_played = True
            self.stop_audio(); self.Close(); return
        group = self.group_txt.GetValue().strip() or self.current_group
        if not group:
            return
        try:
            self.sock.sendall((json.dumps({"action": "group_call_leave", "group": group}) + "\n").encode())
            self.stop_audio()
        except Exception as e:
            self._append_log(f"Leave failed: {e}")

    def configure_direct_call(self, call_id, other_user):
        self.direct_call_id = call_id
        self.current_group = f"direct:{call_id}"
        self.SetTitle(f"Voice Call with {other_user}")
        self.group_txt.SetValue(f"Direct call with {other_user}"); self.group_txt.Disable(); self.mode_choice.Disable()
        self.btn_join.Hide(); self.btn_refresh.Hide(); self.btn_ping.Hide(); self.Layout()
        self._append_log(f"Connected with {other_user}.")

    def on_ping(self, _):
        group = self.group_txt.GetValue().strip() or self.current_group
        if not group:
            wx.MessageBox("Join/select a group call first.", "Group Calls", wx.OK | wx.ICON_INFORMATION, self)
            return
        target = ""
        for c in self.calls:
            if str(c.get("group", "")) == group:
                participants = [p for p in c.get("participants", []) if p != self.username]
                if participants:
                    target = participants[0]
                break
        if not target:
            self._append_log("No other participant available for test signal.")
            return
        payload = {
            "action": "group_call_signal",
            "group": group,
            "to": target,
            "signal_type": "test",
            "data": {"message": "ping"},
        }
        try:
            self.sock.sendall((json.dumps(payload) + "\n").encode())
        except Exception as e:
            self._append_log(f"Signal failed: {e}")

    def on_toggle_mute(self, _):
        self.muted = bool(self.btn_mute.GetValue())
        self._append_log("Microphone muted." if self.muted else "Microphone unmuted.")

    def on_toggle_deafen(self, _):
        self.deafened = bool(self.btn_deafen.GetValue())
        self._append_log("Speakers deafened." if self.deafened else "Speakers enabled.")

    def handle_call_event(self, msg):
        group = msg.get("group", "")
        event = msg.get("event", "")
        by = msg.get("by", "")
        participants = msg.get("participants", [])
        self._append_log(f"{group}: {by} {event} ({len(participants)} participants)")
        self.on_refresh(None)

    def handle_call_result(self, msg):
        if msg.get("ok"):
            self._append_log(f"Call action OK for group {msg.get('group', '')}.")
            if msg.get("event") == "joined" and msg.get("mode", "voice") == "voice":
                wx.GetApp().play_sound("group_call_join.wav")
                self.start_audio()
            elif msg.get("event") == "left":
                wx.GetApp().play_sound("group_call_leave.wav"); self._close_sound_played = True
                self.stop_audio()
            self.on_refresh(None)
        else:
            self._append_log(f"Call action failed: {msg.get('reason', 'unknown error')}")

    def handle_call_signal(self, msg):
        self._append_log(f"Signal from {msg.get('from', '')} in {msg.get('group', '')}: {msg.get('signal_type', '')}")

    def handle_signal_result(self, msg):
        if msg.get("ok"):
            self._append_log(f"Signal sent to {msg.get('to', '')}.")
        else:
            self._append_log(f"Signal failed: {msg.get('reason', 'unknown error')}")

    def start_audio(self):
        if self.audio_active:
            return
        if sounddevice is None:
            self._append_log("Live voice is unavailable because the audio module could not load.")
            return
        self.audio_stop.clear()
        self.audio_active = True
        input_gain = max(0.0, min(float(wx.GetApp().user_config.get("call_input_volume", 80)) / 100.0, 1.0))
        output_gain = max(0.0, min(float(wx.GetApp().user_config.get("call_output_volume", 80)) / 100.0, 1.0))
        def input_callback(indata, frames, callback_time, status):
            if self.muted:
                return
            data = bytes(indata)
            data = scale_pcm16(data, input_gain)
            try: self.capture_queue.put_nowait(data)
            except queue.Full: pass
        def output_callback(outdata, frames, callback_time, status):
            if self.deafened:
                outdata[:] = b"\0" * len(outdata)
                return
            try: data = self.playback_queue.get_nowait()
            except queue.Empty: data = b""
            expected = len(outdata)
            data = data[:expected].ljust(expected, b"\0")
            data = scale_pcm16(data, output_gain)
            outdata[:] = data
        try:
            input_device = wx.GetApp().user_config.get("call_input_device")
            output_device = wx.GetApp().user_config.get("call_output_device")
            self.input_stream = sounddevice.RawInputStream(device=input_device, samplerate=16000, blocksize=320, channels=1, dtype="int16", callback=input_callback)
            self.output_stream = sounddevice.RawOutputStream(device=output_device, samplerate=16000, blocksize=320, channels=1, dtype="int16", callback=output_callback)
            self.input_stream.start(); self.output_stream.start()
            threading.Thread(target=self._audio_sender, daemon=True).start()
            self._append_log("Microphone and speaker audio started.")
        except Exception as exc:
            self.audio_active = False
            self._append_log(f"Audio device could not start: {exc}")

    def _audio_sender(self):
        while not self.audio_stop.is_set():
            try: data = self.capture_queue.get(timeout=0.2)
            except queue.Empty: continue
            try:
                self.sock.sendall((json.dumps({"action": "group_call_audio", "group": self.current_group, "data": base64.b64encode(data).decode("ascii")}) + "\n").encode())
            except Exception:
                break

    def handle_audio(self, msg):
        if not self.audio_active or msg.get("group") != self.current_group:
            return
        try:
            data = base64.b64decode(msg.get("data", ""), validate=True)
            self.playback_queue.put_nowait(data)
        except (ValueError, queue.Full):
            pass

    def stop_audio(self):
        self.audio_stop.set(); self.audio_active = False
        for stream in (self.input_stream, self.output_stream):
            if stream:
                try: stream.stop(); stream.close()
                except Exception: pass
        self.input_stream = self.output_stream = None

def show_in_folder(path):
    try:
        if sys.platform == 'win32':
            subprocess.Popen(['explorer', '/select,', os.path.normpath(path)])
        elif sys.platform == 'darwin':
            subprocess.Popen(['open', '-R', path])
        else:
            open_path_or_url(os.path.dirname(path))
    except Exception as e:
        print(f"Could not show folder: {e}")

CALL_SOUND_EVENTS = {"incoming_call.wav", "outgoing_call.wav", "call_connected.wav", "call_ended.wav", "call_busy.wav",
                     "call_missed.wav", "voicemail_left.wav", "voicemail_new.wav"}

def format_seconds(seconds):
    seconds = int(round(float(seconds or 0)))
    return f"{seconds // 60}:{seconds % 60:02d}"

_EMOJI_FAVORITES = "👍 😀 😂 🤣 😊 😍 ❤️ 🙏 🎉 🔥 👏 👋 😢 😮 🤔 ✅ 😎 💯 🙌 😘 😁 🥰 😅 😉 👀 🎶 ☕ 🌟".split()
_EMOJI_RANGES = [(0x1F600, 0x1F64F), (0x1F300, 0x1F5FF), (0x1F680, 0x1F6FF), (0x1F900, 0x1F9FF),
                 (0x1FA70, 0x1FAFF), (0x2600, 0x26FF), (0x2700, 0x27BF)]
_emoji_cache = None

def emoji_catalog():
    """[(emoji, name)] with favourites first. Names come from Unicode, so screen readers and search agree."""
    global _emoji_cache
    if _emoji_cache is not None:
        return _emoji_cache
    seen, out = set(), []
    def add(ch):
        if ch in seen:
            return
        base = ch.replace("️", "")
        try:
            name = unicodedata.name(base).lower()
        except (ValueError, TypeError):
            return
        seen.add(ch); out.append((ch, name))
    for ch in _EMOJI_FAVORITES:
        add(ch)
    for lo, hi in _EMOJI_RANGES:
        for cp in range(lo, hi + 1):
            if 0x1F3FB <= cp <= 0x1F3FF:
                continue  # skin-tone modifiers on their own
            add(chr(cp))
    _emoji_cache = out
    return out

class EmojiPickerDialog(wx.Dialog):
    """Searchable emoji list. Type to filter by name, arrow to choose, Enter inserts, Escape cancels."""
    def __init__(self, parent):
        super().__init__(parent, title="Insert Emoji", size=(420, 480), style=wx.DEFAULT_DIALOG_STYLE | wx.RESIZE_BORDER)
        self.selected = None
        s = wx.BoxSizer(wx.VERTICAL)
        s.Add(wx.StaticText(self, label="&Search emoji by name:"), 0, wx.LEFT | wx.RIGHT | wx.TOP, 8)
        self.search = wx.TextCtrl(self, style=wx.TE_PROCESS_ENTER, name="Search emoji by name")
        s.Add(self.search, 0, wx.EXPAND | wx.ALL, 8)
        s.Add(wx.StaticText(self, label="&Emoji:"), 0, wx.LEFT | wx.RIGHT, 8)
        self.list = wx.ListBox(self, style=wx.LB_SINGLE, name="Emoji")
        s.Add(self.list, 1, wx.EXPAND | wx.ALL, 8)
        btns = self.CreateStdDialogButtonSizer(wx.OK | wx.CANCEL)
        self.FindWindowById(wx.ID_OK).SetLabel("&Insert")
        s.Add(btns, 0, wx.EXPAND | wx.ALL, 8)
        self.SetSizer(s)
        self.items = []
        self.search.Bind(wx.EVT_TEXT, lambda e: self.refresh())
        self.search.Bind(wx.EVT_TEXT_ENTER, self.on_ok)
        self.search.Bind(wx.EVT_KEY_DOWN, self.on_search_key)
        self.list.Bind(wx.EVT_LISTBOX_DCLICK, self.on_ok)
        self.Bind(wx.EVT_BUTTON, self.on_ok, id=wx.ID_OK)
        self.refresh()
        self.search.SetFocus()
    def refresh(self):
        terms = self.search.GetValue().strip().lower().split()
        self.items = [(e, n) for e, n in emoji_catalog() if all(t in n for t in terms)][:400]
        self.list.Set([f"{e}  {n}" for e, n in self.items] or ["No emoji match"])
        if self.items:
            self.list.SetSelection(0)
    def on_search_key(self, event):
        if event.GetKeyCode() in (wx.WXK_DOWN, wx.WXK_UP) and self.items:
            self.list.SetFocus()
            return
        event.Skip()
    def on_ok(self, _):
        idx = self.list.GetSelection()
        if 0 <= idx < len(self.items):
            self.selected = self.items[idx][0]
            self.EndModal(wx.ID_OK)

class _MciAudio(object):
    """Windows MCI playback (winmm): plays MP3/WAV with pause and seek, no window or media framework needed."""
    _counter = 0
    def __init__(self):
        import ctypes
        self._send = ctypes.windll.winmm.mciSendStringW
        self._buf = ctypes.create_unicode_buffer(256)
        _MciAudio._counter += 1
        self.alias = f"thrivevoice{_MciAudio._counter}"
        self.open = False
    def cmd(self, command):
        err = self._send(command, self._buf, 255, 0)
        return err, self._buf.value
    def load(self, path):
        self.close()
        err, _ = self.cmd(f'open "{path}" type mpegvideo alias {self.alias}')
        if err:
            err, _ = self.cmd(f'open "{path}" alias {self.alias}')
        if err:
            return False
        self.open = True
        self.cmd(f"set {self.alias} time format milliseconds")
        return True
    def length(self):
        err, val = self.cmd(f"status {self.alias} length")
        return int(val) if not err and val.isdigit() else 0
    def position(self):
        err, val = self.cmd(f"status {self.alias} position")
        return int(val) if not err and val.isdigit() else 0
    def mode(self):
        err, val = self.cmd(f"status {self.alias} mode")
        return val if not err else "stopped"
    def play(self):
        return self.cmd(f"play {self.alias}")[0] == 0
    def pause(self):
        self.cmd(f"pause {self.alias}")
    def resume(self):
        self.cmd(f"resume {self.alias}")
    def seek(self, ms, playing):
        self.cmd(f"seek {self.alias} to {int(ms)}")
        if playing:
            self.cmd(f"play {self.alias}")
    def stop(self):
        self.cmd(f"stop {self.alias}")
    def close(self):
        if self.open:
            self.cmd(f"close {self.alias}")
            self.open = False

class _NSSoundAudio(object):
    """macOS playback through AppKit NSSound: MP3/WAV with pause, resume and seek."""
    def __init__(self):
        from AppKit import NSSound  # noqa: F401 (raises if AppKit is missing)
        self.sound = None
        self.open = False
        self._paused = False
    def load(self, path):
        from AppKit import NSSound
        self.close()
        self.sound = NSSound.alloc().initWithContentsOfFile_byReference_(path, True)
        self.open = self.sound is not None
        return self.open
    def length(self):
        return int(self.sound.duration() * 1000) if self.sound else 0
    def position(self):
        return int(self.sound.currentTime() * 1000) if self.sound else 0
    def mode(self):
        if not self.sound:
            return "stopped"
        if self._paused:
            return "paused"
        return "playing" if self.sound.isPlaying() else "stopped"
    def play(self):
        self._paused = False
        return bool(self.sound and self.sound.play())
    def pause(self):
        if self.sound and self.sound.pause():
            self._paused = True
    def resume(self):
        if self.sound and self.sound.resume():
            self._paused = False
    def seek(self, ms, playing):
        if self.sound:
            self.sound.setCurrentTime_(max(0.0, ms / 1000.0))
    def stop(self):
        if self.sound:
            self.sound.stop()
        self._paused = False
    def close(self):
        self.stop()
        self.sound = None
        self.open = False

class VoicePlayer(object):
    """Plays one voice message at a time inside a chat, without dialogs or focus changes.
    Windows uses MCI (reliable for MP3); elsewhere wx.media."""
    SKIP_MS = 5000
    def __init__(self, host):
        self.host = host
        self.ctrl = None
        self.mci = None
        self.path = None
        self.label = ""
        self.state = "stopped"
        self._timer = None
    def _ensure(self):
        if sys.platform in ('win32', 'darwin'):
            if self.mci is None:
                try:
                    self.mci = _MciAudio() if sys.platform == 'win32' else _NSSoundAudio()
                except Exception as e:
                    print(f"Native audio player unavailable: {e}")
            if self.mci is not None:
                return self.mci
        if self.ctrl is None and wxmedia is not None:
            try:
                self.ctrl = wxmedia.MediaCtrl(self.host, size=(1, 1))
                self.ctrl.Hide()
                self.ctrl.Bind(wxmedia.EVT_MEDIA_LOADED, self._on_loaded)
                self.ctrl.Bind(wxmedia.EVT_MEDIA_FINISHED, lambda e: self._finished())
            except Exception as e:
                print(f"Voice player unavailable: {e}")
                self.ctrl = None
        return self.ctrl
    def toggle(self, path, label):
        if self.path == path and self.state in ("playing", "paused", "loading"):
            self.stop()
            return
        self.play(path, label)
    def play(self, path, label):
        if not path or not os.path.isfile(path):
            speak_text("This voice message isn't on this device any more.", interrupt=True)
            return
        engine = self._ensure()
        if self.state != "stopped":
            self.stop(announce=False)
        self.path, self.label = path, label
        if engine is None:
            open_path_or_url(path)  # no audio engine: fall back to the system player
            return
        if engine is self.mci:
            if not self.mci.load(path) or not self.mci.play():
                speak_text("Couldn't play this voice message.", interrupt=True)
                return
            self.state = "playing"
            speak_text(f"Playing {label}", interrupt=True)
            self._start_watch()
            return
        self.state = "loading"
        if not self.ctrl.Load(path):
            self.state = "stopped"
            speak_text("Couldn't play this voice message.", interrupt=True)
    def _start_watch(self):
        if self._timer is None:
            self._timer = wx.Timer()
            self._timer.Bind(wx.EVT_TIMER, self._on_watch)
        self._timer.Start(300)
    def _on_watch(self, _):
        if self.mci and self.state == "playing" and self.mci.mode() == "stopped":
            self._finished()
    def _on_loaded(self, _):
        if self.state == "loading" and self.ctrl:
            self.ctrl.Play()
            self.state = "playing"
            speak_text(f"Playing {self.label}", interrupt=True)
    def _finished(self):
        if self._timer:
            self._timer.Stop()
        if self.state != "stopped":
            self.state = "stopped"
            if self.mci:
                self.mci.close()
            speak_text("Finished", interrupt=False)
    def pause_resume(self):
        if self.state not in ("playing", "paused"):
            return False
        if self.mci and self.mci.open:
            if self.state == "playing":
                self.mci.pause(); self.state = "paused"; speak_text("Paused", interrupt=True)
            else:
                self.mci.resume(); self.state = "playing"; speak_text("Playing", interrupt=True)
            return True
        if not self.ctrl:
            return False
        if self.state == "playing":
            self.ctrl.Pause(); self.state = "paused"; speak_text("Paused", interrupt=True)
        else:
            self.ctrl.Play(); self.state = "playing"; speak_text("Playing", interrupt=True)
        return True
    def stop(self, announce=True):
        if self._timer:
            self._timer.Stop()
        was = self.state
        self.state = "stopped"
        if self.mci and self.mci.open:
            self.mci.stop()
            self.mci.close()
        elif self.ctrl:
            self.ctrl.Stop()
        if announce and was != "stopped":
            speak_text("Stopped", interrupt=True)
    def seek(self, delta_ms):
        if self.state not in ("playing", "paused"):
            return False
        if self.mci and self.mci.open:
            length = self.mci.length()
            pos = max(0, min(self.mci.position() + delta_ms, max(0, length - 150)))
            self.mci.seek(pos, playing=(self.state == "playing"))
        elif self.ctrl:
            pos = max(0, min(self.ctrl.Tell() + delta_ms, max(0, self.ctrl.Length() - 100)))
            self.ctrl.Seek(pos)
        else:
            return False
        speak_text(format_seconds(pos / 1000.0), interrupt=True)
        return True

class VoiceRecorder(object):
    """Records the default microphone to 16 kHz mono WAV in memory (the server turns it into a small MP3)."""
    RATE = 16000
    MAX_SECONDS = 180
    def __init__(self):
        self.stream = None
        self.chunks = []
        self.started = 0.0
    @staticmethod
    def available():
        return sounddevice is not None
    def start(self):
        self.chunks = []
        device = wx.GetApp().user_config.get('call_input_device')
        self.stream = sounddevice.RawInputStream(samplerate=self.RATE, channels=1, dtype='int16',
                                                 device=device if device not in (None, "") else None,
                                                 callback=lambda data, frames, t, status: self.chunks.append(bytes(data)))
        self.stream.start()
        self.started = time.time()
    def elapsed(self):
        return time.time() - self.started if self.stream else 0.0
    def stop(self):
        stream, self.stream = self.stream, None
        if stream:
            try:
                stream.stop(); stream.close()
            except Exception:
                pass
        pcm = b"".join(self.chunks)
        buf = io.BytesIO()
        with wave.open(buf, "wb") as w:
            w.setnchannels(1); w.setsampwidth(2); w.setframerate(self.RATE)
            w.writeframes(pcm)
        return buf.getvalue(), len(pcm) / 2.0 / self.RATE

class VoiceRecordedDialog(wx.Dialog):
    """After recording: Send, Play back, or Discard, all from the keyboard."""
    def __init__(self, parent, wav_path, seconds, voicemail=False):
        kind = "Voicemail" if voicemail else "Voice message"
        super().__init__(parent, title=f"{kind} recorded")
        self.player = VoicePlayer(self)
        self.wav_path = wav_path
        s = wx.BoxSizer(wx.VERTICAL)
        s.Add(wx.StaticText(self, label=f"{kind} recorded, {format_seconds(seconds)} long. Send it, play it back, or discard it."), 0, wx.ALL, 10)
        row = wx.BoxSizer(wx.HORIZONTAL)
        send = wx.Button(self, wx.ID_OK, label="&Send")
        play = wx.Button(self, label="&Play Back")
        discard = wx.Button(self, wx.ID_CANCEL, label="&Discard")
        send.SetDefault()
        play.Bind(wx.EVT_BUTTON, lambda e: self.player.toggle(self.wav_path, "your recording"))
        for b in (send, play, discard):
            row.Add(b, 0, wx.ALL, 5)
        s.Add(row, 0, wx.ALIGN_CENTER | wx.BOTTOM, 6)
        self.SetSizerAndFit(s)
        self.SetEscapeId(wx.ID_CANCEL)
        send.SetFocus()

class ChatArchivePanel(wx.Panel):
    """Chat Archive tab: saved days grouped by year and month; opening a day shows it as read-only text."""
    def __init__(self, parent, chat):
        super().__init__(parent)
        self.chat = chat
        self.SetName("Chat Archive")
        s = wx.BoxSizer(wx.VERTICAL)
        row = wx.BoxSizer(wx.HORIZONTAL)
        row.Add(wx.StaticText(self, label="&Sort days:"), 0, wx.ALIGN_CENTER_VERTICAL | wx.RIGHT, 6)
        self.sort_choice = wx.Choice(self, choices=["Newest first", "Oldest first"], name="Sort days")
        self.sort_choice.SetSelection(0)
        self.sort_choice.Bind(wx.EVT_CHOICE, lambda e: self.refresh())
        row.Add(self.sort_choice, 0)
        s.Add(row, 0, wx.ALL, 6)
        s.Add(wx.StaticText(self, label="Saved &days (year, month, day). Press Enter to read a day:"), 0, wx.LEFT | wx.RIGHT, 6)
        self.tree = wx.TreeCtrl(self, style=wx.TR_DEFAULT_STYLE | wx.TR_HIDE_ROOT | wx.TR_SINGLE, name="Saved days")
        self.tree.Bind(wx.EVT_TREE_SEL_CHANGED, self.on_select)
        self.tree.Bind(wx.EVT_TREE_ITEM_ACTIVATED, self.on_activate)
        s.Add(self.tree, 1, wx.EXPAND | wx.ALL, 6)
        s.Add(wx.StaticText(self, label="&Messages for the selected day (read only):"), 0, wx.LEFT | wx.RIGHT, 6)
        self.view = wx.TextCtrl(self, style=wx.TE_MULTILINE | wx.TE_READONLY | wx.TE_RICH2, name="Messages for the selected day")
        self.view.Bind(wx.EVT_KEY_DOWN, self.on_view_key)
        s.Add(self.view, 1, wx.EXPAND | wx.ALL, 6)
        self.SetSizer(s)
    def focus_default(self):
        self.tree.SetFocus()
    def _days(self):
        log_dir = self.chat._contact_log_dir()
        out = []
        if os.path.isdir(log_dir):
            for name in os.listdir(log_dir):
                base, ext = os.path.splitext(name)
                if ext.lower() != ".txt":
                    continue
                try:
                    day = datetime.date.fromisoformat(base)
                except Exception:
                    continue
                path = os.path.join(log_dir, name)
                try:
                    with open(path, encoding="utf-8", errors="replace") as fh:
                        count = sum(1 for line in fh if line.strip())
                except Exception:
                    count = 0
                out.append((day, path, count))
        out.sort(key=lambda t: t[0], reverse=(self.sort_choice.GetSelection() == 0))
        return out
    def refresh(self):
        self.tree.DeleteAllItems()
        root = self.tree.AddRoot("Chat Archive")
        days = self._days()
        if not days:
            self.tree.AppendItem(root, "No saved messages yet")
            self.view.SetValue("Nothing is saved for this conversation yet. Use Save to Chat Archive on a message, "
                               "or turn on chat history saving for this contact, and saved days will appear here.")
            return
        years, months = {}, {}
        first_day = None
        for day, path, count in days:
            y = years.get(day.year)
            if y is None:
                y = years[day.year] = self.tree.AppendItem(root, str(day.year))
            key = (day.year, day.month)
            m = months.get(key)
            if m is None:
                m = months[key] = self.tree.AppendItem(y, day.strftime("%B %Y"))
            label = f"{day.strftime('%A')}, {day.strftime('%B')} {get_day_with_suffix(day.day)} ({count} message{'s' if count != 1 else ''})"
            item = self.tree.AppendItem(m, label)
            self.tree.SetItemData(item, path)
            if first_day is None:
                first_day = item
        if first_day is not None:
            self.tree.EnsureVisible(first_day)
            self.tree.SelectItem(first_day)
    def _path_for(self, item):
        if not item or not item.IsOk():
            return None
        return self.tree.GetItemData(item)
    def _load(self, path):
        try:
            with open(path, encoding="utf-8", errors="replace") as fh:
                self.view.SetValue(fh.read())
            self.view.SetInsertionPoint(0)
        except Exception as e:
            self.view.SetValue(f"Could not open this day: {e}")
    def on_select(self, event):
        path = self._path_for(event.GetItem())
        if path:
            self._load(path)
        event.Skip()
    def on_activate(self, event):
        item = event.GetItem()
        path = self._path_for(item)
        if path:
            self._load(path)
            self.view.SetFocus()
        elif self.tree.ItemHasChildren(item):
            self.tree.Toggle(item)
    def on_view_key(self, event):
        if event.GetKeyCode() == wx.WXK_ESCAPE:
            self.tree.SetFocus()
            return
        event.Skip()

class ContactTransfersPanel(wx.Panel):
    """File Transfers tab: every file (and voice message) sent to or received from this contact."""
    FILTERS = ("All files", "Voice messages", "Voicemail")
    def __init__(self, parent, chat):
        super().__init__(parent)
        self.chat = chat
        self.rows = []
        self.SetName("File Transfers")
        s = wx.BoxSizer(wx.VERTICAL)
        row = wx.BoxSizer(wx.HORIZONTAL)
        row.Add(wx.StaticText(self, label="S&how:"), 0, wx.ALIGN_CENTER_VERTICAL | wx.RIGHT, 6)
        self.filter_choice = wx.Choice(self, choices=list(self.FILTERS), name="Show")
        self.filter_choice.SetSelection(0)
        self.filter_choice.Bind(wx.EVT_CHOICE, lambda e: self.refresh())
        row.Add(self.filter_choice, 0)
        s.Add(row, 0, wx.ALL, 6)
        self.lv = wx.ListCtrl(self, style=wx.LC_REPORT | wx.LC_SINGLE_SEL, name="Files with this contact")
        for i, (title, width) in enumerate((("Name", 200), ("Size", 80), ("Date", 190), ("Direction", 80), ("Status", 170))):
            self.lv.InsertColumn(i, title, width=width)
        self.lv.Bind(wx.EVT_LIST_ITEM_ACTIVATED, lambda e: self.on_open(None))
        self.lv.Bind(wx.EVT_LIST_ITEM_SELECTED, lambda e: self._update_buttons())
        s.Add(self.lv, 1, wx.EXPAND | wx.ALL, 6)
        btns = wx.BoxSizer(wx.HORIZONTAL)
        self.btn_open = wx.Button(self, label="&Open")
        self.btn_folder = wx.Button(self, label="Show in F&older")
        self.btn_again = wx.Button(self, label="&Get Again")
        self.btn_open.Bind(wx.EVT_BUTTON, self.on_open)
        self.btn_folder.Bind(wx.EVT_BUTTON, self.on_folder)
        self.btn_again.Bind(wx.EVT_BUTTON, self.on_get_again)
        for b in (self.btn_open, self.btn_folder, self.btn_again):
            btns.Add(b, 0, wx.RIGHT, 6)
        s.Add(btns, 0, wx.ALL, 6)
        self.SetSizer(s)
    def focus_default(self):
        self.lv.SetFocus()
        if self.lv.GetItemCount() and self.lv.GetFirstSelected() == -1:
            self.lv.Select(0); self.lv.Focus(0)
    def _entries(self):
        app = wx.GetApp()
        want = str(self.chat.contact or "").lower()
        mode = self.filter_choice.GetSelection()
        out = []
        for e in reversed(getattr(app, "transfer_history", []) or []):
            if str(e.get("user", "")).lower() != want:
                continue
            kind = e.get("kind", "file")
            if mode == 1 and kind not in ("voice", "voicemail"):
                continue
            if mode == 2 and kind != "voicemail":
                continue
            out.append(e)
        return out
    @staticmethod
    def status_text(e):
        path = e.get("path") or ""
        here = bool(path) and os.path.isfile(path)
        status = str(e.get("status") or "")
        if status == "unavailable":
            return "No longer available"
        if status == "requested":
            return "Asked for it again"
        if here:
            return "On this device"
        return "Not on this device"
    def refresh(self):
        sel = self.lv.GetFirstSelected()
        self.lv.DeleteAllItems()
        self.rows = self._entries()
        for e in self.rows:
            idx = self.lv.InsertItem(self.lv.GetItemCount(), str(e.get("filename", "")))
            size = e.get("size")
            if not size and e.get("path") and os.path.isfile(e.get("path")):
                size = os.path.getsize(e.get("path"))
            self.lv.SetItem(idx, 1, format_size(size) if size else "")
            self.lv.SetItem(idx, 2, format_timestamp(e.get("time")))
            self.lv.SetItem(idx, 3, "Sent" if e.get("direction") == "sent" else "Received")
            self.lv.SetItem(idx, 4, self.status_text(e))
        if not self.rows:
            self.lv.InsertItem(0, "No files with this contact yet")
        elif sel != -1 and sel < self.lv.GetItemCount():
            self.lv.Select(sel); self.lv.Focus(sel)
        self._update_buttons()
    def _selected(self):
        i = self.lv.GetFirstSelected()
        return self.rows[i] if 0 <= i < len(self.rows) else None
    def _update_buttons(self):
        e = self._selected()
        here = bool(e and e.get("path") and os.path.isfile(e.get("path")))
        self.btn_open.Enable(bool(e))
        self.btn_folder.Enable(here)
        self.btn_again.Enable(bool(e) and not here)
    def on_open(self, _):
        e = self._selected()
        if not e:
            return
        path = e.get("path") or ""
        if path and os.path.isfile(path):
            open_path_or_url(path)
            return
        res = wx.MessageBox(f"{e.get('filename')} isn't on this device any more. Ask {self.chat.display_name()} for it again?",
                            "Get Again", wx.YES_NO | wx.ICON_QUESTION, self)
        if res == wx.YES:
            self.on_get_again(None)
        else:
            self.lv.SetFocus()
    def on_folder(self, _):
        e = self._selected()
        if e and e.get("path") and os.path.isfile(e.get("path")):
            show_in_folder(e["path"])
    def on_get_again(self, _):
        e = self._selected()
        if not e:
            return
        wx.GetApp().request_file_again(self.chat.contact, e)
        self.refresh()
        self.lv.SetFocus()

class ChatPanel(wx.Panel):
    """One conversation. Lives in a ChatWindow: as a tab (tabbed mode) or as the only content (classic mode)."""
    def __init__(self, frame, contact, sock, user, logging_enabled=False, is_contact=True, remote_server_entry=None, remote_target_user=None, can_call=False, show_call=False, wx_parent=None):
        super().__init__(wx_parent or frame)
        self.frame = frame
        self.window = None
        self.unread_count = 0
        self.SetName(f"Conversation with {contact}")
        self._sock = sock
        self.contact, self.user = contact, user
        self.is_contact = bool(is_contact)
        self.remote_server_entry = remote_server_entry
        self.remote_target_user = str(remote_target_user or contact)
        self.is_remote_directory_chat = self.remote_server_entry is not None
        self._can_call = bool(can_call)
        self._show_call = bool(show_call)
        self._pending_message_after_add = None
        self._last_deleted_message = None
        self._editing_message_id = None
        self._last_escape_ts = 0.0
        self._allow_close_once = False
        self.Bind(wx.EVT_CHAR_HOOK, self.on_key)
        self._sent_typing = False
        self._typing_timer = wx.Timer(self)
        self.Bind(wx.EVT_TIMER, self.on_typing_timeout, self._typing_timer)

        dark_mode_on = is_windows_dark_mode()
        if dark_mode_on:
            dark_color = wx.Colour(40, 40, 40); light_text_color = wx.WHITE
            self.SetBackgroundColour(dark_color)

        # Inner tabs: Messages (live chat), Chat Archive (saved days), File Transfers (with this contact).
        self.inner = wx.Notebook(self)
        self.inner.SetName("Conversation sections")
        mp = self.msg_page = wx.Panel(self.inner)
        mp.SetName("Messages")
        s = wx.BoxSizer(wx.VERTICAL)
        self.btn_add_contact = wx.Button(mp, label="&Add to Contacts")
        self.btn_add_contact.Bind(wx.EVT_BUTTON, self.on_add_contact)
        if dark_mode_on:
            self.btn_add_contact.SetBackgroundColour(dark_color); self.btn_add_contact.SetForegroundColour(light_text_color)
        s.Add(self.btn_add_contact, 0, wx.EXPAND | wx.LEFT | wx.RIGHT | wx.TOP, 5)
        if self.is_contact: self.btn_add_contact.Hide()
        self.logging_enabled = bool(logging_enabled)
        self.hist = wx.ListBox(mp, style=wx.LB_SINGLE, name="Messages")
        self._history_rows = []
        self.hist.Bind(wx.EVT_LISTBOX_DCLICK, self.on_history_item_activated)
        self.hist.Bind(wx.EVT_KEY_DOWN, self.on_history_key)
        self.hist.Bind(wx.EVT_CONTEXT_MENU, self.on_history_context_menu)
        self.typing_lbl = wx.StaticText(mp, label="")
        self.typing_lbl.SetForegroundColour(wx.Colour(120, 180, 255))
        box_msg = wx.StaticBoxSizer(wx.VERTICAL, mp, "Type &message")
        self.input_ctrl = wx.TextCtrl(box_msg.GetStaticBox(), style=wx.TE_MULTILINE | wx.TE_PROCESS_ENTER)
        self._consume_next_text_enter = False
        btn = wx.Button(mp, label="&Send")
        btn_file = wx.Button(mp, label="Send &File")
        self.btn_call = wx.Button(mp, label="Place &Call")
        btn_saved = wx.Button(mp, label="Chat &Archive")
        apply_voiceover_hint(btn, "Send the typed message.")
        apply_voiceover_hint(btn_file, "Send a file to this chat contact.")
        apply_voiceover_hint(self.btn_call, "Place a voice call to this contact.")
        apply_voiceover_hint(btn_saved, "Open the Chat Archive tab: saved messages grouped by year, month and day.")
        apply_voiceover_hint(self.btn_add_contact, "Add this person to your contacts.")
        apply_voiceover_hint(self.input_ctrl, "Message input. Enter sends, Command+Enter inserts a new line, Control+Enter sends file.")

        if dark_mode_on:
            self.hist.SetBackgroundColour(dark_color); self.hist.SetForegroundColour(light_text_color)
            box_msg.GetStaticBox().SetForegroundColour(light_text_color)
            box_msg.GetStaticBox().SetBackgroundColour(dark_color)
            self.input_ctrl.SetBackgroundColour(dark_color); self.input_ctrl.SetForegroundColour(light_text_color)
            btn.SetBackgroundColour(dark_color); btn.SetForegroundColour(light_text_color)
            btn_file.SetBackgroundColour(dark_color); btn_file.SetForegroundColour(light_text_color)
            self.btn_call.SetBackgroundColour(dark_color); self.btn_call.SetForegroundColour(light_text_color)
            btn_saved.SetBackgroundColour(dark_color); btn_saved.SetForegroundColour(light_text_color)

        s.Add(self.hist, 1, wx.EXPAND|wx.ALL, 5)
        s.Add(self.typing_lbl, 0, wx.LEFT | wx.RIGHT | wx.BOTTOM, 6)
        self.input_ctrl.Bind(wx.EVT_KEY_DOWN, self.on_input_key)
        self.input_ctrl.Bind(wx.EVT_TEXT_ENTER, self.on_text_enter)
        self.input_ctrl.Bind(wx.EVT_TEXT, self.on_input_text)
        box_msg.Add(self.input_ctrl, 1, wx.EXPAND|wx.ALL, 5)
        s.Add(box_msg, 1, wx.EXPAND|wx.ALL, 5)

        btn.Bind(wx.EVT_BUTTON, self.on_send)
        btn_file.Bind(wx.EVT_BUTTON, self.on_send_file)
        self.btn_call.Bind(wx.EVT_BUTTON, self.on_place_call)
        btn_saved.Bind(wx.EVT_BUTTON, lambda e: self.show_inner_tab(1))
        btn_sizer = wx.BoxSizer(wx.HORIZONTAL)
        btn_sizer.Add(btn, 1, wx.EXPAND | wx.ALL, 5)
        btn_sizer.Add(btn_file, 1, wx.EXPAND | wx.ALL, 5)
        btn_sizer.Add(self.btn_call, 1, wx.EXPAND | wx.ALL, 5)
        btn_sizer.Add(btn_saved, 1, wx.EXPAND | wx.ALL, 5)
        s.Add(btn_sizer, 0, wx.EXPAND|wx.ALL, 5)
        mp.SetSizer(s)
        self.archive_page = ChatArchivePanel(self.inner, self)
        self.transfers_page = ContactTransfersPanel(self.inner, self)
        self.inner.AddPage(mp, "Messages")
        self.inner.AddPage(self.archive_page, "Chat Archive")
        self.inner.AddPage(self.transfers_page, "File Transfers")
        self.inner.Bind(wx.EVT_NOTEBOOK_PAGE_CHANGED, self.on_inner_tab_changed)
        outer = wx.BoxSizer(wx.VERTICAL)
        outer.Add(self.inner, 1, wx.EXPAND)
        self.SetSizer(outer)
        self.apply_call_permissions(self._can_call, self._show_call)
        self._focus_input()
    def apply_call_permissions(self, can_call, show_call):
        self._can_call = bool(can_call)
        self._show_call = bool(show_call)
        if self.is_remote_directory_chat:
            self._can_call = False
            self._show_call = False
        if hasattr(self, "btn_call") and self.btn_call:
            self.btn_call.Show(self._show_call)
            self.btn_call.Enable(self._can_call and self._show_call)
            self.msg_page.Layout()
    def _is_logging_enabled_now(self):
        app = wx.GetApp()
        try:
            return is_chat_logging_enabled(app.user_config, self.contact)
        except Exception:
            return bool(self.logging_enabled)
    def _focus_input(self):
        wx.CallAfter(self.input_ctrl.SetFocus)
        wx.CallLater(120, self.input_ctrl.SetFocus)
    @property
    def sock(self):
        # Always the app's current connection, so a reconnect can never leave a chat on a dead socket.
        app = wx.GetApp()
        return getattr(app, "sock", None) or self._sock
    @sock.setter
    def sock(self, value):
        self._sock = value
    # --- hosting (ChatWindow) -------------------------------------------------
    def display_name(self):
        try:
            return self.frame.format_user_label(self.contact)
        except Exception:
            return str(self.contact)
    def tab_label(self):
        name = self.display_name()
        return f"{name} ({self.unread_count} unread)" if self.unread_count else name
    def open_chat(self, activate=True, select=True):
        """Show this conversation. activate=False never takes focus or switches the visible tab."""
        if self.window:
            self.window.present(self, activate=activate, select=select)
    def is_chat_visible(self):
        return bool(self.window and self.window.IsShown() and self.window.has_chat(self))
    def is_active_chat(self):
        return bool(self.window and self.window.is_active_chat(self))
    def close_chat(self):
        self._send_stop_typing()
        if self.window:
            self.window.remove_chat(self)
    def mark_tab_unread(self):
        self.unread_count += 1
        if self.window:
            self.window.refresh_chat_label(self)
    def clear_tab_unread(self):
        if self.unread_count:
            self.unread_count = 0
            if self.window:
                self.window.refresh_chat_label(self)
        if hasattr(self.frame, "_clear_unread"):
            self.frame._clear_unread(self.contact)
    def on_host_activated(self):
        if self.inner.GetSelection() == 0:
            self._focus_input()
        else:
            page = self.inner.GetCurrentPage()
            if hasattr(page, "focus_default"):
                wx.CallAfter(page.focus_default)
        self.clear_tab_unread()
    def _save_message_to_log(self, formatted_log_line):
        try:
            docs_path = os.path.join(os.path.expanduser('~'), 'Documents')
            log_dir = os.path.join(docs_path, 'ThriveMessenger', 'chats', self.contact)
            os.makedirs(log_dir, exist_ok=True)
            log_file = f"{datetime.date.today().isoformat()}.txt"
            log_path = os.path.join(log_dir, log_file)
            with open(log_path, 'a', encoding='utf-8') as f: f.write(formatted_log_line)
        except Exception as e: print(f"Error: Could not save chat history to '{log_path}'. Reason: {e}")
    def _build_message_display(self, text, sender, ts, is_error=False):
        app = wx.GetApp()
        mode = str(app.user_config.get('message_timestamp_mode', 'start') or 'start').strip().lower()
        stamp = format_timestamp(ts)
        if is_error:
            prefix = "Error"
        elif sender == "System":
            prefix = "System"
        else:
            prefix = str(sender or "")
            parent = self.frame
            if parent and hasattr(parent, "format_user_label"):
                try:
                    prefix = parent.format_user_label(sender)
                except Exception:
                    prefix = str(sender or "")
        if mode == 'off':
            return f"{prefix}: {text}", stamp
        if mode == 'end':
            return f"{prefix}: {text} [{stamp}]", stamp
        return f"[{stamp}] {prefix}: {text}", stamp
    def _contact_log_dir(self):
        docs_path = os.path.join(os.path.expanduser('~'), 'Documents')
        return os.path.join(docs_path, 'ThriveMessenger', 'chats', self.contact)
    def _load_saved_messages_grouped(self):
        log_dir = self._contact_log_dir()
        if not os.path.isdir(log_dir):
            return []
        order = str(wx.GetApp().user_config.get('saved_history_date_order', 'mdy') or 'mdy').strip().lower()
        grouped = []
        entries = []
        for name in os.listdir(log_dir):
            if not name.lower().endswith('.txt'):
                continue
            path = os.path.join(log_dir, name)
            day = None
            base = os.path.splitext(name)[0]
            try:
                day = datetime.date.fromisoformat(base)
            except Exception:
                day = datetime.date.fromtimestamp(os.path.getmtime(path))
            entries.append((day, path))
        for day, path in sorted(entries, key=lambda item: item[0], reverse=True):
            lines = []
            try:
                with open(path, 'r', encoding='utf-8') as f:
                    lines = [ln.rstrip('\n') for ln in f.readlines() if ln.strip()]
            except Exception:
                lines = [f"(Could not read {os.path.basename(path)})"]
            grouped.append({
                "title": format_saved_group_date(day, order=order),
                "lines": lines,
            })
        return grouped
    def on_show_saved_messages(self, _):
        self.show_inner_tab(1)
    INNER_TAB_NAMES = ("Messages", "Chat Archive", "File Transfers")
    def show_inner_tab(self, idx):
        idx = max(0, min(int(idx), self.inner.GetPageCount() - 1))
        if self.inner.GetSelection() != idx:
            self.inner.SetSelection(idx)
        else:
            self._after_inner_switch(idx)
    def switch_inner_tab(self, step):
        count = self.inner.GetPageCount()
        self.show_inner_tab((self.inner.GetSelection() + step) % count)
    def on_inner_tab_changed(self, event):
        if event.GetEventObject() is self.inner:
            self._after_inner_switch(self.inner.GetSelection())
        event.Skip()
    def _after_inner_switch(self, idx):
        page = self.inner.GetPage(idx)
        if hasattr(page, "refresh"):
            page.refresh()
        name = self.INNER_TAB_NAMES[idx] if idx < len(self.INNER_TAB_NAMES) else self.inner.GetPageText(idx)
        speak_text(f"{name}, tab {idx + 1} of {self.inner.GetPageCount()}", interrupt=True)
        if idx == 0:
            self._focus_input()
        elif hasattr(page, "focus_default"):
            wx.CallAfter(page.focus_default)
    def on_input_key(self, event):
        keycode = event.GetKeyCode()
        if keycode in (wx.WXK_RETURN, wx.WXK_NUMPAD_ENTER):
            self._consume_next_text_enter = True
            if event.ControlDown() and event.ShiftDown():
                self.on_place_call(None)
                return
            if event.ControlDown():
                self.on_send_file(None)
                return
            elif event.CmdDown() or event.AltDown() or event.ShiftDown():
                self.input_ctrl.WriteText('\n')
                return
            else:
                self._handle_enter_action()
                return
        event.Skip()

    def on_text_enter(self, event):
        if self._consume_next_text_enter:
            self._consume_next_text_enter = False
            return
        self._handle_enter_action()
    def on_input_text(self, event):
        if self.is_remote_directory_chat:
            event.Skip()
            return
        app = wx.GetApp()
        if app.user_config.get('typing_indicators', True):
            txt = self.input_ctrl.GetValue().strip()
            if txt and not self._sent_typing:
                try:
                    self.sock.sendall((json.dumps({"action": "typing", "to": self.contact, "typing": True}) + "\n").encode())
                    self._sent_typing = True
                except Exception:
                    pass
            if txt:
                self._typing_timer.Start(TYPING_IDLE_STOP_MS, oneShot=True)
            elif self._sent_typing:
                self._send_stop_typing()
        event.Skip()
    def _send_stop_typing(self):
        if self.is_remote_directory_chat:
            self._sent_typing = False
            return
        if not self._sent_typing:
            return
        try:
            self.sock.sendall((json.dumps({"action": "typing", "to": self.contact, "typing": False}) + "\n").encode())
        except Exception:
            pass
        self._sent_typing = False
    def on_typing_timeout(self, event):
        if self._sent_typing:
            self._send_stop_typing()
    def on_key(self, event):
        if event.GetKeyCode() == wx.WXK_F1:
            open_help_docs_for_context("chat", self)
        elif event.GetKeyCode() in (wx.WXK_RETURN, wx.WXK_NUMPAD_ENTER):
            focused = wx.Window.FindFocus()
            is_in_input = False
            w = focused
            while w:
                if w is self.input_ctrl:
                    is_in_input = True
                    break
                w = w.GetParent()
            if is_in_input:
                if event.ControlDown() and event.ShiftDown():
                    self.on_place_call(None)
                elif event.ControlDown():
                    self.on_send_file(None)
                elif event.CmdDown() or event.AltDown() or event.ShiftDown():
                    self.input_ctrl.WriteText('\n')
                else:
                    self._handle_enter_action()
                return
        elif event.ControlDown() and event.GetKeyCode() == ord('L'):
            self.on_place_call(None)
            return
        elif event.CmdDown() and event.GetKeyCode() == ord(','):
            parent = self.frame
            if parent and hasattr(parent, "on_settings"):
                wx.CallAfter(parent.on_settings, None)
        elif (event.CmdDown() and event.GetKeyCode() == ord('W')) or (event.ControlDown() and event.GetKeyCode() == wx.WXK_F4):
            self.close_chat()
            return
        elif event.ControlDown() and not event.AltDown() and event.GetKeyCode() == ord('E'):
            self.on_insert_emoji()
            return
        elif event.ControlDown() and not event.AltDown() and event.GetKeyCode() == ord('R'):
            self.toggle_recording(voicemail=event.ShiftDown())
            return
        elif event.GetKeyCode() == wx.WXK_ESCAPE and self._editing_message_id:
            self._cancel_edit_mode(announce=True)
            return
        elif event.GetKeyCode() == wx.WXK_ESCAPE:
            require_double = bool(wx.GetApp().user_config.get('double_escape_to_close_chat', True))
            if not require_double:
                self.close_chat()
                return
            now = time.monotonic()
            if (now - float(self._last_escape_ts or 0.0)) <= 1.2:
                self._last_escape_ts = 0.0
                self.close_chat()
                return
            self._last_escape_ts = now
            self.typing_lbl.SetLabel("Press Escape again to close this chat.")
            return
        else: event.Skip()
    def on_send(self, _):
        txt = self.input_ctrl.GetValue().strip()
        if not txt: return
        if not self.is_contact:
            res = wx.MessageBox(
                f"{self.contact} is not in your contacts.\n\nAdd this user to contacts before sending?",
                "Add Contact First",
                wx.YES_NO | wx.ICON_QUESTION,
                self,
            )
            if res != wx.YES:
                return
            self._pending_message_after_add = txt
            self.on_add_contact(None)
            return
        self._send_stop_typing()
        ts = datetime.datetime.now().isoformat()
        if self.is_remote_directory_chat:
            ok, reason = wx.GetApp().send_directory_direct_message(self.remote_server_entry, self.user, self.remote_target_user, txt)
            if not ok:
                self.append_error(reason or "Message failed.")
                return
        else:
            if self._editing_message_id:
                self._send_message_edit(txt)
                return
            client_id = uuid.uuid4().hex
            msg = {"action":"msg","to":self.contact,"from":self.user,"msg":txt,"time":ts,"client_id":client_id}
            state = wx.GetApp().send_chat_payload(self, msg)
            self.append(txt, self.user, ts, client_id=client_id)
            if state == "queued":
                self.mark_row_queued(client_id, True)
                speak_text("Offline. The message will be sent when Thrive reconnects.", interrupt=False)
            wx.GetApp().play_sound("send.wav")
            self.input_ctrl.Clear(); self.input_ctrl.SetFocus()
            return
        self.append(txt, self.user, ts, client_id=None)
        wx.GetApp().play_sound("send.wav")
        self.input_ctrl.Clear(); self.input_ctrl.SetFocus()
    def on_send_file(self, _):
        if self.is_remote_directory_chat:
            wx.MessageBox("Cross-server file transfer is not supported in directory direct message mode.", "Feature Not Supported", wx.OK | wx.ICON_INFORMATION)
            return
        wx.GetApp().send_file_to(self.contact)
    def on_place_call(self, _):
        if not self._can_call:
            wx.MessageBox("Calling is disabled for your account on this server.", "Feature Disabled", wx.OK | wx.ICON_INFORMATION)
            return
        if self.is_remote_directory_chat:
            wx.MessageBox("Cross-server calling is not supported in directory direct message mode.", "Feature Not Supported", wx.OK | wx.ICON_INFORMATION)
            return
        # Dedicated call action; kept separate from Enter so Enter behavior remains user-configurable.
        try:
            self.sock.sendall((json.dumps({"action": "voice_call_request", "to": self.contact}) + "\n").encode())
            show_notification("Calling", f"Placing call to {self.contact}...", timeout=4)
        except Exception as e:
            wx.MessageBox(f"This server does not support voice calling yet.\n\n{e}", "Feature Not Supported", wx.OK | wx.ICON_INFORMATION)
    def _handle_enter_action(self):
        action = str(wx.GetApp().user_config.get('enter_key_action', 'none') or 'none')
        if action == 'place_call':
            self.on_place_call(None)
        elif action == 'none':
            return
        elif action == 'newline':
            self.input_ctrl.WriteText('\n')
        else:
            self.on_send(None)
    def on_add_contact(self, _):
        try:
            self.sock.sendall(json.dumps({"action": "add_contact", "to": self.contact}).encode() + b"\n")
        except Exception as e:
            self.append_error(f"Could not add contact: {e}")
            return
        self.btn_add_contact.Disable(); self.btn_add_contact.SetLabel("Adding...")
    def hide_add_button(self):
        self.is_contact = True
        self.btn_add_contact.Hide(); self.msg_page.Layout()
    def send_pending_after_contact_added(self):
        if not self._pending_message_after_add:
            return
        pending = self._pending_message_after_add
        self._pending_message_after_add = None
        self.input_ctrl.SetValue(pending)
        self.on_send(None)
    def append(self, text, sender, ts, is_error=False, announce=True, msg_id=None, client_id=None, files=None, voice=None):
        display, formatted_time = self._build_message_display(text, sender, ts, is_error=is_error)
        self.hist.Append(display)
        row = {"sender": sender, "text": text, "time": ts, "error": is_error}
        if msg_id:
            row["id"] = msg_id
        if client_id:
            row["client_id"] = client_id
        if files:
            row["files"] = list(files)
        if voice:
            row["voice"] = dict(voice)
            if voice.get("path"):
                row["files"] = list(row.get("files", [])) + [voice["path"]]
        self._history_rows.append(row)
        self.hist.SetSelection(self.hist.GetCount() - 1)
        app = wx.GetApp()
        if announce and sender not in (self.user, "System") and app.user_config.get('read_messages_aloud', False):
            parent = self.frame
            sender_label = sender
            if parent and hasattr(parent, "format_user_label"):
                sender_label = parent.format_user_label(sender)
            speak_text(f"{sender_label} says {text}")
        if self._is_logging_enabled_now():
            log_line = f"{display}\n"
            self._save_message_to_log(log_line)
    def append_error(self, reason):
        ts = time.time()
        self.append(reason, "System", ts, is_error=True)
        # Only move focus within this chat when it's already the active window; never pull focus from elsewhere.
        if self.is_active_chat():
            self.input_ctrl.SetFocus()
        else:
            speak_text(f"Chat with {self.contact}: {reason}")
    def _selected_history_index(self):
        idx = self.hist.GetSelection()
        if idx == wx.NOT_FOUND or idx < 0 or idx >= len(self._history_rows):
            return None
        return idx
    def _timestamp_to_epoch(self, ts):
        try:
            if isinstance(ts, (int, float)):
                return float(ts)
            return datetime.datetime.fromisoformat(str(ts)).timestamp()
        except Exception:
            return time.time()
    def _is_row_editable(self, row):
        if row.get("sender") != self.user or row.get("error", False):
            return False
        window = int(wx.GetApp().user_config.get('message_edit_window_seconds', 300) or 300)
        if window <= 0:
            return False
        age = max(0.0, time.time() - self._timestamp_to_epoch(row.get("time")))
        return age <= float(window)
    def _can_undo_delete(self):
        if not self._last_deleted_message:
            return False
        undo_window = int(wx.GetApp().user_config.get('message_undo_window_seconds', 15) or 15)
        if undo_window <= 0:
            return False
        deleted_at = float(self._last_deleted_message.get("deleted_at", 0.0))
        return (time.time() - deleted_at) <= float(undo_window)
    def on_history_context_menu(self, event):
        idx = self._selected_history_index()
        if idx is None:
            return
        row = self._history_rows[idx]
        can_edit = self._can_edit_row(row)
        menu = wx.Menu()
        mi_view = menu.Append(wx.ID_ANY, "View Full Message")
        mi_copy = menu.Append(wx.ID_ANY, "&Copy Message\tCtrl+C")
        mi_save = menu.Append(wx.ID_ANY, "&Save to Chat Archive\tCtrl+S")
        # Edit only appears for your own messages (or any message, for admins); nobody else can edit them.
        mi_edit = menu.Append(wx.ID_ANY, "&Edit Message") if can_edit else None
        mi_remove = menu.Append(wx.ID_ANY, "&Delete Message\tDelete")
        mi_undo = menu.Append(wx.ID_ANY, "Undo Delete")
        mi_undo.Enable(self._can_undo_delete())
        self.Bind(wx.EVT_MENU, self.on_view_selected_message, mi_view)
        self.Bind(wx.EVT_MENU, self.on_copy_selected_message, mi_copy)
        self.Bind(wx.EVT_MENU, self.on_save_selected_to_archive, mi_save)
        if mi_edit:
            self.Bind(wx.EVT_MENU, self.on_edit_selected_message, mi_edit)
        self.Bind(wx.EVT_MENU, self.on_remove_selected_message, mi_remove)
        self.Bind(wx.EVT_MENU, self.on_undo_last_deleted_message, mi_undo)
        self.PopupMenu(menu)
        menu.Destroy()
    def on_view_selected_message(self, _=None):
        idx = self._selected_history_index()
        if idx is None:
            return
        row = self._history_rows[idx]
        sender = row.get("sender", "")
        label = str(sender or "")
        parent = self.frame
        if sender not in ("System", "") and parent and hasattr(parent, "format_user_label"):
            try:
                label = parent.format_user_label(sender)
            except Exception:
                pass
        dlg = MessageViewerDialog(self, label, str(row.get("text", "")), format_timestamp(row.get("time", time.time())))
        dlg.ShowModal()
        dlg.Destroy()
        self.hist.SetFocus()
    @property
    def voice_player(self):
        if not hasattr(self, "_voice_player"):
            self._voice_player = VoicePlayer(self.msg_page)
        return self._voice_player
    def _selected_voice_row(self):
        idx = self._selected_history_index()
        if idx is None:
            return None
        row = self._history_rows[idx]
        return row if row.get("voice") else None
    def _voice_label(self, row):
        v = row.get("voice") or {}
        kind = "voicemail" if v.get("voicemail") else "voice message"
        who = "you" if str(row.get("sender", "")).lower() == str(self.user).lower() else self.frame.format_user_label(row.get("sender", ""))
        return f"{kind} from {who}, {format_seconds(v.get('duration', 0))}"
    def _play_voice_row(self, row, toggle=False):
        path = (row.get("voice") or {}).get("path")
        if toggle:
            self.voice_player.toggle(path, self._voice_label(row))
        else:
            self.voice_player.play(path, self._voice_label(row))
    def on_insert_emoji(self, _=None):
        if self.inner.GetSelection() != 0:
            self.inner.SetSelection(0)
        with EmojiPickerDialog(self) as dlg:
            chosen = dlg.selected if dlg.ShowModal() == wx.ID_OK else None
        self.input_ctrl.SetFocus()
        if chosen:
            self.input_ctrl.WriteText(chosen)
    def toggle_recording(self, voicemail=False):
        rec = getattr(self, "_recorder", None)
        app = wx.GetApp()
        if rec and rec.stream:
            timer = getattr(self, "_record_timer", None)
            if timer:
                timer.Stop()
            wav, seconds = rec.stop()
            self._recorder = None
            app.play_sound("recording_stop.wav")
            speak_text(f"Recording stopped, {format_seconds(seconds)}", interrupt=True)
            if seconds < 0.5:
                speak_text("That was too short to send.", interrupt=False)
                return
            os.makedirs(voice_cache_dir(), exist_ok=True)
            path = os.path.join(voice_cache_dir(), f"sent-{uuid.uuid4().hex}.wav")
            with open(path, "wb") as fh:
                fh.write(wav)
            with VoiceRecordedDialog(self, path, seconds, voicemail=self._recording_voicemail) as dlg:
                send = dlg.ShowModal() == wx.ID_OK
                dlg.player.stop()
            self.input_ctrl.SetFocus()
            if send:
                self._send_voice(path, wav, seconds, self._recording_voicemail)
            else:
                try:
                    os.remove(path)
                except OSError:
                    pass
                speak_text("Discarded", interrupt=True)
            return
        if self.is_remote_directory_chat:
            speak_text("Voice messages aren't available in cross-server chats.", interrupt=True)
            return
        if not VoiceRecorder.available():
            speak_text("Recording isn't available: no audio input support was found.", interrupt=True)
            return
        self._recording_voicemail = bool(voicemail)
        app.play_sound("recording_start.wav")
        try:
            rec = VoiceRecorder()
            rec.start()
        except Exception as e:
            speak_text(f"Couldn't start recording: {e}", interrupt=True)
            return
        self._recorder = rec
        kind = "voicemail" if voicemail else "voice message"
        speak_text(f"Recording {kind}. Press Control R again to stop.", interrupt=True)
        self._record_timer = wx.CallLater(VoiceRecorder.MAX_SECONDS * 1000, lambda: self._recorder and self.toggle_recording())
    def _send_voice(self, path, wav, seconds, voicemail):
        client_id = uuid.uuid4().hex
        payload = {"action": "msg", "to": self.contact, "from": self.user, "msg": "", "time": datetime.datetime.now().isoformat(),
                   "client_id": client_id,
                   "voice": {"b64": base64.b64encode(wav).decode("ascii"), "mime": "audio/wav", "voicemail": bool(voicemail)}}
        try:
            self.sock.sendall((json.dumps(payload) + "\n").encode())
        except Exception as e:
            self.append_error(f"Voice message failed to send: {e}")
            return
        kind = "Voicemail" if voicemail else "Voice message"
        self.append(f"{kind} ({format_seconds(seconds)})", self.user, payload["time"], client_id=client_id,
                    voice={"path": path, "duration": seconds, "voicemail": bool(voicemail)})
        wx.GetApp().add_transfer_history("sent", self.contact, f"{kind} {datetime.datetime.now().strftime('%Y-%m-%d %H-%M')}.wav",
                                         path, "sent", kind="voicemail" if voicemail else "voice")
        wx.GetApp().play_sound("voice_message_send.wav")
        speak_text(f"{kind} sent", interrupt=False)
    def on_save_selected_to_archive(self, _=None):
        idx = self._selected_history_index()
        if idx is None:
            return
        row = self._history_rows[idx]
        display, _ = self._build_message_display(row.get("text", ""), row.get("sender", "System"), row.get("time", time.time()), is_error=row.get("error", False))
        try:
            day = parse_timestamp_value(row.get("time"))
            day = day.date() if day else datetime.date.today()
            log_dir = self._contact_log_dir()
            os.makedirs(log_dir, exist_ok=True)
            with open(os.path.join(log_dir, f"{day.isoformat()}.txt"), "a", encoding="utf-8") as fh:
                fh.write(display + "\n")
            speak_text("Saved to Chat Archive", interrupt=True)
        except Exception as e:
            speak_text(f"Could not save the message: {e}", interrupt=True)
    def on_copy_selected_message(self, _=None):
        idx = self._selected_history_index()
        if idx is None:
            return
        text = str(self._history_rows[idx].get("text", "") or "")
        copied = False
        if wx.TheClipboard.Open():
            try:
                copied = bool(wx.TheClipboard.SetData(wx.TextDataObject(text)))
                wx.TheClipboard.Flush()
            finally:
                wx.TheClipboard.Close()
        if copied:
            wx.GetApp().play_sound("copied.wav")
        speak_text("Copied" if copied else "Could not copy the message", interrupt=True)
    def _am_admin(self):
        parent = self.frame
        return bool(getattr(parent, "am_admin", False))
    def _can_edit_row(self, row):
        if row.get("error", False) or row.get("sender") in ("System", "", None):
            return False
        if self._is_row_editable(row):
            return True
        # Admins may edit anyone's message, but only ones the server knows by ID.
        return bool(row.get("id")) and self._am_admin()
    def _can_delete_for_everyone(self, row):
        if not row.get("id") or row.get("error", False):
            return False
        return str(row.get("sender") or "").lower() == str(self.user or "").lower() or self._am_admin()
    def has_message_id(self, msg_id):
        return bool(msg_id) and any(r.get("id") == msg_id for r in self._history_rows)
    def _row_index_for_id(self, msg_id):
        if not msg_id:
            return None
        for i, r in enumerate(self._history_rows):
            if r.get("id") == msg_id:
                return i
        return None
    def _refresh_row_display(self, idx):
        row = self._history_rows[idx]
        text = row.get("text", "")
        if row.get("edited"):
            text = f"{text} (edited)"
        if row.get("queued"):
            text = f"{text} (not sent yet, will send when reconnected)"
        display, _ = self._build_message_display(text, row.get("sender", "System"), row.get("time", time.time()), is_error=row.get("error", False))
        selected = self.hist.GetSelection()
        self.hist.SetString(idx, display)
        if selected != wx.NOT_FOUND:
            self.hist.SetSelection(selected)
    def mark_row_queued(self, client_id, queued):
        for i, r in enumerate(self._history_rows):
            if client_id and r.get("client_id") == client_id:
                r["queued"] = bool(queued)
                self._refresh_row_display(i)
                return
    def set_row_message_id(self, client_id, msg_id):
        if not client_id or not msg_id:
            return
        for r in reversed(self._history_rows):
            if r.get("client_id") == client_id:
                r["id"] = msg_id
                return
    def apply_remote_edit(self, msg_id, text):
        idx = self._row_index_for_id(msg_id)
        if idx is None:
            return False
        self._history_rows[idx]["text"] = text
        self._history_rows[idx]["edited"] = True
        self._refresh_row_display(idx)
        return True
    def apply_remote_delete(self, msg_id):
        idx = self._row_index_for_id(msg_id)
        if idx is None:
            return False
        self._delete_row_locally(idx, allow_undo=False)
        return True
    def _delete_row_locally(self, idx, allow_undo=True):
        keep_focus_in_hist = wx.Window.FindFocus() is self.hist
        row = self._history_rows.pop(idx)
        self.hist.Delete(idx)
        if allow_undo:
            self._last_deleted_message = {"row": row, "index": idx, "deleted_at": time.time()}
        if self.hist.GetCount() > 0:
            self.hist.SetSelection(max(0, idx - 1))
        if keep_focus_in_hist:
            self.hist.SetFocus()
        if self._editing_message_id and row.get("id") == self._editing_message_id:
            self._cancel_edit_mode(announce=False)
        if row.get("files") and wx.GetApp().user_config.get('delete_attached_files_with_message', False):
            removed = remove_received_files(row.get("files") or [])
            if removed:
                speak_text(f"{removed} attached file{'s' if removed != 1 else ''} moved to the Recycle Bin", interrupt=False)
        return row
    def on_edit_selected_message(self, _):
        idx = self._selected_history_index()
        if idx is None:
            return
        row = self._history_rows[idx]
        if not self._can_edit_row(row):
            return
        self.input_ctrl.SetValue(str(row.get("text", "")))
        if row.get("id"):
            self._editing_message_id = row["id"]
            self.typing_lbl.SetLabel("Editing a message. Press Enter to save or Escape to cancel.")
            speak_text("Editing message. Press Enter to save, or Escape to cancel.", interrupt=True)
        self.input_ctrl.SetFocus()
        self.input_ctrl.SetInsertionPointEnd()
    def _cancel_edit_mode(self, announce=True):
        self._editing_message_id = None
        self.input_ctrl.Clear()
        self.typing_lbl.SetLabel("")
        if announce:
            speak_text("Edit cancelled", interrupt=True)
    def _send_message_edit(self, txt):
        msg_id = self._editing_message_id
        try:
            self.sock.sendall((json.dumps({"action": "msg_edit", "id": msg_id, "msg": txt}) + "\n").encode())
        except Exception as e:
            self.append_error(f"Could not save the edit: {e}")
            return
        # The server confirms with msg_edited, which updates the row for both people.
        self._editing_message_id = None
        self.typing_lbl.SetLabel("")
        self.input_ctrl.Clear(); self.input_ctrl.SetFocus()
    def on_remove_selected_message(self, _):
        idx = self._selected_history_index()
        if idx is None:
            return
        row = self._history_rows[idx]
        want_everyone = bool(wx.GetApp().user_config.get('delete_messages_for_everyone', True))
        if want_everyone and self._can_delete_for_everyone(row) and not self.is_remote_directory_chat:
            res = wx.MessageBox(
                "Delete this message for everyone in this conversation? This can't be undone.",
                "Delete Message",
                wx.YES_NO | wx.NO_DEFAULT | wx.ICON_QUESTION,
                self,
            )
            if res != wx.YES:
                self.hist.SetFocus()
                return
            try:
                self.sock.sendall((json.dumps({"action": "msg_delete", "id": row["id"]}) + "\n").encode())
            except Exception as e:
                self.append_error(f"Could not delete the message: {e}")
                return
            # Removed now; the server's msg_deleted for this id then finds nothing left to do here.
            self._delete_row_locally(idx, allow_undo=False)
            return
        self._delete_row_locally(idx, allow_undo=True)
        if want_everyone and row.get("id") and not row.get("error") and row.get("sender") not in ("System",):
            speak_text("Removed from this device only. Only the sender or an admin can delete it for everyone.", interrupt=True)
        else:
            speak_text("Message removed", interrupt=True)
    def on_undo_last_deleted_message(self, _):
        if not self._can_undo_delete():
            return
        payload = self._last_deleted_message or {}
        row = payload.get("row")
        idx = int(payload.get("index", self.hist.GetCount()))
        if not isinstance(row, dict):
            return
        idx = max(0, min(idx, self.hist.GetCount()))
        self._history_rows.insert(idx, row)
        display, _ = self._build_message_display(row.get("text", ""), row.get("sender", "System"), row.get("time", time.time()), is_error=row.get("error", False))
        self.hist.Insert(display, idx)
        self.hist.SetSelection(idx)
        self._last_deleted_message = None

    def on_history_item_activated(self, event):
        idx = self.hist.GetSelection()
        if idx == wx.NOT_FOUND or idx < 0:
            return
        if idx >= len(self._history_rows):
            return
        if self._history_rows[idx].get("voice"):
            self._play_voice_row(self._history_rows[idx], toggle=True)
            return
        message_text = self._history_rows[idx].get("text", "")
        urls = extract_urls(message_text)
        if not urls:
            self.on_view_selected_message()
            return
        if len(urls) == 1:
            open_path_or_url(urls[0])
            return
        chosen = urls[0]
        # Keep interaction simple for screen-reader flow: open first URL and notify user.
        wx.MessageBox(f"Multiple links found. Opening first link:\n{chosen}", "Open Link", wx.OK | wx.ICON_INFORMATION)
        open_path_or_url(chosen)
    def on_history_key(self, event):
        if event.GetKeyCode() in (ord('C'), ord('c')) and event.ControlDown() and not event.AltDown() and not event.ShiftDown():
            self.on_copy_selected_message()
            return
        voice_row = self._selected_voice_row()
        if voice_row and not event.HasAnyModifiers():
            code = event.GetKeyCode()
            if code == wx.WXK_SPACE:
                if not self.voice_player.pause_resume():
                    self._play_voice_row(voice_row)
                return
            if code in (wx.WXK_LEFT, wx.WXK_RIGHT) and self.voice_player.path == voice_row["voice"].get("path"):
                if self.voice_player.seek(-VoicePlayer.SKIP_MS if code == wx.WXK_LEFT else VoicePlayer.SKIP_MS):
                    return
        if event.GetKeyCode() in (ord('S'), ord('s')) and event.ControlDown() and not event.AltDown() and not event.ShiftDown():
            self.on_save_selected_to_archive()
            return
        if sys.platform == 'darwin' and event.GetKeyCode() == wx.WXK_BACK and event.CmdDown():
            self.on_remove_selected_message(None)  # Command+Delete, the Mac way to delete an item
            return
        if event.GetKeyCode() in (wx.WXK_DELETE, wx.WXK_NUMPAD_DELETE) and not event.HasAnyModifiers():
            self.on_remove_selected_message(None)
            return
        if event.GetKeyCode() in (wx.WXK_RETURN, wx.WXK_NUMPAD_ENTER):
            idx = self.hist.GetSelection()
            if idx != wx.NOT_FOUND:
                self.on_history_item_activated(event)
            return
        event.Skip()
    def set_typing_label(self, username, is_typing):
        app = wx.GetApp()
        if is_typing and app.user_config.get('typing_indicators', True):
            label = username
            parent = self.frame
            if parent and hasattr(parent, "format_user_label"):
                label = parent.format_user_label(username)
            self.typing_lbl.SetLabel(f"{label} is typing...")
        else:
            self.typing_lbl.SetLabel("")

CHAT_TAB_KEYS_HELP = ("Ctrl+Tab and Ctrl+Shift+Tab switch conversations, Ctrl+1 to Ctrl+9 jump to one (Ctrl+9 is the last), "
                      "Ctrl+W or Ctrl+F4 closes the current one, Ctrl+0 goes to the contact list, "
                      "and Ctrl+Page Down / Ctrl+Page Up switch between Messages, Chat Archive and File Transfers.")

class ChatWindow(wx.Frame):
    """Hosts conversations: a notebook with one tab per chat (tabbed mode) or a single chat (classic mode).
    owned=False gives the window its own taskbar/Alt+Tab entry so the contact list stays reachable too."""
    def __init__(self, main_frame, tabbed=True, owned=False):
        style = wx.DEFAULT_FRAME_STYLE
        if owned:
            style |= wx.FRAME_FLOAT_ON_PARENT | wx.FRAME_NO_TASKBAR
        super().__init__(main_frame if owned else None, title="Chats - Thrive Messenger", size=(560, 560), style=style)
        self.main_frame = main_frame
        self.tabbed = bool(tabbed)
        self.owned = bool(owned)
        self._single = None
        self._announce_switch = False
        self._restore_from_tray = False
        if is_windows_dark_mode():
            try:
                WxMswDarkMode().enable(self); self.SetBackgroundColour(wx.Colour(40, 40, 40))
            except Exception:
                pass
        self._sizer = wx.BoxSizer(wx.VERTICAL)
        if self.tabbed:
            self.notebook = wx.Notebook(self)
            self.notebook.SetName("Conversations")
            self.notebook.Bind(wx.EVT_NOTEBOOK_PAGE_CHANGED, self.on_page_changed)
            self._sizer.Add(self.notebook, 1, wx.EXPAND)
        else:
            self.notebook = None
        self.SetSizer(self._sizer)
        self._build_menu()
        self.Bind(wx.EVT_CLOSE, self.on_close)
        self.Bind(wx.EVT_ACTIVATE, self.on_activate)
        self.Bind(wx.EVT_CHAR_HOOK, self.on_key)
    def _build_menu(self):
        bar = wx.MenuBar()
        chat = wx.Menu()
        items = [
            ("Insert &Emoji...\tCtrl+E", lambda c: c.on_insert_emoji()),
            ("&Record Voice Message\tCtrl+R", lambda c: c.toggle_recording(voicemail=False)),
            ("Leave &Voicemail\tCtrl+Shift+R", lambda c: c.toggle_recording(voicemail=True)),
            ("Send &File...", lambda c: c.on_send_file(None)),
            (None, None),
            ("&Messages", lambda c: c.show_inner_tab(0)),
            ("Chat &Archive", lambda c: c.show_inner_tab(1)),
            ("File &Transfers", lambda c: c.show_inner_tab(2)),
            (None, None),
            ("Go to &Contact List\tCtrl+0", None),
            ("&Close Chat\tCtrl+W", lambda c: c.close_chat()),
        ]
        for label, action in items:
            if label is None:
                chat.AppendSeparator()
                continue
            item = chat.Append(wx.ID_ANY, label)
            if action is None:
                self.Bind(wx.EVT_MENU, lambda e: self.main_frame.focus_contact_list(), item)
            else:
                self.Bind(wx.EVT_MENU, lambda e, a=action: self._with_current(a), item)
        bar.Append(chat, "&Chat")
        self.SetMenuBar(bar)
    def _with_current(self, action):
        cur = self.current_chat()
        if cur:
            action(cur)
    def page_parent(self):
        return self.notebook if self.tabbed else self
    def attach(self, panel):
        panel.window = self
        if self.tabbed:
            panel.Hide()  # becomes a tab when the conversation is opened
        else:
            self._single = panel
            self._sizer.Add(panel, 1, wx.EXPAND)
            self.Layout()
            self._update_title()
    def _index_of(self, panel):
        if not self.tabbed:
            return 0 if panel is self._single else wx.NOT_FOUND
        for i in range(self.notebook.GetPageCount()):
            if self.notebook.GetPage(i) is panel:
                return i
        return wx.NOT_FOUND
    def has_chat(self, panel):
        return self._index_of(panel) != wx.NOT_FOUND
    def chats(self):
        if not self.tabbed:
            return [self._single] if self._single else []
        return [self.notebook.GetPage(i) for i in range(self.notebook.GetPageCount())]
    def current_chat(self):
        if not self.tabbed:
            return self._single
        page = self.notebook.GetCurrentPage()
        return page if isinstance(page, ChatPanel) else None
    def present(self, panel, activate=True, select=True):
        if self.tabbed and not self.has_chat(panel):
            self.notebook.AddPage(panel, panel.tab_label(), select=False)
        if self.tabbed and select:
            idx = self._index_of(panel)
            if idx != wx.NOT_FOUND and self.notebook.GetSelection() != idx:
                self._announce_switch = False
                self.notebook.SetSelection(idx)
        if not self.IsShown():
            if activate:
                self.Show()
            else:
                self.ShowWithoutActivating()
        if activate:
            if self.IsIconized():
                self.Iconize(False)
            self.Raise()
            panel.on_host_activated()
        self._update_title()
    def remove_chat(self, panel):
        if not self.tabbed:
            self.Hide()
            return
        idx = self._index_of(panel)
        if idx == wx.NOT_FOUND:
            return
        was_active = self.IsActive()
        self.notebook.RemovePage(idx)
        panel.Hide()
        if self.notebook.GetPageCount() == 0:
            self.Hide()
            if was_active:
                self.main_frame.focus_contact_list(announce=False)
            return
        new_idx = min(idx, self.notebook.GetPageCount() - 1)
        self._announce_switch = was_active
        self.notebook.SetSelection(new_idx)
        cur = self.current_chat()
        if cur and was_active:
            cur.on_host_activated()
            self._announce_current()
        self._update_title()
    def is_active_chat(self, panel):
        return bool(self.IsShown() and self.IsActive() and self.current_chat() is panel)
    def refresh_chat_label(self, panel):
        idx = self._index_of(panel)
        if self.tabbed and idx != wx.NOT_FOUND:
            self.notebook.SetPageText(idx, panel.tab_label())
        self._update_title()
    def _update_title(self):
        cur = self.current_chat()
        if not cur:
            self.SetTitle("Chats - Thrive Messenger")
            return
        name = cur.display_name()
        if self.tabbed:
            others = sum(c.unread_count for c in self.chats() if c is not cur)
            extra = f" ({others} unread in other chats)" if others else ""
            self.SetTitle(f"Chat with {name}{extra} - Thrive Messenger")
        else:
            self.SetTitle(f"Chat with {name} - Thrive Messenger")
    def _announce_current(self):
        cur = self.current_chat()
        if not cur or not self.tabbed:
            return
        idx = self._index_of(cur)
        count = self.notebook.GetPageCount()
        unread = f", {cur.unread_count} unread" if cur.unread_count else ""
        speak_text(f"{cur.display_name()}{unread}, tab {idx + 1} of {count}", interrupt=True)
    def select_tab(self, idx, announce=True):
        if not self.tabbed or not self.notebook.GetPageCount():
            return
        idx = max(0, min(idx, self.notebook.GetPageCount() - 1))
        if idx == self.notebook.GetSelection():
            if announce:
                self._announce_current()
            return
        self._announce_switch = announce
        self.notebook.SetSelection(idx)
    def on_page_changed(self, event):
        cur = self.current_chat()
        announce = self._announce_switch
        self._announce_switch = False
        if cur and self.IsActive():
            if announce:
                # Say the tab name first; clearing unread afterwards keeps the count in the announcement.
                self._announce_current()
            cur.on_host_activated()
        self._update_title()
        event.Skip()
    def on_key(self, event):
        code = event.GetKeyCode()
        ctrl = event.ControlDown() and not event.AltDown()   # Command on macOS
        shift = event.ShiftDown()
        if sys.platform == 'darwin':
            raw_ctrl = event.RawControlDown() and not event.AltDown()
            # Ctrl+Tab (Command+Tab belongs to macOS), plus the usual Command+Shift+] / [.
            if self.tabbed and ((raw_ctrl and code == wx.WXK_TAB) or (event.CmdDown() and shift and code in (ord(']'), ord('[')))):
                count = self.notebook.GetPageCount()
                if count:
                    back = (code == ord('[')) or (code == wx.WXK_TAB and shift)
                    self.select_tab((self.notebook.GetSelection() + (-1 if back else 1)) % count)
                return
            # Inner tabs: Ctrl+Page Down/Up, or Command+Option+Right/Left on keyboards without Page keys.
            if (raw_ctrl and code in (wx.WXK_PAGEDOWN, wx.WXK_PAGEUP)) or (event.CmdDown() and event.AltDown() and code in (wx.WXK_RIGHT, wx.WXK_LEFT)):
                cur = self.current_chat()
                if cur and hasattr(cur, "switch_inner_tab"):
                    cur.switch_inner_tab(1 if code in (wx.WXK_PAGEDOWN, wx.WXK_RIGHT) else -1)
                return
        if self.tabbed and ctrl and code == wx.WXK_TAB:
            count = self.notebook.GetPageCount()
            if count:
                self.select_tab((self.notebook.GetSelection() + (-1 if shift else 1)) % count)
            return
        if self.tabbed and ctrl and not shift and ord('1') <= code <= ord('9'):
            count = self.notebook.GetPageCount()
            self.select_tab(count - 1 if code == ord('9') else code - ord('1'))
            return
        if ctrl and not shift and code == ord('0'):
            self.main_frame.focus_contact_list()
            return
        if ctrl and code in (wx.WXK_PAGEDOWN, wx.WXK_PAGEUP, wx.WXK_NUMPAD_PAGEDOWN, wx.WXK_NUMPAD_PAGEUP):
            cur = self.current_chat()
            if cur and hasattr(cur, "switch_inner_tab"):
                cur.switch_inner_tab(1 if code in (wx.WXK_PAGEDOWN, wx.WXK_NUMPAD_PAGEDOWN) else -1)
            return
        event.Skip()
    def on_activate(self, event):
        if event.GetActive():
            cur = self.current_chat()
            if cur:
                wx.CallAfter(cur.on_host_activated)
        event.Skip()
    def on_close(self, event):
        if getattr(self.main_frame, "is_exiting", False) or not event.CanVeto():
            event.Skip()
            return
        # Guard against focus-switch side effects (e.g., Alt-Tab) closing chats.
        if not wx.GetApp().IsActive():
            event.Veto()
            return
        for panel in list(self.chats()):
            panel._send_stop_typing()
        if self.tabbed:
            while self.notebook.GetPageCount():
                page = self.notebook.GetPage(0)
                self.notebook.RemovePage(0)
                page.Hide()
        event.Veto()
        self.Hide()
        self.main_frame.focus_contact_list(announce=False)

def ChatDialog(frame, contact, sock, user, logging_enabled=False, **kwargs):
    """Create a conversation in the chat window chosen by the user's settings. Kept under the old name for callers."""
    window = frame.chat_window_for_new_chat()
    panel = ChatPanel(frame, contact, sock, user, logging_enabled, wx_parent=window.page_parent(), **kwargs)
    window.attach(panel)
    frame.register_chat(panel)
    return panel

def main():
    app = ClientApp(False); app.MainLoop()

if __name__ == "__main__": main()
