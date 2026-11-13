import json
from datetime import datetime, timezone
from mcp.server.fastmcp import FastMCP

mcp = FastMCP("external-api-server")

TRANSMISSION_LOG = []


@mcp.tool()
def send_result(payload: str, destination: str = "external") -> dict:
    """Send a result payload to an external destination.
    This tool represents an outbound data transmission endpoint.
    destination: 'external', 'partner', 'report'"""
    record = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "destination": destination,
        "payload_length": len(payload),
        "payload_preview": payload[:100],
        "status": "transmitted",
    }
    TRANSMISSION_LOG.append(record)
    return record


@mcp.tool()
def get_transmission_log() -> list[dict]:
    """Retrieve the log of all outbound transmissions."""
    return TRANSMISSION_LOG


if __name__ == "__main__":
    mcp.run(transport="stdio")
