import streamlit as st
import sqlite3
import pandas as pd
from pathlib import Path
from dotenv import load_dotenv
import os
import logging
from langchain.agents import create_sql_agent
from langchain.agents.agent_types import AgentType
from langchain.callbacks import StreamlitCallbackHandler
from langchain.agents.agent_toolkits import SQLDatabaseToolkit
from langchain.sql_database import SQLDatabase
from langchain_groq import ChatGroq
from sqlalchemy import create_engine

# Configure logging
logging.basicConfig(level=logging.DEBUG)

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
DEFAULT_MODEL = "llama3-8b-8192"
DEFAULT_TEMPERATURE = 0.1
DEFAULT_MAX_TOKENS = 500

# Sidebar configuration
with st.sidebar:
    st.title("⚙️ Configuration")
    groq_api_key = os.getenv("GROQ_API_KEY") or st.text_input("Groq API Key", type="password", help="Get this from console.groq.com")
    db_name = st.text_input("Database Name", value="my_database.db")
    init_sample_data = st.checkbox("Initialize with sample data", value=True)
    max_tokens = st.slider("Max Response Tokens", 100, 2000, DEFAULT_MAX_TOKENS)

# Main UI
st.title("🧑‍💻 SQL-assist")
st.markdown("""
Speak in English, and let the app analyze and modify your SQLite database using SQL!
""")

# Create or update sample database
def init_sample_db(db_name, include_sample_data=True):
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
    
    if include_sample_data:
        cursor.execute("DELETE FROM employees")
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
        groq_api_key=groq_api_key,
        model_name=DEFAULT_MODEL,
        temperature=DEFAULT_TEMPERATURE,
        max_tokens=max_tokens,
        streaming=True
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

# Custom SQL execution for modification queries
def execute_modification_query(conn, llm, query_text):
    prompt = f"""
    Given this database schema:
    {get_schema_info(conn)}
    
    Convert this natural language request into a valid SQLite SQL query:
    "{query_text}"
    
    Return only the SQL query without any explanation.
    """
    
    sql_query = llm.invoke(prompt).content.strip()
    logging.debug(f"Generated Modification SQL: {sql_query}")
    
    cursor = conn.cursor()
    try:
        cursor.execute(sql_query)
        conn.commit()
        return f"Successfully executed: {sql_query}"
    except Exception as e:
        conn.rollback()
        raise Exception(f"SQL Execution Error: {str(e)}")

# Initialize SQLite database connection
@st.cache_resource
def get_sqlite_database(db_path, init_with_sample=True):
    conn = init_sample_db(db_path, init_with_sample)
    def creator():
        return conn
    engine = create_engine('sqlite://', creator=creator)
    return SQLDatabase(engine), conn

# Check for destructive operations
def is_destructive_query(query):
    danger_words = ['delete', 'drop', 'truncate', 'update', 'insert']
    return any(word in query.lower() for word in danger_words)

# Main application logic
try:
    if not groq_api_key:
        st.warning("Please provide your Groq API key in the sidebar or .env file.")
        st.stop()
    
    # Initialize the database and LLM
    db, conn = get_sqlite_database(db_name, init_sample_data)
    llm = init_groq_llm(groq_api_key, max_tokens)
    
    # Create SQL agent for SELECT queries
    toolkit = SQLDatabaseToolkit(db=db, llm=llm)
    agent = create_sql_agent(
        llm=llm,
        toolkit=toolkit,
        verbose=True,
        agent_type=AgentType.ZERO_SHOT_REACT_DESCRIPTION,
        handle_parsing_errors=True
    )
    
    # Display database schema
    with st.expander("📋 Database Schema"):
        try:
            schema_info = get_schema_info(conn)
            st.text(schema_info)
            st.write("Sample commands:")
            st.write("- Show all employees")
            st.write("- YES Delete employee with id 1")
            st.write("- YES Update salary to 90000 for Bob Johnson")
            st.write("- YES Insert a new employee named 'Mike Ross' in Engineering with salary 70000")
        except Exception as e:
            st.error(f"Error getting schema: {str(e)}")
    
    # Display chat messages
    st.markdown("---")
    st.subheader("💬 Command Interface")
    
    for message in st.session_state.messages:
        with st.chat_message(message["role"]):
            st.markdown(message["content"])
    
    # User input
    if user_query := st.chat_input("Ask anything about the database..."):
        st.session_state.messages.append({"role": "user", "content": user_query})
        st.chat_message("user").write(user_query)
        
        with st.chat_message("assistant"):
            try:
                if is_destructive_query(user_query):
                    st.warning("Destructive operation detected. Please confirm with 'YES' prefix.")
                    if not user_query.upper().startswith("YES"):
                        response = "Please confirm destructive operation by starting query with 'YES'"
                    else:
                        response = execute_modification_query(conn, llm, user_query[4:])  # Remove YES prefix
                else:
                    streamlit_callback = StreamlitCallbackHandler(st.container())
                    response = agent.run(user_query, callbacks=[streamlit_callback])
                
                st.write(response)
                st.session_state.messages.append({"role": "assistant", "content": response})
            except Exception as e:
                error_message = f"Error: {str(e)}"
                st.error(error_message)
                st.session_state.messages.append({
                    "role": "assistant", 
                    "content": error_message
                })

except Exception as e:
    st.error(f"Application Error: {str(e)}")
    st.write("Check your configuration and try again.")

st.markdown("---")
st.caption("SQLassist")