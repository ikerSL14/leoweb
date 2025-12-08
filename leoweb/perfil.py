import reflex as rx
from .auth_state import AuthState, get_connection
from .sidebar import sidebar, sidebar_button
from .ui_state import UIState
from passlib.hash import pbkdf2_sha256
from datetime import datetime, date
from typing import List, Dict, Any

Reservation = Dict[str, Any]
HomeEvent = Dict[str, Any]
EventDetail = Dict[str, List[Dict[str, Any]]]

# Definición de la estructura de un ítem de menú (ejemplo)
class MenuItem(rx.Base):
    cantidad: int
    costo_unitario: float
    nombre_producto: str
    
    # 🚨 NUEVO CAMPO: Agrega el costo total ya formateado como string
    costo_formateado_str: str 
    
    # Agrega el total para referencia
    subtotal: float

# En la función que carga o calcula la lista de eventos/detalles
def format_menu_item(item: dict) -> MenuItem:
    cantidad = item.get("cantidad", 0)
    costo_unitario = item.get("costo_unitario", 0.0)
    
    subtotal = cantidad * costo_unitario
    
    # 🚨 Formateo de Python: Usamos el f-string nativo de Python
    # para asegurar que el string tenga 2 decimales.
    costo_str = f"${subtotal:.2f}"
    
    return MenuItem(
        cantidad=cantidad,
        costo_unitario=costo_unitario,
        nombre_producto=item.get("nombre_producto", ""),
        subtotal=subtotal,
        costo_formateado_str=costo_str # <-- String listo para usar
    )

# Si tu estado tiene una lista de dicts (ejemplo)
# self.lista_menu_items = [format_menu_item(d) for d in data_desde_backend]

