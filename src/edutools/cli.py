import os
import tomllib
import typer
import csv
from typing import Optional
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn, TaskProgressColumn
from rich import print as rprint

CONFIG_DIR = os.path.join(os.path.expanduser("~"), ".config", "edutools")
CONFIG_FILE = os.path.join(CONFIG_DIR, "config.toml")

_DEFAULT_CONFIG = """\
# Edutools Configuration
# Fill in the values below for each service you want to use.
# Run 'edutools check' to verify your credentials after editing.

[canvas]
# API access token (required for Canvas commands)
# Generate at: Canvas -> Account -> Settings -> Approved Integrations -> + New Access Token
token = ""
# Canvas instance URL (optional, defaults to https://boisestatecanvas.instructure.com)
# endpoint = "https://boisestatecanvas.instructure.com"

[google]
# Path to Google OAuth client_secret.json (optional)
# Default location: ~/.config/edutools/client_secret.json
#
# Setup steps:
#   1. Create a project at https://console.cloud.google.com
#   2. Enable the Google Docs, Drive, and Gmail APIs
#   3. Create OAuth 2.0 credentials (Desktop application)
#   4. Download the client secrets JSON and save to ~/.config/edutools/client_secret.json
# oauth_path = ""

[aws]
# AWS credentials for IAM user management
# Get these from AWS IAM console -> Security Credentials
access_key_id = ""
secret_access_key = ""
# AWS region (optional, defaults to us-west-2)
# region = "us-west-2"
"""

app = typer.Typer(
    name="edutools",
    help="🎓 Educational Tools CLI - Manage Canvas LMS, AWS IAM, and Google Docs",
    add_completion=False,
    rich_markup_mode="rich",
)

console = Console()

# Sub-apps for organization
canvas_app = typer.Typer(help="📚 Canvas LMS operations", no_args_is_help=True)
iam_app = typer.Typer(help="☁️  AWS IAM user management", no_args_is_help=True)
google_app = typer.Typer(help="📄 Google Docs operations", no_args_is_help=True)

app.add_typer(canvas_app, name="canvas")
app.add_typer(iam_app, name="iam")
app.add_typer(google_app, name="google")


def _check_config() -> tuple[bool, bool, bool]:
    """Check which services are configured. Returns (canvas, google, aws)."""
    has_canvas = bool(os.getenv("CANVAS_TOKEN"))
    has_google = os.path.exists(os.path.join(CONFIG_DIR, "client_secret.json"))
    has_aws = bool(os.getenv("AWS_ACCESS_KEY_ID") and os.getenv("AWS_SECRET_ACCESS_KEY"))
    if not has_aws:
        has_aws = os.path.exists(os.path.join(os.path.expanduser("~"), ".aws", "credentials"))
    return has_canvas, has_google, has_aws


