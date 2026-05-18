from auth import init_admin
from gui_app import LoginWindow


def main():
    try:
        init_admin()
        app = LoginWindow()
        app.mainloop()

    except Exception as e:
        print(f"[ERROR] Application failed to start: {e}")


if __name__ == "__main__":
    main()
    