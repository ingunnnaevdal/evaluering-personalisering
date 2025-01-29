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
evaluering_kolleksjon = client['SamiaEvalDB']['evalueringer']

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

st.title("Evaluering av sammendrag")

filsti = 'data.csv'
data = les_datasett(filsti)

if f'artikkel_indeks_{bruker_id}' not in st.session_state:
    bruker_evaluering = evaluering_kolleksjon.find_one({'bruker_id': bruker_id}, sort=[('_id', -1)])
    st.session_state[f'artikkel_indeks_{bruker_id}'] = bruker_evaluering['artikkel_indeks'] + 1 if bruker_evaluering else 0

start_indeks = st.session_state[f'artikkel_indeks_{bruker_id}']
if start_indeks >= len(data):
    st.success("Alle artikler er evaluert!")
    st.stop()

row = data.iloc[start_indeks]

st.header(f"Artikkel {start_indeks + 1}/{len(data)}")
st.subheader("Artikkeltekst:")
st.write(row['artikkeltekst_clean'])

if f"valgte_sammendrag_{bruker_id}_{start_indeks}" not in st.session_state:
    sammendrag_liste = [(col.replace('prompt_', ''), row[col]) for col in row.index if 'prompt' in col]
    random.shuffle(sammendrag_liste)
    st.session_state[f"valgte_sammendrag_{bruker_id}_{start_indeks}"] = sammendrag_liste[:3]

valgte_sammendrag = st.session_state[f"valgte_sammendrag_{bruker_id}_{start_indeks}"]

st.subheader("Sammendrag:")
sammendrag_valg = []
for i, (kilde, tekst) in enumerate(valgte_sammendrag):
    with st.expander(f"Sammendrag {i + 1}"):
        st.write(tekst)
        sammendrag_valg.append(f"Sammendrag {i + 1}")

beste_sammendrag = st.radio("Hvilket sammendrag foretrekker du?", sammendrag_valg + ["Ingen"], index=len(sammendrag_valg), key=f"beste_sammendrag_{bruker_id}_{start_indeks}")
kommentar = st.text_area("Kommentar:", key=f"kommentar_{bruker_id}_{start_indeks}")

if st.button("Lagre evaluering", key=f"lagre_{bruker_id}_{start_indeks}"):
    valgt_kilde = None if beste_sammendrag == "Ingen" else valgte_sammendrag[sammendrag_valg.index(beste_sammendrag)][0]
    evaluering = {
        'bruker_id': bruker_id,
        'artikkel_indeks': start_indeks,
        'uuid': row['uuid'],
        'foretrukket_sammendrag': valgt_kilde if valgt_kilde else 'Ingen',
        'sammendrag_kilder': [kilde for kilde, _ in valgte_sammendrag],
        'kommentar': kommentar
    }
    lagre_evaluering_mongodb(evaluering_kolleksjon, evaluering)
    
    st.session_state[f'artikkel_indeks_{bruker_id}'] += 1
    st.rerun()