def _show_setup_status(has_canvas: bool, has_google: bool, has_aws: bool) -> None:
    """Display which services are configured and setup instructions for missing ones."""
    lines: list[str] = []

    lines.append(f"Config file: [cyan]{CONFIG_FILE}[/cyan]\n")

    # --- Canvas ---
    if has_canvas:
        lines.append("[green]✓[/green] [bold magenta]Canvas LMS[/bold magenta] - configured")
    else:
        lines.append("[red]✗[/red] [bold magenta]Canvas LMS[/bold magenta] - not configured")
        lines.append(f"  Edit [cyan]{CONFIG_FILE}[/cyan] [canvas] section:")
        lines.append("  [yellow]token[/yellow]    - API access token (required)")
        lines.append("              Generate at: Canvas -> Account -> Settings")
        lines.append("              -> Approved Integrations -> + New Access Token")
        lines.append("  [yellow]endpoint[/yellow] - Canvas URL (optional)")
        lines.append("              Defaults to https://boisestatecanvas.instructure.com")

    lines.append("")

    # --- Google ---
    if has_google:
        lines.append("[green]✓[/green] [bold magenta]Google Docs / Gmail[/bold magenta] - configured")
    else:
        lines.append("[red]✗[/red] [bold magenta]Google Docs / Gmail[/bold magenta] - not configured")
        lines.append("  1. Create a project at https://console.cloud.google.com")
        lines.append("  2. Enable the Google Docs, Drive, and Gmail APIs")
        lines.append("  3. Create OAuth 2.0 credentials (Desktop application)")
        lines.append("  4. Download the client secrets JSON and save as:")
        lines.append(f"     [cyan]{os.path.join(CONFIG_DIR, 'client_secret.json')}[/cyan]")
        lines.append(f"  Or set [yellow]oauth_path[/yellow] in [cyan]{CONFIG_FILE}[/cyan] [google] section")

    lines.append("")

    # --- AWS ---
    if has_aws:
        lines.append("[green]✓[/green] [bold magenta]AWS IAM[/bold magenta] - configured")
    else:
        lines.append("[red]✗[/red] [bold magenta]AWS IAM[/bold magenta] - not configured")
        lines.append(f"  Edit [cyan]{CONFIG_FILE}[/cyan] [aws] section:")
        lines.append("  [yellow]access_key_id[/yellow]     - Your AWS access key")
        lines.append("  [yellow]secret_access_key[/yellow] - Your AWS secret key")

    lines.append("")
    lines.append("[dim]Run 'edutools check' to verify credentials work.[/dim]")

    console.print(Panel.fit(
        "\n".join(lines),
        title="Setup Status",
        border_style="yellow",
    ))


def _load_config() -> dict[str, dict[str, str]]:
    """Read config.toml and set environment variables for all services.

    Config file values take precedence over existing environment variables.
    """
    if not os.path.exists(CONFIG_FILE):
        return {}

    with open(CONFIG_FILE, "rb") as f:
        config = tomllib.load(f)

    # Canvas
    canvas = config.get("canvas", {})
    if canvas.get("token"):
        os.environ["CANVAS_TOKEN"] = canvas["token"]
    if canvas.get("endpoint"):
        os.environ["CANVAS_ENDPOINT"] = canvas["endpoint"]

    # AWS
    aws = config.get("aws", {})
    if aws.get("access_key_id"):
        os.environ["AWS_ACCESS_KEY_ID"] = aws["access_key_id"]
    if aws.get("secret_access_key"):
        os.environ["AWS_SECRET_ACCESS_KEY"] = aws["secret_access_key"]
    if aws.get("region"):
        os.environ["AWS_DEFAULT_REGION"] = aws["region"]

    # Google
    google = config.get("google", {})
    if google.get("oauth_path"):
        os.environ["GOOGLE_OAUTH_PATH"] = google["oauth_path"]

    return config


def init():
    """Initialize environment and ensure config directory exists."""
    os.makedirs(CONFIG_DIR, exist_ok=True)

    # Create default config file with placeholders on first run
    if not os.path.exists(CONFIG_FILE):
        with open(CONFIG_FILE, "w", encoding="utf-8") as f:
            f.write(_DEFAULT_CONFIG)

    _load_config()
    has_canvas, has_google, has_aws = _check_config()
    if not has_canvas or not has_google or not has_aws:
        _show_setup_status(has_canvas, has_google, has_aws)


# ============================================================================
# Check Command
# ============================================================================

