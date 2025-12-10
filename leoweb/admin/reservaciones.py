import reflex as rx
from typing import List, Dict, Any, TypedDict, Tuple
from datetime import datetime, timedelta
from collections import defaultdict # Para agrupar las reservas
from ..auth_state import AuthState, get_connection
from .adminsidebar import admin_sidebar, admin_sidebar_button
from .aui_state import AUIState

# Traducción manual de días y meses (para evitar problemas de locale)
DIAS_ES = {
    "Monday": "Lunes",
    "Tuesday": "Martes",
    "Wednesday": "Miércoles",
    "Thursday": "Jueves",
    "Friday": "Viernes",
    "Saturday": "Sábado",
    "Sunday": "Domingo",
}

MESES_ES = {
    "January": "Enero",
    "February": "Febrero",
    "March": "Marzo",
    "April": "Abril",
    "May": "Mayo",
    "June": "Junio",
    "July": "Julio",
    "August": "Agosto",
    "September": "Septiembre",
    "October": "Octubre",
    "November": "Noviembre",
    "December": "Diciembre",
}


# Definición de un tipo para la reserva completa, incluyendo datos del usuario
FullReservation = Dict[str, Any]
# Definición de un tipo para las reservas agrupadas: {fecha: [reserva1, reserva2, ...]}
class GroupedItem(TypedDict):
    header: str
    reservas: List[FullReservation]

GroupedReservations = Dict[str, GroupedItem]

