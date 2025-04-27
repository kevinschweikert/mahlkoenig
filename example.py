import asyncio
import logging

from zeroconf import ServiceStateChange, Zeroconf
from zeroconf.asyncio import AsyncZeroconf, AsyncServiceBrowser, AsyncServiceInfo

from mahlkoenig import Grinder


async def handle_service(zeroconf: Zeroconf, service_type: str, name: str):
    info = AsyncServiceInfo(service_type, name)
    if not await info.async_request(zeroconf, 500):
        print(f"[warning] no info for {name}")
        return

    host = info.server
    port = info.port
    print(f"[discovered] {host}:{port}")

    try:
        async with Grinder(host=host, port=port, password="test") as grinder:
            await grinder.request_machine_info()
            await grinder.request_wifi_info()
            await grinder.request_system_status()
            await grinder.request_auto_sleep_time()
            await grinder.request_recipe_list()
            await grinder.request_statistics()
            print("[machine_info]", grinder.machine_info)
            print("[system status]", grinder.system_status)
            print("[auto sleep time]", grinder.auto_sleep_time)
            print("[recipes]", grinder.recipes)
            print("[statistics]", grinder.statistics)
    except Exception as e:
        print(f"[error] {e}")


def on_service_state_change(
    zeroconf: Zeroconf,
    service_type: str,
    name: str,
    state_change: ServiceStateChange,
):
    if state_change is not ServiceStateChange.Added:
        return
    # schedule our async resolver in the loop
    asyncio.create_task(handle_service(zeroconf, service_type, name))


async def main():
    async_zc = AsyncZeroconf()
    services = ["_ws._tcp.local."]
    print(f"Browsing {services}, CTRL-C to exit…")
    browser = AsyncServiceBrowser(
        async_zc.zeroconf, services, handlers=[on_service_state_change]
    )
    try:
        # run forever until interrupted
        await asyncio.Event().wait()
    finally:
        await browser.async_cancel()
        await async_zc.async_close()


if __name__ == "__main__":
    logging.basicConfig(level=logging.DEBUG)
    asyncio.run(main())
