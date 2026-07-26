import os


def resolve_windows_relaunch_executable(program_dir, current_executable="", is_frozen=False):
    """Return the installed executable that should be relaunched after an update."""
    if is_frozen and current_executable:
        current_executable = os.path.abspath(current_executable)
        if os.path.isfile(current_executable):
            return current_executable

    for filename in ("Indiginous.exe", "thrive_messenger.exe", "ThriveMessenger.exe"):
        candidate = os.path.join(program_dir, filename)
        if os.path.isfile(candidate):
            return candidate

    # New installers use the Indiginous product name. Returning that path also
    # lets an installer create/replace it before the deferred relaunch occurs.
    return os.path.join(program_dir, "Indiginous.exe")