# ------------------------------------------------------------
# STATE DEL PERFIL
# ------------------------------------------------------------
class ProfileState(rx.State):
    nombre: str = ""
    correo: str = ""
    telefono: str = ""
    contrasena_actual: str = ""
    nueva_contrasena: str = ""
    confirmar_contrasena: str = ""

    edit_mode: bool = False

    show_reservations_modal: bool = False # 👈 Variable para abrir/cerrar modal
    user_reservations: List[Reservation] = [] # 👈 Lista de reservaciones

    show_home_events_modal: bool = False # 👈 Variable para abrir/cerrar modal de eventos
    user_home_events: List[HomeEvent] = [] # 👈 Lista de eventos
    # {id_evento: [{"nombre_producto": "...", "cantidad": X, "costo_unitario": Y}]}
    event_details: EventDetail = {} # 👈 Diccionario para guardar el detalle del menú (desplegable)

    # --------------------------------------------------------
    # ---- TOGGLE MODAL EVENTOS A DOMICILIO ----
    @rx.event
    async def toggle_home_events_modal(self, is_open: bool):
        """Abre y cierra el modal de eventos a domicilio y carga los datos."""
        self.show_home_events_modal = is_open
        
        # Cargar datos al abrir
        if is_open:
            auth_state = await self.get_state(AuthState)
            current_user_id = auth_state.current_user
            # Limpiamos los detalles al abrir
            self.event_details = {} 
            # Es importante usar `yield` ya que `load_home_events_data` puede devolver un Toast
            yield self.load_home_events_data(current_user_id)

    # ---- CARGAR DATOS DE EVENTOS A DOMICILIO ----
    def load_home_events_data(self, current_user_id: int):
        """Carga los eventos a domicilio activos y pasados del usuario."""
        conn = None
        if current_user_id is None:
            return rx.toast.error("Error: No se detecta el usuario.")
            
        try:
            conn = get_connection()
            cur = conn.cursor()
            
            cur.execute("""
                SELECT 
                    id_evento, 
                    fecha, 
                    hora, 
                    ubicacion, 
                    cant_personas, 
                    costo 
                FROM eventos
                WHERE id_usuario = %s
                ORDER BY fecha DESC, hora DESC;
            """, (current_user_id,))
            
            rows = cur.fetchall()
            events = []
            now = datetime.now()
            
            for row in rows:
                id_evento, res_date, res_time, ubicacion, cant_personas, costo = row
                
                reservation_dt = datetime.combine(res_date, res_time)
                is_past = reservation_dt < now
                
                formatted_date = res_date.strftime("%d/%m/%Y")
                formatted_time = res_time.strftime("%I:%M %p") 
                
                events.append({
                    "id_evento": id_evento,
                    "fecha": formatted_date,
                    "hora": formatted_time,
                    "ubicacion": ubicacion,
                    "cant_personas": cant_personas,
                    "costo": costo,
                    "es_pasado": is_past
                })
            
            self.user_home_events = events
            
        except Exception as e:
            print(f"Error cargando eventos a domicilio: {e}")
            return rx.toast.error(f"Error al cargar eventos: {str(e)}")
            
        finally:
            if conn:
                conn.close()

    # ---- TOGGLE DETALLE DEL EVENTO (Menú) ----
    def toggle_event_details(self, id_evento: int):
        """Abre/cierra el detalle del menú para un evento, cargando los datos si es necesario."""
        str_id = str(id_evento) # Las claves del diccionario son strings en Reflex
        
        # 1. Si el detalle ya está cargado (la clave existe), simplemente lo eliminamos (cerrar)
        if str_id in self.event_details:
            del self.event_details[str_id]
            return

        # 2. Si no está cargado, lo cargamos (abrir)
        conn = None
        try:
            conn = get_connection()
            cur = conn.cursor()
            
            # Consultamos los productos ligados a este evento, con sus detalles de 'menu'
            cur.execute("""
                SELECT 
                    m.nombre, 
                    me.cantidad, 
                    m.precio
                FROM menu_evento me
                JOIN menu m ON me.id_producto = m.id_producto
                WHERE me.id_evento = %s;
            """, (id_evento,))
            
            rows = cur.fetchall()
            menu_items = []
            
            for row in rows:
                nombre, cantidad, precio = row
                menu_items.append({
                    "nombre_producto": nombre,
                    "cantidad": cantidad,
                    "costo_unitario": precio
                })
            
            # Almacenar en el diccionario de detalles. La clave es el id_evento como string.
            self.event_details[str_id] = menu_items
            
        except Exception as e:
            print(f"Error cargando detalles del evento {id_evento}: {e}")
            return rx.toast.error(f"Error al cargar menú: {str(e)}")
            
        finally:
            if conn:
                conn.close()

    # ---- ELIMINAR EVENTO A DOMICILIO ----
    def delete_home_event(self, id_evento: int):
        """Elimina un evento a domicilio pendiente y sus ítems de menú relacionados."""
        conn = None
        try:
            conn = get_connection()
            cur = conn.cursor()
            
            # 1. Comprobar que el evento no haya pasado.
            cur.execute("SELECT fecha, hora FROM eventos WHERE id_evento = %s;", (id_evento,))
            row = cur.fetchone()
            
            if row:
                res_date, res_time = row
                reservation_dt = datetime.combine(res_date, res_time)
                
                if reservation_dt < datetime.now():
                    return rx.toast.error("No se puede eliminar un evento que ya ha pasado.")

                # 2. Eliminar los ítems de menu_evento (CASCADE: esto podría ser manejado por la DB)
                cur.execute("DELETE FROM menu_evento WHERE id_evento = %s;", (id_evento,))

                # 3. Eliminar el evento
                cur.execute("DELETE FROM eventos WHERE id_evento = %s;", (id_evento,))
                conn.commit()
                
                # 4. Actualizar la lista de eventos en el estado
                self.user_home_events = [
                    event for event in self.user_home_events 
                    if event["id_evento"] != id_evento
                ]

                # 5. Eliminar el detalle de los eventos
                str_id = str(id_evento)
                if str_id in self.event_details:
                    del self.event_details[str_id]
                
                return rx.toast.success("Evento a domicilio eliminado correctamente. 🗑️")
            else:
                return rx.toast.error("Evento no encontrado.")

        except Exception as e:
            if conn:
                conn.rollback()
            print(f"Error eliminando evento: {e}")
            return rx.toast.error(f"Error al eliminar evento: {str(e)}")
        finally:
            if conn:
                conn.close()

    # ---- TOGGLE MODAL RESERVACIONES ----
    async def toggle_reservations_modal(self):
        """Abre y cierra el modal de reservaciones."""
        self.show_reservations_modal = not self.show_reservations_modal
        
        # Al abrir, si la lista está vacía, cargarla.
        # Al cerrar, no pasa nada, los datos persisten hasta que se recargue la página/vuelva a abrir el modal.
        if self.show_reservations_modal:
            auth_state = await self.get_state(AuthState)
            current_user_id = auth_state.current_user
            
            # Llama a load_reservations_data con el ID, y usa yield para devolver
            # el resultado del toast o la actualización de estado.
            # Convertimos load_reservations_data en una función normal que recibe el ID
            yield self.load_reservations_data(current_user_id) # 👈 PASA EL ID

    # ---- CARGAR DATOS DE RESERVACIONES ----
    def load_reservations_data(self, current_user_id: int):
        """Carga las reservaciones activas y pasadas del usuario."""
        conn = None
        
        if current_user_id is None:
            # Esto no debería pasar si la página se cargó correctamente, pero es un buen guardrail
            return rx.toast.error("Error: No se detecta el usuario.")
            
        try:
            conn = get_connection()
            cur = conn.cursor()
            
            # NOTA: Asumimos que tienes una tabla 'sucursales' con 'id_sucursal' y 'nombre'
            cur.execute("""
                SELECT 
                    r.id_reserva, 
                    r.cant_personas, 
                    r.fecha, 
                    r.hora, 
                    r.tipo_evento,
                    s.nombre as sucursal_nombre
                FROM reserva r
                JOIN sucursales s ON r.id_sucursal = s.id_sucursal
                WHERE r.id_usuario = %s
                ORDER BY r.fecha DESC, r.hora DESC;
            """, (current_user_id,))
            
            rows = cur.fetchall()
            reservations = []
            now = datetime.now()
            
            for row in rows:
                id_reserva, cant_personas, res_date, res_time, tipo_evento, sucursal = row
                
                # Combinar fecha y hora para una comparación correcta
                reservation_dt = datetime.combine(res_date, res_time)
                
                # Determinar si la reservación ya pasó
                is_past = reservation_dt < now
                
                # Formatear la hora y fecha para la UI
                formatted_date = res_date.strftime("%d/%m/%Y")
                # %I:%M %p es formato 12 horas con AM/PM (ej: 07:00 PM)
                formatted_time = res_time.strftime("%I:%M %p") 
                
                reservations.append({
                    "id_reserva": id_reserva,
                    "cant_personas": cant_personas,
                    "fecha": formatted_date,
                    "hora": formatted_time,
                    "tipo_evento": tipo_evento,
                    "sucursal": sucursal,
                    "es_pasada": is_past
                })
            
            self.user_reservations = reservations
            
        except Exception as e:
            print(f"Error cargando reservaciones: {e}")
            return rx.toast.error(f"Error al cargar reservaciones: {str(e)}")
            
        finally:
            if conn:
                conn.close()

    # ---- ELIMINAR RESERVACIÓN ----
    def delete_reservation(self, id_reserva: int):
        """Elimina una reservación pendiente."""
        conn = None
        try:
            conn = get_connection()
            cur = conn.cursor()
            
            # 1. Comprobar que la reserva no haya pasado. 
            # (Lo hacemos en el frontend deshabilitando el botón, pero el backend debe confirmar)
            cur.execute("SELECT fecha, hora FROM reserva WHERE id_reserva = %s;", (id_reserva,))
            row = cur.fetchone()
            
            if row:
                res_date, res_time = row
                reservation_dt = datetime.combine(res_date, res_time)
                
                if reservation_dt < datetime.now():
                    return rx.toast.error("No se puede eliminar una reservación que ya ha pasado.")

                # 2. Eliminar la reservación
                cur.execute("DELETE FROM reserva WHERE id_reserva = %s;", (id_reserva,))
                conn.commit()
                
                # 3. Actualizar la lista de reservaciones en el estado
                self.user_reservations = [
                    res for res in self.user_reservations 
                    if res["id_reserva"] != id_reserva
                ]
                
                return rx.toast.success("Reservación eliminada correctamente. 🗑️")
            else:
                return rx.toast.error("Reservación no encontrada.")

        except Exception as e:
            if conn:
                conn.rollback()
            print(f"Error eliminando reservación: {e}")
            return rx.toast.error(f"Error al eliminar reservación: {str(e)}")
        finally:
            if conn:
                conn.close()

    # ---- SETTERS ----
    def set_nombre(self, value: str):
        self.nombre = value

    def set_correo(self, value: str):
        self.correo = value

    def set_telefono(self, value: str):
        self.telefono = value

    def set_contra_actual(self, value: str):
        self.contrasena_actual = value

    def set_contra_nueva(self, value: str):
        self.nueva_contrasena = value

    def set_contra_confirm(self, value: str):
        self.confirmar_contrasena = value

    # --------------------------------------------------------
    # CARGAR DATOS DEL USUARIO DESDE LA DB
    # --------------------------------------------------------
    def load_user_data(self, user_id: int):
        conn = None
        try:
            conn = get_connection()
            cur = conn.cursor()
            cur.execute("""
                SELECT nombre, correo, telefono
                FROM usuarios
                WHERE id_usuario = %s;
            """, (user_id,))
            row = cur.fetchone()
            if row:
                self.nombre, self.correo, self.telefono = row
        except Exception as e:
            print("Error cargando datos de usuario:", e)
        finally:
            if conn:
                conn.close()

    # --------------------------------------------------------
    # ON LOAD
    # --------------------------------------------------------
    async def on_load(self):
        # 🟢 CÓDIGO CORREGIDO: Esperar el objeto de estado y luego acceder al atributo
        auth_state = await self.get_state(AuthState)
        user_id = auth_state.current_user # <-- ACCEDER AQUÍ
        
        # Redirigir si no está logeado (el valor es None)
        if user_id is None:
            return rx.redirect("/login")
        
        # Cargar los datos del usuario logeado
        self.load_user_data(user_id)

    # --------------------------------------------------------
    # TOGGLE MODO EDICIÓN
    # --------------------------------------------------------
    def toggle_edit(self):
        self.edit_mode = not self.edit_mode
        # Opcional: limpiar campos de contraseña al salir de edición
        if not self.edit_mode:
            self.contrasena_actual = ""
            self.nueva_contrasena = ""
            self.confirmar_contrasena = ""

    # --------------------------------------------------------
    # GUARDAR CAMBIOS
    # --------------------------------------------------------
    async def save_profile(self):
        # 🟢 CÓDIGO CORREGIDO: Esperar el objeto de estado y luego acceder al atributo
        auth_state = await self.get_state(AuthState)
        user = auth_state.current_user # <-- ACCEDER AQUÍ
        
        if user is None:
            return rx.toast.error("Debes iniciar sesión.")

        conn = None 
        try:
            conn = get_connection()
            cur = conn.cursor()
            
            # --- Lógica de Cambio de Contraseña ---
            if self.nueva_contrasena or self.confirmar_contrasena:
                if self.nueva_contrasena != self.confirmar_contrasena:
                    return rx.toast.error("Las contraseñas no coinciden.")

                if not self.contrasena_actual:
                    return rx.toast.error("Debes escribir tu contraseña actual.")

                # 1. Verificar Contraseña Actual
                cur.execute("SELECT contrasena FROM usuarios WHERE id_usuario = %s;", (user,))
                row = cur.fetchone()

                if not row or not pbkdf2_sha256.verify(self.contrasena_actual, row[0]):
                    return rx.toast.error("Tu contraseña actual es incorrecta.")

                # 2. Hashear Nueva Contraseña
                hashed_password = pbkdf2_sha256.hash(self.nueva_contrasena)

                # 3. Actualizar datos Y contraseña
                cur.execute("""
                    UPDATE usuarios 
                    SET nombre = %s, correo = %s, telefono = %s, contrasena = %s
                    WHERE id_usuario = %s;
                """, (self.nombre, self.correo, self.telefono, hashed_password, user))

            else:
                # --- Lógica de Solo Actualizar Datos ---
                # Si los campos de contraseña están vacíos, solo actualiza nombre, correo, teléfono
                cur.execute("""
                    UPDATE usuarios 
                    SET nombre = %s, correo = %s, telefono = %s
                    WHERE id_usuario = %s;
                """, (self.nombre, self.correo, self.telefono, user))

            conn.commit()

        except Exception as e:
            # Importante hacer rollback si algo falla
            if conn:
                conn.rollback()
            print("Error actualizando perfil:", e)
            return rx.toast.error(f"Error al actualizar perfil: {str(e)}")

        finally:
            if conn:
                conn.close()

        # Resetear edición y campos de contraseña
        self.edit_mode = False
        self.contrasena_actual = ""
        self.nueva_contrasena = ""
        self.confirmar_contrasena = ""

        return rx.toast.success("Perfil actualizado correctamente. 👍")
    
