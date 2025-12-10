import reflex as rx
from typing import List, Dict, Any, TypedDict, Optional
from ..auth_state import AuthState, get_connection
from .adminsidebar import admin_sidebar, admin_sidebar_button
from .aui_state import AUIState

# =========================================================
# ==================== DEFINICIÓN DE TIPOS ================
# =========================================================

class UserDict(TypedDict):
    id_usuario: int
    nombre: str
    correo: str
    telefono: str
    total_reservas: int
    total_eventos: int

# =========================================================
# ==================== STATE DE USUARIOS ==================
# =========================================================

class AdminUsuarioState(rx.State):
    search_query: str = ""
    all_users: List[UserDict] = [] # Lista maestra

    # --- VARIABLES PARA EL MODAL DE CONFIRMACIÓN ---
    show_confirm_modal: bool = False
    user_to_delete_id: int = -1
    user_to_delete_name: str = ""

    # --------------------------------------------------
    # CICLO DE VIDA Y SEGURIDAD
    # --------------------------------------------------
    async def on_load(self):
        auth_state = await self.get_state(AuthState)
        if not auth_state.logged_in:
            return rx.redirect("/login")
        if auth_state.rol != "admin":
            return [rx.toast.error("Acceso denegado."), rx.redirect("/")]
        
        return self.load_users()

    # --------------------------------------------------
    # CARGA DE DATOS
    # --------------------------------------------------
    def load_users(self):
        conn = None
        try:
            conn = get_connection()
            cur = conn.cursor()

            query = """
                SELECT 
                    u.id_usuario, 
                    u.nombre, 
                    u.correo, 
                    u.telefono,
                    (SELECT COUNT(*) FROM reserva r WHERE r.id_usuario = u.id_usuario) as total_reservas,
                    (SELECT COUNT(*) FROM eventos e WHERE e.id_usuario = u.id_usuario) as total_eventos
                FROM usuarios u
                WHERE u.rol = 'usuario'
                ORDER BY u.nombre ASC;
            """
            cur.execute(query)
            rows = cur.fetchall()

            users_formatted = []
            for row in rows:
                users_formatted.append({
                    "id_usuario": row[0],
                    "nombre": row[1],
                    "correo": row[2],
                    "telefono": row[3] if row[3] else "Sin teléfono",
                    "total_reservas": row[4],
                    "total_eventos": row[5]
                })

            self.all_users = users_formatted

        except Exception as e:
            print(f"Error cargando usuarios: {e}")
            return rx.toast.error(f"Error al cargar usuarios: {str(e)}")
        finally:
            if conn: conn.close()

    # --------------------------------------------------
    # BÚSQUEDA
    # --------------------------------------------------
    def set_search(self, value: str):
        self.search_query = value

    @rx.var
    def filtered_users(self) -> List[UserDict]:
        if not self.search_query:
            return self.all_users
        
        q = self.search_query.lower()
        return [
            u for u in self.all_users 
            if q in u["nombre"].lower() or q in u["correo"].lower()
        ]

    # --------------------------------------------------
    # GESTIÓN DEL MODAL DE ELIMINACIÓN
    # --------------------------------------------------
    
    def ask_delete_user(self, id_usuario: int, nombre: str):
        """Prepara los datos y abre el modal de confirmación."""
        self.user_to_delete_id = id_usuario
        self.user_to_delete_name = nombre
        self.show_confirm_modal = True

    def cancel_delete(self):
        """Cierra el modal y limpia las variables."""
        self.show_confirm_modal = False
        self.user_to_delete_id = -1
        self.user_to_delete_name = ""

    def perform_delete(self):
        """Ejecuta la eliminación real en la base de datos."""
        conn = None
        try:
            conn = get_connection()
            cur = conn.cursor()
            
            id_usuario = self.user_to_delete_id

            # 1. Borrar items de menú de eventos del usuario
            cur.execute("SELECT id_evento FROM eventos WHERE id_usuario = %s", (id_usuario,))
            eventos_ids = [row[0] for row in cur.fetchall()]
            
            if eventos_ids:
                ids_tuple = tuple(eventos_ids)
                # Sintaxis SQL segura para tuplas en IN
                cur.execute(f"DELETE FROM menu_evento WHERE id_evento IN {ids_tuple}")

            # 2. Eliminar eventos
            cur.execute("DELETE FROM eventos WHERE id_usuario = %s", (id_usuario,))

            # 3. Eliminar reservaciones
            cur.execute("DELETE FROM reserva WHERE id_usuario = %s", (id_usuario,))

            # 4. Eliminar usuario
            cur.execute("DELETE FROM usuarios WHERE id_usuario = %s", (id_usuario,))
            
            conn.commit()

            # Actualizar lista localmente
            self.all_users = [u for u in self.all_users if u["id_usuario"] != id_usuario]
            
            # Cerrar modal
            self.cancel_delete()
            return rx.toast.success("Usuario eliminado correctamente.")

        except Exception as e:
            if conn: conn.rollback()
            print(f"Error eliminando usuario: {e}")
            return rx.toast.error(f"Error crítico al eliminar: {str(e)}")
        finally:
            if conn: conn.close()


