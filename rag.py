
from snowflake.snowpark.session import Session
from snowflake.cortex import Complete
from snowflake.core import Root
from dotenv import load_dotenv
from typing import List
from datetime import datetime
import os

load_dotenv()

connection_parameters = {
    "account": os.getenv("SNOWFLAKE_ACCOUNT"),
    "user": os.getenv("SNOWFLAKE_USER"),
    "password": os.getenv("SNOWFLAKE_PASSWORD"),
    "warehouse": os.getenv("SNOWFLAKE_WAREHOUSE"),
    "database": os.getenv("SNOWFLAKE_DATABASE"),
    "schema": os.getenv("SNOWFLAKE_SCHEMA"),
    "role": os.getenv("SNOWFLAKE_ROLE"),
}

snowpark_session = Session.builder.configs(connection_parameters).create()

root = Root(snowpark_session)
=======
from snowflake.connector import connect
from snowflake.snowpark.session import Session
from snowflake.core import Root
import os
from dotenv import load_dotenv
import json
from datetime import datetime

# Load environment variables
load_dotenv()

# Snowflake connection configuration remains the same
def create_snowflake_session():
    connection_parameters = {
        "account": os.getenv("SNOWFLAKE_ACCOUNT"),
        "user": os.getenv("SNOWFLAKE_USER"),
        "password": os.getenv("SNOWFLAKE_PASSWORD"),
        "warehouse": os.getenv("SNOWFLAKE_WAREHOUSE"),
        "database": os.getenv("SNOWFLAKE_DATABASE"),
        "schema": os.getenv("SNOWFLAKE_SCHEMA"),
        "role": os.getenv("SNOWFLAKE_ROLE"),
        "login_timeout": 30,
        "network_timeout": 30,
        "retry_on_connection_error": True,
        "max_connection_retries": 3
    }
    
    try:
        session = Session.builder.configs(connection_parameters).create()
        return session
    except Exception as e:
        print(f"Failed to create Snowflake session: {e}")
        return None

# Initialize session with error handling
session = create_snowflake_session()
if session is None:
    print("Could not establish connection to Snowflake")

root = Root(session)

# Configuration
DATABASE = os.getenv("SNOWFLAKE_DATABASE")
SCHEMA = os.getenv("SNOWFLAKE_SCHEMA")
TABLE = "TEXT_PARAGRAPHS_TABLE"
CORTEX_SEARCH_SERVICE = "CC_SEARCH_SERVICE_CS"

#svc = root.databases[DATABASE].schemas[SCHEMA].cortex_search_services[CORTEX_SEARCH_SERVICE]

def inject_information(text_content):
    try:
        # Standardize dates before injection
        standardized_text = standardize_dates(text_content)
        
        query = """
        INSERT INTO TEXT_PARAGRAPHS_TABLE (TEXT_CONTENT)
        VALUES (?)
        """
        snowpark_session.sql(query, params=[standardized_text]).collect()
        return True
    except Exception as e:
        print(f"Error injecting information: {e}")
        return False

def get_current_date_info():
    current = datetime.now()
    return {
        'date': current.strftime('%Y-%m-%d'),
        'day': current.strftime('%A'),
        'full_date': current.strftime('%A, %B %d, %Y'),
        'time': current.strftime('%I:%M %p')
    }

def standardize_dates(text, is_query=False):
    try:
        current_date = get_current_date_info()
        
        # Different prompts for input text vs query
        if is_query:
            prompt = f"""Current date is {current_date['full_date']}.
            Convert any relative date references (today, tomorrow, next week, etc.) in this query to actual dates.if there is nothing relative, ignore the date provided, and just provide the query as it is.
            Original query: "{text}"
            Only output the converted query with no explanations or additional text."""
        else:
            prompt = f"""Current date is {current_date['full_date']} at {current_date['time']}.
            1. Convert any relative date references (today, tomorrow, next week, etc.) in this text to their actual dates.
            2. Add 'on [date] (with day also)' where appropriate but don't change any other information like the actual text.
            3. At the end of the text, add a new line and append:
               "(Note recorded on {current_date['full_date']} at {current_date['time']})"
            
            Original text: "{text}"
            Only output the converted text with no explanations or additional text."""
        
        # Make LLM call using existing Snowflake Mixtral integration
        response = snowpark_session.sql("""

            select snowflake.cortex.complete(?, ?) as response
        """, params=['mistral-large2', prompt]).collect()
        
        standardized_text = response[0].RESPONSE if response else text
        return standardized_text.strip('"').strip()
    
    except Exception as e:
        print(f"Error standardizing dates: {e}")
        return text



class CortexSearchRetriever:

    def __init__(self, snowpark_session: Session, limit_to_retrieve: int = 3):
        self._snowpark_session = snowpark_session
        self._limit_to_retrieve = limit_to_retrieve

    def retrieve(self, query: str) -> List[str]:
        root = Root(self._snowpark_session)
        cortex_search_service = (
            root.databases[os.getenv("SNOWFLAKE_DATABASE")]
            .schemas[os.getenv("SNOWFLAKE_SCHEMA")]
            .cortex_search_services["CC_SEARCH_SERVICE_CS"]
        )
        resp = cortex_search_service.search(
            query=query,
            columns=["TEXT_CONTENT"],
            limit=self._limit_to_retrieve,
        )

        if resp.results:
            return [curr["TEXT_CONTENT"] for curr in resp.results]
        else:
            return []


class RAG_from_scratch:

    def __init__(self):
        self.retriever = CortexSearchRetriever(snowpark_session=snowpark_session, limit_to_retrieve=4)

    def retrieve_context(self, query: str) -> list:
        """
        Retrieve relevant text from vector store.
        """
        standard_query = standardize_dates(query,is_query=True)
        return self.retriever.retrieve(standard_query)

    def generate_completion(self, query: str, context_str: list) -> str:
        """
        Generate answer from context.
        """
        prompt = f"""You are a personal AI assistant who helps the user recall and elaborate on their past thoughts, plans, and discussions.ext):
        You have access to the user's personal notes and memories.

        Context of previous discussions:
        <context>
        {context_text}

        User's current question: {query}

        Based on the context and your understanding, provide a helpful and precise response.
        If the context directly addresses the question, use those details.
        If not, respond based on the most relevant information available.
        Always be supportive and sound like a trusted personal assistant.

        Respond with a clear, natural text response. Do not use any special formatting or JSON structure.
        """
        return Complete("mistral-large2", prompt)

    def query(self, query: str) -> str:
        context_str = self.retrieve_context(query)
        return self.generate_completion(query, context_str)


rag = RAG_from_scratch() 
print(rag.query("what was my christmas this year like"))