# Puedes definir esta función en el mismo archivo (perfil.py) o en otro si organizas componentes

def reservation_row(reservation: Reservation):
    """Muestra una sola fila de reservación con la opción de eliminar."""
    
    # 1. Determinar si el botón de eliminar debe estar desactivado
    is_disabled = reservation["es_pasada"]
    
    return rx.hstack(
        # INFORMACIÓN (Fecha, Hora, Personas, Tipo, Sucursal)
        rx.box(
            rx.text(
                f"{reservation['fecha']} a las {reservation['hora']}",
                font_weight="bold",
                color=rx.cond(is_disabled, "#888888", "white"), # Gris si es pasada
            ),
            rx.text(
                f"{reservation['tipo_evento']} en {reservation['sucursal']} | {reservation['cant_personas']} personas",
                font_size="sm",
                color=rx.cond(is_disabled, "#aaaaaa", "#e0e0e0"),
            ),
            width="100%",
        ),
        
        # BOTÓN DE ELIMINAR (A la derecha)
        rx.button(
            rx.icon(tag="trash"),
            on_click=ProfileState.delete_reservation(reservation["id_reserva"]),
            is_disabled=is_disabled, # Desactivar si ya pasó
            color_scheme=rx.cond(is_disabled, "gray", "red"), # Color diferente si está desactivado
            cursor=rx.cond(is_disabled, "default", "pointer"),
            margin_left="auto",
        ),
        
        width="100%",
        align_items="center",
        padding="15px 10px",
        border_bottom="1px solid rgba(255, 255, 255, 0.1)",
        _hover={
            "background": rx.cond(is_disabled, "none", "rgba(255,255,255,0.05)")
        },
    )

