import os
from dotenv import load_dotenv

load_dotenv()

endpoint = 'https://boisestatecanvas.instructure.com/api/v1/courses'
headers = {'Authorization': os.getenv('CANVAS_TOKEN')}

__all__ = ["endpoint", "headers"]
