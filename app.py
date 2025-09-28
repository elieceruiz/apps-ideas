# app.py
with tab_guardadas:
    ideas = list(collection.find().sort("timestamp", -1))
    st.markdown(f"📌 {len(ideas)} guardadas")
    
    # Funcionalidad para listar ideas pero sin contar/mostrar texto
    for idea in ideas:
        fecha_local = idea["timestamp"].astimezone(colombia_tz)
        with st.expander(f"💡 {idea['title']}  —  {fecha_local.strftime('%Y-%m-%d %H:%M')}"):
            st.write(idea["description"])
            # Aquí va el código para notas que ya tienes en listar_ideas
            # Copia y adapta el código para notas pendientes y completadas aquí
            if "updates" in idea and len(idea["updates"]) > 0:
                st.markdown("**Trazabilidad / Notas adicionales:**")

                for idx, note in enumerate(idea["updates"]):
                    fecha_nota_local = note["timestamp"].astimezone(colombia_tz)

                    if not note.get("done", False):
                        col1, col2 = st.columns([0.1, 0.9])
                        with col1:
                            checked = st.checkbox("", key=f"chk_{idea['_id']}_{idx}", value=False)
                        with col2:
                            st.markdown(
                                f"➡️ {note['text']}  \n ⏰ {fecha_nota_local.strftime('%Y-%m-%d %H:%M')}"
                            )
                        if checked:
                            done_at = datetime.now(pytz.UTC)
                            collection.update_one(
                                {"_id": idea["_id"]},
                                {"$set": {
                                    f"updates.{idx}.done": True,
                                    f"updates.{idx}.done_at": done_at
                                }}
                            )
                            st.success("✅ Nota marcada como acción ejecutada")
                            st.experimental_rerun()

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
            # Form para agregar nota
            with st.form(f"form_update_{idea['_id']}", clear_on_submit=True):
                nueva_nota = st.text_area("Agregar nota", key=f"nota_{idea['_id']}")
                enviar_nota = st.form_submit_button("Guardar nota")
                if enviar_nota:
                    agregar_nota(idea["_id"], nueva_nota)
                    st.experimental_rerun()
