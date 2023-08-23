from typing import Optional, MutableSet, Callable, Coroutine
from ._task import _run, _create_bg_task
from ._task import TMPDIR, TERMUX_NOTIFICATION_REMOVE, TERMUX_NOTIFICATION, CURL
import atexit
import asyncio
import os
import shlex
import uuid
ActionCallback = Callable[[], Coroutine]

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
        """ Send notify """
        self.notification_set.discard(notification_item)
        self.notification_set.add(notification_item)
        cmd = self._notification_cmd(notification_item)
        await _run(cmd)
    
    async def send_notification_wait(self, notification_item: Notification):
        """ Send notify and wait for action result, e.g. ACTION_CLICK """
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
    
    async def __aenter__(self):
        await self.start_callback_server()
        return self
    
    async def __aexit__(self, type, value, trace):
        self.stop_callback_server()
