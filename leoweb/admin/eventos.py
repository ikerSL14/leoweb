import reflex as rx
from .adminsidebar import admin_sidebar, admin_sidebar_button
from typing import Dict, Any, List, Tuple, TypedDict, Optional
from .aui_state import AUIState
from datetime import datetime, timedelta # Importar para manejo de fechas
from collections import defaultdict # Importar para agrupar eventos
from ..auth_state import AuthState, get_connection # Asumo esta importación

# Traducción manual de días y meses (para replicar reservaciones.py)
DIAS_ES = {
    "Monday": "Lunes", "Tuesday": "Martes", "Wednesday": "Miércoles", 
    "Thursday": "Jueves", "Friday": "Viernes", "Saturday": "Sábado", 
    "Sunday": "Domingo",
}

MESES_ES = {
    "January": "Enero", "February": "Febrero", "March": "Marzo", 
    "April": "Abril", "May": "Mayo", "June": "Junio", "July": "Julio", 
    "August": "Agosto", "September": "Septiembre", "October": "Octubre", 
    "November": "Noviembre", "December": "Diciembre",
}
# Define los tipos para que Reflex entienda la estructura
# Tipo para un solo evento

# 1. Tipo para cada ítem dentro del menú del evento
class MenuItem(TypedDict):
    nombre: str
    cantidad: int # O str, dependiendo de cómo lo devuelva tu backend

# 2. Tipo para un solo evento, que ahora incluye una lista de MenuItems
class FullEvent(TypedDict): # Ya no es solo Dict[str, Any]
    id_evento: int
    nombre_usuario: str
    descripcion: str
    fecha_evento_str: str
    total: float # O str, si lo manejas como string formateado
    menu_items: List[MenuItem] # <--- DEFINICIÓN EXPLÍCITA
    # Puedes añadir aquí cualquier otra clave que uses: 'fecha_dt', etc.
    es_pasado: bool
    # 💡 AÑADIR NUEVOS CAMPOS 💡
    cant_personas: int
    user_email: Optional[str] # Asumimos que email puede ser nulo
    user_phone: Optional[str] # Asumimos que teléfono puede ser nulo

class GroupedEventItem(TypedDict):
    header: str
    eventos: List[FullEvent]

# Tipo para la variable computada final
# El formato de filtered_events es: List[Tuple[str, GroupedEventItem]]
FinalFilteredList = List[Tuple[str, GroupedEventItem]]

