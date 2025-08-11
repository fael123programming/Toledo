import streamlit.components.v1 as components
from urllib.parse import urlparse
from datetime import datetime
from pathlib import Path
import streamlit as st
import feedparser
import base64

# ---------- Settings ----------
st.set_page_config(page_title="Toledo Consultoria", layout="wide")
MAXW = 1000  # target content width in pixels (tweak as you like)

# ---------- Helpers ----------
def img_to_b64(path: str) -> str:
    p = Path(path)
    return base64.b64encode(p.read_bytes()).decode() if p.exists() else ""

def today_ptbr() -> str:
    months = {
        "January": "Janeiro", "February": "Fevereiro", "March": "Março",
        "April": "Abril", "May": "Maio", "June": "Junho",
        "July": "Julho", "August": "Agosto", "September": "Setembro",
        "October": "Outubro", "November": "Novembro", "December": "Dezembro"
    }
    s = datetime.now().strftime("%d de %B de %Y, %H:%M")
    for en, pt in months.items():
        s = s.replace(en, pt)
    return s

# ---------- Center the Streamlit page container ----------
st.markdown(f"""
<style>
:root {{
  --gold: #c6a565;
  --navy: #0c1a2c;
  --steel: #6e7884;
  --silver: #b1b8c5;
  --nearblack: #0a0a0a;
}}
.block-container {{
  max-width: {MAXW}px !important;
  margin: 0 auto !important;
  padding-top: 4vh !important;
}}
</style>
""", unsafe_allow_html=True)

# ---------- Top: login info (if available) ----------
try:
    st.write(f"**Logado como {st.session_state['user_data']['email']}**")
except Exception:
    pass

# ---------- HERO ----------
logo_b64 = img_to_b64("assets/toledo.png")
today = today_ptbr()

hero_html = f"""
<style>
  :root {{ --maxw: {MAXW}px; --gold:#c6a565; --navy:#0c1a2c; --silver:#b1b8c5; --nearblack:#0a0a0a; }}
  html, body {{ margin:0; padding:0; }}
  .outer {{ display:flex; justify-content:center; }}
  .inner {{ width: min(var(--maxw), 96vw); }}

  .hero-wrapper {{
    display:flex; gap:28px; align-items:center;
    border-radius:24px; padding:32px 38px; margin:0 auto 32px;
    backdrop-filter: blur(14px);
    background: rgba(255,255,255,.08);
    box-shadow: 0 8px 32px rgba(0,0,0,.25);
  }}
  .hero-wrapper img {{ width:140px; border-radius:18px; box-shadow:0 4px 14px rgba(0,0,0,.35); }}
  .hero-text h1 {{ margin:0; font-size:2rem; font-weight:700; color:#ffffff; }}
  .hero-text p {{ margin:6px 0 0 0; font-size:1rem; color:#dbeafe; }}

  @media (max-width:640px) {{
    .hero-wrapper {{ flex-direction:column; text-align:center; }}
    .hero-text h1 {{ font-size:1.4rem; }}
  }}

  /* Light mode overrides */
  @media (prefers-color-scheme: light) {{
    .hero-wrapper {{ background: rgba(255,255,255,.55); box-shadow:0 6px 18px rgba(0,0,0,.10); }}
    .hero-text h1 {{ color:#1e293b; }}
    .hero-text p {{ color:#1e40af; }}
  }}
</style>

<div class="outer"><div class="inner">
  <div class="hero-wrapper">
    {'<img src="data:image/png;base64,'+logo_b64+'"/>' if logo_b64 else ''}
    <div class="hero-text">
      <h1>👋 Seja bem-vindo à Toledo Consultoria</h1>
      <p>Soluções inovadoras em contabilidade, tecnologia e automação</p>
      <p>🗓️ <b>{today}</b></p>
    </div>
  </div>
</div></div>
"""
components.html(hero_html, height=300, scrolling=False)

# ---------- Headlines ----------
st.subheader("📰 Manchetes relevantes (Direito • Economia • Política)")

feed = feedparser.parse("https://news.google.com/rss?hl=pt-BR&gl=BR&ceid=BR:pt-419")
kw = [
    "stf","stj","tse","justiça","tribunal","lei","juríd","advoc","oab",
    "economia","econôm","inflação","pib","juros","tribut","imposto","fiscal",
    "política","governo","congresso","senado","câmara","eleição"
]
entries = []
for e in feed.entries:
    text = (getattr(e, "title", "") + " " + getattr(e, "summary", "")).lower()
    if any(k in text for k in kw):
        entries.append(e)
filtered = entries[:6]

if not filtered:
    st.info("Nenhuma notícia relevante no momento.")
else:
    slides = ""
    for e in filtered:
        source = getattr(getattr(e, "source", {}), "title", None) or urlparse(getattr(e, "link", "#")).netloc
        title = getattr(e, "title", "Sem título")
        link = getattr(e, "link", "#")
        slides += f"""
        <div class='swiper-slide'>
          <div class='news-card'>
            <a class='headline' href='{link}' target='_blank' rel='noopener noreferrer'>{title}</a>
            <div class='meta'>{source}</div>
          </div>
        </div>
        """

    slider_html = f"""
    <link rel='stylesheet' href='https://cdnjs.cloudflare.com/ajax/libs/Swiper/11.0.5/swiper-bundle.min.css'/>
    <script src='https://cdnjs.cloudflare.com/ajax/libs/Swiper/11.0.5/swiper-bundle.min.js'></script>

    <style>
      :root {{ --maxw:{MAXW}px; --gold:#c6a565; --navy:#0c1a2c; --silver:#b1b8c5; }}
      html, body {{ margin:0; padding:0; }}
      .outer {{ display:flex; justify-content:center; }}
      .inner {{ width: min(var(--maxw), 96vw); }}

      .news-container {{ margin-top: 12px; }}
      .swiper {{ width: 100%; }}
      .news-card {{
        display:flex; flex-direction:column; gap:6px;
        border-radius:18px; padding:22px; min-height:110px;
        backdrop-filter:blur(10px);
        background:rgba(255,255,255,.07);
        box-shadow:0 4px 18px rgba(0,0,0,.25);
      }}
      .headline {{ font-weight:600; text-decoration:none; font-size:1rem; color:#bae6fd; }}
      .headline:hover {{ text-decoration:underline; }}
      .meta {{ font-size:.8rem; color:#cbd5e1; }}
      .swiper-pagination-bullet {{ opacity:1; background:#94a3b8; }}
      .swiper-pagination-bullet-active {{ background: var(--gold); }}

      @media (prefers-color-scheme: light) {{
        .news-card {{ background:#f8fafc; box-shadow:0 4px 12px rgba(0,0,0,.1); }}
        .headline {{ color:#2563eb; }}
        .meta {{ color:#475569; }}
        .swiper-pagination-bullet {{ background:#cbd5e1; }}
        .swiper-pagination-bullet-active {{ background:#2563eb; }}
      }}
    </style>

    <div class="outer"><div class="inner">
      <div class='news-container'>
        <div class='swiper'>
          <div class='swiper-wrapper'>
            {slides}
          </div>
          <div class='swiper-pagination'></div>
        </div>
      </div>
    </div></div>

    <script>
      new Swiper('.swiper', {{
        loop: true,
        autoplay: {{ delay: 6000 }},
        pagination: {{ el: '.swiper-pagination', clickable: true }}
      }});
    </script>
    """
    components.html(slider_html, height=240, scrolling=False)