# Agrega esta función en perfil.py (o donde tengas los componentes de la UI)

def reservations_modal():
    """Modal para mostrar y gestionar las reservaciones del usuario."""
    return rx.dialog.root(
        rx.dialog.content(
            rx.vstack(

                # HEADER
                rx.hstack(
                    rx.dialog.title(
                        rx.heading("Mis Reservaciones", size="6", color="white")
                    ),
                    # Botón de cierre (Radix lo incluye por defecto, pero podemos agregarlo explícitamente si queremos)
                    rx.dialog.close(
                        rx.icon(
                            tag="x", 
                            color="white", 
                            size=20, 
                            cursor="pointer",
                            _hover={"color": "#ff0000"}
                        )
                    ),
                    width="100%",
                    justify="between",
                    align="center",
                    margin_bottom="20px",
                ),

                # LISTA DE RESERVACIONES
                rx.cond(
                    # 1. Si hay reservaciones, muéstralas
                    ProfileState.user_reservations.length() > 0,
                    rx.vstack(
                        rx.foreach(
                            ProfileState.user_reservations,
                            lambda res: reservation_row(res), # Usamos la función de fila definida arriba
                        ),
                        width="100%",
                        max_height="400px", # Para que sea scrollable
                        overflow_y="auto",
                    ),
                    # 2. Si no hay reservaciones, muestra un mensaje
                    rx.center(
                        rx.text(
                            "Aún no tienes reservaciones. ¡Es hora de planear una!", 
                            color="#aaaaaa",
                            padding="20px"
                        ),
                        width="100%",
                    )
                ),

            ),
            background="#1a1a1c",
            border_radius="15px",
            width="650px",
            padding="30px",
        ),

        open=ProfileState.show_reservations_modal,
        on_open_change=ProfileState.toggle_reservations_modal,
    )

