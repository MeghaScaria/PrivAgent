import random
from mcp.server.fastmcp import FastMCP
from faker import Faker

fake = Faker()
random.seed(42)
Faker.seed(42)

mcp = FastMCP("database-server")

EMPLOYEES = [
    {
        "id": i,
        "name": fake.name(),
        "department": random.choice(["HR", "Finance", "Engineering", "Sales"]),
        "salary": random.randint(40000, 150000),
        "email": fake.email(),
        "start_date": str(fake.date_between(start_date="-10y")),
    }
    for i in range(1, 101)
]

TRANSACTIONS = [
    {
        "id": i,
        "account": fake.bban(),
        "amount": random.randint(100, 100000),
        "vendor": fake.company(),
        "date": str(fake.date_between(start_date="-2y")),
        "status": random.choice(["completed", "pending", "failed"]),
    }
    for i in range(1, 101)
]


@mcp.tool()
def query_database(table: str, filters: str = "") -> list[dict]:
    """Query a database table with optional filter string.
    Tables: employees, transactions.
    Filters example: 'department=Engineering' or 'status=pending'"""
    if table == "employees":
        data = EMPLOYEES
    elif table == "transactions":
        data = TRANSACTIONS
    else:
        return [{"error": f"Unknown table: {table}"}]

    if filters:
        key, _, value = filters.partition("=")
        key = key.strip()
        value = value.strip().lower()
        data = [row for row in data if str(row.get(key, "")).lower() == value]

    return data[:10]


@mcp.tool()
def list_tables() -> list[str]:
    """List available database tables."""
    return ["employees", "transactions"]


if __name__ == "__main__":
    mcp.run(transport="stdio")
