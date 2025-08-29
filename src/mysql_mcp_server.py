import mysql.connector
import yaml
import os
import logging
from fastmcp import FastMCP
from dotenv import load_dotenv

# -------------------- Setup --------------------
load_dotenv()  # Load secrets from .env

# Paths
CONFIG_FILE = os.path.join("config", "config.yaml")
YAML_FILE = os.path.join("outputs", "mcp_feed.yaml")

# Logging
logging.basicConfig(
    filename="mcp_server.log",
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s"
)

# -------------------- Load Config and Schema --------------------
def load_config(config_file=CONFIG_FILE):
    if not os.path.exists(config_file):
        raise FileNotFoundError(f"{config_file} not found.")
    with open(config_file) as f:
        return yaml.safe_load(f)

def load_schema(yaml_file=YAML_FILE):
    if not os.path.exists(yaml_file):
        raise FileNotFoundError(f"{yaml_file} not found.")
    with open(yaml_file) as f:
        return yaml.safe_load(f)

config = load_config()
schema = load_schema()

# -------------------- MySQL Config --------------------
db_config = {
    "host": os.getenv("DB_HOST", config["db"]["host"]),
    "user": os.getenv("DB_USER", config["db"]["user"]),
    "password": os.getenv("DB_PASSWORD", config["db"]["password"]),
    "database": schema["default_schema"]
}

# -------------------- Safe Query Filter --------------------
FORBIDDEN_SQL = ["DROP", "DELETE", "ALTER", "TRUNCATE"]

def is_safe_query(query: str) -> bool:
    """Prevent destructive SQL statements."""
    return not any(word in query.upper() for word in FORBIDDEN_SQL)

# -------------------- Run SQL Query --------------------
def run_query(query: str, params=None):
    """Safely execute a SQL query with protection and logging."""
    if not is_safe_query(query):
        logging.warning(f"Blocked unsafe query: {query}")
        raise ValueError("Unsafe query detected. Execution blocked.")

    cnx = None
    cursor = None
    try:
        cnx = mysql.connector.connect(**db_config)
        cursor = cnx.cursor(dictionary=True)
        cursor.execute(query, params or ())
        rows = cursor.fetchall()
        cnx.commit()
        logging.info(f"Executed query: {query}")
        return rows
    except mysql.connector.Error as e:
        logging.error(f"MySQL error: {e}")
        raise
    finally:
        if cursor:
            cursor.close()
        if cnx:
            cnx.close()
            logging.info("DB connection closed.")

# -------------------- FastMCP Setup --------------------
mcp = FastMCP("mysql-mcp")

@mcp.tool()
def sql_query(query: str):
    """Run a SQL query on the MySQL database."""
    return run_query(query)

# -------------------- Main --------------------
if __name__ == "__main__":
    logging.info("Starting MySQL MCP server...")
    mcp.run()
