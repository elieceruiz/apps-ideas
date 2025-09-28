# app.py
import streamlit as st
import pytz
import time
from pymongo import MongoClient
from datetime import datetime, timedelta
from dateutil.parser import parse
import pandas as pd

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
dev_collection = db[mongodb_collection_desarrollo]

# Zona horaria Colombia
colombia_tz = pytz.timezone("America/Bogota")

st.title("💡 Apps Ideas")

# ==============================
# FUNCIONES IDEAS
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

# ==============================
# FUNCIONES DESARROLLO
# ==============================
def to_datetime_local(dt):
    if not isinstance(dt, datetime):
        dt = parse(str(dt))
    return dt.astimezone(colombia_tz)

def cronometro_desarrollo():
    st.subheader("⏳ Tiempo invertido en el desarrollo de la App")

    evento = dev_collection.find_one({"tipo": "dev_app", "en_curso": True})

    if evento:
        hora_inicio = to_datetime_local(evento["inicio"])
        segundos_transcurridos = int((datetime.now(colombia_tz) - hora_inicio).total_seconds())
        st.success(f"🟢 Desarrollo en curso desde las {hora_inicio.strftime('%H:%M:%S')}")
        cronometro = st.empty()
        stop_button = st.button("⏹️ Finalizar desarrollo", key="stop_dev")

        for i in range(segundos_transcurridos, segundos_transcurridos + 100000):
            if stop_button:
                dev_collection.update_one(
                    {"_id": evento["_id"]},
                    {"$set": {"fin": datetime.now(colombia_tz), "en_curso": False}}
                )
                st.success("✅ Registro finalizado.")
                st.rerun()

            duracion = str(timedelta(seconds=i))
            cronometro.markdown(f"### ⏱️ Duración: {duracion}")
            time.sleep(1)
    else:
        if st.button("🟢 Iniciar desarrollo", key="start_dev"):
            dev_collection.insert_one({
                "tipo": "dev_app",
                "inicio": datetime.now(colombia_tz),
                "en_curso": True
            })
            st.rerun()

# ==============================
# UI PRINCIPAL
# ==============================
tab_guardadas, tab_ideas, tab_desarrollo, tab_historial = st.tabs(
    ["📂 Guardadas", "💡 Ideas", "💻 Desarrollo", "📊 Historial Desarrollo"]
)

with tab_guardadas:
    ideas = list(collection.find().sort("timestamp", -1))
    st.subheader(f"📌 {len(ideas)} guardadas")

    for idea in ideas:
        fecha_local = idea["timestamp"].astimezone(colombia_tz)

        # --- Progreso de notas ---
        updates = idea.get("updates", [])
        total = len(updates)
        hechas = sum(1 for note in updates if note.get("done", False))
        progreso = f" ({hechas}/{total})" if total > 0 else ""

        # --- Encabezado del expander ---
        with st.expander(f"💡 {idea['title']} {progreso} ⏰ {fecha_local.strftime('%Y-%m-%d %H:%M')}"):
            st.write(idea["description"])

            # Formulario para nueva nota (antes de la lista de trazabilidad)
            with st.form(f"form_update_{idea['_id']}", clear_on_submit=True):
                nueva_nota = st.text_area("Agregar nota", key=f"nota_{idea['_id']}")
                enviar_nota = st.form_submit_button("Guardar nota")
                if enviar_nota:
                    agregar_nota(idea["_id"], nueva_nota)
                    st.rerun()

            # Notas ya registradas
            if total > 0:
                st.markdown("**Trazabilidad / Notas adicionales:**")
                for idx, note in enumerate(updates):
                    fecha_nota_local = note["timestamp"].astimezone(colombia_tz)

                    if not note.get("done", False):
                        col_text, col_btn = st.columns([0.9, 0.1])
                        with col_text:
                            st.markdown(f"➡️ {note['text']}  ⏰ {fecha_nota_local.strftime('%Y-%m-%d %H:%M')}")
                        with col_btn:
                            if st.button("✅ Listo!!!", key=f"done_{idea['_id']}_{idx}"):
                                done_at = datetime.now(pytz.UTC)
                                collection.update_one(
                                    {"_id": idea["_id"]},
                                    {"$set": {
                                        f"updates.{idx}.done": True,
                                        f"updates.{idx}.done_at": done_at
                                    }}
                                )
                                st.rerun()
                    else:
                        done_at = note.get("done_at")
                        done_local = done_at.astimezone(colombia_tz) if done_at else None
                        delta = (done_at - note["timestamp"]) if done_at else None
                        duracion = ""
                        if delta:
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

