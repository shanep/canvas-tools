import os
import requests
import json
from datetime import datetime, timezone

class CanvasLMS():
    def __init__(self):
        token = os.getenv("CANVAS_TOKEN")
        if not token:
            raise ValueError(
                "CANVAS_TOKEN not set. Add your token to ~/.config/edutools/config.toml [canvas] section."
            )
        self.endpoint = os.getenv("CANVAS_ENDPOINT", "https://boisestatecanvas.instructure.com")
        self.headers = {"Authorization": f"Bearer {token}"}

    def __execute_get(self,param, url=""):
        request = requests.get(self.endpoint + url, params=param, headers=self.headers)
        if not request.ok:
            raise RuntimeError(f"Canvas API error {request.status_code}: {request.text}")
        return json.loads(request.text)


    def get_courses(self):
        params = {"state[]": "available", "enrollment_type": "teacher",
                  "per_page": 40, "include[]": "term"}
        url_postfix = "/api/v1/courses"
        courses = self.__execute_get(params, url_postfix)
        now = datetime.now(timezone.utc)
        active = []
        for c in courses:
            if c.get("workflow_state") != "available":
                continue
            term = c.get("term", {})
            end = term.get("end_at")
            if end and datetime.fromisoformat(end) < now:
                continue
            active.append(c)
        return active

    def get_assignments(self,course_id):
        param = {"per_page": 150}
        url_postfix = f"/api/v1/courses/{course_id}/assignments"
        assignments = self.__execute_get(param, url_postfix)
        return assignments

    def get_students(self, course_id):
        param = {"per_page": 150, "enrollment_type[]": "student"}
        url_postfix = f"/api/v1/courses/{course_id}/users"
        students = self.__execute_get(param, url_postfix)
        return students

    def get_submissions(self, course_id, assignment_id):
        param = {"per_page": 150}
        url_postfix = f"/api/v1/courses/{course_id}/assignments/{assignment_id}/submissions"
        submissions = self.__execute_get(param, url_postfix)
        return submissions

    def get_assignment(self, course_id, assignment_id):
        param = {"per_page": 150}
        url_postfix = f"/api/v1/courses/{course_id}/assignments/{assignment_id}/"
        assignment = self.__execute_get(param, url_postfix)
        return assignment