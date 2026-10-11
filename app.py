import streamlit as st
import pandas as pd
from garminconnect import Garmin
from datetime import date, timedelta
import json
import os

st.set_page_config(page_title="Dziennik Treningowy - Kraków 2027", layout="wide")

# Pliki do zapisu danych
SILOWNIA_FILE = "silownia_db.json"
FITATU_FILE = "fitatu_db.json"

def load_json(filepath):
    if os.path.exists(filepath):
        with open(filepath, "r", encoding="utf-8") as f:
            return json.load(f)
    return {}

def save_json(filepath, data):
    with open(filepath, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

st.title("🏃‍♂️ Dziennik Treningowy: Droga do Maratonu w Krakowie")

tab1, tab2, tab3, tab4 = st.tabs(["🏋️‍♂️ Siłownia", "⌚ Garmin", "🥗 Fitatu", "📋 Generator Raportu"])

# --- ZAKŁADKA 1: SIŁOWNIA ---
with tab1:
    st.header("Zapisz trening siłowy")
    
    col_d, col_c = st.columns(2)
    with col_d:
        data_treningu = st.date_input("Data treningu", date.today())
    with col_c:
        cwiczenie = st.text_input("Nazwa ćwiczenia (np. Przysiad ze sztangą)")
    
    liczba_serii = st.number_input("Liczba serii", min_value=1, max_value=10, value=3, step=1)
    
    st.write("---")
    st.write("**Wprowadź powtórzenia i ciężar dla poszczególnych serii:**")
    
    serie_dane = []
    cols_input = st.columns(int(liczba_serii))
    for i in range(int(liczba_serii)):
        with cols_input[i]:
            st.markdown(f"**Seria {i+1}**")
            powtorzenia = st.number_input(f"Powt. S{i+1}", min_value=1, value=8, key=f"powt_{i}")
            ciezar = st.number_input(f"Ciężar S{i+1} (kg)", min_value=0.0, value=0.0, step=2.5, key=f"ciezar_{i}")
            serie_dane.append({"seria": i+1, "powt": powtorzenia, "ciezar": ciezar})
            
    if st.button("Zapisz ćwiczenie na siłowni"):
        if cwiczenie.strip():
            db_silownia = load_json(SILOWNIA_FILE)
            if not isinstance(db_silownia, list):
                db_silownia = []
                
            db_silownia.append({
                "data": str(data_treningu),
                "cwiczenie": cwiczenie,
                "serie": serie_dane
            })
            save_json(SILOWNIA_FILE, db_silownia)
            st.success(f"Dodano {cwiczenie} do dziennika!")
        else:
            st.warning("Wpisz nazwę ćwiczenia.")

    st.subheader("Historia treningów siłowych")
    db_silownia = load_json(SILOWNIA_FILE)
    if isinstance(db_silownia, list) and db_silownia:
        for entry in reversed(db_silownia):
            serie_str = ", ".join([f"S{s['seria']}: {s['powt']}x{s['ciezar']}kg" for s in entry['serie']])
            st.markdown(f"- **{entry['data']}** | **{entry['cwiczenie']}** $\rightarrow$ {serie_str}")
    else:
        st.info("Brak wpisów w historii siłowni.")

# --- ZAKŁADKA 2: GARMIN ---
with tab2:
    st.header("Synchronizacja z Garmin Connect")
    
    with st.form("garmin_form"):
        col_g1, col_g2 = st.columns(2)
        with col_g1:
            email = st.text_input("Email Garmin Connect")
        with col_g2:
            password = st.text_input("Hasło", type="password")
        submit_garmin = st.form_submit_button("Synchronizuj biegi i aktywności")

    if submit_garmin and email and password:
        try:
            client = Garmin(email, password)
            client.login()
            st.success("Połączono z Garmin Connect!")
            
            today = date.today()
            start_date = today - timedelta(days=7)
            activities = client.get_activities_by_date(start_date.isoformat(), today.isoformat(), "")
            
            st.session_state["garmin_activities"] = activities
            st.success(f"Pobrano {len(activities)} aktywności z ostatnich 7 dni.")
            
        except Exception as e:
            st.error(f"Błąd logowania do Garmina: {e}")

    st.subheader("Pobrane treningi z Garmina (Ostatnie 7 dni)")
    garmin_acts = st.session_state.get("garmin_activities", [])
    if garmin_acts:
        acts_data = []
        for act in garmin_acts:
            acts_data.append({
                "Data": act.get("startTimeLocal", "")[:10],
                "Nazwa": act.get("activityName", "Aktywność"),
                "Typ": act.get("activityType", {}).get("typeKey", ""),
                "Dystans (km)": round(act.get("distance", 0) / 1000, 2),
                "Czas (min)": round(act.get("duration", 0) / 60, 1),
                "Śr. Tętno": act.get("averageHR", "-")
            })
        st.dataframe(pd.DataFrame(acts_data), use_container_width=True)
    else:
        st.info("Brak synchronizowanych aktywności. Zaloguj się powyżej.")

# --- ZAKŁADKA 3: FITATU ---
with tab3:
    st.header("Żywienie i Kalorie (Fitatu)")
    
    dni_tygodnia = ["Poniedziałek", "Wtorek", "Środa", "Czwartek", "Piątek", "Sobota", "Niedziela"]
    fitatu_db = load_json(FITATU_FILE)
    if not isinstance(fitatu_db, dict):
        fitatu_db = {}
        
    wybrany_dzien = st.selectbox("Wybierz dzień tygodnia", dni_tygodnia)
    dane_dnia = fitatu_db.get(wybrany_dzien, {"kcal": 2300, "b": 170, "t": 75, "w": 235, "spalone": 0})
    
    st.subheader(f"Wprowadź dane dla: {wybrany_dzien}")
    c1, c2, c3, c4, c5 = st.columns(5)
    with c1:
        kcal = st.number_input("Zjedzone Kcal", min_value=0, value=int(dane_dnia.get("kcal", 2300)), key=f"f_kcal_{wybrany_dzien}")
    with c2:
        b = st.number_input("Białko (g)", min_value=0, value=int(dane_dnia.get("b", 170)), key=f"f_b_{wybrany_dzien}")
    with c3:
        t = st.number_input("Tłuszcze (g)", min_value=0, value=int(dane_dnia.get("t", 75)), key=f"f_t_{wybrany_dzien}")
    with c4:
        w = st.number_input("Węgle (g)", min_value=0, value=int(dane_dnia.get("w", 235)), key=f"f_w_{wybrany_dzien}")
    with c5:
        spalone = st.number_input("Spalone Kcal", min_value=0, value=int(dane_dnia.get("spalone", 0)), key=f"f_sp_{wybrany_dzien}")
        
    if st.button(f"Zapisz {wybrany_dzien}"):
        fitatu_db[wybrany_dzien] = {"kcal": kcal, "b": b, "t": t, "w": w, "spalone": spalone}
        save_json(FITATU_FILE, fitatu_db)
        st.success(f"Zapisano dane dla dnia {wybrany_dzien}!")

    st.subheader("Podsumowanie tygodnia (Fitatu)")
    if fitatu_db:
        df_f = pd.DataFrame.from_dict(fitatu_db, orient="index")
        st.dataframe(df_f, use_container_width=True)

# --- ZAKŁADKA 4: GENERATOR RAPORTU ---
with tab4:
    st.header("Wygeneruj raport tygodniowy")
    st.write("Skopiuj poniższy tekst i wklej go na czacie.")
    
    if st.button("Generuj Raport dla Gemini"):
        db_silownia = load_json(SILOWNIA_FILE)
        fitatu_db = load_json(FITATU_FILE)
        garmin_acts = st.session_state.get("garmin_activities", [])
        
        raport = "=== PODSUMOWANIE TYGODNIA ===\n\n"
        
        raport += "1. SIŁOWNIA:\n"
        if isinstance(db_silownia, list) and db_silownia:
            for item in db_silownia[-10:]:
                serie_str = ", ".join([f"S{s['seria']}: {s['powt']}x{s['ciezar']}kg" for s in item['serie']])
                raport += f"- {item['data']} | {item['cwiczenie']}: {serie_str}\n"
        else:
            raport += "Brak wpisów z siłowni.\n"
            
        raport += "\n2. GARMIN (Treningi):\n"
        if garmin_acts:
            for act in garmin_acts:
                nazwa = act.get("activityName", "Aktywność")
                dystans = round(act.get("distance", 0) / 1000, 2)
                czas = round(act.get("duration", 0) / 60, 1)
                hr = act.get("averageHR", "-")
                raport += f"- {act.get('startTimeLocal', '')[:10]} | {nazwa} | Dystans: {dystans} km | Czas: {czas} min | HR: {hr}\n"
        else:
            raport += "Brak pobranych aktywności z Garmina.\n"
            
        raport += "\n3. FITATU (Dieta i Kalorie):\n"
        if isinstance(fitatu_db, dict) and fitatu_db:
            for dzien, d in fitatu_db.items():
                raport += f"- {dzien}: {d.get('kcal')} kcal (B: {d.get('b')}g, T: {d.get('t')}g, W: {d.get('w')}g) | Spalone: {d.get('spalone')} kcal\n"
        else:
            raport += "Brak wpisów w Fitatu.\n"
            
        st.text_area("Gotowy raport (skopiuj całość):", raport, height=300)
