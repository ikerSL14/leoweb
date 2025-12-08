# insert_user.py

from passlib.hash import pbkdf2_sha256
import psycopg2

# --- 1. DATOS DE CONEXIÓN (usa tu get_connection) ---
DB_NAME = "leoweb"
DB_USER = "postgres"
DB_PASSWORD = "adminp"
DB_HOST = "localhost"
DB_PORT = "5432"

# --- 2. DATOS DEL USUARIO DE PRUEBA ---
EMAIL = "prueba@leoweb.com"
PASSWORD = "123456"
NOMBRE = "Usuario Prueba"
TELEFONO = "5551234567"
ROL = "usuario" # O "admin" si quieres probar el dashboard

def create_hashed_user():
    """Genera el hash e inserta/actualiza el usuario en la DB."""
    
    # Generar el hash de la contraseña
    hashed_password = pbkdf2_sha256.hash(PASSWORD)
    print(f"✅ Hash generado: {hashed_password[:30]}...")
    
    conn = None
    try:
        # Conectar a la base de datos
        conn = psycopg2.connect(
            dbname=DB_NAME,
            user=DB_USER,
            password=DB_PASSWORD,
            host=DB_HOST,
            port=DB_PORT
        )
        cur = conn.cursor()
        
        # Intentar seleccionar el usuario por email
        cur.execute("SELECT id_usuario FROM usuarios WHERE correo = %s;", (EMAIL,))
        user_exists = cur.fetchone()

        if user_exists:
            # Si el usuario existe, actualiza su contraseña y otros campos
            query = """
                UPDATE usuarios 
                SET nombre = %s, contrasena = %s, telefono = %s, rol = %s
                WHERE correo = %s;
            """
            cur.execute(query, (NOMBRE, hashed_password, TELEFONO, ROL, EMAIL))
            print(f"🔄 Usuario '{EMAIL}' actualizado con la nueva contraseña hasheada.")
        else:
            # Si el usuario no existe, inserta uno nuevo
            query = """
                INSERT INTO usuarios (nombre, correo, telefono, contrasena, rol)
                VALUES (%s, %s, %s, %s, %s);
            """
            cur.execute(query, (NOMBRE, EMAIL, TELEFONO, hashed_password, ROL))
            print(f"➕ Nuevo usuario '{EMAIL}' insertado con contraseña hasheada.")
            
        conn.commit()
        
    except Exception as e:
        print(f"❌ ERROR de Base de Datos: {e}")
        if conn:
            conn.rollback()
    finally:
        if conn:
            conn.close()

if __name__ == "__main__":
    create_hashed_user()