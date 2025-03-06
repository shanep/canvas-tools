# canvas-tools

Tools for working with the canvas reset API:

- [https://canvas.instructure.com/doc/api/](https://canvas.instructure.com/doc/api/)

## Dependencies

- python3 -m pip install requests
- python3 -m pip install python-dotenv

## Configuration

- Generate a canvas API access token from the settings page in canvas
  - [How to generate API Access Token](https://community.canvaslms.com/t5/Canvas-Basics-Guide/How-do-I-manage-API-access-tokens-in-my-user-account/ta-p/615312)
- Create a .env file in the same directory as the canvas.py file with the
  following variables. Replace YOUR_CANVAS_API_TOKEN_HERE with the token
  generated from canvas, you must include the Bearer keyword before the token
  and have a space between bearer and the token.

Variables:
```
CANVAS_TOKEN=Bearer YOUR_CANVAS_API_TOKEN_HERE
```

Example .env file:
```
CANVAS_TOKEN=Bearer 13342~FaMaaBv2hasdfsdfMaNQ9K6PReNsadfasdfsWcrMaPeutJH86asdfasdfNQ8
```

Once you have created the .env file your directory should look like this:
```
shane|(master *%=):canvas-tools$ ll -a
total 56
drwxr-xr-x   8 shane  staff   256 Mar  6 16:00 .
drwxr-xr-x  68 shane  staff  2176 Mar  6 15:48 ..
-rw-r--r--   1 shane  staff    90 Mar  6 16:00 .env
drwxr-xr-x  13 shane  staff   416 Mar  6 15:49 .git
-rw-r--r--   1 shane  staff  3415 Mar  6 15:48 .gitignore
-rw-r--r--   1 shane  staff  1072 Mar  6 15:48 LICENSE
-rw-r--r--   1 shane  staff  1626 Mar  6 15:58 README.md
-rwxr-xr-x   1 shane  staff  9229 Mar  6 15:49 canvas.py
```

## Usage

You can test the configuration by listing all active courses with the -c flag.

```
shane|(master<):grading$ ./canvas.py -c
23688 *Sandbox CS117 - C++ For Engineers
30877 Department of Computer Science - Students Groups
 4432 Fa21 - CS-HU 250 - Intro to Version Control
14333 Fa22 - CS 221 - Computer Science II
14640 Fa22 - CS 401 - Intro to Web Development
16069 Fa22 - CS-HU 250 - Intro to Version Control
22537 Fa23 - CS 155 - Intro to Version Control
...
```

## Currently, implemented tools

```
usage: canvas.py [-h] [-a <course_id>] [-c] [-u <course_id>] [-s <course_id> <assignment_id>]
                 [-f <course_id> <assignment_id> <filename>]
                 [-z <course_id> <assignment_id> <filename>]

Canvas tools for grading

options:
  -h, --help            show this help message and exit
  -a <course_id>        List all assignments for course
  -c                    List all active courses
  -u <course_id>        List all users in the course
  -s <course_id> <assignment_id>
                        List all submissions for assignment
  -z <course_id> <assignment_id> <filename>
                        Update zybooks grades for a course and assignment
```