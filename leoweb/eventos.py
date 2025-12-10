import reflex as rx
from .auth_state import AuthState, get_connection
from .sidebar import sidebar, sidebar_button
from .ui_state import UIState
import datetime

# --------------------------------------------------------
# OBTENER PRODUCTOS DESDE BD
# --------------------------------------------------------
def fetch_products():
    products = []
    try:
        conn = get_connection()

        cur = conn.cursor()
        cur.execute("SELECT id_producto, nombre, precio FROM menu WHERE estado = 'activo' ORDER BY id_producto;")
        rows = cur.fetchall()

        for row in rows:
            id_producto, nombre, precio = row
            products.append({
                "id": id_producto,
                "name": nombre,
                "price": float(precio)
            })


    except Exception as e:
        print("ERROR FETCH_PRODUCTS:", e)

    finally:
        try:
            conn.close()
        except:
            pass

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

    current_product: str = ""
    current_quantity: int = 1

    lineas_menu: list[dict] = []
    def nueva_linea_menu(self):
        self.lineas_menu.append({
            "producto": "",
            "cantidad": 1,
            "precio": 0
        })
    
    def set_linea_producto(self, index, nombre):
        self.lineas_menu[index]["producto"] = nombre
        for p in self.products:
            if p["name"] == nombre:
                self.lineas_menu[index]["precio"] = p["price"]
        self.update_total()
    
    def set_linea_cantidad(self, index, cantidad):
        try:
            n = int(cantidad)
            self.lineas_menu[index]["cantidad"] = max(1, n)
        except:
            self.lineas_menu[index]["cantidad"] = 1
        self.update_total()
    
    def eliminar_linea(self, index):
        self.lineas_menu.pop(index)
        self.update_total()
    

    def set_current_product(self, v):
        self.current_product = v

    def set_current_quantity(self, v):
        try:
            q = int(v)
            self.current_quantity = max(1, q)
        except:
            self.current_quantity = 1

    def add_selected_product(self):
        if not self.current_product:
            return

        # Encontrar producto en la lista
        for p in self.products:
            if p["name"] == self.current_product:
                self.add_producto(p["id"], p["name"], p["price"])
                self.current_product = ""
                self.current_quantity = 1
                return
    
    @rx.var
    def product_names(self) -> list[str]:
        return [p["name"] for p in self.products]

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

    # Fecha mínima
    @rx.var
    def fecha_minima(self) -> str:
        """Devuelve la fecha actual en formato YYYY-MM-DD para bloquear el calendario."""
        return datetime.date.today().strftime("%Y-%m-%d")

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
            l["cantidad"] * l["precio"] for l in self.lineas_menu
        )

    def save_menu(self):
        if not self.lineas_menu:
            return rx.toast.error("Agrega al menos un platillo.")

        self.productos_seleccionados = []
        for l in self.lineas_menu:
            if l["producto"] == "":
                return rx.toast.error("Completa todos los productos antes de guardar.")

            # Buscar id
            for p in self.products:
                if p["name"] == l["producto"]:
                    self.productos_seleccionados.append({
                        "id": p["id"],
                        "name": l["producto"],
                        "cantidad": l["cantidad"],
                        "precio": l["precio"]
                    })

        self.menu_modal_open = False
        rx.toast.success("Menú guardado!")

    @rx.var
    def lineas_subtotales(self) -> list[str]:
        arr = []
        for l in self.lineas_menu:
            try:
                arr.append(f"${(l['cantidad'] * l['precio']):.2f}")
            except:
                arr.append("$0.00")
        return arr


    # ---------------------------------------
    # BD: Guardar Evento
    # ---------------------------------------
    def submit_event(self, current_user):
         # ⚠ Validar usuario
        if not current_user:
            return rx.toast.error("Debes iniciar sesión.", position="bottom-right")

        # ⚠ Validar campos obligatorios
        if not self.fecha:
            return rx.toast.warning("Selecciona una fecha para el evento.", position="bottom-right")

        if not self.hora:
            return rx.toast.warning("Selecciona una hora para el evento.", position="bottom-right")

        if not self.ubicacion.strip():
            return rx.toast.warning("Escribe la ubicación del evento.", position="bottom-right")
        
        # 🟢 VALIDACIÓN NUEVA: Fecha pasada
        try:
            fecha_seleccionada = datetime.datetime.strptime(self.fecha, "%Y-%m-%d").date()
            if fecha_seleccionada < datetime.date.today():
                return rx.toast.error("No puedes solicitar un evento en una fecha pasada.", position="bottom-right")
        except ValueError:
            return rx.toast.error("Formato de fecha inválido.", position="bottom-right")

        # ⚠ Validar número de personas
        if self.cant_personas < 1:
            return rx.toast.error("La cantidad mínima es 1 persona.", position="bottom-right")

        # ⚠ Validar menú
        if not self.productos_seleccionados:
            return rx.toast.error("Agrega al menos un platillo al menú.", position="bottom-right")

        # ⚠ Validar total
        if self.total <= 0:
            return rx.toast.error("El costo del menú debe ser mayor a 0.", position="bottom-right")

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

            # Reset
            self.fecha = ""
            self.hora = ""
            self.ubicacion = ""
            self.cant_personas = 1
            self.productos_seleccionados = []
            self.total = 0.0
            return rx.toast.success("Evento guardado correctamente!")

        except Exception as e:
            print(f"Error al guardar evento: {e}")
            return rx.toast.error("Error al guardar evento")
        finally:
            conn.close()

