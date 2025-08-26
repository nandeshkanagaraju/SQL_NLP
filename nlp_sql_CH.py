import yaml
import mysql.connector
from openai import OpenAI
from tabulate import tabulate
import pandas as pd
import os
import re

# ---------- Config ----------
MODEL = "gpt-4o-mini"
MAX_HISTORY_MESSAGES = 20   # allow more context
MAX_SQL_HISTORY = 5         # keep last 5 SQLs for reference
# ----------------------------

# Load schema text (keep it concise)
with open("company_mcp_feed.yaml", "r") as f:
    schema_text = f.read()

# DB (keep one connection; open dict cursors per query)
conn = mysql.connector.connect(
    host="localhost",
    user="root",
    password="password",
    database="company_db"
)

# OpenAI
client = OpenAI(api_key=os.getenv(""))

# Conversation memory
conversation_history = []   # [{"role":"user"/"assistant","content":str}]
sql_history = []            # [{"user":..., "sql":...}]
last_df = None              # pandas.DataFrame of the last result
last_sql = None             # last executed SQL (string)

BASE_SYSTEM_PROMPT = """You are a MySQL SQL generator assistant.
- Always output a single SQL query ending with a semicolon.
- Never use Markdown or code fences.
- You have memory of the conversation and must resolve pronouns like "them", "their", "same", "above", "those" using prior context.
- When modifying previous queries, keep WHERE, JOIN, GROUP BY, ORDER BY, and LIMIT unless the user overrides them.
- "names" = CONCAT(first_name, ' ', last_name) if available.
- Keep SQL simple and valid MySQL.
"""

# -------------------- Helpers --------------------

def strip_code_fences(text: str) -> str:
    text = text.strip()
    m = re.match(r"^```[a-zA-Z]*\s*([\s\S]*?)\s*```$", text)
    if m:
        return m.group(1).strip()
    return text

def ensure_name_columns(df: pd.DataFrame) -> pd.DataFrame:
    """Create a 'name'/'names' column if first_name + last_name exist."""
    if "name" not in df.columns and "names" not in df.columns:
        if "first_name" in df.columns and "last_name" in df.columns:
            df = df.copy()
            df["name"] = df["first_name"].astype(str).str.strip() + " " + df["last_name"].astype(str).str.strip()
    return df

def df_to_table(df: pd.DataFrame) -> str:
    if df is None or df.empty:
        return "⚠️ No rows."
    return tabulate(df, headers=df.columns, tablefmt="fancy_grid", showindex=False)

def try_parse_int(text: str) -> int | None:
    m = re.search(r"(?:first|top|only|limit|last|bottom)?\s*(\d+)", text)
    return int(m.group(1)) if m else None

def pick_sort_column(text: str, df: pd.DataFrame) -> str | None:
    # Try explicit "by <col>" first
    m = re.search(r"\bby\s+([a-zA-Z_ ]+)", text)
    candidate = None
    if m:
        candidate = m.group(1).strip().replace(" ", "_")
    else:
        # Guess from words in the text
        if re.search(r"\bname(s)?\b", text) and ("names" in df.columns or "name" in df.columns):
            return "names" if "names" in df.columns else "name"
        for col in ["salary", "hire_date", "dept_id", "department_id", "emp_id", "employee_id", "job_id"]:
            if col.replace("_", " ") in text or col in text:
                if col in df.columns:
                    return col
    if candidate and candidate in df.columns:
        return candidate
    # Default to names if present, else first text-like column
    if "names" in df.columns: return "names"
    if "name" in df.columns: return "name"
    for c in df.columns:
        if df[c].dtype == "object":
            return c
    return df.columns[0] if len(df.columns) else None

def parse_filter_expression(text: str, df: pd.DataFrame):
    """
    Very small filter parser: matches things like
    'salary > 50000', 'dept_id = 2', 'hire_date >= 2022-01-01'
    Returns (col, op, value) or None.
    """
    ops = r"(>=|<=|=|>|<)"
    m = re.search(r"\b([a-zA-Z_]+)\s*" + ops + r"\s*([a-zA-Z0-9\-\./_]+)", text)
    if not m: 
        return None
    col, op, val = m.group(1), m.group(2), m.group(3)
    if col not in df.columns:
        return None
    # try to cast numeric where possible
    try:
        if df[col].dtype.kind in "iu":   # ints
            val = int(re.sub(r"[^\d\-]", "", val))
        elif df[col].dtype.kind in "f":  # floats
            val = float(re.sub(r"[^\d\.\-]", "", val))
        # else keep string/date as-is
    except:
        pass
    return (col, op, val)

