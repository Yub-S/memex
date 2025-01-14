import streamlit as st
from rag import RAG_from_scratch, establish_connection, DateStandardizer
import time

def local_css():
    st.markdown("""
        <style>
        /* Custom styling for the main title */
        .main-title {
            color: #1E88E5;
            font-size: 1.8rem !important;
            font-weight: 700;
            margin-bottom: 0;
            display: inline-flex;
            align-items: center;
            gap: 8px;
        }
        
        /* Gradient background for the sidebar */
        section[data-testid="stSidebar"] {
            background-image: linear-gradient(180deg, #f0f8ff, #ffffff);
        }
        
        /* Text area styling */
        .stTextArea textarea {
            border-radius: 10px;
            border: 2px solid #e0e0e0;
            transition: border 0.3s ease;
            font-size: 1.1rem;
        }
        
        .stTextArea textarea:focus {
            border-color: #1E88E5;
            box-shadow: 0 0 0 2px rgba(30,136,229,0.2);
        }
        
        /* Custom button styling */
        .stButton button {
            border-radius: 4px;
            transition: all 0.3s ease;
            background-color: #1E88E5;
            color: white;
            font-weight: 500;
            padding: 0.3rem 1rem;
            font-size: 0.9rem;
            margin-top: 0.5rem;
        }
        
        .stButton button:hover {
            transform: translateY(-2px);
            box-shadow: 0 4px 12px rgba(0,0,0,0.1);
            background-color: #1976D2;
        }

        /* Modern heading styles */
        .modern-header {
            font-size: 2.2rem !important;
            font-weight: 600 !important;
            color: #1E88E5;
            margin-bottom: 0.5rem !important;
            margin-top: -2rem !important;
        }
        
        .modern-subheader {
            font-size: 1.1rem !important;
            color: #666;
            margin-bottom: 1rem !important;
        }
        
        /* Toggle button styling */
        .stToggleButton {
            scale: 1.2;
        }

        /* Container styling for vertical centering */
        .content-container {
            margin-top: -3rem;
        }

        /* Center align elements */
        div[data-testid="column"] {
            text-align: center;
        }

        /* Message alignment */
        .stSpinner, div.stAlert {
            display: inline-block;
            margin: 0 0.5rem;
        }

        /* Mode indicator styling */
        .mode-indicator {
            padding: 0.5rem 1rem;
            border-radius: 4px;
            margin-top: 0.5rem;
            font-size: 0.9rem;
            text-align: center;
        }

        .chat-mode {
            background-color: rgba(25, 135, 84, 0.1);
            color: rgb(25, 135, 84);
            border: 1px solid rgba(25, 135, 84, 0.2);
        }

        .storage-mode {
            background-color: rgba(13, 110, 253, 0.1);
            color: rgb(13, 110, 253);
            border: 1px solid rgba(13, 110, 253, 0.2);
        }

        /* Updated Typing indicator container */
        .typing-indicator {
            display: inline-flex;
            align-items: center;
            gap: 2px;  /* Reduced gap between dots */
            padding: 8px 12px;  /* Reduced padding */
            background: #f0f2f6;
            border-radius: 12px;  /* Adjusted for smaller size */
            margin: 2px 0;
            transform: scale(0.85);  /* Slightly reduce overall size */
            transform-origin: left center;
        }
        
        /* Updated Dots styling */
        .typing-dot {
            width: 5px;  /* Smaller dots */
            height: 5px;  /* Smaller dots */
            background: #1E88E5;
            border-radius: 50%;
            opacity: 0.7;  /* Slightly increased opacity */
            animation: typing-bubble 0.8s infinite;  /* Faster animation */
        }
        
        /* Updated Animation for each dot */
        @keyframes typing-bubble {
            0%, 100% { transform: translateY(0); }
            50% { transform: translateY(-3px); }  /* Smaller bounce height */
        }
        
        /* Updated Delay for each dot */
        .typing-dot:nth-child(1) { animation-delay: 0s; }
        .typing-dot:nth-child(2) { animation-delay: 0.15s; }  /* Faster sequence */
        .typing-dot:nth-child(3) { animation-delay: 0.3s; }   /* Faster sequence */
        </style>
    """, unsafe_allow_html=True)

