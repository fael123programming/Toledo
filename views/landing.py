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
        .landing-container .stButton {margin-top: 12px;}
        .landing-container .stButton>button {
            background: none;
            border: none;
            color: #ffffff;
            font-size: 1.25rem;
            font-family: 'Montserrat', sans-serif;
            text-decoration: underline;
            opacity: 0;
            pointer-events: none;
            transition: opacity .3s ease;
        }
        .landing-container:hover .stButton>button {
            opacity: 1;
            pointer-events: auto;
            cursor: pointer;
        }
        </style>
        """,
        unsafe_allow_html=True,
    )

    st.markdown(
        f"""
        <div class="landing-container">
            {'<img src="data:image/png;base64,'+logo_b64+'" class="logo-img"/>' if logo_b64 else ''}
            <h1>Toledo Consultoria</h1>
    """,
        unsafe_allow_html=True,
    )
    enter_clicked = st.button("Entrar", key="landing_enter")
    st.markdown("</div>", unsafe_allow_html=True)
    if enter_clicked:
        st.session_state.page_state = "login"
        st.rerun()
