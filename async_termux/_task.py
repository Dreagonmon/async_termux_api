import os
import asyncio
import shlex

def _is_in_termux():
    return os.environ.get("TMPDIR", "/root").startswith("/data/data/com.termux")

def _find_in_path(file, path=None):
    if path is None:
        path = os.environ['PATH']
    paths = path.split(os.pathsep)
    for p in paths:
        try:
            for f in os.listdir(p):
                if f != file: continue
                f_path = os.path.join(p, file)
                if os.path.isfile(f_path):
                    return f_path
        except FileNotFoundError: pass
    return None
TERMUX_ROOTDIR = "/data/data/com.termux/files"
TERMUX_HOMEDIR = os.path.join(TERMUX_ROOTDIR, "home")
TERMUX_STORAGE = os.path.join(TERMUX_ROOTDIR, "home", "storage", "shared")
DEFAULT_TMPDIR = os.path.join(TERMUX_ROOTDIR, "usr", "tmp")
DEFAULT_PATH = os.path.join(TERMUX_ROOTDIR, "usr", "bin")
SYSTEM_PATH = "/system/bin"
TMPDIR = os.environ.get("TMPDIR", DEFAULT_TMPDIR) if _is_in_termux() else DEFAULT_TMPDIR
PATH = os.environ.get("PATH", DEFAULT_PATH) if _is_in_termux() else DEFAULT_PATH
TERMUX_TOAST = _find_in_path("termux-toast", PATH)
TERMUX_NOTIFICATION = _find_in_path("termux-notification", PATH)
TERMUX_NOTIFICATION_REMOVE = _find_in_path("termux-notification-remove", PATH)
TERMUX_CLIPBOARD_GET = _find_in_path("termux-clipboard-get", PATH)
TERMUX_CLIPBOARD_SET = _find_in_path("termux-clipboard-set", PATH)
TERMUX_BATTERY_STATUS = _find_in_path("termux-battery-status", PATH)
TERMUX_FINGERPRINT = _find_in_path("termux-fingerprint", PATH)
TERMUX_VIBRATE = _find_in_path("termux-vibrate", PATH)
TERMUX_MEDIA_PLAYER = _find_in_path("termux-media-player", PATH)
TERMUX_SENSOR = _find_in_path("termux-sensor", PATH)
ADB = _find_in_path("adb", PATH)
CURL = _find_in_path("curl", PATH)
SUDO = _find_in_path("sudo", PATH)
AD_START = os.path.join(SYSTEM_PATH, "start")
AD_STOP = os.path.join(SYSTEM_PATH, "stop")

__background_tasks = set()

def _create_bg_task(coro):
    task = asyncio.create_task(coro)
    __background_tasks.add(task)
    task.add_done_callback(__background_tasks.discard)

async def _run(cmd):
    if not isinstance(cmd, str):
        cmd = shlex.join(cmd)
    proc = await asyncio.create_subprocess_shell(
        cmd,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE)
    stdout, stderr = await proc.communicate()
    return proc, stdout, stderr

async def _shell(cmd, *, stdin = True, stdout = True, stderr = True):
    if not isinstance(cmd, str):
        cmd = shlex.join(cmd)
    proc = await asyncio.create_subprocess_shell(
        cmd,
        stdin=asyncio.subprocess.PIPE if stdin else asyncio.subprocess.DEVNULL,
        stdout=asyncio.subprocess.PIPE if stdout else asyncio.subprocess.DEVNULL,
        stderr=asyncio.subprocess.PIPE if stderr else asyncio.subprocess.DEVNULL,
    )
    return proc
