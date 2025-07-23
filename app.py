from views import whatsapp, sheets, home, docs, login
import streamlit as st
import warnings
import locale


try:
    locale.setlocale(locale.LC_ALL, 'pt_BR.UTF-8')
except locale.Error:
    warnings.warn("pt_BR.UTF-8 locale unavailable; using default settings")
    try:
        locale.setlocale(locale.LC_ALL, "")
    except locale.Error:
        pass

PAGES = [
    {
        'page': home.render,
        'title': 'Home',
        'icon': '🏠',
    },
    {
        'page': sheets.render,
        'title': 'Planilhas',
        'icon': '📊',
    },
    {
        'page': docs.render,
        'title': 'Documentos',
        'icon': '📑',
    },
    {
        'page': whatsapp.render,
        'title': 'WhatsApp',
        'icon': '💬',
    }
]


def main():
    st.set_page_config(
        page_title="Toledo Consultoria",
        page_icon="title",
        layout="wide"
    )
    if 'page_state' not in st.session_state:
        st.session_state.page_state = 'login'
        st.session_state.logged_in = False

    if not st.session_state.logged_in:
        st.session_state.page_state = 'login'
        login.render()
        return

    selected = st.navigation(
        [
            st.Page(
                page['page'],
                title=page['title'],
                icon=page["icon"],
                url_path=f"/{page['title'].lower().replace(' ', '_')}"
            )
            for page in PAGES
        ],
        position="sidebar"
    )
    selected.run()

    with st.sidebar:
        if st.button("Sair", use_container_width=True):
            st.session_state.logged_in = False
            st.session_state.page_state = "landing"
            st.rerun()


if __name__ == "__main__":
    main()
