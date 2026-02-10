"""Edutools GUI — tkinter interface mirroring the CLI functionality."""

import csv
import os
import threading
import tkinter as tk
from tkinter import filedialog, messagebox, ttk
from typing import Any

from edutools.cli import init as cli_init


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _run_in_thread(func: Any, *args: Any, **kwargs: Any) -> threading.Thread:
    """Run *func* in a daemon thread so the UI stays responsive."""
    t = threading.Thread(target=func, args=args, kwargs=kwargs, daemon=True)
    t.start()
    return t


# ---------------------------------------------------------------------------
# Main Application
# ---------------------------------------------------------------------------

class EdutoolsApp(tk.Tk):
    """Top-level window for Edutools GUI."""

    def __init__(self) -> None:
        super().__init__()
        self.title("Edutools GUI")
        self.geometry("900x620")
        self.minsize(780, 520)

        # Initialise config (same as CLI)
        cli_init()

        self._build_toolbar()
        self._build_notebook()
        self._build_statusbar()

    # -- toolbar ----------------------------------------------------------

    def _build_toolbar(self) -> None:
        toolbar = ttk.Frame(self, padding=4)
        toolbar.pack(fill=tk.X)
        ttk.Button(toolbar, text="Check Credentials", command=self._check_credentials).pack(side=tk.LEFT)

    # -- notebook / tabs --------------------------------------------------

    def _build_notebook(self) -> None:
        self.notebook = ttk.Notebook(self)
        self.notebook.pack(fill=tk.BOTH, expand=True, padx=6, pady=(2, 0))

        self.canvas_tab = CanvasTab(self.notebook, self)
        self.iam_tab = IAMTab(self.notebook, self)
        self.google_tab = GoogleTab(self.notebook, self)

        self.notebook.add(self.canvas_tab, text="Canvas")
        self.notebook.add(self.iam_tab, text="IAM")
        self.notebook.add(self.google_tab, text="Google")

    # -- status bar -------------------------------------------------------

    def _build_statusbar(self) -> None:
        self.status_var = tk.StringVar(value="Ready")
        bar = ttk.Label(self, textvariable=self.status_var, relief=tk.SUNKEN, anchor=tk.W, padding=4)
        bar.pack(fill=tk.X, side=tk.BOTTOM)

    def set_status(self, msg: str) -> None:
        self.status_var.set(msg)

    # -- credential check -------------------------------------------------

    def _check_credentials(self) -> None:
        self.set_status("Checking credentials...")
        _run_in_thread(self._do_check_credentials)

    def _do_check_credentials(self) -> None:
        lines: list[str] = []

        # Canvas
        canvas_token = os.getenv("CANVAS_TOKEN")
        if not canvas_token:
            lines.append("Canvas LMS: SKIPPED (no token)")
        else:
            try:
                from edutools.canvas import CanvasLMS

                canvas = CanvasLMS()
                courses = canvas.get_courses()
                lines.append(f"Canvas LMS: OK ({len(courses)} courses)")
            except Exception as exc:
                lines.append(f"Canvas LMS: FAILED ({exc})")

        # Google
        try:
            from edutools.google_helpers import _get_oauth_path

            _get_oauth_path()
            oauth_found = True
        except Exception:
            oauth_found = False

        if not oauth_found:
            lines.append("Google Docs: SKIPPED (no client_secret.json)")
            lines.append("Gmail: SKIPPED")
        else:
            try:
                from edutools.google_helpers import _get_credentials

                _get_credentials()
                lines.append("Google Docs: OK")
            except Exception as exc:
                lines.append(f"Google Docs: FAILED ({exc})")
            try:
                from edutools.google_helpers import _get_gmail_credentials

                _get_gmail_credentials()
                lines.append("Gmail: OK")
            except Exception as exc:
                lines.append(f"Gmail: FAILED ({exc})")

        # AWS
        try:
            import boto3

            sts = boto3.client("sts")
            identity = sts.get_caller_identity()
            account = identity["Account"]
            lines.append(f"AWS IAM: OK (Account {account})")
        except Exception as exc:
            lines.append(f"AWS IAM: FAILED ({exc})")

        msg = "\n".join(lines)
        self.after(0, lambda: messagebox.showinfo("Credential Check", msg))
        self.after(0, lambda: self.set_status("Ready"))


