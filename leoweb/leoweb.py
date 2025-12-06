import reflex as rx
from rxconfig import config
from .login import login_page
from .auth_state import AuthState
from .productos import productos_page
from .reservaciones import reservaciones_page
from .eventos import eventos_page
from .sidebar import sidebar, sidebar_button
from .ui_state import UIState

# --------------------------
# COMPONENTE DE SERVICIO REUTILIZABLE
# --------------------------
def service_item(icon_name: str, title: str):
    return rx.vstack(
        rx.box(
            rx.icon(
                icon_name,
                size=50,
                color="white",
            ),
            border="3px solid red",
            border_radius="50%",
            padding="20px",
            background="rgba(0, 0, 0, 0.65)",
            width="125px",
            height="125px",
            display="flex",
            align_items="center",
            justify_content="center",
            transition="transform 0.3s ease",
            _hover={"transform": "scale(1.1)"}
        ),
        rx.text(
            title,
            color="white",
            font_size="18px",
            font_weight="bold",
            margin_top="10px",
            text_align="center"
        ),
        spacing="3",
        min_width="150px",
        align="center",
        justify="center",
        margin_x="auto"
    )

# --------------------------
# HERO PRINCIPAL
# --------------------------
def hero():
    return rx.box(
        rx.box(
            position="absolute",
            bottom="0",
            left="0",
            right="0",
            height="100%",
            background="linear-gradient(to top, rgba(0,0,0,0.9), rgba(0,0,0,0.0))",
        ),
        rx.vstack(
            rx.heading("Leo Web", size="9", color="white"),
            rx.text("Descubre comidas fascinantes", size="5", color="#ddd"),
            rx.button(
                rx.icon("chevron-down", size=22),
                variant="solid",
                size="4",
                border_radius="50%",
                padding="14px",
                background="red",
                color="white",
                margin_top="20px",
                transition="all 0.2s ease-in-out",
                _hover={
                    "background": "#cc0000",
                    "transform": "scale(1.08)",
                    "cursor": "pointer",
                },
                on_click=rx.scroll_to("conocenos"),
            ),
            spacing="4",
            justify="center",
            align="center",
            height="100%",
            position="relative",
            z_index="2"
        ),
        background_image="url('https://images.unsplash.com/photo-1600891964599-f61ba0e24092')",
        background_size="cover",
        background_position="center",
        height="90vh",
        background_repeat="no-repeat",
        position="relative",
    )

# --------------------------
# SECCIÓN CONÓCENOS
# --------------------------
def conocenos():
    return rx.box(
        rx.box(
            rx.heading("Conócenos", size="8", color="white", text_align="center"),
            rx.box(
                margin_top="20px",
                height="4px",
                width="120px",
                background="red",
                border_radius="10px",
                margin_x="auto"
            ),
            text_align="center",
            margin_bottom="60px",
        ),
        # BLOQUE 1: TEXTO + IMAGEN
        rx.flex(
            rx.box(
                rx.text(
                    "**Grupo LEO** es una empresa tabasqueña con una larga tradición culinaria. "
                    "Durante décadas, nos hemos dedicado a ofrecer productos y servicios "
                    "de calidad, abarcando restaurante, pastelería y carnes frías. "
                    "Nuestras emblemáticas **Leonesas**, reconocidas por su sabor único, "
                    "son ya parte del patrimonio gastronómico de la región.",
                    color="#ddd", font_size="18px", line_height="1.6"
                ),
                width=["100%", "100%", "55%"],
                padding_right=["0", "0", "40px"],
            ),
            rx.box(
                rx.image(
                    src="https://images.unsplash.com/photo-1572802419224-296b0aeee0d9?q=80&w=815&auto=format&fit=crop&ixlib=rb-4.1.0&ixid=M3wxMjA3fDB8MHxwaG90by1wYWdlfHx8fGVufDB8fHx8fA%3D%3D",
                    width="100%", border_radius="14px", object_fit="cover"
                ),
                width=["100%", "100%", "45%"],
            ),
            display="flex",
            direction="row",
            wrap="wrap",
            justify="between",
            align="center",
            width="80%",
            max_width="1200px",
            margin_x="auto",
            margin_bottom="90px",
        ),
        # BLOQUE 2: IMAGEN + TEXTO
        rx.flex(
            rx.box(
                rx.image(
                    src="https://images.unsplash.com/photo-1528605248644-14dd04022da1",
                    width="100%", border_radius="14px", object_fit="cover"
                ),
                width=["100%", "100%", "45%"],
                padding_right=["0", "0", "40px"]
            ),
            rx.box(
                rx.text(
                    "Restaurantes LEO ha sido parte de la vida de los tabasqueños desde 1973. "
                    "Con más de 50 años de trayectoria, su sabor, ambiente familiar y dedicación "
                    "constante a la calidad la han convertido en una de las marcas más queridas "
                    "y respetadas del estado.",
                    color="#ddd", font_size="18px", line_height="1.6"
                ),
                width=["100%", "100%", "55%"],
            ),
            display="flex",
            direction="row",
            wrap="wrap",
            justify="between",
            align="center",
            width="80%",
            max_width="1200px",
            margin_x="auto",
            margin_bottom="90px",
        ),
        padding_y="100px",
        padding_x=["20px", "40px", "60px"],
        background="#0d0d0f",
        width="100%",
        id="conocenos",
    )

