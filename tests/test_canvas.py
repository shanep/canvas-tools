import os
import pytest
from unittest.mock import patch, MagicMock
from edutools.canvas import CanvasLMS


class TestCanvasLMSInitialization:
    """Test CanvasLMS initialization"""

    def test_init_with_valid_env_vars(self):
        """Test successful initialization with valid environment variables"""
        with patch.dict(
            os.environ,
            {"CANVAS_ENDPOINT": "https://canvas.example.com/api/v1/courses", "CANVAS_TOKEN": "test_token_123"},
        ):
            canvas = CanvasLMS()
            assert canvas.endpoint == "https://canvas.example.com/api/v1/courses"
            assert canvas.headers["Authorization"] == "Bearer test_token_123"

    def test_init_missing_endpoint(self):
        """Test initialization fails without CANVAS_ENDPOINT"""
        with patch.dict(os.environ, {"CANVAS_TOKEN": "test_token"}, clear=True):
            with pytest.raises(ValueError, match="CANVAS_ENDPOINT and CANVAS_TOKEN must be set"):
                CanvasLMS()

    def test_init_missing_token(self):
        """Test initialization succeeds even without CANVAS_TOKEN (creates 'Bearer None' header)"""
        with patch.dict(os.environ, {"CANVAS_ENDPOINT": "https://canvas.example.com/api/v1"}, clear=True):
            canvas = CanvasLMS()
            assert canvas.endpoint == "https://canvas.example.com/api/v1"
            assert canvas.headers["Authorization"] == "Bearer None"

    def test_init_empty_token(self):
        """Test initialization succeeds with empty CANVAS_TOKEN (creates 'Bearer ' header)"""
        with patch.dict(
            os.environ, {"CANVAS_ENDPOINT": "https://canvas.example.com/api/v1", "CANVAS_TOKEN": ""}
        ):
            canvas = CanvasLMS()
            assert canvas.endpoint == "https://canvas.example.com/api/v1"
            assert canvas.headers["Authorization"] == "Bearer "

    def test_init_empty_endpoint(self):
        """Test initialization fails with empty CANVAS_ENDPOINT"""
        with patch.dict(
            os.environ, {"CANVAS_ENDPOINT": "", "CANVAS_TOKEN": "test_token"}
        ):
            with pytest.raises(ValueError, match="CANVAS_ENDPOINT and CANVAS_TOKEN must be set"):
                CanvasLMS()


class TestCanvasLMSGetCourses:
    """Test get_courses method"""

    @patch("edutools.canvas.requests.get")
    def test_get_courses_success(self, mock_get):
        """Test successful retrieval of courses"""
        mock_response = MagicMock()
        mock_response.ok = True
        mock_response.text = '[{"id": 1, "name": "Course 1"}, {"id": 2, "name": "Course 2"}]'
        mock_get.return_value = mock_response

        with patch.dict(
            os.environ,
            {"CANVAS_ENDPOINT": "https://canvas.example.com/api/v1/courses", "CANVAS_TOKEN": "test_token"},
        ):
            canvas = CanvasLMS()
            courses = canvas.get_courses()

            assert len(courses) == 2
            assert courses[0]["id"] == 1
            assert courses[0]["name"] == "Course 1"
            assert courses[1]["id"] == 2
            assert courses[1]["name"] == "Course 2"

            # Verify request parameters
            mock_get.assert_called_once()
            call_args = mock_get.call_args
            assert call_args[1]["params"]["state[]"] == "available"
            assert call_args[1]["params"]["enrollment_type"] == "teacher"
            assert call_args[1]["params"]["per_page"] == 40

    @patch("edutools.canvas.requests.get")
    def test_get_courses_empty(self, mock_get):
        """Test get_courses when no courses available"""
        mock_response = MagicMock()
        mock_response.ok = True
        mock_response.text = "[]"
        mock_get.return_value = mock_response

        with patch.dict(
            os.environ,
            {"CANVAS_ENDPOINT": "https://canvas.example.com/api/v1/courses", "CANVAS_TOKEN": "test_token"},
        ):
            canvas = CanvasLMS()
            courses = canvas.get_courses()
            assert courses == []

    @patch("edutools.canvas.requests.get")
    def test_get_courses_api_failure(self, mock_get):
        """Test get_courses when API returns error"""
        mock_response = MagicMock()
        mock_response.ok = False
        mock_response.status_code = 401
        mock_response.text = "Unauthorized"
        mock_get.return_value = mock_response

        with patch.dict(
            os.environ,
            {"CANVAS_ENDPOINT": "https://canvas.example.com/api/v1/courses", "CANVAS_TOKEN": "test_token"},
        ):
            canvas = CanvasLMS()
            with pytest.raises(SystemExit) as exc_info:
                canvas.get_courses()
            assert exc_info.value.code == 401


