import reflex as rx
import os
import shutil # Para borrar carpetas
from .adminsidebar import admin_sidebar, admin_sidebar_button
from .aui_state import AUIState
from ..auth_state import AuthState, get_connection
from typing import List, Dict, Any
from pathlib import Path # Para manejar rutas de archivos

# ----------------------------------------------------------------------------
# STATE: PRODUCTOS
# ----------------------------------------------------------------------------
class AdminProductState(rx.State):
    all_products: List[Dict[str, Any]] = [] # Lista maestra
    search_query: str = "" # Texto del buscador

    # --- NUEVO PRODUCTO ---
    show_add_modal: bool = False
    
    # Campos del formulario
    new_name: str = ""
    new_category: str = "Hamburguesas" # Valor por defecto
    new_desc: str = ""
    new_price: str = "" # Usamos string para el input, luego convertimos
    
    # Categorías disponibles (Hardcoded como pediste)
    categories: list[str] = [
        "Hamburguesas", "Pizzas", "Ensaladas", "Snacks", 
        "Postres", "Platillos Fuertes", "Bebidas"
    ]

    # --- EDITAR PRODUCTO ---
    show_edit_modal: bool = False
    
    # Variables del producto actualmente seleccionado para edición
    edit_id: int = -1
    edit_original_img_file: str = "" # Nombre del archivo de imagen en la BD
    edit_original_img_url: str = "/favicon.ico" # URL actual del producto para preview

    # --- ELIMINAR PRODUCTO CON CONFIRMACIÓN ---
    show_delete_confirm: bool = False
    delete_id: int = -1
    delete_name: str = ""

    # --------------------------------------------------
    # NUEVOS MÉTODOS PARA EL CICLO DE EDICIÓN
    # --------------------------------------------------
    
    def start_edit(self, 
                   product_id: int,
                   nombre: str,
                   categoria: str,
                   descripcion: str,
                   precio: float,
                   img_file: str,
                   img_url: str):
        """Carga los datos del producto seleccionado en el estado y abre el modal."""
        self.edit_id = product_id
        self.new_name = nombre
        self.new_category = categoria
        self.new_desc = descripcion
        self.new_price = f"{precio:.2f}" # Formato a string con 2 decimales
        self.edit_original_img_file = img_file
        
          # CORRECCIÓN: Construye la URL correctamente
        if img_file:
            # Usa la ruta que mencionaste: assets/img/(id_producto)/
            self.edit_original_img_url = f"/imgs/{self.edit_id}/{img_file}"
        else:
            self.edit_original_img_url = "/favicon.ico"  # O un placeholder vacío

        self.show_edit_modal = True

    def toggle_edit_modal(self):
        """Cierra el modal de edición y resetea las variables de edición."""
        self.show_edit_modal = not self.show_edit_modal
        
        # Resetear campos al cerrar
        if not self.show_edit_modal:
            self.edit_id = -1
            self.edit_original_img_file = ""
            self.edit_original_img_url = "/favicon.ico"
            # También reseteamos los campos de formulario 'new_'
            self.new_name = ""
            self.new_category = "Hamburguesas"
            self.new_desc = ""
            self.new_price = ""
            # Además, limpia los archivos seleccionados del upload
            return rx.clear_selected_files("upload_product_img")
        
    # --- FUNCIÓN DE ACTUALIZAR PRODUCTO (CON IMAGEN CONDICIONAL) ---
    async def handle_update(self, files: List[rx.UploadFile]):
        """Maneja la actualización del registro en BD, incluyendo la imagen condicional."""
        
        # 1. Validaciones básicas
        if not self.new_name or not self.new_desc or not self.new_price:
            return rx.toast.error("Por favor completa todos los campos de texto.")
        
        try:
            price_float = float(self.new_price)
        except ValueError:
            return rx.toast.error("El precio debe ser un número válido.")

        conn = None
        try:
            conn = get_connection()
            cur = conn.cursor()
            
            new_filename = self.edit_original_img_file # Por defecto, usa el nombre de archivo existente
            
            # --- Lógica de la imagen ---
            if files:
                # Se subió una NUEVA imagen
                file = files[0]
                new_filename = file.filename
                
                # 2. Guardar el nuevo archivo físico en assets/imgs/{id}/
                upload_data = await file.read()
                target_dir = Path(f"assets/imgs/{self.edit_id}")
                target_dir.mkdir(parents=True, exist_ok=True) # Asegura que el directorio exista
                
                # Opcional: Borrar el archivo anterior si existe (y si tiene un nombre)
                if self.edit_original_img_file:
                    old_path = target_dir / self.edit_original_img_file
                    if old_path.exists():
                        old_path.unlink() # Borra el archivo anterior
                        
                # Guardar la nueva imagen
                target_path = target_dir / new_filename
                with open(target_path, "wb") as f:
                    f.write(upload_data)
            
            # 3. Actualizar el registro en la BD
            cur.execute("""
                UPDATE menu 
                SET nombre = %s, descripcion = %s, categoria = %s, precio = %s, img = %s
                WHERE id_producto = %s;
            """, (self.new_name, self.new_desc, self.new_category, price_float, new_filename, self.edit_id))
            
            conn.commit()

            # 4. Cerrar modal y recargar lista
            self.toggle_edit_modal()
            self.load_products()
            return rx.toast.success(f"Producto '{self.new_name}' actualizado correctamente.")

        except Exception as e:
            if conn:
                conn.rollback()
            print(f"Error actualizando producto: {e}")
            return rx.toast.error(f"Error al actualizar: {str(e)}")
        finally:
            if conn:
                conn.close()

    def start_delete(self, id_producto: int, nombre: str):
        """Prepara el modal de confirmación de borrado (soft delete)."""
        self.delete_id = id_producto
        self.delete_name = nombre
        self.show_delete_confirm = True

    def cancel_delete(self):
        """Cierra el modal de confirmación."""
        self.delete_id = -1
        self.delete_name = ""
        self.show_delete_confirm = False
        
    def final_delete_product(self):
        """Llama a la función de soft-delete real y cierra el modal."""
        # Retorna una lista de Event Handlers/Events para ejecución secuencial
        return [
            AdminProductState.delete_product(self.delete_id), 
            AdminProductState.cancel_delete
        ]

    def toggle_add_modal(self):
        self.show_add_modal = not self.show_add_modal
        # Resetear campos al cerrar
        if not self.show_add_modal:
            self.new_name = ""
            self.new_category = "Hamburguesas"
            self.new_desc = ""
            self.new_price = ""

    # Setters para los campos
    def set_new_name(self, v): self.new_name = v
    def set_new_category(self, v): self.new_category = v
    def set_new_desc(self, v): self.new_desc = v
    def set_new_price(self, v): self.new_price = v

    # --- FUNCIÓN DE AGREGAR PRODUCTO (CON IMAGEN) ---
    async def handle_upload(self, files: List[rx.UploadFile]):
        """Maneja la subida del archivo y la creación del registro en BD."""
        
        # 1. Validaciones básicas
        if not self.new_name or not self.new_desc or not self.new_price:
            return rx.toast.error("Por favor completa todos los campos de texto.")
        
        if not files:
            return rx.toast.error("Debes seleccionar una imagen.")

        try:
            price_float = float(self.new_price)
        except ValueError:
            return rx.toast.error("El precio debe ser un número válido.")

        conn = None
        try:
            conn = get_connection()
            cur = conn.cursor()

            # 2. Obtener el archivo (solo el primero)
            file = files[0]
            filename = file.filename

            # 3. Insertar en la BD primero (para obtener ID)
            # Guardamos el nombre del archivo temporalmente
            cur.execute("""
                INSERT INTO menu (nombre, descripcion, categoria, precio, img, estado)
                VALUES (%s, %s, %s, %s, %s, 'activo')
                RETURNING id_producto;
            """, (self.new_name, self.new_desc, self.new_category, price_float, filename))
            
            new_id = cur.fetchone()[0]
            conn.commit()

            # 4. Guardar el archivo físico en assets/imgs/{id}/
            upload_data = await file.read()
            
            # Definir ruta de destino
            # assets/ está en la raíz del proyecto
            target_dir = Path(f"assets/imgs/{new_id}")
            target_dir.mkdir(parents=True, exist_ok=True) # Crear carpeta si no existe
            
            target_path = target_dir / filename
            
            with open(target_path, "wb") as f:
                f.write(upload_data)

            # 5. Cerrar modal y recargar lista
            self.toggle_add_modal()
            self.load_products()
            return rx.toast.success("Producto agregado correctamente.")

        except Exception as e:
            if conn:
                conn.rollback()
            print(f"Error agregando producto: {e}")
            return rx.toast.error(f"Error al agregar: {str(e)}")
        finally:
            if conn:
                conn.close()

    # --- CARGA Y SEGURIDAD ---
    async def on_load(self):
        auth_state = await self.get_state(AuthState)
        
        # 1. Seguridad
        if not auth_state.logged_in:
            return rx.redirect("/login")
        if auth_state.rol != "admin":
            return [
                rx.toast.error("Acceso denegado."),
                rx.redirect("/") 
            ]
        
        # 2. Cargar datos
        self.load_products()

    def load_products(self):
        """Obtiene todos los productos de la BD."""
        conn = None
        try:
            conn = get_connection()
            cur = conn.cursor()
            # Seleccionamos también el ID para poder borrar
            cur.execute("SELECT id_producto, nombre, descripcion, categoria, precio, img, estado FROM menu ORDER BY estado ASC, id_producto DESC;")
            rows = cur.fetchall()
            
            products = []
            for row in rows:
                p_id, nombre, desc, cat, precio, img, estado = row
                
                # Ruta web para mostrar la imagen (/imgs/...)
                # Si no hay imagen, usar placeholder
                img_url = f"/imgs/{p_id}/{img}" if img else "/favicon.ico"

                products.append({
                    "id": p_id,
                    "nombre": nombre,
                    "descripcion": desc,
                    "categoria": cat,
                    "precio": float(precio),
                    "img_url": img_url,
                    "img_file": img, # Guardamos nombre archivo para referencia
                    "estado": estado
                })
            
            self.all_products = products
            
        except Exception as e:
            print(f"Error cargando productos: {e}")
        finally:
            if conn:
                conn.close()

    # --- BÚSQUEDA ---
    def set_search(self, query: str):
        self.search_query = query

    @rx.var
    def filtered_products(self) -> List[Dict[str, Any]]:
        """Filtra la lista maestra según el texto de búsqueda."""
        if not self.search_query:
            return self.all_products
        
        return [
            p for p in self.all_products 
            if self.search_query.lower() in p["nombre"].lower()
        ]

    # --- SOFT DELETE (DESACTIVAR) ---
    def delete_product(self, id_producto: int):
        conn = None
        try:
            conn = get_connection()
            cur = conn.cursor()

            # 1. SOFT DELETE: Actualizar estado a 'inactivo'
            cur.execute("UPDATE menu SET estado = 'inactivo' WHERE id_producto = %s;", (id_producto,))
            conn.commit()

            # Nota: No se borra la carpeta de imágenes (assets/imgs/{id})
            # para que el producto pueda ser restaurado.

            # 2. Recargar lista
            self.load_products()
            
            return rx.toast.success("Producto desactivado correctamente.")

        except Exception as e:
            if conn:
                conn.rollback()
            print(f"Error DB al desactivar: {e}")
            return rx.toast.error(f"No se pudo desactivar: {str(e)}")
        finally:
            if conn:
                conn.close()
    
    # --- RESTABLECER PRODUCTO (ACTIVAR) ---
    def restore_product(self, id_producto: int):
        conn = None
        try:
            conn = get_connection()
            cur = conn.cursor()
            
            # 1. Actualizar estado a 'activo'
            cur.execute("UPDATE menu SET estado = 'activo' WHERE id_producto = %s;", (id_producto,))
            conn.commit()
            
            # 2. Recargar lista
            self.load_products()
            
            return rx.toast.success("Producto restablecido correctamente.")
                
        except Exception as e:
            if conn:
                conn.rollback()
            print(f"Error DB al restablecer: {e}")
            return rx.toast.error(f"No se pudo restablecer: {str(e)}")
        finally:
            if conn:
                conn.close()


