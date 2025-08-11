from urllib.parse import urlparse
from datetime import datetime
from pathlib import Path
import streamlit as st


def main():
  left_col, right_col = st.columns([1, 10], vertical_alignment='center')
  with left_col:
    st.image(
      "assets/toledo.png"
    )
  with right_col:
    st.write("# Seja bem-vindo à Toledo Consultoria")



main()