class TestCanvasLMSGetAssignments:
    """Test get_assignments method"""

    @patch("edutools.canvas.requests.get")
    def test_get_assignments_success(self, mock_get):
        """Test successful retrieval of assignments"""
        mock_response = MagicMock()
        mock_response.ok = True
        mock_response.text = '[{"id": 1, "name": "Assignment 1"}, {"id": 2, "name": "Assignment 2"}]'
        mock_get.return_value = mock_response

        with patch.dict(
            os.environ,
            {"CANVAS_ENDPOINT": "https://canvas.example.com/api/v1/courses", "CANVAS_TOKEN": "test_token"},
        ):
            canvas = CanvasLMS()
            assignments = canvas.get_assignments(123)

            assert len(assignments) == 2
            assert assignments[0]["id"] == 1
            assert assignments[1]["name"] == "Assignment 2"

            # Verify URL construction
            mock_get.assert_called_once()
            call_args = mock_get.call_args
            assert "/123/assignments" in call_args[0][0]
            assert call_args[1]["params"]["per_page"] == 150

    @patch("edutools.canvas.requests.get")
    def test_get_assignments_empty(self, mock_get):
        """Test get_assignments when no assignments exist"""
        mock_response = MagicMock()
        mock_response.ok = True
        mock_response.text = "[]"
        mock_get.return_value = mock_response

        with patch.dict(
            os.environ,
            {"CANVAS_ENDPOINT": "https://canvas.example.com/api/v1/courses", "CANVAS_TOKEN": "test_token"},
        ):
            canvas = CanvasLMS()
            assignments = canvas.get_assignments(123)
            assert assignments == []

    @patch("edutools.canvas.requests.get")
    def test_get_assignments_api_failure(self, mock_get):
        """Test get_assignments when API returns error"""
        mock_response = MagicMock()
        mock_response.ok = False
        mock_response.status_code = 404
        mock_response.text = "Not Found"
        mock_get.return_value = mock_response

        with patch.dict(
            os.environ,
            {"CANVAS_ENDPOINT": "https://canvas.example.com/api/v1/courses", "CANVAS_TOKEN": "test_token"},
        ):
            canvas = CanvasLMS()
            with pytest.raises(SystemExit) as exc_info:
                canvas.get_assignments(999)
            assert exc_info.value.code == 404


class TestCanvasLMSGetStudents:
    """Test get_students method"""

    @patch("edutools.canvas.requests.get")
    def test_get_students_success(self, mock_get):
        """Test successful retrieval of students"""
        mock_response = MagicMock()
        mock_response.ok = True
        mock_response.text = '[{"id": 1, "name": "Student 1"}, {"id": 2, "name": "Student 2"}]'
        mock_get.return_value = mock_response

        with patch.dict(
            os.environ,
            {"CANVAS_ENDPOINT": "https://canvas.example.com/api/v1/courses", "CANVAS_TOKEN": "test_token"},
        ):
            canvas = CanvasLMS()
            students = canvas.get_students(123)

            assert len(students) == 2
            assert students[0]["id"] == 1
            assert students[1]["name"] == "Student 2"

            # Verify URL construction
            mock_get.assert_called_once()
            call_args = mock_get.call_args
            assert "/123/users" in call_args[0][0]
            assert call_args[1]["params"]["enrollment_type[]"] == "student"
            assert call_args[1]["params"]["per_page"] == 150

    @patch("edutools.canvas.requests.get")
    def test_get_students_empty(self, mock_get):
        """Test get_students when no students enrolled"""
        mock_response = MagicMock()
        mock_response.ok = True
        mock_response.text = "[]"
        mock_get.return_value = mock_response

        with patch.dict(
            os.environ,
            {"CANVAS_ENDPOINT": "https://canvas.example.com/api/v1/courses", "CANVAS_TOKEN": "test_token"},
        ):
            canvas = CanvasLMS()
            students = canvas.get_students(123)
            assert students == []

    @patch("edutools.canvas.requests.get")
    def test_get_students_api_failure(self, mock_get):
        """Test get_students when API returns error"""
        mock_response = MagicMock()
        mock_response.ok = False
        mock_response.status_code = 403
        mock_response.text = "Forbidden"
        mock_get.return_value = mock_response

        with patch.dict(
            os.environ,
            {"CANVAS_ENDPOINT": "https://canvas.example.com/api/v1/courses", "CANVAS_TOKEN": "test_token"},
        ):
            canvas = CanvasLMS()
            with pytest.raises(SystemExit) as exc_info:
                canvas.get_students(123)
            assert exc_info.value.code == 403


