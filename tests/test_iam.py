import json
import os
import string
import pytest
from unittest.mock import patch, MagicMock
from botocore.exceptions import ClientError
from edutools.iam import IAMProvisioner, provision_students, deprovision_students, EC2_POLICY


class TestIAMProvisionerPasswordGeneration:
    """Test password generation functionality"""

    def test_generate_password_default_length(self):
        """Test password generation with default length of 16"""
        provisioner = IAMProvisioner()
        password = provisioner.generate_password()
        assert len(password) == 16

    def test_generate_password_custom_length(self):
        """Test password generation with custom length"""
        provisioner = IAMProvisioner()
        password = provisioner.generate_password(length=24)
        assert len(password) == 24

    def test_generate_password_minimum_length(self):
        """Test that password is at least 8 characters even if shorter requested"""
        provisioner = IAMProvisioner()
        password = provisioner.generate_password(length=4)
        assert len(password) == 8

    def test_generate_password_has_uppercase(self):
        """Test password contains at least one uppercase letter"""
        provisioner = IAMProvisioner()
        password = provisioner.generate_password()
        assert any(c in string.ascii_uppercase for c in password)

    def test_generate_password_has_lowercase(self):
        """Test password contains at least one lowercase letter"""
        provisioner = IAMProvisioner()
        password = provisioner.generate_password()
        assert any(c in string.ascii_lowercase for c in password)

    def test_generate_password_has_digit(self):
        """Test password contains at least one digit"""
        provisioner = IAMProvisioner()
        password = provisioner.generate_password()
        assert any(c in string.digits for c in password)

    def test_generate_password_has_special_char(self):
        """Test password contains at least one special character"""
        provisioner = IAMProvisioner()
        password = provisioner.generate_password()
        special_chars = "!@#$_-"  # AWS-safe special characters
        assert any(c in special_chars for c in password)

    def test_generate_password_uniqueness(self):
        """Test that generated passwords are unique"""
        provisioner = IAMProvisioner()
        passwords = [provisioner.generate_password() for _ in range(10)]
        assert len(set(passwords)) == 10


class TestIAMProvisionerCreateUser:
    """Test IAM user creation"""

    @patch("edutools.iam.boto3.session.Session")
    def test_create_user_success(self, mock_session):
        """Test successful user creation"""
        mock_client = MagicMock()
        mock_session.return_value.client.return_value = mock_client

        provisioner = IAMProvisioner()
        result = provisioner.create_user("testuser")

        assert result["username"] == "testuser"
        assert result["status"] == "created"
        assert result["password"] is not None
        assert result["error"] is None

        # Verify API calls
        mock_client.create_user.assert_called_once_with(UserName="testuser")
        mock_client.create_login_profile.assert_called_once()
        call_args = mock_client.create_login_profile.call_args
        assert call_args[1]["UserName"] == "testuser"
        assert call_args[1]["PasswordResetRequired"] is True

    @patch("edutools.iam.boto3.session.Session")
    def test_create_user_already_exists(self, mock_session):
        """Test handling of user that already exists"""
        mock_client = MagicMock()
        mock_session.return_value.client.return_value = mock_client

        error_response = {"Error": {"Code": "EntityAlreadyExists", "Message": "User already exists"}}
        mock_client.create_user.side_effect = ClientError(error_response, "CreateUser")

        provisioner = IAMProvisioner()
        result = provisioner.create_user("existinguser")

        assert result["username"] == "existinguser"
        assert result["status"] == "skipped"
        assert result["password"] is None
        assert result["error"] == "already exists"

    @patch("edutools.iam.boto3.session.Session")
    def test_create_user_api_error(self, mock_session):
        """Test handling of general API errors"""
        mock_client = MagicMock()
        mock_session.return_value.client.return_value = mock_client

        error_response = {"Error": {"Code": "AccessDenied", "Message": "Access denied"}}
        mock_client.create_user.side_effect = ClientError(error_response, "CreateUser")

        provisioner = IAMProvisioner()
        result = provisioner.create_user("testuser")

        assert result["username"] == "testuser"
        assert result["status"] == "error"
        assert result["password"] is None
        assert "Access denied" in result["error"]


