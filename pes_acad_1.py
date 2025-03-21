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

# Configuração inicial do app
st.set_page_config(page_title="Pesquisa Científica Médica", layout="wide")

# Caminho do logo
LOGO_PATH = "C:/Users/Elmer/OneDrive/Documentos/Spesia/Logo.png"

# Tentativa de carregar o logo no canto superior esquerdo
try:
    logo = Image.open(LOGO_PATH)
    col1, col2 = st.columns([1, 10])
    with col1:
        st.image(logo, width=100)
    with col2:
        st.title("🔬 Pesquisa Científica Médica")
except Exception as e:
    st.title("🔬 Pesquisa Científica Médica")
    st.warning("Logo não pôde ser carregado.")

# Inicializa o estado da sessão
if "artigos_completos" not in st.session_state:
    st.session_state.artigos_completos = pd.DataFrame(columns=["title", "date", "source", "abstract", "url", "summary"])

# Função: Buscar artigos no PubMed
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
                    "summary": ""  # será preenchido depois
                })
    return pd.DataFrame(articles)

# Função: Web scraping de links fornecidos
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

# Função: Resumo IA simples (sem API)
def generate_summary(text):
    return text[:300] + "..." if len(text) > 300 else text

# Função: Geração do relatório PDF consolidado
def generate_combined_pdf(dataframe):
    buffer = BytesIO()
    pdf = canvas.Canvas(buffer, pagesize=letter)
    pdf.setTitle("Relatório de Referências Bibliográficas e Bibliografia")

    # Logo no topo
    try:
        logo = ImageReader(LOGO_PATH)
        pdf.drawImage(logo, 40, 720, width=100, preserveAspectRatio=True)
    except:
        pass

    # Título
    pdf.setFont("Helvetica-Bold", 16)
    pdf.drawCentredString(300, 750, "Relatório de Referências Bibliográficas e Bibliografia")

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
    pdf.drawImage(ImageReader(img_hist), 130, 590, width=350, height=100)

    # Tabela de artigos
    y = 570
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
        pdf.drawString(50, y, f"Resumo IA: {row['summary']}")
        y -= 30

    pdf.save()
    buffer.seek(0)
    return buffer

# Interface: Pesquisa por tema
query = st.text_input("Digite o tema de pesquisa:")
if st.button("Pesquisar"):
    with st.spinner("Buscando artigos..."):
        novos_artigos = search_scientific_articles(query)
        novos_artigos["summary"] = novos_artigos["abstract"].apply(generate_summary)
        st.session_state.artigos_completos = pd.concat([st.session_state.artigos_completos, novos_artigos], ignore_index=True)
        st.dataframe(novos_artigos)

# Interface: Web scraping de links
st.subheader("🌍 Web Scraping de Artigos")
urls = st.text_area("Cole os links dos artigos (um por linha):")
if st.button("Coletar Conteúdo"):
    with st.spinner("Realizando scraping..."):
        scraping = scrape_articles(urls.strip().splitlines())
        scraping["summary"] = scraping["abstract"].apply(generate_summary)
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

    pdf_data = generate_combined_pdf(st.session_state.artigos_completos)
    st.download_button("📥 Baixar Relatório PDF", pdf_data, file_name="relatorio_bibliografico.pdf", mime="application/pdf")
