import reflex as rx
from .auth_state import AuthState, get_connection
from .sidebar import sidebar, sidebar_button
from .ui_state import UIState
import os

# --------------------------
# CARD DE PRODUCTO MEJORADA
# --------------------------
def product_card(name, category, desc, img):
    return rx.box(
        rx.vstack(
            # Imagen
            rx.image(
                src=img,
                width="100%",
                height="180px",
                border_radius="10px 10px 0 0",
                object_fit="cover"
            ),
            # Contenido
            rx.vstack(
                rx.text(
                    name, 
                    color="white", 
                    font_weight="bold", 
                    size="4",
                    text_align="center"
                ),
                rx.center(
                    rx.badge(category, color_scheme="tomato", variant="solid"),
                ),
                rx.text(
                    desc, 
                    color="#ccc", 
                    size="2",
                    text_align="center",
                    margin_top="10px"
                ),
                spacing="2",
                align_items="center",
                padding="15px",
                width="100%",
            ),
            align="center",
            width="100%",
        ),
        background="#1a1a1c",
        border_radius="15px",
        width="100%",
        box_shadow="0 4px 15px rgba(0,0,0,0.3)",
        _hover={
            "transform": "translateY(-5px)",
            "transition": "0.3s",
            "box_shadow": "0 8px 25px rgba(0,0,0,0.4)",
        },
        transition="all 0.3s ease",
    )

# --------------------------
# OBTENER PRODUCTOS DESDE LA BD
# --------------------------
def fetch_products():
    products = []
    try:
        conn = get_connection()
        cur = conn.cursor()
        cur.execute("SELECT id_producto, nombre, descripcion, categoria, img FROM menu ORDER BY id_producto;")
        rows = cur.fetchall()
        for row in rows:
            id_producto, nombre, descripcion, categoria, img = row
            # Construir ruta de imagen: imgs/{id}/{img}
            img_path = f"/imgs/{id_producto}/{img}"
            products.append({
                "name": nombre,
                "category": categoria,
                "desc": descripcion,
                "img": img_path
            })
    except Exception as e:
        print(f"Error al obtener productos: {e}")
    finally:
        conn.close()
    return products

# --------------------------
# PAGE: PRODUCTOS DINÁMICA
# --------------------------
def productos_page():
    products = fetch_products()
    
    return rx.box(
        # Sidebar
        sidebar(active_item="productos"),
        sidebar_button(),
        
        # Contenido principal
        rx.box(
            # HERO SECTION
            rx.box(
                rx.box(
                    # Imagen de fondo con overlay
                    rx.box(
                        rx.image(
                            src="https://images.unsplash.com/photo-1757834787931-ddd70f3379a5?q=80&w=870&auto=format&fit=crop",
                            width="100%",
                            height="350px",
                            object_fit="cover",
                        ),
                        rx.box(
                            style={
                                "position": "absolute",
                                "top": "0",
                                "left": "0",
                                "width": "100%",
                                "height": "100%",
                                "background": "linear-gradient(to right, rgba(0,0,0,1), rgba(0,0,0,0.1))",
                            }
                        ),
                        rx.box(
                            rx.vstack(
                                rx.heading(
                                    "Echa ojo a nuestros productos", 
                                    color="white", 
                                    size="8",
                                    margin_bottom="10px"
                                ),
                                rx.text(
                                    "Lo que te ofrecemos en LEO no tiene igual. Revisa los productos disponibles en nuestro menú y en la cocina móvil.",
                                    color="#ddd",
                                    size="4",
                                    max_width="600px",
                                ),
                                align="start",
                                spacing="4",
                            ),
                            style={
                                "position": "absolute",
                                "top": "50%",
                                "left": "80px",
                                "transform": "translateY(-50%)",
                                "z_index": "2",
                            }
                        ),
                        position="relative",
                        width="100%",
                        height="350px",
                        overflow="hidden",
                    ),
                    width="100%",
                ),
                margin_bottom="40px",
                width="100%",
            ),
            
            # PRODUCTOS SECTION
            rx.vstack(
                rx.heading(
                    "Nuestro Menú", 
                    color="white", 
                    size="7",
                    margin_bottom="30px",
                    text_align="center"
                ),
                
                # Grid de productos dinámico
                rx.grid(
                    *[product_card(p["name"], p["category"], p["desc"], p["img"]) for p in products],
                    columns="4",
                    spacing="5",
                    width="100%",
                    padding_x=["20px", "40px", "60px", "80px"],
                    padding_bottom="60px",
                ),
                
                align="center",
                width="100%",
                spacing="7",
            ),
            
            # Estilos del contenedor principal
            background="#0d0d0f",
            min_height="100vh",
            padding_top="0",
            margin_top="0",
            margin_left=rx.cond(UIState.sidebar_open, "260px", "0px"),
            transition="margin-left 0.3s ease",
        ),
        width="100%",
        min_height="100vh",
    )
