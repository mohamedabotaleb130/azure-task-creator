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
  <link rel="apple-touch-icon" sizes="180x180" href="/apple-touch-icon.png" />
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
    :root {
      --navy: #10243d;
      --blue: #2456d8;
      --blue-2: #3d6ce8;
      --text: #17283d;
      --muted: #718096;
      --line: #e3eaf2;
      --soft: #f6f8fb;
      --green: #078768;
      --shadow: 0 10px 28px rgba(16, 36, 61, 0.08);
    }
    body {
      background: linear-gradient(180deg, #eaf1fb 0, #f5f7fb 290px, #f5f7fb 100%);
      min-height: 100dvh;
      padding: max(14px, env(safe-area-inset-top)) 14px calc(28px + env(safe-area-inset-bottom));
    }
    .wrap { max-width: 560px; }
    .hero {
      position: relative;
      overflow: hidden;
      min-height: 126px;
      align-items: flex-start;
      padding: 23px 20px;
      margin: 0 0 14px;
      border-radius: 24px;
      background: linear-gradient(125deg, #10243d 0%, #183d69 62%, #2860aa 100%);
      box-shadow: 0 16px 34px rgba(16, 36, 61, 0.18);
    }
    .hero::after {
      content: "";
      position: absolute;
      width: 190px;
      height: 190px;
      left: -62px;
      top: -90px;
      border: 1px solid rgba(255,255,255,.12);
      border-radius: 50%;
      box-shadow: 0 0 0 22px rgba(255,255,255,.035), 0 0 0 48px rgba(255,255,255,.025);
      pointer-events: none;
    }
    .logo {
      width: 46px;
      height: 46px;
      border: 1px solid rgba(255,255,255,.24);
      background: rgba(255,255,255,.13);
      box-shadow: none;
    }
    h1 { font-size: 23px; }
    .sub { color: #d9e7fb; font-size: 14px; }
    .card {
      padding: 17px;
      border-radius: 20px;
      box-shadow: 0 6px 20px rgba(16,36,61,.055);
      border-color: #e7edf5;
      margin-bottom: 12px;
    }
    .card-head { margin-bottom: 12px; }
    .card-title { font-size: 17px; }
    .badge { background: #edf3ff; color: #3158a4; padding: 6px 11px; }
    .grid.two { grid-template-columns: repeat(2, minmax(0, 1fr)); gap: 12px 10px; }
    .field.full { grid-column: 1 / -1; }
    label { font-size: 13px; color: #40536b; }
    input, select {
      min-height: 48px;
      border-radius: 13px;
      border-color: #dfe7f0;
      background: #fbfcfe;
    }
    input:focus, select:focus { outline: 3px solid rgba(61,108,232,.14); }
    .hint { line-height: 1.55; }
    button {
      min-height: 46px;
      border-radius: 13px;
      transition: transform .15s ease, opacity .15s ease;
    }
    button:disabled { opacity: .65; cursor: wait; }
    .primary {
      min-height: 54px;
      background: linear-gradient(135deg, #3470ed, #2456d8);
      box-shadow: 0 8px 18px rgba(36,86,216,.2);
    }
    .ok { background: linear-gradient(135deg,#0b9b78,#078768); }
    .secondary { background: #eef2f7; }
    .ghost { color: var(--blue); white-space: nowrap; }
    .status {
      border-radius: 12px;
      padding: 10px 12px;
      background: #f5f7fa;
      line-height: 1.55;
    }
    .status.success { color: #087455; background: #eaf8f2; }
    .status.error { color: #b42318; background: #fff0ef; }
    #profileSelect { font-weight: 700; }
    #createBtn { width: 100%; }
    .task-actions {
      position: sticky;
      bottom: env(safe-area-inset-bottom);
      z-index: 4;
      padding-top: 10px;
      background: linear-gradient(180deg, rgba(255,255,255,0), #fff 20%);
    }
    .toast { border-radius: 14px; }
    @media (max-width: 370px) {
      body { padding-left: 10px; padding-right: 10px; }
      .hero { padding: 19px 15px; }
      .card { padding: 14px; }
      .grid.two { grid-template-columns: 1fr; gap: 10px; }
      .card-head { align-items: flex-start; }
    }
  </style>
</head>
<body>
  <div class="wrap">
    <div id="toast" class="toast hidden"></div>
    <header class="hero">
      <div class="logo">AT</div>
      <div>
        <h1>منشئ المهام اليومية</h1>
        <p class="sub">سجّل وقتك في Azure Boards بسهولة</p>
      </div>
    </header>

    <section class="card">
      <div class="card-head">
        <h2 class="card-title">حساب Azure</h2>
        <button class="ghost" id="addUserBtn" type="button">＋ إضافة حساب</button>
      </div>
      <div class="field">
        <label for="profileSelect">الحساب المستخدم</label>
        <select id="profileSelect"></select>
        <p class="hint">الحسابات محفوظة على هذا الجهاز فقط.</p>
      </div>
    </section>

    <section class="card hidden" id="userFormCard">
      <div class="card-head">
          <h2 class="card-title">إضافة حساب Azure</h2>
      </div>
      <div class="grid two">
        <div class="field full">
          <label for="newUser">اسم المستخدم في Azure</label>
          <input id="newUser" placeholder="Name <email@domain.com>" />
        </div>
        <div class="field full">
          <label for="newPat">رمز الوصول الشخصي (PAT)</label>
          <input id="newPat" type="password" />
          <p class="hint">يُحفظ الرمز في متصفح هذا الجهاز ويُرسل عند إنشاء المهمة.</p>
        </div>
        <div class="field">
          <label for="newOrg">المنظمة</label>
          <input id="newOrg" />
        </div>
        <div class="field">
          <label for="newProject">المشروع</label>
          <input id="newProject" />
        </div>
        <div class="field full">
          <label for="newManager">المدير المباشر</label>
          <input id="newManager" />
        </div>
      </div>
      <div class="row" style="margin-top:14px">
        <button class="ok" id="saveUserBtn" type="button">حفظ الحساب على الجهاز</button>
        <button class="secondary" id="cancelUserBtn" type="button">إلغاء</button>
      </div>
    </section>

    <section class="card">
      <div class="card-head">
        <h2 class="card-title">بيانات المهمة</h2>
        <span class="badge">التسجيل 9:00 م</span>
      </div>
      <div class="grid two">
        <div class="field">
          <label for="org">المنظمة</label>
          <input id="org" />
        </div>
        <div class="field">
          <label for="project">المشروع</label>
          <input id="project" />
        </div>
        <div class="field full">
          <label for="manager">المدير المباشر</label>
          <input id="manager" />
        </div>
        <div class="field full">
          <label for="user">المستخدم المكلّف</label>
          <input id="user" />
        </div>
        <div class="field">
          <label for="date">تاريخ المهمة</label>
          <input id="date" type="date" />
          <p class="hint">وقت نهاية المهمة ثابت: 9:00 مساءً</p>
        </div>
        <div class="field">
          <label for="hours">ساعات العمل</label>
          <input id="hours" inputmode="decimal" />
        </div>
        <div class="field full">
          <label for="title">وصف المهمة</label>
          <input id="title" />
        </div>
      </div>
      <div class="task-actions">
        <button class="primary" id="createBtn" type="button">إنشاء / تحديث المهمة</button>
      </div>
      <p class="status" id="status" role="status" aria-live="polite">جاهز</p>
    </section>
  </div>

  <script>
    const defaults = __DEFAULTS__;
    let state = { profiles: [], active_profile: "" };
    const localStateKey = "azureTaskCreatorState";
    const profileSelectEl = document.getElementById("profileSelect");
    const statusEl = document.getElementById("status");
    const toastEl = document.getElementById("toast");
    const orgInput = document.getElementById("org");
    const projectInput = document.getElementById("project");
    const managerInput = document.getElementById("manager");
    const userInput = document.getElementById("user");
    const dateInput = document.getElementById("date");
    const hoursInput = document.getElementById("hours");
    const titleInput = document.getElementById("title");
    const addUserButtonEl = document.getElementById("addUserBtn");
    const userFormCardEl = document.getElementById("userFormCard");
    const newUserInput = document.getElementById("newUser");
    const newPatInput = document.getElementById("newPat");
    const newOrgInput = document.getElementById("newOrg");
    const newProjectInput = document.getElementById("newProject");
    const newManagerInput = document.getElementById("newManager");
    const cancelUserButtonEl = document.getElementById("cancelUserBtn");
    const saveUserButtonEl = document.getElementById("saveUserBtn");
    const createButtonEl = document.getElementById("createBtn");

    function saveLocalState() {
      localStorage.setItem(localStateKey, JSON.stringify(state));
    }

    function fillTaskForm(profile) {
      if (!profile) return;
      orgInput.value = profile.org || defaults.org;
      projectInput.value = profile.project || defaults.project;
      managerInput.value = profile.manager || defaults.manager;
      userInput.value = profile.user || "";
    }

    function showToast(text) {
      toastEl.textContent = text;
      toastEl.classList.remove("hidden");
      setTimeout(() => toastEl.classList.add("hidden"), 4000);
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
      profileSelectEl.innerHTML = "";
      if (!state.profiles.length) {
        const opt = document.createElement("option");
        opt.value = "";
        opt.textContent = "أضف مستخدمًا لحفظ بياناته على هذا الهاتف";
        profileSelectEl.appendChild(opt);
      }
      state.profiles.forEach((p) => {
        const opt = document.createElement("option");
        opt.value = p.id;
        opt.textContent = p.label || p.user;
        if (p.id === state.active_profile) opt.selected = true;
        profileSelectEl.appendChild(opt);
      });
      const active = state.profiles.find((p) => p.id === state.active_profile);
      fillTaskForm(active);
    }

    async function loadState() {
      try {
        const saved = JSON.parse(localStorage.getItem(localStateKey) || "{}");
        state = {
          profiles: Array.isArray(saved.profiles) ? saved.profiles : [],
          active_profile: saved.active_profile || ""
        };
      } catch {
        state = { profiles: [], active_profile: "" };
      }
      renderProfiles();
      if (!state.profiles.length) {
        statusEl.textContent = "ابدأ بإضافة حساب Azure، ثم احفظ المهمة من هنا.";
      }
    }

    addUserButtonEl.onclick = () => {
      userFormCardEl.classList.remove("hidden");
      newUserInput.value = "";
      newPatInput.value = "";
      newOrgInput.value = defaults.org;
      newProjectInput.value = defaults.project;
      newManagerInput.value = defaults.manager;
    };
    cancelUserButtonEl.onclick = () => userFormCardEl.classList.add("hidden");

    saveUserButtonEl.onclick = async () => {
      statusEl.textContent = "جارٍ حفظ الحساب على هذا الجهاز...";
      saveUserButtonEl.disabled = true;
      const originalButtonText = saveUserButtonEl.textContent;
      saveUserButtonEl.textContent = "جارٍ الحفظ...";
      try {
        const profile = {
          id: crypto.randomUUID ? crypto.randomUUID() : String(Date.now()),
          label: newUserInput.value.trim(),
          user: newUserInput.value.trim(),
          pat: newPatInput.value.trim(),
          org: newOrgInput.value.trim() || defaults.org,
          project: newProjectInput.value.trim() || defaults.project,
          manager: newManagerInput.value.trim() || defaults.manager
        };
        if (!profile.user || !profile.pat) throw new Error("أدخل اسم المستخدم وPAT.");
        if (profile.pat.length < 20) throw new Error("PAT قصير جدًا؛ أدخل الرمز كاملًا.");
        const existingIndex = state.profiles.findIndex((p) =>
          (p.user || "").toLowerCase() === profile.user.toLowerCase()
        );
        if (existingIndex >= 0) {
          profile.id = state.profiles[existingIndex].id;
          state.profiles[existingIndex] = profile;
        } else {
          state.profiles.push(profile);
        }
        state.active_profile = profile.id;
        saveLocalState();
        renderProfiles();
        statusEl.className = "status success";
        statusEl.textContent = "تم حفظ المستخدم على هذا الهاتف.";
        showToast("تم حفظ الحساب على هذا الجهاز");
        userFormCardEl.classList.add("hidden");
      } catch (error) {
        statusEl.className = "status error";
        statusEl.textContent = error.message || "تعذر حفظ البيانات في المتصفح.";
      } finally {
        saveUserButtonEl.disabled = false;
        saveUserButtonEl.textContent = originalButtonText;
      }
    };

    profileSelectEl.onchange = () => {
      state.active_profile = profileSelectEl.value;
      try {
        saveLocalState();
        fillTaskForm(state.profiles.find((p) => p.id === state.active_profile));
      } catch (error) {
        statusEl.className = "status error";
        statusEl.textContent = error.message || "تعذر حفظ الاختيار على هذا الهاتف.";
      }
    };

    createButtonEl.onclick = async () => {
      statusEl.textContent = "جارٍ إرسال المهمة إلى Azure...";
      createButtonEl.disabled = true;
      const originalButtonText = createButtonEl.textContent;
      createButtonEl.textContent = "جارٍ الحفظ في Azure...";
      try {
        const profile = state.profiles.find((p) => p.id === state.active_profile);
        if (!profile) throw new Error("احفظ بيانات المستخدم أولًا على هذا الهاتف.");
        const data = await requestJson("/api/create", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            org: orgInput.value,
            project: projectInput.value,
            manager: managerInput.value,
            user: userInput.value,
            date: dateInput.value,
            title: titleInput.value,
            hours: hoursInput.value,
            pat: profile.pat
          })
        });
        statusEl.className = "status " + (data.ok ? "success" : "error");
        statusEl.textContent = data.message || "Done";
        if (data.ok) showToast("تم حفظ المهمة بنجاح");
      } catch (error) {
        statusEl.className = "status error";
        statusEl.textContent = error.message || "تعذر الاتصال بالسيرفر.";
      } finally {
        createButtonEl.disabled = false;
        createButtonEl.textContent = originalButtonText;
      }
    };

    function localDateValue() {
      const now = new Date();
      const year = now.getFullYear();
      const month = String(now.getMonth() + 1).padStart(2, "0");
      const day = String(now.getDate()).padStart(2, "0");
      return year + "-" + month + "-" + day;
    }
    dateInput.value = localDateValue();
    titleInput.value = defaults.title;
    hoursInput.value = defaults.hours;
    loadState().catch((error) => {
      statusEl.className = "status error";
      statusEl.textContent = error.message || "تعذر تحميل البيانات من السيرفر.";
    });
  </script>
</body>
</html>
"""

MANIFEST = {
    "name": "Azure Task Creator",
    "short_name": "Azure Task",
    "description": "إنشاء وتحديث المهام اليومية في Azure Boards",
    "start_url": "/",
    "scope": "/",
    "display": "standalone",
    "background_color": "#1e3a8a",
    "theme_color": "#1e3a8a",
    "icons": [
      {"src": "/icons/icon-192.png", "sizes": "192x192", "type": "image/png", "purpose": "any"},
      {"src": "/icons/icon-512.png", "sizes": "512x512", "type": "image/png", "purpose": "any maskable"},
  ],
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
        icon_files = {
            "/apple-touch-icon.png": "apple-touch-icon.png",
            "/icons/icon-192.png": "icon-192.png",
            "/icons/icon-512.png": "icon-512.png",
        }
        if path in icon_files:
            icon_path = os.path.join(os.path.dirname(__file__), "static", icon_files[path])
            try:
                with open(icon_path, "rb") as icon_file:
                    body = icon_file.read()
            except OSError:
                self.send_error(404)
                return
            self.send_response(200)
            self.send_header("Content-Type", "image/png")
            self.send_header("Content-Length", str(len(body)))
            self.send_header("Cache-Control", "public, max-age=86400")
            self.end_headers()
            self.wfile.write(body)
            return
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
        if path == "/api/create":
            selected_org = (payload.get("org") or "").strip()
            selected_project = (payload.get("project") or "").strip()
            selected_manager = (payload.get("manager") or "").strip()
            selected_user = (payload.get("user") or "").strip()
            selected_pat = (payload.get("pat") or "").strip()
            title = (payload.get("title") or "").strip()
            if not all([selected_org, selected_project, selected_manager, selected_user, title, selected_pat]):
                _json_response(self, {"ok": False, "message": "All task fields and PAT are required."}, 400)
                return
            valid, error = validate_pat(selected_pat)
            if not valid:
                _json_response(self, {"ok": False, "message": error}, 400)
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
                selected_pat,
            )
            _json_response(self, {"ok": success, "message": message}, 200 if success else 400)
            return

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
