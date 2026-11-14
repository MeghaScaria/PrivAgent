"""
MCP client manager. The MCP client session objects are bound to the
asyncio event loop they were created in, and Streamlit's execution
model is synchronous. To bridge that cleanly, this module runs one
dedicated background thread with its own persistent event loop, opens
a stdio connection to each of the four MCP servers on that loop, and
exposes a synchronous call_tool() that dispatches into the background
loop and blocks for the result.

This is the only place in the codebase that speaks raw MCP protocol.
Everything else (agents/tools.py) calls the synchronous methods here.
"""
import asyncio
import json
import os
import sys
import threading
from contextlib import AsyncExitStack

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import get_default_environment, stdio_client

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

SERVERS = {
    "document": os.path.join(BASE_DIR, "mcp_servers", "document_server", "server.py"),
    "database": os.path.join(BASE_DIR, "mcp_servers", "database_server", "server.py"),
    "web": os.path.join(BASE_DIR, "mcp_servers", "web_server", "server.py"),
    "external": os.path.join(BASE_DIR, "mcp_servers", "external_server", "server.py"),
}

# Tools whose underlying return type is a single object (dict), not a
# list — FastMCP always serialises these as exactly one content block,
# so no special reconstruction is needed. Every other tool returns a
# list, and FastMCP serialises a list as one content block PER ITEM
# (including zero blocks for an empty list), which _call_tool_async
# below reconstructs back into a proper Python list.
SINGLE_OBJECT_TOOLS = {"retrieve_document", "send_result"}
TOOL_TO_SERVER = {
    "search_documents": "document",
    "retrieve_document": "document",
    "query_database": "database",
    "list_tables": "database",
    "search_web": "web",
    "send_result": "external",
    "get_transmission_log": "external",
}


START_TIMEOUT_ENV = "PRIVAGENT_MCP_START_TIMEOUT"
DEFAULT_START_TIMEOUT = 30


def start_timeout():
    """Seconds to wait for all MCP servers to connect. Default 30 (the
    original value); PRIVAGENT_MCP_START_TIMEOUT overrides it, e.g. on a
    slow or heavily loaded machine. Invalid or non-positive values are
    ignored."""
    try:
        value = float(os.environ.get(START_TIMEOUT_ENV, DEFAULT_START_TIMEOUT))
    except ValueError:
        return DEFAULT_START_TIMEOUT
    return value if value > 0 else DEFAULT_START_TIMEOUT


DATA_VERSION_ENV = "PRIVAGENT_DATA_VERSION"
INJECTION_FILE_ENV = "PRIVAGENT_INJECTION_FILE"   # WP6: planted prompt injections


def _server_env():
    """The stdio servers get a filtered environment from the MCP client, so
    the synthetic data version (V2_PLAN.md WP4: "v2_canary") must be passed
    through explicitly. Unset, nothing is added and the servers start
    exactly as in v1."""
    passed = {k: os.environ[k] for k in (DATA_VERSION_ENV, INJECTION_FILE_ENV) if os.environ.get(k)}
    if not passed:
        return {}
    return {"env": {**get_default_environment(), **passed}}


def server_identity(tool_name):
    """The MCP server a call to tool_name is routed to: its name and the
    server script (relative to the repo). Used by v2 send binding; it
    reads the same routing tables the client uses."""
    name = TOOL_TO_SERVER[tool_name]
    return {"server": name,
            "script": os.path.relpath(SERVERS[name], BASE_DIR).replace(os.sep, "/")}


class MCPClientManager:
    _instance = None
    _instance_lock = threading.Lock()

    def __init__(self):
        self._loop = None
        self._thread = None
        self._sessions = {}
        self._exit_stack = None
        self._started = threading.Event()
        self._start_error = None

    @classmethod
    def get_instance(cls):
        with cls._instance_lock:
            if cls._instance is None:
                cls._instance = MCPClientManager()
                cls._instance.start()
            return cls._instance

    def start(self):
        if self._thread is not None:
            return
        self._thread = threading.Thread(target=self._run_loop, daemon=True)
        self._thread.start()
        self._started.wait(timeout=start_timeout())
        if self._start_error:
            raise RuntimeError(f"Failed to start MCP servers: {self._start_error}")

    def _run_loop(self):
        self._loop = asyncio.new_event_loop()
        asyncio.set_event_loop(self._loop)
        try:
            self._loop.run_until_complete(self._connect_all())
            self._started.set()
            self._loop.run_forever()
        except Exception as e:
            self._start_error = str(e)
            self._started.set()

    async def _connect_all(self):
        self._exit_stack = AsyncExitStack()
        for name, script_path in SERVERS.items():
            params = StdioServerParameters(command=sys.executable, args=[script_path],
                                           **_server_env())
            read, write = await self._exit_stack.enter_async_context(stdio_client(params))
            session = await self._exit_stack.enter_async_context(ClientSession(read, write))
            await session.initialize()
            self._sessions[name] = session

    async def _call_tool_async(self, server_name, tool_name, arguments):
        session = self._sessions.get(server_name)
        if session is None:
            raise RuntimeError(f"No connected session for server '{server_name}'")
        result = await session.call_tool(tool_name, arguments)
        if result.isError:
            raise RuntimeError(f"MCP tool '{tool_name}' returned an error: {result.content}")

        # FastMCP serialises a Python list return value as one content
        # block per item (zero blocks for an empty list). A single dict
        # return value is always exactly one block. Reconstruct the
        # original Python structure accordingly.
        parsed_blocks = []
        for block in result.content:
            try:
                parsed_blocks.append(json.loads(block.text))
            except (json.JSONDecodeError, TypeError):
                parsed_blocks.append(block.text)

        if tool_name in SINGLE_OBJECT_TOOLS:
            return parsed_blocks[0] if parsed_blocks else None
        return parsed_blocks

    def call_tool(self, tool_name, arguments, timeout=30):
        """Synchronous entry point. Safe to call from Streamlit's main
        thread or from any LangGraph node. Returns the already-parsed
        Python object (dict, list, or list of dicts) -- no further JSON
        decoding needed by the caller."""
        server_name = TOOL_TO_SERVER.get(tool_name)
        if server_name is None:
            raise ValueError(f"Unknown tool: {tool_name}")
        future = asyncio.run_coroutine_threadsafe(
            self._call_tool_async(server_name, tool_name, arguments), self._loop
        )
        return future.result(timeout=timeout)

    def is_ready(self):
        return self._started.is_set() and self._start_error is None


def get_mcp_manager():
    return MCPClientManager.get_instance()
