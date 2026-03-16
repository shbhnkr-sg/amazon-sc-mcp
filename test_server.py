"""
End-to-end smoke test for the Amazon Seller Central MCP server.

Usage:
    python test_server.py                          # test localhost:8000
    python test_server.py http://192.168.0.150:3100 # test remote
"""

import sys
import json
import asyncio
from mcp import ClientSession
from mcp.client.streamable_http import streamablehttp_client


async def run_tests(base_url: str):
    url = f"{base_url}/mcp"
    passed = 0
    failed = 0

    print(f"Testing MCP server at {url}\n")

    try:
        async with streamablehttp_client(url) as (read_stream, write_stream, _):
            async with ClientSession(read_stream, write_stream) as session:
                # Test 1: Initialize
                print("1. Initialize...", end=" ")
                result = await session.initialize()
                server_name = result.serverInfo.name if result.serverInfo else "unknown"
                assert server_name == "amazon-seller-central", f"got {server_name}"
                print(f"OK — server: {server_name}, protocol: {result.protocolVersion}")
                passed += 1

                # Test 2: List tools
                print("2. List tools...", end=" ")
                tools_result = await session.list_tools()
                tool_count = len(tools_result.tools)
                assert tool_count >= 40, f"expected >= 40 tools, got {tool_count}"
                print(f"OK — {tool_count} tools")
                for t in tools_result.tools[:5]:
                    print(f"   - {t.name}")
                if tool_count > 5:
                    print(f"   ... and {tool_count - 5} more")
                passed += 1

                # Test 3: Verify tool schemas have proper structure
                print("3. Schema check...", end=" ")
                sample_tool = next((t for t in tools_result.tools if t.name == "searchOrders"), None)
                assert sample_tool is not None, "searchOrders tool not found"
                schema = sample_tool.inputSchema
                assert "properties" in schema, "missing properties in schema"
                assert schema.get("type") == "object", "schema type not object"
                print(f"OK — searchOrders has {len(schema['properties'])} params")
                passed += 1

                # Test 4: Verify tool annotations
                print("4. Annotations...", end=" ")
                get_tool = next((t for t in tools_result.tools if t.name == "searchOrders"), None)
                assert get_tool.annotations is not None, "missing annotations"
                assert get_tool.annotations.readOnlyHint is True, "GET tool should be readOnly"
                assert get_tool.annotations.openWorldHint is True, "should be openWorld"
                del_tool = next((t for t in tools_result.tools if t.name == "deleteListingsItem"), None)
                if del_tool:
                    assert del_tool.annotations.destructiveHint is True, "DELETE should be destructive"
                    print("OK — GET=readOnly, DELETE=destructive, openWorld=True")
                else:
                    print("OK — GET=readOnly, openWorld=True (no DELETE tool to verify)")
                passed += 1

                # Test 5: Call a tool (expect auth error — proves MCP dispatch works)
                print("5. Call searchOrders...", end=" ")
                try:
                    call_result = await session.call_tool("searchOrders", {"MarketplaceIds": "ATVPDKIKX0DER"})
                    content = call_result.content[0].text
                    assert content, "empty response"
                    if call_result.isError:
                        print(f"OK — got expected error: {content[:80]}")
                    else:
                        data = json.loads(content)
                        print(f"OK — got response: {list(data.keys())}")
                    passed += 1
                except Exception as e:
                    print(f"FAIL: {e}")
                    failed += 1

    except ConnectionRefusedError:
        print(f"\nFAIL: Cannot connect to {url}")
        failed += 1
    except BaseException as e:
        print(f"FAIL: {e}")
        failed += 1

    print(f"\n{'=' * 40}")
    print(f"Results: {passed} passed, {failed} failed")
    return failed == 0


if __name__ == "__main__":
    base_url = sys.argv[1] if len(sys.argv) > 1 else "http://localhost:8000"
    ok = asyncio.run(run_tests(base_url))
    sys.exit(0 if ok else 1)
