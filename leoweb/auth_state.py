import reflex as rx
import psycopg2
# 🟢 Añadir la importación del hash
from passlib.hash import pbkdf2_sha256 # <-- AGREGAR ESTA LÍNEA
from typing import ClassVar

def get_connection():
    return psycopg2.connect(
        dbname="leoweb",
        user="postgres",
        password="adminp",
        host="localhost",
        port="5432"
    )

class AuthState(rx.State):
    email: str = ""
    password: str = ""

    # 🟢 Variables para el Registro
    register_name: str = ""
    register_phone: str = ""
    register_email: str = ""
    register_password: str = ""
    register_confirm_password: str = ""

    # Variables de Sesión
    error: str = ""
    logged_in: bool = False
    current_user: int | None = None
    rol: str = ""

    # 🟢 Setters para Registro (NUEVOS)
    def set_register_name(self, value: str):
        self.register_name = value

    def set_register_phone(self, value: str):
        self.register_phone = value

    def set_register_email(self, value: str):
        self.register_email = value

    def set_register_password(self, value: str):
        self.register_password = value

    def set_register_confirm_password(self, value: str):
        self.register_confirm_password = value
    
    # ----------------------------------------------------
    # 🟢 FUNCIÓN DE REGISTRO (NUEVA)
    # ----------------------------------------------------
    def register(self):
        # 1. Validación de campos
        if not all([self.register_name, self.register_email, self.register_phone, self.register_password, self.register_confirm_password]):
            return rx.toast.error("Todos los campos son obligatorios.")

        if self.register_password != self.register_confirm_password:
            return rx.toast.error("Las contraseñas no coinciden.")
        
        # 2. Hashing de contraseña
        hashed_password = pbkdf2_sha256.hash(self.register_password)
        
        conn = None
        try:
            conn = get_connection()
            cur = conn.cursor()

            # 3. Verificar si el correo ya existe
            cur.execute("SELECT id_usuario FROM usuarios WHERE correo = %s", (self.register_email,))
            if cur.fetchone():
                return rx.toast.error("Este correo ya está registrado.")
            
            # 4. Inserción del nuevo usuario
            insert_query = """
                INSERT INTO usuarios (nombre, correo, telefono, rol, contrasena) 
                VALUES (%s, %s, %s, %s, %s) 
                RETURNING id_usuario;
            """
            # El rol siempre será 'usuario' para esta pantalla
            cur.execute(insert_query, (self.register_name, self.register_email, self.register_phone, "usuario", hashed_password))
            
            new_user_id = cur.fetchone()[0]
            conn.commit()

            # 5. Iniciar Sesión automáticamente
            self.logged_in = True
            self.current_user = new_user_id
            self.rol = "usuario"
            
            # 6. Limpiar campos de registro
            self.register_name = ""
            self.register_phone = ""
            self.register_email = ""
            self.register_password = ""
            self.register_confirm_password = ""
            
            rx.toast.success("Registro exitoso. ¡Bienvenido!")
            
            # 7. Redirigir a la página principal
            return rx.redirect("/")

        except Exception as e:
            if conn:
                conn.rollback()
            self.error = f"Error: {str(e)}"
            return rx.toast.error(f"Error de base de datos al registrar: {str(e)}")

        finally:
            if conn:
                conn.close()

    def login(self):
        try:
            conn = get_connection()
            cur = conn.cursor()

            query = """
                SELECT id_usuario, rol, contrasena 
                FROM usuarios 
                WHERE correo = %s
            """
            cur.execute(query, (self.email,))
            result = cur.fetchone()

            if not result:
                return rx.toast.error("Correo no encontrado")
                

            user_id, rol, stored_password = result

            if not pbkdf2_sha256.verify(self.password, stored_password):
                return rx.toast.error("Contraseña incorrecta")
                
            
            # Guardar sesión
            self.logged_in = True
            self.current_user = user_id
            self.rol = rol

            # ESTO ES IMPORTANTE:
            # ---- RETURN -------
            if rol == "usuario":
                return rx.redirect("/")
            else:
                return rx.redirect("/dashboard")

        except Exception as e:
            self.error = f"Error: {str(e)}"
            # 🟢 MOSTRAR EL ERROR DE LA DB AL USUARIO
            return rx.toast.error(f"Error de conexión o consulta: {str(e)}")

        finally:
            conn.close()


    def logout(self):
        self.logged_in = False
        self.current_user = None
        self.rol = ""

        # Redirección sin return
        return rx.redirect("/login")
