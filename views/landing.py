from pathlib import Path
import streamlit as st
import base64


@st.fragment
def render():
    logo_path = Path("assets/toledo.png")
    logo_b64 = base64.b64encode(logo_path.read_bytes()).decode() if logo_path.exists() else ""
    st.markdown(
        f"""
        <div class="landing-container">
            {'<img src="data:image/png;base64,'+logo_b64+'" class="logo-img"/>' if logo_b64 else ''}
            <h1>Toledo Consultoria</h1>
    """,
        unsafe_allow_html=True,
    )
    enter_clicked = st.button("Entrar", key="landing_enter", use_container_width=True)
    st.markdown("</div>", unsafe_allow_html=True)
    if enter_clicked:
        st.session_state.page_state = "login"
        st.rerun()
