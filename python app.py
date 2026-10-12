import tkinter as tk
from datetime import datetime
from tkinter import messagebox, ttk

from task_core import (
    DEFAULT_MANAGER,
    DEFAULT_TITLE,
    ORG,
    PROJECT,
    USER,
    WORK_HOURS,
    create_task,
    get_active_profile,
    make_profile,
    normalize_config,
    set_active_profile,
    upsert_profile,
    validate_pat,
)
from public_access import start_public_tunnel
from qr_utils import draw_qr_on_canvas, qr_matrix
from web_app import start_web_server


def apply_profile_to_form(profile, org_entry, project_entry, manager_entry, user_entry):
    values = [
        (org_entry, (profile or {}).get("org") or ORG),
        (project_entry, (profile or {}).get("project") or PROJECT),
        (manager_entry, (profile or {}).get("manager") or DEFAULT_MANAGER),
        (user_entry, (profile or {}).get("user") or USER),
    ]
    for entry, value in values:
        entry.delete(0, tk.END)
        entry.insert(0, value)


def open_user_form(root, title, initial, on_save):
    setup = tk.Toplevel(root)
    setup.title(title)
    setup.geometry("560x360")
    setup.resizable(False, False)
    setup.transient(root)
    setup.grab_set()

    frame = ttk.Frame(setup, padding=16)
    frame.pack(fill="both", expand=True)
    frame.columnconfigure(1, weight=1)

    fields = [
        ("Assigned User", "user", False),
        ("PAT Token", "pat", True),
        ("Organization", "org", False),
        ("Project", "project", False),
        ("Direct Manager", "manager", False),
    ]
    entries = {}
    for row, (label, key, secret) in enumerate(fields):
        ttk.Label(frame, text=label).grid(row=row, column=0, sticky="w", pady=(0, 8))
        entry = ttk.Entry(frame, show="*" if secret else "")
        entry.insert(0, initial.get(key, ""))
        entry.grid(row=row, column=1, sticky="ew", pady=(0, 8))
        entries[key] = entry

    def save():
        data = {key: entry.get().strip() for key, entry in entries.items()}
        if not data["user"] or not data["pat"]:
            messagebox.showerror("Input Error", "PAT and Assigned User are required.", parent=setup)
            return
        is_valid, error_message = validate_pat(data["pat"])
        if not is_valid:
            messagebox.showerror("Invalid PAT", error_message, parent=setup)
            return
        on_save(data)
        setup.destroy()

    ttk.Button(frame, text="Save", command=save).grid(
        row=len(fields), column=1, sticky="e", pady=(12, 0)
    )
    setup.wait_window()


