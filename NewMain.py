import streamlit as st
import sqlite3
import pandas as pd
from pathlib import Path
from dotenv import load_dotenv
import os

# LangChain imports
from langchain.agents import create_sql_agent
from langchain.agents.agent_types import AgentType
from langchain.callbacks import StreamlitCallbackHandler
from langchain.agents.agent_toolkits import SQLDatabaseToolkit
from langchain.sql_database import SQLDatabase
from langchain_groq import ChatGroq
from sqlalchemy import create_engine

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
    # Add checkbox to initialize with sample data
    init_sample_data = st.checkbox("Initialize with sample data", value=True)
    max_tokens = st.slider("Max Response Tokens", 100, 2000, DEFAULT_MAX_TOKENS)

# Main UI
st.title("🧑‍💻 SQL-assist")
st.markdown("""
Speak in English, and let the app analyze your SQLite database using SQL!
""")

# Create or update sample database
def init_sample_db(db_name, include_sample_data=True):
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
    
    if include_sample_data:
        cursor.execute("DELETE FROM employees")  # Clear existing data
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

# Initialize SQLite database connection with caching
@st.cache_resource
def get_sqlite_database(db_path, init_with_sample=True):
    conn = init_sample_db(db_path, init_with_sample)
    
    # Create SQLAlchemy engine that reuses the SQLite connection
    def creator():
        return conn
    
    engine = create_engine('sqlite://', creator=creator)
    return SQLDatabase(engine), conn

# Main application logic
try:
    if not groq_api_key:
        st.warning("Please provide your Groq API key in the sidebar or .env file.")
        st.stop()
    
    # Initialize the database
    db, conn = get_sqlite_database(db_name, init_sample_data)
    
    # Initialize the LLM
    llm = init_groq_llm(groq_api_key, max_tokens)
    
    # Create the SQL agent toolkit and agent
    toolkit = SQLDatabaseToolkit(db=db, llm=llm)
    
    agent = create_sql_agent(
        llm=llm,
        toolkit=toolkit,
        verbose=True,
        agent_type=AgentType.ZERO_SHOT_REACT_DESCRIPTION
    )
    
    # Display database schema
    with st.expander("📋 Database Schema"):
        try:
            schema_info = get_schema_info(conn)
            st.text(schema_info)
            
            st.write("Sample commands:")
            st.write("- Show all employees")
            st.write("- Who are the engineering employees?") 
            st.write("- Find employees with salary above 70000")
            st.write("- What's the average salary by department?")
            st.write("- Who was hired most recently?")
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
                streamlit_callback = StreamlitCallbackHandler(st.container())
                response = agent.run(user_query, callbacks=[streamlit_callback])
                #response = agent.run(user_query, callbacks=[streamlit_callback], handle_parsing_errors=True)
                st.session_state.messages.append({"role": "assistant", "content": response})
                st.write(response)
            except Exception as e:
                error_message = f"Error: {str(e)}"
                st.error(error_message)
                st.session_state.messages.append({
                    "role": "assistant", 
                    "content": f"Error: {error_message}"
                })

except Exception as e:
    st.error(f"Application Error: {str(e)}")
    st.write("Check your configuration and try again.")

st.markdown("---")
st.caption("SQLassist")