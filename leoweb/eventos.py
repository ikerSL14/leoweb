import reflex as rx
from .auth_state import AuthState, get_connection
from .sidebar import sidebar, sidebar_button
from .ui_state import UIState


# --------------------------------------------------------
# OBTENER PRODUCTOS DESDE BD
# --------------------------------------------------------
def fetch_products():
    products = []
    try:
        conn = get_connection()
        cur = conn.cursor()
        cur.execute("SELECT id_producto, nombre, precio FROM menu ORDER BY id_producto;")
        rows = cur.fetchall()
        for row in rows:
            id_producto, nombre, precio = row
            products.append({
                "id": id_producto,
                "name": nombre,
                "price": float(precio)
            })
    except Exception as e:
        print(f"Error al obtener productos: {e}")
    finally:
        conn.close()
    return products


# --------------------------------------------------------
# STATE PARA EVENTOS
# --------------------------------------------------------
class EventState(rx.State):
    products: list[dict] = []

    fecha: str = ""
    hora: str = ""
    ubicacion: str = ""
    cant_personas: int = 1

    menu_modal_open: bool = False
    productos_seleccionados: list[dict] = []
    total: float = 0.0

    @rx.var
    def subtotales(self) -> list[str]:
        return [f"${p['cantidad'] * p['precio']:.2f}" for p in self.productos_seleccionados]


    # CALCULAR SUBTOTAL DE UN PRODUCTO DESDE FOREACH
    def get_subtotal(self, index):
        try:
            p = self.productos_seleccionados[index]
            return p["cantidad"] * p["precio"]
        except:
            return 0

    @rx.var
    def total_str(self) -> str:
        return f"Total = ${self.total:.2f}"

    # Cargar productos al iniciar
    def on_load(self):
        self.products = fetch_products()

    # ---------------------------------------
    # SETTERS
    # ---------------------------------------
    def set_fecha(self, v):
        self.fecha = v

    def set_hora(self, v):
        self.hora = v

    def set_ubicacion(self, v):
        self.ubicacion = v

    def set_cant_personas(self, v):
        try:
            n = int(v) if v else 1
            if n < 1:
                n = 1
            self.cant_personas = n
        except:
            self.cant_personas = 1

    # ---------------------------------------
    # MENÚ
    # ---------------------------------------
    def toggle_menu_modal(self):
        self.menu_modal_open = not self.menu_modal_open

    def add_producto(self, pid, name, price):
        for p in self.productos_seleccionados:
            if p["id"] == pid:
                p["cantidad"] += 1
                self.update_total()
                return

        self.productos_seleccionados.append({
            "id": pid,
            "name": name,
            "cantidad": 1,
            "precio": price
        })
        self.update_total()

    def remove_producto(self, index):
        if 0 <= index < len(self.productos_seleccionados):
            self.productos_seleccionados.pop(index)
            self.update_total()

    def update_cantidad(self, index, cantidad):
        try:
            n = int(cantidad) if cantidad else 1
            if n < 1:
                n = 1
            self.productos_seleccionados[index]["cantidad"] = n
            self.update_total()
        except:
            pass

    def update_total(self):
        self.total = sum(
            p["cantidad"] * p["precio"] for p in self.productos_seleccionados
        )

    def save_menu(self):
        self.menu_modal_open = False

    # ---------------------------------------
    # BD: Guardar Evento
    # ---------------------------------------
    def submit_event(self, current_user):
        if not self.fecha or not self.hora or not self.ubicacion:
            return rx.toast.error("Completa todos los campos")

        try:
            conn = get_connection()
            cur = conn.cursor()

            # Guardar evento
            cur.execute("""
                INSERT INTO eventos (id_usuario, fecha, hora, ubicacion, cant_personas, costo)
                VALUES (%s, %s, %s, %s, %s, %s)
                RETURNING id_evento;
            """, (
                current_user,
                self.fecha,
                self.hora,
                self.ubicacion,
                self.cant_personas,
                self.total
            ))

            id_evento = cur.fetchone()[0]

            # Guardar productos
            for p in self.productos_seleccionados:
                cur.execute("""
                    INSERT INTO menu_evento (id_producto, id_evento, cantidad)
                    VALUES (%s, %s, %s);
                """, (
                    p["id"], id_evento, p["cantidad"]
                ))

            conn.commit()
            rx.toast.success("Evento guardado correctamente!")

            # Reset
            self.fecha = ""
            self.hora = ""
            self.ubicacion = ""
            self.cant_personas = 1
            self.productos_seleccionados = []
            self.total = 0.0

        except Exception as e:
            print(f"Error al guardar evento: {e}")
            rx.toast.error("Error al guardar evento")
        finally:
            conn.close()

