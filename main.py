import streamlit as st
import sqlite3
import pandas as pd
from langchain.prompts import PromptTemplate
from langchain_groq import ChatGroq
from dotenv import load_dotenv
import os

# Load environment variables
load_dotenv()

# Streamlit page configuration
st.set_page_config(
    page_title="SQL-assist",
    page_icon="🧑‍💻",
    layout="wide"
)

# Initialize session state
if 'messages' not in st.session_state:
    st.session_state.messages = []

# Set default values
DEFAULT_MODEL = "llama3-8b-8192"  # Fixed model
DEFAULT_TEMPERATURE = 0.1  # Fixed temperature
DEFAULT_MAX_TOKENS = 500

# Sidebar configuration
with st.sidebar:
    st.title("⚙️ Configuration")
    groq_api_key = os.getenv("GROQ_API_KEY") or st.text_input("Groq API Key", type="password", help="Get this from console.groq.com")
    db_name = st.text_input("Database Name", value="my_database.db")
    max_tokens = st.slider("Max Response Tokens", 100, 2000, DEFAULT_MAX_TOKENS)

# Main UI
st.title("🧑‍💻SQL-assist")
st.markdown("""
Speak in English, and let the app generate and execute SQL queries on your SQLite database!
""")

# Create or update sample database
def init_sample_db(db_name):
    # Using check_same_thread=False to avoid thread issues with Streamlit
    conn = sqlite3.connect(db_name, check_same_thread=False)
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS employees (
            id INTEGER PRIMARY KEY,
            name TEXT,
            department TEXT,
            salary REAL,
            hire_date TEXT
        )
    """)
    cursor.execute("SELECT COUNT(*) FROM employees")
    if cursor.fetchone()[0] == 0:
        sample_data = [
            (1, "John Doe", "Engineering", 75000, "2023-01-15"),
            (2, "Jane Smith", "Marketing", 65000, "2022-06-20"),
            (3, "Bob Johnson", "Engineering", 80000, "2021-09-01"),
            (4, "Alice Brown", "HR", 60000, "2023-03-10")
        ]
        cursor.executemany("INSERT INTO employees VALUES (?, ?, ?, ?, ?)", sample_data)
    conn.commit()
    return conn

# Initialize Groq LLM
def init_groq_llm(groq_api_key, max_tokens):
    if not groq_api_key:
        raise ValueError("Groq API key is required")
    return ChatGroq(
        api_key=groq_api_key,
        model_name=DEFAULT_MODEL,
        temperature=DEFAULT_TEMPERATURE,
        max_tokens=max_tokens
    )

# SQL Generation Prompt
sql_prompt = PromptTemplate(
    input_variables=["input", "schema"],
    template="""
You are an expert SQL database engineer. Convert this natural language command into a valid SQLite SQL query.

Database schema:
{schema}

Command: {input}

