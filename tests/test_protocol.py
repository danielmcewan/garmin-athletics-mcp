import os
import sys

import anyio
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client


def test_stdio_server_lists_only_read_tools(tmp_path) -> None:
    async def run() -> None:
        params = StdioServerParameters(
            command=sys.executable,
            args=["-m", "garmin_mcp.server"],
            env={**os.environ, "GARMIN_MCP_HOME": str(tmp_path)},
        )
        async with (
            stdio_client(params) as streams,
            ClientSession(*streams) as session,
        ):
            await session.initialize()
            tools = await session.list_tools()
            names = {tool.name for tool in tools.tools}
            assert "get_daily_health" in names
            assert "get_workout_details" in names
            assert "erase" not in names
            assert "login" not in names
            assert all("delete" not in name and "upload" not in name for name in names)

    anyio.run(run)
