# app.py
import streamlit as st
import pytz
from pymongo import MongoClient
from datetime import datetime

# Leer configuración MongoDB de Secrets
mongodb_uri = st.secrets["mongodb"]["uri"]
mongodb_db = st.secrets["mongodb"]["db"]
mongodb_collection = st.secrets["mongodb"]["collection"]

# Conexión a MongoDB
client = MongoClient(mongodb_uri)
db = client[mongodb_db]
collection = db[mongodb_collection]

# Zona horaria Colombia
colombia_tz = pytz.timezone('America/Bogota')

st.title("Registro de Ideas de Aplicaciones")

# Formulario para ingresar nueva idea
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
                "timestamp": datetime.now(colombia_tz)
            }
            collection.insert_one(nueva_idea)
            st.success("Idea guardada correctamente")

# Mostrar ideas guardadas ordenadas por fecha descendente
st.subheader("Ideas guardadas")
ideas = collection.find().sort("timestamp", -1)
for idea in ideas:
    st.markdown(f"**{idea['title']}** - _{idea['timestamp'].strftime('%Y-%m-%d %H:%M:%S %Z')}_")
    st.markdown(idea['description'])
    st.markdown("---")
