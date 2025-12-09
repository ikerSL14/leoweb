# leoweb/admin/aui_state.py
import reflex as rx

class AUIState(rx.State):
    sidebar_open: bool = True # Por defecto abierta en admin suele ser mejor

    def toggle_sidebar(self):
        self.sidebar_open = not self.sidebar_open