def glass_card(*children):
    return rx.box(
        *children,
        margin_top="76px",
        width="700px",
        padding="40px",
        border_radius="20px",
        background="rgba(0,0,0,0.35)",
        backdrop_filter="blur(10px)",
        border="1px solid rgba(255,255,255,0.15)",
        box_shadow="0px 8px 25px rgba(0,0,0,0.4)",
    )


@rx.page(route="/eventos", on_load=EventState.on_load)
def eventos_page():
    _ = EventState.products   # fuerza a Reflex a registrar el state
    return rx.box(
        sidebar(active_item="eventos"),
        sidebar_button(),

        rx.center(
            glass_card(

                rx.heading(
                    "Solicita un evento a domicilio",
                    color="white",
                    size="6",
                    margin_bottom="25px",
                    text_align="center"
                ),

                # ----------------------
                # FILA 1: FECHA + HORA
                # ----------------------
                rx.hstack(
                    rx.vstack(
                        rx.text("Fecha", color="white", margin_bottom="5px"),
                        rx.input(
                            type="date",
                            value=EventState.fecha,
                            on_change=EventState.set_fecha,
                            min=EventState.fecha_minima,
                            size="3",
                            width="100%",
                            background="rgba(255,255,255,0.08)",
                            color="white",
                            border_radius="10px",
                            padding_left="10px",
                            style={"color-scheme": "dark"},
                        ),
                        spacing="1",
                        width="50%"
                    ),

                    rx.vstack(
                        rx.text("Hora", color="white", margin_bottom="5px"),
                        rx.input(
                            type="time",
                            value=EventState.hora,
                            on_change=EventState.set_hora,
                            size="3",
                            width="100%",
                            background="rgba(255,255,255,0.08)",
                            color="white",
                            border_radius="10px",
                            padding_left="10px",
                            style={"color-scheme": "dark"},
                        ),
                        spacing="1",
                        width="50%"
                    ),

                    spacing="4",
                    margin_bottom="20px"
                ),

                # ----------------------
                # FILA 2: UBICACIÓN + PERSONAS
                # ----------------------
                rx.hstack(
                    rx.vstack(
                        rx.text("Ubicación", color="white", margin_bottom="5px"),
                        rx.input(
                            placeholder="Dirección del evento",
                            value=EventState.ubicacion,
                            on_change=EventState.set_ubicacion,
                            size="3",
                            width="100%",
                            background="rgba(255,255,255,0.08)",
                            color="white",
                            border_radius="10px",
                            padding_left="10px",
                        ),
                        spacing="1",
                        width="70%"
                    ),

                    rx.vstack(
                        rx.text("Personas", color="white", margin_bottom="5px"),
                        rx.input(
                            type="number",
                            min=1,
                            value=EventState.cant_personas,
                            on_change=EventState.set_cant_personas,
                            size="3",
                            width="100%",
                            background="rgba(255,255,255,0.08)",
                            color="white",
                            border_radius="10px",
                            padding_left="10px",
                        ),
                        spacing="1",
                        width="30%"
                    ),

                    spacing="4",
                    margin_bottom="25px"
                ),

                # ----------------------
                # BOTÓN ABRIR MODAL MENÚ
                # ----------------------
                rx.button(
                    rx.hstack(
                        rx.text("Arma tu menú"),
                        rx.text(f"(${EventState.total:.2f})", opacity="0.8"),
                        spacing="2"
                    ),
                    on_click=EventState.toggle_menu_modal,
                    background_color="#047e00",
                    _hover={"background_color": "#006605"},
                    width="100%",
                    cursor="pointer",
                    margin_top="20px",
                    size="2",
                    border_radius="10px",
                    padding="10px",
                    margin_bottom="16px"
                ),

                # ----------------------
                # MODAL MENÚ (reemplazar)
                # ----------------------
                rx.dialog.root(
                    rx.dialog.content(
                        rx.vstack(

                            # HEADER
                            rx.hstack(
                                rx.dialog.title(
                                    rx.heading("Arma tu menú", size="6", color="white")
                                ),
                                rx.text(EventState.total_str, color="white", margin_left="auto"),
                                width="100%",
                                margin_bottom="20px"
                            ),

                            # BOTÓN AGREGAR PRODUCTO
                            rx.button(
                                "+ Agregar producto",
                                on_click=EventState.nueva_linea_menu,
                                color_scheme="blue",
                                width="100%",
                                cursor="pointer",
                                margin_bottom="15px"
                            ),

                            # LISTA DE LÍNEAS
                            rx.foreach(
                                EventState.lineas_menu,
                                lambda linea, i:
                                    rx.hstack(
                                        # SELECT PRODUCTOS: pasar la lista POSICIONALMENTE
                                        rx.select(
                                            EventState.product_names,            # <- items como primer arg
                                            value=linea["producto"],
                                            on_change=lambda v, idx=i: EventState.set_linea_producto(idx, v),
                                            placeholder="Selecciona platillo",
                                            width="45%",
                                        ),

                                        # CANTIDAD
                                        rx.input(
                                            type="number",
                                            min=1,
                                            value=linea["cantidad"],
                                            on_change=lambda v, idx=i: EventState.set_linea_cantidad(idx, v),
                                            width="80px",
                                        ),

                                        # SUBTOTAL (var que ya calculas)
                                        rx.text(
                                            EventState.lineas_subtotales[i],
                                            color="white",
                                            width="90px",
                                        ),

                                        # BORRAR (usa lambda con payload)
                                        rx.button(
                                            "Borrar",
                                            on_click=lambda _, idx=i: EventState.eliminar_linea(idx),
                                            background_color="#d00000",
                                            _hover={"background_color": "#b00000"},
                                            cursor="pointer",
                                        ),

                                        width="100%",
                                        spacing="3",
                                        margin_bottom="12px"
                                    )
                            ),

                            # GUARDAR
                            rx.button(
                                "Guardar menú",
                                on_click=EventState.save_menu,
                                background_color="#047e00",
                                _hover={"background_color": "#006605"},
                                cursor="pointer",
                                width="100%",
                                margin_top="15px"
                            ),

                        ),

                        background="#1a1a1c",
                        border_radius="15px",
                        width="650px",
                        padding="30px",
                    ),

                    open=EventState.menu_modal_open,
                    on_open_change=EventState.toggle_menu_modal,
                ),


                # ----------------------
                # BOTÓN FINAL
                # ----------------------
                rx.button(
                    "Solicitar evento",
                    on_click=lambda: EventState.submit_event(AuthState.current_user),
                    background_color="#ff0000",
                    _hover={"background_color": "#b00000"},
                    cursor="pointer",
                    border_radius="10px",
                    padding="10px",
                    transition= "all 0.2s ease-in-out",
                    width="100%",
                    size="3",
                    margin_top="20px"
                ),
            ),
            
            margin_left=rx.cond(UIState.sidebar_open, "260px", "0px"),
            transition="margin-left 0.3s ease",
        ),

        width="100%",
        min_height="100vh",
        background=(
        "linear-gradient(rgba(0,0,0,0.6), rgba(0,0,0,0.6)), "
        "url('https://images.unsplash.com/photo-1659345737306-7022e0687e0d?q=80&w=1631&auto=format&fit=crop&ixlib=rb-4.1.0&ixid=M3wxMjA3fDB8MHxwaG90by1wYWdlfHx8fGVufDB8fHx8fA%3D%3D')"
        ),
        background_size="cover",
        background_position="center",
    )
