"""Actual MCP SDK clients communicate with real subprocesses over stdio."""
import asyncio
import json
import os
from pathlib import Path
import sys
import tempfile
import unittest
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client


async def run_client(path, writer):
    env={**os.environ,"PEOPLE_MATCH_DB":str(path)}
    async with stdio_client(StdioServerParameters(command=sys.executable,args=["-m","people_match.server"],env=env)) as (read,write):
        async with ClientSession(read,write) as session:
            await session.initialize()
            listed=await session.list_tools()
            names={t.name for t in listed.tools}
            assert {"record_interaction","search_memory","get_person_history","undo_change"} <= names
            assert all(t.inputSchema.get("type")=="object" for t in listed.tools)
            if writer:
                response=await session.call_tool("record_interaction",{"name":"Fictional Riley","source_text":"Riley needs a PCB designer.","observations":[{"category":"need","text":"PCB design help","evidence":"needs a PCB designer"}],"account_urls":["https://example.com/riley"]})
                assert not response.isError,response
                return json.loads(response.content[0].text)
            response=await session.call_tool("search_memory",{"query":"PCB","category":"need","active_only":True})
            assert not response.isError,response
            if response.structuredContent is not None:
                data=response.structuredContent["result"]
            else:
                data=[json.loads(block.text) for block in response.content if block.type=="text"]
            assert data,data
            return data


class MCPTests(unittest.TestCase):
    def test_two_independent_clients_share_memory(self):
        with tempfile.TemporaryDirectory() as tmp:
            path=Path(tmp)/"memory.sqlite3"
            saved=asyncio.run(asyncio.wait_for(run_client(path,True),timeout=30))
            recalled=asyncio.run(asyncio.wait_for(run_client(path,False),timeout=30))
            self.assertTrue(saved["saved"])
            self.assertEqual(recalled[0]["person_id"],saved["person_id"])


if __name__=="__main__":unittest.main()
