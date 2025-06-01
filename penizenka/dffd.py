from kivy.app import App
from kivy.uix.boxlayout import BoxLayout
from kivy_garden.webview import WebView

class WebApp(BoxLayout):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.orientation = "vertical"
        self.webview = WebView(url="https://твой-сайт.com")
        self.add_widget(self.webview)

class MyApp(App):
    def build(self):
        return WebApp()

if __name__ == "__main__":
    MyApp().run()