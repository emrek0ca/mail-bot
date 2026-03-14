from __future__ import annotations

import os
import sys
import threading
import traceback
from datetime import datetime

from . import DATA_DIR
from .app_controller import AppController
from .database import Database


def _setup_logging() -> None:
    log_file = DATA_DIR / "app.log"
    try:
        # Keep log file size reasonable by overwriting if very large (> 5MB)
        if log_file.exists() and log_file.stat().st_size > 5 * 1024 * 1024:
            log_file.unlink()
        
        f = open(log_file, "a", encoding="utf-8")
        f.write(f"\n--- Uygulama Baslatildi: {datetime.now()} ---\n")
        # Redirect stdout and stderr to the file as well if needed, 
        # but for now let's just make sure we can write to it.
        f.close()
    except Exception as e:
        print(f"Log dosyasi olusturulamadi: {e}", file=sys.stderr)


def _global_exception_handler(exc_type, exc_value, exc_traceback) -> None:
    if issubclass(exc_type, KeyboardInterrupt):
        sys.__excepthook__(exc_type, exc_value, exc_traceback)
        return

    err_msg = "".join(traceback.format_exception(exc_type, exc_value, exc_traceback))
    print(f"FATAL ERROR: {err_msg}", file=sys.stderr)
    
    # Write to log file
    try:
        with open(DATA_DIR / "app.log", "a", encoding="utf-8") as f:
            f.write(f"\n[{datetime.now()}] KRITIK HATA:\n{err_msg}\n")
    except Exception:
        pass

    try:
        from tkinter import messagebox
        import tkinter as tk
        root = tk.Tk()
        root.withdraw()
        messagebox.showerror(
            "Beklenmedik Bir Hata Olustu",
            f"Uygulama beklenmedik bir hata nedeniyle durduruldu.\n\nHata Detayi:\n{exc_value}\n\nTam log dosyasi su konumdadir:\n{DATA_DIR / 'app.log'}",
        )
        root.destroy()
    except Exception:
        pass


def main() -> None:
    _setup_logging()
    sys.excepthook = _global_exception_handler
    # Python 3.8+ for threading.excepthook
    if hasattr(threading, "excepthook"):
        def _thread_exception_handler(args):
            _global_exception_handler(args.exc_type, args.exc_value, args.exc_trace)
        threading.excepthook = _thread_exception_handler

    try:
        from .gui.app import MailBotApp
    except ImportError as exc:
        if "_tkinter" in str(exc):
            msg = "Tkinter bulunamadi."
            if sys.platform.startswith("linux"):
                msg += "\nLinux kullaniyorsaniz: 'sudo apt-get install python3-tk' komutunu calistirin."
            elif sys.platform == "darwin":
                msg += "\nmacOS kullaniyorsaniz: Python'un Tk destekli surumunu kurun (brew install python-tk@3.11)."
            raise SystemExit(msg) from exc
        raise SystemExit(f"GUI bagimliliklari eksik: {exc}\n`pip install -r requirements.txt` komutunu calistirin.") from exc

    try:
        database = Database()
        database.init_db()
        controller = AppController(database)
        app = MailBotApp(controller)
        app.mainloop()
    except Exception:
        traceback.print_exc()
        _global_exception_handler(*sys.exc_info())


if __name__ == "__main__":
    main()
