import mysql.connector
import yaml
from fastmcp import FastMCP

# Load YAML schema (your file)
with open("company_mcp_feed.yaml", "r") as f:
    schema = yaml.safe_load(f)

# MySQL config (edit with your credentials)
db_config = {
    "host": "localhost",
    "user": "root",           # change if you use another user
    "password": "Password",  # replace with your password
    "database": schema["default_schema"]
}

# Connect and run queries
def run_query(query: str):
    cnx = mysql.connector.connect(**db_config)
    cursor = cnx.cursor(dictionary=True)
    cursor.execute(query)
    rows = cursor.fetchall()
    cursor.close()
    cnx.close()
    return rows

# Setup FastMCP
mcp = FastMCP("mysql-mcp")

@mcp.tool()
def sql_query(query: str):
    """Run a SQL query on the MySQL database."""
    return run_query(query)

if __name__ == "__main__":
    mcp.run()

