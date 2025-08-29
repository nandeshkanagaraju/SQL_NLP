import os
import yaml
import pandas as pd
import mysql.connector
from openai import OpenAI
import re

# ---------------- CONFIG ----------------
MODEL = "gpt-4o-mini"
CONFIG_FILE = os.path.join(os.path.dirname(os.path.dirname(__file__)), "config.yaml")
YAML_FILE = os.path.join(os.path.dirname(os.path.dirname(__file__)), "outputs", "mcp_feed.yaml")

# ---------------- HELPERS ----------------
def display_df(df: pd.DataFrame) -> str:
    """Display full DataFrame without truncation."""
    if df is None or df.empty:
        return "No results."
    pd.set_option("display.max_rows", None)
    pd.set_option("display.max_columns", None)
    pd.set_option("display.width", 200)
    pd.set_option("display.colheader_justify", "center")
    return df.to_string(index=False)

def extract_sql(llm_response: str) -> str:
    """Extract the first SQL statement from LLM response."""
    text = re.sub(r"```sql|```", "", llm_response, flags=re.IGNORECASE).strip()
    match = re.search(r"(SELECT|INSERT|UPDATE|DELETE).*?;", text, flags=re.IGNORECASE | re.DOTALL)
    if match:
        return match.group(0)
    return text.strip()

# ---------------- LOAD CONFIG & SCHEMA ----------------
def load_config(file_path=CONFIG_FILE):
    if not os.path.exists(file_path):
        raise FileNotFoundError(f"{file_path} not found.")
    with open(file_path) as f:
        return yaml.safe_load(f)

def load_schema(file_path=YAML_FILE):
    if not os.path.exists(file_path):
        raise FileNotFoundError(f"{file_path} not found.")
    with open(file_path) as f:
        return yaml.safe_load(f)

config = load_config()
schema = load_schema()
schema_text = yaml.dump(schema)

# ---------------- DATABASE ----------------
conn = mysql.connector.connect(
    host=config["db"]["host"],
    user=config["db"]["user"],
    password=config["db"]["password"],
    database=schema["default_schema"]
)

# ---------------- OPENAI ----------------
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

# ---------------- MEMORY ----------------
class ConversationMemory:
    """Stores full conversation with SQL and results"""
    def __init__(self):
        self.steps = []  # Each step: {"user": str, "sql": str, "df": pd.DataFrame}

    def add_step(self, user_query, sql_query, df):
        self.steps.append({"user": user_query, "sql": sql_query, "df": df})

    def get_last_df(self):
        for step in reversed(self.steps):
            if step["df"] is not None and not step["df"].empty:
                return step["df"]
        return None

memory = ConversationMemory()

# ---------------- SQL EXECUTION ----------------
def execute_sql(sql_query: str) -> pd.DataFrame:
    cur = conn.cursor(dictionary=True)
    cur.execute(sql_query)
    rows = cur.fetchall()
    cur.close()
    return pd.DataFrame(rows)

# ---------------- FOLLOW-UP SQL ----------------
def followup_sql(user_query, last_df):
    """
    Generate SQL limited to previous result if possible.
    Supports selecting columns and ordering on previous rows only.
    """
    if last_df is None or last_df.empty:
        return None

    # Extract requested columns from user query
    cols = re.findall(r"their (\w+)|only (\w+)|give me (\w+)", user_query.lower())
    cols = [c for t in cols for c in t if c]
    if not cols:
        cols = list(last_df.columns)

    # Use previous emp_ids if available
    if 'emp_id' in last_df.columns:
        ids = last_df['emp_id'].tolist()
        id_str = ','.join(map(str, ids))
        sql = f"SELECT {', '.join(cols)} FROM employees WHERE emp_id IN ({id_str})"

        # Check for sorting
        match = re.search(r"sort.*by (\w+)", user_query.lower())
        if match:
            order_col = match.group(1)
            order = "DESC" if "desc" in user_query.lower() else "ASC"
            sql += f" ORDER BY {order_col} {order}"
        sql += ";"
        return sql

    # Fallback: generate SQL via LLM if no emp_id
    prompt = f"""
    You have the previous result (columns: {', '.join(last_df.columns)}).
    User query: {user_query}
    Generate SQL using only available context, ending with a semicolon.
    """
    resp = client.chat.completions.create(
        model=MODEL,
        messages=[{"role": "user", "content": prompt}],
        temperature=0
    )
    return extract_sql(resp.choices[0].message.content)

# ---------------- SQL GENERATION ----------------
def generate_sql(user_query: str) -> str:
    """Generate SQL using full conversation history"""
    messages = [{"role": "system", "content": f"You are a MySQL SQL assistant. Schema:\n{schema_text}"}]
    for step in memory.steps:
        messages.append({"role": "user", "content": step["user"]})
        messages.append({"role": "assistant", "content": step["sql"]})
    messages.append({"role": "user", "content": user_query})

    resp = client.chat.completions.create(model=MODEL, messages=messages, temperature=0)
    llm_output = resp.choices[0].message.content.strip()
    sql_query = extract_sql(llm_output)
    return sql_query

# ---------------- CHAT LOOP ----------------
def chat():
    print("SQL Assistant ready! Ask me anything.\n")
    while True:
        user_query = input("You: ").strip()
        if user_query.lower() in {"exit", "quit", "bye"}:
            print("Goodbye!")
            break

        last_df = memory.get_last_df()
        df = None

        # Determine if follow-up
        if last_df is not None and any(x in user_query.lower() for x in ["their", "them", "these", "those", "top"]):
            try:
                sql_query = followup_sql(user_query, last_df)
                df = execute_sql(sql_query)
            except Exception as e:
                print(f"Error executing follow-up SQL: {e}")
                sql_query = None
        else:
            try:
                sql_query = generate_sql(user_query)
                df = execute_sql(sql_query)
            except Exception as e:
                print(f"Error running SQL: {e}")
                sql_query = None

        # Save in memory
        memory.add_step(user_query, sql_query, df)

        # Display
        if sql_query:
            print(f"\nSQL Generated:\n{sql_query}\n")
        print("Results:\n")
        print(display_df(df))
        print("\n" + "="*80 + "\n")

if __name__ == "__main__":
    chat()
