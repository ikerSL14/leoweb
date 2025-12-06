import reflex as rx
import datetime # ⬅️ Necesario para manejar horas
from .sidebar import sidebar, sidebar_button
from .auth_state import get_connection, AuthState
from .ui_state import UIState

# --------------------------
# STATE PARA RESERVACIONES
# --------------------------
class ReservaState(rx.State):
    fecha: str = ""
    tipo_evento: str = ""
    hora: str = ""
    cant_personas: str = "1"
    id_sucursal: int = 1

    DURACION_RESERVA_MINUTOS: int = 120
    BUFFER_ENTRE_EVENTOS_MINUTOS: int = 120
    
    # 1. LISTA MAESTRA DE HORARIOS (Tus horarios de servicio)
    # Define aquí las horas en las que abres.
    horarios_base: list[str] = [
        "13:00", "14:00", "15:00", "16:00", "17:00", 
        "18:00", "19:00", "20:00", "21:00", "22:00"
    ]
    
    # 2. Variable dinámica que alimentará el Select
    horas_disponibles: list[str] = [] 

    # 3. Disparador: Se ejecuta cuando cambian la fecha
    async def set_fecha_y_buscar_horas(self, fecha: str):
        self.fecha = fecha
        self.hora = "" # Reseteamos la hora seleccionada previa
        await self.cargar_horas_disponibles()

    async def cargar_horas_disponibles(self):
        if not self.fecha:
            self.horas_disponibles = []
            return

        conn = None
        try:
            conn = get_connection()
            cur = conn.cursor()

            # 4. Buscamos las reservas de ESA fecha en ESA sucursal
            query = """
                SELECT hora, cant_personas FROM reserva 
                WHERE fecha = %s AND id_sucursal = %s
            """
            cur.execute(query, (self.fecha, self.id_sucursal))
            reservas = cur.fetchall() # Devuelve lista de tuplas [(datetime.time(20,0),), ...]

            intervalos_bloqueados = []

            # --- 1. Determinar el Intervalo de Bloqueo Total (Con Búfer Antes y Después) ---
            
            for hora_inicio_db, cant_personas in reservas:
                inicio_reserva_db = datetime.datetime.combine(datetime.date.today(), hora_inicio_db)
                
                # INICIO del BLOQUEO TOTAL: Hora de inicio real - Búfer requerido antes
                inicio_bloqueo = inicio_reserva_db - datetime.timedelta(minutes=self.BUFFER_ENTRE_EVENTOS_MINUTOS) # ⬅️ APLICAR BÚFER HACIA ATRÁS
                
                # FIN del BLOQUEO TOTAL: Hora de inicio real + Duración + Búfer requerido después
                fin_bloqueo = inicio_reserva_db + datetime.timedelta(
                    minutes=self.DURACION_RESERVA_MINUTOS + self.BUFFER_ENTRE_EVENTOS_MINUTOS # ⬅️ APLICAR DURACIÓN Y BÚFER HACIA ADELANTE
                )
                
                # La reserva existente ocupa el intervalo [inicio_bloqueo, fin_bloqueo)
                intervalos_bloqueados.append({
                    'inicio': inicio_bloqueo, 
                    'fin': fin_bloqueo
                })

            horas_libres = []
            
            # --- 2. Revisar cada SLOT base para ver si el BLOQUE ENTERO está disponible ---

            for h_base in self.horarios_base:
                h_base_time = datetime.datetime.strptime(h_base, "%H:%M").time()
                inicio_slot_candidato = datetime.datetime.combine(datetime.date.today(), h_base_time)
                
                # El usuario quiere reservar el bloque: [inicio_slot_candidato, fin_slot_candidato]
                # La duración del slot que el usuario toma debe ser la DURACION_RESERVA_MINUTOS
                fin_slot_candidato = inicio_slot_candidato + datetime.timedelta(minutes=self.DURACION_RESERVA_MINUTOS)
                
                esta_disponible = True
                for bloqueo in intervalos_bloqueados:
                    # Criterio de Solapamiento:
                    # El slot candidato se solapa con el bloqueo si:
                    # [Inicio Candidato] < [Fin Bloqueo] Y [Fin Candidato] > [Inicio Bloqueo]
                    if inicio_slot_candidato < bloqueo['fin'] and fin_slot_candidato > bloqueo['inicio']:
                        esta_disponible = False
                        break
                
                if esta_disponible:
                    horas_libres.append(h_base)

            self.horas_disponibles = horas_libres
            
            # Si no hay horas, avisar (opcional)
            if not self.horas_disponibles:
                rx.toast.warning("No hay horarios disponibles para esta fecha.", position="bottom-right")

        except Exception as e:
            print(f"Error buscando horas: {e}")
            self.horas_disponibles = [] # Fallback seguro
        finally:
            if conn:
                conn.close()

    async def reservar(self):
        auth = await self.get_state(AuthState)

        if not auth.logged_in:
            return rx.toast.error("Debes iniciar sesión primero.", position="bottom-right")

        if not self.fecha or not self.hora or not self.tipo_evento:
            return rx.toast.warning("Por favor completa todos los campos.", position="bottom-right")

        # --- GUARDAR EN BD ---
        conn = None 
        try:
            conn = get_connection()
            cur = conn.cursor()
            
            # (Opcional) Doble verificación por seguridad 
            # por si dos usuarios dieron click al mismo milisegundo
            check_query = "SELECT id_reserva FROM reserva WHERE fecha=%s AND hora=%s"
            cur.execute(check_query, (self.fecha, self.hora))
            if cur.fetchone():
                return rx.toast.error("¡Ups! Alguien te ganó la hora hace un instante.", position="bottom-right")

            query = """
                INSERT INTO reserva (id_usuario, cant_personas, fecha, hora, tipo_evento, id_sucursal)
                VALUES (%s, %s, %s, %s, %s, %s)
            """

            cur.execute(query, (
                auth.current_user,
                int(self.cant_personas),
                self.fecha,
                self.hora,
                self.tipo_evento,
                self.id_sucursal
            ))

            conn.commit()
            
            # Limpieza y recarga de horas (para quitar la que acabas de tomar)
            temp_fecha = self.fecha
            self.tipo_evento = ""
            self.hora = ""
            await self.set_fecha_y_buscar_horas(temp_fecha) # Refrescar lista
            
            return rx.toast.success("¡Reservación realizada con éxito!", position="bottom-right")

        except Exception as e:
            if conn:
                conn.rollback()
            return rx.toast.error(f"Error al guardar: {str(e)}", position="bottom-right")

        finally:
            if conn:
                conn.close()