with tab_ideas:
    with st.form("form_agregar_idea", clear_on_submit=True):
        titulo_idea = st.text_input("Título de la idea")
        descripcion_idea = st.text_area("Descripción de la idea")
        envio = st.form_submit_button("Guardar idea")
        if envio:
            guardar_idea(titulo_idea, descripcion_idea)
            st.rerun()

with tab_desarrollo:
    cronometro_desarrollo()

with tab_historial:
    st.subheader("📊 Historial de sesiones de desarrollo")

    sesiones = list(dev_collection.find({"tipo": "dev_app"}).sort("inicio", -1))

    if not sesiones:
        st.info("No hay registros de desarrollo aún.")
    else:
        filas = []
        total = len(sesiones)
        for idx, sesion in enumerate(sesiones, start=1):
            numero = total - idx + 1  # Numeración descendente

            inicio_local = to_datetime_local(sesion["inicio"])
            fin_local = to_datetime_local(sesion["fin"]) if sesion.get("fin") else None

            if fin_local:
                duracion = fin_local - inicio_local
                estado = "Finalizado"
            else:
                duracion = datetime.now(colombia_tz) - inicio_local
                estado = "En curso"

            horas, resto = divmod(int(duracion.total_seconds()), 3600)
            minutos, segundos = divmod(resto, 60)
            duracion_str = f"{horas:02d}:{minutos:02d}:{segundos:02d}"

            filas.append({
                "#": numero,
                "Inicio": inicio_local.strftime("%Y-%m-%d %H:%M"),
                "Fin": fin_local.strftime("%Y-%m-%d %H:%M") if fin_local else "—",
                "Duración": duracion_str,
                "Estado": estado
            })

        df = pd.DataFrame(filas)
        df = df.sort_values("#", ascending=False).reset_index(drop=True)
        st.dataframe(df, use_container_width=True, hide_index=True)
# app.py
import streamlit as st
import pytz
import time
from pymongo import MongoClient
from datetime import datetime, timedelta
from dateutil.parser import parse
import pandas as pd

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
dev_collection = db[mongodb_collection_desarrollo]

# Zona horaria Colombia
colombia_tz = pytz.timezone("America/Bogota")

st.title("💡 Apps Ideas")

# ==============================
# FUNCIONES IDEAS
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

# ==============================
# FUNCIONES DESARROLLO
# ==============================
def to_datetime_local(dt):
    if not isinstance(dt, datetime):
        dt = parse(str(dt))
    return dt.astimezone(colombia_tz)

def cronometro_desarrollo():
    st.subheader("⏳ Tiempo invertido en el desarrollo de la App")

    evento = dev_collection.find_one({"tipo": "dev_app", "en_curso": True})

    if evento:
        hora_inicio = to_datetime_local(evento["inicio"])
        segundos_transcurridos = int((datetime.now(colombia_tz) - hora_inicio).total_seconds())
        st.success(f"🟢 Desarrollo en curso desde las {hora_inicio.strftime('%H:%M:%S')}")
        cronometro = st.empty()
        stop_button = st.button("⏹️ Finalizar desarrollo", key="stop_dev")

        for i in range(segundos_transcurridos, segundos_transcurridos + 100000):
            if stop_button:
                dev_collection.update_one(
                    {"_id": evento["_id"]},
                    {"$set": {"fin": datetime.now(colombia_tz), "en_curso": False}}
                )
                st.success("✅ Registro finalizado.")
                st.rerun()

            duracion = str(timedelta(seconds=i))
            cronometro.markdown(f"### ⏱️ Duración: {duracion}")
            time.sleep(1)
    else:
        if st.button("🟢 Iniciar desarrollo", key="start_dev"):
            dev_collection.insert_one({
                "tipo": "dev_app",
                "inicio": datetime.now(colombia_tz),
                "en_curso": True
            })
            st.rerun()

