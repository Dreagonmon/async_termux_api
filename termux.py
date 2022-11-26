import asyncio, os, uuid, shlex, atexit, json
from typing import Optional, MutableSet, Callable, Coroutine
ActionCallback = Callable[[], Coroutine]
GROUP_NUMBER_INPUT = "_number_input_"
ACTION_CLICK = "click"
ACTION_DELETE = "delete"
ACTION_BUTTON1 = "button1"
ACTION_BUTTON2 = "button2"
ACTION_BUTTON3 = "button3"
ACTION_MEDIA_PLAY = "media_play"
ACTION_MEDIA_PAUSE = "media_pause"
ACTION_MEDIA_NEXT = "media_next"
ACTION_MEDIA_PREVIOUS = "media_previous"
async def NO_OP(): pass
BRACE_OPEN = b"{"[0]
BRACE_CLOSE = b"}"[0]

def _is_in_termux():
    return os.environ.get("TMPDIR", "/root").startswith("/data/data/com.termux")

def _find_in_path(file, path=None):
    if path is None:
        path = os.environ['PATH']
    paths = path.split(os.pathsep)
    for p in paths:
        for f in os.listdir(p):
            if f != file: continue
            f_path = os.path.join(p, file)
            if os.path.isfile(f_path):
                return f_path
    return None
TERMUX_ROOTDIR = "/data/data/com.termux/files"
TERMUX_HOMEDIR = os.path.join(TERMUX_ROOTDIR, "home")
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

async def media_play(file: Optional[str] = None):
    args = [TERMUX_MEDIA_PLAYER, "play"]
    if isinstance(file, str):
        args.append(file)
    await _run(args)

async def media_pause():
    await _run([TERMUX_MEDIA_PLAYER, "pause"])

async def media_stop():
    await _run([TERMUX_MEDIA_PLAYER, "stop"])

async def media_info():
    res = await _run([TERMUX_MEDIA_PLAYER, "info"])
    result = res[1].decode("utf8").rstrip("\r\n") if res[1] else ""
    info = {}
    for line in result.splitlines():
        inx = line.find(":")
        if inx < 0:
            continue
        param = line[:inx].lower().replace(" ", "_")
        if param == "current_position":
            value = tuple(line[inx+2:].split(" / "))
        else:
            value = line[inx+2:]
        info[param] = value
    return info

async def sensor_list():
    res = await _run([TERMUX_SENSOR, "-l"])
    result = res[1].decode("utf8") if res[1] else "{}"
    return json.loads(result).get("sensors", [])

class Notification:
    def __init__(self, n_id:int, content:str, title:str="", *, group:str="", priority:str="", n_type:str="", alert_once:bool=False, ongoing:bool=False, sound:bool=False, image_path:str="", icon:str="", vibrate:str=""):
        """Notification item.
        - n_id: notification id (will overwrite any previous notification with the same id)
        - content: content to show in the notification
        - title: notification title to show (default "", not set)
        - group: notification group (notifications with the same group are shown together) (default "", not set)
        - priority: notification priority (high/low/max/min/default) (default "", not set)
        - n_type: notification style to use (default/media) (default "", not set, some system may ignore this)
        - alert_once: do not alert when the notification is edited (default False, some system may ignore this)
        - ongoing: pin the notification (default False)
        - sound: play a sound with the notification (default False, some system may ignore this)
        - image_path: absolute path to an image which will be shown in the notification (default "", not set)"
        - icon: set the icon that shows up in the status bar. View available icons at https://material.io/resources/icons/ (default "", not set, use default icon "event_note", system like "MIUI" show the icon incorrectly)
        - vibrate: vibrate pattern, comma separated as in "500,1000,200" (default "", not set, some system may ignore this)
        """
        self.n_id = n_id
        self.content = content
        self.title = title
        self.group = group
        self.priority = priority
        self.n_type = n_type
        self.alert_once = alert_once
        self.ongoing = ongoing
        self.sound = sound
        self.image_path = image_path
        self.icon = icon
        self.vibrate = vibrate
        self.button1: str = ""
        self.button2: str = ""
        self.button3: str = ""
        self.action_button1: ActionCallback = NO_OP
        self.action_button2: ActionCallback = NO_OP
        self.action_button3: ActionCallback = NO_OP
        self.action_click: ActionCallback = NO_OP
        self.action_delete: ActionCallback = NO_OP
        self.action_media_play: ActionCallback = NO_OP
        self.action_media_pause: ActionCallback = NO_OP
        self.action_media_next: ActionCallback = NO_OP
        self.action_media_previous: ActionCallback = NO_OP
        self._flag = asyncio.Event()
        self._result: Optional[str] = None
    
    def set_click_action(self, action_callback: ActionCallback):
        self.action_click = action_callback
    
    def set_delete_action(self, action_callback: ActionCallback):
        self.action_delete = action_callback

    def set_media_play_action(self, action_callback: ActionCallback):
        self.action_media_play = action_callback
    
    def set_media_pause_action(self, action_callback: ActionCallback):
        self.action_media_pause = action_callback
    
    def set_media_next_action(self, action_callback: ActionCallback):
        self.action_media_next = action_callback
    
    def set_media_next_action(self, action_callback: ActionCallback):
        self.action_media_next = action_callback
    
    def set_button1(self, button_text: str, action_callback: ActionCallback = NO_OP):
        if not button_text:
            self.button1 = ""
            self.action_button1 = NO_OP
        self.button1 = button_text
        self.action_button1 = action_callback
    
    def set_button2(self, button_text: str, action_callback: ActionCallback = NO_OP):
        if not button_text:
            self.button2 = ""
            self.action_button2 = NO_OP
        self.button2 = button_text
        self.action_button2 = action_callback
    
    def set_button3(self, button_text: str, action_callback: ActionCallback = NO_OP):
        if not button_text:
            self.button3 = ""
            self.action_button3 = NO_OP
        self.button3 = button_text
        self.action_button3 = action_callback
    
    def __eq__(self, other: object) -> bool:
        if isinstance(other, Notification):
            return self.n_id == other.n_id
        return False

    def __hash__(self) -> int:
        return hash(self.n_id)