def launch_gui():
    root = tk.Tk()
    root.title("Azure DevOps Task Creator")
    root.geometry("760x580")
    root.minsize(760, 580)
    root.resizable(False, False)

    style = ttk.Style()
    style.configure("Main.TFrame", background="#f4f6fb")
    style.configure("Title.TLabel", font=("Segoe UI", 15, "bold"), background="#f4f6fb")
    style.configure("Subtitle.TLabel", font=("Segoe UI", 10), foreground="#4b5563", background="#f4f6fb")
    style.configure("FieldLabel.TLabel", font=("Segoe UI", 10, "bold"), background="#f4f6fb")
    style.configure("Status.TLabel", font=("Segoe UI", 10), background="#f4f6fb")

    root.configure(bg="#f4f6fb")
    default_date = datetime.now().strftime("%Y-%m-%d")
    user_config = {"profiles": [], "active_profile": ""}

    main = ttk.Frame(root, style="Main.TFrame", padding=20)
    main.pack(fill="both", expand=True)
    main.columnconfigure(1, weight=1)

    ttk.Label(main, text="Azure DevOps Task Creator", style="Title.TLabel").grid(
        row=0, column=0, columnspan=2, sticky="w"
    )
    ttk.Label(
        main,
        text="Create task, add another user, or open the same screen on iPhone",
        style="Subtitle.TLabel",
    ).grid(row=1, column=0, columnspan=2, sticky="w", pady=(2, 16))

    ttk.Label(main, text="Saved User", style="FieldLabel.TLabel").grid(
        row=2, column=0, sticky="w", pady=(0, 6)
    )
    profile_var = tk.StringVar()
    profile_combo = ttk.Combobox(main, textvariable=profile_var, state="readonly")
    profile_combo.grid(row=2, column=1, sticky="ew", pady=(0, 6))

    ttk.Label(main, text="Organization", style="FieldLabel.TLabel").grid(
        row=3, column=0, sticky="w", pady=(0, 6)
    )
    org_entry = ttk.Entry(main)
    org_entry.grid(row=3, column=1, sticky="ew", pady=(0, 6))

    ttk.Label(main, text="Project", style="FieldLabel.TLabel").grid(
        row=4, column=0, sticky="w", pady=(0, 6)
    )
    project_entry = ttk.Entry(main)
    project_entry.grid(row=4, column=1, sticky="ew", pady=(0, 6))

    ttk.Label(main, text="Direct Manager", style="FieldLabel.TLabel").grid(
        row=5, column=0, sticky="w", pady=(0, 6)
    )
    manager_entry = ttk.Entry(main)
    manager_entry.grid(row=5, column=1, sticky="ew", pady=(0, 6))

    ttk.Label(main, text="Assigned User", style="FieldLabel.TLabel").grid(
        row=6, column=0, sticky="w", pady=(0, 6)
    )
    user_entry = ttk.Entry(main)
    user_entry.grid(row=6, column=1, sticky="ew", pady=(0, 6))

    ttk.Label(main, text="Date (YYYY-MM-DD)", style="FieldLabel.TLabel").grid(
        row=7, column=0, sticky="w", pady=(0, 6)
    )
    date_entry = ttk.Entry(main)
    date_entry.insert(0, default_date)
    date_entry.grid(row=7, column=1, sticky="ew", pady=(0, 6))

    ttk.Label(main, text="Task Title (value)", style="FieldLabel.TLabel").grid(
        row=8, column=0, sticky="w", pady=(0, 6)
    )
    title_entry = ttk.Entry(main)
    title_entry.insert(0, DEFAULT_TITLE)
    title_entry.grid(row=8, column=1, sticky="ew", pady=(0, 6))

    ttk.Label(main, text="Work Hours", style="FieldLabel.TLabel").grid(
        row=9, column=0, sticky="w", pady=(0, 6)
    )
    hours_entry = ttk.Entry(main)
    hours_entry.insert(0, str(WORK_HOURS))
    hours_entry.grid(row=9, column=1, sticky="ew", pady=(0, 12))

    status_var = tk.StringVar(value="Ready")
    ttk.Label(main, textvariable=status_var, style="Status.TLabel", foreground="#2563eb").grid(
        row=10, column=0, columnspan=2, sticky="w", pady=(8, 16)
    )

    button_row = ttk.Frame(main, style="Main.TFrame")
    button_row.grid(row=11, column=0, columnspan=2, sticky="e")

    id_by_label = {}

    def refresh_profiles(select_id=None):
        nonlocal id_by_label
        id_by_label = {
            (p.get("label") or p.get("user") or p.get("id")): p.get("id")
            for p in user_config.get("profiles") or []
        }
        labels = list(id_by_label.keys())
        profile_combo["values"] = labels
        active = None
        if select_id:
            for label, profile_id in id_by_label.items():
                if profile_id == select_id:
                    profile_var.set(label)
                    active = next(
                        (p for p in user_config["profiles"] if p.get("id") == select_id),
                        None,
                    )
                    break
        if not active:
            active = get_active_profile(user_config)
            if active:
                profile_var.set(active.get("label") or active.get("user") or "")
        apply_profile_to_form(active, org_entry, project_entry, manager_entry, user_entry)

    def current_profile():
        return get_active_profile(user_config)

    def on_profile_selected(_event=None):
        profile_id = id_by_label.get(profile_var.get())
        if not profile_id:
            return
        profile = set_active_profile(user_config, profile_id)
        apply_profile_to_form(profile, org_entry, project_entry, manager_entry, user_entry)

    def on_submit():
        raw_date = date_entry.get().strip()
        task_title = title_entry.get().strip()
        raw_hours = hours_entry.get().strip()
        selected_org = org_entry.get().strip()
        selected_project = project_entry.get().strip()
        selected_manager = manager_entry.get().strip()
        selected_user = user_entry.get().strip()

        if not selected_org:
            messagebox.showerror("Input Error", "Organization is required.")
            return
        if not selected_project:
            messagebox.showerror("Input Error", "Project is required.")
            return
        if not selected_manager:
            messagebox.showerror("Input Error", "Direct Manager is required.")
            return
        if not task_title:
            messagebox.showerror("Input Error", "Task Title is required.")
            return
        if not selected_user:
            messagebox.showerror("Input Error", "Assigned User is required.")
            return

        try:
            selected_date = datetime.strptime(raw_date, "%Y-%m-%d")
        except ValueError:
            messagebox.showerror("Input Error", "Date must be in YYYY-MM-DD format.")
            return
        try:
            selected_hours = float(raw_hours)
        except ValueError:
            messagebox.showerror("Input Error", "Work Hours must be a number.")
            return

        status_var.set("Submitting task...")
        root.update_idletasks()
        active = current_profile() or {}
        success, message = create_task(
            selected_org,
            selected_project,
            selected_user,
            selected_manager,
            selected_date,
            task_title,
            selected_hours,
            active.get("pat", ""),
        )
        status_var.set("Ready")
        if success:
            messagebox.showinfo("تم الإضافة بنجاح", message)
        else:
            messagebox.showwarning("Result", message)

    def on_reset():
        refresh_profiles(user_config.get("active_profile"))
        date_entry.delete(0, tk.END)
        date_entry.insert(0, default_date)
        title_entry.delete(0, tk.END)
        title_entry.insert(0, DEFAULT_TITLE)
        hours_entry.delete(0, tk.END)
        hours_entry.insert(0, str(WORK_HOURS))
        status_var.set("Ready")

    def on_add_user():
        def save(data):
            profile = make_profile(
                data["user"],
                data["pat"],
                data["org"],
                data["project"],
                data["manager"],
            )
            upsert_profile(user_config, profile)
            refresh_profiles(profile["id"])
            messagebox.showinfo("تم الإضافة بنجاح", "تم إضافة المستخدم بنجاح")

        open_user_form(
            root,
            "Add Another User",
            {
                "user": "",
                "pat": "",
                "org": ORG,
                "project": PROJECT,
                "manager": DEFAULT_MANAGER,
            },
            save,
        )

    def on_update_login():
        active = current_profile() or {}

        def save(data):
            profile = make_profile(
                data["user"],
                data["pat"],
                data["org"],
                data["project"],
                data["manager"],
                active.get("id"),
            )
            upsert_profile(user_config, profile)
            refresh_profiles(profile["id"])
            messagebox.showinfo("Saved", "User updated successfully.")

        open_user_form(
            root,
            "Update Current User",
            {
                "user": active.get("user", ""),
                "pat": active.get("pat", ""),
                "org": active.get("org", ORG),
                "project": active.get("project", PROJECT),
                "manager": active.get("manager", DEFAULT_MANAGER),
            },
            save,
        )

    def show_qr_window(url, note):
        popup = tk.Toplevel(root)
        popup.title("Scan QR from anywhere")
        popup.geometry("420x520")
        popup.resizable(False, False)
        popup.transient(root)

        ttk.Label(popup, text="Scan this QR with iPhone Camera").pack(pady=(16, 8))
        canvas = tk.Canvas(popup, background="white", highlightthickness=0)
        canvas.pack()
        draw_qr_on_canvas(canvas, qr_matrix(url), scale=7)

        url_var = tk.StringVar(value=url)
        ttk.Entry(popup, textvariable=url_var, justify="center").pack(fill="x", padx=16, pady=(12, 6))
        ttk.Label(popup, text=note, wraplength=380, justify="center").pack(padx=16)

        def copy_url():
            popup.clipboard_clear()
            popup.clipboard_append(url)
            status_var.set("Link copied")

        ttk.Button(popup, text="Copy Link", command=copy_url).pack(pady=12)

    def on_open_iphone():
        ip, port = start_web_server()
        local_url = f"http://{ip}:{port}"
        status_var.set("Creating public link...")
        root.update_idletasks()
        try:
            public_url = start_public_tunnel(port)
            status_var.set(f"Open from anywhere: {public_url}")
            show_qr_window(
                public_url,
                "Works from any network. Keep this program open on the PC.",
            )
        except Exception as error:
            status_var.set(f"Local only: {local_url}")
            show_qr_window(
                local_url,
                f"Public link failed ({error}). This QR works only on the same Wi-Fi.",
            )

    profile_combo.bind("<<ComboboxSelected>>", on_profile_selected)
    ttk.Button(button_row, text="Open on iPhone", command=on_open_iphone).pack(side="right", padx=(0, 8))
    ttk.Button(button_row, text="Reset", command=on_reset).pack(side="right", padx=(0, 8))
    ttk.Button(button_row, text="Add User", command=on_add_user).pack(side="right", padx=(0, 8))
    ttk.Button(button_row, text="Update User", command=on_update_login).pack(side="right", padx=(0, 8))
    ttk.Button(button_row, text="Create Task", command=on_submit).pack(side="right")

    user_config.update(normalize_config())
    if not user_config.get("profiles"):
        def first_save(data):
            profile = make_profile(
                data["user"],
                data["pat"],
                data["org"],
                data["project"],
                data["manager"],
            )
            upsert_profile(user_config, profile)

        open_user_form(
            root,
            "First Time Setup",
            {
                "user": USER,
                "pat": "",
                "org": ORG,
                "project": PROJECT,
                "manager": DEFAULT_MANAGER,
            },
            first_save,
        )
        user_config.update(normalize_config())
        if not user_config.get("profiles"):
            root.destroy()
            return

    refresh_profiles(user_config.get("active_profile"))
    root.mainloop()


if __name__ == "__main__":
    launch_gui()
