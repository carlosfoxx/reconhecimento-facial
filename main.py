import sys
from frontend import App

if __name__ == "__main__":
    app = App()
    app.protocol("WM_DELETE_WINDOW", app.fechar)
    app.mainloop()
