# app.py
import streamlit as st
import pytz
from pymongo import MongoClient
from datetime import datetime
from dateutil import parser  # para parsear strings a datetime

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
        return False

    nueva_idea = {
        "title": titulo.strip(),
        "description": descripcion.strip(),
        "timestamp": datetime.now(pytz.UTC),  # siempre guardar en UTC
        "updates": [],  # historial de trazabilidad
        "sessions": []  # sesiones de cronómetro
    }
    collection.insert_one(nueva_idea)
    st.success("✅ Idea guardada correctamente")
    return True


def agregar_nota(idea_id, texto: str):
    """Agrega una nota de trazabilidad a una idea existente."""
    if texto.strip() == "":
        st.error("La nota no puede estar vacía")
        return False

    nueva_actualizacion = {
        "text": texto.strip(),
        "timestamp": datetime.now(pytz.UTC)  # guardar en UTC
    }
    collection.update_one(
        {"_id": idea_id},
        {"$push": {"updates": nueva_actualizacion}}
    )
    st.success("📝 Nota agregada a la idea")
    return True


def listar_ideas():
    """Muestra las ideas guardadas con su trazabilidad, sesiones y notas."""
    st.subheader("📌 Guardadas")
    ideas = collection.find().sort("timestamp", -1)

    for idea in ideas:
        fecha_local = idea["timestamp"].astimezone(colombia_tz)
        with st.expander(f"💡 {idea['title']}  —  {fecha_local.strftime('%Y-%m-%d %H:%M')}"):
            st.write(idea["description"])

            # ======================
            # Cronómetro
            # ======================
            sesiones = idea.get("sessions", [])
            sesion_activa = next((s for s in sesiones if s.get("fin") is None), None)

            if sesion_activa:
                inicio = sesion_activa.get("inicio")

                if inicio:
                    if isinstance(inicio, str):
                        try:
                            inicio = parser.parse(inicio)
                        except Exception:
                            inicio = None

                if isinstance(inicio, datetime):
                    segundos = int((datetime.now(pytz.UTC) - inicio).total_seconds())
                    horas, resto = divmod(segundos, 3600)
                    minutos, segundos = divmod(resto, 60)
                    st.markdown(
                        f"⏱ **Cronómetro en curso:** {horas:02}:{minutos:02}:{segundos:02}"
                    )
                else:
                    st.warning("⚠️ Cronómetro activo pero con inicio inválido.")

                if st.button("⏹ Detener", key=f"stop_{idea['_id']}"):
                    collection.update_one(
                        {"_id": idea["_id"], "sessions.inicio": sesion_activa.get("inicio")},
                        {"$set": {"sessions.$.fin": datetime.now(pytz.UTC)}}
                    )
                    st.rerun()
            else:
                if st.button("▶️ Iniciar cronómetro", key=f"start_{idea['_id']}"):
                    nueva_sesion = {
                        "inicio": datetime.now(pytz.UTC),
                        "fin": None
                    }
                    collection.update_one(
                        {"_id": idea["_id"]},
                        {"$push": {"sessions": nueva_sesion}}
                    )
                    st.rerun()

            # Historial de actualizaciones
            if "updates" in idea and len(idea["updates"]) > 0:
                st.markdown("**Trazabilidad / Notas adicionales:**")
                for note in idea["updates"]:
                    fecha_nota_local = note["timestamp"].astimezone(colombia_tz)
                    st.markdown(
                        f"➡️ {note['text']}  \n ⏰ {fecha_nota_local.strftime('%Y-%m-%d %H:%M')}"
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
