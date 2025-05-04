# Mahlkönig X54 Client

A Python client for the Mahlkönig X54 coffee grinder with WebSocket API support.

## Installation

```bash
uv add mahlkoenig
```

or

```bash
pip install mahlkoenig
```

## Features

- Asynchronous WebSocket communication with the X54 grinder
- API coverage for common grinder operations
- Type-safe request and response handling
- Automatic connection management and authentication
- Easy access to grinder status, recipes, and statistics

## Quick Start

```python
import asyncio
from mahlkoenig import Grinder, AutoSleepTimePreset

async def main():
    # Connect to your grinder (default password is empty)
    async with Grinder(host="10.10.10.10") as client:
        # Get machine information
        machine_info = await client.request_machine_info()
        print(f"Connected to X54 grinder: {machine_info.serial_no}")
        print(f"Software version: {machine_info.sw_version}")
        
        # Get all recipes
        recipes = await client.request_recipe_list()
        for recipe_no, recipe in recipes.items():
            print(f"Recipe {recipe_no}: {recipe.name} - {recipe.grind_time}")
        
        # Set auto sleep time to 10 minutes
        await client.set_auto_sleep_time(AutoSleepTimePreset.MIN_10)
        print(f"Set auto sleep time to 10min")
        
        # Get grinding statistics
        stats = await client.request_statistics()
        print(f"Total grinding shots: {stats.total_grind_shots}")
        print(f"Total grinding time: {stats.total_grind_time}")

if __name__ == "__main__":
    asyncio.run(main())
```

## API Reference

The Grinder class provides these main methods:

- `connect()` - Establishes connection to the grinder
- `close()` - Closes the connection
- `request_machine_info()` - Gets machine information
- `request_wifi_info()` - Gets WiFi settings
- `request_system_status()` - Gets current grinder status
- `request_recipe_list()` - Gets all programmed recipes
- `request_auto_sleep_time()` - Gets current auto-sleep setting
- `set_auto_sleep_time()` - Changes auto-sleep setting
- `request_statistics()` - Gets usage statistics

The client also supports context manager syntax for automatic connection management.

## Development

See [DEVELOP.md](./DEVELOP.md) for instruction on how to use [mitmproxy](https://mitmproxy.org/) to intercept the communication between the app and the grinder

## License

MIT
