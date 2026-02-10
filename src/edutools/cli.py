import typer
import csv
from typing import Optional
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn, TaskProgressColumn
from rich import print as rprint
from dotenv import load_dotenv

app = typer.Typer(
    name="edutools",
    help="🎓 Educational Tools CLI - Manage Canvas LMS, AWS IAM, and Google Docs",
    add_completion=False,
    rich_markup_mode="rich",
)

console = Console()

# Sub-apps for organization
canvas_app = typer.Typer(help="📚 Canvas LMS operations")
iam_app = typer.Typer(help="☁️  AWS IAM user management")
google_app = typer.Typer(help="📄 Google Docs operations")

app.add_typer(canvas_app, name="canvas")
app.add_typer(iam_app, name="iam")
app.add_typer(google_app, name="google")


def init():
    """Initialize environment variables."""
    load_dotenv()


# ============================================================================
# Canvas Commands
# ============================================================================

@canvas_app.command("courses")
def list_courses():
    """📋 List all active Canvas courses where you are a teacher."""
    init()
    from edutools.canvas import CanvasLMS

    with console.status("[bold green]Fetching courses from Canvas...", spinner="dots"):
        canvas = CanvasLMS()
        courses = canvas.get_courses()

    if not courses:
        console.print("[yellow]No courses found.[/yellow]")
        return

    table = Table(title="📚 Your Canvas Courses", show_header=True, header_style="bold magenta")
    table.add_column("ID", style="cyan", justify="right")
    table.add_column("Course Name", style="green")

    for c in courses:
        table.add_row(str(c["id"]), c["name"])

    console.print(table)
    console.print(f"\n[dim]Total: {len(courses)} courses[/dim]")


@canvas_app.command("assignments")
def list_assignments(course_id: str = typer.Argument(..., help="Canvas course ID")):
    """📝 List all assignments for a course."""
    init()
    from edutools.canvas import CanvasLMS

    with console.status(f"[bold green]Fetching assignments for course {course_id}...", spinner="dots"):
        canvas = CanvasLMS()
        assignments = canvas.get_assignments(course_id)

    if not assignments:
        console.print("[yellow]No assignments found.[/yellow]")
        return

    table = Table(title=f"📝 Assignments for Course {course_id}", show_header=True, header_style="bold magenta")
    table.add_column("ID", style="cyan", justify="right")
    table.add_column("Assignment Name", style="green")

    for a in assignments:
        table.add_row(str(a["id"]), a["name"])

    console.print(table)
    console.print(f"\n[dim]Total: {len(assignments)} assignments[/dim]")


@canvas_app.command("students")
def list_students(course_id: str = typer.Argument(..., help="Canvas course ID")):
    """👥 List all students in a course."""
    init()
    from edutools.canvas import CanvasLMS

    with console.status(f"[bold green]Fetching students for course {course_id}...", spinner="dots"):
        canvas = CanvasLMS()
        students = canvas.get_students(course_id)

    if not students:
        console.print("[yellow]No students found.[/yellow]")
        return

    table = Table(title=f"👥 Students in Course {course_id}", show_header=True, header_style="bold magenta")
    table.add_column("ID", style="cyan", justify="right")
    table.add_column("Email", style="green")

    for s in students:
        table.add_row(str(s["id"]), s.get("email", "[dim]No email[/dim]"))

    console.print(table)
    console.print(f"\n[dim]Total: {len(students)} students[/dim]")


@canvas_app.command("submissions")
def list_submissions(
    course_id: str = typer.Argument(..., help="Canvas course ID"),
    assignment_id: str = typer.Argument(..., help="Assignment ID"),
):
    """📊 List all submissions for an assignment."""
    init()
    from edutools.canvas import CanvasLMS

    with console.status(f"[bold green]Fetching submissions...", spinner="dots"):
        canvas = CanvasLMS()
        submissions = canvas.get_submissions(course_id, assignment_id)

    if not submissions:
        console.print("[yellow]No submissions found.[/yellow]")
        return

    table = Table(title=f"📊 Submissions for Assignment {assignment_id}", show_header=True, header_style="bold magenta")
    table.add_column("User ID", style="cyan", justify="right")
    table.add_column("Grade", style="green")

    for sub in submissions:
        grade = sub.get("grade") or "[dim]Not graded[/dim]"
        table.add_row(str(sub["user_id"]), str(grade))

    console.print(table)
    console.print(f"\n[dim]Total: {len(submissions)} submissions[/dim]")


# ============================================================================
# IAM Commands
# ============================================================================

