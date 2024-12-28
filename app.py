import streamlit as st
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
        st.error(f"Failed to create Snowflake session: {e}")
        return None

# Initialize session with error handling
session = create_snowflake_session()
if session is None:
    st.error("Could not establish connection to Snowflake")
    st.stop()

root = Root(session)

# Configuration
DATABASE = os.getenv("SNOWFLAKE_DATABASE")
SCHEMA = os.getenv("SNOWFLAKE_SCHEMA")
TABLE = "TEXT_PARAGRAPHS_TABLE"
CORTEX_SEARCH_SERVICE = "CC_SEARCH_SERVICE_CS"

svc = root.databases[DATABASE].schemas[SCHEMA].cortex_search_services[CORTEX_SEARCH_SERVICE]

# New function to get current date information
def get_current_date_info():
    current = datetime.now()
    return {
        'date': current.strftime('%Y-%m-%d'),
        'day': current.strftime('%A'),
        'full_date': current.strftime('%A, %B %d, %Y'),
        'time': current.strftime('%I:%M %p')
    }

# New function to standardize dates in text
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
        response = session.sql("""
            select snowflake.cortex.complete(?, ?) as response
        """, params=['mistral-large2', prompt]).collect()
        
        standardized_text = response[0].RESPONSE if response else text
        return standardized_text.strip('"').strip()
    
    except Exception as e:
        st.error(f"Error standardizing dates: {e}")
        return text

# Your existing functions remain the same
def inject_information(text_content):
    try:
        # Standardize dates before injection
        standardized_text = standardize_dates(text_content)
        
        query = """
        INSERT INTO TEXT_PARAGRAPHS_TABLE (TEXT_CONTENT)
        VALUES (?)
        """
        session.sql(query, params=[standardized_text]).collect()
        return True
    except Exception as e:
        st.error(f"Error injecting information: {e}")
        return False

def get_similar_chunks(query):
    try:
        response = svc.search(query, ["TEXT_CONTENT"], limit=3)
        context = response.json()
        return context
    except Exception as e:
        st.error(f"Error retrieving context: {e}")
        import traceback
        st.error(traceback.format_exc())
        return None

def create_prompt(query, context):
    if not context:
        return query
    
    try:
        if isinstance(context, str):
            try:
                context_dict = json.loads(context)
            except json.JSONDecodeError:
                st.error("Could not parse context as JSON")
                context_text = context
                return query
        else:
            context_dict = context
        
        context_text = "\n".join([
            item.get('TEXT_CONTENT', '') 
            for item in context_dict.get('results', [])
        ])
        
        prompt = f"""You are a personal AI assistant who helps the user recall and elaborate on their past thoughts, plans, and discussions. 
        You have access to the user's personal notes and memories.

        Context of previous discussions:
        <context>
        {context_text}
        </context>

        User's current question: {query}

        Based on the context and your understanding, provide a helpful and precise response. 
        If the context directly addresses the question, use those details. 
        If not, respond based on the most relevant information available.
        Always be supportive and sound like a trusted personal assistant.
        """
        
        return prompt
    
    except Exception as e:
        st.error(f"Comprehensive Error extracting context text: {e}")
        import traceback
        st.error(traceback.format_exc())
        return query

def get_llm_response(query):
    try:
        # Standardize dates in the query
        standardized_query = standardize_dates(query, is_query=True)
        
        context = get_similar_chunks(standardized_query)
        prompt = create_prompt(standardized_query, context)
        
        if not prompt:
            return "I couldn't generate a meaningful prompt."
        
        try:
            response = session.sql("""
                select snowflake.cortex.complete(?, ?) as response
            """, params=['mistral-large2', prompt]).collect()
            
            return response[0].RESPONSE if response else "No response generated."
        
        except Exception as e:
            st.error(f"Cortex Complete Error: {e}")
            return f"Error in LLM processing: {str(e)}"
    
    except Exception as e:
        st.error(f"Unexpected error in get_llm_response: {e}")
        return "An unexpected error occurred while processing your request."

def main():
    # Set page configuration
    st.set_page_config(page_title="MindbookLM", layout="wide")
    
    # Custom CSS for the toggle switch
    st.markdown("""
        <style>
        .stRadio [role=radiogroup] {
            display: none;
        }
        </style>
    """, unsafe_allow_html=True)
    
    # Sidebar with enhanced styling
    with st.sidebar:
        st.title("🧠 MindbookLM")
        st.markdown("*Your digital memory companion*")
        st.markdown("---")
        
        # Create a toggle switch using columns with description
        st.markdown("##### Mode Selection")
        st.caption("Toggle to switch between Chat and Memory Storage modes")
        col1, col2, col3 = st.columns([1,2,1])
        with col2:
            mode = st.toggle("Chat Mode", value=True)
        st.caption("Currently in: " + ("Chat Mode" if mode else "Memory Storage Mode"))
        st.markdown("---")

    if 'messages' not in st.session_state:
        st.session_state.messages = []

    if not mode:  # Inject Mode
        st.markdown("### Inject Memory")
        
        new_info = st.text_area(
            label="",
            height=200,
            placeholder="Share your thoughts, experiences, or plans here...",
            key="memory_input"
        )
        
        if st.button("💾 Save Memory"):
            if new_info:
                with st.spinner("Saving your memory..."):
                    if inject_information(new_info):
                        st.success("Memory saved successfully!")
            else:
                st.warning("Please enter a memory to save.")
    
    else:  # Chat Mode
        # Initialize chat interface with minimal header
        for message in st.session_state.messages:
            with st.chat_message(message["role"]):
                st.markdown(message["content"])

        # Chat input
        if prompt := st.chat_input("Ask about your memories..."):
            with st.chat_message("user"):
                st.markdown(prompt)
            st.session_state.messages.append({"role": "user", "content": prompt})

            with st.chat_message("assistant"):
                response = get_llm_response(prompt)
                st.markdown(response)
                st.session_state.messages.append({"role": "assistant", "content": response})

if __name__ == "__main__":
    main()