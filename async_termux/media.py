from ._task import _run
from ._task import TERMUX_MEDIA_PLAYER
from typing import Optional

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
