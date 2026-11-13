import random
from mcp.server.fastmcp import FastMCP
from faker import Faker

fake = Faker()
random.seed(42)
Faker.seed(42)

mcp = FastMCP("web-search-server")


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
    return results


if __name__ == "__main__":
    mcp.run(transport="stdio")
