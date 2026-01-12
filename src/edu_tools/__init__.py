import os
from dotenv import load_dotenv

def load_canvas_config():
    global endpoint, headers
    tmp = os.getenv('CANVAS_ENDPOINT')
    headers = {'Authorization': f'Bearer {os.getenv("CANVAS_TOKEN")}'}
    if not tmp or not headers['Authorization']:
        raise ValueError("CANVAS_ENDPOINT and CANVAS_TOKEN must be set in environment variables.")
    endpoint = tmp


load_dotenv()
load_canvas_config()

__all__ = ["endpoint", "headers"]
