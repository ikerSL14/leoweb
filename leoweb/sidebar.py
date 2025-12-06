import reflex as rx
from .auth_state import AuthState
from .ui_state import UIState

# ----- ITEM -----
def sidebar_item(label, icon, active=False, link=None):
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
def sidebar(active_item=None):
    return rx.box(
        rx.vstack(
            rx.center(
                rx.image(
                    src="https://i.ibb.co/RkKgcyWy/leon.png",
                    width="70px",
                ),
                padding_top="25px",
                padding_bottom="10px"
            ),

            rx.heading("Menú", size="6", color="white"),

            sidebar_item("Restaurantes", "store", active=(active_item=="restaurantes"), link="/"),
            sidebar_item("Productos", "package", active=(active_item=="productos"), link="/productos"),

            rx.cond(
                AuthState.logged_in,
                rx.fragment(
                    sidebar_item("Reservaciones", "calendar-check", active=(active_item=="reservaciones"), link="/reservaciones"),
                    sidebar_item("Eventos a domicilio", "utensils", active=(active_item=="eventos"), link="/eventos"),
                    sidebar_item("Perfil", "user", active=(active_item=="perfil")),
                )
            ),

            rx.spacer(),

            # Login/Logout
            rx.cond(
                AuthState.logged_in,
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
                rx.button(
                    "Iniciar sesión",
                    width="100%",
                    background="red",
                    color="white",
                    border_radius="10px",
                    padding="12px",
                    cursor="pointer",
                    transition="background 0.3s ease-in-out",
                    _hover={"background": "#b30000"},
                    on_click=rx.redirect("/login"),
                )
            ),

            spacing="4",
            padding="20px",
            align="center",
        ),
        position="fixed",
        top="0",
        left="0",
        height="100vh",
        width="260px",
        background="#111",
        transform=rx.cond(UIState.sidebar_open, "translateX(0%)", "translateX(-100%)"),
        transition="0.3s",
        z_index="1000",
        box_shadow="4px 0 15px rgba(0,0,0,0.5)",
    )


# ----- BOTÓN -----
def sidebar_button():
    return rx.box(
        rx.button(
            rx.cond(
                UIState.sidebar_open,
                "✕",
                "☰"
            ),
            size="4",
            on_click=UIState.toggle_sidebar,
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
        left=rx.cond(UIState.sidebar_open, "280px", "20px"),
        transition="all 0.3s ease",
        z_index="1100"
    )