# --- STATE DE RESERVACIONES ---
class AdminReservaState(rx.State):
    """Estado para la gestión de reservaciones en el panel de administrador."""
    
    # Datos Maestros
    all_reservations: List[FullReservation] = [] # Lista maestra sin filtrar
    
    # Búsqueda
    search_query: str = "" # Texto del buscador (por nombre de usuario)

    # Datos Agrupados (Variable computada para la UI)
    grouped_reservations: GroupedReservations = {} 

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
        return self.load_all_reservations()

    # --------------------------------------------------
    # LÓGICA DE DATOS
    # --------------------------------------------------

    @rx.var
    def grouped_reservations_list(self) -> List[GroupedItem]:
        return [
            {
                "date_key": k,
                "header": v["header"],
                "reservas": v["reservas"]
            }
            for k, v in self.grouped_reservations.items()
        ]

    
    def load_all_reservations(self):
        """Carga todas las reservaciones junto con los datos del usuario asociado."""
        conn = None
        try:
            conn = get_connection()
            cur = conn.cursor()
            
            # 💡 Consulta JOIN para obtener: Reserva + Usuario + Sucursal (asumiendo que existe)
            cur.execute("""
                SELECT 
                    r.id_reserva, r.cant_personas, r.fecha, r.hora, r.tipo_evento,
                    u.nombre, u.correo, u.telefono,
                    s.nombre as sucursal_nombre
                FROM reserva r
                JOIN usuarios u ON r.id_usuario = u.id_usuario
                -- Asume que la tabla 'reserva' tiene 'id_sucursal' y 'sucursales' existe
                LEFT JOIN sucursales s ON r.id_sucursal = s.id_sucursal 
                ORDER BY r.fecha DESC, r.hora ASC; -- Ordenamos por fecha descendente (más próxima arriba)
            """)
            
            rows = cur.fetchall()
            reservations = []
            now = datetime.now()
            
            for row in rows:
                (id_reserva, cant_personas, res_date, res_time, tipo_evento,
                 user_name, user_email, user_phone, sucursal) = row
                
                reservation_dt = datetime.combine(res_date, res_time)
                
                reservations.append({
                    "id_reserva": id_reserva,
                    "cant_personas": cant_personas,
                    "fecha_dt": res_date, # Para ordenar/agrupar
                    "fecha": res_date.strftime("%d/%m/%Y"), 
                    "hora": res_time.strftime("%I:%M %p"), 
                    "tipo_evento": tipo_evento,
                    "sucursal": sucursal if sucursal else "No especificada",
                    "es_pasada": reservation_dt < now,
                    "usuario_nombre": user_name,
                    "usuario_correo": user_email,
                    "usuario_telefono": user_phone if user_phone else "N/A"
                })
            
            self.all_reservations = reservations
            self.group_reservations_by_date() # Agrupar al cargar
            
        except Exception as e:
            print(f"Error cargando reservaciones de admin: {e}")
            return rx.toast.error(f"Error al cargar reservaciones: {str(e)}")
            
        finally:
            if conn:
                conn.close()

    def group_reservations_by_date(self):
        """Agrupa y ordena reservas por fecha, poniendo las futuras arriba, luego una sección especial, y al final las pasadas."""
        
        source = self.filtered_reservations
        today = datetime.now().date()

        future_or_today = []
        past = []

        for res in source:
            if res["fecha_dt"] >= today:
                future_or_today.append(res)
            else:
                past.append(res)

        def agrupar(lista):
            grouped = defaultdict(lambda: {"header": "", "reservas": []})
            for r in lista:
                date_key = r["fecha_dt"].strftime("%Y-%m-%d")

                if r["fecha_dt"] == today:
                    header = "HOY"
                elif r["fecha_dt"] == today + timedelta(days=1):
                    header = "MAÑANA"
                else:
                    day_name = r["fecha_dt"].strftime("%A")
                    month_name = r["fecha_dt"].strftime("%B")
                    day_es = DIAS_ES.get(day_name, day_name)
                    month_es = MESES_ES.get(month_name, month_name)
                    header = f"{day_es.upper()}, {r['fecha_dt'].day:02d} DE {month_es.upper()} DE {r['fecha_dt'].year}"

                grouped[date_key]["header"] = header
                grouped[date_key]["reservas"].append(r)

            return grouped

        grouped_future = agrupar(future_or_today)
        grouped_past = agrupar(past)

        future_keys = sorted(grouped_future.keys()) 
        past_keys = sorted(grouped_past.keys())

        final_ordered = {}

        # FUTURO
        for k in future_keys:
            final_ordered[k] = grouped_future[k]

        # SEPARADOR ESPECIAL
        if len(past_keys) > 0:
            final_ordered["__PAST_HEADER__"] = {
                "header": "RESERVACIONES PASADAS",
                "reservas": []
            }

        # PASADO
        for k in past_keys:
            final_ordered[k] = grouped_past[k]

        self.grouped_reservations = final_ordered


        
    # --------------------------------------------------
    # LÓGICA DE BÚSQUEDA Y FILTRO
    # --------------------------------------------------

    def set_search_query(self, query: str):
        """Actualiza la consulta de búsqueda y recalcula la agrupación."""
        self.search_query = query
        self.group_reservations_by_date() # Volvemos a agrupar con el nuevo filtro

    @rx.var
    def filtered_reservations(self) -> List[FullReservation]:
        """Filtra la lista maestra de reservas por nombre de usuario."""
        if not self.search_query:
            return self.all_reservations
        
        query = self.search_query.lower()
        
        return [
            r for r in self.all_reservations 
            if query in r["usuario_nombre"].lower()
        ]
        
    # --------------------------------------------------
    # LÓGICA DE ELIMINACIÓN
    # --------------------------------------------------

    def delete_reservation(self, id_reserva: int):
        """Elimina una reservación pendiente y actualiza el estado."""
        conn = None
        try:
            conn = get_connection()
            cur = conn.cursor()
            
            # El backend debe confirmar que la reserva es futura antes de eliminar (Guardrail)
            cur.execute("SELECT fecha, hora FROM reserva WHERE id_reserva = %s;", (id_reserva,))
            row = cur.fetchone()
            
            if row:
                res_date, res_time = row
                reservation_dt = datetime.combine(res_date, res_time)
                
                if reservation_dt < datetime.now():
                    return rx.toast.error("No se puede eliminar una reservación que ya ha pasado.")

                cur.execute("DELETE FROM reserva WHERE id_reserva = %s;", (id_reserva,))
                conn.commit()
                
                # 3. Actualizar la lista de reservaciones en el estado
                self.all_reservations = [
                    res for res in self.all_reservations 
                    if res["id_reserva"] != id_reserva
                ]
                
                self.group_reservations_by_date() # Recalcular la vista agrupada
                
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

# --- COMPONENTES DE LA UI ---

