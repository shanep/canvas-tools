import unittest
from unittest.mock import patch, MagicMock
from dotenv import load_dotenv
from edu_tools.google import create_document, share_document, create_and_share

load_dotenv()

class TestGoogleDocs(unittest.TestCase):

    @patch('edu_tools.google.build')
    @patch('edu_tools.google._load_credentials')
    def test_create_document(self, mock_load_credentials, mock_build):
        # Test creating a document with a mock title
        mock_doc = {'documentId': 'mock_doc_id'}
        mock_service = MagicMock()
        mock_service.documents().create().execute.return_value = mock_doc
        mock_build.return_value = mock_service

        title = "Test Document"
        document_id = create_document(title)
        self.assertEqual(document_id, 'mock_doc_id')

    @patch('edu_tools.google.build')
    @patch('edu_tools.google._load_credentials')
    def test_share_document(self, mock_load_credentials, mock_build):
        # Test sharing a document with a mock email
        mock_perm = {'id': 'mock_perm_id'}
        mock_drive = MagicMock()
        mock_drive.permissions().create().execute.return_value = mock_perm
        mock_build.return_value = mock_drive

        document_id = "mock_document_id"
        email = "test@example.com"
        permission_id = share_document(document_id, email)
        self.assertEqual(permission_id, 'mock_perm_id')

    @patch('edu_tools.google.share_document')
    @patch('edu_tools.google.create_document', return_value='mock_doc_id')
    def test_create_and_share(self, mock_create_document, mock_share_document):
        # Test creating and sharing a document
        title = "Test Document"
        email = "test@example.com"
        document_id = create_and_share(title, email)
        self.assertEqual(document_id, 'mock_doc_id')
        mock_create_document.assert_called_once_with(title, None)
        mock_share_document.assert_called_once_with('mock_doc_id', email, role='writer', credentials_path=None, notify=False)