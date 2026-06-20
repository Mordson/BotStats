"""Dashboard Streamlit do wizualizacji statystyk Discord Activity Bot."""

from __future__ import annotations

import os

import pandas as pd
import requests
import streamlit as st

API_URL = os.getenv("API_URL", "http://localhost:8000")


def fetch(path: str, params: dict | None = None) -> list[dict]:
    try:
        resp = requests.get(f"{API_URL}{path}", params=params, timeout=10)
        resp.raise_for_status()
        return resp.json()
    except requests.exceptions.ConnectionError:
        st.error(f"Nie można połączyć się z API ({API_URL}). Upewnij się, że bot i API są uruchomione.")
        st.stop()
    except requests.exceptions.HTTPError as e:
        st.error(f"Błąd API: {e}")
        st.stop()


def seconds_to_hours(seconds: int) -> float:
    return round(seconds / 3600, 2)


st.set_page_config(page_title="Discord Activity Dashboard", page_icon="🎮", layout="wide")
st.title("🎮 Discord Activity Dashboard")

tab_voice, tab_games, tab_user = st.tabs(["🔊 Czas głosowy", "🕹️ Top gry", "👤 Użytkownik"])

with tab_voice:
    st.header("Ranking — czas na kanałach głosowych")

    data = fetch("/stats/voice-time")
    if data:
        df = pd.DataFrame(data)
        df["Godziny"] = df["total_seconds"].apply(seconds_to_hours)
        df = df.rename(columns={"display_name": "Użytkownik"})[["Użytkownik", "Godziny"]]

        st.bar_chart(df.set_index("Użytkownik")["Godziny"])
        st.dataframe(df, use_container_width=True, hide_index=True)
    else:
        st.info("Brak danych — bot jeszcze nie zarejestrował żadnych sesji głosowych.")

with tab_games:
    st.header("Ranking gier — łączny czas wszystkich użytkowników")

    limit = st.slider("Liczba gier", min_value=5, max_value=50, value=10, step=5)
    data = fetch("/stats/top-games", params={"limit": limit})

    if data:
        df = pd.DataFrame(data)
        df["Godziny"] = df["total_seconds"].apply(seconds_to_hours)
        df = df.rename(columns={"activity_name": "Gra"})[["Gra", "Godziny"]]

        st.bar_chart(df.set_index("Gra")["Godziny"])
        st.dataframe(df, use_container_width=True, hide_index=True)
    else:
        st.info("Brak danych — bot jeszcze nie zarejestrował żadnych aktywności.")

with tab_user:
    st.header("Statystyki użytkownika")

    users = fetch("/users/")
    if not users:
        st.info("Brak użytkowników w bazie.")
    else:
        options = {u["display_name"]: u["id"] for u in users}
        selected_name = st.selectbox("Wybierz użytkownika", list(options.keys()))
        user_id = options[selected_name]

        games = fetch(f"/users/{user_id}/games")
        if games:
            df = pd.DataFrame(games)
            df["Godziny"] = df["total_seconds"].apply(seconds_to_hours)
            df = df.rename(columns={"activity_name": "Gra"})[["Gra", "Godziny"]]
            df = df.sort_values("Godziny", ascending=False)

            st.subheader(f"Gry — {selected_name}")
            st.bar_chart(df.set_index("Gra")["Godziny"])
            st.dataframe(df, use_container_width=True, hide_index=True)
        else:
            st.info(f"{selected_name} nie ma jeszcze żadnych zarejestrowanych aktywności.")