def search_bar():
    """Barra de búsqueda para filtrar por nombre de usuario."""
    return rx.box(
        rx.hstack(
            rx.icon("search", size=16, color="#666", margin_left="10px"),
            rx.input(
                placeholder="Buscar por nombre de usuario...",
                value=AdminReservaState.search_query,
                on_change=AdminReservaState.set_search_query,
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
        width="350px", # Un poco más ancha que la de productos
        border_radius="8px",
        background="#1a1a1c",
        border="1px solid rgba(255,255,255,0.1)",
        color="white",
        padding_right="10px",
        margin_top="30px"
    )

def reservation_card(reserva: FullReservation):
    """Muestra una sola reservación con la información de usuario completa."""
    is_disabled = reserva["es_pasada"]
    
    return rx.box(
        rx.hstack(
            # INFORMACIÓN DE RESERVA Y USUARIO
            rx.vstack(
                # Reserva (Hora, Personas, Tipo, Sucursal)
                rx.hstack(
                    rx.icon("clock", size=14, color="#e0e0e0"),
                    rx.text(
                        f"{reserva['hora']} | {reserva['cant_personas']} personas | {reserva['tipo_evento']}",
                        font_weight="bold",
                        color=rx.cond(is_disabled, "#aaaaaa", "white"),
                    ),
                    spacing="2",
                ),
                rx.text(
                    f"Sucursal: {reserva['sucursal']}",
                    font_size="sm",
                    color=rx.cond(is_disabled, "#aaaaaa", "#e0e0e0"),
                    margin_top="5px",
                ),
                
                # Usuario (Nombre, Correo, Teléfono)
                rx.text("Datos del Usuario:", font_size="xs", color="red", margin_top="10px"),
                rx.text(
                    f"👤 {reserva['usuario_nombre']} | 📧 {reserva['usuario_correo']} | 📞 {reserva['usuario_telefono']}",
                    font_size="sm",
                    color="#bdbdbd",
                ),
                align_items="start",
                width="100%",
                spacing="1"
            ),
            
            # BOTÓN DE ELIMINAR
            rx.button(
                rx.icon(tag="trash"),
                on_click=AdminReservaState.delete_reservation(reserva["id_reserva"]),
                is_disabled=is_disabled,
                color_scheme=rx.cond(is_disabled, "gray", "red"),
                cursor=rx.cond(is_disabled, "default", "pointer"),
                margin_left="auto",
            ),
            
            width="100%",
            align_items="center",
            padding="15px",
        ),
        
        width="100%",
        background=rx.cond(is_disabled, "#141414", "#1a1a1c"), # Color diferente si es pasada
        border_radius="10px",
        border="1px solid rgba(255, 255, 255, 0.1)",
        box_shadow="0 2px 4px rgba(0, 0, 0, 0.2)",
        _hover={
            "background": rx.cond(is_disabled, "#141414", "#222224")
        },
    )

def reservations_by_day():
    return rx.vstack(
        rx.foreach(
            AdminReservaState.grouped_reservations.items(),
            lambda item: (
                # item = (key, group)
                rx.cond(
                    item[0] == "__PAST_HEADER__",

                    # Separador de reservaciones pasadas
                    rx.vstack(
                        rx.box(
                            rx.text(
                                item[1]["header"],
                                font_size="1.2rem",
                                color="white",
                                font_weight="bold",
                            ),
                            width="100%",
                            padding_y="10px",
                            margin_y="20px",
                            background="rgba(255,255,255,0.05)",
                            border_top="2px solid #444",
                            border_bottom="2px solid #444",
                            text_align="center"
                        )
                    ),

                    # Bloque normal: encabezado + tarjetas
                    rx.vstack(
                        rx.heading(
                            item[1]["header"],
                            size="4",
                            color="red",
                            margin_top="30px",
                            margin_bottom="15px",
                            border_bottom="2px solid red",
                            padding_bottom="5px",
                        ),

                        rx.cond(
                            item[1]["reservas"].length() > 0,
                            rx.vstack(
                                rx.foreach(
                                    item[1]["reservas"],
                                    lambda res: reservation_card(res)
                                ),
                                spacing="4",
                                width="100%",
                            ),
                            rx.text("No hay reservas para este día.", color="gray")
                        ),

                        width="100%",
                        align_items="start"
                    )
                )
            )
        )
    )



# --- PÁGINA PRINCIPAL ---

@rx.page(route="/admin/reservas", on_load=AdminReservaState.on_load)
def adm_reservas_page():
    return rx.box(
        admin_sidebar(active_item="reservas"),
        admin_sidebar_button(),
        
        rx.box(
            rx.vstack(
                # Encabezado y Barra de Búsqueda
                rx.hstack(
                    rx.heading("Gestión de Reservaciones", size="7", color="white", margin_bottom="30px"),
                    
                    search_bar(),
                    width="100%",
                    justify="between",
                    align_items="center",
                    margin_bottom="10px",
                ),
                
                # Contenido principal: Reservaciones Agrupadas
                reservations_by_day(),
                
                align_items="stretch",
                width="100%",
                margin_x="auto",
                max_width="1200px",
            ),
            
            padding="40px",
            padding_top="80px",
            margin_left=rx.cond(AUIState.sidebar_open, "260px", "0px"),
            transition="margin-left 0.3s ease",
            min_height="100vh",
            background="#0d0d0f"
        ),
        
        width="100%",
        min_height="100vh",
        background="#0d0d0f"
    )