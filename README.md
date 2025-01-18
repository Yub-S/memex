# memex
memex is your personal memory companion designed to preserve your memories, thoughts, and experiences. Unlike traditional note-taking tools, it helps you reconnect with your past self by bringing memories to life in a meaningful way.

## Project Structure
```bash
├── app.py           # Streamlit frontend interface
├── rag.py           # RAG implementation using Snowflake Cortex Search and mixtral llm
├── snowflake.py     # Initial Snowflake setup (database, schema, table, search engine)
└── trulens.ipynb       # RAG evaluation using TruLens
```

## How to Run Locally

1. Clone the repository:

    ```bash
    git clone https://github.com/Yub-S/memex
    cd memex
    ```

2. Set up the virtual environment:

    On Mac/Linux:
    ```bash
    python -m venv venv
    source venv/bin/activate
    ```

    On Windows:
    ```bash
    python -m venv venv
    venv\Scripts\activate
    ```

3. Install the required dependencies:

    ```bash
    pip install -r requirements.txt
    ```

4. Set up the `.env` file with your Snowflake credentials:

    ```env
    SNOWFLAKE_ACCOUNT="your-account"
    SNOWFLAKE_USER="username"
    SNOWFLAKE_PASSWORD="password"
    ```

5. Run Snowflake setup:

    ```bash
    python snowflake.py
    ```

6. Update the `.env` file with the following Snowflake details:

    ```env
    SNOWFLAKE_WAREHOUSE="COMPUTE_WH"
    SNOWFLAKE_DATABASE="MINDBOOKLM"
    SNOWFLAKE_SCHEMA="DATA"
    SNOWFLAKE_ROLE="ACCOUNTADMIN"
    SNOWFLAKE_CORTEX_SEARCH="MINDBOOK_SEARCH_SERVICE"
    ```

    **Note:** Adjust these values if you modified them in `snowflake.py`.

7. Run the app:

    ```bash
    streamlit run app.py
    ```

    The app should now be running. You can inject memories in "Inject Mode" and chat with Memex in "Chat Mode".

## RAG Evaluation with TruLens

Check out `trulens.ipynb` for details on how TruLens is used to measure and improve the RAG (Retrieval-Augmented Generation) system in memex.
