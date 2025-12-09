import reflex as rx
from .auth_state import AuthState

# --------------------------
# ESTILO DE GLASSMORPHISM
# --------------------------
def glass_card(*children):
    """Componente reutilizable para la tarjeta con efecto glassmorphism."""
    return rx.box(
        *children,
        width="380px",
        padding="30px",
        border_radius="20px",
        background="rgba(0,0,0,0.35)",
        backdrop_filter="blur(10px)",
        border="1px solid rgba(255,255,255,0.15)",
        box_shadow="0px 8px 25px rgba(0,0,0,0.4)",
    )


# --------------------------
# BOTÓN REGRESAR (float)
# --------------------------
def back_button():
    """Botón flotante para regresar a la página principal."""
    return rx.button(
        "← Regresar",
        on_click=rx.redirect("/"),
        position="absolute",
        top="20px",
        left="20px",
        background="rgba(250,0,0,0.8)",
        color="white",
        cursor="pointer",
        border_radius="8px",
        padding="10px 16px",
        transition="background 0.3s ease-in-out",
        backdrop_filter="blur(6px)",
        _hover={"background": "rgba(235,0,0,0.7)"},
        z_index="2000"
    )


# --------------------------
# LOGIN PAGE
# --------------------------
def login_page():
    return rx.box(
        back_button(),

        rx.center(
            # 🟢 1. ENVOLVEMOS EL CONTENIDO EN UN rx.form
            rx.form(
                
                
                # Usamos glass_card para darle el estilo visual al contenido del formulario
                glass_card( 
                    rx.heading(
                        "Iniciar sesión", color="white", size="6", margin_bottom="40px", text_align="center"
                    ),

                    # INPUT EMAIL
                    rx.hstack(
                        rx.icon("mail", color="white", size=20),
                        rx.input(
                            placeholder="Correo electrónico",
                            on_change=AuthState.set_email,
                            type="email",
                            size="3",
                            background="rgba(255,255,255,0.08)",
                            color="white",
                            border_radius="10px",
                            padding_left="10px",
                            _placeholder={"color": "rgba(255,255,255,0.5)"},
                            _focus={"border": "1px solid red"},
                            width="100%"
                        ),
                        spacing="3",
                        width="100%",
                        margin_bottom="15px",
                        align_items="center"
                    ),

                    # INPUT PASSWORD
                    rx.hstack(
                        rx.icon("lock", color="white", size=20),
                        rx.input(
                            placeholder="Contraseña",
                            on_change=AuthState.set_password,
                            type="password",
                            size="3",
                            background="rgba(255,255,255,0.08)",
                            color="white",
                            border_radius="10px",
                            padding_left="10px",
                            _placeholder={"color": "rgba(255,255,255,0.5)"},
                            _focus={"border": "1px solid red"},
                            width="100%"
                        ),
                        spacing="3",
                        width="100%",
                        margin_bottom="25px",
                        align_items="center"
                    ),

                    # BOTÓN ENTRAR
                    rx.button(
                        "Entrar",
                        # 🟢 3. AÑADIMOS type="submit" para que Enter lo active
                        type="submit", 
                        # on_click ya no es necesario aquí, pero si lo tuvieras, 
                        # on_submit tiene precedencia al presionar Enter.
                        width="100%",
                        size="3",
                        background="red",
                        color="white",
                        border_radius="10px",
                        margin_bottom="20px",
                        cursor="pointer",
                        transition="background 0.3s ease-in-out",
                        _hover={"background": "#b30000"},
                    ),

                    rx.divider(
                        border_color="rgba(255,255,255,0.2)", margin_y="10px"
                    ),

                    # LINK DE REGISTRO
                    rx.text(
                        "¿No tienes cuenta? ",
                        rx.link(
                            "Regístrate aquí",
                            href="/register",
                            font_weight="bold",
                            color="#ff4747",
                            _hover={"color": "#ff0000"},
                        ),
                        color="white",
                    ),
                ), # Cierre de glass_card
                # 🟢 2. ASIGNAMOS EL EVENTO DE LOGIN AL on_submit DEL FORMULARIO
                on_submit=AuthState.login,
                width="380px", # Aseguramos el ancho para el formulario
            ) # Cierre de rx.form
        ), # Cierre de rx.center

        width="100%",
        height="100vh",
        background=(
        "linear-gradient(rgba(0,0,0,0.6), rgba(0,0,0,0.6)), "
        "url('https://images.unsplash.com/photo-1684957691800-502e754ea1e5?q=80&w=774&auto=format&fit=crop&ixlib=rb-4.1.0&ixid=M3wxMjA3fDB8MHxwaG90by1wYWdlfHx8fGVufDB8fHx8fA%3D%3D')"
        ),
        background_size="cover",
        background_position="center",
        position="relative",
        display="flex",
        justify_content="center",
        align_items="center",
    )