# --------------------------
# SERVICIOS PARALLAX FULL-WIDTH
# --------------------------
def servicios_parallax():
    return rx.box(
        rx.box(
            width="100%",
            height="100%",
            bg="rgba(0,0,0,0.7)",
            position="absolute",
            top="0",
            left="0",
            right="0",
            bottom="0",
            z_index="0",
        ),
        rx.box(
            rx.heading("Servicios", size="8", color="white", text_align="center"),
            rx.box(
                margin_top="20px",
                height="4px",
                width="120px",
                bg="red",
                border_radius="10px",
                margin_x="auto",
                margin_bottom="20px"
            ),
            rx.text(
                "Te ofrecemos los siguientes servicios:",
                color="#ddd",
                font_size="20px",
                text_align="center",
                margin_bottom="120px"
            ),
            rx.grid(
                service_item("store", "Comida en Sucursal"),
                service_item("calendar-check", "Reservaciones"),
                service_item("utensils", "Eventos a Domicilio"),
                columns="repeat(3, 1fr)",
                spacing="8",
                width="100%",
                max_width="900px",
                margin_x="auto",
                margin_top="40px",
            ),
            width="100%",
            max_width="1200px",
            margin_x="auto",
            position="relative",
            z_index="1",
        ),
        background_image="url('https://images.unsplash.com/photo-1552960226-639240203497?q=80&w=870&auto=format&fit=crop&ixlib=rb-4.1.0&ixid=M3wxMjA3fDB8MHxwaG90by1wYWdlfHx8fGVufDB8fHx8fA%3D%3D')",
        background_attachment="fixed",
        background_size="cover",
        background_position="center",
        background_repeat="no-repeat",
        width="100%",
        max_width="100%",
        margin_x="0",
        padding_x="0",
        position="relative",
        padding_y="120px",
        margin_bottom="100px",
    )

# --------------------------
# UBICACIÓN
# --------------------------
def ubicacion():
    return rx.box(
        rx.heading("Ubicación", size="8", color="white", text_align="center"),
        rx.box(
            margin_top="20px",
            height="4px",
            width="120px",
            bg="red",
            border_radius="10px",
            margin_x="auto",
            margin_bottom="40px"
        ),
        rx.html(
            """
            <iframe 
              width="100%" 
              height="450" 
              frameborder="0" 
              style="border:0; border-radius: 14px;"
              src="https://www.google.com/maps/embed?pb=!1m18!1m12!1m3!1d3794.815736937002!2d-92.9263084!3d17.9873078!2m3!1f0!2f0!3f0!3m2!1i1024!2i768!4f13.1!3m3!1m2!1s0x85edd831b44fc153%3A0x242d29d2524faa90!2sGrupo%20Leo!5e0!3m2!1ses-419!2smx!4v1764989628814!5m2!1ses-419!2smx"
              allowfullscreen loading="lazy">
            </iframe>
            """
        ),
        # ===== ANCHO LIMITADO Y CENTRADO =====
        width=["90%", "80%", "70%"],
        margin_x="auto",
        margin_bottom="60px",
        background="#0d0d0f",
        padding_x="0"
    )

# --------------------------
# FOOTER
# --------------------------
def footer():
    return rx.box(
        rx.text("© 2025 Leoweb • Todos los derechos reservados", color="#888"),
        padding="30px",
        background="#111",
        text_align="center"
    )

# --------------------------
# INDEX PAGE
# --------------------------
def index():
    return rx.box(
        sidebar(active_item="restaurantes"),
        sidebar_button(),
        hero(),
        conocenos(),
        servicios_parallax(),
        ubicacion(),
        footer(),
        background="#0d0d0f",
        width="100%",
        min_height="100vh",
        padding_left=rx.cond(UIState.sidebar_open, "260px", "0px"), 
        transition="padding-left 0.3s ease",
    )

# APP
app = rx.App(stylesheets=[],
    style={
        "html": {
            "scrollBehavior": "smooth"
        }
    })
app.add_page(index, title="Leoweb Restaurant")
app.add_page(login_page, route="/login", title="Iniciar sesión")
app.add_page(productos_page, route="/productos", title="Productos")
app.add_page(reservaciones_page, route="/reservaciones", title="Reservaciones")
app.add_page(eventos_page, route="/eventos", title="Eventos a Domicilio")