class TestIAMProvisionerAttachPolicy:
    """Test EC2 policy attachment"""

    @patch("edutools.iam.boto3.session.Session")
    def test_attach_ec2_policy_success(self, mock_session):
        """Test successful policy attachment"""
        mock_client = MagicMock()
        mock_session.return_value.client.return_value = mock_client

        provisioner = IAMProvisioner()
        result = provisioner.attach_ec2_policy("testuser")

        assert result is True
        mock_client.put_user_policy.assert_called_once()
        call_args = mock_client.put_user_policy.call_args
        assert call_args[1]["UserName"] == "testuser"
        assert call_args[1]["PolicyName"] == "EC2OnlyAccess"

        # Verify policy document
        policy_doc = json.loads(call_args[1]["PolicyDocument"])
        assert policy_doc == EC2_POLICY

    @patch("edutools.iam.boto3.session.Session")
    def test_attach_ec2_policy_failure(self, mock_session):
        """Test policy attachment failure"""
        mock_client = MagicMock()
        mock_session.return_value.client.return_value = mock_client

        error_response = {"Error": {"Code": "NoSuchEntity", "Message": "User not found"}}
        mock_client.put_user_policy.side_effect = ClientError(error_response, "PutUserPolicy")

        provisioner = IAMProvisioner()
        result = provisioner.attach_ec2_policy("nonexistent")

        assert result is False


class TestEC2Policy:
    """Test the EC2 policy structure"""

    def test_policy_version(self):
        """Test policy has correct version"""
        assert EC2_POLICY["Version"] == "2012-10-17"

    def test_policy_has_ec2_actions(self):
        """Test policy includes expected EC2 actions"""
        # Collect all actions from all statements
        all_actions = []
        for statement in EC2_POLICY["Statement"]:
            all_actions.extend(statement["Action"])

        expected_actions = [
            "ec2:RunInstances",
            "ec2:DescribeInstances",
            "ec2:StartInstances",
            "ec2:StopInstances",
            "ec2:TerminateInstances",
            "ec2:CreateKeyPair",
            "ec2:CreateSecurityGroup",
            "ec2:AuthorizeSecurityGroupIngress",
        ]
        for action in expected_actions:
            assert action in all_actions

    def test_policy_restricted_to_us_west_2(self):
        """Test policy is restricted to us-west-2 region"""
        for statement in EC2_POLICY["Statement"]:
            assert "Condition" in statement
            assert statement["Condition"]["StringEquals"]["ec2:Region"] == "us-west-2"

    def test_policy_effect_is_allow(self):
        """Test policy effect is Allow for all statements"""
        for statement in EC2_POLICY["Statement"]:
            assert statement["Effect"] == "Allow"


