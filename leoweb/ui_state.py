import reflex as rx

class UIState(rx.State):
    sidebar_open: bool = False

    def toggle_sidebar(self):
        self.sidebar_open = not self.sidebar_open