# 🟢 FUNCIÓN PARA MOSTRAR LOS DETALLES DEL MENÚ (CORRECCIÓN DEFINITIVA V2)
def menu_detail_row(item: Dict[str, Any]):
    """Muestra una sola fila de producto del menú para el detalle del evento."""
    
    # 1. Extracción y forzado de tipos (esto está BIEN y debe mantenerse)
    cantidad_var = item["cantidad"].to(int)
    nombre_var = item["nombre_producto"]
    
    costo_formateado = item["costo_formateado_str"]
    
    
    return rx.hstack(
        rx.text(
            # 🚨 INYECCIÓN DIRECTA: Concatenar visualmente dentro del componente
            ["x", cantidad_var.to(str), " - ", nombre_var],
            color="#e0e0e0",
            font_size="sm",
            font_weight="500",
        ),
        rx.text(
            costo_formateado, # Usamos la variable concatenada
            color="#ff0000",
            font_weight="bold",
            font_size="sm",
            margin_left="auto",
        ),
        width="100%",
        padding_y="5px",
    )


# 🟢 NUEVA FUNCIÓN PARA MOSTRAR UNA FILA DE EVENTO A DOMICILIO
def home_event_row(event: HomeEvent):
    """Muestra una sola fila de evento a domicilio con la opción de desplegar/eliminar."""
    is_disabled = event["es_pasada"]
    event_id_str = event["id_evento"].to(str)
    # Verificar si los detalles están abiertos/cargados en el estado
    is_open = ProfileState.event_details.get(event_id_str, False)
    
    return rx.vstack( # Usamos vstack para la fila principal y el detalle desplegable
        rx.hstack(
            # INFORMACIÓN (Fecha, Hora, Ubicación, Personas, Costo)
            rx.box(
                rx.text(
                    f"{event['fecha']} a las {event['hora']} | {event['ubicacion']}",
                    font_weight="bold",
                    color=rx.cond(is_disabled, "#888888", "white"),
                ),
                rx.text(
                    f"{event['cant_personas']} personas | Total: ${event['costo']:.2f}",
                    font_size="sm",
                    color=rx.cond(is_disabled, "#aaaaaa", "#e0e0e0"),
                ),
                width="100%",
            ),
            
            # BOTONES DE ACCIÓN (Desplegar y Eliminar)
            rx.hstack(
                # BOTÓN DE DESPLEGAR
                rx.button(
                    rx.icon(tag=rx.cond(is_open, "x", "chevron-down")),
                    on_click=ProfileState.toggle_event_details(event["id_evento"]),
                    color_scheme=rx.cond(is_open, "red", "gray"), # Rojo si está abierto
                    variant="soft",
                    margin_right="10px",
                ),
                # BOTÓN DE ELIMINAR
                rx.button(
                    rx.icon(tag="trash"),
                    on_click=ProfileState.delete_home_event(event["id_evento"]),
                    is_disabled=is_disabled,
                    color_scheme=rx.cond(is_disabled, "gray", "red"),
                    cursor=rx.cond(is_disabled, "default", "pointer"),
                ),
                margin_left="auto",
            ),
            
            width="100%",
            align_items="center",
            padding_x="10px",
        ),
        
        # CONTENIDO DESPLEGABLE (DETALLE DEL MENÚ)
        rx.cond(
            is_open,
            rx.vstack(
                rx.divider(margin_y="10px"),
                rx.text("Detalle del Menú:", font_weight="bold", color="white", margin_bottom="5px"),
                
                # Renderizar la lista de productos
                rx.foreach(
                    ProfileState.event_details[event_id_str],
                    lambda item: menu_detail_row(item),
                ),
                
                width="95%", # Un poco más estrecho para el detalle
                align_items="flex-start",
                padding="0 20px 10px 20px",
            ),
        ),
        
        width="100%",
        align_items="center",
        padding_y="15px",
        border_bottom="1px solid rgba(255, 255, 255, 0.1)",
        _hover={
            "background": rx.cond(is_disabled, "none", "rgba(255,255,255,0.05)")
        },
    )


