# app.py
import streamlit as st
import pytz
from pymongo import MongoClient
from datetime import datetime
from bson import ObjectId
from twilio.rest import Client

# ==============================
# CONFIG
# ==============================
st.set_page_config(page_title="💡 Apps Ideas", page_icon="💡", layout="centered")

# MongoDB
mongodb_uri = st.secrets["mongodb"]["uri"]
mongodb_db = st.secrets["mongodb"]["db"]
mongodb_collection = st.secrets["mongodb"]["collection"]

client = MongoClient(mongodb_uri)
db = client[mongodb_db]
collection = db[mongodb_collection]

# Twilio
twilio_sid = st.secrets["twilio"]["account_sid"]
twilio_token = st.secrets["twilio"]["auth_token"]
twilio_from = st.secrets["twilio"]["sandbox_number"]
twilio_to = st.secrets["twilio"]["to_number"]
twilio_client = Client(twilio_sid, twilio_token)

# Zona horaria
colombia_tz = pytz.timezone("America/Bogota")

st.title("💡 Apps Ideas")

# ==============================
# FUNCIONES
# ==============================
def parse_datetime(value):
    """Convierte value a datetime si viene como string ISO."""
    if isinstance(value, datetime):
        return value
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00"))
    except Exception:
        return None


def guardar_idea(titulo: str, descripcion: str):
    if titulo.strip() == "" or descripcion.strip() == "":
        st.error("Complete todos los campos por favor")
        return False

    nueva_idea = {
        "title": titulo.strip(),
        "description": descripcion.strip(),
        "timestamp": datetime.now(pytz.UTC),
        "updates": [],
        "sessions": []  # sesiones de trabajo
    }
    collection.insert_one(nueva_idea)
    st.success("✅ Idea guardada correctamente")
    return True


def agregar_nota(idea_id, texto: str):
    if texto.strip() == "":
        st.error("La nota no puede estar vacía")
        return False

    nueva_actualizacion = {
        "text": texto.strip(),
        "timestamp": datetime.now(pytz.UTC)
    }
    collection.update_one(
        {"_id": ObjectId(idea_id)},
        {"$push": {"updates": nueva_actualizacion}}
    )
    st.success("📝 Nota agregada a la idea")

    # Notificación por Twilio
    try:
        twilio_client.messages.create(
            body=f"Nueva nota en idea {idea_id}: {texto.strip()}",
            from_=twilio_from,
            to=twilio_to
        )
    except Exception as e:
        st.warning(f"⚠️ No se pudo enviar mensaje Twilio: {e}")

    return True


def listar_ideas():
    st.subheader("📌 Guardadas")
    ideas = collection.find().sort("timestamp", -1)

    for idea in ideas:
        fecha_local = idea["timestamp"].astimezone(colombia_tz)
        with st.expander(f"💡 {idea['title']}  —  {fecha_local.strftime('%Y-%m-%d %H:%M')}"):
            st.write(idea["description"])

            # Sesiones (debug)
            if "sessions" in idea and idea["sessions"]:
                st.markdown("**⏱ Sesiones registradas:**")

                for i, sesion in enumerate(idea["sessions"], start=1):
                    st.write(f"🔍 Sesión {i} cruda desde MongoDB:")
                    st.json(sesion)  # mostrar el objeto tal cual

                    inicio = parse_datetime(sesion.get("inicio"))
                    fin = parse_datetime(sesion.get("fin"))

                    st.write(f"👉 inicio parsed: {inicio} ({type(inicio)})")
                    st.write(f"👉 fin parsed: {fin} ({type(fin)})")

                    if inicio:
                        if fin:
                            duracion = int((fin - inicio).total_seconds())
                            st.success(f"✔️ Finalizada: {duracion // 60} min {duracion % 60} seg")
                        else:
                            try:
                                segundos = int((datetime.now(pytz.UTC) - inicio).total_seconds())
                                st.info(f"⏳ Activa: {segundos // 60} min {segundos % 60} seg")
                            except Exception as e:
                                st.error(f"❌ Error restando datetime: {e}")
                    else:
                        st.warning("⚠️ Sesión sin inicio válido")

            # Historial de notas
            if "updates" in idea and idea["updates"]:
                st.markdown("**Trazabilidad / Notas adicionales:**")
                for note in idea["updates"]:
                    fecha_nota_local = note["timestamp"].astimezone(colombia_tz)
                    st.markdown(
                        f"➡️ {note['text']}  \n ⏰ {fecha_nota_local.strftime('%Y-%m-%d %H:%M')}"
                    )
                st.divider()

            # Formulario nota
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
