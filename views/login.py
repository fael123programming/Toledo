import streamlit as st
from st_supabase_connection import SupabaseConnection
from gotrue.errors import AuthApiError
import os
import time


@st.cache_resource
def init_supabase_connection():
    max_retries = 3
    retry_delay = 2
    for attempt in range(max_retries):
        try:
            supabase_url = st.secrets["connections"]["supabase"]["SUPABASE_URL"]
            supabase_key = st.secrets["connections"]["supabase"]["SUPABASE_KEY"]
            if not supabase_url or not supabase_key:
                st.error("Variáveis SUPABASE_URL e SUPABASE_KEY não configuradas")
                return None
            try:
                sb = SupabaseConnection(
                    connection_name="supabase",
                    url=supabase_url,
                    key=supabase_key
                )
                sb.client.table('_test').select('*').limit(1).execute()
                return sb
            except:
                import supabase
                sb = supabase.create_client(supabase_url, supabase_key)
                return sb
        except Exception as e:
            st.warning(f"Tentativa {attempt + 1} falhou: {str(e)}")
            if attempt < max_retries - 1:
                time.sleep(retry_delay)
            else:
                st.error(f"Falha na conexão após {max_retries} tentativas")
                return None


sb = init_supabase_connection()


@st.fragment
def render():
    if not sb:
        st.error("Não foi possível conectar ao Supabase. Verifique as configurações.")
        return
    _, center_col, _ = st.columns([2, 2, 2], vertical_alignment='center')
    with center_col:
        st.header("Seja muito bem-vindo(a) ao Toledo!")
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
        if submit and email and pwd:
            try:
                with st.spinner("Realizando login..."):
                    if hasattr(sb, 'client'):
                        resp = sb.client.auth.sign_in_with_password({
                            'email': email, 
                            'password': pwd
                        })
                    else:
                        resp = sb.auth.sign_in_with_password({
                            'email': email, 
                            'password': pwd
                        })
                    if resp.user:
                        st.session_state['user'] = resp.user
                        st.session_state.logged_in = True
                        st.session_state.page_state = "app"
                        st.success("Login realizado com sucesso!")
                        st.rerun()
                    else:
                        st.error("Falha no login. Verifique suas credenciais.")
            except AuthApiError as e:
                st.error("Usuário ou senha inválidos.")
                st.error(e)
            except Exception as e:
                error_msg = str(e).lower()
                if "name or service not known" in error_msg:
                    st.error("Erro de conectividade. Tente novamente em alguns segundos.")
                elif "timeout" in error_msg:
                    st.error("Timeout na conexão. Verifique sua internet.")
                else:
                    st.error(f"Erro ao realizar login: {str(e)}")