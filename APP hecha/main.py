#!/usr/bin/env python3
"""Inicia SmartRoute WMS en el navegador (Flask + HTML)."""

from __future__ import annotations

import os
import subprocess
import sys
import webbrowser
from threading import Timer

from server import app

PORT = int(os.environ.get("PORT", "5000"))
URL = f"http://127.0.0.1:{PORT}"


def _free_port(port: int) -> None:
    """Cierra procesos viejos que bloquean el puerto (evita servidores zombie con código roto)."""
    if sys.platform != "win32":
        return
    try:
        out = subprocess.check_output(
            f'netstat -ano | findstr ":{port}" | findstr LISTENING',
            shell=True,
            text=True,
            stderr=subprocess.DEVNULL,
        )
        my_pid = os.getpid()
        for line in out.splitlines():
            parts = line.split()
            if not parts:
                continue
            pid = int(parts[-1])
            if pid != my_pid:
                subprocess.run(
                    ["taskkill", "/F", "/PID", str(pid)],
                    capture_output=True,
                    check=False,
                )
                print(f"  Cerrado proceso antiguo en puerto {port} (PID {pid})")
    except (subprocess.CalledProcessError, ValueError, OSError):
        pass


def _open_browser():
    webbrowser.open(URL)


if __name__ == "__main__":
    _free_port(PORT)
    Timer(1.2, _open_browser).start()
    print(f"\n  SmartRoute WMS — {URL}\n  Ctrl+C para detener\n")
    app.run(host="127.0.0.1", port=PORT, debug=False, use_reloader=False)
