from snowflake.snowpark.session import Session
from snowflake.cortex import Complete
from snowflake.core import Root
from dotenv import load_dotenv
from typing import List
from datetime import datetime
from trulens.core import TruSession
from trulens.connectors.snowflake import SnowflakeConnector
from trulens.apps.custom import instrument
from trulens.core.guardrails.base import context_filter
import os
from trulens.providers.cortex.provider import Cortex
from trulens.core import Feedback
from trulens.core import Select
import numpy as np

load_dotenv()

def establish_connection():
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
    return snowpark_session

class DateStandardizer:
    def __init__(self, session):
        self.session = session
    
    def standardize_dates(self, text, is_query=False):
        try:
            current_date = self.get_current_date_info()
            
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
                   "(conversation happened on {current_date['full_date']} at {current_date['time']})"
                
                Original text: "{text}"
                Only output the converted text with no explanations or additional text."""
            
            # Pass session explicitly to Complete
            response = Complete("mistral-large2", prompt=prompt, session=self.session)
            standardized_text = response if response else text
            return standardized_text.strip('"').strip()
        
        except Exception as e:
            print(f"Error standardizing dates: {e}")
            return text

    def get_current_date_info(self):
        current = datetime.now()
        return {
            'date': current.strftime('%Y-%m-%d'),
            'day': current.strftime('%A'),
            'full_date': current.strftime('%A, %B %d, %Y'),
            'time': current.strftime('%I:%M %p')
        }

class CortexSearchRetriever:
    def __init__(self, snowpark_session, limit_to_retrieve: int = 4):
        self._snowpark_session = snowpark_session
        self._limit_to_retrieve = limit_to_retrieve
        self._date_standardizer = DateStandardizer(snowpark_session)

    def retrieve(self, query: str) -> List[str]:
        root = Root(self._snowpark_session)
        cortex_search_service = (
            root.databases[os.getenv("SNOWFLAKE_DATABASE")]
            .schemas[os.getenv("SNOWFLAKE_SCHEMA")]
            .cortex_search_services["MINDBOOK_SEARCH_SERVICE"]
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
    def __init__(self, session):
        self.session = session
        self.retriever = CortexSearchRetriever(snowpark_session=session, limit_to_retrieve=4)
        self.date_standardizer = DateStandardizer(session)
        
        # Initialize Cortex provider
        self.provider = Cortex(
            session,
            model_engine="mistral-large2",
        )
        
        # Initialize feedback score
        self.context_relevance_score = Feedback(
            self.provider.context_relevance,
            name="Context Relevance"
        )

    def inject_information(self, text_content):
        try:
            standardized_text = self.date_standardizer.standardize_dates(text_content)
            
            query = """
            INSERT INTO TEXT_PARAGRAPHS_TABLE (TEXT_CONTENT)
            VALUES (?)
            """
            result = self.session.sql(query, params=[standardized_text]).collect()
            self.session.sql("COMMIT").collect()
            return True
        except Exception as e:
            print(f"Error injecting information: {e}")
            return False

    @instrument
    def retrieve_context_with_filter(self, query: str) -> list:
        """
        Wrapper method to apply filtering based on context_relevance_score.
        """
        @context_filter(self.context_relevance_score, 0.4, keyword_for_prompt="query")
        def _retrieve(query: str) -> list:
            standard_query = self.date_standardizer.standardize_dates(query, is_query=True)
            return self.retriever.retrieve(standard_query)
        
        return _retrieve(query)

    @instrument
    def generate_completion(self, query: str, context_str: list) -> str:
        prompt = f"""You are a personal AI assistant who helps the user recall and elaborate on their past thoughts, plans, and discussions.
        You have access to the user's personal notes and memories.

        Context of previous discussions:
        <context>
        {context_str}
        </context>

        User's current question: {query}

        Based on the context and your understanding, provide a helpful and precise response.
        If the context directly addresses the question, use those details.
        If not, respond based on the most relevant information available.
        Always be supportive and sound like a trusted personal assistant.

        Respond with a clear, natural text response. Do not use any special formatting or JSON structure.
        """
        return Complete("mistral-large2", prompt, session=self.session)

    @instrument
    def query(self, query: str) -> str:
        context_str = self.retrieve_context_with_filter(query)
        print(context_str)
        return self.generate_completion(query, context_str)

def main():
    # Creating a rag
    session = establish_connection()
    rag = RAG_from_scratch(session)
    
if __name__ == "__main__":
    main()