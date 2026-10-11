import streamlit as st
import pandas as pd
from datetime import date, timedelta
import json
import os

try:
    from garminconnect import Garmin
except ImportError:
    Garmin = None

st.set_page_config(page_title="Dziennik Treningowy - Kraków 2027", layout="wide")

SILOWNIA_FILE = "silownia_db.json"
FITATU_FILE = "fitatu_db.json"

def load_json(filepath, default_val):
    if os.path.exists(filepath):
        try:
            with open(filepath, "r", encoding="utf-8") as f:
                data = json.load(f)
                if isinstance(data, type(default_val)):
                    return data
        except Exception:
            pass
    return default_val

def save_json(filepath, data):
    with open(filepath, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

def format_czas(sekundy):
    if not sekundy:
        return "0s"
    h = int(sekundy // 3600)
    m = int((sekundy % 3600) // 60)
    s = int(sekundy % 60)
    if h > 0:
        return f"{h}h {m}m {s}s"
    elif m > 0:
        return f"{m}m {s}s"
    else:
        return f"{s}s"

st.title("🏃‍♂️ Dziennik Treningowy: Droga do Maratonu w Krakowie")

tab1, tab2, tab3, tab4, tab5 = st.tabs(["🏋️‍♂️ Siłownia", "Garmin", "🥗 Fitatu", "📋 Generator Raportu", "📊 Omówienie tygodnia"])

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
            db_silownia = load_json(SILOWNIA_FILE, [])
            if not isinstance(db_silownia, list):
                db_silownia = []
                
            db_silownia.append({
                "data": str(data_treningu),
                "cwiczenie": cwiczenie,
                "serie": serie_dane
            })
            save_json(SILOWNIA_FILE, db_silownia)
            st.success(f"Dodano {cwiczenie} do dziennika!")
            st.rerun()
        else:
            st.warning("Wpisz nazwę ćwiczenia.")

    st.subheader("Historia i zarządzanie treningami siłowymi")
    db_silownia = load_json(SILOWNIA_FILE, [])
    if isinstance(db_silownia, list) and db_silownia:
        for idx, entry in enumerate(db_silownia):
            if isinstance(entry, dict) and "serie" in entry:
                serie_list = entry.get("serie", [])
                serie_str = ", ".join([f"S{s.get('seria', 1)}: {s.get('powt', 0)}x{s.get('ciezar', 0)}kg" for s in serie_list if isinstance(s, dict)])
                
                col_e1, col_e2 = st.columns([5, 1])
                with col_e1:
                    st.markdown(f"- **{entry.get('data', '')}** | **{entry.get('cwiczenie', '')}** $\rightarrow$ {serie_str}")
                with col_e2:
                    if st.button("Usuń", key=f"del_sil_{idx}"):
                        db_silownia.pop(idx)
                        save_json(SILOWNIA_FILE, db_silownia)
                        st.rerun()
    else:
        st.info("Brak wpisów w historii siłowni.")

# --- ZAKŁADKA 2: GARMIN ---
with tab2:
    st.header("Synchronizacja z Garmin Connect")
    st.info("⚠️ Uwaga: Garmin czasami blokuje zbyt częste próby logowania (błąd 429). Jeśli zobaczysz taki komunikat, odczekaj kilkanaście minut.")
    
    with st.form("garmin_form"):
        col_g1, col_g2 = st.columns(2)
        with col_g1:
            email = st.text_input("Email Garmin Connect")
        with col_g2:
            password = st.text_input("Hasło", type="password")
        submit_garmin = st.form_submit_button("Synchronizuj biegi i aktywności")

    if submit_garmin and email and password:
        if Garmin is None:
            st.error("Biblioteka garminconnect nie jest zainstalowana.")
        else:
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
            duration_sec = act.get("duration", 0)
            acts_data.append({
                "Data": act.get("startTimeLocal", "")[:10],
                "Nazwa": act.get("activityName", "Aktywność"),
                "Typ": act.get("activityType", {}).get("typeKey", ""),
                "Dystans (km)": round(act.get("distance", 0) / 1000, 2),
                "Czas trwania": format_czas(duration_sec),
                "Śr. Tętno": act.get("averageHR", "-")
            })
        st.dataframe(pd.DataFrame(acts_data), width="stretch")
    else:
        st.info("Brak synchronizowanych aktywności. Zaloguj się powyżej.")

# --- ZAKŁADKA 3: FITATU ---
with tab3:
    st.header("Żywienie i Kalorie (Fitatu) – Cały tydzień")
    
    dni_tygodnia = ["Poniedziałek", "Wtorek", "Środa", "Czwartek", "Piątek", "Sobota", "Niedziela"]
    fitatu_db = load_json(FITATU_FILE, {})
    if not isinstance(fitatu_db, dict):
        fitatu_db = {}
        
    updated_fitatu = {}
    for dzien in dni_tygodnia:
        st.subheader(dzien)
        dane_dnia = fitatu_db.get(dzien, {"kcal": 2300, "b": 170, "t": 75, "w": 235, "spalone": 0})
        
        c1, c2, c3, c4, c5 = st.columns(5)
        with c1:
            kcal = st.number_input("Zjedzone Kcal", min_value=0, value=int(dane_dnia.get("kcal", 2300)), key=f"f_kcal_{dzien}")
        with c2:
            b = st.number_input("Białko (g)", min_value=0, value=int(dane_dnia.get("b", 170)), key=f"f_b_{dzien}")
        with c3:
            t = st.number_input("Tłuszcze (g)", min_value=0, value=int(dane_dnia.get("t", 75)), key=f"f_t_{dzien}")
        with c4:
            w = st.number_input("Węgle (g)", min_value=0, value=int(dane_dnia.get("w", 235)), key=f"f_w_{dzien}")
        with c5:
            spalone = st.number_input("Spalone Kcal", min_value=0, value=int(dane_dnia.get("spalone", 0)), key=f"f_sp_{dzien}")
            
        updated_fitatu[dzien] = {"kcal": kcal, "b": b, "t": t, "w": w, "spalone": spalone}
        st.write("---")
        
    if st.button("Zapisz wszystkie dni Fitatu"):
        save_json(FITATU_FILE, updated_fitatu)
        st.success("Zapisano dane Fitatu dla całego tygodnia!")

# --- ZAKŁADKA 4: GENERATOR RAPORTU ---
with tab4:
    st.header("Wygeneruj raport tygodniowy")
    st.write("Kliknij przycisk, skopiuj poniższy tekst i wklej go w zakładce 'Omówienie tygodnia' lub bezpośrednio na czacie.")
    
    if st.button("Generuj Raport"):
        db_silownia = load_json(SILOWNIA_FILE, [])
        fitatu_db = load_json(FITATU_FILE, {})
        garmin_acts = st.session_state.get("garmin_activities", [])
        
        raport = "=== PODSUMOWANIE TYGODNIA ===\n\n"
        
        raport += "1. SIŁOWNIA:\n"
        if isinstance(db_silownia, list) and db_silownia:
            for item in db_silownia:
                if isinstance(item, dict):
                    serie_list = item.get("serie", [])
                    serie_str = ", ".join([f"S{s.get('seria', 1)}: {s.get('powt', 0)}x{s.get('ciezar', 0)}kg" for s in serie_list if isinstance(s, dict)])
                    raport += f"- {item.get('data', '')} | {item.get('cwiczenie', '')}: {serie_str}\n"
        else:
            raport += "Brak wpisów z siłowni.\n"
            
        raport += "\n2. GARMIN (Treningi):\n"
        if garmin_acts:
            for act in garmin_acts:
                nazwa = act.get("activityName", "Aktywność")
                dystans = round(act.get("distance", 0) / 1000, 2)
                czas_str = format_czas(act.get("duration", 0))
                hr = act.get("averageHR", "-")
                raport += f"- {act.get('startTimeLocal', '')[:10]} | {nazwa} | Dystans: {dystans} km | Czas: {czas_str} | HR: {hr}\n"
        else:
            raport += "Brak pobranych aktywności z Garmina.\n"
            
        raport += "\n3. FITATU (Dieta i Kalorie):\n"
        if isinstance(fitatu_db, dict) and fitatu_db:
            for dzien, d in fitatu_db.items():
                if isinstance(d, dict):
                    raport += f"- {dzien}: {d.get('kcal')} kcal (B: {d.get('b')}g, T: {d.get('t')}g, W: {d.get('w')}g) | Spalone: {d.get('spalone')} kcal\n"
        else:
            raport += "Brak wpisów w Fitatu.\n"
            
        st.text_area("Gotowy raport (skopiuj całość):", raport, height=300)

# --- ZAKŁADKA 5: OMÓWIENIE TYGODNIA ---
with tab5:
    st.header("Omówienie i Analiza Tygodnia")
    st.write("Wklej tutaj wygenerowany raport lub swoje notatki z minionego tygodnia, abyśmy mogli wspólnie przeanalizować postępy i zaplanować kolejny krok.")
    
    notatki = st.text_area("Wklej raport / notatki do omówienia:", height=250)
    if notatki:
        st.success("Raport gotowy do omówienia! Wklej go teraz tutaj na czacie, a przeanalizujemy go punkt po punkcie.")