# 🟢 NUEVA FUNCIÓN: MODAL DE EVENTOS A DOMICILIO
def home_events_modal():
    """Modal para mostrar y gestionar los eventos a domicilio del usuario."""
    # Usamos ProfileState.user_home_events.length() para checar si está vacía
    has_events = ProfileState.user_home_events.length() > 0
    
    return rx.dialog.root(
        rx.dialog.content(
            rx.vstack(
                # HEADER
                rx.hstack(
                    rx.dialog.title(
                        rx.heading("Mis Eventos a Domicilio", size="6", color="white")
                    ),
                    rx.dialog.close(
                        rx.icon(
                            tag="x", 
                            color="white", 
                            size=20, 
                            cursor="pointer",
                            on_click=ProfileState.toggle_home_events_modal(False),
                            _hover={"color": "#ff0000"}
                        )
                    ),
                    width="100%",
                    justify="between",
                    align="center",
                    margin_bottom="20px",
                ),

                # LISTA DE EVENTOS
                rx.cond(
                    # 1. Si hay eventos, muéstralos
                    has_events,
                    rx.vstack(
                        rx.foreach(
                            ProfileState.user_home_events,
                            lambda event: home_event_row(event),
                        ),
                        width="100%",
                        max_height="400px",
                        overflow_y="auto",
                    ),
                    # 2. Si no hay eventos, muestra un mensaje
                    rx.center(
                        rx.text(
                            "Aún no tienes eventos a domicilio programados. ¡Pide el tuyo!", 
                            color="#aaaaaa",
                            padding="20px"
                        ),
                        width="100%",
                    )
                ),
            ),
            background="#1a1a1c",
            border_radius="15px",
            width="750px", # Un poco más ancho para dar espacio al detalle
            padding="30px",
        ),
        # Conexión al estado del modal
        open=ProfileState.show_home_events_modal,
        on_open_change=ProfileState.toggle_home_events_modal,
    )

