import streamlit.components.v1 as components
from urllib.parse import urlparse
from datetime import datetime
from pathlib import Path
import streamlit as st
import feedparser
import base64


def img_to_b64(path: str):
    p = Path(path)
    return base64.b64encode(p.read_bytes()).decode() if p.exists() else ""


def main():
    today = datetime.now().strftime("%d de %B de %Y, %H:%M")
    st.write(f"**Logado como {st.session_state['user_data']['email']}**")
    logo_b64 = img_to_b64("assets/toledo.png")
    hero_html = f"""
    <style>
      /* -------------- shared -------------- */
      .hero-wrapper{{
        display:flex;gap:28px;align-items:center;
        backdrop-filter:blur(14px);
        border-radius:24px;padding:32px 38px;margin-bottom:32px;
        transition:background .3s ease,box-shadow .3s ease;
      }}
      .hero-wrapper img{{width:140px;border-radius:18px;box-shadow:0 4px 14px rgba(0,0,0,.35);}}
      .hero-text h1{{margin:0;font-size:2rem;font-weight:700;font-family:'Montserrat',sans-serif;}}
      .hero-text p{{margin:6px 0 0 0;font-size:1rem;}}
      @media(max-width:640px){{.hero-wrapper{{flex-direction:column;text-align:center;}}
        .hero-text h1{{font-size:1.4rem;}}
      }}

      /* ------ dark (default) ----- */
      .hero-wrapper{{background:rgba(255,255,255,.08);box-shadow:0 8px 32px rgba(0,0,0,.25);}}
      .hero-text h1{{color:#ffffff;}}
      .hero-text p{{color:#dbeafe;}}

      /* ------ light theme override ----- */
      @media (prefers-color-scheme: light){{
        .hero-wrapper{{background:rgba(255,255,255,.55);box-shadow:0 6px 18px rgba(0,0,0,.10);}}
        .hero-text h1{{color:#1e293b;}}
        .hero-text p{{color:#1e40af;}}
      }}
    </style>
    <div class="hero-wrapper">
      {'<img src="data:image/png;base64,'+logo_b64+'"/>' if logo_b64 else ''}
      <div class="hero-text">
        <h1>👋 Seja bem‑vindo à Toledo Consultoria</h1>
        <p>Soluções inovadoras em contabilidade, tecnologia e automação</p>
        <p>🗓️ <b>{today}</b></p>
      </div>
    </div>
    """
    components.html(hero_html, height=290, scrolling=False)
    st.subheader("📰 Manchetes relevantes (Direito • Economia • Política)")
    feed = feedparser.parse("https://news.google.com/rss?hl=pt-BR&gl=BR&ceid=BR:pt-419")
    kw = [
        "stf","stj","tse","justiça","tribunal","lei","juríd","advoc","oab",
        "economia","econôm","inflação","pib","juros","tribut","imposto","fiscal",
        "política","governo","congresso","senado","câmara","eleição"
    ]
    filtered = [e for e in feed.entries if any(k in (e.title+e.summary).lower() for k in kw)][:6]

    if not filtered:
        st.info("Nenhuma notícia relevante no momento.")
        return

    slides = ""
    for e in filtered:
        source = e.source.title if hasattr(e,'source') else urlparse(e.link).netloc
        slides += f"""
        <div class='swiper-slide'>
          <div class='news-card'>
            <a class='headline' href='{e.link}' target='_blank'>{e.title}</a>
            <div class='meta'>{source}</div>
          </div>
        </div>
        """

    slider_html = f"""
    <link rel='stylesheet' href='https://cdnjs.cloudflare.com/ajax/libs/Swiper/11.0.5/swiper-bundle.min.css'/>
    <script src='https://cdnjs.cloudflare.com/ajax/libs/Swiper/11.0.5/swiper-bundle.min.js'></script>

    <style>
      .news-container{{margin-top:12px;}}
      .swiper{{width:100%;}}
      .news-card{{
        display:flex;flex-direction:column;gap:6px;
        border-radius:18px;padding:22px;min-height:110px;
        backdrop-filter:blur(10px);
        transition:background .3s ease,box-shadow .3s ease;
      }}
      .headline{{font-weight:600;text-decoration:none;font-size:1rem;transition:color .2s;}}
      .headline:hover{{text-decoration:underline;}}
      .meta{{font-size:.8rem;}}
      .swiper-pagination-bullet{{opacity:1;transition:background .2s;}}

      /* -------------- dark -------------- */
      .news-card{{background:rgba(255,255,255,.07);box-shadow:0 4px 18px rgba(0,0,0,.25);}}
      .headline{{color:#bae6fd;}}
      .meta{{color:#cbd5e1;}}
      .swiper-pagination-bullet{{background:#64748b;}}
      .swiper-pagination-bullet-active{{background:#3b82f6;}}

      /* -------------- light -------------- */
      @media (prefers-color-scheme: light){{
        .news-card{{background:#f8fafc;box-shadow:0 4px 12px rgba(0,0,0,.1);}}
        .headline{{color:#2563eb;}}
        .meta{{color:#475569;}}
        .swiper-pagination-bullet{{background:#94a3b8;}}
        .swiper-pagination-bullet-active{{background:#2563eb;}}
      }}
    </style>

    <div class='news-container'>
      <div class='swiper'>
        <div class='swiper-wrapper'>
          {slides}
        </div>
        <div class='swiper-pagination'></div>
      </div>
    </div>

    <script>
      new Swiper('.swiper', {{ loop:true, autoplay:{{delay:6000}}, pagination:{{el:'.swiper-pagination',clickable:true}} }});
    </script>
    """
    components.html(slider_html, height=220, scrolling=False)


main()