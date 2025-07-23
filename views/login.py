import streamlit as st


USERNAME = "welton_toledo"
PASSWORD = "V7#pL9$wXz!F3qRt"

@st.fragment
def render():
    _, center_col, _ = st.columns([2, 2, 2], vertical_alignment='center')
    with center_col:
        _, center_2_col, _ = st.columns([1, 3, 1], vertical_alignment='center')
        with center_2_col:
            st.image("assets/toledo.png", width=200)
        with st.form("login_form"):
            user = st.text_input("Usuário")
            pwd = st.text_input("Senha", type="password")
            submit = st.form_submit_button(
                "Entrar", 
                use_container_width=True, 
                type="primary"
            )
        if submit:
            if user == USERNAME and pwd == PASSWORD:
                st.session_state.logged_in = True
                st.session_state.page_state = "app"
                st.success("Login realizado com sucesso!")
                st.rerun()
            else:
                st.error("Usuário ou senha inválidos.")
        if st.button("Voltar", use_container_width=True):
            st.session_state.page_state = "landing"
            st.rerun()