# ---------------------------------------------------------------------------
# Canvas Tab
# ---------------------------------------------------------------------------

class CanvasTab(ttk.Frame):
    """Canvas LMS operations: courses, students, assignments, submissions."""

    def __init__(self, parent: ttk.Notebook, app: EdutoolsApp) -> None:
        super().__init__(parent, padding=6)
        self.app = app

        # Cached data
        self._courses: list[dict[str, Any]] = []
        self._assignments: list[dict[str, Any]] = []

        self._build_controls()
        self._build_table()

    def _build_controls(self) -> None:
        ctrl = ttk.Frame(self)
        ctrl.pack(fill=tk.X)

        # Row 1 — courses
        row1 = ttk.Frame(ctrl)
        row1.pack(fill=tk.X, pady=2)

        self.show_all_var = tk.BooleanVar()
        ttk.Checkbutton(row1, text="Show all", variable=self.show_all_var).pack(side=tk.LEFT)
        ttk.Button(row1, text="List Courses", command=self._list_courses).pack(side=tk.LEFT, padx=4)

        ttk.Label(row1, text="Course:").pack(side=tk.LEFT, padx=(12, 2))
        self.course_cb = ttk.Combobox(row1, state="readonly", width=40)
        self.course_cb.pack(side=tk.LEFT)
        self.course_cb.bind("<<ComboboxSelected>>", self._on_course_selected)

        # Row 2 — students, assignments, submissions
        row2 = ttk.Frame(ctrl)
        row2.pack(fill=tk.X, pady=2)

        ttk.Button(row2, text="List Students", command=self._list_students).pack(side=tk.LEFT, padx=4)
        ttk.Button(row2, text="List Assignments", command=self._list_assignments).pack(side=tk.LEFT, padx=4)

        ttk.Label(row2, text="Assignment:").pack(side=tk.LEFT, padx=(12, 2))
        self.assignment_cb = ttk.Combobox(row2, state="readonly", width=40)
        self.assignment_cb.pack(side=tk.LEFT)

        ttk.Button(row2, text="List Submissions", command=self._list_submissions).pack(side=tk.LEFT, padx=4)

    def _build_table(self) -> None:
        container = ttk.Frame(self)
        container.pack(fill=tk.BOTH, expand=True, pady=4)

        self.tree = ttk.Treeview(container, show="headings")
        vsb = ttk.Scrollbar(container, orient=tk.VERTICAL, command=self.tree.yview)
        self.tree.configure(yscrollcommand=vsb.set)
        self.tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        vsb.pack(side=tk.RIGHT, fill=tk.Y)

    # -- helpers --

    def _selected_course_id(self) -> str | None:
        idx = self.course_cb.current()
        if idx < 0 or idx >= len(self._courses):
            return None
        return str(self._courses[idx]["id"])

    def _selected_assignment_id(self) -> str | None:
        idx = self.assignment_cb.current()
        if idx < 0 or idx >= len(self._assignments):
            return None
        return str(self._assignments[idx]["id"])

    def _populate_tree(self, columns: list[str], rows: list[list[str]]) -> None:
        self.tree.delete(*self.tree.get_children())
        self.tree["columns"] = columns
        for col in columns:
            self.tree.heading(col, text=col)
            self.tree.column(col, width=120, stretch=True)
        for row in rows:
            self.tree.insert("", tk.END, values=row)

    # -- actions --

    def _list_courses(self) -> None:
        self.app.set_status("Fetching courses...")
        _run_in_thread(self._do_list_courses)

    def _do_list_courses(self) -> None:
        try:
            from edutools.canvas import CanvasLMS

            canvas = CanvasLMS()
            courses = canvas.get_courses(include_all=self.show_all_var.get())
            self._courses = courses
            names = [f"{c['name']}  (ID: {c['id']})" for c in courses]
            rows = [[str(c["id"]), str(c["name"])] for c in courses]
            self.after(0, lambda: self.course_cb.configure(values=names))
            self.after(0, lambda: self._populate_tree(["ID", "Course Name"], rows))
            self.after(0, lambda: self.app.set_status(f"{len(courses)} courses loaded"))
        except Exception as exc:
            err_msg = str(exc)
            self.after(0, lambda: messagebox.showerror("Canvas Error", err_msg))
            self.after(0, lambda: self.app.set_status("Ready"))

    def _on_course_selected(self, _event: object = None) -> None:
        self.app.set_status("Fetching assignments...")
        _run_in_thread(self._do_fetch_assignments)

    def _do_fetch_assignments(self) -> None:
        cid = self._selected_course_id()
        if cid is None:
            return
        try:
            from edutools.canvas import CanvasLMS

            canvas = CanvasLMS()
            assignments = canvas.get_assignments(cid)
            self._assignments = assignments
            names = [f"{a['name']}  (ID: {a['id']})" for a in assignments]
            self.after(0, lambda: self.assignment_cb.configure(values=names))
            self.after(0, lambda: self.app.set_status(f"{len(assignments)} assignments loaded"))
        except Exception as exc:
            err_msg = str(exc)
            self.after(0, lambda: messagebox.showerror("Canvas Error", err_msg))
            self.after(0, lambda: self.app.set_status("Ready"))

    def _list_students(self) -> None:
        cid = self._selected_course_id()
        if cid is None:
            messagebox.showwarning("Select Course", "Please select a course first.")
            return
        self.app.set_status("Fetching students...")
        _run_in_thread(self._do_list_students, cid)

    def _do_list_students(self, course_id: str) -> None:
        try:
            from edutools.canvas import CanvasLMS

            canvas = CanvasLMS()
            students = canvas.get_students(course_id)
            rows = [[str(s["id"]), s.get("email", "N/A")] for s in students]
            self.after(0, lambda: self._populate_tree(["ID", "Email"], rows))
            self.after(0, lambda: self.app.set_status(f"{len(students)} students loaded"))
        except Exception as exc:
            err_msg = str(exc)
            self.after(0, lambda: messagebox.showerror("Canvas Error", err_msg))
            self.after(0, lambda: self.app.set_status("Ready"))

    def _list_assignments(self) -> None:
        cid = self._selected_course_id()
        if cid is None:
            messagebox.showwarning("Select Course", "Please select a course first.")
            return
        self.app.set_status("Fetching assignments...")
        _run_in_thread(self._do_list_assignments, cid)

    def _do_list_assignments(self, course_id: str) -> None:
        try:
            from edutools.canvas import CanvasLMS

            canvas = CanvasLMS()
            assignments = canvas.get_assignments(course_id)
            self._assignments = assignments
            names = [f"{a['name']}  (ID: {a['id']})" for a in assignments]
            rows = [[str(a["id"]), a["name"]] for a in assignments]
            self.after(0, lambda: self.assignment_cb.configure(values=names))
            self.after(0, lambda: self._populate_tree(["ID", "Assignment Name"], rows))
            self.after(0, lambda: self.app.set_status(f"{len(assignments)} assignments loaded"))
        except Exception as exc:
            err_msg = str(exc)
            self.after(0, lambda: messagebox.showerror("Canvas Error", err_msg))
            self.after(0, lambda: self.app.set_status("Ready"))

    def _list_submissions(self) -> None:
        cid = self._selected_course_id()
        aid = self._selected_assignment_id()
        if cid is None or aid is None:
            messagebox.showwarning("Select Items", "Please select a course and assignment first.")
            return
        self.app.set_status("Fetching submissions...")
        _run_in_thread(self._do_list_submissions, cid, aid)

    def _do_list_submissions(self, course_id: str, assignment_id: str) -> None:
        try:
            from edutools.canvas import CanvasLMS

            canvas = CanvasLMS()
            submissions = canvas.get_submissions(course_id, assignment_id)
            rows = [[str(s["user_id"]), s.get("grade") or "Not graded"] for s in submissions]
            self.after(0, lambda: self._populate_tree(["User ID", "Grade"], rows))
            self.after(0, lambda: self.app.set_status(f"{len(submissions)} submissions loaded"))
        except Exception as exc:
            err_msg = str(exc)
            self.after(0, lambda: messagebox.showerror("Canvas Error", err_msg))
            self.after(0, lambda: self.app.set_status("Ready"))