# =========================================================
# ===============  STATE DE EVENTOS COMPLETO  =============
# =========================================================
class AdminEventoState(rx.State):
    search_query: str = ""
    menu_open_id: Optional[int] = None
    all_events: List[FullEvent] = [] # Lista maestra sin filtrar

    # Diccionario agrupado: { "2025-01-01": {header:"...", eventos:[...] } }
    grouped_events: Dict[str, GroupedEventItem] = {} # Usar el tipo definido

    # --------------------------------------------------
    # CICLO DE VIDA Y VALIDACIÓN
    # --------------------------------------------------

    async def on_load(self):
        """Validación de admin y carga inicial de datos."""
        auth_state = await self.get_state(AuthState)
        
        # 1. Redireccionar si no está logueado
        if not auth_state.logged_in:
            return rx.redirect("/login")
        
        # 2. Redireccionar si no es admin
        if auth_state.rol != "admin":
            return [
                rx.toast.error("Acceso denegado. Se requiere ser administrador."),
                rx.redirect("/") 
            ]
        
        # 3. Cargar datos
        return self.load_all_events()


    def set_search(self, value: str):
        self.search_query = value
        self.group_events_by_date() # Recalculamos la vista agrupada al buscar

    def toggle_menu(self, id_evento: int):
        self.menu_open_id = None if self.menu_open_id == id_evento else id_evento

    # --------------------------------------------------
    # LÓGICA DE DATOS Y AGRUPACIÓN
    # --------------------------------------------------

    @rx.var
    def filtered_events(self) -> FinalFilteredList:
        data = self.grouped_events

        if self.search_query:
            query = self.search_query.lower()
            filtered = {}
            
            # El filtrado ahora opera sobre grouped_events, que ya es un dictionary agrupado
            for k, group in data.items():
                if k == "__PAST_HEADER__": continue # Omitir el separador
                
                eventos_filtrados = [
                    ev for ev in group["eventos"]
                    if query in ev["nombre_usuario"].lower()
                    or query in ev["descripcion"].lower()
                ]
                
                if eventos_filtrados:
                    # Creamos un nuevo grupo con el encabezado original
                    filtered[k] = {
                        "header": group["header"],
                        "eventos": eventos_filtrados
                    }
            data = filtered
        # Retornamos la lista de tuplas (clave, valor) que el frontend necesita para foreach
        return list(data.items())

    # Nuevo método para cargar datos de la BD
    def load_all_events(self):
        """Carga todos los eventos junto con los datos del usuario y el menú."""
        conn = None
        try:
            conn = get_connection()
            cur = conn.cursor()
            
            # Consulta compleja: Eventos + Usuario + Items de Menú
            # Usamos una subconsulta o agrupamos los resultados en Python
            # Optaremos por cargar todo y agrupar los menú items en Python.
            
            # 💡 Consulta JOIN: eventos, usuarios, menu_evento, menu
            # Nota: Agregué `descripcion` al SELECT, asumiendo que lo tienes en `eventos` o lo mapeas de `ubicacion`/`tipo`
            cur.execute("""
                SELECT 
                    e.id_evento, e.fecha, e.hora, e.ubicacion, e.cant_personas, e.costo, e.ubicacion AS descripcion_evento,
                    u.nombre as nombre_usuario,
                    u.correo, u.telefono,
                    me.cantidad,
                    m.nombre as nombre_menu
                FROM eventos e
                JOIN usuarios u ON e.id_usuario = u.id_usuario
                LEFT JOIN menu_evento me ON e.id_evento = me.id_evento
                LEFT JOIN menu m ON me.id_producto = m.id_producto
                ORDER BY e.fecha DESC, e.hora ASC;
            """)
            
            rows = cur.fetchall()
            
            events_raw = defaultdict(lambda: {
                "menu_items": []
            })
            
            for row in rows:
                (id_evento, event_date, event_time, ubicacion, cant_personas, costo, descripcion_evento,
                 user_name, user_email, user_phone, menu_item_cantidad, menu_item_nombre) = row
                
                if id_evento not in events_raw:
                    # Inicialización del evento
                    event_dt = datetime.combine(event_date, event_time)
                    events_raw[id_evento].update({
                        "id_evento": id_evento,
                        "nombre_usuario": user_name,
                        "user_email": user_email,          # <--- AGREGAR AL DICCIONARIO
                        "user_phone": user_phone,          # <--- AGREGAR AL DICCIONARIO
                        "cant_personas": int(cant_personas), # <--- AGREGAR cant_personas
                        "descripcion": descripcion_evento, # Usar ubicacion si no hay descripcion
                        "fecha_evento_str": event_date.strftime("%d/%m/%Y"),
                        "total": float(costo) if costo is not None else 0.0, # Asegurar que es float
                        "fecha_dt": event_dt, # Para ordenar/agrupar
                        "es_pasado": event_dt < datetime.now(),
                    })
                
                # Agregar item del menú si existe
                if menu_item_nombre:
                    events_raw[id_evento]["menu_items"].append({
                        "nombre": menu_item_nombre,
                        "cantidad": int(menu_item_cantidad),
                    })
            
            # Convertir el diccionario de eventos a una lista para el estado
            self.all_events = list(events_raw.values())
            
            self.group_events_by_date() # Agrupar al cargar
            
            # En caso de éxito
            rx.toast.success(f"Se cargaron {len(self.all_events)} eventos.")

        except Exception as e:
            print(f"Error cargando eventos de admin: {e}")
            return rx.toast.error(f"Error al cargar eventos: {str(e)}")
            
        finally:
            if conn:
                conn.close()

    def group_events_by_date(self):
        """Agrupa y ordena eventos por fecha (Futuros, Hoy/Mañana, Pasados)."""
        
        # Usamos self.all_events si no hay búsqueda activa, sino la lista que resulta del filtrado
        source = self.all_events if not self.search_query else self.filtered_events_list_for_grouping
        
        today = datetime.now().date()
        future_or_today = []
        past = []

        for ev in source:
            if ev["fecha_dt"].date() >= today:
                future_or_today.append(ev)
            else:
                past.append(ev)
        
        # Ordenamos los futuros del más cercano al más lejano, y los pasados del más reciente al más antiguo
        future_or_today.sort(key=lambda x: x["fecha_dt"])
        past.sort(key=lambda x: x["fecha_dt"], reverse=True)


        def agrupar(lista):
            grouped = defaultdict(lambda: {"header": "", "eventos": []})
            for r in lista:
                date_key = r["fecha_dt"].strftime("%Y-%m-%d")

                if r["fecha_dt"].date() == today:
                    header = "HOY"
                elif r["fecha_dt"].date() == today + timedelta(days=1):
                    header = "MAÑANA"
                else:
                    date_obj = r["fecha_dt"].date()
                    day_name = date_obj.strftime("%A")
                    month_name = date_obj.strftime("%B")
                    day_es = DIAS_ES.get(day_name, day_name)
                    month_es = MESES_ES.get(month_name, month_name)
                    header = f"{day_es.upper()}, {date_obj.day:02d} DE {month_es.upper()} DE {date_obj.year}"

                grouped[date_key]["header"] = header
                grouped[date_key]["eventos"].append(r)

            return grouped

        grouped_future = agrupar(future_or_today)
        grouped_past = agrupar(past)
        
        # Convertir a lista de tuplas y luego a diccionario para mantener el orden de inserción
        future_keys = sorted(grouped_future.keys())
        past_keys = sorted(grouped_past.keys(), reverse=True) # Pasados del más reciente al más antiguo
        
        final_ordered = {}

        # FUTURO
        for k in future_keys:
            final_ordered[k] = grouped_future[k]
        
        # SEPARADOR ESPECIAL
        if len(past_keys) > 0:
            final_ordered["__PAST_HEADER__"] = {
                "header": "EVENTOS PASADOS",
                "eventos": []
            }

        # PASADO
        for k in past_keys:
            final_ordered[k] = grouped_past[k]

        self.grouped_events = final_ordered

    # Helper para obtener la lista plana de eventos filtrados (usada en group_events_by_date)
    @rx.var
    def filtered_events_list_for_grouping(self) -> List[FullEvent]:
        """Devuelve la lista plana de eventos filtrados para ser agrupados."""
        if not self.search_query:
            return self.all_events
        
        query = self.search_query.lower()
        
        return [
            ev for ev in self.all_events 
            if query in ev["nombre_usuario"].lower()
            or query in ev["descripcion"].lower()
        ]

    # --------------------------------------------------
    # LÓGICA DE ELIMINACIÓN
    # --------------------------------------------------

    def delete_event(self, id_evento: int):
        """Elimina un evento pendiente y actualiza el estado."""
        conn = None
        try:
            conn = get_connection()
            cur = conn.cursor()
            
            # 1. Obtener la fecha del evento para la validación de pasado/futuro
            cur.execute("SELECT fecha, hora FROM eventos WHERE id_evento = %s;", (id_evento,))
            row = cur.fetchone()
            
            if row:
                event_date, event_time = row
                event_dt = datetime.combine(event_date, event_time)
                
                if event_dt < datetime.now():
                    return rx.toast.error("No se puede eliminar un evento que ya ha pasado.")

                # 2. Eliminar items del menú asociados (Importante por FK)
                cur.execute("DELETE FROM menu_evento WHERE id_evento = %s;", (id_evento,))

                # 3. Eliminar el evento
                cur.execute("DELETE FROM eventos WHERE id_evento = %s;", (id_evento,))
                conn.commit()
                
                # 4. Actualizar el estado en Reflex
                self.all_events = [
                    ev for ev in self.all_events 
                    if ev["id_evento"] != id_evento
                ]
                
                self.group_events_by_date() # Recalcular la vista agrupada
                
                return rx.toast.success("Evento eliminado correctamente. 🗑️")
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



