import mysql.connector
import yaml

with open("company_mcp_feed.yaml", "r") as f:
    schema = yaml.safe_load(f)

db_config = {
    "host": "localhost",
    "user": "root",          # change if needed
    "password": "Jeya@4679", # your MySQL password
    "database": schema["default_schema"]
}

cnx = mysql.connector.connect(**db_config)
cursor = cnx.cursor(dictionary=True)
cursor.execute("SELECT * FROM employees LIMIT 5;")
rows = cursor.fetchall()

for row in rows:
    print(row)

cursor.close()
cnx.close()

