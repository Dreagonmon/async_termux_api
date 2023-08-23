from ._task import _run
from ._task import TERMUX_TOAST, TERMUX_VIBRATE, TERMUX_CLIPBOARD_GET, TERMUX_CLIPBOARD_SET
from ._task import TERMUX_BATTERY_STATUS, TERMUX_FINGERPRINT
import json
from typing import Callable, Coroutine
ActionCallback = Callable[[], Coroutine]

async def toast(msg, background:str="gray", color:str="white", position:str="middle", short:bool=False):
    """Show text in a Toast (a transient popup).
    - background: set background color (default: gray)
    - color: set text color (default: white)
    - position: set position of toast: [top, middle, or bottom] (default: middle)
    - short: only show the toast for a short while
    """
    args = [TERMUX_TOAST]
    args.extend(["-b", background])
    args.extend(["-c", color])
    args.extend(["-g", position])
    if short:
        args.append("-s")
    args.append(msg)
    await _run(args)

async def vibrate(duration = 1000, force = False):
    args = [TERMUX_VIBRATE, "-d", str(duration)]
    if force:
        args.append("-f")
    await _run(args)

async def get_clipboard():
    """ get clipboard, may not work """
    res = await _run([TERMUX_CLIPBOARD_GET])
    return res[1].decode("utf8").rstrip("\r\n") if res[1] else ""

async def set_clipboard(text):
    await _run([TERMUX_CLIPBOARD_SET, text])

async def battery_status():
    res = await _run([TERMUX_BATTERY_STATUS])
    result = res[1].decode("utf8") if res[1] else "{}"
    return json.loads(result)

async def check_fingerprint():
    res = await _run([TERMUX_FINGERPRINT])
    result = res[1].decode("utf8") if res[1] else ""
    return result.find("AUTH_RESULT_SUCCESS") >= 0