# ---------------------------------------------------------------------------
# IAM Tab
# ---------------------------------------------------------------------------

class IAMTab(ttk.Frame):
    """AWS IAM operations: provision, deprovision, reset, email, policy."""

    def __init__(self, parent: ttk.Notebook, app: EdutoolsApp) -> None:
        super().__init__(parent, padding=6)
        self.app = app

        self._courses: list[dict[str, Any]] = []

        self._build_course_row()
        self._build_action_buttons()
        self._build_single_reset()
        self._build_email_section()
        self._build_progress()
        self._build_table()

    # -- layout -----------------------------------------------------------

    def _build_course_row(self) -> None:
        row = ttk.Frame(self)
        row.pack(fill=tk.X, pady=2)

        ttk.Button(row, text="Load Courses", command=self._load_courses).pack(side=tk.LEFT)
        ttk.Label(row, text="Course:").pack(side=tk.LEFT, padx=(12, 2))
        self.course_cb = ttk.Combobox(row, state="readonly", width=40)
        self.course_cb.pack(side=tk.LEFT)

    def _build_action_buttons(self) -> None:
        row = ttk.Frame(self)
        row.pack(fill=tk.X, pady=2)

        ttk.Button(row, text="Provision", command=self._provision).pack(side=tk.LEFT, padx=4)
        ttk.Button(row, text="Deprovision", command=self._deprovision).pack(side=tk.LEFT, padx=4)
        ttk.Button(row, text="Reset Passwords", command=self._reset_passwords).pack(side=tk.LEFT, padx=4)
        ttk.Button(row, text="Update Policy", command=self._update_policy).pack(side=tk.LEFT, padx=4)

    def _build_single_reset(self) -> None:
        row = ttk.Frame(self)
        row.pack(fill=tk.X, pady=2)

        ttk.Label(row, text="Single user reset:").pack(side=tk.LEFT)
        self.username_entry = ttk.Entry(row, width=30)
        self.username_entry.pack(side=tk.LEFT, padx=4)
        ttk.Button(row, text="Reset Password", command=self._reset_single).pack(side=tk.LEFT, padx=4)

    def _build_email_section(self) -> None:
        frame = ttk.LabelFrame(self, text="Email Credentials", padding=4)
        frame.pack(fill=tk.X, pady=4)

        row1 = ttk.Frame(frame)
        row1.pack(fill=tk.X, pady=2)
        ttk.Label(row1, text="CSV File:").pack(side=tk.LEFT)
        self.csv_path_var = tk.StringVar()
        ttk.Entry(row1, textvariable=self.csv_path_var, width=40).pack(side=tk.LEFT, padx=4)
        ttk.Button(row1, text="Browse...", command=self._browse_csv).pack(side=tk.LEFT)

        row2 = ttk.Frame(frame)
        row2.pack(fill=tk.X, pady=2)
        ttk.Label(row2, text="Sender Name:").pack(side=tk.LEFT)
        self.sender_var = tk.StringVar(value="Course Instructor")
        ttk.Entry(row2, textvariable=self.sender_var, width=30).pack(side=tk.LEFT, padx=4)
        ttk.Button(row2, text="Send Emails", command=self._send_emails).pack(side=tk.LEFT, padx=4)

    def _build_progress(self) -> None:
        self.progress = ttk.Progressbar(self, mode="determinate")
        self.progress.pack(fill=tk.X, pady=2)

    def _build_table(self) -> None:
        container = ttk.Frame(self)
        container.pack(fill=tk.BOTH, expand=True, pady=4)

        self.tree = ttk.Treeview(container, show="headings")
        vsb = ttk.Scrollbar(container, orient=tk.VERTICAL, command=self.tree.yview)
        self.tree.configure(yscrollcommand=vsb.set)
        self.tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        vsb.pack(side=tk.RIGHT, fill=tk.Y)

    # -- helpers --

    def _selected_course_id(self) -> str | None:
        idx = self.course_cb.current()
        if idx < 0 or idx >= len(self._courses):
            return None
        return str(self._courses[idx]["id"])

    def _populate_tree(self, columns: list[str], rows: list[list[str]]) -> None:
        self.tree.delete(*self.tree.get_children())
        self.tree["columns"] = columns
        for col in columns:
            self.tree.heading(col, text=col)
            self.tree.column(col, width=120, stretch=True)
        for row in rows:
            self.tree.insert("", tk.END, values=row)

    def _gui_progress_callback(self, current: int, total: int, message: str) -> None:
        if total > 0:
            self.after(0, lambda: self.progress.configure(maximum=total, value=current))
        self.after(0, lambda: self.app.set_status(message))

    def _display_results(self, results: list[dict[str, Any]], show_password: bool = False) -> None:
        cols = ["Email", "Username"]
        if show_password:
            cols.append("Password")
        cols.append("Status")
        rows: list[list[str]] = []
        for r in results:
            row = [r.get("email", "N/A"), r.get("username", "N/A")]
            if show_password:
                row.append(r.get("password", "N/A"))
            row.append(r.get("status", "N/A"))
            rows.append(row)
        self.after(0, lambda: self._populate_tree(cols, rows))

    # -- actions --

    def _load_courses(self) -> None:
        self.app.set_status("Fetching courses...")
        _run_in_thread(self._do_load_courses)

    def _do_load_courses(self) -> None:
        try:
            from edutools.canvas import CanvasLMS

            canvas = CanvasLMS()
            courses = canvas.get_courses()
            self._courses = courses
            names = [f"{c['name']}  (ID: {c['id']})" for c in courses]
            self.after(0, lambda: self.course_cb.configure(values=names))
            self.after(0, lambda: self.app.set_status(f"{len(courses)} courses loaded"))
        except Exception as exc:
            err_msg = str(exc)
            self.after(0, lambda: messagebox.showerror("Canvas Error", err_msg))
            self.after(0, lambda: self.app.set_status("Ready"))

    def _provision(self) -> None:
        cid = self._selected_course_id()
        if cid is None:
            messagebox.showwarning("Select Course", "Please select a course first.")
            return
        self.app.set_status("Provisioning IAM users...")
        _run_in_thread(self._do_provision, cid)

    def _do_provision(self, course_id: str) -> None:
        try:
            from edutools.iam import provision_students

            results = provision_students(course_id, progress_callback=self._gui_progress_callback)
            self._display_results(results, show_password=True)

            if results:
                filename = f"provisioned_{course_id}.csv"
                with open(filename, "w", newline="") as f:
                    writer = csv.DictWriter(f, fieldnames=["email", "username", "password", "status"])
                    writer.writeheader()
                    for r in results:
                        writer.writerow({
                            "email": r.get("email", ""),
                            "username": r.get("username", ""),
                            "password": r.get("password", ""),
                            "status": r.get("status", ""),
                        })
                self.after(0, lambda: self.app.set_status(f"Done — results saved to {filename}"))
            else:
                self.after(0, lambda: self.app.set_status("No students found"))
        except Exception as exc:
            err_msg = str(exc)
            self.after(0, lambda: messagebox.showerror("IAM Error", err_msg))
            self.after(0, lambda: self.app.set_status("Ready"))

    def _deprovision(self) -> None:
        cid = self._selected_course_id()
        if cid is None:
            messagebox.showwarning("Select Course", "Please select a course first.")
            return
        if not messagebox.askyesno("Confirm Deprovision", f"DELETE all IAM users for course {cid}?"):
            return
        self.app.set_status("Deprovisioning IAM users...")
        _run_in_thread(self._do_deprovision, cid)

    def _do_deprovision(self, course_id: str) -> None:
        try:
            from edutools.iam import deprovision_students

            results = deprovision_students(course_id, progress_callback=self._gui_progress_callback)
            self._display_results(results)
            self.after(0, lambda: self.app.set_status("Deprovisioning complete"))
        except Exception as exc:
            err_msg = str(exc)
            self.after(0, lambda: messagebox.showerror("IAM Error", err_msg))
            self.after(0, lambda: self.app.set_status("Ready"))

    def _reset_passwords(self) -> None:
        cid = self._selected_course_id()
        if cid is None:
            messagebox.showwarning("Select Course", "Please select a course first.")
            return
        self.app.set_status("Resetting passwords...")
        _run_in_thread(self._do_reset_passwords, cid)

    def _do_reset_passwords(self, course_id: str) -> None:
        try:
            from edutools.iam import reset_student_passwords

            results = reset_student_passwords(course_id, progress_callback=self._gui_progress_callback)
            self._display_results(results, show_password=True)
            self.after(0, lambda: self.app.set_status("Password reset complete"))
        except Exception as exc:
            err_msg = str(exc)
            self.after(0, lambda: messagebox.showerror("IAM Error", err_msg))
            self.after(0, lambda: self.app.set_status("Ready"))

    def _update_policy(self) -> None:
        cid = self._selected_course_id()
        if cid is None:
            messagebox.showwarning("Select Course", "Please select a course first.")
            return
        self.app.set_status("Updating policies...")
        _run_in_thread(self._do_update_policy, cid)

    def _do_update_policy(self, course_id: str) -> None:
        try:
            from edutools.iam import update_student_policies

            results = update_student_policies(course_id, progress_callback=self._gui_progress_callback)
            self._display_results(results)
            self.after(0, lambda: self.app.set_status("Policy update complete"))
        except Exception as exc:
            err_msg = str(exc)
            self.after(0, lambda: messagebox.showerror("IAM Error", err_msg))
            self.after(0, lambda: self.app.set_status("Ready"))

    def _reset_single(self) -> None:
        username = self.username_entry.get().strip()
        if not username:
            messagebox.showwarning("Username Required", "Enter a username to reset.")
            return
        self.app.set_status(f"Resetting password for {username}...")
        _run_in_thread(self._do_reset_single, username)

    def _do_reset_single(self, username: str) -> None:
        try:
            from edutools.iam import IAMProvisioner

            iam = IAMProvisioner()
            result = iam.reset_password(username)
            if result["status"] == "reset":
                msg = f"Username: {username}\nNew Password: {result['password']}"
                self.after(0, lambda: messagebox.showinfo("Password Reset", msg))
            else:
                err = result.get("error", "unknown error")
                self.after(0, lambda: messagebox.showerror("Reset Failed", err))
            self.after(0, lambda: self.app.set_status("Ready"))
        except Exception as exc:
            err_msg = str(exc)
            self.after(0, lambda: messagebox.showerror("IAM Error", err_msg))
            self.after(0, lambda: self.app.set_status("Ready"))

    def _browse_csv(self) -> None:
        path = filedialog.askopenfilename(filetypes=[("CSV files", "*.csv"), ("All files", "*.*")])
        if path:
            self.csv_path_var.set(path)

    def _send_emails(self) -> None:
        csv_path = self.csv_path_var.get().strip()
        if not csv_path or not os.path.exists(csv_path):
            messagebox.showwarning("CSV Required", "Select a valid CSV file first.")
            return
        sender = self.sender_var.get().strip() or "Course Instructor"
        self.app.set_status("Sending emails...")
        _run_in_thread(self._do_send_emails, csv_path, sender)

    def _do_send_emails(self, csv_path: str, sender_name: str) -> None:
        try:
            from edutools.google_helpers import send_email
            from edutools.iam import IAMProvisioner

            with open(csv_path, newline="") as f:
                reader = csv.DictReader(f)
                rows = [r for r in reader if r.get("status") == "created" and r.get("email")]

            if not rows:
                self.after(0, lambda: messagebox.showinfo("No Recipients", "No created users found in CSV."))
                self.after(0, lambda: self.app.set_status("Ready"))
                return

            iam = IAMProvisioner()
            sign_in_url = iam.get_sign_in_url()

            sent = 0
            failed = 0
            total = len(rows)
            for i, row in enumerate(rows, 1):
                self._gui_progress_callback(i, total, f"Emailing {row['email']}")
                subject = "Your AWS Account Credentials"
                body_text = (
                    f"Hello,\n\n"
                    f"Your AWS IAM account has been created. Here are your login credentials:\n\n"
                    f"Sign-in URL: {sign_in_url}\n"
                    f"Username: {row['username']}\n"
                    f"Temporary Password: {row['password']}\n\n"
                    f"IMPORTANT: You will be required to change your password on first login.\n\n"
                    f"Your account has permissions to use EC2 (virtual machines) in the us-west-2 region only.\n\n"
                    f"Best regards,\n{sender_name}\n"
                )
                try:
                    result = send_email(to=row["email"], subject=subject, body_text=body_text)
                    if result.get("success"):
                        sent += 1
                    else:
                        failed += 1
                except Exception:
                    failed += 1

            self.after(0, lambda: messagebox.showinfo(
                "Email Summary", f"Sent: {sent}\nFailed: {failed}\nTotal: {total}"
            ))
            self.after(0, lambda: self.app.set_status("Ready"))
        except Exception as exc:
            err_msg = str(exc)
            self.after(0, lambda: messagebox.showerror("Email Error", err_msg))
            self.after(0, lambda: self.app.set_status("Ready"))


