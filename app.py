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
def traducir_session_state(state: dict):
    """Convierte el session_state en frases legibles."""
    traducciones = []
    for k, v in state.items():
        if k.startswith("FormSubmitter:form_agregar_idea"):
            traducciones.append(f"📝 Botón 'Guardar idea': {'presionado' if v else 'no presionado'}")
        elif k.startswith("FormSubmitter:form_update_"):
            idea_id = k.split("_")[-1].split("-")[0]
            traducciones.append(f"📝 Botón 'Guardar nota' (idea {idea_id}): {'presionado' if v else 'no presionado'}")
        elif k.startswith("nota_"):
            idea_id = k.replace("nota_", "")
            if v.strip() == "":
                traducciones.append(f"🗒️ Campo de nota (idea {idea_id}): vacío")
            else:
                traducciones.append(f"🗒️ Campo de nota (idea {idea_id}): con texto → '{v}'")
        elif k == "titulo_idea":
            traducciones.append(f"💡 Campo título: '{v}'" if v else "💡 Campo título vacío")
        elif k == "descripcion_idea":
            traducciones.append(f"📄 Campo descripción: '{v}'" if v else "📄 Campo descripción vacío")
        else:
            traducciones.append(f"🔧 {k}: {v}")
    return traducciones


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
                    st.markdown(f"➡️ {note['text']}  \n ⏰ {note['timestamp'].strftime('%Y-%m-%d %H:%M')}")
                st.divider()

            # Formulario para agregar nueva nota
            nota_key = f"nota_{idea['_id']}"
            with st.form(f"form_update_{idea['_id']}"):
                nueva_nota = st.text_area("Agregar nota", key=nota_key, value="")
                enviar_nota = st.form_submit_button("Guardar nota")

                if enviar_nota:
                    exito = agregar_nota(idea["_id"], nueva_nota)
                    if exito:
                        try:
                            st.session_state[nota_key] = ""
                            st.rerun()
                        except Exception as e:
                            st.warning(f"⚠️ No se pudo limpiar la nota: {e}")
                            st.write("🔍 Estado actual:", dict(st.session_state))
                            st.markdown("### 🗣️ Traducción del estado")
                            for linea in traducir_session_state(st.session_state):
                                st.write(linea)

# ==============================
# UI PRINCIPAL
# ==============================
with st.form("form_agregar_idea"):
    titulo_idea = st.text_input("Título de la idea", key="titulo_idea", value="")
    descripcion_idea = st.text_area("Descripción de la idea", key="descripcion_idea", value="")
    envio = st.form_submit_button("Guardar idea")

    if envio:
        exito = guardar_idea(titulo_idea, descripcion_idea)
        if exito:
            try:
                st.session_state["titulo_idea"] = ""
                st.session_state["descripcion_idea"] = ""
                st.rerun()
            except Exception as e:
                st.warning(f"⚠️ No se pudieron limpiar los campos: {e}")
                st.write("🔍 Estado actual:", dict(st.session_state))
                st.markdown("### 🗣️ Traducción del estado")
                for linea in traducir_session_state(st.session_state):
                    st.write(linea)

listar_ideas()
