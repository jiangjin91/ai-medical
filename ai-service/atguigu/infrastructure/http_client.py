"""

定义HTTP客户端(异步)

"""
import asyncio

from httpx import AsyncClient

http_client: AsyncClient | None = None

def init_http_client():
    """
    初始化
    :return:
    """
    global http_client
    http_client = AsyncClient(timeout=120, trust_env=False) # 参数作用：不用关心代理。

async def disposed_http_client():
    """
    释放资源
    :return:
    """
    await http_client.aclose()

async def main_test():
    init_http_client()

    res = await http_client.get("http://192.168.10.130:18081/orders/A20260408002")
    print(res.json())

    data = res.json()["data"]
    print(data)

if __name__ == '__main__':
    asyncio.run(main_test())