# ----------------------------------------------------------------------------
# COMPONENTES UI
# ----------------------------------------------------------------------------

# ----------------------------------------------------------------------------
# COMPONENTE: MODAL AGREGAR PRODUCTO
# ----------------------------------------------------------------------------
def add_product_modal():
    # El diseño es el original que proporcionaste
    return rx.dialog.root(
        rx.dialog.content(
            rx.vstack(
                rx.heading("Nuevo Producto", size="6", margin_bottom="20px", color="white"),
                
                # FILA 1: Nombre + Categoría
                rx.hstack(
                    rx.vstack(
                        rx.text("Nombre", font_weight="bold", size="2", color="white"),
                        rx.input(
                            placeholder="Nombre del platillo",
                            value=AdminProductState.new_name,
                            on_change=AdminProductState.set_new_name,
                            width="100%",
                            color="white",
                            background="#0d0d0f",
                            border="1px solid rgba(255,255,255,0.1)"
                        ),
                        width="60%",
                        align_items="start"
                    ),
                    rx.vstack(
                        rx.text("Categoría", font_weight="bold", size="2", color="white"),
                        rx.select(
                            AdminProductState.categories,
                            value=AdminProductState.new_category,
                            on_change=AdminProductState.set_new_category,
                            width="100%",
                            color="white",
                            background="#0d0d0f",
                            border="1px solid rgba(255,255,255,0.1)"
                        ),
                        width="40%",
                        align_items="start"
                    ),
                    width="100%",
                    spacing="4",
                    margin_bottom="15px"
                ),
                
                # FILA 2: Descripción + Precio
                rx.hstack(
                    rx.vstack(
                        rx.text("Descripción", font_weight="bold", size="2", color="white"),
                        rx.text_area(
                            placeholder="Ingredientes, detalles...",
                            value=AdminProductState.new_desc,
                            on_change=AdminProductState.set_new_desc,
                            width="100%",
                            height="80px",
                            color="white",
                            background="#0d0d0f",
                            border="1px solid rgba(255,255,255,0.1)"
                        ),
                        width="70%",
                        align_items="start"
                    ),
                    rx.vstack(
                        rx.text("Precio ($)", font_weight="bold", size="2", color="white"),
                        rx.input(
                            placeholder="0.00",
                            type="number", 
                            value=AdminProductState.new_price,
                            on_change=AdminProductState.set_new_price,
                            width="100%",
                            color="white",
                            background="#0d0d0f",
                            border="1px solid rgba(255,255,255,0.1)"
                        ),
                        width="30%",
                        align_items="start"
                    ),
                    width="100%",
                    spacing="4",
                    align_items="start", 
                    margin_bottom="15px"
                ),
                
                # FILA 3: Imagen (Upload)
                rx.vstack(
                    rx.text("Fotografía", font_weight="bold", size="2", color="white"),
                    rx.upload(
                        rx.vstack(
                            rx.button(
                                "Seleccionar imagen", 
                                color="white", 
                                bg="slate.900", 
                                border="1px solid slate.500"
                            ),
                            rx.text(
                                "Arrastra o haz click", 
                                font_size="sm", 
                                color="gray"
                            ),
                            align="center",
                            spacing="2"
                        ),
                        id="upload_product_img",
                        border="1px dotted rgb(107,99,246)",
                        padding="20px",
                        width="100%",
                        accept={
                            "image/png": [".png"], 
                            "image/jpeg": [".jpg", ".jpeg"]
                        },
                        max_files=1
                    ),
                    # Mostrar archivos seleccionados (nombre)
                    rx.foreach(
                        rx.selected_files("upload_product_img"), 
                        lambda file_name: rx.text(file_name, color="#4caf50", font_size="sm")
                    ),
                    width="100%",
                    margin_bottom="25px",
                    align_items="start"
                ),
                
                # BOTONES
                rx.hstack(
                    rx.button(
                        "Cancelar", 
                        on_click=AdminProductState.toggle_add_modal,
                        variant="soft", 
                        color_scheme="gray"
                    ),
                    rx.button(
                        "Insertar Producto",
                        on_click=lambda: AdminProductState.handle_upload(
                            rx.upload_files(upload_id="upload_product_img")
                        ),
                        background="red", 
                        color="white",
                        _hover={"background": "#b30000"}
                    ),
                    spacing="3",
                    justify="end",
                    width="100%"
                )
            ),
            background="#1a1a1c",
            border_radius="15px",
            padding="30px",
            width="600px"
        ),
        open=AdminProductState.show_add_modal,
        on_open_change=AdminProductState.toggle_add_modal,
    )

