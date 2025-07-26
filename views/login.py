from st_supabase_connection import SupabaseConnection
from gotrue.errors import AuthApiError
import streamlit as st


sb = SupabaseConnection("supabase")


@st.fragment
def render():
    _, center_col, _ = st.columns([2, 2, 2], vertical_alignment='center')
    with center_col:
        _, center_2_col, _ = st.columns([1, 3, 1], vertical_alignment='center')
        with center_2_col:
            st.image("assets/toledo.png", width=200)
        with st.form("login_form"):
            email = st.text_input("E-mail")
            pwd = st.text_input("Senha", type="password")
            submit = st.form_submit_button(
                "Entrar", 
                use_container_width=True, 
                type="primary"
            )
        if submit:
            try:
                resp = sb.client.auth.sign_in_with_password({'email': email, 'password': pwd})
                if resp.user:
                    st.session_state['user'] = resp.user
                    st.session_state.logged_in = True
                    st.session_state.page_state = "app"
                    st.success("Login realizado com sucesso!")
                    st.rerun()
            except AuthApiError:
                st.error("Usuário ou senha inválidos.")
            except Exception as e:
                st.error(f"Erro ao realizar login: {str(e)}")
            # if user == USERNAME and pwd == PASSWORD:
            #     st.session_state.logged_in = True
            #     st.session_state.page_state = "app"
            #     st.success("Login realizado com sucesso!")
            #     st.rerun()
            # else:
            #     st.error("Usuário ou senha inválidos.")
# @st.fragment
# def render():
#     _, center_col, _ = st.columns([2, 2, 2], vertical_alignment='center')
#     with center_col:
#         _, center_2_col, _ = st.columns([1, 3, 1], vertical_alignment='center')
#         with center_2_col:
#             st.image("assets/toledo.png", width=200)
#         with st.form("login_form"):
#             user = st.text_input("Usuário")
#             pwd = st.text_input("Senha", type="password")
#             submit = st.form_submit_button(
#                 "Entrar", 
#                 use_container_width=True, 
#                 type="primary"
#             )
#         if submit:
#             if user == USERNAME and pwd == PASSWORD:
#                 st.session_state.logged_in = True
#                 st.session_state.page_state = "app"
#                 st.success("Login realizado com sucesso!")
#                 st.rerun()
#             else:
#                 st.error("Usuário ou senha inválidos.")