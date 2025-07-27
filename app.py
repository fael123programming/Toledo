from utils.supabase_connection import init_supabase_connection
from streamlit_cookies_manager import EncryptedCookieManager
from datetime import datetime, timezone
from gotrue.errors import AuthApiError
import streamlit as st
import locale
import json
import time


st.set_page_config(
    page_title="Toledo Consultoria",
    page_icon="title",
    layout="wide"
)

try:
    locale.setlocale(locale.LC_ALL, 'pt_BR.UTF-8')
except locale.Error:
    try:
        locale.setlocale(locale.LC_ALL, "")
    except locale.Error:
        pass


VIEWS = [
    {
        'page': "views/home.py",
        'title': 'Home',
        'icon': '🏠',
        "url_path": "/home"
    },
    {
        'page': "views/sheets.py",
        'title': 'Planilhas',
        'icon': '📊',
        "url_path": "/sheets"
    },
    {
        'page': "views/docs.py",
        'title': 'Documentos',
        'icon': '📑',
        "url_path": "/docs"
    },
    {
        'page': "views/whatsapp.py",
        'title': 'WhatsApp',
        'icon': '💬',
        "url_path": "/whatsapp"
    }
]


cookies = EncryptedCookieManager(
    prefix="myapp_", 
    password=st.secrets["cookies"]["COOKIE_MASTER_KEY"]
)

if not cookies.ready():
    st.stop()


def initialize_session():
    if "user_data" not in st.session_state:
        try:
            user_json = cookies.get("user_data")
            if user_json:
                try:
                    user_dict = json.loads(user_json)
                    st.session_state['user_data'] = user_dict
                except (json.JSONDecodeError, TypeError, ValueError):
                    st.session_state['user_data'] = None
            else:
                st.session_state['user_data'] = None
        except json.JSONDecodeError:
            st.session_state['user_data'] = None


def logout():
    st.session_state.pop('user_data', None)
    cookies['user_data'] = ''
    cookies.save()
    st.rerun()


def main():
    sb = init_supabase_connection()
    if not sb:
        st.error("Não foi possível conectar ao Supabase. Verifique as configurações.")
        return
    initialize_session()
    if st.session_state['user_data']:
        selected = st.navigation(
            [
                st.Page(
                    view['page'],
                    title=view['title'],
                    icon=view["icon"],
                    url_path=view['url_path']
                )
                for view in VIEWS
            ],
            position="sidebar"
        )
        selected.run()
        with st.sidebar:
            if st.button("Sair", use_container_width=True):
                st.session_state.logged_in = False
                logout()
                st.rerun()
    else:
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
                                cookies["user_data"] = json.dumps({"id": resp.user.id, "email": resp.user.email})
                                cookies["login_timestamp"] = login_timestamp.isoformat()
                                cookies.save()
                                time.sleep(2)
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


if __name__ == "__main__":
    main()