# ----------------------------------------------------------------------------
# COMPONENTE: MODAL EDITAR PRODUCTO
# ----------------------------------------------------------------------------
def edit_product_modal():
    
    selected_files = rx.selected_files("upload_product_img")

    has_selected_files = selected_files.length() > 0
    
    # CORRECCIÓN 2: Fuente de imagen mejorada
    current_image_src = rx.cond(
        has_selected_files,
        # 🟡 NO PODEMOS MOSTRAR EL ARCHIVO, PERO SÍ UN PLACEHOLDER
        "/placeholder_new_image.png",   # tú puedes elegir un ícono de tu proyecto
        # Si no se seleccionó archivo → mostrar la imagen actual del producto
        AdminProductState.edit_original_img_url
    )
    # CORRECCIÓN 3: Condición para mostrar imagen - más precisa
    is_image_available = (has_selected_files) | (AdminProductState.edit_original_img_url != "/favicon.ico")
    
    # CORRECCIÓN 4: Añade un componente para debug (opcional, quítalo después)
    debug_info = rx.text(
        f"ID: {AdminProductState.edit_id} | URL: {AdminProductState.edit_original_img_url} | Files: {selected_files}",
        color="red",
        font_size="xs"
    )

    return rx.dialog.root(
        rx.dialog.content(
            rx.vstack(
                # CAMBIO 1: Título
                rx.heading("Editar Producto", size="6", margin_bottom="20px", color="white"),
                
                # FILA 1: Nombre + Categoría (Igual, usa new_name/category/setters)
                rx.hstack(
                    rx.vstack(
                        rx.text("Nombre", font_weight="bold", size="2", color="white"),
                        rx.input(
                            placeholder="Nombre del platillo",
                            value=AdminProductState.new_name,
                            on_change=AdminProductState.set_new_name,
                            width="100%",
                            color="white",
                            background="#0d0d0f",
                            border="1px solid rgba(255,255,255,0.1)"
                        ),
                        width="60%",
                        align_items="start"
                    ),
                    rx.vstack(
                        rx.text("Categoría", font_weight="bold", size="2", color="white"),
                        rx.select(
                            AdminProductState.categories,
                            value=AdminProductState.new_category,
                            on_change=AdminProductState.set_new_category,
                            width="100%",
                            color="white",
                            background="#0d0d0f",
                            border="1px solid rgba(255,255,255,0.1)"
                        ),
                        width="40%",
                        align_items="start"
                    ),
                    width="100%",
                    spacing="4",
                    margin_bottom="15px"
                ),
                
                # FILA 2: Descripción + Precio (Igual, usa new_desc/price/setters)
                rx.hstack(
                    rx.vstack(
                        rx.text("Descripción", font_weight="bold", size="2", color="white"),
                        rx.text_area(
                            placeholder="Ingredientes, detalles...",
                            value=AdminProductState.new_desc,
                            on_change=AdminProductState.set_new_desc,
                            width="100%",
                            height="80px",
                            color="white",
                            background="#0d0d0f",
                            border="1px solid rgba(255,255,255,0.1)"
                        ),
                        width="70%",
                        align_items="start"
                    ),
                    rx.vstack(
                        rx.text("Precio ($)", font_weight="bold", size="2", color="white"),
                        rx.input(
                            placeholder="0.00",
                            type="number", 
                            value=AdminProductState.new_price,
                            on_change=AdminProductState.set_new_price,
                            width="100%",
                            color="white",
                            background="#0d0d0f",
                            border="1px solid rgba(255,255,255,0.1)"
                        ),
                        width="30%",
                        align_items="start"
                    ),
                    width="100%",
                    spacing="4",
                    align_items="start", 
                    margin_bottom="15px"
                ),
                
                # FILA 3: Imagen (Upload + Preview mejorado para edición)
                rx.vstack(
                    rx.text("Fotografía (Opcional)", font_weight="bold", size="2", color="white"),
                    #debug_info,
                    rx.hstack(
                        # 1. Componente de Carga (Botón) - ID debe coincidir
                        rx.upload(
                            rx.button(
                                "Seleccionar imagen nueva", 
                                color="white", 
                                bg="slate.900", 
                                border="1px solid slate.500"
                            ),
                            id="upload_product_img", # Debe ser el mismo ID que en el modal de añadir
                            border="1px dotted rgb(107,99,246)",
                            padding="20px",
                            width="100%",
                            accept={"image/png": [".png"], "image/jpeg": [".jpg", ".jpeg"]},
                            max_files=1
                        ),
                        
                        # 2. Recuadro de PREVIEW de Imagen
                        rx.box(
                            rx.cond(
                                # Usamos la variable is_image_available para la condición
                                has_selected_files,
                                # Si hay nueva imagen seleccionada → mostrar placeholder elegante
                                rx.box(
                                    rx.text(
                                        "Nueva imagen seleccionada",
                                        color="#4caf50",
                                        font_weight="bold",
                                        size="3",
                                    ),
                                    width="100%",
                                    height="100%",
                                    bg="#1f1f22",
                                    border="1px dashed #4caf50",
                                    border_radius="8px",
                                    display="flex",
                                    align_items="center",
                                    justify_content="center"
                                ),
                                
                                # Rama True: Mostrar imagen
                                rx.image(
                                    src=current_image_src, # Usamos la URL calculada
                                    width="100%",
                                    height="100%",
                                    object_fit="cover",
                                    border_radius="8px"
                                ),
                                
                                
                            ),
                            width="100%", # Ocupa el 100% de su espacio
                            height="100px", 
                            border="1px solid rgba(255,255,255,0.1)",
                            border_radius="8px",
                            background="#0d0d0f",
                            overflow="hidden"
                        ),
                        
                        width="100%",
                        spacing="4",
                        align_items="center"
                    ),
                    
                    # 3. Mostrar archivos seleccionados (nombre)
                    # Muestra el nombre del nuevo archivo si se seleccionó, si no, se queda vacío.
                    rx.foreach(
                        rx.selected_files("upload_product_img"), 
                        lambda file_name: rx.text("Nuevo archivo: " + file_name, color="#FFA500", font_size="sm", margin_top="5px")
                    ),
                    
                    # Mostrar el nombre del archivo original si no se ha seleccionado uno nuevo
                    rx.cond(
                        ~rx.selected_files("upload_product_img"), # SI NO hay archivos seleccionados
                        rx.cond(
                            AdminProductState.edit_original_img_file, # Y SI hay un archivo original
                            rx.text("Archivo actual: " + AdminProductState.edit_original_img_file, color="gray", font_size="sm", margin_top="5px"),
                            rx.text("No hay imagen cargada actualmente.", color="gray", font_size="sm", margin_top="5px")
                        )
                    ),
                    
                    width="100%",
                    margin_bottom="25px",
                    align_items="start"
                ),
                
                # BOTONES
                rx.hstack(
                    rx.button(
                        "Cancelar", 
                        on_click=AdminProductState.toggle_edit_modal, # CAMBIO 2: Toggle del modal de edición
                        variant="soft", 
                        color_scheme="gray"
                    ),
                    rx.button(
                        "Guardar Cambios", # CAMBIO 3: Texto del botón
                        # CAMBIO 4: Llama al nuevo handler de actualización
                        on_click=lambda: AdminProductState.handle_update(
                            rx.upload_files(upload_id="upload_product_img")
                        ),
                        background="orange", # Un color diferente para distinguirlo
                        color="white",
                        _hover={"background": "#cc8400"}
                    ),
                    spacing="3",
                    justify="end",
                    width="100%"
                )
            ),
            background="#1a1a1c",
            border_radius="15px",
            padding="30px",
            width="600px"
        ),
        # CAMBIO 5: Control del modal de edición
        open=AdminProductState.show_edit_modal,
        on_open_change=AdminProductState.toggle_edit_modal,
    )