# ... (Tu código de glass_card igual que antes con width 700px) ...
def glass_card(*children):
    return rx.box(
        *children,
        width="700px",
        padding="40px",
        border_radius="20px",
        background="rgba(0,0,0,0.35)",
        backdrop_filter="blur(10px)",
        border="1px solid rgba(255,255,255,0.15)",
        box_shadow="0px 8px 25px rgba(0,0,0,0.4)",
    )

# --------------------------
# RESERVACIONES PAGE (MODIFICADA)
# --------------------------
def reservaciones_page():
    return rx.box(
        sidebar(active_item="reservaciones"),
        sidebar_button(),
        rx.center(
            glass_card(
                rx.heading("Haz tu reservación ahora", color="white", size="6", margin_bottom="25px", text_align="center"),

                # --- FILA 1: FECHA + HORA (SELECT) ---
                rx.hstack(
                    rx.vstack(
                        rx.text("Fecha", color="white", margin_bottom="5px"),
                        rx.input(
                            type="date",
                            # 7. AQUÍ CAMBIAMOS EL EVENTO:
                            on_change=ReservaState.set_fecha_y_buscar_horas,
                            size="3",
                            width="100%",
                            background="rgba(255,255,255,0.08)",
                            color="white",
                            border_radius="10px",
                            padding_left="10px",
                            # Truco para que el icono del calendario se vea blanco (depende navegador)
                            style={"color-scheme": "dark"}, 
                        ),
                        spacing="1",
                        width="50%"
                    ),
                    rx.vstack(
                        rx.text("Hora Disponible", color="white", margin_bottom="5px"),
                        
                        # 8. USAMOS SELECT EN LUGAR DE INPUT TIME
                        rx.select(
                            ReservaState.horas_disponibles, # La lista filtrada desde BD
                            placeholder="Selecciona hora...",
                            on_change=ReservaState.set_hora,
                            value=ReservaState.hora, # Vinculado para poder limpiarlo
                            size="3",
                            width="100%",
                            background="rgba(255,255,255,0.08)",
                            color="white",
                            border_radius="10px",
                            border="1px solid rgba(255,255,255,0.2)", # Agregamos un borde sutil

                            # ⬅️ ESTILOS AVANZADOS PARA EL PLACEHOLDER, FLECHA Y TEXTO
                            style={
                                "color-scheme": "dark", # Asegura que la flecha sea clara
                                "padding-left": "10px",
                            },
                            _placeholder={"color": "rgba(255,255,255,0.5)"}, # Estilo del placeholder
                            _hover={"background": "rgba(255,255,255,0.12)"}, # Estilo al pasar el ratón
                            
                            # ⬅️ IMPORTANTE: ELIMINAR variant="soft" 
                        ),
                        spacing="1",
                        width="50%"
                    ),
                    spacing="4",
                    margin_bottom="20px",
                ),

                # ... (El resto de inputs: Tipo, Cantidad, Tienda, Botón se quedan IGUAL) ...
                rx.hstack(
                    rx.vstack(
                        rx.text("Tipo de reservación", color="white", margin_bottom="5px"),
                        rx.input(
                            placeholder="TRABAJO, FAMILIA, CUMPLEAÑOS...",
                            on_change=ReservaState.set_tipo_evento,
                            size="3", width="100%", background="rgba(255,255,255,0.08)", color="white", border_radius="10px", padding_left="10px",
                        ),
                        spacing="1", width="50%"
                    ),
                    rx.vstack(
                        rx.text("Cantidad de personas", color="white", margin_bottom="5px"),
                        rx.input(
                            type="number", min="1",
                            on_change=ReservaState.set_cant_personas,
                            size="3", width="100%", background="rgba(255,255,255,0.08)", color="white", border_radius="10px", padding_left="10px",
                        ),
                        spacing="1", width="50%"
                    ),
                    spacing="4", margin_bottom="20px",
                ),
                rx.vstack(
                    rx.text("Tienda", color="white", margin_bottom="5px"),
                    rx.input(value="Paseo Tabasco", disabled=True, size="3", width="100%", background="rgba(255,255,255,0.15)", color="white", border_radius="10px", padding_left="10px"),
                    spacing="1", margin_bottom="20px"
                ),
                rx.button(
                    "Reservar", width="100%", size="3", background="red", color="white", border_radius="10px", padding="10px", cursor="pointer",
                    on_click=ReservaState.reservar, transition="background 0.3s ease-in-out", _hover={"background": "#b30000"},
                ),
            )
        ),
        width="100%", height="100vh",
        background_image="url('https://plus.unsplash.com/premium_photo-1661883237884-263e8de8869b?q=80&w=889&auto=format&fit=crop')",
        background_size="cover", background_position="center", display="flex", justify_content="center", align_items="center",
        padding_left=rx.cond(UIState.sidebar_open, "260px", "0px"), transition="padding-left 0.3s ease",
    )