class NotificationManager:
    """Termux Notification API"""
    def __init__(self, init_nid = 0):
        """__init__"""
        self.socketpath = os.path.abspath(os.path.join(TMPDIR, "termux-notification-callback-"+str(uuid.uuid4())+".sock"))
        self.server: Optional[asyncio.Server] = None
        self.notification_set: MutableSet[Notification] = set()
        self._nid: int = init_nid
        atexit.register(self._on_exit_task)
    
    async def send_notification(self, notification_item: Notification):
        self.notification_set.discard(notification_item)
        self.notification_set.add(notification_item)
        cmd = self._notification_cmd(notification_item)
        # print(cmd)
        await _run(cmd)
    
    async def send_notification_wait(self, notification_item: Notification):
        _create_bg_task(self.send_notification(notification_item))
        await notification_item._flag.wait()
        return notification_item._result
    
    async def remove_notification(self, notification_item: Notification):
        self.notification_set.discard(notification_item)
        await _run([TERMUX_NOTIFICATION_REMOVE, str(notification_item.n_id)])

    async def remove_all_notifications(self):
        await asyncio.gather(*[_run([TERMUX_NOTIFICATION_REMOVE, str(n.n_id)]) for n in self.notification_set])

    async def start_callback_server(self):
        self.server = await asyncio.start_unix_server(self._callback_server, self.socketpath, start_serving=False)
        await self.server.start_serving()

    async def _callback_server(self, reader, writer):
        method, http_path, http_version = (await reader.readline()).decode("utf8").split(" ")
        # ignore header
        n_id, n_act = http_path.split(":")
        n_id = int(n_id[1:])
        # print(n_id, n_act)
        writer.write("HTTP/1.1 200 OK\r\n\r\nok".encode("utf8"))
        await writer.drain()
        writer.close()
        await self._on_action_callback(n_id, n_act)
    
    async def _on_action_callback(self, nid, action):
        for n in self.notification_set:
            if n.n_id == nid:
                break
        else: return # not found, do nothing
        if action == ACTION_CLICK and n.action_click: _create_bg_task(n.action_click())
        elif action == ACTION_DELETE and n.action_delete: _create_bg_task(n.action_delete())
        elif action == ACTION_MEDIA_PLAY and n.action_media_play: _create_bg_task(n.action_media_play())
        elif action == ACTION_MEDIA_PAUSE and n.action_media_pause: _create_bg_task(n.action_media_pause())
        elif action == ACTION_MEDIA_NEXT and n.action_media_next: _create_bg_task(n.action_media_next())
        elif action == ACTION_MEDIA_PREVIOUS and n.action_media_previous: _create_bg_task(n.action_media_previous())
        elif action == ACTION_BUTTON1 and n.action_button1: _create_bg_task(n.action_button1())
        elif action == ACTION_BUTTON2 and n.action_button2: _create_bg_task(n.action_button2())
        elif action == ACTION_BUTTON3 and n.action_button3: _create_bg_task(n.action_button3())
        n._result = action
        n._flag.set()
        if action in [ACTION_CLICK, ACTION_DELETE]:
            self.notification_set.discard(n)
    
    def is_serving(self):
        return self.server.is_serving() if self.server else False

    def stop_callback_server(self):
        self.server.close()

    def new_nid(self):
        self._nid += 1
        return self._nid

    def _curl_cmd(self, action_id):
        return shlex.join([CURL, "-GET", "--unix-socket", self.socketpath, f"http://localhost/{action_id}"])

    def _notification_cmd(self, n: Notification):
        args = [TERMUX_NOTIFICATION]
        args.extend(["--id", str(n.n_id)])
        args.extend(["--content", n.content])
        if n.title: args.extend(["--title", n.title])
        if n.group: args.extend(["--group", n.group])
        if n.priority: args.extend(["--priority", n.priority])
        if n.n_type: args.extend(["--type", n.n_type])
        if n.alert_once: args.append("--alert-once")
        if n.ongoing: args.append("--ongoing")
        if n.sound: args.append("--sound")
        if n.image_path: args.extend(["--image-path", n.image_path])
        if n.icon: args.extend(["--icon", n.icon])
        if n.vibrate: args.extend(["--vibrate", n.vibrate])
        if n.action_click or not n.ongoing: args.extend(["--action", self._curl_cmd(f"{n.n_id}:{ACTION_CLICK}")])
        if n.action_delete or not n.ongoing: args.extend(["--on-delete", self._curl_cmd(f"{n.n_id}:{ACTION_DELETE}")])
        if n.n_type == "media":
            if n.action_media_play: args.extend(["--media-play", self._curl_cmd(f"{n.n_id}:{ACTION_MEDIA_PLAY}")])
            if n.action_media_pause: args.extend(["--media-pause", self._curl_cmd(f"{n.n_id}:{ACTION_MEDIA_PAUSE}")])
            if n.action_media_next: args.extend(["--media-next", self._curl_cmd(f"{n.n_id}:{ACTION_MEDIA_NEXT}")])
            if n.action_media_previous: args.extend(["--media-previous", self._curl_cmd(f"{n.n_id}:{ACTION_MEDIA_PREVIOUS}")])
        if n.button1:
            args.extend(["--button1", n.button1])
            args.extend(["--button1-action", self._curl_cmd(f"{n.n_id}:{ACTION_BUTTON1}")])
        if n.button2:
            args.extend(["--button2", n.button2])
            args.extend(["--button2-action", self._curl_cmd(f"{n.n_id}:{ACTION_BUTTON2}")])
        if n.button3:
            args.extend(["--button3", n.button3])
            args.extend(["--button3-action", self._curl_cmd(f"{n.n_id}:{ACTION_BUTTON3}")])
        if n.title: args.extend(["--title", n.title])
        return shlex.join(args)
    
    def _on_exit_task(self):
        # print("cleaning all notifications...")
        try:
            if self.is_serving():
                self.stop_callback_server()
        except: pass
        asyncio.run(self.remove_all_notifications())