# ----------------------------------------------------------------------------
# COMPONENTE: MODAL DE CONFIRMACIÓN DE BORRADO (SOFT DELETE)
# ----------------------------------------------------------------------------
def delete_confirm_modal():
    return rx.dialog.root(
        rx.dialog.content(
            rx.vstack(
                rx.icon("alert-octagon", size=40, color="#ffc107", margin="0 auto", margin_bottom="10px"),
                rx.dialog.title("Confirmar Desactivación", color="white", margin="0 auto"),
                rx.text(
                    rx.text("¿Estás seguro que deseas ", color="white"),
                    rx.text("DESACTIVAR ", font_weight="bold", color="#ffc107"),
                    rx.text("el producto ", color="white"),
                    rx.text(AdminProductState.delete_name, font_weight="bold", color="yellow"),
                    rx.text("? Se moverá a la lista de inactivos.", color="white"),
                    margin="0 auto",
                    margin_bottom="20px",
                    text_align="center"
                ),
                rx.hstack(
                    rx.button(
                        "Cancelar", 
                        on_click=AdminProductState.cancel_delete,
                        variant="soft", 
                        color_scheme="gray"
                    ),
                    rx.button(
                        "Desactivar", 
                        on_click=AdminProductState.final_delete_product, # Llama al Soft Delete
                        background="#d00000", 
                        color="white",
                        _hover={"background": "#b00000"}
                    ),
                    spacing="3",
                    justify="end",
                    width="100%"
                )
            ),
            background="#1a1a1c",
            border_radius="15px",
            padding="30px",
            width="400px"
        ),
        open=AdminProductState.show_delete_confirm,
        on_open_change=AdminProductState.cancel_delete,
    )

