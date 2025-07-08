import asyncio
import time 

async def async_gen():
    for i in range(1000000):
        await asyncio.sleep(0.0000001)  # 비동기 처리
        yield i  # 값을 보내줌

def async_gen2():
    for i in range(1000000):
        time.sleep(0.0000001)  # 비동기 처리
        yield i  # 값을 보내줌

async def main():
    start = time.time()
    async for x in async_gen():
        pass
    end = time.time() 
    print(end - start)

def main2():
    start = time.time()
    for x in async_gen2():
        pass
    end = time.time() 
    print(end - start)
    
asyncio.run(main())
print() 
main2()