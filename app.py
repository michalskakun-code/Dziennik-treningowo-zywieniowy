import streamlit as st
import pandas as pd
from datetime import date, timedelta
import json
import os

try:
    from garminconnect import Garmin
except ImportError:
    Garmin = None

try:
    import google.generativeai as genai
except ImportError:
    genai = None

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

def m_s_to_pace(m_s):
    if not m_s or m_s <= 0:
        return "-"
    sec_per_km = 1000 / m_s
    m = int(sec_per_km // 60)
    s = int(sec_per_km % 60)
    return f"{m}:{s:02d} min/km"

st.title("🏃‍♂️ Dziennik Treningowy: Droga do Maratonu w Krakowie")

tab1, tab2, tab3, tab4, tab5, tab6 = st.tabs(["🏋️‍♂️ Siłownia", "Garmin", "🥗 Fitatu", "📋 Generator Raportu", "📊 Omówienie", "🤖 Gemini"])

# --- ZAKŁADKA 1: SIŁOWNIA ---
with tab1:
    st.header("Zapisz trening siłowy")
    db_silownia = load_json(SILOWNIA_FILE, [])
    if "edit_idx" not in st.session_state:
        st.session_state["edit_idx"] = None

    editing_index = st.session_state["edit_idx"]
    if editing_index is not None and 0 <= editing_index < len(db_silownia):
        st.info(f"Edytujesz wpis z dnia: {db_silownia[editing_index].get('data')}")
        item_to_edit = db_silownia[editing_index]
        ed_data = st.date_input("Data (edycja)", value=date.fromisoformat(item_to_edit.get("data", str(date.today()))), key="ed_data")
        ed_cwiczenie = st.text_input("Nazwa ćwiczenia (edycja)", value=item_to_edit.get("cwiczenie", ""), key="ed_cw")
        
        ed_serie = []
        old_serie = item_to_edit.get("serie", [])
        for i, s in enumerate(old_serie):
            c1, c2 = st.columns(2)
            with c1:
                p = st.number_input(f"Powt. S{i+1}", min_value=1, value=int(s.get("powt", 8)), key=f"ed_p_{i}")
            with c2:
                kg = st.number_input(f"Ciężar S{i+1} (kg)", min_value=0.0, value=float(s.get("ciezar", 0.0)), step=2.5, key=f"ed_kg_{i}")
            ed_serie.append({"seria": i+1, "powt": p, "ciezar": kg})
            
        col_act1, col_act2 = st.columns(2)
        with col_act1:
            if st.button("Zapisz zmiany"):
                db_silownia[editing_index] = {"data": str(ed_data), "cwiczenie": ed_cwiczenie, "serie": ed_serie}
                save_json(SILOWNIA_FILE, db_silownia)
                st.session_state["edit_idx"] = None
                st.success("Zaktualizowano wpis!")
                st.rerun()
        with col_act2:
            if st.button("Anuluj edycję"):
                st.session_state["edit_idx"] = None
                st.rerun()
        st.write("---")

    col_d, col_c = st.columns(2)
    with col_d:
        data_treningu = st.date_input("Data treningu", date.today())
    with col_c:
        cwiczenie = st.text_input("Nazwa ćwiczenia (np. Przysiad ze sztangą)")
    
    liczba_serii = st.number_input("Liczba serii", min_value=1, max_value=10, value=3, step=1)
    
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
            db_silownia.append({"data": str(data_treningu), "cwiczenie": cwiczenie, "serie": serie_dane})
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
                col_e1, col_e2, col_e3 = st.columns([4, 1, 1])
                with col_e1:
                    st.markdown(f"- **{entry.get('data', '')}** | **{entry.get('cwiczenie', '')}** $\rightarrow$ {serie_str}")
                with col_e2:
                    if st.button("Edytuj", key=f"edit_sil_{idx}"):
                        st.session_state["edit_idx"] = idx
                        st.rerun()
                with col_e3:
                    if st.button("Usuń", key=f"del_sil_{idx}"):
                        db_silownia.pop(idx)
                        save_json(SILOWNIA_FILE, db_silownia)
                        if st.session_state["edit_idx"] == idx:
                            st.session_state["edit_idx"] = None
                        st.rerun()

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
        if Garmin is None:
            st.error("Brak biblioteki garminconnect.")
        else:
            try:
                client = Garmin(email, password)
                client.login()
                today = date.today()
                start_date = today - timedelta(days=7)
                activities = client.get_activities_by_date(start_date.isoformat(), today.isoformat(), "")
                st.session_state["garmin_client"] = client
                st.session_state["garmin_activities"] = activities
                st.success(f"Pobrano {len(activities)} aktywności z ostatnich 7 dni.")
            except Exception as e:
                st.error(f"Błąd logowania do Garmina: {e}")

    garmin_acts = st.session_state.get("garmin_activities", [])
    client = st.session_state.get("garmin_client", None)
    if garmin_acts:
        for idx, act in enumerate(garmin_acts):
            aid = act.get("activityId")
            aname = act.get("activityName", "Aktywność")
            adate = act.get("startTimeLocal", "")[:10]
            adist = round(act.get("distance", 0) / 1000, 2)
            atime = format_czas(act.get("duration", 0))
            ahr = act.get("averageHR", "-")
            mhr = act.get("maxHR", "-")
            kcal = act.get("calories", "-")
            with st.expander(f"📌 {adate} | {aname} ({adist} km, {atime})"):
                c_a1, c_a2, c_a3 = st.columns(3)
                with c_a1:
                    st.metric("Dystans", f"{adist} km")
                    st.metric("Średnie Tętno", f"{ahr} bpm")
                with c_a2:
                    st.metric("Czas trwania", atime)
                    st.metric("Maksymalne Tętno", f"{mhr} bpm")
                with c_a3:
                    st.metric("Spalone Kalorie", f"{kcal} kcal")
                if client and aid:
                    if st.button(f"Pobierz wykresy i okrążenia", key=f"det_{aid}"):
                        try:
                            splits_data = client.get_activity_splits(aid)
                            lap_list = splits_data.get("lapDTOs", []) if isinstance(splits_data, dict) else (splits_data if isinstance(splits_data, list) else [])
                            laps = []
                            for i, lap in enumerate(lap_list):
                                dist_km = round(lap.get("distance", 0) / 1000, 2)
                                duration_s = lap.get("duration", 0)
                                avg_speed = lap.get("averageSpeed", 0)
                                pace_sec = (1000 / avg_speed) if avg_speed > 0 else 0
                                laps.append({
                                    "Okrążenie": i + 1, "Dystans (km)": dist_km,
                                    "Czas": format_czas(duration_s), "Tempo": m_s_to_pace(avg_speed),
                                    "Śr. T
