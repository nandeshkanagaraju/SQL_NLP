import yaml
import mysql.connector
from openai import OpenAI
from tabulate import tabulate
import pandas as pd
import os
import re

# ---------- Config ----------
MODEL = "gpt-4o-mini"
MAX_HISTORY_MESSAGES = 20   
MAX_SQL_HISTORY = 5         
CONFIG_FILE = "config.yaml"
YAML_FILE = os.path.join("outputs", "mcp_feed.yaml")
# ----------------------------

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
schema_text = yaml.dump(schema)  

# -------------------- DB Connection --------------------
conn = mysql.connector.connect(
    host=config["db"]["host"],
    user=config["db"]["user"],
    password=config["db"]["password"],
    database=schema["default_schema"]
)

# -------------------- OpenAI Setup --------------------
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

# -------------------- Memory --------------------
conversation_history = []
sql_history = []
last_df = None
last_sql = None

BASE_SYSTEM_PROMPT = """You are a MySQL SQL generator assistant.
- Always output a single SQL query ending with a semicolon.
- Never use Markdown or code fences.
- You have memory of the conversation and must resolve pronouns like "them", "their", "same", "above", "those" using prior context.
- When modifying previous queries, keep WHERE, JOIN, GROUP BY, ORDER BY, and LIMIT unless the user overrides them.
- "names" = CONCAT(first_name, ' ', last_name) if available.
- Keep SQL simple and valid MySQL.
"""

# -------------------- Helpers --------------------
# (reuse all functions from your previous code, e.g., strip_code_fences, ensure_name_columns, df_to_table, try_parse_int,
# pick_sort_column, parse_filter_expression, apply_followup, etc.)
# Make sure all references to schema/db are generic.

# -------------------- LLM path --------------------
def build_messages(user_query: str):
    messages = [
        {"role": "system", "content": BASE_SYSTEM_PROMPT},
        {"role": "system", "content": f"Schema:\n{schema_text}"}
    ]
    messages.extend(conversation_history[-MAX_HISTORY_MESSAGES:])
    if sql_history:
        sql_context = "\n".join(
            [f"User: {h['user']}\nSQL: {h['sql']}" for h in sql_history[-MAX_SQL_HISTORY:]]
        )
        messages.append({
            "role": "system",
            "content": "Recent SQL history:\n" + sql_context
        })
    messages.append({"role": "user", "content": user_query})
    return messages

def nlp_to_sql(user_query: str) -> str:
    global conversation_history, sql_history, last_sql
    messages = build_messages(user_query)
    resp = client.chat.completions.create(model=MODEL, messages=messages, temperature=0)
    sql_query = resp.choices[0].message.content.strip()
    sql_query = re.sub(r"^```.*|```$", "", sql_query).strip()

    conversation_history.append({"role": "user", "content": user_query})
    conversation_history.append({"role": "assistant", "content": sql_query})
    sql_history.append({"user": user_query, "sql": sql_query})

    # Keep memory within limits
    conversation_history[:] = conversation_history[-MAX_HISTORY_MESSAGES:]
    sql_history[:] = sql_history[-MAX_SQL_HISTORY:]
    last_sql = sql_query
    return sql_query

# -------------------- DB Execution --------------------
def run_query(sql_query: str) -> pd.DataFrame:
    cur = conn.cursor(dictionary=True)
    cur.execute(sql_query)
    rows = cur.fetchall()
    cur.close()
    df = pd.DataFrame(rows)
    return df

# -------------------- Chat Loop --------------------
def chat_loop():
    global last_df
    print("SQL Assistant ready! Ask me anything.\n")
    while True:
        user_query = input("You: ").strip()
        if user_query.lower() in {"exit", "quit", "bye"}:
            print("Goodbye!")
            break

        # 1) Try follow-up on last_df
        handled_df = apply_followup(user_query, last_df)
        if handled_df is not None:
            last_df = handled_df
            print("\n Results (from previous set):\n")
            print(df_to_table(last_df))
            continue

        # 2) Otherwise, ask LLM
        sql_query = nlp_to_sql(user_query)
        print(f"\n SQL Generated:\n{sql_query}\n")

        try:
            last_df = run_query(sql_query)
            last_df = ensure_name_columns(last_df)
            print(" Results:\n")
            print(df_to_table(last_df))
        except Exception as e:
            print(f"Error: {e}")
        print("\n" + "="*60 + "\n")

if __name__ == "__main__":
    chat_loop()
