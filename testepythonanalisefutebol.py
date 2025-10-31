import streamlit as st
import requests
from bs4 import BeautifulSoup
import pandas as pd
import datetime
import base64

# 🔁 Atualização automática
st.set_page_config(page_title="Painel eSoccer", layout="wide")
st.title("📊 Painel de Análise de Partidas eSoccer")
st.markdown("Atualiza automaticamente a cada X minutos e identifica padrões estatísticos em partidas.")

# ⚙️ Configurações do usuário
intervalo = st.sidebar.slider("⏱ Intervalo de atualização (min)", 1, 30, 5)
delta_ataques = st.sidebar.number_input("🔺 Delta mínimo de Ataques", value=10)
delta_posse = st.sidebar.number_input("🔺 Delta mínimo de Posse (%)", value=5)
exigir_dominio_b = st.sidebar.checkbox("✅ Exigir que Time B domine Finalizações e Chutes")

# 🔄 Atualização automática
from streamlit_autorefresh import st_autorefresh

# ⏱ Atualização automática a cada X minutos
st_autorefresh(interval=intervalo * 60 * 1000, key="datarefresh")
st.session_state["last_refresh"] = datetime.datetime.now().timestamp()

# 🌐 Fonte de dados
URL = "https://www.forebet.com/pt/esoccer/esoccer-battle-8-mins-play"

def coletar_dados():
    try:
        response = requests.get(URL, timeout=10)
        soup = BeautifulSoup(response.text, "html.parser")
        partidas = []

        for bloco in soup.select(".match-row"):
            try:
                times = bloco.select_one(".homeTeam").text.strip(), bloco.select_one(".awayTeam").text.strip()
                estatisticas = bloco.select(".stat-row")
                stats = {stat.select_one(".stat-name").text.strip(): stat.select_one(".stat-value").text.strip() for stat in estatisticas}
                partidas.append({
                    "Time A": times[0],
                    "Time B": times[1],
                    "Ataques A": int(stats.get("Ataques A", 0)),
                    "Ataques B": int(stats.get("Ataques B", 0)),
                    "Ataques perigosos A": int(stats.get("Ataques perigosos A", 0)),
                    "Ataques perigosos B": int(stats.get("Ataques perigosos B", 0)),
                    "Posse A": int(stats.get("Posse A", "0%").replace("%", "")),
                    "Posse B": int(stats.get("Posse B", "0%").replace("%", "")),
                    "Finalizações A": int(stats.get("Finalizações A", 0)),
                    "Finalizações B": int(stats.get("Finalizações B", 0)),
                    "Chutes a gol A": int(stats.get("Chutes a gol A", 0)),
                    "Chutes a gol B": int(stats.get("Chutes a gol B", 0)),
                })
            except:
                continue
        return pd.DataFrame(partidas)
    except Exception as e:
        st.warning("⚠️ Não foi possível carregar os dados do site.")
        return pd.DataFrame()

# 📊 Lógica de seleção
def aplicar_logica(df):
    def verifica_padrao(row):
        dominio_a = (
            row["Ataques A"] - row["Ataques B"] >= delta_ataques and
            row["Ataques perigosos A"] > row["Ataques perigosos B"] and
            row["Posse A"] - row["Posse B"] >= delta_posse
        )
        dominio_b = (
            row["Finalizações B"] > row["Finalizações A"] and
            row["Chutes a gol B"] > row["Chutes a gol A"]
        ) if exigir_dominio_b else (
            row["Finalizações B"] > row["Finalizações A"] or
            row["Chutes a gol B"] > row["Chutes a gol A"]
        )
        return dominio_a and dominio_b

    df["Padrão ✅"] = df.apply(verifica_padrao, axis=1)
    return df

# 📥 Coleta e análise
df = coletar_dados()
if not df.empty:
    df = aplicar_logica(df)
    st.dataframe(df, use_container_width=True)

    # 📄 Relatório HTML
    def gerar_html(df):
        destaque = df[df["Padrão ✅"]]
        html = f"<h1>Relatório eSoccer</h1><p>Gerado em {datetime.datetime.now()}</p>"
        html += df.to_html(index=False)
        html += "<h2>Jogos que batem o padrão:</h2>"
        html += destaque.to_html(index=False)
        return html

    html_content = gerar_html(df)
    b64 = base64.b64encode(html_content.encode()).decode()
    href = f'<a href="data:text/html;base64,{b64}" download="relatorio_esoccer.html">📥 Baixar Relatório HTML</a>'
    st.markdown(href, unsafe_allow_html=True)
else:
    st.info("Nenhuma partida disponível no momento.")
