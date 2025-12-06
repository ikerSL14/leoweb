import reflex as rx
import psycopg2

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
    error: str = ""
    logged_in: bool = False
    current_user: int | None = None
    rol: str = ""

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
                rx.toast.error("Correo no encontrado")
                return

            user_id, rol, stored_password = result

            if self.password != stored_password:
                rx.toast.error("Contraseña incorrecta")
                return
            
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

        finally:
            conn.close()


    def logout(self):
        self.logged_in = False
        self.current_user = None
        self.rol = ""

        # Redirección sin return
        return rx.redirect("/login")
