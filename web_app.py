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
  <link rel="preconnect" href="https://fonts.googleapis.com" />
  <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin />
  <link href="https://fonts.googleapis.com/css2?family=Tajawal:wght@400;500;700;800&display=swap" rel="stylesheet" />
  <title>Azure Task Creator</title>
  <style>
    :root {
      --navy: #0b1f4a;
      --blue: #1d4ed8;
      --blue-2: #2563eb;
      --card: #ffffff;
      --text: #0f172a;
      --muted: #64748b;
      --line: #e2e8f0;
      --soft: #f8fafc;
      --green: #059669;
      --shadow: 0 12px 32px rgba(15, 23, 42, 0.1);
    }
    * { box-sizing: border-box; }
    body {
      margin: 0;
      font-family: Tajawal, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
      background:
        radial-gradient(1200px 400px at 100% -10%, #3b82f6 0%, transparent 55%),
        linear-gradient(180deg, var(--navy) 0 210px, #eef2f7 210px 100%);
      color: var(--text);
      min-height: 100vh;
      padding: 20px 16px 36px;
    }
    .wrap { max-width: 720px; margin: 0 auto; }
    .hero {
      display: flex;
      align-items: center;
      gap: 12px;
      margin: 8px 0 18px;
    }
    .logo {
      width: 48px;
      height: 48px;
      border-radius: 14px;
      background: linear-gradient(180deg, #60a5fa, #1d4ed8);
      color: #fff;
      display: grid;
      place-items: center;
      font-weight: 800;
      font-size: 18px;
      box-shadow: 0 8px 20px rgba(37, 99, 235, 0.35);
      flex: 0 0 auto;
    }
    h1 { color: #fff; font-size: 24px; margin: 0; line-height: 1.2; }
    .sub { color: #bfdbfe; margin: 4px 0 0; font-size: 13px; }
    .card {
      background: var(--card);
      border-radius: 22px;
      padding: 18px;
      box-shadow: var(--shadow);
      margin-bottom: 14px;
      border: 1px solid rgba(226, 232, 240, 0.8);
    }
    .card-head {
      display: flex;
      align-items: center;
      justify-content: space-between;
      gap: 10px;
      margin-bottom: 14px;
    }
    .card-title {
      margin: 0;
      font-size: 16px;
      font-weight: 800;
    }
    .badge {
      background: #dbeafe;
      color: #1e40af;
      border-radius: 999px;
      padding: 6px 10px;
      font-size: 12px;
      font-weight: 800;
      white-space: nowrap;
    }
    .grid {
      display: grid;
      grid-template-columns: 1fr;
      gap: 12px;
    }
    @media (min-width: 640px) {
      .grid.two { grid-template-columns: 1fr 1fr; }
    }
    .field { display: flex; flex-direction: column; gap: 6px; }
    .field.full { grid-column: 1 / -1; }
    label { font-size: 13px; font-weight: 800; color: #334155; }
    input, select {
      width: 100%;
      border: 1px solid var(--line);
      border-radius: 12px;
      padding: 12px 14px;
      font-size: 16px;
      font-family: inherit;
      background: var(--soft);
      color: var(--text);
    }
    input:focus, select:focus {
      outline: 2px solid #93c5fd;
      border-color: var(--blue-2);
      background: #fff;
    }
    .hint {
      margin: 0;
      color: var(--muted);
      font-size: 12px;
      font-weight: 700;
    }
    .row { display: flex; gap: 8px; flex-wrap: wrap; margin-top: 4px; }
    button {
      border: 0;
      border-radius: 12px;
      padding: 12px 14px;
      font-size: 15px;
      font-weight: 800;
      cursor: pointer;
      font-family: inherit;
    }
    .primary { background: linear-gradient(180deg, #3b82f6, var(--blue)); color: #fff; flex: 1; }
    .primary:active { transform: translateY(1px); }
    .secondary { background: #e2e8f0; color: #0f172a; flex: 1; }
    .ok { background: var(--green); color: #fff; flex: 1; }
    .ghost { background: transparent; color: #1d4ed8; padding: 8px 4px; }
    .status { font-size: 14px; color: var(--muted); white-space: pre-wrap; margin: 10px 0 0; }
    .status.success { color: var(--green); font-weight: 800; }
    .status.error { color: #dc2626; font-weight: 800; }
    .hidden { display: none !important; }
    .toast {
      position: fixed;
      left: 16px;
      right: 16px;
      top: max(16px, env(safe-area-inset-top));
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
  <div class="wrap">
    <div id="toast" class="toast hidden"></div>
    <header class="hero">
      <div class="logo">AT</div>
      <div>
        <h1>Azure Task Creator</h1>
        <p class="sub">إنشاء مهمة يومية بسرعة ومن الموبايل</p>
      </div>
    </header>

    <section class="card">
      <div class="card-head">
        <h2 class="card-title">المستخدم</h2>
        <button class="ghost" id="addUserBtn" type="button">+ إضافة مستخدم</button>
      </div>
      <div class="field">
        <label>المستخدم المحفوظ</label>
        <select id="profileSelect"></select>
      </div>
    </section>

    <section class="card hidden" id="userFormCard">
      <div class="card-head">
        <h2 class="card-title">بيانات المستخدم الجديد</h2>
      </div>
      <div class="grid two">
        <div class="field full">
          <label>المستخدم</label>
          <input id="newUser" placeholder="Name <email@domain.com>" />
        </div>
        <div class="field full">
          <label>PAT Token</label>
          <input id="newPat" type="password" />
        </div>
        <div class="field">
          <label>Organization</label>
          <input id="newOrg" />
        </div>
        <div class="field">
          <label>Project</label>
          <input id="newProject" />
        </div>
        <div class="field full">
          <label>Direct Manager</label>
          <input id="newManager" />
        </div>
      </div>
      <div class="row" style="margin-top:14px">
        <button class="ok" id="saveUserBtn" type="button">حفظ المستخدم</button>
        <button class="secondary" id="cancelUserBtn" type="button">إلغاء</button>
      </div>
    </section>

    <section class="card">
      <div class="card-head">
        <h2 class="card-title">تفاصيل المهمة</h2>
        <span class="badge">الوقت ثابت 9:00 PM</span>
      </div>
      <div class="grid two">
        <div class="field">
          <label>Organization</label>
          <input id="org" />
        </div>
        <div class="field">
          <label>Project</label>
          <input id="project" />
        </div>
        <div class="field full">
          <label>Direct Manager</label>
          <input id="manager" />
        </div>
        <div class="field full">
          <label>Assigned User</label>
          <input id="user" />
        </div>
        <div class="field">
          <label>التاريخ</label>
          <input id="date" type="date" />
          <p class="hint">اليوم فقط. الساعة دائمًا 9:00 مساءً</p>
        </div>
        <div class="field">
          <label>ساعات العمل</label>
          <input id="hours" inputmode="decimal" />
        </div>
        <div class="field full">
          <label>عنوان المهمة</label>
          <input id="title" />
        </div>
      </div>
      <div class="row" style="margin-top:16px">
        <button class="primary" id="createBtn" type="button">إنشاء المهمة</button>
      </div>
      <p class="status" id="status">جاهز</p>
    </section>
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

    async function requestJson(url, options) {
      const response = await fetch(url, options);
      const body = await response.text();
      let data;
      try {
        data = JSON.parse(body);
      } catch {
        throw new Error(`خطأ من السيرفر (${response.status}). أعد المحاولة، ولو استمرت المشكلة راجع سجل الخدمة.`);
      }
      if (!response.ok) {
        throw new Error(data.message || `تعذر الحفظ (${response.status}).`);
      }
      return data;
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
      state = await requestJson("/api/state");
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
      saveUserBtn.disabled = true;
      try {
        const data = await requestJson("/api/users", {
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
        status.className = "status " + (data.ok ? "success" : "error");
        status.textContent = data.message || "Saved";
        if (!data.ok) return;
        showToast("تم الإضافة بنجاح");
        userFormCard.classList.add("hidden");
        await loadState();
      } catch (error) {
        status.className = "status error";
        status.textContent = error.message || "تعذر الاتصال بالسيرفر.";
      } finally {
        saveUserBtn.disabled = false;
      }
    };

    profileSelect.onchange = async () => {
      try {
        await requestJson("/api/active", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ id: profileSelect.value })
        });
        await loadState();
      } catch (error) {
        status.className = "status error";
        status.textContent = error.message || "تعذر الاتصال بالسيرفر.";
      }
    };

    createBtn.onclick = async () => {
      status.textContent = "Submitting task...";
      createBtn.disabled = true;
      try {
        const data = await requestJson("/api/create", {
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
        status.className = "status " + (data.ok ? "success" : "error");
        status.textContent = data.message || "Done";
        if (data.ok) showToast("تم الإضافة بنجاح");
      } catch (error) {
        status.className = "status error";
        status.textContent = error.message || "تعذر الاتصال بالسيرفر.";
      } finally {
        createBtn.disabled = false;
      }
    };

    function localDateValue() {
      const now = new Date();
      const year = now.getFullYear();
      const month = String(now.getMonth() + 1).padStart(2, "0");
      const day = String(now.getDate()).padStart(2, "0");
      return year + "-" + month + "-" + day;
    }
    date.value = localDateValue();
    title.value = defaults.title;
    hours.value = defaults.hours;
    loadState().catch((error) => {
      status.className = "status error";
      status.textContent = error.message || "تعذر تحميل البيانات من السيرفر.";
    });
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
            try:
                config = normalize_config()
            except OSError:
                _json_response(self, {"ok": False, "message": "تعذر حفظ البيانات على السيرفر. تحقق من صلاحية مجلد التخزين."}, 500)
                return
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
        try:
            config = normalize_config()
        except OSError:
            _json_response(self, {"ok": False, "message": "تعذر حفظ البيانات على السيرفر. تحقق من صلاحية مجلد التخزين."}, 500)
            return

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
            try:
                upsert_profile(config, profile)
            except OSError:
                _json_response(self, {"ok": False, "message": "تعذر حفظ المستخدم على السيرفر. تحقق من صلاحية مجلد التخزين."}, 500)
                return
            _json_response(self, {"ok": True, "message": "تم الإضافة بنجاح", "id": profile["id"]})
            return

        if path == "/api/active":
            try:
                set_active_profile(config, payload.get("id"))
            except OSError:
                _json_response(self, {"ok": False, "message": "تعذر حفظ الاختيار على السيرفر. تحقق من صلاحية مجلد التخزين."}, 500)
                return
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
