import re
import shutil
import subprocess
import threading
import time
import urllib.error
import urllib.request
from pathlib import Path

TOOLS_DIR = Path(__file__).with_name("tools")
CLOUDFLARED = TOOLS_DIR / "cloudflared.exe"
CLOUDFLARED_URL = (
    "https://github.com/cloudflare/cloudflared/releases/latest/download/"
    "cloudflared-windows-amd64.exe"
)
_tunnel_proc = None
_public_url = None
_lock = threading.Lock()
URL_PATTERN = re.compile(r"https://[a-z0-9-]+\.trycloudflare\.com")


def ensure_cloudflared():
    if CLOUDFLARED.exists():
        return CLOUDFLARED
    found = shutil.which("cloudflared")
    if found:
        return Path(found)
    TOOLS_DIR.mkdir(exist_ok=True)
    urllib.request.urlretrieve(CLOUDFLARED_URL, CLOUDFLARED)
    return CLOUDFLARED


def _is_tunnel_alive():
    return bool(_tunnel_proc and _tunnel_proc.poll() is None and _public_url)


def _stop_tunnel():
    global _tunnel_proc, _public_url
    proc = _tunnel_proc
    _tunnel_proc = None
    _public_url = None
    if proc and proc.poll() is None:
        proc.terminate()
        try:
            proc.wait(timeout=5)
        except subprocess.TimeoutExpired:
            proc.kill()


def _wait_for_url(proc):
    for _ in range(80):
        line = proc.stdout.readline()
        if not line:
            break
        match = URL_PATTERN.search(line)
        if match:
            return match.group(0)
        if proc.poll() is not None:
            break
    return None


def _url_is_reachable(url):
    request = urllib.request.Request(url, method="GET")
    try:
        with urllib.request.urlopen(request, timeout=8) as response:
            body = response.read(400).decode("utf-8", errors="ignore")
            return response.status < 500 and "1033" not in body
    except urllib.error.HTTPError as error:
        body = error.read(400).decode("utf-8", errors="ignore")
        if "1033" in body or error.code == 530:
            return False
        return error.code < 500
    except OSError:
        return False


def _wait_until_ready(url):
    for _ in range(12):
        if not _is_tunnel_alive():
            return False
        if _url_is_reachable(url):
            return True
        time.sleep(1)
    return False


def start_public_tunnel(port):
    global _tunnel_proc, _public_url
    with _lock:
        if _is_tunnel_alive():
            return _public_url

        _stop_tunnel()
        binary = ensure_cloudflared()
        _tunnel_proc = subprocess.Popen(
            [
                str(binary),
                "tunnel",
                "--url",
                f"http://127.0.0.1:{port}",
                "--protocol",
                "http2",
                "--no-autoupdate",
            ],
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
        )
        public_url = _wait_for_url(_tunnel_proc)
        if not public_url:
            _stop_tunnel()
            raise RuntimeError("Could not create a public link. Check internet and try again.")

        _public_url = public_url
        threading.Thread(target=_drain_output, daemon=True).start()
        if not _wait_until_ready(public_url):
            _stop_tunnel()
            raise RuntimeError(
                "Public link was created but Cloudflare error 1033 appeared. "
                "Keep the program open and press Open on iPhone again."
            )
        return _public_url


def _drain_output():
    global _public_url
    if _tunnel_proc and _tunnel_proc.stdout:
        for _ in _tunnel_proc.stdout:
            pass
    if _tunnel_proc and _tunnel_proc.poll() is not None:
        _public_url = None
