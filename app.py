from utils.supabase_connection import init_supabase_connection
from streamlit_cookies_manager import EncryptedCookieManager
from datetime import datetime, timezone
from gotrue.errors import AuthApiError
import streamlit as st
import locale
import base64
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
    # {
    #     'page': "views/home.py",
    #     'title': 'Home',
    #     'icon': '🏠',
    #     "url_path": "/home"
    # },
    {
        'page': "views/sheets.py",
        'title': 'Planilhas',
        'icon': '📊',
        "url_path": "/sheets"
    },
    {
        'page': "views/whatsapp.py",
        'title': 'WhatsApp',
        'icon': '🟩',
        "url_path": "/whatsapp"
    },
    {
        'page': "views/docs.py",
        'title': 'Documentos',
        'icon': '📑',
        "url_path": "/docs"
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
    st.sidebar.empty()
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
        st.markdown("""
        <style>
        /* Wider page container (still responsive) */
        .block-container {
        max-width: clamp(480px, 88vw, 720px) !important;  /* was 480px */
        margin: 0 auto !important;
        padding-top: 8vh !important;
        }

        /* Keep the logo visually compact */
        .logo-wrap { max-width: 260px; margin: 0 auto 1rem; }
        .logo-wrap img { width: 100%; height: auto; display:block; }

        /* Form "card" */
        [data-testid="stForm"] {
        box-sizing: border-box;
        width: 100%;
        padding: 1.5rem 1.5rem;          /* a touch roomier */
        border-radius: 16px;
        box-shadow: 0 10px 30px rgba(0,0,0,0.08);
        }

        [data-testid="stForm"] .stButton > button { width: 100% !important; }
        </style>
        """, unsafe_allow_html=True)

        # --- Logo (path -> base64 -> <img>) ---
        image_path = "assets/toledo.png"
        with open(image_path, "rb") as f:
            encoded_image = base64.b64encode(f.read()).decode()

        st.markdown(
            f'<div class="logo-wrap"><img src="data:image/png;base64,{encoded_image}" alt="Logo"/></div>',
            unsafe_allow_html=True
        )

        # --- Form (stacked under the logo, already centered by page CSS) ---
        with st.form("login_form"):
            email = st.text_input("E-mail", key='login_email')
            pwd = st.text_input("Senha", key='password_key', type="password")
            remember_me = st.checkbox("Lembrar-me", key='remember_me', value=True)
            submit = st.form_submit_button("Entrar", type="primary")

        # --- Submit handler (unchanged logic, just moved out of columns) ---
        if submit and email and pwd:
            try:
                with st.spinner(""):
                    # sb can be either a client wrapper or the raw supabase client
                    if hasattr(sb, 'client'):
                        resp = sb.client.auth.sign_in_with_password({'email': email, 'password': pwd})
                    else:
                        resp = sb.auth.sign_in_with_password({'email': email, 'password': pwd})

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
            except AuthApiError:
                st.error("Usuário ou senha inválidos.")
            except Exception as e:
                msg = str(e).lower()
                if "name or service not known" in msg:
                    st.error("Erro de conectividade. Tente novamente em alguns segundos.")
                elif "timeout" in msg:
                    st.error("Timeout na conexão. Verifique sua internet.")
                else:
                    st.error(f"Erro ao realizar login: {e}")


if __name__ == "__main__":
    main()