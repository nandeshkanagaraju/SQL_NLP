import mysql.connector
import yaml

def get_db_schema(host, user, password, database):
    cnx = None
    try:
        cnx = mysql.connector.connect(
            host=host,
            user=user,
            password=password,
            database=database
        )
        cursor = cnx.cursor()

        tables_data = []

        # Get table names
        cursor.execute("SHOW TABLES;")
        tables = [table[0] for table in cursor.fetchall()]

        for table_name in tables:
            table_info = {
                "name": table_name,
                "schema": database,  # Using database name as schema
                "title": table_name.replace("_", " ").title(),  # Simple title generation
                "description": f"Table containing {table_name.replace('_', ' ')} data.",
                "columns": []
            }

            # Get column details
            cursor.execute(f"DESCRIBE {table_name};")
            columns = cursor.fetchall()

            for col in columns:
                col_name = col[0]
                col_type = col[1].decode("utf-8") if isinstance(col[1], bytes) else col[1]

                column_info = {
                    "name": col_name,
                    "type": col_type.upper(),
                    "role": "dimension",  # Default role
                    "description": f"Column for {col_name.replace('_', ' ')}.",
                    "agg": "sum" if "INT" in col_type.upper() or "DECIMAL" in col_type.upper() else None
                }
                table_info["columns"].append(column_info)

            tables_data.append(table_info)

    except mysql.connector.Error as err:
        print(f"❌ Error: {err}")
        return None
    finally:
        if cnx:
            cnx.close()
    return tables_data


def generate_mcp_feed_yaml(output_file, db_schema_data, default_schema="company_db", dialect="mysql"):
    mcp_feed = {
        "default_schema": default_schema,
        "dialect": dialect,
        "tables": db_schema_data
    }

    with open(output_file, "w") as f:
        yaml.dump(mcp_feed, f, indent=2, sort_keys=False)


if __name__ == "__main__":
    # ✅ Fill in your MySQL login details here
    DB_CONFIG = {
        "host": "localhost",          # or "127.0.0.1"
        "user": "root",               # your MySQL username
        "password": "Jeya@4679",      # your MySQL password
        "database": "company_db"      # your database name
    }

    schema_data = get_db_schema(**DB_CONFIG)

    if schema_data:
        # ✅ Absolute path so you don’t lose the file
        output_path = "/Users/nandeshkanagaraju/Documents/Sql/company_mcp_feed.yaml"
        generate_mcp_feed_yaml(output_path, schema_data)
        print(f"✅ MCP feed YAML generated successfully at {output_path}")
    else:
        print("❌ Failed to retrieve database schema.")

