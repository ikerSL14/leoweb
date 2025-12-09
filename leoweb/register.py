import reflex as rx
from .auth_state import AuthState

# --------------------------
# ESTILO DE GLASSMORPHISM (Mantenemos la función)
# --------------------------
def glass_card(*children):
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
    # 🟢 Se cambia el on_click para redirigir a /login
    return rx.button(
        "← Iniciar Sesión",
        on_click=rx.redirect("/login"),
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
# REGISTER PAGE (Adaptamos los inputs)
# --------------------------
def register_page():
    return rx.box(
        back_button(),

        rx.center(
            glass_card(
                # TÍTULO
                rx.heading(
                    "Regístrate", color="white", size="6", margin_bottom="30px", text_align="center"
                ),

                # INPUT NOMBRE (NUEVO)
                rx.hstack(
                    rx.icon("user", color="white", size=20),
                    rx.input(
                        placeholder="Nombre completo",
                        on_change=AuthState.set_register_name,
                        value=AuthState.register_name, # Para mantener el valor si hay error
                        type="text",
                        size="3",
                        background="rgba(255,255,255,0.08)",
                        color="white",
                        border_radius="10px",
                        _placeholder={"color": "rgba(255,255,255,0.5)"},
                        _focus={"border": "1px solid red"},
                        width="100%"
                    ),
                    spacing="3",
                    width="100%",
                    margin_bottom="15px",
                    align_items="center"
                ),
                
                # INPUT CORREO
                rx.hstack(
                    rx.icon("mail", color="white", size=20),
                    rx.input(
                        placeholder="Correo electrónico",
                        on_change=AuthState.set_register_email,
                        value=AuthState.register_email, # Para mantener el valor
                        type="email",
                        size="3",
                        background="rgba(255,255,255,0.08)",
                        color="white",
                        border_radius="10px",
                        _placeholder={"color": "rgba(255,255,255,0.5)"},
                        _focus={"border": "1px solid red"},
                        width="100%"
                    ),
                    spacing="3",
                    width="100%",
                    margin_bottom="15px",
                    align_items="center"
                ),
                
                # INPUT TELÉFONO (NUEVO)
                rx.hstack(
                    rx.icon("phone", color="white", size=20),
                    rx.input(
                        placeholder="Teléfono",
                        on_change=AuthState.set_register_phone,
                        value=AuthState.register_phone, # Para mantener el valor
                        type="tel",
                        size="3",
                        background="rgba(255,255,255,0.08)",
                        color="white",
                        border_radius="10px",
                        _placeholder={"color": "rgba(255,255,255,0.5)"},
                        _focus={"border": "1px solid red"},
                        width="100%"
                    ),
                    spacing="3",
                    width="100%",
                    margin_bottom="15px",
                    align_items="center"
                ),

                # INPUT CONTRASEÑA
                rx.hstack(
                    rx.icon("lock", color="white", size=20),
                    rx.input(
                        placeholder="Contraseña",
                        on_change=AuthState.set_register_password,
                        value=AuthState.register_password, # Para limpiar después del registro
                        type="password",
                        size="3",
                        background="rgba(255,255,255,0.08)",
                        color="white",
                        border_radius="10px",
                        _placeholder={"color": "rgba(255,255,255,0.5)"},
                        _focus={"border": "1px solid red"},
                        width="100%"
                    ),
                    spacing="3",
                    width="100%",
                    margin_bottom="15px",
                    align_items="center"
                ),
                
                # INPUT CONFIRMAR CONTRASEÑA (NUEVO)
                rx.hstack(
                    rx.icon("lock", color="white", size=20),
                    rx.input(
                        placeholder="Confirmar Contraseña",
                        on_change=AuthState.set_register_confirm_password,
                        value=AuthState.register_confirm_password, # Para limpiar después del registro
                        type="password",
                        size="3",
                        background="rgba(255,255,255,0.08)",
                        color="white",
                        border_radius="10px",
                        _placeholder={"color": "rgba(255,255,255,0.5)"},
                        _focus={"border": "1px solid red"},
                        width="100%"
                    ),
                    spacing="3",
                    width="100%",
                    margin_bottom="25px",
                    align_items="center"
                ),

                # BOTÓN REGISTRARSE
                rx.button(
                    "Registrarse",
                    on_click=AuthState.register, # 🟢 Llama a la función de registro
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

                # LINK DE INICIO DE SESIÓN
                rx.text(
                    "¿Ya tienes cuenta? ",
                    rx.link(
                        "Inicia sesión aquí",
                        href="/login", # 🟢 Redirige a /login
                        font_weight="bold",
                        color="#ff4747",
                        _hover={"color": "#ff0000"},
                    ),
                    color="white",
                ),
            )
        ),

        width="100%",
        height="100vh",
        # 🟢 NUEVA IMAGEN DE FONDO
        background=(
        "linear-gradient(rgba(0,0,0,0.6), rgba(0,0,0,0.6)), "
        "url('https://images.unsplash.com/photo-1635527443454-2b695552d3df?q=80&w=870&auto=format&fit=crop&ixlib=rb-4.1.0&ixid=M3wxMjA3fDB8MHxwaG90by1wYWdlfHx8fGVufDB8fHx8fA%3D%3D')"
        ),
        background_size="cover",
        background_position="center",
        position="relative",
        display="flex",
        justify_content="center",
        align_items="center",
    )