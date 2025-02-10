import streamlit as st
import pandas as pd
import os
import json
import random
from pymongo.mongo_client import MongoClient
from pymongo.server_api import ServerApi
from dotenv import load_dotenv

st.set_page_config(layout="wide")

load_dotenv()
password = os.getenv("MONGODB_PASSWORD")
uri = f"mongodb+srv://ingunn:{password}@samiaeval.2obnm.mongodb.net/?retryWrites=true&w=majority&tlsAllowInvalidCertificates=true"

client = MongoClient(uri, server_api=ServerApi('1'))
evaluering_kolleksjon = client['SamiaEvalDB']['personalisering_evaluering']

bruker_id = st.text_input("Skriv inn ditt navn eller ID:", key="bruker_id")
if not bruker_id:
    st.stop()

def lagre_evaluering_mongodb(kolleksjon, evaluering):
    """Lagrer evalueringer i MongoDB."""
    try:
        kolleksjon.insert_one(evaluering)
        st.success("Evaluering lagret!")
    except Exception as e:
        st.error(f"Feil under lagring i MongoDB: {e}")

def les_datasett(filsti):
    return pd.read_csv(filsti)

undersokelse_svart = evaluering_kolleksjon.find_one({'bruker_id': bruker_id, 'type': 'undersokelse'})

if not undersokelse_svart:
    st.title("Brukerundersøkelse")
    st.header("Før vi starter, vennligst svar på noen spørsmål:")

    svar_lengde = st.radio(
        "Hvor lange mener du at nyhetssammendrag burde være?",
        options=["1-2 setninger", "Et kort avsnitt", "En mer detaljert oppsummering (flere avsnitt)", "Varierer avhengig av sakens kompleksitet"]
    )

    svar_presentasjon = st.radio(
        "Hvordan foretrekker du at nyhetssammendrag presenteres?",
        options=[
            "Nøytralt og objektivt, uten vurderinger",
            "Kort og konsist, med kun de viktigste fakta",
            "Med en kort vurdering av saken",
            "Med forklaringer av komplekse begreper eller sammenhenger"
        ]
    )

    svar_bakgrunn = st.radio(
        "Hvor viktig er det at nyhetssammendrag gir bakgrunnsinformasjon og kontekst?",
        options=["Svært viktig", "Litt viktig", "Ikke viktig"]
    )

    svar_viktigst = st.radio(
        "Hva er viktigst for deg?",
        options=[
            "At nyhetssammendraget gir meg all relevant informasjon raskt",
            "At nyhetssammendraget forklarer hvorfor saken er viktig",
            "At nyhetssammendraget er enkelt å forstå",
            "At nyhetssammendraget har god språklig kvalitet"
        ]
    )

    svar_irriterende = st.radio(
        "Hva ville irritert deg mest med et nyhetssammendrag?",
        options=[
            "Upresis eller unøyaktig informasjon",
            "For mye tekst eller unødvendige detaljer",
            "Mangel på kontekst eller bakgrunn",
            "Et subjektivt eller vinklet språk"
        ]
    )

    if st.button("Start evaluering"):
        undersokelse = {
            'bruker_id': bruker_id,
            'type': 'undersokelse',
            'svar_lengde': svar_lengde,
            'svar_presentasjon': svar_presentasjon,
            'svar_bakgrunn': svar_bakgrunn,
            'svar_viktigst': svar_viktigst,
            'svar_irriterende': svar_irriterende
        }
        evaluering_kolleksjon.insert_one(undersokelse)
        st.success("Takk for at du svarte! Du kan nå starte evalueringen.")
        st.rerun()

else:
    st.write("Takk for at du svarte på undersøkelsen tidligere! Du kan nå fortsette til evalueringen.")

st.title("Evaluering av sammendrag")

filsti = 'data.csv'
data = les_datasett(filsti)

if f'artikkel_indeks_{bruker_id}' not in st.session_state:
    bruker_evaluering = evaluering_kolleksjon.find_one({'bruker_id': bruker_id}, sort=[('_id', -1)])
    st.session_state[f'artikkel_indeks_{bruker_id}'] = (
    bruker_evaluering.get('artikkel_indeks', -1) + 1 if bruker_evaluering else 0
)

