# app.py
import streamlit as st
import pytz
from pymongo import MongoClient
from datetime import datetime

# ==============================
# CONFIG
# ==============================
st.set_page_config(page_title="💡 Apps Ideas", page_icon="💡", layout="centered")

# Leer configuración MongoDB de Secrets
mongodb_uri = st.secrets["mongodb"]["uri"]
mongodb_db = st.secrets["mongodb"]["db"]
mongodb_collection = st.secrets["mongodb"]["collection"]

# Conexión a MongoDB
client = MongoClient(mongodb_uri)
db = client[mongodb_db]
collection = db[mongodb_collection]

# Zona horaria Colombia
colombia_tz = pytz.timezone("America/Bogota")

st.title("💡 Apps Ideas")

# ==============================
# FUNCIONES
# ==============================
def guardar_idea(titulo: str, descripcion: str):
    """Guarda una nueva idea en la colección."""
    if titulo.strip() == "" or descripcion.strip() == "":
        st.error("Complete todos los campos por favor")
        return

    nueva_idea = {
        "title": titulo.strip(),
        "description": descripcion.strip(),
        "timestamp": datetime.now(colombia_tz),
        "updates": []  # historial de trazabilidad
    }
    collection.insert_one(nueva_idea)
    st.success("✅ Idea guardada correctamente")

    # Limpiar formulario principal
    st.session_state["titulo_idea"] = ""
    st.session_state["descripcion_idea"] = ""

    st.rerun()


def agregar_nota(idea_id, texto: str, key: str):
    """Agrega una nota de trazabilidad a una idea existente."""
    if texto.strip() == "":
        st.error("La nota no puede estar vacía")
        return

    nueva_actualizacion = {
        "text": texto.strip(),
        "timestamp": datetime.now(colombia_tz)
    }
    collection.update_one(
        {"_id": idea_id},
        {"$push": {"updates": nueva_actualizacion}}
    )
    st.success("📝 Nota agregada a la idea")

    # Limpiar el campo de nota de esta idea
    st.session_state[key] = ""

    st.rerun()


def listar_ideas():
    """Muestra las ideas guardadas con su trazabilidad y formulario de notas."""
    st.subheader("📌 Guardadas")
    ideas = collection.find().sort("timestamp", -1)

    for idea in ideas:
        with st.expander(f"💡 {idea['title']}  —  {idea['timestamp'].strftime('%Y-%m-%d %H:%M')}"):
            st.write(idea["description"])

            # Historial de actualizaciones
            if "updates" in idea and len(idea["updates"]) > 0:
                st.markdown("**Trazabilidad / Notas adicionales:**")
                for note in idea["updates"]:
                    st.markdown(f"➡️ {note['text']}  \n ⏰ {note['timestamp'].strftime('%Y-%m-%d %H:%M')}")
                st.divider()

            # Formulario para agregar nueva nota
            nota_key = f"nota_{idea['_id']}"
            with st.form(f"form_update_{idea['_id']}"):
                nueva_nota = st.text_area("Agregar nota", key=nota_key)
                enviar_nota = st.form_submit_button("Guardar nota")

                if enviar_nota:
                    agregar_nota(idea["_id"], nueva_nota, nota_key)

# ==============================
# UI PRINCIPAL
# ==============================
with st.form("form_agregar_idea"):
    titulo_idea = st.text_input("Título de la idea", key="titulo_idea")
    descripcion_idea = st.text_area("Descripción de la idea", key="descripcion_idea")
    envio = st.form_submit_button("Guardar idea")

    if envio:
        guardar_idea(titulo_idea, descripcion_idea)

listar_ideas()
