import asyncio, os, uuid, shlex, atexit
from typing import Optional, MutableSet, Callable, Coroutine
ActionCallback = Optional[Callable[[], Coroutine]]
ACTION_CLICK = "click"
ACTION_DELETE = "delete"
ACTION_BUTTON1 = "button1"
ACTION_BUTTON2 = "button2"
ACTION_BUTTON3 = "button3"
ACTION_MEDIA_PLAY = "media_play"
ACTION_MEDIA_PAUSE = "media_pause"
ACTION_MEDIA_NEXT = "media_next"
ACTION_MEDIA_PREVIOUS = "media_previous"

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

async def get_clipboard():
    res = await _run([TERMUX_CLIPBOARD_GET])
    return res[1].decode("utf8") if res[1] else ""

async def set_clipboard(text):
    await _run([TERMUX_CLIPBOARD_SET, text])

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
        self.action_button1: ActionCallback = None
        self.action_button2: ActionCallback = None
        self.action_button3: ActionCallback = None
        self.action_click: ActionCallback = None
        self.action_delete: ActionCallback = None
        self.action_media_play: ActionCallback = None
        self.action_media_pause: ActionCallback = None
        self.action_media_next: ActionCallback = None
        self.action_media_previous: ActionCallback = None
    
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
    
    def set_button1(self, button_text: str, action_callback: ActionCallback):
        if button_text == "" or action_callback == None:
            self.button1 = ""
            self.action_button1 = None
        self.button1 = button_text
        self.action_button1 = action_callback
    
    def set_button2(self, button_text: str, action_callback: ActionCallback):
        if button_text == "" or action_callback == None:
            self.button2 = ""
            self.action_button2 = None
        self.button2 = button_text
        self.action_button2 = action_callback
    
    def set_button3(self, button_text: str, action_callback: ActionCallback):
        if button_text == "" or action_callback == None:
            self.button3 = ""
            self.action_button3 = None
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
    def __init__(self):
        """__init__"""
        self.socketpath = os.path.abspath(os.path.join(TMPDIR, "termux-notification-callback-"+str(uuid.uuid4())+".sock"))
        self.server: Optional[asyncio.Server] = None
        self.notification_set: MutableSet[Notification] = set()
        self._nid: int = 0
        atexit.register(self._on_exit_task)
    
    async def send_notification(self, notification_item: Notification):
        self.notification_set.discard(notification_item)
        self.notification_set.add(notification_item)
        cmd = self._notification_cmd(notification_item)
        # print(cmd)
        await _run(cmd)
    
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
        await self._on_action_callback(n_id, n_act)
        writer.write("HTTP/1.1 200 OK\r\n\r\nok".encode("utf8"))
        await writer.drain()
        writer.close()
    
    async def _on_action_callback(self, nid, action):
        for n in self.notification_set:
            if n.n_id == nid:
                break
        else: return # not found, do nothing
        if action == ACTION_CLICK and n.action_click: asyncio.create_task(n.action_click())
        elif action == ACTION_DELETE and n.action_delete: asyncio.create_task(n.action_delete())
        elif action == ACTION_MEDIA_PLAY and n.action_media_play: asyncio.create_task(n.action_media_play())
        elif action == ACTION_MEDIA_PAUSE and n.action_media_pause: asyncio.create_task(n.action_media_pause())
        elif action == ACTION_MEDIA_NEXT and n.action_media_next: asyncio.create_task(n.action_media_next())
        elif action == ACTION_MEDIA_PREVIOUS and n.action_media_previous: asyncio.create_task(n.action_media_previous())
        elif action == ACTION_BUTTON1 and n.action_button1: asyncio.create_task(n.action_button1())
        elif action == ACTION_BUTTON2 and n.action_button2: asyncio.create_task(n.action_button2())
        elif action == ACTION_BUTTON3 and n.action_button3: asyncio.create_task(n.action_button3())
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
        if n.button1: args.extend(["--button1", n.button1])
        if n.button2: args.extend(["--button2", n.button2])
        if n.button3: args.extend(["--button3", n.button3])
        if n.action_button1: args.extend(["--button1-action", self._curl_cmd(f"{n.n_id}:{ACTION_BUTTON1}")])
        if n.action_button2: args.extend(["--button2-action", self._curl_cmd(f"{n.n_id}:{ACTION_BUTTON2}")])
        if n.action_button3: args.extend(["--button3-action", self._curl_cmd(f"{n.n_id}:{ACTION_BUTTON3}")])
        if n.title: args.extend(["--title", n.title])
        return shlex.join(args)
    
    def _on_exit_task(self):
        # print("cleaning all notifications...")
        try:
            if self.is_serving():
                self.stop_callback_server()
        except: pass
        asyncio.run(self.remove_all_notifications())

DEFAULT_TMPDIR = "/data/data/com.termux/files/usr/tmp"
DEFAULT_PATH = "/data/data/com.termux/files/usr/bin"
TMPDIR = os.environ.get("TMPDIR", DEFAULT_TMPDIR) if _is_in_termux() else DEFAULT_TMPDIR
PATH = os.environ.get("PATH", DEFAULT_PATH) if _is_in_termux() else DEFAULT_PATH
TERMUX_TOAST = _find_in_path("termux-toast", PATH)
TERMUX_NOTIFICATION = _find_in_path("termux-notification", PATH)
TERMUX_NOTIFICATION_REMOVE = _find_in_path("termux-notification-remove", PATH)
TERMUX_CLIPBOARD_GET = _find_in_path("termux-clipboard-get", PATH)
TERMUX_CLIPBOARD_SET = _find_in_path("termux-clipboard-set", PATH)
CURL = _find_in_path("curl", PATH)

# Test Function Below

async def __main():
    nm = NotificationManager()
    await nm.start_callback_server()
    async def __test_click():
        await toast("Exit!")
        nm.stop_callback_server()
    n = Notification(nm.new_nid(), "Hello Notification!\nSecond Line", "from termux", ongoing=True)
    async def __cpb():
        await toast(await get_clipboard())
    n.set_button1("EXIT", __test_click)
    n.set_button2("读取剪贴板", __cpb)
    await nm.send_notification(n)
    while nm.is_serving():
        await asyncio.sleep(0.5)

if __name__ == "__main__":
    try:
        asyncio.run(__main())
    except KeyboardInterrupt: pass