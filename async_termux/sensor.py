from ._task import _run
from ._task import TERMUX_SENSOR
from typing import Optional
import asyncio
import shlex
import json

BRACE_OPEN = b"{"[0]
BRACE_CLOSE = b"}"[0]

async def sensor_list():
    res = await _run([TERMUX_SENSOR, "-l"])
    result = res[1].decode("utf8") if res[1] else "{}"
    return json.loads(result).get("sensors", [])

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
            stderr=asyncio.subprocess.DEVNULL)
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
