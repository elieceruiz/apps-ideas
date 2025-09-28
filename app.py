# app.py
import streamlit as st
import pytz
from pymongo import MongoClient
from datetime import datetime
from dateutil import parser
from twilio.rest import Client

# ==============================
# CONFIG
# ==============================
st.set_page_config(page_title="💡 Apps Ideas", page_icon="💡", layout="centered")

# Leer configuración MongoDB de Secrets
mongodb_uri = st.secrets["mongodb"]["uri"]
mongodb_db = st.secrets["mongodb"]["db"]
mongodb_collection = st.secrets["mongodb"]["collection"]

# Config Twilio
twilio_sid = st.secrets["twilio"]["account_sid"]
twilio_token = st.secrets["twilio"]["auth_token"]
twilio_from = f"whatsapp:{st.secrets['twilio']['sandbox_number']}"
twilio_to = f"whatsapp:{st.secrets['twilio']['to_number']}"

twilio_client = Client(twilio_sid, twilio_token)

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
        "updates": [],
        "sessions": []  # ahora cada idea podrá tener sesiones
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
        "timestamp": datetime.now(pytz.UTC)
    }
    collection.update_one(
        {"_id": idea_id},
        {"$push": {"updates": nueva_actualizacion}}
    )
    st.success("📝 Nota agregada a la idea")
    return True


def iniciar_sesion(idea_id):
    """Inicia una sesión de cronómetro para una idea."""
    nueva_sesion = {
        "inicio": datetime.now(pytz.UTC),
        "fin": None
    }
    collection.update_one(
        {"_id": idea_id},
        {"$push": {"sessions": nueva_sesion}}
    )
    st.success("▶️ Sesión iniciada")
    # Enviar WhatsApp inmediato
    try:
        mensaje = f"🚀 Iniciaste sesión de trabajo en tu idea."
        msg = twilio_client.messages.create(
            body=mensaje,
            from_=twilio_from,
            to=twilio_to
        )
        st.info(f"📤 Debug Twilio SID: {msg.sid}")
    except Exception as e:
        st.error(f"⚠️ Error al enviar WhatsApp: {e}")


def detener_sesion(idea_id):
    """Detiene la última sesión activa de una idea."""
    idea = collection.find_one({"_id": idea_id})
    if not idea or "sessions" not in idea or len(idea["sessions"]) == 0:
        st.warning("⚠️ No hay sesiones para detener")
        return

    ultima = idea["sessions"][-1]
    if ultima["fin"] is None:
        collection.update_one(
            {"_id": idea_id, "sessions.inicio": ultima["inicio"]},
            {"$set": {"sessions.$.fin": datetime.now(pytz.UTC)}}
        )
        st.success("⏹ Sesión detenida")
        try:
            mensaje = f"✅ Finalizaste sesión de trabajo en tu idea."
            msg = twilio_client.messages.create(
                body=mensaje,
                from_=twilio_from,
                to=twilio_to
            )
            st.info(f"📤 Debug Twilio SID: {msg.sid}")
        except Exception as e:
            st.error(f"⚠️ Error al enviar WhatsApp: {e}")
    else:
        st.warning("⚠️ No hay sesión activa")


def listar_ideas():
    """Muestra las ideas guardadas con trazabilidad y cronómetro."""
    st.subheader("📌 Guardadas")
    ideas = collection.find().sort("timestamp", -1)

    for idea in ideas:
        fecha_local = idea["timestamp"].astimezone(colombia_tz)
        with st.expander(f"💡 {idea['title']}  —  {fecha_local.strftime('%Y-%m-%d %H:%M')}"):
            st.write(idea["description"])

            # =========================
            # Cronómetro de sesiones
            # =========================
            sesiones = idea.get("sessions", [])
            sesion_activa = None
            for s in sesiones:
                if s["fin"] is None:
                    sesion_activa = s
                    break

            if sesion_activa:
                inicio = sesion_activa.get("inicio")
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
                    st.warning("⚠️ Cronómetro activo pero sin fecha válida (debug).")

                if st.button("⏹ Detener sesión", key=f"stop_{idea['_id']}"):
                    detener_sesion(idea["_id"])
                    st.rerun()
            else:
                if st.button("▶️ Iniciar sesión", key=f"start_{idea['_id']}"):
                    iniciar_sesion(idea["_id"])
                    st.rerun()

            # =========================
            # Historial de actualizaciones
            # =========================
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