# ---------------------------------------------------------------------------
# Google Tab
# ---------------------------------------------------------------------------

class GoogleTab(ttk.Frame):
    """Google Docs operations: create document."""

    def __init__(self, parent: ttk.Notebook, app: EdutoolsApp) -> None:
        super().__init__(parent, padding=6)
        self.app = app
        self._build_controls()
        self._build_result()

    def _build_controls(self) -> None:
        row1 = ttk.Frame(self)
        row1.pack(fill=tk.X, pady=2)
        ttk.Label(row1, text="Document Title:").pack(side=tk.LEFT)
        self.title_var = tk.StringVar()
        ttk.Entry(row1, textvariable=self.title_var, width=40).pack(side=tk.LEFT, padx=4)

        row2 = ttk.Frame(self)
        row2.pack(fill=tk.X, pady=2)
        ttk.Label(row2, text="Folder ID (optional):").pack(side=tk.LEFT)
        self.folder_var = tk.StringVar()
        ttk.Entry(row2, textvariable=self.folder_var, width=40).pack(side=tk.LEFT, padx=4)

        ttk.Button(row2, text="Create Doc", command=self._create_doc).pack(side=tk.LEFT, padx=4)

    def _build_result(self) -> None:
        self.result_var = tk.StringVar()
        ttk.Label(self, textvariable=self.result_var, wraplength=700).pack(fill=tk.X, pady=8)

    def _create_doc(self) -> None:
        title = self.title_var.get().strip()
        if not title:
            messagebox.showwarning("Title Required", "Enter a document title.")
            return
        folder_id = self.folder_var.get().strip() or None
        self.app.set_status("Creating Google Doc...")
        _run_in_thread(self._do_create_doc, title, folder_id)

    def _do_create_doc(self, title: str, folder_id: str | None) -> None:
        try:
            import edutools.google_helpers as google_helpers

            doc_id = google_helpers.create_doc(title, folder_id)
            url = f"https://docs.google.com/document/d/{doc_id}"
            self.after(0, lambda: self.result_var.set(f"Created: {url}"))
            self.after(0, lambda: self.app.set_status("Document created"))
        except Exception as exc:
            err_msg = str(exc)
            self.after(0, lambda: messagebox.showerror("Google Error", err_msg))
            self.after(0, lambda: self.app.set_status("Ready"))


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

def main() -> None:
    """Launch the Edutools GUI."""
    app = EdutoolsApp()
    app.mainloop()


if __name__ == "__main__":
    main()