Provide only the SQL query without any explanation or additional text. Ensure it's valid SQLite syntax.
"""
)

# Get database schema
def get_schema_info(conn):
    cursor = conn.cursor()
    tables = cursor.execute("SELECT name FROM sqlite_master WHERE type='table';").fetchall()
    
    schema_info = ""
    for table in tables:
        table_name = table[0]
        columns = cursor.execute(f"PRAGMA table_info({table_name})").fetchall()
        schema_info += f"Table: {table_name}\n"
        for col in columns:
            schema_info += f"- {col[1]} ({col[2]})\n"
        schema_info += "\n"
    
    return schema_info

# Initialize database connection once
# Use check_same_thread=False to allow SQLite to be used across threads
@st.cache_resource
def get_database_connection(db_path):
    return init_sample_db(db_path)

# Get the connection
conn = get_database_connection(db_name)

# Display database schema
with st.expander("📋 Database Schema"):
    try:
        schema_info = get_schema_info(conn)
        st.text(schema_info)
        
        st.write("Sample commands:")
        st.write("- Show all employees")
        st.write("- Get employees in Engineering")
        st.write("- Find employees with salary above 70000")
        st.write("- Add a new employee named Mike in Sales with 68000 salary hired on 2024-03-15")
        st.write("- Update John Doe's salary to 80000")
        st.write("- Delete employee with id 2")
    except Exception as e:
        st.error(f"Error getting schema: {str(e)}")

# Main application logic
if groq_api_key:
    try:
        groq_llm = init_groq_llm(groq_api_key, max_tokens)
        
        try:
            schema_info = get_schema_info(conn)
        except Exception as schema_err:
            st.error(f"Error fetching schema: {str(schema_err)}")
            schema_info = "Table: employees\n- id (INTEGER)\n- name (TEXT)\n- department (TEXT)\n- salary (REAL)\n- hire_date (TEXT)"
        
        # Display chat messages
        st.markdown("---")
        st.subheader("💬 Command Interface")
        
        for message in st.session_state.messages:
            with st.chat_message(message["role"]):
                st.markdown(message["content"])
        
        # User input
        if prompt := st.chat_input("Enter your command in English..."):
            with st.chat_message("user"):
                st.markdown(prompt)
            st.session_state.messages.append({"role": "user", "content": prompt})
            
            with st.chat_message("assistant"):
                with st.spinner("Processing command..."):
                    try:
                        # Generate SQL query using LLM
                        sql_chain_input = {"input": prompt, "schema": schema_info}
                        sql_query = groq_llm.invoke(sql_prompt.format(**sql_chain_input)).content.strip()
                        
                        # Display generated SQL
                        st.code(sql_query, language="sql")
                        
                        # Execute SQL query
                        cursor = conn.cursor()
                        if sql_query.strip().lower().startswith(("select", "pragma", "explain")):
                            # For SELECT queries, show results
                            results = cursor.execute(sql_query).fetchall()
                            if cursor.description:  # Check if there are column descriptions
                                columns = [desc[0] for desc in cursor.description]
                                if results:
                                    st.write("Results:")
                                    df = pd.DataFrame(results, columns=columns)
                                    st.dataframe(df)
                                else:
                                    st.write("No results found.")
                            else:
                                st.write("Query executed (no results to display).")
                        else:
                            # For other queries (INSERT, UPDATE, DELETE, etc.)
                            cursor.execute(sql_query)
                            conn.commit()
                            st.success("Command executed successfully!")
                            
                            # Show current table state after modification
                            st.write("Current table state:")
                            try:
                                # Try to determine the table that was affected
                                table_name = "employees"  # Default to employees table
                                
                                # Try to extract table name from the query
                                if "into " in sql_query.lower():
                                    parts = sql_query.lower().split("into ")
                                    if len(parts) > 1:
                                        table_name = parts[1].split()[0].strip()
                                elif "update " in sql_query.lower():
                                    parts = sql_query.lower().split("update ")
                                    if len(parts) > 1:
                                        table_name = parts[1].split()[0].strip()
                                elif "from " in sql_query.lower():
                                    parts = sql_query.lower().split("from ")
                                    if len(parts) > 1:
                                        table_name = parts[1].split()[0].strip()
                                
                                # Show the updated table
                                results = cursor.execute(f"SELECT * FROM {table_name}").fetchall()
                                columns = [desc[0] for desc in cursor.description]
                                df = pd.DataFrame(results, columns=columns)
                                st.dataframe(df)
                            except Exception as table_err:
                                st.warning(f"Could not show updated table: {str(table_err)}")
                        
                        # Store message in history
                        result_message = f"Generated SQL: ```sql\n{sql_query}\n```\n\nQuery executed successfully."
                        st.session_state.messages.append({
                            "role": "assistant", 
                            "content": result_message
                        })
                    except Exception as e:
                        error_message = f"Error: {str(e)}"
                        st.error(error_message)
                        st.session_state.messages.append({
                            "role": "assistant", 
                            "content": f"Error executing query: {error_message}"
                        })
    except Exception as e:
        st.error(f"Error initializing LLM: {str(e)}")
        st.write("Check your API key and internet connection.")
else:
    st.warning("Please provide your Groq API key in the sidebar or .env file.")

st.markdown("---")
st.caption("SQLassist")