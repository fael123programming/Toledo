from PyPDF2 import PdfReader
from heapq import nlargest
from docx import Document
import streamlit as st
import re


def summarize_text(text: str, num_sentences: int = 3) -> str:
    sentences = re.split(r'(?<=[.!?]) +', text)
    if len(sentences) <= num_sentences:
        return text
    words = re.findall(r'\w+', text.lower())
    freq = {}
    for w in words:
        freq[w] = freq.get(w, 0) + 1

    ranking = {}
    for i, sent in enumerate(sentences):
        for w in re.findall(r'\w+', sent.lower()):
            ranking[i] = ranking.get(i, 0) + freq.get(w, 0)
    top_idxs = nlargest(num_sentences, ranking, key=ranking.get)
    return " ".join(sentences[j] for j in sorted(top_idxs))


@st.fragment
def render():
    tabs = st.tabs(["📑 Resumir PDF", "📝 Resumir DOCX"])
    with tabs[0]:
        pdf_file = st.file_uploader("Envie um PDF", type=["pdf"])
        if pdf_file:
            reader = PdfReader(pdf_file)
            text = "".join(page.extract_text() or "" for page in reader.pages)
            summary = summarize_text(text, num_sentences=4)
            st.subheader("Resumo")
            st.write(summary)
    with tabs[1]:
        docx_file = st.file_uploader("Envie um DOCX", type=["docx"])
        if docx_file:
            doc = Document(docx_file)
            text = "\n".join(p.text for p in doc.paragraphs)
            summary = summarize_text(text, num_sentences=4)
            st.subheader("Resumo")
            st.write(summary)