# ==============================
# UI PRINCIPAL
# ==============================
tab_guardadas, tab_ideas, tab_desarrollo, tab_historial = st.tabs(
    ["📂 Guardadas", "💡 Ideas", "💻 Desarrollo", "📊 Historial Desarrollo"]
)

with tab_guardadas:
    ideas = list(collection.find().sort("timestamp", -1))  # Obtener ideas primero
    st.subheader(f"📌 {len(ideas)} guardadas")              # Mostrar contador antes

    for idea in ideas:
        fecha_local = idea["timestamp"].astimezone(colombia_tz)
        with st.expander(f"💡 {idea['title']}  —  {fecha_local.strftime('%Y-%m-%d %H:%M')}"):
            st.write(idea["description"])

            # 👉 Agregar nota PRIMERO
            with st.form(f"form_update_{idea['_id']}", clear_on_submit=True):
                nueva_nota = st.text_area("Agregar nota", key=f"nota_{idea['_id']}")
                enviar_nota = st.form_submit_button("Guardar nota")
                if enviar_nota:
                    agregar_nota(idea["_id"], nueva_nota)
                    st.rerun()

            # 👉 Luego mostrar trazabilidad
            if "updates" in idea and len(idea["updates"]) > 0:
                st.markdown("**Trazabilidad / Notas adicionales:**")

                for idx, note in enumerate(idea["updates"]):
                    fecha_nota_local = note["timestamp"].astimezone(colombia_tz)

                    if not note.get("done", False):
                        col_text, col_btn = st.columns([0.85, 0.15])
                        with col_text:
                            st.markdown(f"➡️ {note['text']}  ⏰ {fecha_nota_local.strftime('%Y-%m-%d %H:%M')}")
                        with col_btn:
                            if st.button("Listo!!!", key=f"btn_{idea['_id']}_{idx}"):
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

with tab_ideas:
    with st.form("form_agregar_idea", clear_on_submit=True):
        titulo_idea = st.text_input("Título de la idea")
        descripcion_idea = st.text_area("Descripción de la idea")
        envio = st.form_submit_button("Guardar idea")
        if envio:
            guardar_idea(titulo_idea, descripcion_idea)
            st.rerun()

with tab_desarrollo:
    cronometro_desarrollo()

with tab_historial:
    st.subheader("📊 Historial de sesiones de desarrollo")

    sesiones = list(dev_collection.find({"tipo": "dev_app"}).sort("inicio", -1))

    if not sesiones:
        st.info("No hay registros de desarrollo aún.")
    else:
        filas = []
        total = len(sesiones)
        for idx, sesion in enumerate(sesiones, start=1):
            numero = total - idx + 1  # Numeración descendente

            inicio_local = to_datetime_local(sesion["inicio"])
            fin_local = to_datetime_local(sesion["fin"]) if sesion.get("fin") else None

            if fin_local:
                duracion = fin_local - inicio_local
                estado = "Finalizado"
            else:
                duracion = datetime.now(colombia_tz) - inicio_local
                estado = "En curso"

            horas, resto = divmod(int(duracion.total_seconds()), 3600)
            minutos, segundos = divmod(resto, 60)
            duracion_str = f"{horas:02d}:{minutos:02d}:{segundos:02d}"

            filas.append({
                "#": numero,
                "Inicio": inicio_local.strftime("%Y-%m-%d %H:%M"),
                "Fin": fin_local.strftime("%Y-%m-%d %H:%M") if fin_local else "—",
                "Duración": duracion_str,
                "Estado": estado
            })

        df = pd.DataFrame(filas)
        df = df.sort_values("#", ascending=False).reset_index(drop=True)
        st.dataframe(df, use_container_width=True, hide_index=True)