# =========================================================
# =============== COMPONENTES VISUALES ====================
# =========================================================

# ----- ITEM DENTRO DEL MENÚ DEL EVENTO -----
def menu_item_row(item):
    return rx.hstack(
        rx.text(item["nombre"], color="white"),
        rx.spacer(),
        rx.text(f"x {item['cantidad']}", color="red"),
        padding_y="4px",
        width="100%",
    )


# ----- DROPDOWN DE MENÚ -----
def evento_menu_dropdown(evento):
    return rx.vstack(
        rx.box(
            rx.hstack(
                rx.text("Ver menú del evento", color="white", weight="bold"),
                rx.icon("chevron-down", color="white", size=18),
                cursor="pointer",
                on_click=lambda: AdminEventoState.toggle_menu(evento["id_evento"]),
                width="100%",
                justify="between",
            ),
            padding="10px",
            background="#1a1a1c",
            border_radius="8px",
            border="1px solid rgba(255,255,255,0.1)",
            width="100%"
        ),

        # Contenido expandido
        rx.cond(
            AdminEventoState.menu_open_id == evento["id_evento"],
            rx.vstack(
                rx.foreach(evento["menu_items"].to(List[MenuItem]), menu_item_row),
                padding="10px",
                spacing="2",
                background="#0f0f11",
                border_radius="8px",
                border="1px solid rgba(255,255,255,0.05)",
                margin_top="8px",
                width="100%"
            )
        ),

        width="100%",
        spacing="2"
    )