# ----------------------------------------------------------------------------
# COMPONENTE: CARD DEL PRODUCTO (CON LÓGICA DE ESTADO)
# ----------------------------------------------------------------------------
def admin_product_card(product: Dict[str, Any]):
    """Tarjeta horizontal para administración de productos, adaptada para estado 'activo'/'inactivo'."""
    # 🟢 Lógica para determinar el estado
    is_inactive = product["estado"] == "inactivo"
    
    return rx.box(
        rx.hstack(
            # 1. IMAGEN (Izquierda)
            rx.image(
                src=product["img_url"],
                width="140px",
                height="100%",
                object_fit="cover",
                border_radius="10px 0 0 10px",
                # 🟢 Estilo para inactivo
                style=rx.cond(is_inactive, {"opacity": 0.4}, {})
            ),
            
            # 2. INFO (Derecha)
            rx.vstack(
                # Encabezado: Nombre y Badge
                rx.hstack(
                    rx.vstack(
                        rx.text(
                            product["nombre"], 
                            color=rx.cond(is_inactive, "#666", "white"), # 🟢 Color atenuado si es inactivo
                            font_weight="bold", 
                            font_size="lg",
                        ),
                        
                        align_items="start",
                        width="100%"
                    ),

                    # 🟢 Mostrar etiqueta "INACTIVO" o la Categoría
                    rx.cond(
                        is_inactive,
                        rx.badge("ELIMINADO", color_scheme="red", variant="outline", margin_left="10px"),
                        rx.badge(product["categoria"], color_scheme="tomato", variant="solid"),
                    ),
                    width="100%",
                    justify="between",
                    align="start"
                ),
                
                # Descripción
                rx.text(
                    product["descripcion"],
                    color="#aaa",
                    font_size="sm",
                    no_of_lines=2, 
                ),
                
                
                
                # Precio y Botones (Abajo)
                rx.hstack(
                    rx.text(
                        f"${product['precio']:.2f}",
                        color="#4caf50",
                        font_weight="bold",
                        font_size="lg"
                    ),

                    # --- BOTONES DE ACCIÓN (CONDICIONAL) ---
                    rx.hstack(
                        rx.cond(
                            is_inactive,

                            # Rama 1: INACTIVO → Reestablecer
                            rx.hstack(
                                rx.button(
                                    rx.icon("rotate-ccw", size=16),
                                    "Reestablecer",
                                    on_click=lambda: AdminProductState.restore_product(product["id"]),
                                    color_scheme="green",
                                    size="2",
                                    cursor="pointer"
                                ),
                                spacing="3"
                            ),

                            # Rama 2: ACTIVO → Editar y Desactivar
                            rx.hstack(
                                rx.icon(
                                    "pencil",
                                    color="white",
                                    size=20,
                                    cursor="pointer",
                                    _hover={"color": "blue"},
                                    on_click=lambda: AdminProductState.start_edit(
                                        product["id"],
                                        product["nombre"],
                                        product["categoria"],
                                        product["descripcion"],
                                        product["precio"],
                                        product["img_file"],
                                        product["img_url"]
                                    )
                                ),
                                rx.icon(
                                    "trash-2",
                                    color="white",
                                    size=20,
                                    cursor="pointer",
                                    _hover={"color": "red"},
                                    on_click=lambda: AdminProductState.start_delete(product["id"], product["nombre"])
                                ),
                                spacing="3"
                            )
                        ),
                        background=rx.cond(is_inactive, "transparent", "rgba(255,255,255,0.1)"),
                        padding="8px",
                        border_radius="8px"
                    ),

                    width="100%",
                    justify="between"
                ),
                
                width="100%",
                height="100%",
                padding="15px",
                justify="end",
                align_items="start"
            ),
            
            height="100%",
            width="100%",
            spacing="0"
        ),
        
        height="150px", 
        width="100%",
        # 🟢 Estilos condicionales
        background=rx.cond(is_inactive, "#111113", "#1a1a1c"), 
        border_radius="10px",
        border=rx.cond(is_inactive, "1px solid rgba(255,0,0,0.2)", "1px solid rgba(255,255,255,0.05)"),
        box_shadow="0 4px 6px rgba(0,0,0,0.2)",
        _hover={"border_color": rx.cond(is_inactive, "rgba(255,0,0,0.5)", "rgba(255,255,255,0.2)")}
    )

