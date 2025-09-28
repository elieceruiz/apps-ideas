# app.py
import streamlit as st
import pytz
from pymongo import MongoClient
from datetime import datetime, timedelta
from streamlit_autorefresh import st_autorefresh
from twilio.rest import Client

# ==============================
# CONFIG
# ==============================
st.set_page_config(page_title="💡 Apps Ideas", page_icon="💡", layout="centered")

# Leer configuración MongoDB de Secrets
mongodb_uri = st.secrets["mongodb"]["uri"]
mongodb_db = st.secrets["mongodb"]["db"]
mongodb_collection = st.secrets["mongodb"]["collection"]
mongodb_collection_desarrollo = st.secrets["mongodb"]["collection_desarrollo"]

# Conexión a MongoDB
client = MongoClient(mongodb_uri)
db = client[mongodb_db]
collection = db[mongodb_collection]
collection_desarrollo = db[mongodb_collection_desarrollo]

# Zona horaria Colombia
colombia_tz = pytz.timezone("America/Bogota")

# Config Twilio
twilio_sid = st.secrets["twilio"]["account_sid"]
twilio_token = st.secrets["twilio"]["auth_token"]
twilio_from = f"whatsapp:{st.secrets['twilio']['sandbox_number']}"
twilio_to = f"whatsapp:{st.secrets['twilio']['to_number']}"
client_twilio = Client(twilio_sid, twilio_token)

st.title("💡 Apps Ideas")

# ==============================
# FUNCIONES
# ==============================
def guardar_idea(titulo: str, descripcion: str):
    if titulo.strip() == "" or descripcion.strip() == "":
        st.error("Complete todos los campos por favor")
        return False
    nueva_idea = {
        "title": titulo.strip(),
        "description": descripcion.strip(),
        "timestamp": datetime.now(pytz.UTC),
        "updates": []
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
        {"_id": idea_id},
        {"$push": {"updates": nueva_actualizacion}}
    )
    st.success("📝 Nota agregada a la idea")
    return True


def listar_ideas():
    st.subheader("📌 Guardadas")
    ideas = collection.find().sort("timestamp", -1)
    for idea in ideas:
        fecha_local = idea["timestamp"].astimezone(colombia_tz)
        with st.expander(f"💡 {idea['title']}  —  {fecha_local.strftime('%Y-%m-%d %H:%M')}"):
            st.write(idea["description"])
            if "updates" in idea and len(idea["updates"]) > 0:
                st.markdown("**Trazabilidad / Notas adicionales:**")
                for note in idea["updates"]:
                    fecha_nota_local = note["timestamp"].astimezone(colombia_tz)
                    st.markdown(
                        f"➡️ {note['text']}  \n ⏰ {fecha_nota_local.strftime('%Y-%m-%d %H:%M')}"
                    )
                st.divider()
            with st.form(f"form_update_{idea['_id']}", clear_on_submit=True):
                nueva_nota = st.text_area("Agregar nota", key=f"nota_{idea['_id']}")
                enviar_nota = st.form_submit_button("Guardar nota")
                if enviar_nota:
                    agregar_nota(idea["_id"], nueva_nota)
                    st.rerun()

# ==============================
# CRONÓMETRO GLOBAL
# ==============================
st.subheader("⏱️ Cronómetro Global")

if "cronometro_inicio" not in st.session_state:
    st.session_state["cronometro_inicio"] = None
if "cronometro_activo" not in st.session_state:
    st.session_state["cronometro_activo"] = False
if "whatsapp_enviado" not in st.session_state:
    st.session_state["whatsapp_enviado"] = False

col1, col2 = st.columns(2)

if not st.session_state["cronometro_activo"]:
    if col1.button("▶️ Iniciar"):
        st.session_state["cronometro_inicio"] = datetime.now(pytz.UTC)
        st.session_state["cronometro_activo"] = True
        st.session_state["whatsapp_enviado"] = False
else:
    if col2.button("⏹️ Parar"):
        fin = datetime.now(pytz.UTC)
        duracion = fin - st.session_state["cronometro_inicio"]
        registro = {
            "inicio": st.session_state["cronometro_inicio"],
            "fin": fin,
            "duracion_segundos": int(duracion.total_seconds())
        }
        collection_desarrollo.insert_one(registro)
        st.session_state["cronometro_inicio"] = None
        st.session_state["cronometro_activo"] = False
        st.session_state["whatsapp_enviado"] = False

# Refresco automático al segundo
st_autorefresh(interval=1000, key="cronometro_refresh")

# Mostrar tiempo transcurrido
if st.session_state["cronometro_activo"] and st.session_state["cronometro_inicio"]:
    transcurrido = datetime.now(pytz.UTC) - st.session_state["cronometro_inicio"]
    st.write("Tiempo transcurrido:")
    st.write(str(transcurrido).split(".")[0])  # sin microsegundos
    st.write("⏳ Debug:", transcurrido.total_seconds(), "segundos")  # DEBUG

    # Enviar WhatsApp a los 60s
    if transcurrido >= timedelta(minutes=1) and not st.session_state["whatsapp_enviado"]:
        try:
            client_twilio.messages.create(
                body="📲 Han pasado 60 segundos desde que iniciaste el cronómetro.",
                from_=twilio_from,
                to=twilio_to
            )
            st.session_state["whatsapp_enviado"] = True
            st.success("✅ WhatsApp enviado a los 60 segundos")
        except Exception as e:
            st.error(f"❌ Error enviando WhatsApp: {e}")

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