class TestProvisionStudents:
    """Test the provision_students workflow function"""

    @patch("edutools.iam.IAMProvisioner")
    @patch("edutools.iam.CanvasLMS")
    def test_provision_students_success(self, mock_canvas_cls, mock_iam_cls):
        """Test successful provisioning of multiple students"""
        # Mock Canvas response
        mock_canvas = MagicMock()
        mock_canvas.get_students.return_value = [
            {"id": 1, "email": "jsmith@example.edu"},
            {"id": 2, "email": "mjones@example.edu"},
        ]
        mock_canvas_cls.return_value = mock_canvas

        # Mock IAM responses
        mock_iam = MagicMock()
        mock_iam.create_user.side_effect = [
            {"username": "jsmith", "password": "Pass123!", "status": "created", "error": None},
            {"username": "mjones", "password": "Pass456!", "status": "created", "error": None},
        ]
        mock_iam_cls.return_value = mock_iam

        with patch.dict(
            os.environ,
            {"CANVAS_ENDPOINT": "https://canvas.example.com/api/v1/courses", "CANVAS_TOKEN": "test_token"},
        ):
            results = provision_students("12345")

        assert len(results) == 2
        assert results[0]["email"] == "jsmith@example.edu"
        assert results[0]["username"] == "jsmith"
        assert results[0]["status"] == "created"
        assert results[1]["email"] == "mjones@example.edu"
        assert results[1]["username"] == "mjones"

        # Verify EC2 policy was attached for created users
        assert mock_iam.attach_ec2_policy.call_count == 2

    @patch("edutools.iam.IAMProvisioner")
    @patch("edutools.iam.CanvasLMS")
    def test_provision_students_skip_existing(self, mock_canvas_cls, mock_iam_cls):
        """Test that existing users are skipped and EC2 policy not reattached"""
        mock_canvas = MagicMock()
        mock_canvas.get_students.return_value = [
            {"id": 1, "email": "existinguser@example.edu"},
        ]
        mock_canvas_cls.return_value = mock_canvas

        mock_iam = MagicMock()
        mock_iam.create_user.return_value = {
            "username": "existinguser",
            "password": None,
            "status": "skipped",
            "error": "already exists",
        }
        mock_iam_cls.return_value = mock_iam

        with patch.dict(
            os.environ,
            {"CANVAS_ENDPOINT": "https://canvas.example.com/api/v1/courses", "CANVAS_TOKEN": "test_token"},
        ):
            results = provision_students("12345")

        assert len(results) == 1
        assert results[0]["status"] == "skipped"
        # EC2 policy should NOT be attached for skipped users
        mock_iam.attach_ec2_policy.assert_not_called()

    @patch("edutools.iam.IAMProvisioner")
    @patch("edutools.iam.CanvasLMS")
    def test_provision_students_no_email(self, mock_canvas_cls, mock_iam_cls):
        """Test handling of students without email addresses"""
        mock_canvas = MagicMock()
        mock_canvas.get_students.return_value = [
            {"id": 1},  # No email field
            {"id": 2, "email": ""},  # Empty email
        ]
        mock_canvas_cls.return_value = mock_canvas

        mock_iam = MagicMock()
        mock_iam_cls.return_value = mock_iam

        with patch.dict(
            os.environ,
            {"CANVAS_ENDPOINT": "https://canvas.example.com/api/v1/courses", "CANVAS_TOKEN": "test_token"},
        ):
            results = provision_students("12345")

        assert len(results) == 2
        assert results[0]["status"] == "skipped"
        assert results[0]["error"] == "no email"
        assert results[1]["status"] == "skipped"
        # No IAM users should be created
        mock_iam.create_user.assert_not_called()

    @patch("edutools.iam.IAMProvisioner")
    @patch("edutools.iam.CanvasLMS")
    def test_provision_students_username_extraction(self, mock_canvas_cls, mock_iam_cls):
        """Test that username is correctly extracted from email"""
        mock_canvas = MagicMock()
        mock_canvas.get_students.return_value = [
            {"id": 1, "email": "john.doe@university.edu"},
        ]
        mock_canvas_cls.return_value = mock_canvas

        mock_iam = MagicMock()
        mock_iam.create_user.return_value = {
            "username": "john.doe",
            "password": "Pass123!",
            "status": "created",
            "error": None,
        }
        mock_iam_cls.return_value = mock_iam

        with patch.dict(
            os.environ,
            {"CANVAS_ENDPOINT": "https://canvas.example.com/api/v1/courses", "CANVAS_TOKEN": "test_token"},
        ):
            results = provision_students("12345")

        # Verify username was extracted correctly (part before @)
        mock_iam.create_user.assert_called_once_with("john.doe")
        assert results[0]["username"] == "john.doe"

    @patch("edutools.iam.IAMProvisioner")
    @patch("edutools.iam.CanvasLMS")
    def test_provision_students_empty_course(self, mock_canvas_cls, mock_iam_cls):
        """Test provisioning for a course with no students"""
        mock_canvas = MagicMock()
        mock_canvas.get_students.return_value = []
        mock_canvas_cls.return_value = mock_canvas

        mock_iam = MagicMock()
        mock_iam_cls.return_value = mock_iam

        with patch.dict(
            os.environ,
            {"CANVAS_ENDPOINT": "https://canvas.example.com/api/v1/courses", "CANVAS_TOKEN": "test_token"},
        ):
            results = provision_students("12345")

        assert results == []
        mock_iam.create_user.assert_not_called()


