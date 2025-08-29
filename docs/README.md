# MySQL + NLP + MCP Integration Project

## Overview
This project provides a framework to connect a MySQL database with natural language processing (NLP) capabilities. Using **Model Context Protocol (MCP)**, any Large Language Model (LLM) like OpenAI, Claude, or Gemini can query your database using natural language, without writing raw SQL.

The project is ideal for:
- Making SQL accessible to non-technical users
- Experimenting with AI-powered database assistants
- Generating YAML schema feeds for MCP




---

## Features
- **MySQL Database Connectivity:** Seamlessly connect to your MySQL database.
- **Automated Schema Generation:** Generates a YAML feed (`mcp_feed.yaml`) from your database schema.
- **Flexible Database Querying:** Query via SQL or natural language using AI assistant.
- **MCP Integration:** Allows LLMs to interpret and execute database queries.
- **Advanced Context Awareness:** Maintain conversation context to handle multi-step queries.




---

## Project Structure

.
.
├── config/
├── docs/
├── src/
│   ├── generate_mcp_feed.py
│   ├── mysql_mcp_server.py
│   ├── sql_assistant.py
│   └── test_db_query.py
├── .DS_Store
├── .env.example
├── .gitignore
├── config.yaml
├── requirements.txt
└── outputs/



---

## Setup Instructions

### 1. Clone the Repository
```bash
git clone https://github.com/nandeshkanagaraju/SQL_NLP.git
cd SQL_NLP
```

### 2. Create a Python Virtual Environment
```bash
python3 -m venv venv
source venv/bin/activate   # macOS/Linux
venc\Scripts\activate      # Windows
```

### 3. Install Dependencies
```bash
pip install -r requirements.txt
```

Dependencies include:

- `mysql-connector-python`
- `pyyaml`
- `fastmcp`
- `openai` (optional if using OpenAI models)
- `pandas`

### 4. Configure Database

Create a `config.yaml` in the root folder:
```yaml
db:
  host: "localhost"
  user: "root"
  password: "your_password"
  database: "database"
```

Also create `.env` for API keys (if using OpenAI/other LLMs):
```
OPENAI_API_KEY=your_openai_api_key
or
Use export"your_openai_api_key"
```

### 5. Create MySQL Database and Table (Example)
```sql
CREATE DATABASE company_db;

USE company_db;

CREATE TABLE employees (
    emp_id INT PRIMARY KEY,
    first_name VARCHAR(50),
    last_name VARCHAR(50),
    email VARCHAR(100),
    phone_number VARCHAR(50),
    hire_date DATE,
    job_id VARCHAR(50),
    salary DECIMAL(10,2),
    dept_id INT
);

INSERT INTO employees (emp_id, first_name, last_name, email, phone_number, hire_date, job_id, salary, dept_id)
VALUES
(46, 'Phillip', 'Brown', 'phillip.brown45@yahoo.com', '(500)888-6354', '2021-12-31', 'Hotel manager', 119708.94, 8),
(60, 'Steven', 'Scott', 'steven.scott59@yahoo.com', '001-695-645-8290', '2022-01-14', 'Sport and exercise psychologist', 119548.28, 9),
(7, 'Sherri', 'Braun', 'sherri.braun6@gmail.com', '001-478-530-5390x10855', '2025-01-12', 'Contractor', 119310.50, 5),
(139, 'Ashley', 'Wilson', 'ashley.wilson138@hotmail.com', '(941)464-0350x78524', '2025-05-17', 'Industrial/product designer', 119230.55, 3),
(17, 'Tasha', 'Reynolds', 'tasha.reynolds16@hotmail.com', '+1-804-427-7135x7058', '2024-07-10', 'Press photographer', 119094.92, 2);
```

### 6. Generate MCP Feed
```bash
python3 src/generate_mcp_feed.py
```
This will create `outputs/mcp_feed.yaml` containing your database schema.

### 7. Test Database Connection
```bash
python3 src/test_db_query.py
```
Example output:
```
✅ First 5 rows of employees table:
{'emp_id': 46, 'first_name': 'Phillip', 'last_name': 'Brown', ...}
```

### 8. Run MCP Server
```bash
python3 src/mysql_mcp_server.py
```
This exposes your database to any LLM via MCP.

### 9. Use SQL Assistant (NLP)
```bash
python3 src/sql_assistant.py
```
Example interaction:
```
You: top 5 employees
SQL Generated:
SELECT * FROM employees ORDER BY salary DESC LIMIT 5;

Results:
 emp_id first_name last_name email ...
   46  Phillip    Brown  phillip.brown45@yahoo.com ...
```

Ask follow-up queries like:

- `You: give me their email`
- `You: sort them by last_name`
- `You: top 3 salaries`




---

## Security Features

- **No raw passwords in code:** Use `config.yaml` and `.env` for sensitive info.
- **Environment variables:** Store API keys securely.
- **Restricted queries:** MCP server executes controlled queries only.

---

## Notes

- Works with any LLM that supports MCP.
- Conversation memory allows multi-step natural language queries.
- Fully compatible with MySQL 8+.




---

## Optional: Run With Docker (Future)

You can containerize the project for production deployment.


