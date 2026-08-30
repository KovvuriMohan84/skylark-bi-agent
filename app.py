import streamlit as st
import os
from dotenv import load_dotenv
from agent.agent import BIAgent

# Load environment variables (for local development)
load_dotenv()

# App Page Config
st.set_page_config(
    page_title="Skylark Monday BI Agent",
    page_icon="🤖",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ------------------------------------------------------------------ #
#  Sidebar Setup & Keys                                               #
# ------------------------------------------------------------------ #

st.sidebar.title("Configuration ⚙️")

# Read keys from environment / secrets
env_monday_token = os.getenv("MONDAY_API_TOKEN", "")
env_gemini_key = os.getenv("GEMINI_API_KEY", "")
env_deals_board_id = os.getenv("DEALS_BOARD_ID", "5030971872")
env_wo_board_id = os.getenv("WORK_ORDERS_BOARD_ID", "5030971902")

# Check if environment is fully configured
is_configured = bool(env_monday_token and env_gemini_key and env_deals_board_id and env_wo_board_id)

if is_configured:
    # Use environment keys and do not show input fields to hide them from public users
    monday_token = env_monday_token
    gemini_key = env_gemini_key
    deals_board_id = env_deals_board_id
    wo_board_id = env_wo_board_id
    st.sidebar.info("App is running in Production mode. Settings are securely loaded from secrets. 🔒")
else:
    # Show input fields for local testing/setup
    st.sidebar.subheader("Enter Credentials")
    monday_token = st.sidebar.text_input(
        "Monday.com API Token",
        value="",
        type="password",
    )
    gemini_key = st.sidebar.text_input(
        "Gemini API Key",
        value="",
        type="password",
    )
    deals_board_id = st.sidebar.text_input(
        "Deals Board ID",
        value="5030971872",
    )
    wo_board_id = st.sidebar.text_input(
        "Work Orders Board ID",
        value="5030971902",
    )


# ------------------------------------------------------------------ #
#  Agent Initialization & State                                      #
# ------------------------------------------------------------------ #

# Helper to check if credentials are provided
credentials_valid = monday_token and gemini_key and deals_board_id and wo_board_id

if credentials_valid:
    # Initialize agent in session state if not present
    if "agent" not in st.session_state:
        try:
            with st.spinner("Initializing BI Agent & Fetching Boards..."):
                agent = BIAgent(
                    monday_token=monday_token,
                    deals_board_id=deals_board_id,
                    work_orders_board_id=wo_board_id,
                    gemini_key=gemini_key,
                )
                # Fetch data initially
                agent.refresh_data()
                st.session_state.agent = agent
                st.session_state.chat = agent.create_chat_session()
                st.session_state.messages = []
                st.sidebar.success("Connected to Monday.com! ✅")
        except Exception as e:
            st.sidebar.error(f"Initialization Error: {e}")
            st.session_state.pop("agent", None)
else:
    st.sidebar.warning("Please supply your API Keys to start.")

# Add Refresh Button
if "agent" in st.session_state:
    if st.sidebar.button("🔄 Refresh Data from Monday.com"):
        with st.spinner("Refetching board data..."):
            try:
                st.session_state.agent.refresh_data()
                st.sidebar.success("Data refreshed successfully!")
            except Exception as e:
                st.sidebar.error(f"Refresh failed: {e}")

# Pre-canned Questions
st.sidebar.markdown("---")
st.sidebar.subheader("💡 Sample Queries")
suggestions = [
    "How is our pipeline looking this quarter?",
    "Show me a summary of our work orders",
    "How is our Mining sector performing?",
    "Generate a leadership update report",
    "List all data quality issues",
]

for q in suggestions:
    if st.sidebar.button(q, use_container_width=True):
        st.session_state.pending_query = q

# ------------------------------------------------------------------ #
#  Main Chat Interface                                               #
# ------------------------------------------------------------------ #

st.title("📊 Skylark Drones BI Agent")
st.markdown(
    "Ask conversational queries about the sales pipeline (Deals) and operational progress (Work Orders) stored in Monday.com."
)

if "agent" not in st.session_state:
    st.info("👈 Enter your Monday.com and Gemini API Keys in the sidebar to connect the Agent.")
    st.image(
        "https://images.unsplash.com/photo-1460925895917-afdab827c52f?w=1000&auto=format&fit=crop&q=60&ixlib=rb-4.0.3",
        caption="Monday.com Business Intelligence Agent",
    )
else:
    # Print chat history
    for msg in st.session_state.messages:
        with st.chat_message(msg["role"]):
            st.markdown(msg["content"])

    # Determine input (either typed or clicked from sidebar)
    user_input = st.chat_input("Ask a question about the deals or work orders...")
    if "pending_query" in st.session_state:
        user_input = st.session_state.pop("pending_query")

    if user_input:
        # Display user message
        st.session_state.messages.append({"role": "user", "content": user_input})
        with st.chat_message("user"):
            st.markdown(user_input)

        # Generate response
        with st.chat_message("assistant"):
            with st.spinner("Querying Monday.com & analyzing metrics..."):
                try:
                    response = st.session_state.chat.send_message(user_input)
                    ans_text = response.text
                    st.markdown(ans_text)
                    st.session_state.messages.append({"role": "assistant", "content": ans_text})
                except Exception as e:
                    err_msg = f"Error generating answer: {e}"
                    st.error(err_msg)
                    st.session_state.messages.append({"role": "assistant", "content": err_msg})
