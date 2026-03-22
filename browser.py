import os
import sys
import shutil
import subprocess
import webbrowser
import json
import urllib.request
import urllib.error


def open_browser(url: str) -> None:
    """Open a URL in the system's default browser, detecting OS and distro.

    When running inside Docker on Mac or Windows, browser requests are
    forwarded to the host machine via browser_helper_server.py on port 9876.
    """

    host_os = os.environ.get("HOST_OS", "").lower()

    # ── Inside Docker → Mac or Windows host: forward to helper ───────────────
    if host_os in ("mac", "windows"):
        host = os.environ.get("DOCKER_HOST_IP", "host.docker.internal")
        try:
            payload = json.dumps({"url": url}).encode()
            req = urllib.request.Request(
                f"http://{host}:9876",
                data=payload,
                headers={"Content-Type": "application/json"},
                method="POST",
            )
            urllib.request.urlopen(req, timeout=5)
            return
        except urllib.error.URLError:
            print(f"[browser] Host helper unreachable — open manually: {url}")
            return

    # ── Windows native ────────────────────────────────────────────────────────
    if sys.platform == "win32":
        os.startfile(url)
        return

    # ── macOS native ──────────────────────────────────────────────────────────
    if sys.platform == "darwin":
        subprocess.Popen(["open", url])
        return

    # ── Linux (native or Docker with HOST_OS=linux) ───────────────────────────
    for cmd in ["xdg-open", "gio", "gnome-open", "kde-open", "x-www-browser"]:
        if shutil.which(cmd):
            subprocess.Popen([cmd, url])
            return

    desktop = os.environ.get("XDG_CURRENT_DESKTOP", "").lower()
    if "gnome" in desktop and shutil.which("gnome-open"):
        subprocess.Popen(["gnome-open", url])
        return
    if "kde" in desktop and shutil.which("kde-open"):
        subprocess.Popen(["kde-open", url])
        return

    webbrowser.open(url)


if __name__ == "__main__":
    open_browser("https://example.com")