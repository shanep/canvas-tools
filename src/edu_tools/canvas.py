# canvas_tools/canvas.py
import os
import requests
import json
from edu_tools import endpoint, headers

def __execute_get(param, url=""):
    request = requests.get(endpoint + url ,params=param, headers=headers)
    if not request.ok:
        print(f'Failed to connect {request.status_code} - {request.text}')
        exit(request.status_code)
    return json.loads(request.text)

def get_courses():
    params = {'state[]':'available','enrollment_type':'teacher','per_page': 40}
    courses = __execute_get(params)
    return courses

def get_assignments(course_id):
    param = {'per_page':150}
    url_postfix = f'/{course_id}/assignments'
    assignments = __execute_get(param,url_postfix)
    return assignments

def get_students(course_id):
    param = {'per_page':150,'enrollment_type[]':'student'}
    url_postfix = f'/{course_id}/users'
    students = __execute_get(param,url_postfix)
    return students

def get_submissions(course_id,assignment_id):
    param = {'per_page':150}
    url_postfix = f'/{course_id}/assignments/{assignment_id}/submissions'
    submissions = __execute_get(param,url_postfix)
    return submissions

def get_assignment(course_id, assignment_id):
    param = {'per_page':150}
    url_postfix = f'/{course_id}/assignments/{assignment_id}/'
    assignment = __execute_get(param,url_postfix)
    return assignment