start_indeks = st.session_state[f'artikkel_indeks_{bruker_id}']
if start_indeks >= len(data):
    st.success("Alle artikler er evaluert!")
    st.stop()

row = data.iloc[start_indeks]

st.header(f"Artikkel {start_indeks + 1}/{len(data)}")
#st.markdown(f"[Les artikkelen på TV2 sine nettsider her.]({row['url']})", unsafe_allow_html=True)

st.markdown(f"""
<div class='main-container'>
    <h1 class='article-title'>{row['title']}</h1>
    <div class='lead-text'>{row['byline']}</div>
    <div class='lead-text'>Publisert: {row['creation_date']}</div>
    <div class='lead-text'>{row['lead_text']}</div>
    <div class='article-body'>{row['artikkeltekst']}</div>
</div>
""", unsafe_allow_html=True)

if f"valgte_sammendrag_{bruker_id}_{start_indeks}" not in st.session_state:
    sammendrag_liste = [(col.replace('prompt_', ''), row[col]) for col in row.index if 'prompt' in col]
    random.shuffle(sammendrag_liste)
    st.session_state[f"valgte_sammendrag_{bruker_id}_{start_indeks}"] = sammendrag_liste[:3]

valgte_sammendrag = st.session_state[f"valgte_sammendrag_{bruker_id}_{start_indeks}"]

st.subheader("Sammendrag:")
rankings = {}
ranking_options = ["Best", "Middels", "Dårligst"]

for i, (kilde, tekst) in enumerate(valgte_sammendrag):
    with st.expander(f"Sammendrag {i + 1}"):
        st.write(tekst)
        rankings[kilde] = st.selectbox(
            f"Ranger sammendrag {i + 1}", ranking_options, key=f"ranking_{bruker_id}_{start_indeks}_{i}")

kommentar = st.text_area("Kommentar:", key=f"kommentar_{bruker_id}_{start_indeks}")

if st.button("Lagre evaluering", key=f"lagre_{bruker_id}_{start_indeks}"):
    evaluering = {
        'bruker_id': bruker_id,
        'artikkel_indeks': start_indeks,
        'uuid': row['uuid'],
        'rangeringer': rankings,
        'sammendrag_kilder': [kilde for kilde, _ in valgte_sammendrag],
        'kommentar': kommentar
    }
    lagre_evaluering_mongodb(evaluering_kolleksjon, evaluering)
    
    st.session_state[f'artikkel_indeks_{bruker_id}'] += 1
    st.rerun()

st.markdown("""
    <style>
        .main-container {
            max-width: 800px;  /* Gjør containeren smalere */
            margin: auto;
            padding: 20px;
            background-color: #f9f9f9;
            border-radius: 8px;
            box-shadow: 0 4px 8px rgba(0, 0, 0, 0.1);
            max-height: 800px;
            overflow-y: auto;
        }
        .article-title {
            font-size: 28px;
            font-weight: bold;
            color: #333;
            margin-bottom: 10px;
        }
        .lead-text {
            font-size: 18px;
            color: #555;
            margin-bottom: 20px;
        }
        .article-body {
            font-size: 16px;
            line-height: 1.6;
            color: #444;
            margin-bottom: 30px;
        }
        .summary-box {
            background: white;
            padding: 15px;
            border: 1px solid #ddd;
            border-radius: 8px;
            margin-bottom: 20px;
            box-shadow: 0 2px 4px rgba(0, 0, 0, 0.05);
        }
        .summary-header {
            font-weight: bold;
            margin-bottom: 10px;
        }
        .evaluation-section {
            background-color: #fff;
            padding: 20px;
            border: 1px solid #ddd;
            border-radius: 8px;
        }
        .evaluation-button {
            background-color: #2051b3;
            color: white;
            padding: 10px 20px;
            border: none;
            border-radius: 6px;
            cursor: pointer;
        }
        .evaluation-button:hover {
            background-color: #183c85;
        }
    </style>
""", unsafe_allow_html=True)