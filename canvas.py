#!/usr/bin/env python3
# python3 -m pip install requests
# python3 -m pip install python-dotenv
import requests
import json
import argparse
import csv
import logging
from dotenv import load_dotenv
import os


class Student:
    def __init__(self, user,course_id, assignment_id):
        self.__user = user
        self.__submission = None
        self.__update = False
        self.__course_id = course_id
        self.__assignment_id = assignment_id
        self.__comment = ""

    def __str__(self):
        return str(self.user) + str(self.submission)

    @property
    def submission(self):
        return self.__submission
    @submission.setter
    def submission(self, submission):
        self.__submission = submission

    @property
    def user(self):
        return self.__user
    @user.setter
    def user(self, user):
        self.__user = user

    @property
    def grade(self):
        return self.submission["grade"]
    @grade.setter
    def grade(self, grade):
        if self.submission is None:
            print("Got None type on: " + self.bsu_username)
        else:
            self.submission["grade"]=grade
            self.__update = True

    @property
    def update(self):
        return self.__update

    @property
    def bsu_username(self):
        if self.__user['name'] == 'Test Student':
            return 'test_student'
        else:
            return self.__user['login_id'].lower()

    def update_grade(self):
        """Update a grade for a specific student course and assignment
        course_id The id of the course
        assignment_id The id of the assignment
        student_id The id of the student
        grade is the grade in points, percentage, or float
        comment is any comments to leave to the user

        returns the response object from canvas
        """
        canvas_data = {'submission[posted_grade]' : self.grade , 'comment[text_comment]':self.__comment}
        url_postfix = f'/{self.__course_id}/assignments/{self.__assignment_id}/submissions/{self.user["id"]}'
        request = requests.put(endpoint + url_postfix, headers=headers,data=canvas_data)
        if not request.ok:
            print(f'Failed to connect {request.status_code} - {request.text}')


def __execute_get(param, url=""):
    request = requests.get(endpoint + url ,params=param, headers=headers)
    if not request.ok:
        print(f'Failed to connect {request.status_code} - {request.text}')
        exit(request.status_code)
    return json.loads(request.text)

def print_courses():
    params = {'state[]':'available','enrollment_type':'teacher','per_page': 40}
    courses = __execute_get(params)
    for c in courses:
        print(f'{c["id"]:5} {c["name"]}')

def print_assignments(course_id):
    param = {'per_page':150}
    url_postfix = f'/{course_id}/assignments'
    assignments = __execute_get(param,url_postfix)
    for a in assignments:
        print(f'{a["id"]} {a["name"]}')

def print_students(course_id):
    param = {'per_page':150,'enrollment_type[]':'student'}
    url_postfix = f'/{course_id}/users'
    students = __execute_get(param,url_postfix)
    for s in students:
        print(f'{s["id"]} - {s["email"]}')
    print(len(students))

def print_submissions(course_id,assignment_id):
    param = {'per_page':150}
    url_postfix = f'/{course_id}/assignments/{assignment_id}/submissions'
    submissions = __execute_get(param,url_postfix)
    for a in submissions:
        print(json.dumps(a,indent=4, sort_keys=True))

def get_assignment(course_id, assignment_id):
    param = {'per_page':150}
    url_postfix = f'/{course_id}/assignments/{assignment_id}/'
    assignment = __execute_get(param,url_postfix)
    return assignment

def get_students_and_submissions(course_id, assignment_id):
    """Return a dict of student objects index by their bsu id"""

    tmp = {}
    rval = {}

    # build a list of students indexed on id so we can associate submissions
    param = {'per_page':150,'enrollment_type[]':'student','enrollment_state[]':'active'}
    url_postfix = f'/{course_id}/users'
    students = __execute_get(param,url_postfix)
    for s in students:
        key = int(s["id"])
        tmp[key] = Student(s,course_id,assignment_id)

    # associate submissions with each student
    param_a = {'per_page':250}
    url_postfix = f'/{course_id}/assignments/{assignment_id}/submissions'
    submissions = __execute_get(param_a,url_postfix)
    for s in submissions:
        key = int(s["user_id"])
        # ignore any submissions that are not in tmp they are test users
        if key in tmp:
            tmp[key].submission = s

    # index on login_id which is the students bronco username
    for _,v in tmp.items():
        rval[v.bsu_username] = v

    return rval


def parse_zybooks(file_name):
    """
    Parse out the grades from a zyBook export.
    col 2 should contain the student email if that is blank we can check row 2
    col 4 should contain the total score for the assignment

    returns a dictionary of grades key'd on the username
    """
    with open(file_name) as csvfile:
        reader = csv.reader(csvfile,delimiter=',')
        grades = {}
        reader.__next__()
        for row in reader:
            email = row[2]
            # check if email is not null before we do work
            if email:
                email = email.lower()
                #print(email)
                user, domain = email.split("@")
                if domain == "u.boisestate.edu" or domain == "boisestate.edu":
                    grades[user] = row[6]
                else:
                    logging.warning("Bad email: " + email)
            else:
                logging.warning("No valid email was found: " + row)
    return grades


parser = argparse.ArgumentParser(description='Canvas tools for grading')
parser.add_argument("-a", help="List all assignments for course", metavar="<course_id>")
parser.add_argument("-c", help="List all active courses", action='store_true')
parser.add_argument("-u", help="List all users in the course", metavar="<course_id>")
parser.add_argument("-s", help="List all submissions for assignment", nargs=2, metavar=('<course_id>', '<assignment_id>'))
parser.add_argument("-z", help="Update zybooks grades for a course and assignment", nargs=3, metavar=('<course_id>','<assignment_id>','<filename>'))
args = parser.parse_args()



if __name__ == '__main__':
    load_dotenv()
    endpoint = 'https://boisestatecanvas.instructure.com/api/v1/courses'
    headers = {'Authorization': os.getenv('CANVAS_TOKEN')}
    if args.c:
        print_courses()
    elif args.a:
        print_assignments(args.a)
    elif args.u:
        print_students(args.u)
    elif args.s:
        print_submissions(args.s[0],args.s[1])
    elif args.z:
        course_id = args.z[0]
        assignment_id = args.z[1]
        filename = args.z[2]
        print("Updating course_id:" + course_id + " assignment_id: " + assignment_id)
        assignment = get_assignment(course_id,assignment_id)
        max_grade = assignment['points_possible']
        students=get_students_and_submissions(course_id, assignment_id)
        zybooks = parse_zybooks(filename)
        for stu_id, stu in students.items():
            if stu_id in zybooks:
                zgrade = float(zybooks[stu_id])/100 * max_grade
                stu.grade = zgrade
            else:
                stu.grade = 0

        for stu in students.values():
            if stu.update:
                print("updating:", stu.bsu_username)
                stu.update_grade()
    else:
        parser.print_help()
