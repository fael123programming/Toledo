from streamlit_cookies_manager import EncryptedCookieManager
from st_supabase_connection import SupabaseConnection
from datetime import datetime, timedelta, timezone
from gotrue.errors import AuthApiError
from gotrue.types import User
import streamlit as st
import supabase
import json
import time
import os


cookies = EncryptedCookieManager(
    prefix="myapp_", 
    password=st.secrets["cookies"]["COOKIE_MASTER_KEY"]
)

if not cookies.ready():
    st.stop()


def initialize_session():
    if "user_data" not in st.session_state:
        user_json = cookies.get("user_data")
        if user_json:
            user_dict = json.loads(user_json)
            user = User.model_validate(user_dict)
            st.session_state['user_data'] = user
            st.session_state['login_timestamp'] = datetime.fromisoformat(cookies.get("login_timestamp"))
            st.session_state["logged_in"] = True
            st.session_state["page_state"] = "app"
        else:
            st.session_state['user_data'] = None
            st.session_state['login_timestamp'] = None
            st.session_state["logged_in"] = False
            st.session_state["page_state"] = "login"


def is_session_valid(max_hours=24):
    ts = st.session_state.login_timestamp
    return bool(ts and (datetime.utcnow() - ts) < timedelta(hours=max_hours))


def logout():
    for k in ("user_data", "login_timestamp"):
        st.session_state.pop(k, None)
        cookies[k] = None
    cookies.save()
    st.rerun()


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
                sb = supabase.create_client(supabase_url, supabase_key)
                return sb
        except Exception as e:
            st.warning(f"Tentativa {attempt + 1} falhou: {str(e)}")
            if attempt < max_retries - 1:
                time.sleep(retry_delay)
            else:
                st.error(f"Falha na conexão após {max_retries} tentativas")
                return None


@st.fragment
def render():
    sb = init_supabase_connection()
    initialize_session()
    if not sb:
        st.error("Não foi possível conectar ao Supabase. Verifique as configurações.")
        return
    _, center_col, _ = st.columns([2, 2, 2], vertical_alignment='center')
    with center_col:
        _, center_2_col, _ = st.columns([1, 3, 1], vertical_alignment='center')
        with center_2_col:
            st.image("assets/toledo.png", width=200)
        with st.form("login_form"):
            email = st.text_input("E-mail", key='login_email')
            pwd = st.text_input("Senha", key='password_key', type="password")
            remember_me = st.checkbox("Lembrar-me", key='remember_me')
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
                        login_timestamp = datetime.now(timezone.utc)
                        st.session_state['login_timestamp'] = login_timestamp
                        st.session_state["user_data"] = resp.user
                        st.session_state["logged_in"] = True
                        st.session_state["page_state"] = "app"
                        if remember_me:
                            user = resp.user
                            user_dict = user.model_dump(mode="json")
                            cookies["user_data"] = json.dumps(user_dict)
                            cookies["login_timestamp"] = login_timestamp.isoformat()
                            cookies.save()
                        st.rerun()
                    else:
                        st.error("Falha no login. Verifique suas credenciais.")
            except AuthApiError as e:
                st.error("Usuário ou senha inválidos.")
            except Exception as e:
                error_msg = str(e).lower()
                if "name or service not known" in error_msg:
                    st.error("Erro de conectividade. Tente novamente em alguns segundos.")
                elif "timeout" in error_msg:
                    st.error("Timeout na conexão. Verifique sua internet.")
                else:
                    st.error(f"Erro ao realizar login: {str(e)}")