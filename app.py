import streamlit as st
from rag import RAG_from_scratch, standardize_dates, get_current_date_info, inject_information

def main():
    # Set page configuration
    st.set_page_config(page_title="MindbookLM", layout="wide")
    
    rag = RAG_from_scratch()
    # Custom CSS for the toggle switch
    st.markdown("""
        <style>
        .stRadio [role=radiogroup] {
            display: none;
        }
        </style>
    """, unsafe_allow_html=True)
    
    # Sidebar 
    with st.sidebar:
        st.title("🧠 MindbookLM")
        st.markdown("*Your digital memory companion*")
        st.markdown("---")
        
        # Create a toggle switch using columns with description
        st.markdown("##### Mode Selection")
        st.caption("Toggle to change Mode")
        col1, col2, col3 = st.columns([1,2,1])
        with col2:
            mode = st.toggle("Chat Mode", value=False) 
        st.caption("Currently in: " + ("Chat Mode" if mode else "Memory Storage Mode"))
        st.markdown("---")

    if 'messages' not in st.session_state:
        st.session_state.messages = []

    if not mode:  # Inject Mode 
        st.markdown("### Inject Memory")
        st.markdown("Share your thoughts, experiences, notes or plans below.")
        
        new_info = st.text_area(
            label="",
            height=200,
            placeholder="Type your memory here...",
            key="memory_input"
        )
        
        col1, col2, col3 = st.columns([2,1,2])
        with col2:
            if st.button("💾 Save Memory", use_container_width=True):
                if new_info:
                    with st.spinner("Saving your memory..."):
                        if inject_information(new_info):
                            st.success("Memory saved successfully!")
                else:
                    st.warning("Please enter a memory to save.")
    
    else:  # Chat Mode
        
        for message in st.session_state.messages:
            with st.chat_message(message["role"]):
                st.markdown(message["content"])

        # Chat input
        if prompt := st.chat_input("Ask about your memories..."):
            with st.chat_message("user"):
                st.markdown(prompt)
            st.session_state.messages.append({"role": "user", "content": prompt})

            with st.chat_message("assistant"):
                response = rag.query(prompt)
                st.markdown(response)
                st.session_state.messages.append({"role": "assistant", "content": response})

if __name__ == "__main__":
    main()