def _rich_progress_callback(progress: Progress, task_id):
    """Create a progress callback for Rich progress bar."""
    def callback(current: int, total: int, message: str):
        if total > 0:
            progress.update(task_id, completed=current, total=total, description=f"[cyan]{message}")
        else:
            progress.update(task_id, description=f"[cyan]{message}")
    return callback


def _select_course() -> str:
    """Fetch Canvas courses and prompt the user to select one."""
    from edutools.canvas import CanvasLMS

    with console.status("[bold green]Fetching courses from Canvas...", spinner="dots"):
        canvas = CanvasLMS()
        courses = canvas.get_courses()

    if not courses:
        console.print("[yellow]No courses found.[/yellow]")
        raise typer.Exit()

    console.print()
    for i, c in enumerate(courses, 1):
        console.print(f"  [cyan]{i}[/cyan]. {c['name']} [dim](ID: {c['id']})[/dim]")
    console.print()

    choice = typer.prompt("Select a course", type=int)
    if choice < 1 or choice > len(courses):
        console.print("[red]Invalid selection.[/red]")
        raise typer.Exit(1)

    return str(courses[choice - 1]["id"])


@iam_app.command("provision")
def provision_users(course_id: Optional[str] = typer.Argument(None, help="Canvas course ID (prompted if omitted)")):
    """🚀 Create IAM users for all students in a Canvas course (EC2 access only)."""
    init()
    from edutools.iam import provision_students

    if course_id is None:
        course_id = _select_course()

    console.print(Panel.fit(
        "[bold green]IAM User Provisioning[/bold green]\n"
        f"Course ID: [cyan]{course_id}[/cyan]\n"
        "Region: [yellow]us-west-2[/yellow] (EC2 only)",
        title="☁️ AWS IAM",
    ))

    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        BarColumn(),
        TaskProgressColumn(),
        console=console,
    ) as progress:
        task = progress.add_task("[cyan]Starting...", total=None)
        results = provision_students(course_id, progress_callback=_rich_progress_callback(progress, task))

    _display_iam_results(results, "created", "🚀 Provisioning Results", show_password=True)

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
        console.print(f"\n[green]Results written to [bold]{filename}[/bold][/green]")


@iam_app.command("email-credentials")
def email_credentials(
    csv_file: str = typer.Argument(..., help="CSV file generated by 'iam provision'"),
    sender_name: str = typer.Option("Course Instructor", "--sender", "-s", help="Name to use in email signature"),
    all_students: bool = typer.Option(False, "--all", "-a", help="Email all students without prompting"),
    test_email: Optional[str] = typer.Option(None, "--test", "-t", help="Send a test email to this address instead of students"),
):
    """📧 Email credentials to students from a provisioned CSV file."""
    init()
    import os
    from edutools.iam import IAMProvisioner
    from edutools.google_helpers import send_email

    if not os.path.exists(csv_file):
        console.print(f"[red]File not found: {csv_file}[/red]")
        raise typer.Exit(1)

    with open(csv_file, newline="") as f:
        reader = csv.DictReader(f)
        rows = [r for r in reader if r.get("status") == "created" and r.get("email")]

    if not rows:
        console.print("[yellow]No successfully created users found in CSV.[/yellow]")
        raise typer.Exit()

    if test_email:
        selected = [rows[0]]
    elif all_students:
        selected = rows
    else:
        console.print()
        console.print(f"  [cyan]0[/cyan]. All students")
        for i, row in enumerate(rows, 1):
            console.print(f"  [cyan]{i}[/cyan]. {row['email']} [dim]({row['username']})[/dim]")
        console.print()

        choices = typer.prompt("Select students (comma-separated numbers, or 0 for all)")
        nums = [int(n.strip()) for n in choices.split(",")]

        if 0 in nums:
            selected = rows
        else:
            selected = []
            for n in nums:
                if n < 1 or n > len(rows):
                    console.print(f"[red]Invalid selection: {n}[/red]")
                    raise typer.Exit(1)
                selected.append(rows[n - 1])

    iam = IAMProvisioner()
    sign_in_url = iam.get_sign_in_url()

    if test_email:
        console.print(Panel.fit(
            "[bold yellow]TEST MODE[/bold yellow]\n"
            f"Sending to: [cyan]{test_email}[/cyan]\n"
            f"Using sample data from: [dim]{selected[0]['email']}[/dim]\n"
            f"Sign-in URL: [yellow]{sign_in_url}[/yellow]\n"
            f"Sender: [cyan]{sender_name}[/cyan]",
            title="📧 Gmail Test",
        ))
    else:
        console.print(Panel.fit(
            "[bold green]Email Credentials[/bold green]\n"
            f"File: [cyan]{csv_file}[/cyan]\n"
            f"Students: [cyan]{len(selected)}[/cyan]\n"
            f"Sign-in URL: [yellow]{sign_in_url}[/yellow]\n"
            f"Sender: [cyan]{sender_name}[/cyan]",
            title="📧 Gmail",
        ))

    results = []
    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        BarColumn(),
        TaskProgressColumn(),
        console=console,
    ) as progress:
        task = progress.add_task("[cyan]Sending emails...", total=len(selected))
        for i, row in enumerate(selected, 1):
            recipient = test_email if test_email else row["email"]
            username = row["username"]
            password = row["password"]

            progress.update(task, completed=i, description=f"[cyan]Emailing {recipient}")

            subject = "Your AWS Account Credentials"
            body_text = (
                f"Hello,\n\n"
                f"Your AWS IAM account has been created. Here are your login credentials:\n\n"
                f"Sign-in URL: {sign_in_url}\n"
                f"Username: {username}\n"
                f"Temporary Password: {password}\n\n"
                f"IMPORTANT: You will be required to change your password on first login.\n\n"
                f"Your account has permissions to use EC2 (virtual machines) in the us-west-2 region only.\n\n"
                f"Best regards,\n{sender_name}\n"
            )

            email_sent = False
            try:
                result = send_email(to=recipient, subject=subject, body_text=body_text)
                email_sent = result.get("success", False)
                if not email_sent:
                    console.print(f"[red]Failed to email {recipient}: {result.get('error', 'unknown error')}[/red]")
            except Exception as e:
                console.print(f"[red]Failed to email {recipient}: {e}[/red]")

            results.append({"email": recipient, "sent": email_sent})

    sent_count = sum(1 for r in results if r["sent"])
    console.print()
    console.print(Panel.fit(
        f"[bold]Total:[/bold] {len(results)} | "
        f"[green]Sent:[/green] {sent_count} | "
        f"[red]Failed:[/red] {len(results) - sent_count}",
        title="📊 Email Summary",
    ))


