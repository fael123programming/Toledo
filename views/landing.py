from pathlib import Path
import streamlit as st
import base64


@st.fragment
def render():
    logo_path = Path("assets/toledo.png")
    logo_b64 = base64.b64encode(logo_path.read_bytes()).decode() if logo_path.exists() else ""
    _, center, _ = st.columns([1, 2, 1], vertical_alignment="center")
    with center:
        st.markdown(
            f"""
            <div class="landing-container">
                {'<img src="data:image/png;base64,'+logo_b64+'" class="logo-img"/>' if logo_b64 else ''}
        """,
            unsafe_allow_html=True,
        )
        enter_clicked = st.button("Entrar", key="landing_enter", use_container_width=True)
    if enter_clicked:
        st.session_state.page_state = "login"
        st.rerun()