def typing_indicator():
    typing_html = """
        <div class="typing-indicator">
            <div class="typing-dot"></div>
            <div class="typing-dot"></div>
            <div class="typing-dot"></div>
        </div>
    """
    return st.markdown(typing_html, unsafe_allow_html=True)

def clear_on_success():
    if 'text_key' not in st.session_state:
        st.session_state.text_key = 0
    st.session_state.text_key += 1

def initialize_session():
    """Initialize Snowflake session and RAG instance if not already in session state"""
    if 'snowflake_session' not in st.session_state:
        st.session_state.snowflake_session = establish_connection()
    
    if 'rag' not in st.session_state:
        st.session_state.rag = RAG_from_scratch(st.session_state.snowflake_session)
        
    if 'date_standardizer' not in st.session_state:
        st.session_state.date_standardizer = DateStandardizer(st.session_state.snowflake_session)


def main():
    st.set_page_config(
        page_title="memex",
        layout="wide",
        initial_sidebar_state="expanded"
    )
    
    local_css()
    
    # Initialize session and RAG
    initialize_session()

    # Sidebar with refined styling
    with st.sidebar:
        st.markdown('<p class="main-title">🧠 memex </p>', unsafe_allow_html=True)
        st.markdown("*Your digital memory companion*")
        st.markdown("---")
        
        st.markdown("##### 🔄 Mode Selection")
        mode = st.toggle("Enable Chat Mode", value=False, key="mode_toggle")
        
        if mode:
            st.markdown('<div class="mode-indicator chat-mode">🗣️ Chat Mode Active</div>', unsafe_allow_html=True)
        else:
            st.markdown('<div class="mode-indicator storage-mode">💾 Memory Storage Mode Active</div>', unsafe_allow_html=True)
        st.markdown("---")

    if 'messages' not in st.session_state:
        st.session_state.messages = []

    if 'show_success' not in st.session_state:
        st.session_state.show_success = False

    # Main content area
    if not mode:  # Memory Storage Mode
        st.markdown('<div class="content-container">', unsafe_allow_html=True)
        st.markdown('<h1 class="modern-header">Inject Memory</h1>', unsafe_allow_html=True)
        st.markdown('<p class="modern-subheader">Share your thoughts, experiences, notes or plans below.</p>', unsafe_allow_html=True)
        
        text_key = f"memory_input_{st.session_state.get('text_key', 0)}"
        new_info = st.text_area(
            label="",
            height=200,
            placeholder="Type your memory here...",
            key=text_key
        )
        
        col1, col2, col3 = st.columns([2,1,2])
        with col2:
            if st.button("💾 Save Memory"):
                if new_info:
                    with st.spinner("Saving..."):
                        success = st.session_state.rag.inject_information(new_info)
                        if success:
                            st.session_state.show_success = True
                        else:
                            st.error("Failed to save memory. Please try again.")
                else:
                    st.warning("Please enter a memory to save.")
        
        with col3:
            if st.session_state.show_success:
                st.success("Memory saved successfully!")
                time.sleep(1.5)  
                st.session_state.show_success = False  
                clear_on_success()
                st.rerun()  

        st.markdown('</div>', unsafe_allow_html=True)
    
    else:  # Chat Mode 
        for message in st.session_state.messages:
            with st.chat_message(message["role"]):
                st.markdown(message["content"])

        if prompt := st.chat_input("Ask about your memories..."):
            with st.chat_message("user"):
                st.markdown(prompt)
            st.session_state.messages.append({"role": "user", "content": prompt})

            assistant_placeholder = st.chat_message("assistant")
            with assistant_placeholder:
                typing_container = st.empty()
                typing_container.markdown(
                    """
                    <div class="typing-indicator">
                        <div class="typing-dot"></div>
                        <div class="typing-dot"></div>
                        <div class="typing-dot"></div>
                    </div>
                    """,
                    unsafe_allow_html=True
                )
                
                response = st.session_state.rag.query(prompt)
                
                typing_container.markdown(response)
                st.session_state.messages.append({"role": "assistant", "content": response})

if __name__ == "__main__":
    main()