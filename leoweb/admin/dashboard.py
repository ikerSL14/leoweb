# leoweb/admin/dashboard.py
import reflex as rx
from .adminsidebar import admin_sidebar, admin_sidebar_button
from .aui_state import AUIState
from ..auth_state import AuthState, get_connection # Importar get_connection del padre
from typing import List, Dict, Any # Importar tipos para la lista de usuarios/datos

# --- STATE DEL DASHBOARD ---
class DashboardState(rx.State):
    count_productos: int = 0
    count_reservas: int = 0
    count_eventos: int = 0
    count_usuarios: int = 0

    # 🟢 Nuevas variables para la gráfica y la tabla
    activity_data: List[Dict[str, Any]] = []
    latest_users: List[List[str]] = [] # Lista de listas: [[nombre, correo, fecha_registro], ...]

    # Validación de sesión de admin al cargar
    async def on_load(self):
        # 🟢 1. Obtener el estado de autenticación de forma asíncrona
        auth_state = await self.get_state(AuthState)
        
        # Redireccionar si no está logueado
        if not auth_state.logged_in:
            return rx.redirect("/login")
        
        # Redireccionar si no es admin
        if auth_state.rol != "admin":
            return [
                rx.toast.error("Acceso denegado. Se requiere ser administrador."),
                rx.redirect("/") 
            ]
        
        # 3. Cargar datos
        return self.load_counts() # Por ahora cargamos directo para probar
    
    def load_counts(self):
        """Carga los conteos para las tarjetas del dashboard."""
        conn = None
        try:
            conn = get_connection()
            cur = conn.cursor()
            
            # Consultas de conteo
            cur.execute("SELECT COUNT(*) FROM menu;")
            self.count_productos = cur.fetchone()[0]
            
            cur.execute("SELECT COUNT(*) FROM reserva;")
            self.count_reservas = cur.fetchone()[0]
            
            cur.execute("SELECT COUNT(*) FROM eventos;")
            self.count_eventos = cur.fetchone()[0]
            
            cur.execute("SELECT COUNT(*) FROM usuarios WHERE rol = 'usuario';")
            self.count_usuarios = cur.fetchone()[0]

            # 2. Datos de Actividad para la Gráfica
            # Queremos: Cantidad de Reservaciones y Cantidad de Eventos
            self.activity_data = [
                {"name": "Reservaciones", "count": self.count_reservas},
                {"name": "Eventos a Domicilio", "count": self.count_eventos},
            ]
            
            # 3. Últimos 5 Usuarios con rol 'usuario'
            # (Asumiendo que tienes una columna de registro/creación, usaremos id_usuario descendente)
            cur.execute(
                """
                SELECT nombre, correo, id_usuario
                FROM usuarios
                WHERE rol = 'usuario'
                ORDER BY id_usuario DESC 
                LIMIT 5;
                """
            )
            # Formatear la fecha para que se vea mejor en la tabla
            users = cur.fetchall()
            self.latest_users = [[name, email, f"ID: {user_id}"] for name, email, user_id in users]
            
        except Exception as e:
            print(f"Error cargando dashboard: {e}")
        finally:
            if conn:
                conn.close()
    
# 🟢 COMPONENTE GRÁFICA DE BARRAS
def activity_chart():
    return rx.recharts.bar_chart(
        rx.recharts.bar(
            data_key="count", 
            stroke="#ff0000", 
            fill="#ff0000", 
            bar_size=30,
            radius=[5, 5, 0, 0] # Bordes redondeados
        ),
        rx.recharts.x_axis(data_key="name", stroke="#999"),
        rx.recharts.y_axis(stroke="#999"),
        data=DashboardState.activity_data,
        margin={"top": 20, "right": 20, "left": 10, "bottom": 5},
        background_color="#1a1a1c",
        width="100%",
        height=250
    )

# 🟢 COMPONENTE TABLA DE ÚLTIMOS USUARIOS
def latest_users_table():
    return rx.box(
        rx.text("Últimos Usuarios", color="white", font_weight="bold", margin_bottom="15px"),
        rx.table.root(
            rx.table.header(
                rx.table.row(
                    rx.table.column_header_cell("Nombre"),
                    rx.table.column_header_cell("Correo"),
                    rx.table.column_header_cell("ID"),
                ),
                style={"color": "#aaa"}
            ),
            rx.table.body(
                rx.foreach(DashboardState.latest_users, render_user_row)
            ),
        ),
        width="100%"
    )

def render_user_row(user: list):
    """Renderiza una fila de usuario."""
    return rx.table.row(
        rx.table.cell(user[0]),
        rx.table.cell(user[1]),
        rx.table.cell(user[2]),
        style={"color": "white", "font_size": "sm"}
    )

# --- COMPONENTE TARJETA DE RESUMEN ---
def summary_card(title, count, icon):
    return rx.box(
        rx.hstack(
            rx.icon(icon, size=40, color="red"),
            rx.vstack(
                rx.text(title, color="#aaa", font_size="sm", font_weight="bold"),
                rx.text(count, color="white", font_size="3xl", font_weight="bold"),
                align_items="end",
                spacing="1"
            ),
            justify="between",
            align_items="center",
            width="100%"
        ),
        padding="20px",
        background="#1a1a1c", # Gris más claro que el fondo
        border_radius="15px",
        box_shadow="0 4px 6px rgba(0, 0, 0, 0.3)",
        border="1px solid rgba(255,255,255,0.05)",
        width="100%"
    )

# --- PÁGINA DASHBOARD ---
@rx.page(route="/dashboard", on_load=DashboardState.on_load)
def dashboard_page():
    return rx.box(
        admin_sidebar(active_item="dashboard"),
        admin_sidebar_button(),
        
        rx.box(
            rx.vstack(
                # GRID DE TARJETAS
                rx.grid(
                    summary_card("Productos", DashboardState.count_productos, "package"),
                    summary_card("Reservaciones", DashboardState.count_reservas, "calendar-check"),
                    summary_card("Eventos", DashboardState.count_eventos, "utensils"),
                    summary_card("Usuarios", DashboardState.count_usuarios, "users"),
                    columns="4",
                    spacing="5",
                    width="100%",
                    margin_bottom="30px"
                ),
                
                # AQUÍ IRÁN LAS GRÁFICAS Y TABLAS
                rx.hstack(
                    # Contenedor Gráfica
                    rx.box(
                        rx.text("Gráfica de Actividad", color="white", margin_bottom="10px", font_weight="bold"),
                        activity_chart(),
                        height="300px",
                        width="65%",
                        background="#1a1a1c",
                        border_radius="15px",
                        padding="20px"
                    ),
                    # Contenedor Últimos Usuarios
                    rx.box(
                        
                        latest_users_table(),
                        height="300px",
                        width="35%",
                        background="#1a1a1c",
                        border_radius="15px",
                        padding="20px"
                    ),
                    width="100%",
                    spacing="5"
                ),
                
                align_items="start",
                width="100%",
                margin_x="auto", # <-- AGREGAR ESTO PARA CENTRAR EL CONTENIDO
                max_width="1200px", # Ancho máximo para pantallas grandes
            ),
            
            padding="40px",
            padding_top="80px", # Espacio para el botón móvil si fuera necesario
            margin_left=rx.cond(AUIState.sidebar_open, "260px", "0px"),
            transition="margin-left 0.3s ease",
            min_height="100vh",
            background="#0d0d0f"
        ),
        
        width="100%",
        min_height="100vh",
        background="#0d0d0f"
    )