import typer
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


@iam_app.command("provision")
def provision_users(course_id: str = typer.Argument(..., help="Canvas course ID")):
    """🚀 Create IAM users for all students in a Canvas course (EC2 access only)."""
    init()
    from edutools.iam import provision_students

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


@iam_app.command("provision-email")
def provision_and_email_users(
    course_id: str = typer.Argument(..., help="Canvas course ID"),
    sender_name: str = typer.Option("Course Instructor", "--sender", "-s", help="Name to use in email signature"),
):
    """📧 Create IAM users AND email credentials to all students."""
    init()
    from edutools.iam import provision_and_email_students, IAMProvisioner

    # Get sign-in URL to display
    iam = IAMProvisioner()
    sign_in_url = iam.get_sign_in_url()

    console.print(Panel.fit(
        "[bold green]IAM User Provisioning + Email[/bold green]\n"
        f"Course ID: [cyan]{course_id}[/cyan]\n"
        f"Sign-in URL: [yellow]{sign_in_url}[/yellow]\n"
        f"Sender: [cyan]{sender_name}[/cyan]\n"
        "Region: [yellow]us-west-2[/yellow] (EC2 only)",
        title="☁️ AWS IAM + 📧 Gmail",
    ))

    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        BarColumn(),
        TaskProgressColumn(),
        console=console,
    ) as progress:
        task = progress.add_task("[cyan]Starting...", total=None)
        results = provision_and_email_students(
            course_id,
            sender_name=sender_name,
            progress_callback=_rich_progress_callback(progress, task)
        )

    _display_iam_results_with_email(results, "📧 Provisioning + Email Results")


@iam_app.command("deprovision")
def deprovision_users(
    course_id: str = typer.Argument(..., help="Canvas course ID"),
    confirm: bool = typer.Option(False, "--yes", "-y", help="Skip confirmation prompt"),
):
    """🗑️  Remove IAM users for all students in a Canvas course."""
    init()

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


def _display_iam_results_with_email(results: list, title: str):
    """Display IAM + email operation results in a fancy table."""
    if not results:
        console.print("[yellow]No students found in course.[/yellow]")
        return

    table = Table(title=title, show_header=True, header_style="bold magenta")
    table.add_column("Email", style="cyan")
    table.add_column("Username", style="green")
    table.add_column("Password", style="yellow")
    table.add_column("IAM", justify="center")
    table.add_column("Email Sent", justify="center")

    for r in results:
        status = r["status"]
        if status == "created":
            iam_display = "[green]✓ created[/green]"
        elif status == "skipped":
            iam_display = "[yellow]⊘ skipped[/yellow]"
        else:
            iam_display = f"[red]✗ {status}[/red]"

        email_sent = r.get("email_sent", False)
        email_display = "[green]✓ sent[/green]" if email_sent else "[dim]—[/dim]"

        table.add_row(
            r.get("email", "N/A"),
            r.get("username") or "[dim]N/A[/dim]",
            r.get("password") or "[dim]N/A[/dim]",
            iam_display,
            email_display,
        )

    console.print(table)

    # Summary
    created_count = sum(1 for r in results if r["status"] == "created")
    skipped_count = sum(1 for r in results if r["status"] == "skipped")
    error_count = sum(1 for r in results if r["status"] == "error")
    emailed_count = sum(1 for r in results if r.get("email_sent", False))

    console.print()
    console.print(Panel.fit(
        f"[bold]Total:[/bold] {len(results)} | "
        f"[green]✓ Created:[/green] {created_count} | "
        f"[yellow]⊘ Skipped:[/yellow] {skipped_count} | "
        f"[red]✗ Errors:[/red] {error_count}\n"
        f"[bold]Emails Sent:[/bold] {emailed_count}",
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
