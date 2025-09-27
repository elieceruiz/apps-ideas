# app.py
import streamlit as st
import pytz
from pymongo import MongoClient
from datetime import datetime

# ==============================
# CONFIG
# ==============================
st.set_page_config(page_title="💡 Apps Ideas", page_icon="💡", layout="centered")

# === FLAG DEBUG ===
DEBUG = True  # ponelo en False cuando quieras limpio

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
        return False

    nueva_idea = {
        "title": titulo.strip(),
        "description": descripcion.strip(),
        "timestamp": datetime.now(colombia_tz),
        "updates": []  # historial de trazabilidad
    }
    collection.insert_one(nueva_idea)
    st.success("✅ Idea guardada correctamente")

    if DEBUG:
        st.write("🔍 Idea insertada:")
        st.json(nueva_idea)

    return True


def agregar_nota(idea_id, texto: str):
    """Agrega una nota de trazabilidad a una idea existente."""
    if texto.strip() == "":
        st.error("La nota no puede estar vacía")
        return False

    nueva_actualizacion = {
        "text": texto.strip(),
        "timestamp": datetime.now(colombia_tz)
    }
    collection.update_one(
        {"_id": idea_id},
        {"$push": {"updates": nueva_actualizacion}}
    )
    st.success("📝 Nota agregada a la idea")

    if DEBUG:
        st.write(f"🔍 Nota agregada en idea {idea_id}:")
        st.json(nueva_actualizacion)

    return True


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
                    st.markdown(
                        f"➡️ {note['text']}  \n ⏰ {note['timestamp'].strftime('%Y-%m-%d %H:%M')}"
                    )
                st.divider()

            # Formulario para agregar nueva nota
            with st.form(f"form_update_{idea['_id']}", clear_on_submit=True):
                nueva_nota = st.text_area("Agregar nota", key=f"nota_{idea['_id']}")
                enviar_nota = st.form_submit_button("Guardar nota")

                if enviar_nota:
                    agregar_nota(idea["_id"], nueva_nota)
                    st.rerun()

# ==============================
# UI PRINCIPAL
# ==============================
with st.form("form_agregar_idea", clear_on_submit=True):
    titulo_idea = st.text_input("Título de la idea")
    descripcion_idea = st.text_area("Descripción de la idea")
    envio = st.form_submit_button("Guardar idea")

    if envio:
        guardar_idea(titulo_idea, descripcion_idea)
        st.rerun()

listar_ideas()

# ==============================
# DEBUG EXTRA
# ==============================
if DEBUG:
    st.subheader("🔍 Estado completo de la sesión")
    st.json(dict(st.session_state))

    # === Traducción humana del estado ===
    def debug_humano(session_state: dict):
        salida = []
        for k, v in session_state.items():
            if k.startswith("FormSubmitter:form_agregar_idea"):
                estado = "presionado ✅" if v else "no presionado ❌"
                salida.append(f"📌 Botón 'Guardar idea': {estado}")

            elif k.startswith("FormSubmitter:form_update_"):
                idea_id = k.split("_")[2].split("-")[0]
                estado = "presionado ✅" if v else "no presionado ❌"
                salida.append(f"📝 Botón 'Guardar nota' (idea {idea_id}): {estado}")

            elif k.startswith("nota_"):
                idea_id = k.split("_")[1]
                if str(v).strip() == "":
                    salida.append(f"🗒️ Nota en idea {idea_id}: (vacía)")
                else:
                    salida.append(f"🗒️ Nota en idea {idea_id}: {v}")

            else:
                salida.append(f"⚙️ {k}: {v}")

        return salida

    st.subheader("🪄 Estado en lenguaje humano")
    for linea in debug_humano(dict(st.session_state)):
        st.write(linea)
