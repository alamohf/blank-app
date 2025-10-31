import streamlit as st
import requests
import pandas as pd
import datetime
import base64
from streamlit_autorefresh import st_autorefresh

# 🔐 Chave da API via Streamlit Secrets
API_KEY = st.secrets["RAPIDAPI_KEY"]
HEADERS = {
    "X-RapidAPI-Key": API_KEY,
    "X-RapidAPI-Host": "free-api-live-football-data.p.rapidapi.com"
}

# 🔁 Configuração da página
st.set_page_config(page_title="Painel Futebol", layout="wide")
st.title("⚽ Painel de Análise de Partidas de Futebol")
st.markdown("Atualiza automaticamente e identifica padrões estatísticos em partidas reais.")

# ⚙️ Configurações do usuário
intervalo = st.sidebar.slider("⏱ Intervalo de atualização (min)", 1, 30, 5)
delta_ataques = st.sidebar.number_input("🔺 Delta mínimo de Ataques", value=10)
delta_posse = st.sidebar.number_input("🔺 Delta mínimo de Posse (%)", value=5)
exigir_dominio_b = st.sidebar.checkbox("✅ Exigir que Time B domine Finalizações e Chutes")

# 🔄 Atualização automática
st_autorefresh(interval=intervalo * 60 * 1000, key="datarefresh")

# 🌐 Coleta de partidas ao vivo
def buscar_eventos_ao_vivo():
    url = "https://free-api-live-football-data.p.rapidapi.com/live"
    try:
        response = requests.get(url, headers=HEADERS, timeout=10)
        data = response.json()
        return data.get("data", [])
    except Exception:
        st.warning("⚠️ Não foi possível carregar os eventos ao vivo.")
        return []

# 📊 Coleta estatísticas por event_id
def buscar_estatisticas(event_id):
    url = f"https://free-api-live-football-data.p.rapidapi.com/eventstats/{event_id}"
    try:
        response = requests.get(url, headers=HEADERS, timeout=10)
        return response.json().get("data", {})
    except Exception:
        return {}

# 🧠 Processa partidas com estatísticas
def coletar_dados_completos():
    eventos = buscar_eventos_ao_vivo()
    partidas = []

    for evento in eventos:
        event_id = evento.get("event_id")
        home = evento.get("home_team", {}).get("name", "")
        away = evento.get("away_team", {}).get("name", "")
        stats = buscar_estatisticas(event_id)

        if stats:
            partidas.append({
                "Time A": home,
                "Time B": away,
                "Ataques A": stats.get("attacks_home", 0),
                "Ataques B": stats.get("attacks_away", 0),
                "Ataques perigosos A": stats.get("dangerous_attacks_home", 0),
                "Ataques perigosos B": stats.get("dangerous_attacks_away", 0),
                "Posse A": stats.get("possession_home", 0),
                "Posse B": stats.get("possession_away", 0),
                "Finalizações A": stats.get("shots_total_home", 0),
                "Finalizações B": stats.get("shots_total_away", 0),
                "Chutes a gol A": stats.get("shots_on_goal_home", 0),
                "Chutes a gol B": stats.get("shots_on_goal_away", 0),
            })

    return pd.DataFrame(partidas)

# 🔍 Aplica lógica de seleção
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

# 📥 Executa coleta e análise
df = coletar_dados_completos()
if not df.empty:
    df = aplicar_logica(df)
    st.dataframe(df, use_container_width=True)

    # 📄 Relatório HTML
    def gerar_html(df):
        destaque = df[df["Padrão ✅"]]
        html = f"<h1>Relatório Futebol</h1><p>Gerado em {datetime.datetime.now()}</p>"
        html += df.to_html(index=False)
        html += "<h2>Jogos que batem o padrão:</h2>"
        html += destaque.to_html(index=False)
        return html

    html_content = gerar_html(df)
    b64 = base64.b64encode(html_content.encode()).decode()
    href = f'<a href="data:text/html;base64,{b64}" download="relatorio_futebol.html">📥 Baixar Relatório HTML</a>'
    st.markdown(href, unsafe_allow_html=True)
else:
    st.info("Nenhuma partida com estatísticas disponíveis no momento.")
