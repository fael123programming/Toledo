import streamlit as st
import base64
from pathlib import Path

USERNAME = "welton_toledo"
PASSWORD = "V7#pL9$wXz!F3qRt"

@st.fragment
def render():
    logo_path = Path("assets/toledo.png")
    logo_b64 = base64.b64encode(logo_path.read_bytes()).decode() if logo_path.exists() else ""

    st.markdown(
        """
        <style>
        .login-container {
            display: flex;
            flex-direction: column;
            align-items: center;
            justify-content: center;
            min-height: 80vh;
            text-align: center;
        }
        .login-container img {
            width: 140px;
            border-radius: 50%;
            box-shadow: 0 6px 20px rgba(0,0,0,0.3);
            margin-bottom: 20px;
        }
        .stButton>button {
            background-color: #3b82f6;
            color: #ffffff;
            padding: 0.5rem 1.8rem;
            font-size: 1.05rem;
            border-radius: 8px;
            border: none;
        }
        </style>
        """,
        unsafe_allow_html=True,
    )

    st.markdown(
        f"""
        <div class="login-container">
            {'<img src="data:image/png;base64,'+logo_b64+'" />' if logo_b64 else ''}
            <h2>Área Restrita</h2>
        </div>
        """,
        unsafe_allow_html=True,
    )

    with st.form("login_form"):
        user = st.text_input("Usuário")
        pwd = st.text_input("Senha", type="password")
        submit = st.form_submit_button("Entrar")

    if submit:
        if user == USERNAME and pwd == PASSWORD:
            st.session_state.logged_in = True
            st.session_state.page_state = "app"
            st.success("Login realizado com sucesso!")
            st.rerun()
        else:
            st.error("Usuário ou senha inválidos.")

    if st.button("Voltar"):
        st.session_state.page_state = "landing"
        st.rerun()