# ----------------------------------------------------------------------
# COMPONENTE DE CONTENEDOR DE PERFIL
# ----------------------------------------------------------------------
def profile_card():
    return rx.box(
        rx.hstack(

            # INFORMACIÓN + CAMPOS
            rx.box(
                # ICONO EDITAR
                rx.icon(
                    # 🟢 CAMBIO DE ÍCONO: pencil (inactivo) o x (activo)
                    tag=rx.cond(ProfileState.edit_mode, "x", "pencil"), 
                    
                    # 🟢 CAMBIO DE COLOR: Rojo (activo) o Blanco (inactivo)
                    color=rx.cond(ProfileState.edit_mode, "#ff0000", "white"),
                    
                    # 🟢 CAMBIO DE HOVER: Rojo oscuro (activo) o Rojo claro (inactivo)
                    _hover={
                        "color": rx.cond(ProfileState.edit_mode, "#b00000", "#ff0000")
                    },
                    transition="all 0.3s ease-in-out",
                    cursor="pointer",
                    float="right",
                    on_click=ProfileState.toggle_edit,
                ),

                # NOMBRE
                rx.text("Nombre", color="white", margin_top="10px"),
                rx.input(
                    value=ProfileState.nombre,
                    on_change=ProfileState.set_nombre,
                    disabled=~ProfileState.edit_mode,
                    width="100%",
                    background="rgba(255,255,255,0.08)",
                    color="white",
                    border_radius="10px",
                    size="3",
                    padding="10px",
                ),

                # CORREO
                rx.text("Correo", color="white", margin_top="15px"),
                rx.input(
                    value=ProfileState.correo,
                    on_change=ProfileState.set_correo,
                    disabled=~ProfileState.edit_mode,
                    width="100%",
                    background="rgba(255,255,255,0.08)",
                    color="white",
                    size="3",
                    border_radius="10px",
                    padding="10px",
                ),

                # TELÉFONO
                rx.text("Teléfono", color="white", margin_top="15px"),
                rx.input(
                    value=ProfileState.telefono,
                    on_change=ProfileState.set_telefono,
                    disabled=~ProfileState.edit_mode,
                    width="100%",
                    background="rgba(255,255,255,0.08)",
                    color="white",
                    size="3",
                    border_radius="10px",
                    padding="10px",
                ),

                # SEPARADOR
                rx.divider(margin_y="25px"),

                rx.text("Cambiar contraseña", color="white", margin_bottom="10px"),

                # CONTRASEÑA ACTUAL
                rx.input(
                    placeholder="Contraseña actual",
                    type="password",
                    value=ProfileState.contrasena_actual,
                    on_change=ProfileState.set_contra_actual,
                    disabled=~ProfileState.edit_mode,
                    width="100%",
                    size="3",
                    background="rgba(255,255,255,0.08)",
                    color="white",
                    border_radius="10px",
                    padding="10px",
                ),

                # NUEVA + CONFIRMAR
                rx.hstack(
                    rx.input(
                        placeholder="Nueva contraseña",
                        type="password",
                        value=ProfileState.nueva_contrasena,
                        on_change=ProfileState.set_contra_nueva,
                        disabled=~ProfileState.edit_mode,
                        width="100%",
                        size="3",
                        background="rgba(255,255,255,0.08)",
                        color="white",
                        border_radius="10px",
                        padding="10px",
                    ),
                    rx.input(
                        placeholder="Confirmar contraseña",
                        type="password",
                        value=ProfileState.confirmar_contrasena,
                        on_change=ProfileState.set_contra_confirm,
                        disabled=~ProfileState.edit_mode,
                        width="100%",
                        size="3",
                        background="rgba(255,255,255,0.08)",
                        color="white",
                        border_radius="10px",
                        padding="10px",
                    ),
                    spacing="4",
                    margin_top="15px",
                ),

                # BOTONES INFERIORES
                rx.hstack(
                    # 1. BOTÓN GUARDAR (visible/invisible con layout fijo)
                    rx.button(
                        "Guardar",
                        on_click=ProfileState.save_profile,
                        background_color="#ff0000",
                        _hover={"background_color": "#b00000"},
                        cursor=rx.cond(ProfileState.edit_mode, "pointer", "default"), 
                        width="150px",
                        
                        # Mantiene el espacio ocupado, solo oculta el contenido
                        opacity=rx.cond(ProfileState.edit_mode, "1", "0"),
                        visibility=rx.cond(ProfileState.edit_mode, "visible", "hidden"),
                        transition="opacity 0.3s ease", 
                    ), # 👈 ¡Paréntesis de cierre del botón!

                    # 2. Íconos de Navegación (TOOLTIPS CORREGIDOS)
                    # 2. Íconos de Navegación (SOLUCIÓN FINAL DE TOOLTIPS)
                    rx.hstack(
                        # ÍCONO 1: RESERVACIONES
                        # 🟢 Usamos la sintaxis limpia de Radix, que espera solo el label y la configuración.
                        rx.tooltip(
                            rx.icon(
                                tag="calendar-check",
                                color="white",
                                size=24,
                                cursor="pointer",
                                _hover={"color": "#ff0000"},
                                transition="color 0.3s ease",
                                on_click=ProfileState.toggle_reservations_modal,
                            ),
                            # El label debe ser una cadena de texto (str) o un Var, no un componente
                            content="Mis reservaciones", 
                            color_scheme="red",
                        ),
                        
                        # ÍCONO 2: EVENTOS A DOMICILIO
                        rx.tooltip(
                            rx.icon(
                                tag="utensils",
                                color="white",
                                size=24,
                                cursor="pointer",
                                _hover={"color": "#ff0000"},
                                transition="color 0.3s ease",
                                margin_left="15px",
                                on_click=ProfileState.toggle_home_events_modal(True),
                            ),
                            content="Mis eventos a domicilio", 
                            color_scheme="red",
                        ),
                    ),
                    
                    width="100%",
                    justify="between", 
                    margin_top="25px",
                ),

                width="100%",
            ),

            align_items="flex-start",
            width="100%",
            padding="30px",
            background="rgba(0,0,0,0.40)",
            border_radius="20px",
            backdrop_filter="blur(10px)",
            border="1px solid rgba(255,255,255,0.15)",
        ),
        width="800px",
        margin_top="10px",
    )


# ----------------------------------------------------------------------
# PÁGINA DE PERFIL (con sidebar)
# ----------------------------------------------------------------------
@rx.page(route="/perfil", on_load=ProfileState.on_load)
def perfil_page():
    # forzar registro de condicionales que usamos en la UI (Mantener esta línea)
    _ = ProfileState.edit_mode 
    _ = ProfileState.event_details
    return rx.box(
        sidebar(active_item="perfil"),
        sidebar_button(),

        rx.center(
            profile_card(),
            width="100%",
            min_height="100vh",
        ),
        reservations_modal(),
        home_events_modal(),
        width="100%",
        min_height="100vh",
        background=(
            "linear-gradient(rgba(0,0,0,0.6), rgba(0,0,0,0.6)), "
            "url('https://images.unsplash.com/photo-1484659619207-9165d119dafe?q=80&w=870&auto=format&fit=crop&ixlib=rb-4.1.0&ixid=M3wxMjA3fDB8MHxwaG90by1wYWdlfHx8fGVufDB8fHx8fA%3D%3D')"
        ),
        background_size="cover",
        background_position="center",
        padding_left=rx.cond(UIState.sidebar_open, "260px", "0px"),
        transition="padding-left 0.3s ease",
    )