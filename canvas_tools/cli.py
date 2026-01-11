import argparse
import canvas_tools.canvas as canvas

parser = argparse.ArgumentParser(description='Canvas tools for grading')
parser.add_argument("-a", help="List all assignments for course", metavar="<course_id>")
parser.add_argument("-c", help="List all active courses", action='store_true')
parser.add_argument("-u", help="List all users in the course", metavar="<course_id>")
parser.add_argument("-s", help="List all submissions for assignment", nargs=2, metavar=('<course_id>', '<assignment_id>'))

args = parser.parse_args()

__version__ = "0.1.0"

def main(argv=None):

    if args.c:
        courses = canvas.get_courses()
        for c in courses:
            print(f'{c["id"]:5} {c["name"]}')
    elif args.a:
        assignments = canvas.get_assignments(args.a)
        for a in assignments:
            print(f'{a["id"]} {a["name"]}')
    elif args.u:
        students = canvas.get_students(args.u)
        for s in students:
            print(f'{s["id"]} - {s["email"]}')
    elif args.s:
        submissions = canvas.get_submissions(args.s[0],args.s[1])
        for sub in submissions:
            print(f'{sub["user_id"]} - {sub["grade"]}')
    else:
        parser.print_help()

if __name__ == "__main__":
    raise SystemExit(main())