class Sensor:
    def __init__(self, *sensors: str, delay_ms = 1000):
        self.sensors = sensors
        self.delay = delay_ms
        self.proc: Optional[asyncio.subprocess.Process] = None
    
    async def read_once(self):
        args = [TERMUX_SENSOR, "-s", ",".join(self.sensors), "-d", str(self.delay), "-n", "1"]
        res = await _run(args)
        result = res[1].decode("utf8").rstrip("\r\n") if res[1] else "{}"
        return json.loads(result)
    
    async def __aenter__(self):
        args = [TERMUX_SENSOR, "-s", ",".join(self.sensors), "-d", str(self.delay)]
        cmd = shlex.join(args)
        self.proc = await asyncio.create_subprocess_shell(
            cmd,
            stdin=asyncio.subprocess.PIPE,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE)
        return SensorReader(self.proc.stdout)
    
    async def __aexit__(self, type, value, trace):
        if self.proc:
            print("    Cleaning Sensor...")
            self.proc.stdin.write_eof()
            await self.proc.stdin.drain()
            self.proc.kill()
            args = [TERMUX_SENSOR, "-c"]
            await _run(args)
            await self.proc.wait()
            self.proc.stdin.close()
            self.proc = None

class SensorReader:
    def __init__(self, reader: asyncio.StreamReader):
        self.reader = reader
        self.buffer = bytearray()
        self.level = 0
    
    def __aiter__(self):
        return self
    
    async def __anext__(self):
        while True:
            b = await self.reader.read(1)
            if len(b) != 1:
                raise StopAsyncIteration
            byt = b[0]
            self.buffer.append(byt)
            if byt == BRACE_OPEN:
                self.level += 1
            elif byt == BRACE_CLOSE:
                self.level -= 1
                if self.level == 0:
                    data = json.loads(self.buffer.decode("utf8"))
                    self.buffer.clear()
                    return data


# ADB Functions Below

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

async def adb_shell(cmds: list[str]):
    args = [ADB, "shell"]
    args.extend(cmds)
    res = await _run(args)
    return res[1].decode("utf8") if res[1] else ""

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

# Test Function Below

async def __main():
    nm = NotificationManager()
    await nm.start_callback_server()
    if not await adb_try_connect(nm, 5555):
        print("adb配对连接失败, 请重试")
        return
    n = Notification(nm.new_nid(), "点击这条通知，开始程序", "Yay!")
    n.set_button1("Hello")
    n.set_button2("Dragon")
    n.set_button3("Wyvern")
    result = await nm.send_notification_wait(n)
    if result == ACTION_DELETE:
        return
    await toast("好耶, 我们不需要root权, 就可以在termux环境下使用adb连接本机了!", short=True)
    await adb_send_keyevent(3) # Home key
    print(await sensor_list())
    sensor = Sensor("linear_acc", "rot_vec", delay_ms=200)
    async with sensor as reader:
        # only one sensor object can read at the same time
        count = 0
        async for data in reader:
            print(data)
            count += 1
            if count >= 10:
                break
    nm.stop_callback_server()

if __name__ == "__main__":
    try:
        asyncio.run(__main())
    except KeyboardInterrupt: pass
    except:
        import traceback
        traceback.print_exc()