@app.command("check")
def check_credentials():
    """🔍 Test all configured service credentials."""
    init()

    passed = 0
    failed = 0
    skipped = 0
    results: list[str] = []

    def _ok(service: str, detail: str) -> None:
        nonlocal passed
        passed += 1
        results.append(f"  [green]✓[/green] [bold]{service}[/bold] — {detail}")

    def _fail(service: str, detail: str, error: str) -> None:
        nonlocal failed
        failed += 1
        results.append(f"  [red]✗[/red] [bold]{service}[/bold] — {detail}")
        results.append(f"    [red]Error:[/red] {error}")

    def _skip(service: str, detail: str) -> None:
        nonlocal skipped
        skipped += 1
        results.append(f"  [yellow]⊘[/yellow] [bold]{service}[/bold] — {detail}")

    # --- Canvas ---
    canvas_endpoint = os.getenv("CANVAS_ENDPOINT", "https://boisestatecanvas.instructure.com")
    canvas_token = os.getenv("CANVAS_TOKEN")
    if not canvas_token:
        _skip("Canvas LMS", "token not set in config.toml [canvas] section")
    else:
        try:
            from edutools.canvas import CanvasLMS
            with console.status("[bold green]Testing Canvas...", spinner="dots"):
                canvas = CanvasLMS()
                courses = canvas.get_courses()
            _ok("Canvas LMS", f"{canvas_endpoint} ({len(courses)} courses)")
        except (Exception, SystemExit) as e:
            _fail("Canvas LMS", canvas_endpoint, str(e))

    # --- Google Docs / Drive ---
    try:
        from edutools.google_helpers import _get_oauth_path
        _get_oauth_path()
        oauth_found = True
    except (Exception, SystemExit):
        oauth_found = False

    if not oauth_found:
        _skip("Google Docs", "client_secret.json not found in ~/.config/edutools/")
        _skip("Gmail", "Requires Google OAuth (see Google Docs above)")
    else:
        try:
            from edutools.google_helpers import _get_credentials
            with console.status("[bold green]Testing Google Docs...", spinner="dots"):
                _get_credentials()
            _ok("Google Docs", "OAuth token valid")
        except (Exception, SystemExit) as e:
            _fail("Google Docs", "OAuth authentication failed", str(e))

        try:
            from edutools.google_helpers import _get_gmail_credentials
            with console.status("[bold green]Testing Gmail...", spinner="dots"):
                _get_gmail_credentials()
            _ok("Gmail", "OAuth token valid")
        except (Exception, SystemExit) as e:
            _fail("Gmail", "OAuth authentication failed", str(e))

    # --- AWS IAM ---
    try:
        import boto3
        with console.status("[bold green]Testing AWS...", spinner="dots"):
            sts = boto3.client("sts")
            identity = sts.get_caller_identity()
        account_id = identity["Account"]
        arn = identity["Arn"]
        _ok("AWS IAM", f"Account {account_id} ({arn})")
    except ImportError:
        _skip("AWS IAM", "boto3 not installed")
    except (Exception, SystemExit) as e:
        _fail("AWS IAM", "STS GetCallerIdentity failed", str(e))

    # --- Summary ---
    console.print()
    console.print(Panel.fit(
        "\n".join(results) + "\n\n"
        f"[green]✓ Passed: {passed}[/green]  "
        f"[red]✗ Failed: {failed}[/red]  "
        f"[yellow]⊘ Skipped: {skipped}[/yellow]",
        title="Credential Check",
        border_style="green" if failed == 0 else "red",
    ))


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


@canvas_app.command("assignments", no_args_is_help=True)
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


@canvas_app.command("students", no_args_is_help=True)
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


@canvas_app.command("submissions", no_args_is_help=True)
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


@iam_app.command("email-credentials", no_args_is_help=True)
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


@iam_app.command("reset-passwords", no_args_is_help=True)
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


@iam_app.command("reset-password", no_args_is_help=True)
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


@iam_app.command("update-policy", no_args_is_help=True)
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

@google_app.command("create-doc", no_args_is_help=True)
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
    init()
    if ctx.invoked_subcommand is None:
        console.print(Panel.fit(
            "[bold green]🎓 Edu Tools CLI[/bold green]\n\n"
            "Available command groups:\n\n"
            "  [cyan]canvas[/cyan]   - Canvas LMS operations (courses, students, assignments)\n"
            "  [cyan]iam[/cyan]      - AWS IAM user management (provision, deprovision, reset)\n"
            "  [cyan]google[/cyan]   - Google Docs operations\n\n"
            "  [cyan]check[/cyan]    - Test all configured service credentials\n\n"
            "[dim]Run 'edutools <command> --help' for more information.[/dim]",
            title="Welcome",
            border_style="green",
        ))


if __name__ == "__main__":
    app()