class TestIAMProvisionerDeleteUser:
    """Test IAM user deletion"""

    @patch("edutools.iam.boto3.session.Session")
    def test_delete_user_success(self, mock_session):
        """Test successful user deletion"""
        mock_client = MagicMock()
        mock_session.return_value.client.return_value = mock_client
        mock_client.list_user_policies.return_value = {"PolicyNames": ["EC2OnlyAccess"]}
        mock_client.list_attached_user_policies.return_value = {"AttachedPolicies": []}

        provisioner = IAMProvisioner()
        result = provisioner.delete_user("testuser")

        assert result["username"] == "testuser"
        assert result["status"] == "deleted"
        assert result["error"] is None

        # Verify API calls
        mock_client.delete_login_profile.assert_called_once_with(UserName="testuser")
        mock_client.list_user_policies.assert_called_once_with(UserName="testuser")
        mock_client.delete_user_policy.assert_called_once_with(
            UserName="testuser", PolicyName="EC2OnlyAccess"
        )
        mock_client.delete_user.assert_called_once_with(UserName="testuser")

    @patch("edutools.iam.boto3.session.Session")
    def test_delete_user_not_found(self, mock_session):
        """Test handling when user doesn't exist"""
        mock_client = MagicMock()
        mock_session.return_value.client.return_value = mock_client

        error_response = {"Error": {"Code": "NoSuchEntity", "Message": "User not found"}}
        mock_client.delete_login_profile.side_effect = ClientError(error_response, "DeleteLoginProfile")
        mock_client.delete_user.side_effect = ClientError(error_response, "DeleteUser")

        provisioner = IAMProvisioner()
        result = provisioner.delete_user("nonexistent")

        assert result["username"] == "nonexistent"
        assert result["status"] == "skipped"
        assert result["error"] == "user not found"

    @patch("edutools.iam.boto3.session.Session")
    def test_delete_user_no_login_profile(self, mock_session):
        """Test deletion succeeds even if no login profile exists"""
        mock_client = MagicMock()
        mock_session.return_value.client.return_value = mock_client

        # Login profile doesn't exist
        error_response = {"Error": {"Code": "NoSuchEntity", "Message": "Login profile not found"}}
        mock_client.delete_login_profile.side_effect = ClientError(error_response, "DeleteLoginProfile")
        mock_client.list_user_policies.return_value = {"PolicyNames": []}
        mock_client.list_attached_user_policies.return_value = {"AttachedPolicies": []}

        provisioner = IAMProvisioner()
        result = provisioner.delete_user("testuser")

        assert result["status"] == "deleted"
        mock_client.delete_user.assert_called_once_with(UserName="testuser")

    @patch("edutools.iam.boto3.session.Session")
    def test_delete_user_with_attached_policies(self, mock_session):
        """Test deletion detaches managed policies"""
        mock_client = MagicMock()
        mock_session.return_value.client.return_value = mock_client
        mock_client.list_user_policies.return_value = {"PolicyNames": []}
        mock_client.list_attached_user_policies.return_value = {
            "AttachedPolicies": [
                {"PolicyName": "ReadOnlyAccess", "PolicyArn": "arn:aws:iam::aws:policy/ReadOnlyAccess"}
            ]
        }

        provisioner = IAMProvisioner()
        result = provisioner.delete_user("testuser")

        assert result["status"] == "deleted"
        mock_client.detach_user_policy.assert_called_once_with(
            UserName="testuser",
            PolicyArn="arn:aws:iam::aws:policy/ReadOnlyAccess"
        )

    @patch("edutools.iam.boto3.session.Session")
    def test_delete_user_api_error(self, mock_session):
        """Test handling of general API errors"""
        mock_client = MagicMock()
        mock_session.return_value.client.return_value = mock_client

        error_response = {"Error": {"Code": "AccessDenied", "Message": "Access denied"}}
        mock_client.delete_login_profile.side_effect = ClientError(error_response, "DeleteLoginProfile")

        provisioner = IAMProvisioner()
        result = provisioner.delete_user("testuser")

        assert result["username"] == "testuser"
        assert result["status"] == "error"
        assert "Access denied" in result["error"]


