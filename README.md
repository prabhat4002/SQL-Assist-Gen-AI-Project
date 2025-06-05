
# SQL-assist: Natural Language to SQL Query Generator

## Overview
SQL-assist is a Streamlit-based web application that converts natural language commands into executable SQLite queries, enabling non-technical users to interact with databases. It uses LangChain and Groq's LLaMA3-8b model to generate SQL queries based on database schemas.

## Features
- **Natural Language Processing**: Converts English commands into valid SQLite queries using Groq's LLaMA3-8b model.
- **Dynamic Schema Integration**: Retrieves and uses database schema to ensure query accuracy.
- **User-Friendly Interface**: Built with Streamlit for seamless interaction and result visualization.
- **Real-Time Query Execution**: Executes generated queries on an SQLite database and displays results or updated table state.
- **Sample Database**: Includes a pre-populated `employees` table for testing.

## Technologies Used
- **Python**: Core programming language.
- **Streamlit**: Web application framework for the user interface.
- **SQLite**: Lightweight database for query execution.
- **LangChain**: Framework for integrating LLMs with external data.
- **Groq LLM (LLaMA3-8b)**: Language model for generating SQL queries.
- **Pandas**: For displaying query results in tabular format.

## Installation
1. Clone the Repository
bashgit clone https://github.com/yourusername/sql-assist.git
cd sql-assist
2. Install Dependencies
Ensure Python 3.8+ is installed, then install required packages:
bashpip install -r requirements.txt
3. Set Up Environment Variables
Create a .env file in the project root and add your Groq API key:
GROQ_API_KEY=your_groq_api_key_here
Obtain your API key from console.groq.com.
4. Run the Application
Start the Streamlit app:
bashstreamlit run app.py

Requirements
--
Create a requirements.txt file with the following content:
streamlit==1.31.0
sqlite3
pandas==2.2.2
langchain==0.3.1
langchain-groq
python-dotenv==1.0.1

Usage

Launch the app using the command above. It will open in your default web browser.
Enter your Groq API key and database name in the sidebar (defaults to my_database.db).
View the database schema in the expandable section for reference.
Enter a natural language command (e.g., "Show all employees") in the chat input box.
The app generates and executes the SQL query, displaying the query and results (for SELECT queries) or the updated table state (for INSERT/UPDATE/DELETE queries).


Sample Commands

Show all employees
Get employees in Engineering
Find employees with salary above 70000
Add a new employee named Mike in Sales with 68000 salary hired on 2024-03-15
Update John Doe's salary to 80000
Delete employee with id 2


Database Schema
The default database (my_database.db) contains an employees table with the following structure:
Table: employees
- id (INTEGER)
- name (TEXT)
- department (TEXT)
- salary (REAL)
- hire_date (TEXT)

Notes

Ensure a stable internet connection for Groq API calls.
The app uses a fixed model (llama3-8b-8192) and temperature (0.1) for consistent query generation.
Adjust the max tokens slider in the sidebar to control response length (default: 500, range: 100-2000).
The app creates a sample employees table with four records if none exists.


License
This project is licensed under the MIT License - see the LICENSE file for details.

Contributing

Fork the repository
Create your feature branch (git checkout -b feature/AmazingFeature)
Commit your changes (git commit -m 'Add some AmazingFeature')
Push to the branch (git push origin feature/AmazingFeature)
Open a Pull Request
