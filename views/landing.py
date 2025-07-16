import streamlit as st
import base64
from pathlib import Path

@st.fragment
def render():
    logo_path = Path("assets/toledo.png")
    logo_b64 = base64.b64encode(logo_path.read_bytes()).decode() if logo_path.exists() else ""

    st.markdown(
        """
        <style>
        .landing-container {
            display: flex;
            flex-direction: column;
            justify-content: center;
            align-items: center;
            min-height: 90vh;
            text-align: center;
            background: linear-gradient(-45deg, #1e3a8a, #1e293b, #3b82f6, #1e40af);
            background-size: 300% 300%;
            animation: gradient 8s ease infinite;
        }
        @keyframes gradient {
            0% {background-position: 0% 50%;}
            50% {background-position: 100% 50%;}
            100% {background-position: 0% 50%;}
        }
        .landing-container img {
            width: 180px;
            border-radius: 50%;
            box-shadow: 0 8px 30px rgba(0,0,0,0.3);
        }
        .landing-container h1 {
            color: #ffffff;
            font-size: 2.5rem;
            font-family: 'Montserrat', sans-serif;
            margin: 20px 0 40px 0;
        }
        .stButton>button {
            background-color: #3b82f6;
            color: #ffffff;
            padding: 0.6rem 2rem;
            font-size: 1.1rem;
            border-radius: 8px;
            border: none;
        }
        </style>
        """,
        unsafe_allow_html=True,
    )

    st.markdown(
        f"""
        <div class="landing-container">
            {'<img src="data:image/png;base64,'+logo_b64+'" />' if logo_b64 else ''}
            <h1>Toledo Consultoria</h1>
        </div>
        """,
        unsafe_allow_html=True,
    )

    if st.button("Entrar"):
        st.session_state.page_state = "login"
        st.rerun()
