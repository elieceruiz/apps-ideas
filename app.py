# app.py
import streamlit as st
import pytz
from pymongo import MongoClient
from datetime import datetime, timedelta
from dateutil.parser import parse
import pandas as pd

# ==============================
# CONFIG
# ==============================
st.set_page_config(page_title="💡 Apps Ideas", page_icon="💡", layout="centered")

mongodb_uri = st.secrets["mongodb"]["uri"]
mongodb_db = st.secrets["mongodb"]["db"]
mongodb_collection = st.secrets["mongodb"]["collection"]
mongodb_collection_desarrollo = st.secrets["mongodb"]["collection_desarrollo"]

client = MongoClient(mongodb_uri)
db = client[mongodb_db]
collection = db[mongodb_collection]
dev_collection = db[mongodb_collection_desarrollo]

colombia_tz = pytz.timezone("America/Bogota")

st.title("💡 Apps Ideas")

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
        "timestamp": datetime.now(pytz.UTC),
        "done": False,
        "done_at": None
    }
    collection.update_one(
        {"_id": idea_id},
        {"$push": {"updates": nueva_actualizacion}}
    )
    st.success("📝 Nota agregada a la idea")
    return True

def to_datetime_local(dt):
    if not isinstance(dt, datetime):
        dt = parse(str(dt))
    return dt.astimezone(colombia_tz)

# ==============================
# UI Tabs
# ==============================
tab_guardadas, tab_ideas, tab_desarrollo = st.tabs(
    ["📂 Guardadas", "💡 Ideas", "💻 Desarrollo"]
)

with tab_guardadas:
    ideas = list(collection.find().sort("timestamp", -1))
    st.subheader(f"📌 {len(ideas)} guardadas")
    for idea in ideas:
        fecha_local = idea["timestamp"].astimezone(colombia_tz)
        with st.expander(f"💡 {idea['title']}  —  {fecha_local.strftime('%Y-%m-%d %H:%M')}"):
            st.write(idea["description"])
            if "updates" in idea and len(idea["updates"]) > 0:
                st.markdown("**Trazabilidad / Notas adicionales:**")
                for idx, note in enumerate(idea["updates"]):
                    fecha_nota_local = note["timestamp"].astimezone(colombia_tz)
                    if not note.get("done", False):
                        col_text, col_btn = st.columns([0.85, 0.15])
                        with col_text:
                            st.markdown(f"➡️ {note['text']}  ⏰ {fecha_nota_local.strftime('%Y-%m-%d %H:%M')}")
                        with col_btn:
                            if st.button("Listo!!!", key=f"btn_listo_{idea['_id']}_{idx}"):
                                done_at = datetime.now(pytz.UTC)
                                collection.update_one(
                                    {"_id": idea["_id"]},
                                    {"$set": {
                                        f"updates.{idx}.done": True,
                                        f"updates.{idx}.done_at": done_at
                                    }}
                                )
                                st.success("✅ Nota marcada como acción ejecutada")
                                st.rerun()
                    else:
                        done_at = note.get("done_at")
                        done_local = done_at.astimezone(colombia_tz) if done_at else None
                        duracion = ""
                        if done_at:
                            delta = done_at - note["timestamp"]
                            horas, resto = divmod(delta.total_seconds(), 3600)
                            minutos, segundos = divmod(resto, 60)
                            duracion = f"⏱️ {int(horas)}h {int(minutos)}m {int(segundos)}s"
                        st.markdown(
                            f"✔️ ~~{note['text']}~~  \n "
                            f"⏰ {fecha_nota_local.strftime('%Y-%m-%d %H:%M')} → "
                            f"{done_local.strftime('%Y-%m-%d %H:%M') if done_local else ''}  \n "
                            f"{duracion}"
                        )
                    st.divider()
            with st.form(f"form_update_{idea['_id']}", clear_on_submit=True):
                nueva_nota = st.text_area("Agregar nota", key=f"nota_{idea['_id']}")
                enviar_nota = st.form_submit_button("Guardar nota")
                if enviar_nota:
                    agregar_nota(idea["_id"], nueva_nota)
                    st.rerun()

with tab_ideas:
    with st.form("form_agregar_idea", clear_on_submit=True):
        titulo_idea = st.text_input("Título de la idea")
        descripcion_idea = st.text_area("Descripción de la idea")
        envio = st.form_submit_button("Guardar idea")
        if envio:
            guardar_idea(titulo_idea, descripcion_idea)
            st.rerun()

with tab_desarrollo:
    evento = dev_collection.find_one({"tipo": "dev_app", "en_curso": True})

    if evento:
        hora_inicio = to_datetime_local(evento["inicio"])

        # Guardar en session_state inicio real para mantener constante y evitar salto
        if "inicio_dev" not in st.session_state:
            st.session_state.inicio_dev = hora_inicio

        # Usar st_autorefresh para actualizar cada segundo
        refresco = st.experimental_memo(lambda: None, ttl=1)
        refresco()

        # Calcular duración desde inicio en session_state
        duracion = datetime.now(colombia_tz) - st.session_state.inicio_dev
        duracion_str = str(duracion).split('.')[0]

        st.success(f"🟢 Desarrollo en curso desde las {st.session_state.inicio_dev.strftime('%H:%M:%S')}")
        st.markdown(f"### ⏱️ Duración: {duracion_str}")

        if st.button("⏹️ Finalizar desarrollo"):
            dev_collection.update_one(
                {"_id": evento["_id"]},
                {"$set": {"fin": datetime.now(colombia_tz), "en_curso": False}}
            )
            # Limpiar la sesión
            del st.session_state.inicio_dev
            st.rerun()
    else:
        # Limpiar la session_state si no hay evento en curso
        if "inicio_dev" in st.session_state:
            del st.session_state.inicio_dev

        st.info("No hay desarrollo en curso.")
        if st.button("🟢 Iniciar desarrollo"):
            dev_collection.insert_one({
                "tipo": "dev_app",
                "inicio": datetime.now(colombia_tz),
                "en_curso": True
            })
            st.rerun()

    eventos_cursor = dev_collection.find().sort("inicio", -1)
    eventos = list(eventos_cursor)

    if len(eventos) == 0:
        st.info("No hay datos para mostrar.")
    else:
        ahora = datetime.now(colombia_tz)
        data = []
        for ev in eventos:
            inicio_local = ev["inicio"].astimezone(colombia_tz) if "inicio" in ev else None
            fin_local = ev.get("fin", None)
            if fin_local is not None:
                fin_local = fin_local.astimezone(colombia_tz)
            tiempo_final = fin_local if fin_local else ahora
            duracion_timedelta = tiempo_final - inicio_local if inicio_local else timedelta(0)
            duracion_str = str(duracion_timedelta).split('.')[0]
            data.append({
                "Inicio": inicio_local.strftime("%Y-%m-%d %H:%M:%S") if inicio_local else "",
                "Fin": fin_local.strftime("%Y-%m-%d %H:%M:%S") if fin_local else "",
                "Duración": duracion_str,
            })
        df = pd.DataFrame(data)
        # Agrega la numeración al final de la tabla
        df.insert(len(df.columns), "#", range(1, len(df) + 1))
        cols = [c for c in df.columns if c != "#"] + ["#"]
        df = df[cols]
        st.dataframe(df, use_container_width=True)
