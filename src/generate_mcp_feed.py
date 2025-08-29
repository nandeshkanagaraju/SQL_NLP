import mysql.connector
import yaml
import os

# -------------------- Load Config --------------------
CONFIG_FILE = "config.yaml"

def load_config(config_file=CONFIG_FILE):
    if not os.path.exists(config_file):
        raise FileNotFoundError(f"{config_file} not found.")
    with open(config_file) as f:
        return yaml.safe_load(f)

config = load_config()

# -------------------- Extract DB Schema --------------------
def get_db_schema(host, user, password, database):
    """Connect to MySQL and return a list of tables with columns."""
    cnx = None
    try:
        cnx = mysql.connector.connect(host=host, user=user, password=password, database=database)
        cursor = cnx.cursor()
        tables_data = []

        cursor.execute("SHOW TABLES;")
        tables = [t[0] for t in cursor.fetchall()]

        for table_name in tables:
            table_info = {
                "name": table_name,
                "schema": database,
                "title": table_name.replace("_", " ").title(),
                "description": f"Table containing {table_name.replace('_', ' ')} data.",
                "columns": []
            }

            cursor.execute(f"DESCRIBE {table_name};")
            for col in cursor.fetchall():
                col_name, col_type = col[0], col[1]
                if isinstance(col_type, bytes):
                    col_type = col_type.decode("utf-8")
                column_info = {
                    "name": col_name,
                    "type": col_type.upper(),
                    "role": "dimension",
                    "description": f"Column for {col_name.replace('_', ' ')}.",
                    "agg": "sum" if "INT" in col_type.upper() or "DECIMAL" in col_type.upper() else None
                }
                table_info["columns"].append(column_info)

            tables_data.append(table_info)
        return tables_data

    except mysql.connector.Error as err:
        print(f"❌ Database error: {err}")
        return None
    finally:
        if cnx:
            cnx.close()

# -------------------- Generate YAML --------------------
def generate_mcp_feed_yaml(db_schema_data, default_schema):
    """Always write the YAML as outputs/mcp_feed.yaml"""
    output_file = os.path.join("outputs", "mcp_feed.yaml")
    os.makedirs(os.path.dirname(output_file), exist_ok=True)
    
    mcp_feed = {
        "default_schema": default_schema,
        "dialect": "mysql",
        "tables": db_schema_data
    }

    with open(output_file, "w") as f:
        yaml.dump(mcp_feed, f, indent=2, sort_keys=False)

    print(f"✅ MCP feed YAML generated at {output_file}")

# -------------------- Main --------------------
if __name__ == "__main__":
    schema_data = get_db_schema(**config['db'])
    if schema_data:
        generate_mcp_feed_yaml(schema_data, config['db']['database'])
    else:
        print("❌ Failed to retrieve database schema.")