# =========================================================
# ================== COMPONENTES UI =======================
# =========================================================

def search_bar_usuarios():
    return rx.box(
        rx.hstack(
            rx.icon("search", size=16, color="#666", margin_left="10px"),
            rx.input(
                placeholder="Buscar usuario por nombre o correo...",
                value=AdminUsuarioState.search_query,
                on_change=AdminUsuarioState.set_search,
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
        width="350px",
        border_radius="8px",
        background="#1a1a1c",
        border="1px solid rgba(255,255,255,0.1)",
        color="white",
        padding_right="10px",
        margin_bottom="30px" 
    )

def user_card(user: UserDict):
    """Tarjeta individual de usuario."""
    return rx.box(
        rx.hstack(
            # --- INFO PRINCIPAL ---
            rx.vstack(
                rx.hstack(
                    rx.avatar(fallback=user["nombre"][0], size="3", radius="full", color_scheme="ruby"),
                    rx.vstack(
                        rx.text(user["nombre"], font_weight="bold", color="white", font_size="lg"),
                        
                        # 💡 CAMBIO: Correo y Teléfono en la misma fila con iconos
                        rx.hstack(
                            # Correo
                            rx.icon("mail", size=14, color="gray"),
                            rx.text(user["correo"], color="gray", font_size="sm"),
                            
                            # Separador visual (pipe)
                            rx.text("|", color="#333", font_size="sm", margin_x="5px"),
                            
                            # Teléfono
                            rx.icon("phone", size=14, color="gray"),
                            rx.text(user["telefono"], color="gray", font_size="sm"),
                            
                            align_items="center",
                            spacing="1"
                        ),
                        spacing="1",
                        align_items="start"
                    ),
                    spacing="3",
                    align_items="center"
                ),
                
                rx.divider(margin_y="12px", border_color="rgba(255,255,255,0.1)"),
                
                # --- ESTADÍSTICAS ---
                rx.hstack(
                    # Reservaciones
                    rx.hstack(
                        rx.icon("calendar-check", color="orange", size=18),
                        rx.text("Reservaciones:", color="gray", font_size="sm"),
                        rx.text(user["total_reservas"], color="white", font_weight="bold"),
                        spacing="2",
                        align_items="center"
                    ),
                    rx.spacer(),
                    # Eventos
                    rx.hstack(
                        rx.icon("utensils", color="cyan", size=18),
                        rx.text("Eventos a domicilio:", color="gray", font_size="sm"),
                        rx.text(user["total_eventos"], color="white", font_weight="bold"),
                        spacing="2",
                        align_items="center"
                    ),
                    width="100%"
                ),
                
                width="100%",
                align_items="start"
            ),
            
            rx.spacer(),
            
            # --- BOTÓN ELIMINAR (Llama a ask_delete_user) ---
            rx.button(
                rx.icon("trash-2", size=20),
                # 💡 CAMBIO: Ahora llama a la función que abre el modal
                on_click=lambda: AdminUsuarioState.ask_delete_user(user["id_usuario"], user["nombre"]),
                background="transparent",
                color="gray",
                _hover={"color": "red", "background": "rgba(255, 0, 0, 0.1)"},
                padding="10px"
            ),
            
            width="100%",
            align_items="start" 
        ),
        
        padding="20px",
        background="#1a1a1c",
        border_radius="12px",
        border="1px solid rgba(255,255,255,0.05)",
        width="100%",
        _hover={"border_color": "rgba(255,255,255,0.2)"}
    )

def users_grid():
    return rx.vstack(
        rx.cond(
            AdminUsuarioState.filtered_users.length() > 0,
            rx.vstack(
                rx.foreach(
                    AdminUsuarioState.filtered_users,
                    user_card
                ),
                width="100%",
                spacing="4"
            ),
            rx.center(
                rx.text("No se encontraron usuarios.", color="gray", padding="20px"),
                width="100%"
            )
        ),
        width="100%"
    )

# --- MODAL DE CONFIRMACIÓN DE ELIMINACIÓN ---
# --- MODAL DE CONFIRMACIÓN DE ELIMINACIÓN ---
def delete_confirm_modal():
    return rx.alert_dialog.root(
        rx.alert_dialog.content(
            rx.alert_dialog.title(
                "¿Eliminar usuario?",
                color="white",
                # Centrar el título
                text_align="center" 
            ),
            
            # Contenedor para el texto descriptivo
            rx.alert_dialog.description(
                rx.vstack( # Usamos vstack para centrar todo el contenido
                    rx.text(
                        "Estás a punto de eliminar a ",
                        rx.text(AdminUsuarioState.user_to_delete_name, font_weight="bold", color="red", font_size="20px", margin_top="10px"),
                        color="#cccccc",
                        text_align="center"
                    ),
                    
                    rx.text(
                        "Esta acción borrará permanentemente: ",
                        color="#cccccc",
                        margin_top="5px",
                        text_align="center"
                    ),
                    
                    # 💡 CAMBIO: Usamos HSTACKs para alinear los íconos y el texto
                    rx.vstack(
                        # Reservaciones
                        rx.hstack(
                            rx.icon("calendar-check", color="orange", size=18),
                            rx.text("Reservaciones", font_weight="bold", color="white"),
                            spacing="2",
                            align_items="center"
                        ),
                        # Eventos a domicilio
                        rx.hstack(
                            rx.icon("utensils", color="cyan", size=18),
                            rx.text("Eventos a domicilio", font_weight="bold", color="white"),
                            spacing="2",
                            align_items="center"
                        ),
                        spacing="3",
                        margin_top="10px"
                    ),
                    
                    align_items="center", # Centra el contenido dentro del VSTACK
                    width="100%"
                )
            ),
            
            # 💡 CAMBIO: Justify="center" para centrar los botones
            rx.flex(
                rx.alert_dialog.cancel(
                    rx.button(
                        "Cancelar", 
                        variant="soft", 
                        color_scheme="gray",
                        on_click=AdminUsuarioState.cancel_delete
                    ),
                ),
                rx.alert_dialog.action(
                    rx.button(
                        "Sí, eliminar", 
                        background="red", 
                        color="white",
                        _hover={"background": "#b30000"},
                        on_click=AdminUsuarioState.perform_delete
                    ),
                ),
                spacing="3",
                margin_top="25px", # Más margen superior
                justify="center", # Centra los botones
                width="100%"
            ),
            
            # Estilos del Modal
            background="#1a1a1c",
            border="1px solid rgba(255,255,255,0.1)",
        ),
        # 💡 CAMBIO: Ajustar la posición del contenido del modal
        position="fixed",
        top="50%",
        left="50%",
        transform="translate(-50%, -50%)",
        open=AdminUsuarioState.show_confirm_modal,
    )

# =========================================================
# ==================== PÁGINA PRINCIPAL ===================
# =========================================================

@rx.page(route="/admin/usuarios", on_load=AdminUsuarioState.on_load)
def adm_usuarios_page():
    return rx.box(
        admin_sidebar(active_item="usuarios"),
        admin_sidebar_button(),

        rx.box(
            rx.vstack(
                # Header y Buscador
                rx.hstack(
                    rx.heading("Gestión de Usuarios", size="7", color="white"),
                    rx.spacer(),
                    search_bar_usuarios(),
                    width="100%",
                    align_items="center",
                    justify="between"
                ),

                # Lista de Usuarios
                users_grid(),
                
                # Modal de Confirmación (Se renderiza invisible hasta que se activa)
                delete_confirm_modal(),

                width="100%",
                max_width="1000px", 
                margin_x="auto",
                align_items="stretch"
            ),

            padding="40px",
            padding_top="80px",
            margin_left=rx.cond(AUIState.sidebar_open, "260px", "0px"),
            transition="margin-left 0.3s ease",
            min_height="100vh",
            background="#0d0d0f",
        ),
        
        width="100%",
        min_height="100vh",
        background="#0d0d0f"
    )