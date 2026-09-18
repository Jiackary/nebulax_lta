import asyncio
L=asyncio.Lock()
async def contend():
    async def hold():
        async with L: await asyncio.sleep(0.05)
    await asyncio.gather(hold(), hold())
async def nocontend():
    async with L: pass
asyncio.run(nocontend()); asyncio.run(nocontend()); print("uncontended across loops ok")
asyncio.run(contend()); print("contended loop1 ok")
try: asyncio.run(contend()); print("contended loop2 ok")
except RuntimeError as e: print("loop2:", e)