@rx.page(on_load=EventState.on_load)
def eventos_page():
    return rx.box(
        sidebar(active_item="eventos"),
        sidebar_button(),

        rx.box(
            rx.vstack(
                rx.heading(
                    "Solicita un evento a domicilio",
                    color="white",
                    size="8",
                    margin_bottom="20px"
                ),

                # FILA 1
                rx.hstack(
                    rx.input(
                        type_="date",
                        value=EventState.fecha,
                        on_change=EventState.set_fecha
                    ),
                    rx.input(
                        type_="time",
                        value=EventState.hora,
                        on_change=EventState.set_hora
                    ),
                    spacing="5",
                    margin_bottom="20px",
                ),

                # FILA 2
                rx.hstack(
                    rx.input(
                        type_="text",
                        placeholder="Ubicación",
                        value=EventState.ubicacion,
                        on_change=EventState.set_ubicacion
                    ),
                    rx.input(
                        type_="number",
                        min=1,
                        value=EventState.cant_personas,
                        on_change=EventState.set_cant_personas
                    ),
                    spacing="5",
                    margin_bottom="20px",
                ),

                # BOTÓN MENU
                rx.button(
                    "Arma tu menú",
                    on_click=EventState.toggle_menu_modal,
                    color_scheme="red",
                    margin_bottom="20px"
                ),

                # MODAL
                rx.dialog.root(
                    rx.dialog.trigger(
                        rx.button(
                            "Arma tu menú",
                            color_scheme="red",
                            margin_bottom="20px"
                        )
                    ),

                    rx.dialog.content(
                        rx.vstack(
                            rx.hstack(
                                rx.dialog.title(
                                    rx.heading("Arma tu menú", size="6", color="white")
                                ),
                                rx.text(
                                    EventState.total_str,
                                    color="white",
                                    margin_left="auto"
                                ),
                                spacing="4",
                                width="100%"
                            ),

                            # LISTA DE PRODUCTOS SELECCIONADOS
                            rx.foreach(
                                EventState.productos_seleccionados,
                                lambda p, i: rx.hstack(
                                    rx.text(p["name"], color="white", width="200px"),

                                    rx.input(
                                        type_="number",
                                        min=1,
                                        value=p["cantidad"],
                                        on_change=lambda v, idx=i: EventState.update_cantidad(idx, v),
                                        width="100px"
                                    ),

                                    rx.text(
                                        EventState.subtotales[i],
                                        color="white",
                                        width="80px"
                                    ),

                                    rx.button(
                                        "Eliminar",
                                        on_click=lambda idx=i: EventState.remove_producto(idx),
                                        color_scheme="gray"
                                    ),

                                    spacing="3",
                                    margin_bottom="10px",
                                )
                            ),

                            # LISTA DE PRODUCTOS A AGREGAR
                            rx.vstack(
                                rx.text("Agregar platillo", color="#ddd", margin_top="10px"),

                                rx.foreach(
                                    EventState.products,
                                    lambda p: rx.button(
                                        f"+ {p['name']} (${p['price']:.2f})",
                                        on_click=lambda pid=p["id"], n=p["name"], pr=p["price"]: EventState.add_producto(pid, n, pr),
                                        color_scheme="green"
                                    )
                                ),
                                spacing="3"
                            ),

                            rx.button(
                                "Guardar menú",
                                on_click=EventState.save_menu,
                                color_scheme="red",
                                margin_top="20px"
                            ),

                            spacing="5"
                        ),
                        background="#1a1a1c",
                        border_radius="15px",
                        width="600px",
                        padding="25px"
                    ),

                    open=EventState.menu_modal_open,
                    on_open_change=EventState.toggle_menu_modal,
                ),

                rx.button(
                    "Solicitar evento",
                    on_click=lambda: EventState.submit_event(AuthState.current_user),
                    color_scheme="red",
                    margin_top="30px"
                ),

                spacing="5",
            ),

            padding="40px",
            background="#0d0d0f",
            margin_left=rx.cond(UIState.sidebar_open, "260px", "0px"),
            transition="margin-left 0.3s ease",
        ),

        
        width="100%",
        min_height="100vh",
    )