def apply_followup(user_text: str, df: pd.DataFrame) -> pd.DataFrame | None:
    """
    Handle follow-ups on the previous DataFrame:
    - sort (asc/desc, by column); default to names/name when available
    - only names / only salaries / show <col list>
    - limit first/top/bottom/last N
    - simple filters: <col> <op> <value>
    """
    if df is None or df.empty:
        return None

    text = user_text.lower().strip()
    # Does the user clearly refer to previous result?
    refers_prev = any(w in text for w in ["above", "them", "their", "those", "these", "same", "previous", "earlier", "that list", "now "])
    if not refers_prev and not (text.startswith("sort") or text.startswith("only") or text.startswith("show") or text.startswith("just") or text.startswith("top") or text.startswith("first") or text.startswith("last") or text.startswith("bottom") or "filter" in text):
        return None  # doesn't look like a follow-up instruction

    # Work on a copy
    df = df.copy()
    df = ensure_name_columns(df)

    # Column selection like "only names", "now give me their salaries", "show name, salary"
    if ("only" in text or "just" in text or re.search(r"show\s", text)) and not ("sort" in text):
        # find explicit list e.g. "show name, salary"
        mlist = re.findall(r"(?:only|just|show)\s+([a-zA-Z0-9_,\s]+)", text)
        if mlist:
            cols_raw = mlist[-1]
            wanted = [c.strip().replace(" ", "_") for c in cols_raw.split(",")]
            # map 'names'/'name' synonyms
            mapped = []
            for c in wanted:
                if c in df.columns:
                    mapped.append(c)
                elif c in {"name","names"}:
                    mapped.append("names" if "names" in df.columns else "name")
            wanted = [c for c in mapped if c in df.columns]
            if wanted:
                return df[wanted]
        # Single clue like "their salaries" or "only names"
        if "salary" in text and "salary" in df.columns:
            return df[["salary"]]
        if re.search(r"\bname(s)?\b", text):
            if "names" in df.columns:
                return df[["names"]]
            if "name" in df.columns:
                return df[["name"]]

    # Sort
    if "sort" in text or "order by" in text:
        col = pick_sort_column(text, df)
        if col:
            ascending = not any(w in text for w in ["desc", "descending", "reverse", "largest", "highest"])
            # If sorting by a text column that numerically looks like numbers, let pandas handle naturally
            try:
                return df.sort_values(by=col, ascending=ascending, kind="mergesort")  # stable
            except Exception:
                return df

    # Limit / top / first / last
    if any(w in text for w in ["top", "first", "limit", "only", "last", "bottom"]):
        n = try_parse_int(text)
        if n is not None:
            if any(w in text for w in ["last", "bottom"]):
                return df.tail(n)
            else:
                return df.head(n)

    # Simple filters: "salary > 50000"
    if "filter" in text or "where" in text or re.search(r"\b(>=|<=|=|>|<)\b", text):
        cond = parse_filter_expression(text, df)
        if cond:
            col, op, val = cond
            if op == ">":   return df[df[col] >  val]
            if op == "<":   return df[df[col] <  val]
            if op == "=":   return df[df[col] == val]
            if op == ">=":  return df[df[col] >= val]
            if op == "<=":  return df[df[col] <= val]

    # If we got here, treat it as not handled
    return None

# -------------------- LLM path --------------------

def build_messages(user_query: str):
    """Builds the message list with schema, history, and recent SQLs."""
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
            "content": "Recent SQL history (use to resolve pronouns/continuations):\n" + sql_context
        })
    messages.append({"role": "user", "content": user_query})
    return messages

def nlp_to_sql(user_query: str) -> str:
    global conversation_history, sql_history, last_sql

    messages = build_messages(user_query)
    resp = client.chat.completions.create(model=MODEL, messages=messages, temperature=0)
    sql_query = strip_code_fences(resp.choices[0].message.content)

    # Update memory
    conversation_history.append({"role": "user", "content": user_query})
    conversation_history.append({"role": "assistant", "content": sql_query})
    sql_history.append({"user": user_query, "sql": sql_query})
    if len(conversation_history) > MAX_HISTORY_MESSAGES:
        conversation_history[:] = conversation_history[-MAX_HISTORY_MESSAGES:]
    if len(sql_history) > MAX_SQL_HISTORY:
        sql_history[:] = sql_history[-MAX_SQL_HISTORY:]
    last_sql = sql_query
    return sql_query

# -------------------- DB execution --------------------

def run_query(sql_query: str) -> pd.DataFrame:
    cur = conn.cursor(dictionary=True)  # dict rows -> easy DF
    cur.execute(sql_query)
    rows = cur.fetchall()
    cur.close()
    df = pd.DataFrame(rows)
    return df

# -------------------- Chat Loop --------------------

def chat_loop():
    global last_df, last_sql
    print("🤖 SQL Assistant ready! Ask me anything about company_db.\n")
    while True:
        user_query = input("You: ")
        if user_query.lower() in {"exit", "quit", "bye"}:
            print("👋 Goodbye!")
            break

        # 1) Try to treat this as a follow-up on the last result (Pandas path)
        handled_df = apply_followup(user_query, last_df)
        if handled_df is not None:
            last_df = handled_df  # update last result to the new view
            print("\n📊 Results (from previous result set):\n")
            print(df_to_table(last_df))
            print("\n" + "="*60 + "\n")
            # also log to history so LLM sees the progression
            conversation_history.append({"role": "user", "content": user_query})
            conversation_history.append({"role": "assistant", "content": "[Applied follow-up on previous result set]"})
            if len(conversation_history) > MAX_HISTORY_MESSAGES:
                conversation_history[:] = conversation_history[-MAX_HISTORY_MESSAGES:]
            continue

        # 2) Otherwise, ask the LLM for a fresh SQL
        sql_query = nlp_to_sql(user_query)
        print(f"\n📜 SQL Generated:\n{sql_query}\n")

        try:
            last_df = run_query(sql_query)
            print("📊 Results:\n")
            # Ensure we have a derived 'name' if needed for follow-ups
            last_df = ensure_name_columns(last_df)
            print(df_to_table(last_df))
        except Exception as e:
            print(f"⚠️ Error: {e}")
        print("\n" + "="*60 + "\n")

if __name__ == "__main__":
    chat_loop()
