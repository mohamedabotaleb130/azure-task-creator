import json
import os
import socket
import threading
from datetime import datetime
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import urlparse

from task_core import (
    DEFAULT_MANAGER,
    DEFAULT_TITLE,
    ORG,
    PROJECT,
    WORK_HOURS,
    create_task,
    get_active_profile,
    make_profile,
    normalize_config,
    set_active_profile,
    upsert_profile,
    validate_pat,
)

HOST = "0.0.0.0"
PORT = 5050
_server = None


INDEX_HTML = """<!DOCTYPE html>
<html lang="ar" dir="rtl">
<head>
  <meta charset="UTF-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover" />
  <meta name="apple-mobile-web-app-capable" content="yes" />
  <meta name="apple-mobile-web-app-status-bar-style" content="black-translucent" />
  <meta name="apple-mobile-web-app-title" content="Azure Task" />
  <link rel="manifest" href="/manifest.json" />
  <title>Azure Task Creator</title>
  <style>
    :root {
      --bg: #0f172a;
      --card: #ffffff;
      --text: #0f172a;
      --muted: #64748b;
      --line: #e2e8f0;
      --blue: #2563eb;
      --green: #059669;
    }
    * { box-sizing: border-box; }
    body {
      margin: 0;
      font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
      background: linear-gradient(180deg, #1e3a8a 0%, #f1f5f9 220px);
      color: var(--text);
      min-height: 100vh;
      padding: 24px 16px 40px;
    }
    h1 { color: #fff; font-size: 22px; margin: 8px 0 4px; }
    .sub { color: #dbeafe; margin: 0 0 18px; font-size: 14px; }
    .card {
      background: var(--card);
      border-radius: 18px;
      padding: 16px;
      box-shadow: 0 10px 30px rgba(15, 23, 42, 0.12);
      margin-bottom: 14px;
    }
    label { display: block; font-size: 13px; font-weight: 700; margin: 10px 0 6px; }
    input, select, textarea {
      width: 100%;
      border: 1px solid var(--line);
      border-radius: 12px;
      padding: 12px;
      font-size: 16px;
    }
    .row { display: flex; gap: 8px; flex-wrap: wrap; margin-top: 14px; }
    button {
      border: 0;
      border-radius: 12px;
      padding: 12px 14px;
      font-size: 15px;
      font-weight: 700;
      cursor: pointer;
    }
    .primary { background: var(--blue); color: #fff; flex: 1; }
    .secondary { background: #e2e8f0; color: #0f172a; flex: 1; }
    .ok { background: var(--green); color: #fff; flex: 1; }
    .status { font-size: 14px; color: var(--muted); white-space: pre-wrap; }
    .status.success { color: var(--green); font-weight: 700; font-size: 16px; }
    .status.error { color: #dc2626; font-weight: 700; }
    .hidden { display: none; }
    .toast {
      position: fixed;
      left: 16px;
      right: 16px;
      top: 16px;
      z-index: 20;
      background: var(--green);
      color: #fff;
      border-radius: 14px;
      padding: 14px 16px;
      font-weight: 800;
      text-align: center;
      box-shadow: 0 10px 30px rgba(5, 150, 105, 0.35);
    }
  </style>
</head>
<body>
  <div id="toast" class="toast hidden"></div>
  <h1>Azure Task Creator</h1>
  <p class="sub">من الآيفون: Safari ثم Share ثم Add to Home Screen</p>

  <div class="card">
    <label>المستخدم المحفوظ</label>
    <select id="profileSelect"></select>
    <div class="row">
      <button class="secondary" id="addUserBtn" type="button">إضافة مستخدم جديد</button>
    </div>
  </div>

  <div class="card hidden" id="userFormCard">
    <label>Assigned User</label>
    <input id="newUser" placeholder="Name <email@domain.com>" />
    <label>PAT Token</label>
    <input id="newPat" type="password" />
    <label>Organization</label>
    <input id="newOrg" />
    <label>Project</label>
    <input id="newProject" />
    <label>Direct Manager</label>
    <input id="newManager" />
    <div class="row">
      <button class="ok" id="saveUserBtn" type="button">حفظ المستخدم</button>
      <button class="secondary" id="cancelUserBtn" type="button">إلغاء</button>
    </div>
  </div>

  <div class="card">
    <label>Organization</label>
    <input id="org" />
    <label>Project</label>
    <input id="project" />
    <label>Direct Manager</label>
    <input id="manager" />
    <label>Assigned User</label>
    <input id="user" />
    <label>Date</label>
    <input id="date" type="date" />
    <label>Task Title</label>
    <input id="title" />
    <label>Work Hours</label>
    <input id="hours" inputmode="decimal" />
    <div class="row">
      <button class="primary" id="createBtn" type="button">Create Task</button>
    </div>
    <p class="status" id="status">Ready</p>
  </div>

  <script>
    const defaults = __DEFAULTS__;
    let state = { profiles: [], active_profile: "" };

    function fillTaskForm(profile) {
      if (!profile) return;
      org.value = profile.org || defaults.org;
      project.value = profile.project || defaults.project;
      manager.value = profile.manager || defaults.manager;
      user.value = profile.user || "";
    }

    function showToast(text) {
      toast.textContent = text;
      toast.classList.remove("hidden");
      setTimeout(() => toast.classList.add("hidden"), 4000);
    }

    function renderProfiles() {
      profileSelect.innerHTML = "";
      state.profiles.forEach((p) => {
        const opt = document.createElement("option");
        opt.value = p.id;
        opt.textContent = p.label || p.user;
        if (p.id === state.active_profile) opt.selected = true;
        profileSelect.appendChild(opt);
      });
      const active = state.profiles.find((p) => p.id === state.active_profile);
      fillTaskForm(active);
    }

    async function loadState() {
      const res = await fetch("/api/state");
      state = await res.json();
      renderProfiles();
    }

    addUserBtn.onclick = () => {
      userFormCard.classList.remove("hidden");
      newUser.value = "";
      newPat.value = "";
      newOrg.value = defaults.org;
      newProject.value = defaults.project;
      newManager.value = defaults.manager;
    };
    cancelUserBtn.onclick = () => userFormCard.classList.add("hidden");

    saveUserBtn.onclick = async () => {
      status.textContent = "Saving user...";
      const res = await fetch("/api/users", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          user: newUser.value,
          pat: newPat.value,
          org: newOrg.value,
          project: newProject.value,
          manager: newManager.value
        })
      });
      const data = await res.json();
      status.className = "status " + (data.ok ? "success" : "error");
      status.textContent = data.message || "Saved";
      if (data.ok) {
        showToast("تم الإضافة بنجاح");
        userFormCard.classList.add("hidden");
        await loadState();
      }
    };

    profileSelect.onchange = async () => {
      await fetch("/api/active", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ id: profileSelect.value })
      });
      await loadState();
    };

    createBtn.onclick = async () => {
      status.textContent = "Submitting task...";
      const res = await fetch("/api/create", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          org: org.value,
          project: project.value,
          manager: manager.value,
          user: user.value,
          date: date.value,
          title: title.value,
          hours: hours.value
        })
      });
      const data = await res.json();
      status.className = "status " + (data.ok ? "success" : "error");
      status.textContent = data.message || "Done";
      if (data.ok) {
        showToast("تم الإضافة بنجاح");
      }
    };

    date.value = new Date().toISOString().slice(0, 10);
    title.value = defaults.title;
    hours.value = defaults.hours;
    loadState();
  </script>
</body>
</html>
"""

