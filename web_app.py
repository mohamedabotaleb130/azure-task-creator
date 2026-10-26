import json
import os
import requests
import socket
import threading
from datetime import datetime
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import quote, urlparse

from task_core import (
    DEFAULT_MANAGER,
    DEFAULT_TITLE,
    ORG,
    PROJECT,
    WORK_HOURS,
    create_task,
    get_active_profile,
    get_headers_for_create,
    get_headers_for_query,
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
    .wrap { max-width: 1120px; }
    .hero { align-items: center; min-height: 142px; padding: 24px 28px; }
    .hero-copy { position: relative; z-index: 1; flex: 1; }
    .eyebrow, .section-kicker {
      margin: 0 0 4px;
      color: #7991b2;
      font-size: 10px;
      font-weight: 800;
      letter-spacing: .12em;
    }
    .hero .eyebrow { color: #a9c1e2; }
    .hero-date {
      position: relative;
      z-index: 1;
      flex: 0 0 auto;
      padding: 9px 13px;
      color: #edf4ff;
      background: rgba(255,255,255,.11);
      border: 1px solid rgba(255,255,255,.14);
      border-radius: 12px;
      font-size: 13px;
      font-weight: 800;
    }
    .dashboard-summary {
      display: grid;
      grid-template-columns: repeat(4, minmax(0,1fr));
      gap: 12px;
      margin-bottom: 14px;
    }
    .summary-card {
      min-width: 0;
      padding: 14px 16px;
      border: 1px solid #e5ecf4;
      border-radius: 17px;
      background: #fff;
      box-shadow: 0 5px 16px rgba(16,36,61,.045);
    }
    .summary-card span, .summary-card strong { display: block; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
    .summary-card span { color: #77869a; font-size: 12px; font-weight: 700; }
    .summary-card strong { margin-top: 5px; color: #213a59; font-size: 15px; }
    .dashboard-grid { display: grid; grid-template-columns: minmax(0,1.55fr) minmax(290px,.82fr); gap: 14px; align-items: start; }
    .main-column, .side-column { display: grid; gap: 12px; min-width: 0; }
    .card { margin-bottom: 0; }
    .task-card { padding: 22px; }
    .task-card .card-head { align-items: center; }
    .section-kicker { color: #7790b0; }
    .section-help { margin: -3px 0 17px; color: #718096; font-size: 13px; line-height: 1.6; }
    .subtle-badge { color: #65758a; background: #f2f5f9; }
    .form-actions { margin-top: 13px; }
    .form-actions button { flex: 1; }
    .account-hint { margin-top: 9px; }
    .guide-card ol { margin: 12px 0; padding-right: 22px; color: #40536b; line-height: 1.9; font-size: 13px; }
    .history-list { display: grid; gap: 9px; }
    .history-item {
      display: grid;
      grid-template-columns: minmax(0,1fr) auto;
      align-items: center;
      gap: 8px;
      padding: 11px 12px;
      border: 1px solid #e9eef5;
      border-radius: 13px;
      background: #fbfcfe;
    }
    .history-title { overflow: hidden; text-overflow: ellipsis; white-space: nowrap; color: #253b56; font-size: 14px; font-weight: 800; }
    .history-meta { margin-top: 3px; color: #77869a; font-size: 11px; }
    .history-action { color: #087455; background: #eaf8f2; border-radius: 999px; padding: 5px 8px; font-size: 11px; font-weight: 800; white-space: nowrap; }
    .history-empty { padding: 18px 12px; border-radius: 13px; background: #f7f9fc; color: #77869a; text-align: center; font-size: 13px; }
    .query-dashboard { margin: 0 0 14px; padding: 20px; }
    .query-stats { display: grid; grid-template-columns: repeat(3,minmax(0,1fr)); gap: 10px; margin-bottom: 14px; }
    .query-stat { padding: 13px 15px; border: 1px solid #e5ecf4; border-radius: 15px; background: #f8fafc; }
    .query-stat span, .query-stat strong { display: block; }
    .query-stat span { color: #77869a; font-size: 12px; font-weight: 700; }
    .query-stat strong { margin-top: 4px; color: #213a59; font-size: 22px; }
    .query-tools { display: flex; align-items: center; justify-content: space-between; gap: 10px; margin: 10px 0 14px; }
    .query-tools p { margin: 0; color: #718096; font-size: 12px; }
    .query-state-list { display: flex; flex-wrap: wrap; gap: 8px; margin: 0 0 14px; }
    .query-state-chip { border-radius: 999px; background: #eef4ff; color: #274a80; padding: 6px 10px; font-size: 12px; font-weight: 800; }
    .query-table-wrap { overflow-x: auto; border: 1px solid #e6edf5; border-radius: 13px; }
    .query-table { width: 100%; min-width: 560px; border-collapse: collapse; text-align: right; font-size: 13px; }
    .query-table th, .query-table td { padding: 10px 12px; border-bottom: 1px solid #edf1f6; }
    .query-table th { background: #f7f9fc; color: #60738d; font-size: 11px; white-space: nowrap; }
    .query-table tr:last-child td { border-bottom: 0; }
    .query-table a { color: #1d4ed8; font-weight: 800; text-decoration: none; }
    .query-table td { vertical-align: middle; }
    .query-state-badge { display: inline-flex; align-items: center; gap: 6px; border: 1px solid #d5dce6; border-radius: 999px; padding: 4px 9px; font-size: 11px; font-weight: 800; white-space: nowrap; }
    .query-state-badge::before { content: ""; width: 7px; height: 7px; border-radius: 50%; background: currentColor; }
    .query-state-badge.category-proposed { color: #526174; background: #f1f4f8; border-color: #d7dee8; }
    .query-state-badge.category-inprogress { color: #1559b7; background: #eaf3ff; border-color: #bfd8fa; }
    .query-state-badge.category-resolved { color: #a9580a; background: #fff4df; border-color: #f1d49b; }
    .query-state-badge.category-completed { color: #087455; background: #e7f8f1; border-color: #b6e8d3; }
    .query-state-badge.category-removed { color: #7c3aed; background: #f2eefe; border-color: #d9ccfa; }
    .query-state-chip.category-proposed { color: #526174; background: #f1f4f8; }
    .query-state-chip.category-inprogress { color: #1559b7; background: #eaf3ff; }
    .query-state-chip.category-resolved { color: #a9580a; background: #fff4df; }
    .query-state-chip.category-completed { color: #087455; background: #e7f8f1; }
    .query-state-chip.category-removed { color: #7c3aed; background: #f2eefe; }
    .query-state-control { display: flex; align-items: center; gap: 5px; min-width: 210px; }
    .query-state-control select { min-width: 118px; width: auto; padding: 7px 9px; border-radius: 9px; font-size: 12px; }
    .query-state-save { padding: 8px 10px; color: #fff; background: #1d4ed8; border-radius: 9px; font-size: 12px; white-space: nowrap; }
    .query-state-save:disabled { opacity: .55; cursor: wait; }
    .query-loading { padding: 17px 12px; color: #77869a; text-align: center; }
    .query-error { color: #b42318; background: #fff5f4; border-radius: 12px; padding: 12px; font-size: 13px; }
    @media (max-width: 820px) {
      .dashboard-grid { grid-template-columns: 1fr; }
      .side-column { order: -1; }
      .dashboard-summary { grid-template-columns: repeat(2,minmax(0,1fr)); }
      .query-stats { grid-template-columns: repeat(3,minmax(0,1fr)); gap: 7px; }
      .query-stat { padding: 10px; }
      .query-stat strong { font-size: 19px; }
    }
    @media (max-width: 540px) {
      .wrap { max-width: 100%; }
      .hero { min-height: auto; padding: 18px 15px; gap: 10px; }
      .hero-date { display: none; }
      .hero h1 { font-size: 20px; }
      .sub { font-size: 12px; }
      .dashboard-summary { gap: 8px; margin-bottom: 10px; }
      .query-dashboard { padding: 15px; }
      .query-tools { align-items: flex-start; flex-direction: column; }
      .summary-card { padding: 11px 12px; }
      .summary-card strong { font-size: 14px; }
      .task-card { padding: 16px; }
    }
  </style>
</head>
<body>
  <div class="wrap">
    <div id="toast" class="toast hidden"></div>
    <header class="hero">
      <div class="logo">AT</div>
      <div class="hero-copy">
        <p class="eyebrow">AZURE BOARDS</p>
        <h1>لوحة المهام اليومية</h1>
        <p class="sub">أنشئ سجلك اليومي وتابع آخر العمليات من مكان واحد.</p>
      </div>
      <div class="hero-date" id="heroDate"></div>
    </header>

    <section class="dashboard-summary" aria-label="ملخص سريع">
      <article class="summary-card"><span>الحساب النشط</span><strong id="activeAccountSummary">لا يوجد</strong></article>
      <article class="summary-card"><span>المشروع</span><strong id="projectSummary">—</strong></article>
      <article class="summary-card"><span>التاريخ</span><strong id="dateSummary">—</strong></article>
      <article class="summary-card"><span>وقت التسجيل</span><strong>9:00 مساءً</strong></article>
    </section>

    <section class="card query-dashboard" aria-label="لوحة استعلام Azure">
      <div class="card-head">
        <div>
          <p class="section-kicker">HRDF-2026</p>
          <h2 class="card-title">لوحة متابعة الاستعلام</h2>
        </div>
        <span class="badge">Azure DevOps</span>
      </div>
      <div class="query-tools">
        <p id="queryUpdatedAt">اضغط تحديث لعرض البيانات الحالية من الاستعلام.</p>
        <button class="primary" id="refreshQueryBtn" type="button" style="flex:0 0 auto">تحديث البيانات</button>
      </div>
      <div class="query-stats" aria-live="polite">
        <article class="query-stat"><span>إجمالي العناصر</span><strong id="queryTotal">—</strong></article>
        <article class="query-stat"><span>قيد التنفيذ</span><strong id="queryActive">—</strong></article>
        <article class="query-stat"><span>مكتملة</span><strong id="queryDone">—</strong></article>
      </div>
      <div id="queryStateList" class="query-state-list"></div>
      <div id="queryResults" class="query-loading">بيانات الاستعلام لم تُحمّل بعد.</div>
    </section>

    <div class="dashboard-grid">
      <main class="main-column">
        <section class="card task-card">
          <div class="card-head">
            <div>
              <p class="section-kicker">تسجيل يومي</p>
              <h2 class="card-title">إنشاء مهمة</h2>
            </div>
            <span class="badge">وقت النهاية 9:00 م</span>
          </div>
          <p class="section-help">راجع التفاصيل ثم احفظها في Azure Boards. إذا كانت هناك مهمة لليوم نفسه، سيحدّثها التطبيق.</p>
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
            <button class="primary" id="createBtn" type="button">حفظ المهمة في Azure</button>
          </div>
          <p class="status" id="status" role="status" aria-live="polite">اختر حساب Azure للبدء.</p>
        </section>

        <section class="card activity-card">
          <div class="card-head">
            <div>
              <p class="section-kicker">سجل الجهاز</p>
              <h2 class="card-title">آخر العمليات</h2>
            </div>
            <span class="badge subtle-badge">محفوظ محليًا</span>
          </div>
          <div id="historyList" class="history-list"></div>
        </section>
      </main>

      <aside class="side-column">
        <section class="card account-card">
          <div class="card-head">
            <div>
              <p class="section-kicker">إعداد الاتصال</p>
              <h2 class="card-title">حساب Azure</h2>
            </div>
            <button class="ghost" id="addUserBtn" type="button">＋ إضافة</button>
          </div>
          <div class="field">
            <label for="profileSelect">الحساب المستخدم</label>
            <select id="profileSelect"></select>
          </div>
          <p class="hint account-hint">بيانات الحساب وPAT محفوظة في متصفح هذا الجهاز.</p>
        </section>

        <section class="card hidden" id="userFormCard">
          <div class="card-head">
            <div>
              <p class="section-kicker">حساب جديد</p>
              <h2 class="card-title">إضافة حساب Azure</h2>
            </div>
          </div>
          <div class="grid two">
            <div class="field full">
              <label for="newUser">اسم المستخدم في Azure</label>
              <input id="newUser" placeholder="Name <email@domain.com>" />
            </div>
            <div class="field full">
              <label for="newPat">رمز الوصول الشخصي (PAT)</label>
              <input id="newPat" type="password" autocomplete="new-password" />
              <p class="hint">يُرسل الرمز إلى الخادم فقط عند حفظ مهمة.</p>
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
          <div class="row form-actions">
            <button class="ok" id="saveUserBtn" type="button">حفظ الحساب على الجهاز</button>
            <button class="secondary" id="cancelUserBtn" type="button">إلغاء</button>
          </div>
        </section>

        <section class="card guide-card">
          <p class="section-kicker">خطوات سريعة</p>
          <h2 class="card-title">طريقة الاستخدام</h2>
          <ol>
            <li>اختر حساب Azure أو أضف حسابًا.</li>
            <li>راجع المشروع والتاريخ والساعات.</li>
            <li>اضغط «حفظ المهمة في Azure».</li>
          </ol>
          <p class="hint">يمكنك فتح التطبيق من خارج المكتب باستخدام الإنترنت.</p>
        </section>
      </aside>
    </div>
  </div>

  <script>
    const defaults = __DEFAULTS__;
    let state = { profiles: [], active_profile: "" };
    const localStateKey = "azureTaskCreatorState";
    const historyKey = "azureTaskCreatorHistory";
    const activeAccountSummaryEl = document.getElementById("activeAccountSummary");
    const projectSummaryEl = document.getElementById("projectSummary");
    const dateSummaryEl = document.getElementById("dateSummary");
    const heroDateEl = document.getElementById("heroDate");
    const historyListEl = document.getElementById("historyList");
    const refreshQueryButtonEl = document.getElementById("refreshQueryBtn");
    const queryId = "a417b767-a2a0-4f4a-b66a-1e1704878837";
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
      if (profile) {
        orgInput.value = profile.org || defaults.org;
        projectInput.value = profile.project || defaults.project;
        managerInput.value = profile.manager || defaults.manager;
        userInput.value = profile.user || "";
      }
      renderDashboardSummary(profile);
    }

    function displayDate(value) {
      if (!value) return "—";
      const parts = value.split("-");
      return parts.length === 3 ? `${parts[2]}/${parts[1]}/${parts[0]}` : value;
    }

    function renderDashboardSummary(profile) {
      activeAccountSummaryEl.textContent = profile ? (profile.label || profile.user || "نشط") : "لا يوجد";
      projectSummaryEl.textContent = projectInput.value.trim() || "—";
      dateSummaryEl.textContent = displayDate(dateInput.value);
      heroDateEl.textContent = displayDate(dateInput.value);
    }

    function renderHistory() {
      let entries = [];
      try {
        const saved = JSON.parse(localStorage.getItem(historyKey) || "[]");
        if (Array.isArray(saved)) entries = saved.slice(0, 8);
      } catch { /* Keep the dashboard usable if local history is unavailable. */ }
      historyListEl.innerHTML = "";
      if (!entries.length) {
        const empty = document.createElement("p");
        empty.className = "history-empty";
        empty.textContent = "ستظهر هنا المهام التي تحفظها من هذا الجهاز.";
        historyListEl.appendChild(empty);
        return;
      }
      entries.forEach((entry) => {
        const item = document.createElement("article");
        item.className = "history-item";
        const title = document.createElement("strong");
        title.className = "history-title";
        title.textContent = entry.title || "مهمة يومية";
        const meta = document.createElement("span");
        meta.className = "history-meta";
        meta.textContent = [entry.user, entry.project, displayDate(entry.date), entry.hours ? `${entry.hours} ساعة` : ""]
          .filter(Boolean).join(" · ");
        const result = document.createElement("span");
        result.className = "history-action";
        result.textContent = "✓ تم الحفظ في Azure";
        item.append(title, meta, result);
        historyListEl.appendChild(item);
      });
    }

    function saveHistory(entry) {
      try {
        const entries = JSON.parse(localStorage.getItem(historyKey) || "[]");
        const safeEntries = Array.isArray(entries) ? entries : [];
        safeEntries.unshift(entry);
        localStorage.setItem(historyKey, JSON.stringify(safeEntries.slice(0, 8)));
        renderHistory();
      } catch { /* Azure save is successful even if local history cannot be written. */ }
    }

    function fieldValue(fields, referenceName) {
      const value = fields[referenceName];
      if (value && typeof value === "object") return value.displayName || value.name || "";
      return value == null ? "" : String(value);
    }

    function renderQueryDashboard(data) {
      const items = data.items || [];
      const counts = {};
      const stateCatalog = data.statesByType || {};
      items.forEach((item) => {
        const stateName = fieldValue(item.fields || {}, "System.State") || "غير محدد";
        counts[stateName] = (counts[stateName] || 0) + 1;
      });
      const completedNames = new Set(Object.values(stateCatalog).flat().filter((stateItem) => (stateItem.category || "").toLowerCase() === "completed").map((stateItem) => stateItem.name));
      const activeNames = new Set(Object.values(stateCatalog).flat().filter((stateItem) => ["proposed", "inprogress"].includes((stateItem.category || "").toLowerCase())).map((stateItem) => stateItem.name));
      const doneCount = Object.entries(counts).filter(([name]) => completedNames.size ? completedNames.has(name) : /done|closed|completed|مكتمل|مغلق/i.test(name)).reduce((sum, [, count]) => sum + count, 0);
      const activeCount = activeNames.size ? Object.entries(counts).filter(([name]) => activeNames.has(name)).reduce((sum, [, count]) => sum + count, 0) : Math.max(0, data.total - doneCount);
      document.getElementById("queryTotal").textContent = data.total;
      document.getElementById("queryActive").textContent = activeCount;
      document.getElementById("queryDone").textContent = doneCount;
      const stateList = document.getElementById("queryStateList");
      stateList.innerHTML = "";
      Object.entries(counts).sort((a, b) => b[1] - a[1]).forEach(([name, count]) => {
        const chip = document.createElement("span");
        chip.className = "query-state-chip";
        chip.textContent = `${name}: ${count}`;
        const stateInfo = Object.values(stateCatalog).flat().find((candidate) => candidate.name === name);
        if (stateInfo) chip.classList.add(`category-${(stateInfo.category || "").toLowerCase().replace(/[^a-z]/g, "")}`);
        if (stateInfo && /^[0-9a-f]{6}$/i.test(stateInfo.color || "")) {
          chip.style.border = `1px solid #${stateInfo.color}`;
        }
        stateList.appendChild(chip);
      });
      const results = document.getElementById("queryResults");
      results.className = "query-table-wrap";
      results.innerHTML = "";
      if (!items.length) {
        results.className = "query-loading";
        results.textContent = "لا توجد عناصر في نتائج الاستعلام.";
      } else {
        const table = document.createElement("table");
        table.className = "query-table";
        const columns = (data.columns || []).filter((column) => column.referenceName && column.referenceName !== "System.Id" && column.referenceName !== "System.State").slice(0, 6);
        const head = document.createElement("tr");
        const idHead = document.createElement("th"); idHead.textContent = "الرقم"; head.appendChild(idHead);
        const stateHead = document.createElement("th"); stateHead.textContent = "الحالة"; head.appendChild(stateHead);
        columns.forEach((column) => { const th = document.createElement("th"); th.textContent = column.name || column.referenceName; head.appendChild(th); });
        const actionHead = document.createElement("th"); actionHead.textContent = "تغيير الحالة"; head.appendChild(actionHead);
        const thead = document.createElement("thead"); thead.appendChild(head); table.appendChild(thead);
        const tbody = document.createElement("tbody");
        items.forEach((item) => {
          const row = document.createElement("tr");
          const idCell = document.createElement("td");
          const link = document.createElement("a");
          link.href = `https://dev.azure.com/${encodeURIComponent(data.org)}/${encodeURIComponent(data.project)}/_workitems/edit/${item.id}`;
          link.target = "_blank"; link.rel = "noopener noreferrer"; link.textContent = `#${item.id}`;
          idCell.appendChild(link); row.appendChild(idCell);
          const itemFields = item.fields || {};
          const itemType = fieldValue(itemFields, "System.WorkItemType") || "Task";
          const currentState = fieldValue(itemFields, "System.State");
          const states = stateCatalog[itemType] || [{ name: currentState || "غير محدد", color: "64748b", category: "" }];
          const stateCell = document.createElement("td");
          const badge = document.createElement("span");
          const currentStateInfo = states.find((stateItem) => stateItem.name === currentState);
          badge.className = "query-state-badge";
          badge.textContent = currentState || "غير محدد";
          if (currentStateInfo) badge.classList.add(`category-${(currentStateInfo.category || "").toLowerCase().replace(/[^a-z]/g, "")}`);
          if (currentStateInfo && /^[0-9a-f]{6}$/i.test(currentStateInfo.color || "")) {
            badge.style.color = `#${currentStateInfo.color}`;
            badge.style.borderColor = `#${currentStateInfo.color}`;
          }
          stateCell.appendChild(badge); row.appendChild(stateCell);
          columns.forEach((column) => { const cell = document.createElement("td"); cell.textContent = fieldValue(item.fields || {}, column.referenceName); row.appendChild(cell); });
          const actionCell = document.createElement("td");
          const controls = document.createElement("div"); controls.className = "query-state-control";
          const select = document.createElement("select"); select.setAttribute("aria-label", `الحالة الجديدة للمهمة ${item.id}`);
          states.forEach((stateItem) => {
            const option = document.createElement("option"); option.value = stateItem.name; option.textContent = stateItem.name;
            if (stateItem.name === currentState) option.selected = true;
            select.appendChild(option);
          });
          const saveButton = document.createElement("button"); saveButton.className = "query-state-save"; saveButton.type = "button"; saveButton.textContent = "حفظ الحالة";
          saveButton.onclick = async () => {
            if (select.value === currentState) { showToast("الحالة لم تتغير"); return; }
            const activeProfile = state.profiles.find((p) => p.id === state.active_profile);
            if (!activeProfile) { showToast("اختر حساب Azure أولًا"); return; }
            saveButton.disabled = true; saveButton.textContent = "جارٍ الحفظ...";
            try {
              await requestJson("/api/update-state", {
                method: "POST", headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ org: data.org, project: data.project, pat: activeProfile.pat, id: item.id, state: select.value })
              });
              itemFields["System.State"] = select.value;
              renderQueryDashboard(data);
              showToast(`تم تغيير حالة المهمة #${item.id}`);
            } catch (error) {
              saveButton.disabled = false; saveButton.textContent = "حفظ الحالة";
              showToast(error.message || "تعذر تغيير الحالة");
            }
          };
          controls.append(select, saveButton); actionCell.appendChild(controls); row.appendChild(actionCell);
          tbody.appendChild(row);
        });
        table.appendChild(tbody); results.appendChild(table);
      }
      document.getElementById("queryUpdatedAt").textContent = `آخر تحديث: ${new Date().toLocaleString("ar-EG")} · المعروض ${items.length} من ${data.total}`;
    }

    refreshQueryButtonEl.onclick = async () => {
      const profile = state.profiles.find((p) => p.id === state.active_profile);
      const results = document.getElementById("queryResults");
      if (!profile) {
        results.className = "query-error";
        results.textContent = "أضف حساب Azure أولًا لعرض نتائج الاستعلام.";
        return;
      }
      refreshQueryButtonEl.disabled = true;
      results.className = "query-loading";
      results.textContent = "جارٍ تحميل النتائج من Azure DevOps...";
      try {
        const data = await requestJson("/api/query-dashboard", {
          method: "POST", headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ org: orgInput.value, project: projectInput.value, pat: profile.pat, query_id: queryId })
        });
        renderQueryDashboard(data);
      } catch (error) {
        results.className = "query-error";
        results.textContent = error.message || "تعذر تحميل بيانات الاستعلام.";
      } finally {
        refreshQueryButtonEl.disabled = false;
      }
    };

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
      renderHistory();
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
        if (data.ok) {
          saveHistory({
            title: titleInput.value.trim(),
            user: userInput.value.trim(),
            project: projectInput.value.trim(),
            date: dateInput.value,
            hours: hoursInput.value.trim()
          });
          showToast("تم حفظ المهمة بنجاح");
        }
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
    projectInput.addEventListener("input", () => renderDashboardSummary(state.profiles.find((p) => p.id === state.active_profile)));
    dateInput.addEventListener("input", () => renderDashboardSummary(state.profiles.find((p) => p.id === state.active_profile)));
    renderDashboardSummary(null);
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
        if path == "/api/query-dashboard":
            selected_org = (payload.get("org") or "").strip()
            selected_project = (payload.get("project") or "").strip()
            selected_pat = (payload.get("pat") or "").strip()
            query_id = (payload.get("query_id") or "").strip()
            if not all([selected_org, selected_project, selected_pat]) or query_id != "a417b767-a2a0-4f4a-b66a-1e1704878837":
                _json_response(self, {"ok": False, "message": "أدخل بيانات الحساب الصحيحة لعرض الاستعلام."}, 400)
                return
            valid, error = validate_pat(selected_pat)
            if not valid:
                _json_response(self, {"ok": False, "message": error}, 400)
                return
            headers = get_headers_for_query(selected_pat)
            base_url = f"https://dev.azure.com/{selected_org}/{selected_project}/_apis/wit"
            try:
                query_response = requests.get(
                    f"{base_url}/wiql/{query_id}",
                    params={"$top": 2000, "api-version": "7.1"}, headers=headers, timeout=30
                )
                if not query_response.ok:
                    message = "تعذر قراءة الاستعلام من Azure DevOps. تحقق من صلاحية PAT (Work Items: Read) ومشاركة الاستعلام."
                    _json_response(self, {"ok": False, "message": message}, 400)
                    return
                query_data = query_response.json()
                references = [int(item["id"]) for item in query_data.get("workItems", []) if item.get("id")]
                query_columns = query_data.get("columns", [])
                fields = list(dict.fromkeys(
                    [column.get("referenceName") for column in query_columns if column.get("referenceName")]
                    + ["System.Id", "System.Title", "System.State", "System.AssignedTo", "System.WorkItemType"]
                ))
                work_items = []
                for offset in range(0, len(references), 200):
                    batch_response = requests.post(
                        f"{base_url}/workitemsbatch", params={"api-version": "7.1"}, headers=headers,
                        json={"ids": references[offset:offset + 200], "fields": fields}, timeout=30
                    )
                    if not batch_response.ok:
                        _json_response(self, {"ok": False, "message": "تم تشغيل الاستعلام لكن تعذر تحميل تفاصيل عناصره."}, 502)
                        return
                    work_items.extend(batch_response.json().get("value", []))
                states_by_type = {}
                work_types = {str(item.get("fields", {}).get("System.WorkItemType") or "Task") for item in work_items}
                for work_type in work_types:
                    states_response = requests.get(
                        f"{base_url}/workitemtypes/{quote(work_type, safe='')}/states",
                        params={"api-version": "7.1"}, headers=headers, timeout=30
                    )
                    if states_response.ok:
                        states_by_type[work_type] = states_response.json().get("value", [])
                _json_response(self, {
                    "ok": True, "org": selected_org, "project": selected_project,
                    "total": len(references), "columns": query_columns, "items": work_items,
                    "statesByType": states_by_type
                })
            except requests.RequestException:
                _json_response(self, {"ok": False, "message": "تعذر الاتصال بـ Azure DevOps. تحقق من الإنترنت وحاول مجددًا."}, 502)
            except (ValueError, KeyError, TypeError):
                _json_response(self, {"ok": False, "message": "استجابة الاستعلام من Azure غير متوقعة."}, 502)
            return
        if path == "/api/update-state":
            selected_org = (payload.get("org") or "").strip()
            selected_project = (payload.get("project") or "").strip()
            selected_pat = (payload.get("pat") or "").strip()
            selected_state = (payload.get("state") or "").strip()
            try:
                work_item_id = int(payload.get("id"))
            except (TypeError, ValueError):
                work_item_id = 0
            if not all([selected_org, selected_project, selected_pat, selected_state]) or work_item_id <= 0:
                _json_response(self, {"ok": False, "message": "بيانات تغيير الحالة غير مكتملة."}, 400)
                return
            valid, error = validate_pat(selected_pat)
            if not valid:
                _json_response(self, {"ok": False, "message": error}, 400)
                return
            query_headers = get_headers_for_query(selected_pat)
            base_url = f"https://dev.azure.com/{selected_org}/{selected_project}/_apis/wit"
            try:
                item_response = requests.get(
                    f"{base_url}/workitems/{work_item_id}",
                    params={"fields": "System.WorkItemType,System.State", "api-version": "7.1"},
                    headers=query_headers, timeout=30
                )
                if not item_response.ok:
                    _json_response(self, {"ok": False, "message": "تعذر قراءة المهمة من Azure DevOps."}, 400)
                    return
                work_type = item_response.json().get("fields", {}).get("System.WorkItemType") or "Task"
                states_response = requests.get(
                    f"{base_url}/workitemtypes/{quote(work_type, safe='')}/states",
                    params={"api-version": "7.1"}, headers=query_headers, timeout=30
                )
                if not states_response.ok:
                    _json_response(self, {"ok": False, "message": "تعذر قراءة الحالات المسموحة لهذا النوع."}, 502)
                    return
                allowed_states = {entry.get("name") for entry in states_response.json().get("value", [])}
                if selected_state not in allowed_states:
                    _json_response(self, {"ok": False, "message": "الحالة المختارة غير متاحة لهذا النوع من المهام."}, 400)
                    return
                update_response = requests.patch(
                    f"{base_url}/workitems/{work_item_id}", params={"api-version": "7.1"},
                    headers=get_headers_for_create(selected_pat),
                    json=[{"op": "add", "path": "/fields/System.State", "value": selected_state}], timeout=30
                )
                if not update_response.ok:
                    _json_response(self, {"ok": False, "message": "رفض Azure تغيير الحالة. تحقق من انتقال الحالة وصلاحية PAT للتعديل."}, 400)
                    return
                _json_response(self, {"ok": True, "state": selected_state})
            except requests.RequestException:
                _json_response(self, {"ok": False, "message": "تعذر الاتصال بـ Azure DevOps."}, 502)
            except (ValueError, KeyError, TypeError):
                _json_response(self, {"ok": False, "message": "استجابة Azure غير متوقعة أثناء تغيير الحالة."}, 502)
            return
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
