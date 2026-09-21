import os
import socket
import sys
import threading
import time
import webbrowser
import uvicorn

from marketpulse.core.llm_client import LLMClient


def get_local_ip() -> str:
    """Detecta la dirección IP local de la máquina en la red doméstica."""
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.settimeout(0.5)
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except Exception:
        return "127.0.0.1"


def open_browser_delayed(url: str, delay: float = 1.5):
    """Abre el navegador tras un breve retraso para que el servidor haya arrancado."""
    time.sleep(delay)
    try:
        webbrowser.open(url)
    except Exception:
        pass


def main():
    port = int(os.getenv("PORT", "8000"))
    host = os.getenv("HOST", "0.0.0.0")
    local_ip = get_local_ip()

    _, backend_label = LLMClient.get_backend_info()

    print("\n" + "=" * 65)
    print("  🚀 MarketPulse Web - Asistente Multitienda Inteligente")
    print("=" * 65)
    print(f"  • Motor Semántico Activo: {backend_label}")
    print(f"  • Acceso Local (este PC):  http://localhost:{port}")
    print(f"  • Acceso en Red Local/NAS: http://{local_ip}:{port}")
    print("=" * 65 + "\n")
    print("Presiona Ctrl+C para detener el servidor.\n")

    # Abrir navegador automáticamente si se ejecuta interactivamente en Windows/Mac
    if not os.getenv("NO_BROWSER"):
        threading.Thread(target=open_browser_delayed, args=(f"http://localhost:{port}",), daemon=True).start()

    # Auto-recarga automática (hot-reload): se reinicia solo al modificar código
    reload_enabled = os.getenv("RELOAD", "true").lower() in ("true", "1", "yes")
    uvicorn.run(
        "marketpulse.web.app:app",
        host=host,
        port=port,
        reload=reload_enabled,
        reload_dirs=["marketpulse"] if reload_enabled else None,
        log_level="info",
    )


if __name__ == "__main__":
    main()
