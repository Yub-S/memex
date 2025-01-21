import snowflake.connector
import os
from dotenv import load_dotenv
load_dotenv()

def create_snowflake_connection():
    """Create connection to Snowflake"""
    conn = snowflake.connector.connect(
        user=os.getenv("SNOWFLAKE_USER"),
        password=os.getenv("SNOWFLAKE_PASSWORD"),
        account=os.getenv("SNOWFLAKE_ACCOUNT"),
        warehouse='COMPUTE_WH'
    )
    return conn

def execute_setup():
    """Execute all database setup operations"""
    conn = create_snowflake_connection()
    cursor = conn.cursor()

    # Create database and schema
    setup_commands = [
        "CREATE DATABASE IF NOT EXISTS MEMEX",
        "USE DATABASE MEMEX",
        "CREATE SCHEMA IF NOT EXISTS DATA",
        
        # Create table
        """
        CREATE OR REPLACE TABLE TEXT_PARAGRAPHS_TABLE (
            ID NUMBER AUTOINCREMENT PRIMARY KEY,
            TEXT_CONTENT VARCHAR(16777216)
        )
        """,
        
        # Create search service
        """
        CREATE OR REPLACE CORTEX SEARCH SERVICE MEMEX_SEARCH_SERVICE
        ON TEXT_CONTENT
        WAREHOUSE = COMPUTE_WH
        TARGET_LAG = '1 minute'
        AS (
            SELECT TEXT_CONTENT
            FROM TEXT_PARAGRAPHS_TABLE
        )
        """
    ]

    try:
        # Execute all setup commands
        for command in setup_commands:
            cursor.execute(command)
            conn.commit()
        # Query and print results
        cursor.execute("SELECT * FROM TEXT_PARAGRAPHS_TABLE")
        results = cursor.fetchall()
        print("\nQuery Results:")
        for row in results:
            print(row)

    except Exception as e:
        print(f"An error occurred: {e}")
    
    finally:
        cursor.close()
        conn.close()

def info_check():
    """check the talbes and data in the database"""

    conn = create_snowflake_connection()
    cursor = conn.cursor()
    try:
        cursor.execute("USE DATABASE MEMEX")
        cursor.execute("USE SCHEMA DATA")
        # Query and print results
        cursor.execute("SELECT * FROM TEXT_PARAGRAPHS_TABLE")
        results = cursor.fetchall()
        print("\nQuery Results:")
        for row in results:
            print(row)

    except Exception as e:
        print(f"An error occurred: {e}")
    
    finally:
        cursor.close()
        conn.close()

if __name__ == "__main__":
    execute_setup()
    #info_check()