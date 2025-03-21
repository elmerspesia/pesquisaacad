import os
import subprocess
import sys
import base64
import streamlit as st
import requests
import pandas as pd
import matplotlib.pyplot as plt
from bs4 import BeautifulSoup
from io import BytesIO
from datetime import datetime
import plotly.express as px
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas
from reportlab.lib.utils import ImageReader
from PIL import Image

# Configuração do app
st.set_page_config(page_title="Pesquisa Acadêmica Online", layout="wide")

# Caminho do logo no diretório do repositório
LOGO_PATH = os.path.join(os.path.dirname(__file__), "Logo.png")

# Inicializa autenticação na sessão
if "authenticated" not in st.session_state:
    st.session_state.authenticated = False

# Tela de login inicial
if not st.session_state.authenticated:
    try:
        logo = Image.open(LOGO_PATH)
        st.image(logo, width=150)
    except:
        st.warning("Logo não encontrado.")

    st.markdown("<h2 style='text-align: center;'>Pesquisa Acadêmica Online</h2>", unsafe_allow_html=True)

    username = st.text_input("Login", value="spesia123")
    password = st.text_input("Senha", value="spesia123", type="password")

    if st.button("Entrar"):
        if username == "spesia123" and password == "spesia123":
            st.session_state.authenticated = True
            st.experimental_rerun()  # ✅ Garantir atualização correta da tela
        else:
            st.error("Login ou senha incorretos. Tente novamente.")

# Se autenticado, exibir aplicação completa
if st.session_state.authenticated:
    try:
        logo = Image.open(LOGO_PATH)
        st.image(logo, width=120)
    except:
        st.warning("Logo não pôde ser carregado.")

    st.markdown("<h1 style='text-align: center;'>🔬 Pesquisa Científica Médica</h1>", unsafe_allow_html=True)

    # Inicializa armazenamento dos artigos
    if "artigos_completos" not in st.session_state:
        st.session_state.artigos_completos = pd.DataFrame(columns=["title", "date", "source", "abstract", "url", "summary"])

    # 🔎 Função para buscar artigos na PubMed
    def search_scientific_articles(query):
        articles = []
        pubmed_url = f"https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esearch.fcgi?db=pubmed&term={query}&retmode=json&retmax=10"
        response = requests.get(pubmed_url)
        if response.status_code == 200:
            ids = response.json().get("esearchresult", {}).get("idlist", [])
            for pubmed_id in ids:
                details_url = f"https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esummary.fcgi?db=pubmed&id={pubmed_id}&retmode=json"
                details_response = requests.get(details_url)
                if details_response.status_code == 200:
                    info = details_response.json().get("result", {}).get(pubmed_id, {})
                    articles.append({
                        "title": info.get("title"),
                        "date": info.get("pubdate"),
                        "source": "PubMed",
                        "abstract": "Abstract não disponível via API.",
                        "url": f"https://pubmed.ncbi.nlm.nih.gov/{pubmed_id}/",
                        "summary": ""  
                    })
        return pd.DataFrame(articles)

    # 🌐 Função para Web Scraping
    def scrape_articles(urls):
        scraped = []
        for url in urls:
            try:
                r = requests.get(url)
                soup = BeautifulSoup(r.text, "html.parser")
                title = soup.find("h1").text if soup.find("h1") else "Título não encontrado"
                paragraphs = soup.find_all("p")
                content = " ".join(p.text for p in paragraphs[:5])
                scraped.append({
                    "title": title,
                    "date": datetime.today().strftime('%Y-%m-%d'),
                    "source": "Web",
                    "abstract": content,
                    "url": url,
                    "summary": ""
                })
            except Exception as e:
                scraped.append({
                    "title": "Erro",
                    "date": datetime.today().strftime('%Y-%m-%d'),
                    "source": "Web",
                    "abstract": str(e),
                    "url": url,
                    "summary": ""
                })
        return pd.DataFrame(scraped)

    # 📄 Função para gerar PDF
    def generate_combined_pdf(dataframe):
        buffer = BytesIO()
        pdf = canvas.Canvas(buffer, pagesize=letter)
        pdf.setTitle("Relatório de Referências Bibliográficas e Bibliografia")

        # Logo centralizado
        try:
            logo = ImageReader(LOGO_PATH)
            pdf.drawImage(logo, x=230, y=720, width=120, preserveAspectRatio=True)
        except:
            pass

        # Título
        pdf.setFont("Helvetica-Bold", 16)
        pdf.drawCentredString(300, 700, "Relatório de Referências Bibliográficas e Bibliografia")

        # Histograma
        fig, ax = plt.subplots(figsize=(6, 2.5))
        df_hist = dataframe.copy()
        df_hist["date"] = pd.to_datetime(df_hist["date"], errors="coerce")
        df_hist["year"] = df_hist["date"].dt.year
        df_hist["year"].dropna().astype(int).hist(bins=10, ax=ax)
        ax.set_title("Distribuição das Publicações por Ano")
        img_hist = BytesIO()
        plt.tight_layout()
        fig.savefig(img_hist, format='png')
        plt.close(fig)
        img_hist.seek(0)
        pdf.drawImage(ImageReader(img_hist), 130, 560, width=350, height=100)

        # Conteúdo dos artigos
        y = 540
        pdf.setFont("Helvetica", 10)
        for _, row in dataframe.iterrows():
            if y < 100:
                pdf.showPage()
                y = 750
            pdf.drawString(50, y, f"Título: {row['title']}")
            y -= 15
            pdf.drawString(50, y, f"Data: {row['date']} | Fonte: {row['source']}")
            y -= 15
            pdf.drawString(50, y, f"Link: {row['url']}")
            y -= 15
            pdf.drawString(50, y, f"Resumo gerado por IA: {row['summary']}")
            y -= 30

        pdf.save()
        buffer.seek(0)
        return buffer

    # 🔍 Pesquisa por tema
    query = st.text_input("Digite o tema de pesquisa:")
    if st.button("Pesquisar"):
        with st.spinner("Buscando artigos..."):
            novos_artigos = search_scientific_articles(query)
            st.session_state.artigos_completos = pd.concat([st.session_state.artigos_completos, novos_artigos], ignore_index=True)
            st.dataframe(novos_artigos)

    # 🌍 Web Scraping de links
    urls = st.text_area("Cole os links dos artigos (um por linha):")
    if st.button("Coletar Conteúdo"):
        with st.spinner("Realizando scraping..."):
            scraping = scrape_articles(urls.strip().splitlines())
            st.session_state.artigos_completos = pd.concat([st.session_state.artigos_completos, scraping], ignore_index=True)
            st.dataframe(scraping)

    # 📑 Gerar e exibir o PDF
    if not st.session_state.artigos_completos.empty:
        pdf_data = generate_combined_pdf(st.session_state.artigos_completos)
        base64_pdf = base64.b64encode(pdf_data.getvalue()).decode("utf-8")
        pdf_display = f'<iframe src="data:application/pdf;base64,{base64_pdf}" width="700" height="500"></iframe>'
        st.markdown(pdf_display, unsafe_allow_html=True)
        st.download_button("📥 Baixar Relatório PDF", pdf_data, file_name="relatorio_bibliografico.pdf", mime="application/pdf")