# ----------------------------------------------------------------------------
# PÁGINA PRINCIPAL
# ----------------------------------------------------------------------------
@rx.page(route="/admin/productos", on_load=AdminProductState.on_load)
def adm_productos_page():
    return rx.box(
        admin_sidebar(active_item="productos"),
        admin_sidebar_button(),
        
        rx.box(
            rx.vstack(
                rx.heading("Gestión de Productos", color="white", size="7", margin_bottom="20px"),
                
                # --- BARRA SUPERIOR (Agregar + Buscar) ---
                rx.hstack(
                    rx.button(
                        "+ Agregar Producto",
                        background="red",
                        color="white",
                        _hover={"background": "#b30000"},
                        cursor="pointer",
                        on_click=AdminProductState.toggle_add_modal
                    ),
                    # 🟢 Nueva implementación usando rx.input (o rx.input.text)
                    rx.box(
                        rx.hstack(
                            rx.icon("search", size=16, color="#666", margin_left="10px"),
                            rx.input(
                                placeholder="Buscar producto...",
                                value=AdminProductState.search_query,
                                on_change=AdminProductState.set_search,
                                width="100%",
                                background="transparent",
                                color="white",
                                border="none",
                                outline="none",
                                padding_left="0"  # Asegurar que el input empiece justo después del ícono
                            ),
                            align_items="center",
                            width="100%",
                            spacing="2" # Espacio entre el ícono y el input
                        ),
                        width="300px",
                        border_radius="8px",
                        background="#1a1a1c",
                        border="1px solid rgba(255,255,255,0.1)",
                        color="white",
                        padding_right="10px"
                    ),
                    width="100%",
                    justify="between",
                    margin_bottom="30px"
                ),
                
                # --- LISTADO DE PRODUCTOS ---
                rx.cond(
                    AdminProductState.filtered_products,
                    rx.grid(
                        rx.foreach(
                            AdminProductState.filtered_products,
                            admin_product_card
                        ),
                        columns="2", 
                        spacing="4",
                        width="100%"
                    ),
                    # Estado vacío
                    rx.center(
                        rx.text("No se encontraron productos.", color="#666"),
                        width="100%",
                        padding="40px"
                    )
                ),
                
                align_items="start",
                width="100%",
                max_width="1200px",
                margin_x="auto",
            ),
            
            # 🟢 Modales incluidos
            edit_product_modal(),
            add_product_modal(),
            delete_confirm_modal(),
            
            padding="40px",
            padding_top="80px",
            margin_left=rx.cond(AUIState.sidebar_open, "260px", "0px"),
            transition="margin-left 0.3s ease",
            min_height="100vh",
            background="#0d0d0f"
        ),
        
        width="100%",
        min_height="100vh",
        background="#0d0d0f"
    )