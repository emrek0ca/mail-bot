from __future__ import annotations

import sys

from .app_controller import AppController
from .database import Database


def main() -> None:
    try:
        from .gui.app import MailBotApp
    except ImportError as exc:
        if "_tkinter" in str(exc):
            raise SystemExit(
                "Tkinter bulunamadi. Python'un Tk destekli surumunu kurun veya sisteminize Tk ekleyin; ardından `pip install -r requirements.txt` calistirin."
            ) from exc
        raise SystemExit("GUI bagimliliklari eksik. `pip install -r requirements.txt` komutunu calistirin.") from exc

    database = Database()
    database.init_db()
    controller = AppController(database)
    app = MailBotApp(controller)
    app.mainloop()


if __name__ == "__main__":
    main()
