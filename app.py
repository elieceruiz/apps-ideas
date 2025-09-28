# app.py
import streamlit as st
import pytz
from pymongo import MongoClient
from datetime import datetime, timedelta

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
try:
    client = MongoClient(mongodb_uri)
    db = client[mongodb_db]
    collection = db[mongodb_collection]  # ideas
    collection_desarrollo = db[mongodb_collection_desarrollo]  # cronómetro global
except Exception as e:
    st.error(f"❌ Error de conexión a MongoDB: {e}")
    st.stop()

# Zona horaria Colombia
colombia_tz = pytz.timezone("America/Bogota")

st.title("💡 Apps Ideas")

# ==============================
# FUNCIONES
# ==============================
def guardar_idea(titulo: str, descripcion: str):
    try:
        if titulo.strip() == "" or descripcion.strip() == "":
            st.error("Complete todos los campos por favor")
            return False

        nueva_idea = {
            "title": titulo.strip(),
            "description": descripcion.strip(),
            "timestamp": datetime.now(pytz.UTC),  # siempre guardar en UTC
            "updates": []  # historial de trazabilidad
        }
        collection.insert_one(nueva_idea)
        st.success("✅ Idea guardada correctamente")
        return True
    except Exception as e:
        st.error(f"❌ Error al guardar idea: {e}")
        return False


def agregar_nota(idea_id, texto: str):
    try:
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
    except Exception as e:
        st.error(f"❌ Error al agregar nota: {e}")
        return False


def listar_ideas():
    try:
        st.subheader("📌 Guardadas")
        ideas = collection.find().sort("timestamp", -1)

        for idea in ideas:
            fecha_local = idea["timestamp"].astimezone(colombia_tz)
            with st.expander(f"💡 {idea['title']}  —  {fecha_local.strftime('%Y-%m-%d %H:%M')}"):
                st.write(idea["description"])

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
    except Exception as e:
        st.error(f"❌ Error al listar ideas: {e}")


# ==============================
# CRONÓMETRO GLOBAL
# ==============================
st.subheader("⏱️ Cronómetro Global")

# Inicializar estado
if "cronometro_activo" not in st.session_state:
    st.session_state.cronometro_activo = False
if "cronometro_inicio" not in st.session_state:
    st.session_state.cronometro_inicio = None
if "cronometro_tiempo" not in st.session_state:
    st.session_state.cronometro_tiempo = timedelta(0)

# Mostrar tiempo transcurrido
if st.session_state.cronometro_activo and st.session_state.cronometro_inicio:
    st.session_state.cronometro_tiempo = datetime.now(pytz.UTC) - st.session_state.cronometro_inicio

tiempo_str = str(st.session_state.cronometro_tiempo).split(".")[0]
st.metric("Tiempo transcurrido", tiempo_str)

# Botón único
if not st.session_state.cronometro_activo:
    if st.button("▶️ Iniciar"):
        st.session_state.cronometro_activo = True
        st.session_state.cronometro_inicio = datetime.now(pytz.UTC)
        st.rerun()
else:
    if st.button("⏹️ Parar"):
        st.session_state.cronometro_activo = False
        tiempo_total = datetime.now(pytz.UTC) - st.session_state.cronometro_inicio

        # Guardar en Mongo
        try:
            collection_desarrollo.insert_one({
                "inicio": st.session_state.cronometro_inicio,
                "fin": datetime.now(pytz.UTC),
                "duracion": tiempo_total
            })
            st.success(f"✅ Cronómetro guardado: {tiempo_total}")
        except Exception as e:
            st.error(f"❌ Error al guardar en desarrollo: {e}")

# Auto-refresh cada segundo si está activo
if st.session_state.cronometro_activo:
    st.experimental_autorefresh(interval=1000, key="cronometro_refresh")


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
