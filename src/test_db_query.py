import mysql.connector
import yaml
import os

# -------------------- Paths --------------------
CONFIG_FILE = "config.yaml"
YAML_FILE = os.path.join("outputs", "mcp_feed.yaml")  

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
    "host": config["db"]["host"],
    "user": config["db"]["user"],
    "password": config["db"]["password"],
    "database": schema["default_schema"]
}

# -------------------- Connect and Query --------------------
cnx = mysql.connector.connect(**db_config)
cursor = cnx.cursor(dictionary=True)
cursor.execute("SELECT * FROM employees LIMIT 5;")
rows = cursor.fetchall()

print("First 5 rows of employees table:")
for row in rows:
    print(row)

cursor.close()
cnx.close()
