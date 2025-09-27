# app.py
import streamlit as st
import pytz
from pymongo import MongoClient
from datetime import datetime

# ==============================
# CONFIG
# ==============================
st.set_page_config(page_title="💡 Registro de Ideas", page_icon="💡", layout="centered")

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

st.title("💡 Registro de Ideas de Aplicaciones")

# ==============================
# FORMULARIO NUEVA IDEA
# ==============================
with st.form("form_agregar_idea"):
    titulo_idea = st.text_input("Título de la idea")
    descripcion_idea = st.text_area("Descripción de la idea")
    envio = st.form_submit_button("Guardar idea")

    if envio:
        if titulo_idea.strip() == "" or descripcion_idea.strip() == "":
            st.error("Complete todos los campos por favor")
        else:
            nueva_idea = {
                "title": titulo_idea.strip(),
                "description": descripcion_idea.strip(),
                "timestamp": datetime.now(colombia_tz),
                "updates": []  # historial de trazabilidad
            }
            collection.insert_one(nueva_idea)
            st.success("✅ Idea guardada correctamente")

# ==============================
# LISTAR IDEAS
# ==============================
st.subheader("📌 Ideas guardadas")

ideas = collection.find().sort("timestamp", -1)

for idea in ideas:
    with st.expander(f"💡 {idea['title']}  —  {idea['timestamp'].strftime('%Y-%m-%d %H:%M')}"):
        st.write(idea["description"])

        # Mostrar historial de actualizaciones si existen
        if "updates" in idea and len(idea["updates"]) > 0:
            st.markdown("**Trazabilidad / Notas adicionales:**")
            for note in idea["updates"]:
                st.markdown(f"➡️ {note['text']}  \n ⏰ {note['timestamp'].strftime('%Y-%m-%d %H:%M')}")
            st.divider()

        # Formulario para agregar nueva nota a la idea
        with st.form(f"form_update_{idea['_id']}"):
            nueva_nota = st.text_area("Agregar nota", key=f"nota_{idea['_id']}")
            enviar_nota = st.form_submit_button("Guardar nota")

            if enviar_nota:
                if nueva_nota.strip() == "":
                    st.error("La nota no puede estar vacía")
                else:
                    nueva_actualizacion = {
                        "text": nueva_nota.strip(),
                        "timestamp": datetime.now(colombia_tz)
                    }
                    collection.update_one(
                        {"_id": idea["_id"]},
                        {"$push": {"updates": nueva_actualizacion}}
                    )
                    st.success("📝 Nota agregada a la idea")
                    st.rerun()
