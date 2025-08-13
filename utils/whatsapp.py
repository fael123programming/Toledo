from urllib.parse import urlencode
import streamlit as st
import requests


SEND_WPP_MSG_URL = "https://api.ultramsg.com/instance134627/messages/chat"

HEADERS = {
    'content-type': 'application/x-www-form-urlencoded'
}


def send_wpp_msg(msg: str, to: str, token: str) -> dict:
    if not to.startswith("+"):
        to = "+" + to
    payload = urlencode({"token": token, "to": to, "body": msg}, encoding="utf-8")
    resp = requests.post(SEND_WPP_MSG_URL, data=payload, headers=HEADERS)
    return resp.json()