# --- КАРТОЧКА ВЕЩИ ---
                with st.container(border=True):
                    # Заголовок с тремя точками
                    col_title, col_dots = st.columns([6, 1])
                    with col_title:
                        st.markdown(f"**{status_emoji} {name}**")
                        if category:
                            st.caption(f"📂 {category}")
                    with col_dots:
                        if st.button("⋮", key=f"menu_{item_id}", help="Меню"):
                            st.session_state[f"menu_{item_id}"] = not st.session_state.get(f"menu_{item_id}", False)
                    
                    # Основная информация
                    st.caption(f"🏠 {room} → 📍 {location}")
                    if eq_name:
                        st.caption(f"🚜 **Техника:** {eq_name}")
                    if unit_name:
                        st.caption(f"🔧 **Агрегат:** {unit_name}")
                    if application:
                        st.caption(f"📝 **Область применения:** {application}")
                    st.caption(f"📦 Количество: **{qty} {unit}**")
                    st.caption(f"📊 Статус: **{status_text}**")
                    
                    # Фото
                    c1, c2, c3 = st.columns(3)
                    with c1:
                        if item_photo and os.path.exists(item_photo):
                            st.image(item_photo, caption="Вещь", use_container_width=True)
                        else:
                            st.image("https://via.placeholder.com/150/cccccc/969696?text=Нет+фото", use_container_width=True)
                    with c2:
                        if location_photo and os.path.exists(location_photo):
                            st.image(location_photo, caption="Место", use_container_width=True)
                        else:
                            st.image("https://via.placeholder.com/150/cccccc/969696?text=Нет+фото", use_container_width=True)
                    with c3:
                        if installed_photo and os.path.exists(installed_photo):
                            st.image(installed_photo, caption="Установка", use_container_width=True)
                        else:
                            st.image("https://via.placeholder.com/150/cccccc/969696?text=Нет+фото", use_container_width=True)
                    
                    if description:
                        st.write(f"📝 {description}")
                    st.caption(f"🕒 Добавлено: {date_added}")
                    
                    # --- МЕНЮ (появляется при нажатии на ⋮) ---
                    if st.session_state.get(f"menu_{item_id}", False):
                        with st.container(border=True):
                            st.write("**📋 Действия:**")
                            col1, col2, col3 = st.columns(3)
                            with col1:
                                if st.button("✏️ Редактировать", key=f"edit_{item_id}", use_container_width=True):
                                    st.session_state[f"edit_mode_{item_id}"] = True
                                    st.session_state[f"menu_{item_id}"] = False
                                    st.rerun()
                                if st.button("📷 Фото", key=f"photo_{item_id}", use_container_width=True):
                                    st.session_state[f"photo_mode_{item_id}"] = True
                                    st.session_state[f"menu_{item_id}"] = False
                                    st.rerun()
                            with col2:
                                if st.button("📤 Списать", key=f"cons_{item_id}", use_container_width=True):
                                    st.session_state[f"cons_mode_{item_id}"] = True
                                    st.session_state[f"menu_{item_id}"] = False
                                    st.rerun()
                                if st.button("📷 QR", key=f"qr_{item_id}", use_container_width=True):
                                    st.session_state[f"qr_mode_{item_id}"] = True
                                    st.session_state[f"menu_{item_id}"] = False
                                    st.rerun()
                            with col3:
                                if st.button("🚚 Переместить", key=f"move_{item_id}", use_container_width=True):
                                    st.session_state[f"move_mode_{item_id}"] = True
                                    st.session_state[f"menu_{item_id}"] = False
                                    st.rerun()
                                if st.button("🗑️ Удалить", key=f"del_{item_id}", use_container_width=True):
                                    delete_item(item_id)
                                    st.rerun()
                    
                    # --- РЕДАКТИРОВАНИЕ ---
                    if st.session_state.get(f"edit_mode_{item_id}", False):
                        with st.container(border=True):
                            st.write(f"**✏️ Редактирование {name}**")
                            new_name = st.text_input("Название", value=name, key=f"new_name_{item_id}")
                            new_category = st.text_input("Категория", value=category or "", key=f"new_cat_{item_id}")
                            new_description = st.text_area("Описание", value=description or "", key=f"new_desc_{item_id}")
                            new_application = st.text_area("Область применения", value=application or "", key=f"new_app_{item_id}")
                            room_names = get_room_names()
                            new_room = st.selectbox("Помещение", room_names, index=room_names.index(room) if room in room_names else 0, key=f"new_room_{item_id}")
                            equipment_list = get_equipment()
                            eq_names = ["Не выбрано"] + [eq[1] for eq in equipment_list]
                            current_eq = eq_names[0]
                            if equipment_id:
                                eq = get_equipment_by_id(equipment_id)
                                if eq:
                                    current_eq = eq[1]
                            new_eq = st.selectbox("Техника", eq_names, index=eq_names.index(current_eq) if current_eq in eq_names else 0, key=f"new_eq_{item_id}")
                            new_eq_id = None
                            if new_eq != "Не выбрано":
                                for eq in equipment_list:
                                    if eq[1] == new_eq:
                                        new_eq_id = eq[0]; break
                            unit_names = ["Не выбрано"]
                            if new_eq_id:
                                units = get_units(new_eq_id)
                                unit_names += [u[1] for u in units]
                            current_unit = unit_names[0]
                            if unit_id:
                                units = get_units(equipment_id)
                                for u in units:
                                    if u[0] == unit_id:
                                        current_unit = u[1]; break
                            new_unit = st.selectbox("Агрегат", unit_names, index=unit_names.index(current_unit) if current_unit in unit_names else 0, key=f"new_unit_{item_id}")
                            new_unit_id = None
                            if new_unit != "Не выбрано" and new_eq_id:
                                units = get_units(new_eq_id)
                                for u in units:
                                    if u[1] == new_unit:
                                        new_unit_id = u[0]; break
                            col1, col2 = st.columns(2)
                            with col1:
                                if st.button("✅ Сохранить", key=f"save_edit_{item_id}"):
                                    update_item(item_id, new_name, new_category, location, new_room, new_description, new_application, new_eq_id, new_unit_id)
                                    st.session_state[f"edit_mode_{item_id}"] = False
                                    st.success("✅ Изменения сохранены!")
                                    st.rerun()
                            with col2:
                                if st.button("❌ Отмена", key=f"cancel_edit_{item_id}"):
                                    st.session_state[f"edit_mode_{item_id}"] = False
                                    st.rerun()
                    
                    # --- ИЗМЕНЕНИЕ ФОТО ---
                    if st.session_state.get(f"photo_mode_{item_id}", False):
                        with st.container(border=True):
                            st.write(f"**📷 Изменение фото для {name}**")
                            new_item_pic = st.file_uploader("📷 Фото вещи", type=["jpg", "jpeg", "png"], key=f"new_item_{item_id}")
                            new_location_pic = st.file_uploader("📷 Фото места", type=["jpg", "jpeg", "png"], key=f"new_loc_{item_id}")
                            new_installed_pic = st.file_uploader("📷 Фото установки", type=["jpg", "jpeg", "png"], key=f"new_inst_{item_id}")
                            col1, col2 = st.columns(2)
                            with col1:
                                if st.button("✅ Сохранить фото", key=f"save_photo_{item_id}"):
                                    item_path = item_photo or ""; loc_path = location_photo or ""; installed_path = installed_photo or ""
                                    if new_item_pic:
                                        ext = new_item_pic.name.split('.')[-1]
                                        if item_path and os.path.exists(item_path):
                                            os.remove(item_path)
                                        item_path = f"images/{uuid.uuid4()}_item.{ext}"
                                        with open(item_path, "wb") as f: f.write(new_item_pic.getbuffer())
                                    if new_location_pic:
                                        ext = new_location_pic.name.split('.')[-1]
                                        if loc_path and os.path.exists(loc_path):
                                            os.remove(loc_path)
                                        loc_path = f"images/{uuid.uuid4()}_loc.{ext}"
                                        with open(loc_path, "wb") as f: f.write(new_location_pic.getbuffer())
                                    if new_installed_pic:
                                        ext = new_installed_pic.name.split('.')[-1]
                                        if installed_path and os.path.exists(installed_path):
                                            os.remove(installed_path)
                                        installed_path = f"images/{uuid.uuid4()}_installed.{ext}"
                                        with open(installed_path, "wb") as f: f.write(new_installed_pic.getbuffer())
                                    update_item_photos(item_id, item_path, loc_path, installed_path)
                                    st.session_state[f"photo_mode_{item_id}"] = False
                                    st.success("✅ Фото обновлены!")
                                    st.rerun()
                            with col2:
                                if st.button("❌ Отмена", key=f"cancel_photo_{item_id}"):
                                    st.session_state[f"photo_mode_{item_id}"] = False
                                    st.rerun()
                    
                    # --- СПИСАНИЕ ---
                    if st.session_state.get(f"cons_mode_{item_id}", False):
                        with st.container(border=True):
                            st.write(f"**📤 Списание {name}**")
                            st.caption(f"Доступно: {qty} {unit}")
                            col1, col2 = st.columns(2)
                            with col1:
                                consume_qty = st.number_input("Количество", min_value=0.0, step=0.5, max_value=float(qty), value=min(1.0, float(qty)), key=f"cons_qty_{item_id}")
                            with col2:
                                equipment_list = get_equipment()
                                search_options = ["Другое"]
                                for eq in equipment_list:
                                    eq_name = eq[1] + (f" ({eq[2]})" if eq[2] else "")
                                    search_options.append(eq_name)
                                    units = get_units(eq[0])
                                    for unit in units:
                                        search_options.append(f"{eq_name} → {unit[1]}")
                                search_equipment = st.text_input("🔍 Поиск техники или агрегата", placeholder="Начните вводить...", key=f"search_eq_{item_id}")
                                filtered_eq = [opt for opt in search_options if search_equipment.lower() in opt.lower()] if search_equipment else search_options
                                if filtered_eq:
                                    selected_eq = st.selectbox("Выберите объект", filtered_eq, key=f"sel_eq_{item_id}")
                                    object_name = st.text_input("Введите название объекта*", key=f"custom_obj_{item_id}") if selected_eq == "Другое" else selected_eq
                                else:
                                    st.warning("Ничего не найдено")
                                    object_name = st.text_input("Введите название объекта*", key=f"custom_obj_{item_id}")
                            user = st.text_input("Кто списывает", value="Пользователь", key=f"cons_user_{item_id}")
                            note = st.text_area("Примечание", key=f"cons_note_{item_id}")
                            col1, col2 = st.columns(2)
                            with col1:
                                if st.button("✅ Списать", key=f"save_cons_{item_id}"):
                                    if consume_qty <= 0:
                                        st.error("Количество > 0")
                                    elif not object_name:
                                        st.error("Укажите объект")
                                    else:
                                        success, message = consume_item(item_id, consume_qty, object_name, user, note)
                                        if success:
                                            st.success(message)
                                            st.session_state[f"cons_mode_{item_id}"] = False
                                            st.rerun()
                                        else:
                                            st.error(message)
                            with col2:
                                if st.button("❌ Отмена", key=f"cancel_cons_{item_id}"):
                                    st.session_state[f"cons_mode_{item_id}"] = False
                                    st.rerun()
                    
                    # --- ПЕРЕМЕЩЕНИЕ ---
                    if st.session_state.get(f"move_mode_{item_id}", False):
                        with st.container(border=True):
                            st.write(f"**🚚 Перемещение {name}**")
                            st.caption(f"Текущее: **{room}**")
                            room_names = get_room_names()
                            available_rooms = [r for r in room_names if r != room]
                            if available_rooms:
                                new_room = st.selectbox("Новое помещение", available_rooms, key=f"new_room_move_{item_id}")
                                col1, col2 = st.columns(2)
                                with col1:
                                    if st.button("✅ Переместить", key=f"save_move_{item_id}"):
                                        update_item_room(item_id, new_room)
                                        st.session_state[f"move_mode_{item_id}"] = False
                                        st.success(f"✅ Перемещено в '{new_room}'")
                                        st.rerun()
                                with col2:
                                    if st.button("❌ Отмена", key=f"cancel_move_{item_id}"):
                                        st.session_state[f"move_mode_{item_id}"] = False
                                        st.rerun()
                            else:
                                st.warning("Нет доступных помещений")
                                if st.button("❌ Закрыть", key=f"close_move_{item_id}"):
                                    st.session_state[f"move_mode_{item_id}"] = False
                                    st.rerun()
                    
                    # --- QR-КОД ---
                    if st.session_state.get(f"qr_mode_{item_id}", False):
                        with st.container(border=True):
                            st.write(f"**📷 QR-код для {name}**")
                            app_url = "https://garage-app-2-fcfztptpvqdfqmrh3vczif.streamlit.app"
                            qr_data = f"{app_url}?search={item_id}"
                            qr = qrcode.make(qr_data)
                            buf = BytesIO()
                            qr.save(buf, format="PNG")
                            st.image(buf, caption=f"QR для {name}", use_container_width=True)
                            st.download_button(label="⬇️ Скачать QR", data=buf.getvalue(), file_name=f"qr_{name}_{item_id}.png", mime="image/png")
                            if st.button("❌ Закрыть QR", key=f"close_qr_{item_id}"):
                                st.session_state[f"qr_mode_{item_id}"] = False
                                st.rerun()
