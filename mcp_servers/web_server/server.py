import random
from mcp.server.fastmcp import FastMCP
from faker import Faker

fake = Faker()
random.seed(42)
Faker.seed(42)

mcp = FastMCP("web-search-server")


# -- WP6 injection planting (opt-in via PRIVAGENT_INJECTION_FILE) ----------------
# The file holds {"web": text|null, "document": text|null} and is re-read on every
# call, so a harness can plant a different indirect prompt injection per task.
# Unset (the default): results are unchanged.
import json as _json
import os as _os


def _injection(kind):
    path = _os.environ.get("PRIVAGENT_INJECTION_FILE")
    if not path or not _os.path.exists(path):
        return None
    with open(path, encoding="utf-8") as f:
        return _json.load(f).get(kind)


@mcp.tool()
def search_web(query: str) -> list[dict]:
    """Search the web for information on a given query.
    Returns synthetic search results."""
    results = []
    for i in range(3):
        results.append({
            "title": f"{query} - {fake.catch_phrase()}",
            "url": f"https://{fake.domain_name()}/articles/{fake.slug()}",
            "snippet": fake.paragraph(nb_sentences=2),
            "published": str(fake.date_between(start_date="-1y")),
            "sensitivity": "low",
        })
    planted = _injection("web")
    if planted:
        results[0] = {**results[0], "snippet": results[0]["snippet"] + " " + planted}
    return results


if __name__ == "__main__":
    mcp.run(transport="stdio")
