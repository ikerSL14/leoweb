# leoweb/admin/adminsidebar.py
import reflex as rx
from ..auth_state import AuthState # Importamos desde el padre
from .aui_state import AUIState

# ----- ITEM -----
def admin_sidebar_item(label, icon, active=False, link=None):
    return rx.hstack(
        rx.icon(icon, color="red" if active else "#aaa", size=22),
        rx.text(
            label,
            color="red" if active else "white",
            font_weight="bold" if active else "normal"
        ),
        spacing="4",
        padding="12px",
        width="100%",
        border_radius="8px",
        cursor="pointer",
        transition="background 0.3s ease-in-out",
        _hover={"background": "#1b1b1b"},
        background="#1a1a1a" if active else "transparent",
        on_click=rx.redirect(link) if link else None
    )

# ----- SIDEBAR -----
def admin_sidebar(active_item=None):
    return rx.box(
        rx.vstack(
            rx.center(
                # Puedes usar otro logo o el mismo
                rx.image(
                    src="https://i.ibb.co/RkKgcyWy/leon.png", 
                    width="70px",
                ),
                padding_top="25px",
                padding_bottom="10px"
            ),

            rx.heading("Admin Panel", size="4", color="red", margin_bottom="10px"),

            admin_sidebar_item("Inicio", "layout-dashboard", active=(active_item=="dashboard"), link="/dashboard"),
            admin_sidebar_item("Productos", "package", active=(active_item=="productos"), link="/admin/productos"),
            admin_sidebar_item("Reservas", "calendar", active=(active_item=="reservas"), link="/admin/reservas"),
            admin_sidebar_item("Eventos a domicilio", "utensils", active=(active_item=="eventos"), link="/admin/eventos"),
            admin_sidebar_item("Usuarios", "users", active=(active_item=="usuarios"), link="/admin/usuarios"),

            rx.spacer(),

            # Logout
            rx.button(
                "Cerrar sesión",
                width="100%",
                background="red",
                color="white",
                border_radius="10px",
                padding="12px",
                cursor="pointer",
                transition="background 0.3s ease-in-out",
                _hover={"background": "#b30000"},
                on_click=AuthState.logout,
            ),

            spacing="4",
            padding="20px",
            align="center",
            height="100%", 
        ),
        position="fixed",
        top="0",
        left="0",
        height="100vh",
        width="260px",
        background="#111", # Un tono ligeramente distinto si quieres diferenciar
        transform=rx.cond(AUIState.sidebar_open, "translateX(0%)", "translateX(-100%)"),
        transition="0.3s",
        z_index="1000",
        box_shadow="4px 0 15px rgba(0,0,0,0.5)",
    )

# ----- BOTÓN -----
def admin_sidebar_button():
    return rx.box(
        rx.button(
            rx.cond(
                AUIState.sidebar_open,
                "✕",
                "☰"
            ),
            size="4",
            on_click=AUIState.toggle_sidebar,
            background="rgba(0, 0, 0, 0.65)",
            color="white",
            border_radius="50%",
            border="3px solid red",
            cursor="pointer",
            padding="15px",
            _hover={
                "border": "3px solid #b30000",
                "background": "rgba(0, 0, 0, 0.75)",
                "transform": "scale(1.08)",
                "transition": "all 0.2s ease",
            },
            transition="all 0.3s ease",
        ),
        position="fixed",
        top="20px",
        left=rx.cond(AUIState.sidebar_open, "280px", "20px"),
        transition="all 0.3s ease",
        z_index="1100"
    )