class TestDeprovisionStudents:
    """Test the deprovision_students workflow function"""

    @patch("edutools.iam.IAMProvisioner")
    @patch("edutools.iam.CanvasLMS")
    def test_deprovision_students_success(self, mock_canvas_cls, mock_iam_cls):
        """Test successful deprovisioning of multiple students"""
        mock_canvas = MagicMock()
        mock_canvas.get_students.return_value = [
            {"id": 1, "email": "jsmith@example.edu"},
            {"id": 2, "email": "mjones@example.edu"},
        ]
        mock_canvas_cls.return_value = mock_canvas

        mock_iam = MagicMock()
        mock_iam.delete_user.side_effect = [
            {"username": "jsmith", "status": "deleted", "error": None},
            {"username": "mjones", "status": "deleted", "error": None},
        ]
        mock_iam_cls.return_value = mock_iam

        with patch.dict(
            os.environ,
            {"CANVAS_ENDPOINT": "https://canvas.example.com/api/v1/courses", "CANVAS_TOKEN": "test_token"},
        ):
            results = deprovision_students("12345")

        assert len(results) == 2
        assert results[0]["email"] == "jsmith@example.edu"
        assert results[0]["username"] == "jsmith"
        assert results[0]["status"] == "deleted"
        assert results[1]["status"] == "deleted"

    @patch("edutools.iam.IAMProvisioner")
    @patch("edutools.iam.CanvasLMS")
    def test_deprovision_students_user_not_found(self, mock_canvas_cls, mock_iam_cls):
        """Test deprovisioning when user doesn't exist in IAM"""
        mock_canvas = MagicMock()
        mock_canvas.get_students.return_value = [
            {"id": 1, "email": "notiniam@example.edu"},
        ]
        mock_canvas_cls.return_value = mock_canvas

        mock_iam = MagicMock()
        mock_iam.delete_user.return_value = {
            "username": "notiniam",
            "status": "skipped",
            "error": "user not found",
        }
        mock_iam_cls.return_value = mock_iam

        with patch.dict(
            os.environ,
            {"CANVAS_ENDPOINT": "https://canvas.example.com/api/v1/courses", "CANVAS_TOKEN": "test_token"},
        ):
            results = deprovision_students("12345")

        assert len(results) == 1
        assert results[0]["status"] == "skipped"

    @patch("edutools.iam.IAMProvisioner")
    @patch("edutools.iam.CanvasLMS")
    def test_deprovision_students_no_email(self, mock_canvas_cls, mock_iam_cls):
        """Test handling of students without email addresses"""
        mock_canvas = MagicMock()
        mock_canvas.get_students.return_value = [
            {"id": 1},  # No email field
        ]
        mock_canvas_cls.return_value = mock_canvas

        mock_iam = MagicMock()
        mock_iam_cls.return_value = mock_iam

        with patch.dict(
            os.environ,
            {"CANVAS_ENDPOINT": "https://canvas.example.com/api/v1/courses", "CANVAS_TOKEN": "test_token"},
        ):
            results = deprovision_students("12345")

        assert len(results) == 1
        assert results[0]["status"] == "skipped"
        assert results[0]["error"] == "no email"
        mock_iam.delete_user.assert_not_called()

    @patch("edutools.iam.IAMProvisioner")
    @patch("edutools.iam.CanvasLMS")
    def test_deprovision_students_empty_course(self, mock_canvas_cls, mock_iam_cls):
        """Test deprovisioning for a course with no students"""
        mock_canvas = MagicMock()
        mock_canvas.get_students.return_value = []
        mock_canvas_cls.return_value = mock_canvas

        mock_iam = MagicMock()
        mock_iam_cls.return_value = mock_iam

        with patch.dict(
            os.environ,
            {"CANVAS_ENDPOINT": "https://canvas.example.com/api/v1/courses", "CANVAS_TOKEN": "test_token"},
        ):
            results = deprovision_students("12345")

        assert results == []
        mock_iam.delete_user.assert_not_called()
