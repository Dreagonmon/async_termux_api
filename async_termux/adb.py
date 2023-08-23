from ._task import _run, _shell
from ._task import ADB, SUDO, AD_START, AD_STOP
from .notify import NotificationManager, Notification
from typing import Optional
import asyncio

GROUP_NUMBER_INPUT = "_number_input_"

async def input_number_in_notification(nm: NotificationManager ,title="Input a number") -> Optional[int]:
    hint = "swipe to cancel, click to confirm.\n"
    data = {
        "num": 0,
        "numstr": "",
        "confirmed": False,
    }
    flag = asyncio.Event()
    async def __del():
        data["num"] = 0
        data["numstr"] = ""
        data["confirmed"] = True
        flag.set()
    async def __add1():
        data["num"] += 1
        data["num"] %= 10
        flag.set()
    async def __add3():
        data["num"] += 3
        data["num"] %= 10
        flag.set()
    async def __next():
        data["numstr"] += str(data["num"])
        data["num"] = 0
        flag.set()
    async def __click():
        data["confirmed"] = True
        flag.set()
    n = Notification(nm.new_nid(), hint, title, group=GROUP_NUMBER_INPUT, sound=False, ongoing=False)
    n.set_button1("+1", __add1)
    n.set_button2("+3", __add3)
    n.set_button3("Next Digit", __next)
    n.set_delete_action(__del)
    n.set_click_action(__click)
    while not data["confirmed"]:
        flag.clear()
        n.content = hint + \
            f"Current Digit: {data['num']}\n" + \
            f"Total Number: {data['numstr'] if len(data['numstr']) > 0 else 'empty' }\n" + \
            ""
        await nm.send_notification(n)
        await flag.wait()
    return int(data["numstr"]) if len(data["numstr"]) > 0 else None

async def adb_pair_local(nm: NotificationManager):
    code = await input_number_in_notification(nm, "Pairing Code")
    port = await input_number_in_notification(nm, "Pairing Port")
    args = [ADB, "pair", f"127.0.0.1:{port}", f"{code}"]
    res = await _run(args)
    result = res[1].decode("utf8").lower() if res[1] else ""
    return result.find("success") >= 0

async def adb_connect_local(nm: NotificationManager = None, port: Optional[int] = None):
    assert nm != None or port != None, "Must provide a port, or a NotificationManager to input a port."
    if not isinstance(port, int):
        port = await input_number_in_notification(nm, "Wireless Debug Port")
    args = [ADB, "connect", f"127.0.0.1:{port}"]
    res = await _run(args)
    result = res[1].decode("utf8").lower() if res[1] else ""
    return result.find("connected") >= 0

async def adb_disconnect_all():
    args = [ADB, "disconnect"]
    await _run(args)

async def adb_shell_exec(*cmds: str):
    args = [ADB, "shell"]
    args.extend(cmds)
    res = await _run(args)
    return res[1].decode("utf8") if res[1] else ""

async def adb_shell(*cmds: str, stdin = True, stdout = True, stderr = True):
    args = [ADB, "shell"]
    args.extend(cmds)
    proc = await _shell(args, stdin=stdin, stdout=stdout, stderr=stderr)
    return proc

async def adb_start_wireless_adb(port = 5555, reconnect = True):
    args = [ADB, "tcpip", str(port)]
    await _run(args)
    if reconnect:
        await adb_disconnect_all()
        await adb_connect_local(port=port)

async def adb_start_wireless_adb_root(port = 5555, reconnect = True):
    args = [SUDO, "setprop", "service.adb.tcp.port", str(port)]
    await _run(args)
    args = [SUDO, AD_STOP, "adbd"]
    await _run(args)
    args = [SUDO, AD_START, "adbd"]
    await _run(args)
    await asyncio.sleep(0.5)
    if reconnect:
        await adb_disconnect_all()
        await adb_connect_local(port=port)

async def adb_is_connect():
    args = [ADB, "shell", "echo", "ok"]
    res = await _run(args)
    result = res[1].decode("utf8").strip() if res[1] else ""
    return result == "ok"

async def adb_try_connect(nm: NotificationManager, port = 5555):
    """ Try to pair and connect, and using local port 'port' """
    connected = await adb_is_connect()
    if connected:
        # already connected
        return True
    await adb_disconnect_all()
    await adb_start_wireless_adb_root(port, False)
    connected = await adb_connect_local(port=port)
    if connected:
        # can be simple connected
        return True
    n = Notification(nm.new_nid(), "点击开始连接adb无线调试的流程, 你将要输入三个数字", "wait...")
    await nm.send_notification_wait(n)
    await asyncio.sleep(1)
    await adb_pair_local(nm)
    connected = await adb_connect_local(nm)
    if not connected:
        return False
    await adb_start_wireless_adb(port)
    return True

async def adb_send_keyevent(key_code: int):
    """ Full Keycode: https://developer.android.com/reference/android/view/KeyEvent """
    await adb_shell(["input", "keyevent", str(key_code)])
