# MySQL + NLP + MCP Integration Project

## Overview

This project provides a robust and flexible framework for integrating MySQL databases with Natural Language Processing (NLP) capabilities, leveraging the Model Context Protocol (MCP) to enable natural language querying of your database. It abstracts away the complexities of SQL, allowing any Large Language Model (LLM) such as OpenAI, Claude, or Gemini to interact with your database using intuitive natural language commands.

## Features

- **MySQL Database Connectivity**: Seamlessly connect to your MySQL database.
- **Automated Schema Generation**: Automatically generate a YAML schema feed (`mcp_feed.yaml`) from your MySQL database structure.
- **Flexible Database Querying**: Query the database directly using SQL or via an AI assistant using natural language.
- **Model Context Protocol (MCP) Integration**: Utilize MCP to enable LLMs to understand and execute database queries in natural language, enhancing accessibility and ease of use.
- **AI Assistant for Natural Language Queries**: Interact with your database using a local AI assistant that translates natural language requests into SQL queries.

## Project Structure

```
.
├── config.yaml # Database connection config (edit with your credentials)
├── example_schema.yaml # Example schema YAML
├── generate_mcp_feed.py # Script to generate mcp_feed.yaml from MySQL schema
├── mysql_mcp_server.py # MCP server exposing MySQL queries as a tool
├── sql_assistant.py # AI assistant that queries MySQL via MCP
├── test_db_query.py # Direct SQL query test script
```

## Setup Instructions

### 1. Install Dependencies

Ensure Python 3.8+ is installed. Then, install the required packages:

```bash
pip install mysql-connector-python pyyaml fastmcp
# (Optional: Also install OpenAI/Claude/Gemini SDKs if you plan to use AI assistants.)
```

### 2. Configure Database

Edit the `config.yaml` file with your MySQL connection details:

```yaml
db:
  host: "localhost"
  user: "root"
  password: "your_password"
```

### 3. Generate Schema Feed

Run the schema generator script to create `outputs/mcp_feed.yaml`. This script connects to your MySQL database, reads all table and column information, and saves the schema details.

```bash
python generate_mcp_feed.py
```

### 4. Test Database Query

Run a quick query to verify your database connection and setup:

```bash
python test_db_query.py
```

Example output:

```lua
✅ First 5 rows of employees table:
{'id': 1, 'name': 'Alice', 'role': 'Engineer'}
{'id': 2, 'name': 'Bob', 'role': 'Manager'}
...
```

### 5. Run MCP Server

Start the MCP server to expose your MySQL database as a tool. This enables AI assistants to query your database using natural language.

```bash
python mysql_mcp_server.py
```

### 6. Use SQL Assistant

Try the AI assistant locally to interact with your database using natural language:

```bash
python sql_assistant.py
```

Example interaction:

```bash
You: show me first 5 employees
AI: 
{'id': 1, 'name': 'Alice', 'role': 'Engineer'}
{'id': 2, 'name': 'Bob', 'role': 'Manager'}
...
```

## Why MCP?

**Without MCP:**

You must write raw SQL queries manually (e.g., `SELECT * FROM employees LIMIT 5;`). This requires SQL knowledge and can be cumbersome for non-technical users.

**With MCP:**

You simply type natural language requests (e.g., "Show me first 5 employees"). The AI translates these requests into SQL, executes them against the database, and returns the results in a human-readable format.

### Benefits of MCP in this project:

- **Abstraction**: Users do not need SQL knowledge to interact with the database.
- **Portability**: Works seamlessly with any LLM (OpenAI, Claude, Gemini, etc.), providing flexibility in AI model choice.
- **Scalability**: The framework is designed to be extensible, allowing for easy integration of more tools (e.g., APIs, file systems, analytics platforms) in the future.


