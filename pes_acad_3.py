import os
import subprocess
import sys

# Garantir que as dependências estão instaladas
def install_requirements():
    req_file = os.path.join(os.path.dirname(__file__), "requirements.txt")
    if os.path.exists(req_file):
        subprocess.run([sys.executable, "-m", "pip", "install", "-r", req_file], check=True)
    else:
        print("Arquivo requirements.txt não encontrado.")

# Instalar pacotes necessários antes da execução
install_requirements()

# Importação das bibliotecas após instalação das dependências
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
            st.experimental_rerun()
        else:
            st.error("Login ou senha incorretos. Tente novamente.")

# Se autenticado, exibir aplicação
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

    # Função para buscar artigos na PubMed
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

    # Função para Web Scraping
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

    # Interface: Pesquisa por tema
    query = st.text_input("Digite o tema de pesquisa:")
    if st.button("Pesquisar"):
        with st.spinner("Buscando artigos..."):
            novos_artigos = search_scientific_articles(query)
            st.session_state.artigos_completos = pd.concat([st.session_state.artigos_completos, novos_artigos], ignore_index=True)
            st.dataframe(novos_artigos)

    # Interface: Web scraping de links
    st.subheader("🌍 Web Scraping de Artigos")
    urls = st.text_area("Cole os links dos artigos (um por linha):")
    if st.button("Coletar Conteúdo"):
        with st.spinner("Realizando scraping..."):
            scraping = scrape_articles(urls.strip().splitlines())
            st.session_state.artigos_completos = pd.concat([st.session_state.artigos_completos, scraping], ignore_index=True)
            st.dataframe(scraping)

    # Resultados consolidados
    if not st.session_state.artigos_completos.empty:
        st.subheader("📚 Artigos Coletados")
        st.dataframe(st.session_state.artigos_completos)

        fig = px.histogram(st.session_state.artigos_completos, x="date", title="Publicações por Ano")
        st.plotly_chart(fig)

        csv_data = st.session_state.artigos_completos.to_csv(index=False).encode()
        st.download_button("📥 Baixar CSV Consolidado", csv_data, file_name="referencias.csv", mime="text/csv")