@iam_app.command("deprovision")
def deprovision_users(
    course_id: Optional[str] = typer.Argument(None, help="Canvas course ID (prompted if omitted)"),
    confirm: bool = typer.Option(False, "--yes", "-y", help="Skip confirmation prompt"),
):
    """🗑️  Remove IAM users for all students in a Canvas course."""
    init()

    if course_id is None:
        course_id = _select_course()

    if not confirm:
        confirm = typer.confirm(f"⚠️  This will DELETE all IAM users for course {course_id}. Continue?")
        if not confirm:
            console.print("[yellow]Aborted.[/yellow]")
            raise typer.Exit()

    from edutools.iam import deprovision_students

    console.print(Panel.fit(
        "[bold red]IAM User Deprovisioning[/bold red]\n"
        f"Course ID: [cyan]{course_id}[/cyan]",
        title="☁️ AWS IAM",
    ))

    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        BarColumn(),
        TaskProgressColumn(),
        console=console,
    ) as progress:
        task = progress.add_task("[cyan]Starting...", total=None)
        results = deprovision_students(course_id, progress_callback=_rich_progress_callback(progress, task))

    _display_iam_results(results, "deleted", "🗑️ Deprovisioning Results")


@iam_app.command("reset-passwords")
def reset_passwords(course_id: str = typer.Argument(..., help="Canvas course ID")):
    """🔑 Reset passwords for all student IAM users."""
    init()
    from edutools.iam import reset_student_passwords

    console.print(Panel.fit(
        "[bold yellow]Password Reset[/bold yellow]\n"
        f"Course ID: [cyan]{course_id}[/cyan]",
        title="☁️ AWS IAM",
    ))

    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        BarColumn(),
        TaskProgressColumn(),
        console=console,
    ) as progress:
        task = progress.add_task("[cyan]Starting...", total=None)
        results = reset_student_passwords(course_id, progress_callback=_rich_progress_callback(progress, task))

    _display_iam_results(results, "reset", "🔑 Password Reset Results", show_password=True)


@iam_app.command("reset-password")
def reset_password(username: str = typer.Argument(..., help="IAM username to reset")):
    """🔑 Reset password for a single student IAM user."""
    init()
    from edutools.iam import IAMProvisioner

    with console.status(f"[bold yellow]Resetting password for {username}...", spinner="dots"):
        iam = IAMProvisioner()
        result = iam.reset_password(username)

    if result["status"] == "reset":
        console.print(Panel.fit(
            f"[bold green]Password Reset Successful[/bold green]\n\n"
            f"Username: [cyan]{username}[/cyan]\n"
            f"New Password: [yellow]{result['password']}[/yellow]\n\n"
            "[dim]User will be required to change password on next login.[/dim]",
            title="🔑 AWS IAM",
        ))
    else:
        console.print(f"[red]Failed to reset password for {username}: {result.get('error', 'unknown error')}[/red]")
        raise typer.Exit(1)