MANIFEST = {
    "name": "Azure Task Creator",
    "short_name": "Azure Task",
    "start_url": "/",
    "display": "standalone",
    "background_color": "#1e3a8a",
    "theme_color": "#1e3a8a",
}


def get_lan_ip():
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        sock.connect(("8.8.8.8", 80))
        return sock.getsockname()[0]
    except OSError:
        return "127.0.0.1"
    finally:
        sock.close()


def _json_response(handler, payload, status=200):
    body = json.dumps(payload, ensure_ascii=True).encode("utf-8")
    handler.send_response(status)
    handler.send_header("Content-Type", "application/json; charset=utf-8")
    handler.send_header("Content-Length", str(len(body)))
    handler.end_headers()
    handler.wfile.write(body)


def _read_json(handler):
    length = int(handler.headers.get("Content-Length") or 0)
    raw = handler.rfile.read(length) if length else b"{}"
    try:
        return json.loads(raw.decode("utf-8") or "{}")
    except json.JSONDecodeError:
        return {}


class AppHandler(BaseHTTPRequestHandler):
    def log_message(self, format, *args):
        return

    def do_GET(self):
        path = urlparse(self.path).path
        if path == "/manifest.json":
            body = json.dumps(MANIFEST).encode("utf-8")
            self.send_response(200)
            self.send_header("Content-Type", "application/manifest+json")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)
            return
        if path == "/api/state":
            config = normalize_config()
            _json_response(self, public_config(config))
            return
        if path in ("/", "/index.html"):
            defaults = json.dumps({
                "org": ORG,
                "project": PROJECT,
                "manager": DEFAULT_MANAGER,
                "title": DEFAULT_TITLE,
                "hours": str(WORK_HOURS),
            })
            html = INDEX_HTML.replace("__DEFAULTS__", defaults).encode("utf-8")
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Content-Length", str(len(html)))
            self.end_headers()
            self.wfile.write(html)
            return
        self.send_error(404)

    def do_POST(self):
        path = urlparse(self.path).path
        payload = _read_json(self)
        config = normalize_config()

        if path == "/api/users":
            user = (payload.get("user") or "").strip()
            pat = (payload.get("pat") or "").strip()
            if not user or not pat:
                _json_response(self, {"ok": False, "message": "PAT and Assigned User are required."}, 400)
                return
            valid, error = validate_pat(pat)
            if not valid:
                _json_response(self, {"ok": False, "message": error}, 400)
                return
            profile = make_profile(
                user,
                pat,
                (payload.get("org") or "").strip(),
                (payload.get("project") or "").strip(),
                (payload.get("manager") or "").strip(),
            )
            upsert_profile(config, profile)
            _json_response(self, {"ok": True, "message": "تم الإضافة بنجاح", "id": profile["id"]})
            return

        if path == "/api/active":
            set_active_profile(config, payload.get("id"))
            _json_response(self, {"ok": True})
            return

        if path == "/api/create":
            active = get_active_profile(config)
            selected_org = (payload.get("org") or "").strip()
            selected_project = (payload.get("project") or "").strip()
            selected_manager = (payload.get("manager") or "").strip()
            selected_user = (payload.get("user") or "").strip()
            title = (payload.get("title") or "").strip()
            if not all([selected_org, selected_project, selected_manager, selected_user, title]):
                _json_response(self, {"ok": False, "message": "All task fields are required."}, 400)
                return
            try:
                selected_date = datetime.strptime((payload.get("date") or "").strip(), "%Y-%m-%d")
                selected_hours = float(payload.get("hours"))
            except (TypeError, ValueError):
                _json_response(self, {"ok": False, "message": "Date must be YYYY-MM-DD and hours must be a number."}, 400)
                return
            success, message = create_task(
                selected_org,
                selected_project,
                selected_user,
                selected_manager,
                selected_date,
                title,
                selected_hours,
                (active or {}).get("pat", ""),
            )
            _json_response(self, {"ok": success, "message": message}, 200 if success else 400)
            return

        self.send_error(404)


def public_config(config):
    profiles = []
    for profile in config.get("profiles") or []:
        profiles.append({key: value for key, value in profile.items() if key != "pat"})
    return {
        "profiles": profiles,
        "active_profile": config.get("active_profile") or "",
    }


def start_web_server(port=None):
    global _server, PORT
    if port:
        PORT = int(port)
    if _server is not None:
        return get_lan_ip(), PORT
    _server = ThreadingHTTPServer((HOST, PORT), AppHandler)
    thread = threading.Thread(target=_server.serve_forever, daemon=True)
    thread.start()
    return get_lan_ip(), PORT


if __name__ == "__main__":
    ip, port = start_web_server(os.environ.get("PORT", PORT))
    print(f"Open on iPhone Safari: http://{ip}:{port}")
    print("Keep this window open. Same Wi-Fi required.")
    try:
        threading.Event().wait()
    except KeyboardInterrupt:
        pass
