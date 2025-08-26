import os
import json
import yaml
import mysql.connector
from openai import OpenAI

# --- Database executor ---
def execute_sql(query):
    cnx = mysql.connector.connect(
        host="localhost", 
        user="root", 
        password="Password",   # change this
        database="company_db"      # change this
    )
    cursor = cnx.cursor()
    cursor.execute(query)
    rows = cursor.fetchall()
    cols = [desc[0] for desc in cursor.description]
    cnx.close()
    return [dict(zip(cols, row)) for row in rows]

# --- Load schema from YAML ---
def load_schema(path="company_mcp_feed.yaml"):
    with open(path, "r") as f:
        schema_data = yaml.safe_load(f)
    return yaml.dump(schema_data)  # keep it readable for LLM

# --- Main flow ---
if __name__ == "__main__":
    schema = load_schema("company_mcp_feed.yaml")

    user_query = input("Enter your question: ")

    prompt = f"""
    You are a SQL assistant.
    Database Schema:
    {schema}

    User request: {user_query}

    Respond ONLY in JSON like this:
    {{ "query": "<SQL query>" }}
    """

    client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[{"role": "user", "content": prompt}]
    )

    try:
        sql = json.loads(response.choices[0].message.content)["query"]
        print("\n✅ Generated SQL:", sql)
        result = execute_sql(sql)
        print("\n📊 Result:", result)
    except Exception as e:
        print("\n❌ Error:", e)
        print("\nLLM raw response was:", response.choices[0].message.content)