# ----- TARJETA DE EVENTO -----
def evento_card(evento: FullEvent):
    is_disabled = evento.es_pasado
    return rx.box(
        rx.vstack(
            # Encabezado principal
            rx.hstack(
                rx.text(evento["nombre_usuario"], weight="bold", color="white"),
                rx.spacer(),
                rx.text(evento["fecha_evento_str"], color="gray"),
                width="100%"
            ),
            # 💡 NUEVA SECCIÓN DE INFO ADICIONAL 💡
            rx.vstack(
                rx.hstack(
                    rx.icon("user", size=14, color="gray"),
                    rx.text(f"Personas: {evento['cant_personas']}", color="gray", size="2"),
                ),
                rx.hstack(
                    rx.icon("mail", size=14, color="gray"),
                    rx.text(evento["user_email"], color="gray", size="2"),
                ),
                rx.hstack(
                    rx.icon("phone", size=14, color="gray"),
                    rx.text(evento["user_phone"], color="gray", size="2"),
                ),
                align_items="start",
                spacing="1",
                padding_bottom="10px"
            ),

            rx.text(evento["descripcion"], color="white", opacity="0.8"),
            
            # Nuevo HStack para Total y Botón de Eliminar
            rx.hstack(
                rx.text(f"Total: ${evento['total']}", color="red", weight="bold"),
                rx.spacer(),
                rx.button(
                    rx.icon(tag="trash"),
                    on_click=AdminEventoState.delete_event(evento["id_evento"]), # <--- FUNCIÓN DE ELIMINAR
                    is_disabled=is_disabled,
                    color_scheme=rx.cond(is_disabled, "gray", "red"),
                    cursor=rx.cond(is_disabled, "default", "pointer"),
                    margin_left="auto",
                ),
                width="100%",
                align_items="center",
            ),
            
            evento_menu_dropdown(evento),

            spacing="3",
            width="100%"
        ),
        padding="20px",
        background=rx.cond(is_disabled, "#141414", "#1a1a1c"), # Color diferente si es pasado
        border_radius="12px",
        border="1px solid rgba(255,255,255,0.08)",
        width="100%"
    )


# =========================================================
# =============== EVENTOS AGRUPADOS POR DÍA ===============
# =========================================================
def eventos_by_day():
    return rx.vstack(

        rx.foreach(
            AdminEventoState.filtered_events,
            lambda item: rx.vstack(
                rx.heading(
                    item[1]["header"],
                    size="4",
                    color="red",
                    margin_top="35px",
                    margin_bottom="12px",
                    border_bottom="2px solid red",
                    padding_bottom="5px",
                    width="100%"
                ),

                rx.cond(
                    item[1]["eventos"].length() > 0,
                    rx.vstack(
                        rx.foreach(
                            item[1]["eventos"].to(List[FullEvent]),
                            lambda ev: evento_card(ev)
                        ),
                        spacing="4",
                        width="100%"
                    ),
                    #rx.text(
                        #"No hay eventos para este día.",
                        #color="gray",
                        #margin_bottom="20px"
                    #)
                ),

                width="100%",
                spacing="3",
                align_items="stretch",
            )
        ),

        width="100%",
        spacing="4",
        align_items="stretch",
    )

# ----- BARRA DE BÚSQUEDA ESTILIZADA -----
def search_bar_eventos():
    """Barra de búsqueda para filtrar eventos por nombre de usuario o descripción."""
    return rx.box(
        rx.hstack(
            rx.icon("search", size=16, color="#666", margin_left="10px"),
            rx.input(
                placeholder="Buscar por nombre o descripción...",
                value=AdminEventoState.search_query,
                on_change=AdminEventoState.set_search,
                width="100%",
                background="transparent",
                color="white",
                border="none",
                outline="none",
                padding_left="0"
            ),
            align_items="center",
            width="100%",
            spacing="2"
        ),
        width="350px", # Ancho fijo para el input
        border_radius="8px",
        background="#1a1a1c",
        border="1px solid rgba(255,255,255,0.1)",
        color="white",
        padding_right="10px",
        margin_top="30px"
        # Quitamos el margin_top si lo añadimos en el hstack que lo envuelve
    )

# =========================================================
# ======================= PÁGINA ==========================
# =========================================================
@rx.page(route="/admin/eventos", on_load=AdminEventoState.on_load)
def adm_eventos_page():
    return rx.box(
        admin_sidebar(active_item="eventos"),
        admin_sidebar_button(),

        rx.box(
            rx.vstack(
                # ====== Cabecera ======
                rx.hstack(
                    rx.heading("Gestión de Eventos", size="7", color="white", margin_bottom="30px"),
                    
                    # REEMPLAZAMOS EL INPUT DIRECTO POR LA FUNCIÓN DE BARRA ESTILIZADA
                    search_bar_eventos(),
                    width="100%",
                    justify="between",
                    align_items="center",
                    margin_bottom="10px",
                ),

                # ====== Contenido ======
                eventos_by_day(),

                width="100%",
                max_width="1200px",
                margin_x="auto",
                align_items="stretch"
            ),

            padding="40px",
            padding_top="80px",
            margin_left=rx.cond(AUIState.sidebar_open, "260px", "0px"),
            transition="margin-left 0.3s ease",
            min_height="100vh",
            background="#0d0d0f"
        ),

        width="100%",
        background="#0d0d0f",
        min_height="100vh"
    )
