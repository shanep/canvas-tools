import argparse
import os
from dotenv import load_dotenv
from edutools.canvas import CanvasLMS
import edutools.google_helpers as google_helpers

parser = argparse.ArgumentParser(description="Edu Tools CLI")
parser.add_argument("-a", help="List all assignments for course", metavar="<course_id>")
parser.add_argument("-c", help="List all active canvas courses", action="store_true")
parser.add_argument(
    "-u", help="List all users in a canvas course", metavar="<course_id>"
)
parser.add_argument(
    "-s",
    help="List all submissions for assignment",
    nargs=2,
    metavar=("<course_id>", "<assignment_id>"),
)
parser.add_argument(
    "-g",
    help="Create and share Google Doc; pass title and optional folder_id",
    nargs="+",
    metavar=("title", "folder_id"),
)

args = parser.parse_args()



def main(argv=None):
    load_dotenv()
    canvas = CanvasLMS()
    if args.c:
        courses = canvas.get_courses()
        for c in courses:
            print(f"{c['id']:5} {c['name']}")
    elif args.a:
        assignments = canvas.get_assignments(args.a)
        for a in assignments:
            print(f"{a['id']} {a['name']}")
    elif args.u:
        students = canvas.get_students(args.u)
        for s in students:
            print(f"{s['id']} - {s['email']}")
    elif args.s:
        submissions = canvas.get_submissions(args.s[0], args.s[1])
        for sub in submissions:
            print(f"{sub['user_id']} - {sub['grade']}")
    elif args.g:
        if len(args.g) > 2:
            parser.error("-g accepts a title and optional folder_id only")

        title = args.g[0]
        folder_id = args.g[1] if len(args.g) == 2 else None
        doc_id = google_helpers.create_doc(title, folder_id)
        # google.insert_text(doc_id, f'Document Title: {title}\n\n', 1)

        print(f"Created and shared document with ID: {doc_id}")
    else:
        parser.print_help()