@iam_app.command("update-policy")
def update_policy(course_id: str = typer.Argument(..., help="Canvas course ID")):
    """📜 Update EC2 policy for all student IAM users."""
    init()
    from edutools.iam import update_student_policies

    console.print(Panel.fit(
        "[bold blue]Policy Update[/bold blue]\n"
        f"Course ID: [cyan]{course_id}[/cyan]\n"
        "Policy: [yellow]EC2 access in us-west-2 only[/yellow]",
        title="☁️ AWS IAM",
    ))

    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        BarColumn(),
        TaskProgressColumn(),
        console=console,
    ) as progress:
        task = progress.add_task("[cyan]Starting...", total=None)
        results = update_student_policies(course_id, progress_callback=_rich_progress_callback(progress, task))

    _display_iam_results(results, "updated", "📜 Policy Update Results")


def _display_iam_results(results: list, success_status: str, title: str, show_password: bool = False):
    """Display IAM operation results in a fancy table."""
    if not results:
        console.print("[yellow]No students found in course.[/yellow]")
        return

    table = Table(title=title, show_header=True, header_style="bold magenta")
    table.add_column("Email", style="cyan")
    table.add_column("Username", style="green")
    if show_password:
        table.add_column("Password", style="yellow")
    table.add_column("Status", justify="center")

    for r in results:
        status = r["status"]
        if status == success_status:
            status_display = f"[green]✓ {status}[/green]"
        elif status == "skipped":
            status_display = f"[yellow]⊘ {status}[/yellow]"
        else:
            status_display = f"[red]✗ {status}[/red]"

        row = [
            r.get("email", "N/A"),
            r.get("username") or "[dim]N/A[/dim]",
        ]
        if show_password:
            row.append(r.get("password") or "[dim]N/A[/dim]")
        row.append(status_display)

        table.add_row(*row)

    console.print(table)

    # Summary
    success_count = sum(1 for r in results if r["status"] == success_status)
    skipped_count = sum(1 for r in results if r["status"] == "skipped")
    error_count = sum(1 for r in results if r["status"] == "error")

    console.print()
    console.print(Panel.fit(
        f"[bold]Total:[/bold] {len(results)} | "
        f"[green]✓ {success_status.title()}:[/green] {success_count} | "
        f"[yellow]⊘ Skipped:[/yellow] {skipped_count} | "
        f"[red]✗ Errors:[/red] {error_count}",
        title="📊 Summary",
    ))



# ============================================================================
# Google Commands
# ============================================================================

@google_app.command("create-doc")
def create_doc(
    title: str = typer.Argument(..., help="Document title"),
    folder_id: Optional[str] = typer.Argument(None, help="Optional Google Drive folder ID"),
):
    """📄 Create and share a Google Doc."""
    init()
    import edutools.google_helpers as google_helpers

    with console.status("[bold green]Creating Google Doc...", spinner="dots"):
        doc_id = google_helpers.create_doc(title, folder_id)

    console.print(Panel.fit(
        f"[bold green]Document Created![/bold green]\n\n"
        f"Title: [cyan]{title}[/cyan]\n"
        f"Document ID: [yellow]{doc_id}[/yellow]\n"
        f"URL: [link=https://docs.google.com/document/d/{doc_id}]https://docs.google.com/document/d/{doc_id}[/link]",
        title="📄 Google Docs",
    ))


# ============================================================================
# Main Entry Point
# ============================================================================

@app.callback(invoke_without_command=True)
def main(ctx: typer.Context):
    """
    🎓 [bold green]Edu Tools[/bold green] - Educational Technology CLI

    Manage Canvas LMS, AWS IAM users, and Google Docs from the command line.

    [dim]Use --help with any command for more information.[/dim]
    """
    if ctx.invoked_subcommand is None:
        console.print(Panel.fit(
            "[bold green]🎓 Edu Tools CLI[/bold green]\n\n"
            "Available command groups:\n\n"
            "  [cyan]canvas[/cyan]   - Canvas LMS operations (courses, students, assignments)\n"
            "  [cyan]iam[/cyan]      - AWS IAM user management (provision, deprovision, reset)\n"
            "  [cyan]google[/cyan]   - Google Docs operations\n\n"
            "[dim]Run 'edutools <command> --help' for more information.[/dim]",
            title="Welcome",
            border_style="green",
        ))


if __name__ == "__main__":
    app()
