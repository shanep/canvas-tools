import os
import requests
import json

class CanvasLMS():
    def __init__(self):
        tmp = os.getenv("CANVAS_ENDPOINT")
        self.headers = {"Authorization": f"Bearer {os.getenv('CANVAS_TOKEN')}"}
        if not tmp or not self.headers["Authorization"]:
            raise ValueError(
                "CANVAS_ENDPOINT and CANVAS_TOKEN must be set in environment variables."
            )
        self.endpoint = tmp

    def __execute_get(self,param, url=""):
        request = requests.get(self.endpoint + url, params=param, headers=self.headers)
        if not request.ok:
            print(f"Failed to connect {request.status_code} - {request.text}")
            exit(request.status_code)
        return json.loads(request.text)


    def get_courses(self):
        params = {"state[]": "available", "enrollment_type": "teacher", "per_page": 40}
        courses = self.__execute_get(params)
        return courses

    def get_assignments(self,course_id):
        param = {"per_page": 150}
        url_postfix = f"/{course_id}/assignments"
        assignments = self.__execute_get(param, url_postfix)
        return assignments

    def get_students(self, course_id):
        param = {"per_page": 150, "enrollment_type[]": "student"}
        url_postfix = f"/{course_id}/users"
        students = self.__execute_get(param, url_postfix)
        return students

    def get_submissions(self, course_id, assignment_id):
        param = {"per_page": 150}
        url_postfix = f"/{course_id}/assignments/{assignment_id}/submissions"
        submissions = self.__execute_get(param, url_postfix)
        return submissions

    def get_assignment(self, course_id, assignment_id):
        param = {"per_page": 150}
        url_postfix = f"/{course_id}/assignments/{assignment_id}/"
        assignment = self.__execute_get(param, url_postfix)
        return assignment