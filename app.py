from views import whatsapp
from views import sheets
from views import home
from views import docs
import streamlit as st
import locale
import warnings


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


if __name__ == "__main__":
    main()