class TestCanvasLMSGetSubmissions:
    """Test get_submissions method"""

    @patch("edutools.canvas.requests.get")
    def test_get_submissions_success(self, mock_get):
        """Test successful retrieval of submissions"""
        mock_response = MagicMock()
        mock_response.ok = True
        mock_response.text = '[{"id": 1, "user_id": 101}, {"id": 2, "user_id": 102}]'
        mock_get.return_value = mock_response

        with patch.dict(
            os.environ,
            {"CANVAS_ENDPOINT": "https://canvas.example.com/api/v1/courses", "CANVAS_TOKEN": "test_token"},
        ):
            canvas = CanvasLMS()
            submissions = canvas.get_submissions(123, 456)

            assert len(submissions) == 2
            assert submissions[0]["id"] == 1
            assert submissions[1]["user_id"] == 102

            # Verify URL construction
            mock_get.assert_called_once()
            call_args = mock_get.call_args
            assert "/123/assignments/456/submissions" in call_args[0][0]
            assert call_args[1]["params"]["per_page"] == 150

    @patch("edutools.canvas.requests.get")
    def test_get_submissions_empty(self, mock_get):
        """Test get_submissions when no submissions exist"""
        mock_response = MagicMock()
        mock_response.ok = True
        mock_response.text = "[]"
        mock_get.return_value = mock_response

        with patch.dict(
            os.environ,
            {"CANVAS_ENDPOINT": "https://canvas.example.com/api/v1/courses", "CANVAS_TOKEN": "test_token"},
        ):
            canvas = CanvasLMS()
            submissions = canvas.get_submissions(123, 456)
            assert submissions == []

    @patch("edutools.canvas.requests.get")
    def test_get_submissions_api_failure(self, mock_get):
        """Test get_submissions when API returns error"""
        mock_response = MagicMock()
        mock_response.ok = False
        mock_response.status_code = 500
        mock_response.text = "Internal Server Error"
        mock_get.return_value = mock_response

        with patch.dict(
            os.environ,
            {"CANVAS_ENDPOINT": "https://canvas.example.com/api/v1/courses", "CANVAS_TOKEN": "test_token"},
        ):
            canvas = CanvasLMS()
            with pytest.raises(SystemExit) as exc_info:
                canvas.get_submissions(123, 456)
            assert exc_info.value.code == 500


class TestCanvasLMSGetAssignment:
    """Test get_assignment method"""

    @patch("edutools.canvas.requests.get")
    def test_get_assignment_success(self, mock_get):
        """Test successful retrieval of single assignment"""
        mock_response = MagicMock()
        mock_response.ok = True
        mock_response.text = '{"id": 456, "name": "Final Project", "due_at": "2024-12-15"}'
        mock_get.return_value = mock_response

        with patch.dict(
            os.environ,
            {"CANVAS_ENDPOINT": "https://canvas.example.com/api/v1/courses", "CANVAS_TOKEN": "test_token"},
        ):
            canvas = CanvasLMS()
            assignment = canvas.get_assignment(123, 456)

            assert assignment["id"] == 456
            assert assignment["name"] == "Final Project"
            assert assignment["due_at"] == "2024-12-15"

            # Verify URL construction
            mock_get.assert_called_once()
            call_args = mock_get.call_args
            assert "/123/assignments/456/" in call_args[0][0]
            assert call_args[1]["params"]["per_page"] == 150

    @patch("edutools.canvas.requests.get")
    def test_get_assignment_not_found(self, mock_get):
        """Test get_assignment when assignment doesn't exist"""
        mock_response = MagicMock()
        mock_response.ok = False
        mock_response.status_code = 404
        mock_response.text = "Not Found"
        mock_get.return_value = mock_response

        with patch.dict(
            os.environ,
            {"CANVAS_ENDPOINT": "https://canvas.example.com/api/v1/courses", "CANVAS_TOKEN": "test_token"},
        ):
            canvas = CanvasLMS()
            with pytest.raises(SystemExit) as exc_info:
                canvas.get_assignment(123, 999)
            assert exc_info.value.code == 404

    @patch("edutools.canvas.requests.get")
    def test_get_assignment_api_failure(self, mock_get):
        """Test get_assignment when API returns error"""
        mock_response = MagicMock()
        mock_response.ok = False
        mock_response.status_code = 500
        mock_response.text = "Internal Server Error"
        mock_get.return_value = mock_response

        with patch.dict(
            os.environ,
            {"CANVAS_ENDPOINT": "https://canvas.example.com/api/v1/courses", "CANVAS_TOKEN": "test_token"},
        ):
            canvas = CanvasLMS()
            with pytest.raises(SystemExit) as exc_info:
                canvas.get_assignment(123, 456)
            assert exc_info.value.code == 500


class TestCanvasLMSHeaders:
    """Test that authorization headers are properly set"""

    @patch("edutools.canvas.requests.get")
    def test_headers_sent_with_requests(self, mock_get):
        """Test that authorization headers are sent with API requests"""
        mock_response = MagicMock()
        mock_response.ok = True
        mock_response.text = "[]"
        mock_get.return_value = mock_response

        with patch.dict(
            os.environ,
            {"CANVAS_ENDPOINT": "https://canvas.example.com/api/v1/courses", "CANVAS_TOKEN": "secret_token_xyz"},
        ):
            canvas = CanvasLMS()
            canvas.get_courses()

            # Verify headers include authorization
            call_args = mock_get.call_args
            assert "headers" in call_args[1]
            assert call_args[1]["headers"]["Authorization"] == "Bearer secret_token_xyz"
