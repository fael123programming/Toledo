import streamlit as st


@st.fragment
def render():
    _, center, _ = st.columns([1, 2, 1], vertical_alignment="center")
    with center:
        st.image(
            "assets/toledo.png",
            use_container_width=True
        )
        enter_clicked = st.button("Entrar", key="landing_enter", use_container_width=True)
    if enter_clicked:
        st.session_state.page_state = "login"
        st.rerun()
