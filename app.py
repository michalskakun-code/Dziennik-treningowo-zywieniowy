Python

import streamlit as st
import pandas as pd
from garminconnect import Garmin
from datetime import date, timedelta
import json
import os

st.set_page_config(page_title="Dziennik Maraton Krakowski", layout="wide")

# Plik do zapisu siłowni
DB_FILE = "silownia_db.json"

def load_data():
    if os.path.exists(DB_FILE):
        with open(DB_FILE, "r") as f:
            return json.load(f)
    return []

def save_data(data):
    with open(DB_FILE, "w") as f:
        json.dump(data, f)

st.title("🏃‍♂️ Dziennik Treningowy: Droga do Maratonu w Krakowie")

tab1, tab2, tab3 = st.tabs(["🏋️‍♂️ Siłownia", "⌚ Garmin & Fitatu", "📋 Generator Raportu"])

# --- ZAKŁADKA 1: SIŁOWNIA ---
with tab1:
    st.header("Zapisz trening siłowy")
    
    col1, col2 = st.columns(2)
    with col1:
        data_treningu = st.date_input("Data", date.today())
        cwiczenie = st.text_input("Ćwiczenie (np. Przysiad ze sztangą)")
    with col2:
        serie_powtorzenia = st.text_input("Serie x Powtórzenia (np. 4x8)")
        ciezar = st.number_input("Ciężar (kg)", min_value=0.0, step=2.5)

    if st.button("Zapisz ćwiczenie"):
        entry = {
            "data": str(data_treningu),
            "cwiczenie": cwiczenie,
            "serie": serie_powtorzenia,
            "ciezar": ciezar
        }
        history = load_data()
        history.append(entry)
        save_data(history)
        st.success("Zapisano ćwiczenie!")

    st.subheader("Historia treningów siłowych")
    history = load_data()
    if history:
        df = pd.DataFrame(history)
        st.dataframe(df, use_container_width=True)
    else:
        st.info("Brak zapisanych treningów siłowych.")

# --- ZAKŁADKA 2: GARMIN ---
with tab2:
    st.header("Synchronizacja z Garmin Connect")
    
    with st.form("garmin_login"):
        email = st.text_input("Email Garmin Connect")
        password = st.text_input("Hasło", type="password")
        submit = st.form_submit_button("Pobierz dane z Garmina")

    if submit and email and password:
        try:
            client = Garmin(email, password)
            client.login()
            st.success("Pomyślnie połączono z Garmin Connect!")
            
            # Pobieranie aktywności z ostatnich 7 dni
            today = date.today()
            start_date = today - timedelta(days=7)
            activities = client.get_activities_by_date(start_date.isoformat(), today.isoformat(), "")
            
            st.session_state["garmin_activities"] = activities
            st.write(f"Pobrano {len(activities)} aktywności z ostatniego tygodnia.")
            
        except Exception as e:
            st.error(f"Błąd logowania do Garmina: {e}")

# --- ZAKŁADKA 3: GENERATOR RAPORTU ---
with tab3:
    st.header("Wygeneruj raport tygodniowy")
    st.write("Kliknij przycisk, skopiuj wygenerowany tekst i wklej go na naszym czacie.")
    
    if st.button("Generuj Raport dla Gemini"):
        history = load_data()
        garmin_acts = st.session_state.get("garmin_activities", [])
        
        raport = "=== PODSUMOWANIE TYGODNIA ===\n\n"
        
        raport += "1. SIŁOWNIA:\n"
        if history:
            for item in history[-10:]: # Ostatnie 10 wpisów
                raport += f"- {item['data']}: {item['cwiczenie']} ({item['serie']} - {item['ciezar']}kg)\n"
        else:
            raport += "Brak wpisów siłowych.\n"
            
        raport += "\n2. BIEGANIE I AKTYWNOŚCI (GARMIN):\n"
        if garmin_acts:
            for act in garmin_acts:
                nazwa = act.get("activityName", "Aktywność")
                dystans = round(act.get("distance", 0) / 1000, 2)
                czas = round(act.get("duration", 0) / 60, 1)
                raport += f"- {act.get('startTimeLocal', '')[:10]} | {nazwa} | Dystans: {dystans} km | Czas: {czas} min\n"
        else:
            raport += "Brak pobranych danych z Garmina (zaloguj się w zakładce Garmin).\n"
            
        st.text_area("Gotowy raport (skopiuj całość):", raport, height=250)
