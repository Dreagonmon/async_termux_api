from .notify import NotificationManager, Notification
from .notify import ACTION_DELETE
from .adb import adb_try_connect, adb_shell
import asyncio
# Test Function Below

async def __main():
    print("========")
    async with NotificationManager() as nm:
        if not await adb_try_connect(nm, 5555):
            print("adb配对连接失败, 请重试")
            return
        print("adb connected.")
        notify = Notification(nm.new_nid(), "Hello Dragon")
        await nm.send_notification(notify)
        proc = await adb_shell("ls", "/", stdin=False, stderr=False)
        while True:
            data = await proc.stdout.readline()
            print(data)
            if (len(data) <= 0):
                break
    print("========")

if __name__ == "__main__":
    try:
        asyncio.run(__main())
    except KeyboardInterrupt: pass
    except:
        import traceback
        traceback.print_exc()
