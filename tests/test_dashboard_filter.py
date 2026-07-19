"""
Test suite for Dashboard Status Filter functionality
"""

import unittest
from unittest.mock import Mock, patch, MagicMock
from core.sheets_manager import SheetsManager


class TestDashboardFilter(unittest.TestCase):
    """Test cases for dashboard filtering functionality"""

    def setUp(self):
        """Set up test fixtures"""
        self.mock_creds = Mock()
        self.mock_service = Mock()
        self.mock_sheet = Mock()
        
    @patch('core.sheets_manager.Credentials')
    @patch('core.sheets_manager.build')
    def test_get_rows_by_status_success(self, mock_build, mock_creds):
        """Test fetching rows with a specific status"""
        # Setup mocks
        mock_build.return_value.spreadsheets.return_value = self.mock_sheet
        mock_creds.from_service_account_file.return_value = self.mock_creds
        
        # Create test data
        test_data = [
            ["Topic", "Keyword", "Category", "Status", "Blog URL", "Post ID", "Error Log"],
            ["Topic 1", "Keyword 1", "Category 1", "Success", "url1.com", "123", ""],
            ["Topic 2", "Keyword 2", "Category 2", "Failed", "url2.com", "124", "Error details"],
            ["Topic 3", "Keyword 3", "Category 3", "Success", "url3.com", "125", ""],
        ]
        
        self.mock_sheet.values.return_value.get.return_value.execute.return_value = {
            'values': test_data
        }
        
        # Initialize manager
        sheets = SheetsManager("test_sheet_id", "path/to/creds.json", "Sheet1")
        sheets.get_all_rows = Mock(return_value=test_data)
        
        # Test
        results = sheets.get_rows_by_status("Success")
        
        # Verify
        self.assertEqual(len(results), 3)  # Headers + 2 matching rows
        self.assertEqual(results[0], ["Topic", "Keyword", "Category", "Status", "Blog URL", "Post ID", "Error Log"])
        self.assertTrue(any("Topic 1" in row for row in results))
        self.assertTrue(any("Topic 3" in row for row in results))

    @patch('core.sheets_manager.Credentials')
    @patch('core.sheets_manager.build')
    def test_get_rows_by_status_no_matches(self, mock_build, mock_creds):
        """Test when no rows match the status filter"""
        mock_build.return_value.spreadsheets.return_value = self.mock_sheet
        mock_creds.from_service_account_file.return_value = self.mock_creds
        
        test_data = [
            ["Topic", "Keyword", "Category", "Status", "Blog URL", "Post ID", "Error Log"],
            ["Topic 1", "Keyword 1", "Category 1", "Success", "url1.com", "123", ""],
        ]
        
        sheets = SheetsManager("test_sheet_id", "path/to/creds.json", "Sheet1")
        sheets.get_all_rows = Mock(return_value=test_data)
        
        # Test
        results = sheets.get_rows_by_status("NonExistent")
        
        # Verify - should only have headers
        self.assertEqual(len(results), 1)

    @patch('core.sheets_manager.Credentials')
    @patch('core.sheets_manager.build')
    def test_get_status_summary(self, mock_build, mock_creds):
        """Test getting a summary of all statuses"""
        mock_build.return_value.spreadsheets.return_value = self.mock_sheet
        mock_creds.from_service_account_file.return_value = self.mock_creds
        
        test_data = [
            ["Topic", "Keyword", "Category", "Status"],
            ["Topic 1", "Keyword 1", "Category 1", "Success"],
            ["Topic 2", "Keyword 2", "Category 2", "Success"],
            ["Topic 3", "Keyword 3", "Category 3", "Failed"],
            ["Topic 4", "Keyword 4", "Category 4", "Pending"],
        ]
        
        sheets = SheetsManager("test_sheet_id", "path/to/creds.json", "Sheet1")
        sheets.get_all_rows = Mock(return_value=test_data)
        
        # Test
        summary = sheets.get_status_summary()
        
        # Verify
        self.assertEqual(summary["Success"], 2)
        self.assertEqual(summary["Failed"], 1)
        self.assertEqual(summary["Pending"], 1)
        self.assertEqual(len(summary), 3)

    @patch('core.sheets_manager.Credentials')
    @patch('core.sheets_manager.build')
    def test_display_rows_by_status(self, mock_build, mock_creds):
        """Test the convenience method that both fetches and updates"""
        mock_build.return_value.spreadsheets.return_value = self.mock_sheet
        mock_creds.from_service_account_file.return_value = self.mock_creds
        
        test_data = [
            ["Topic", "Keyword", "Category", "Status", "Blog URL", "Post ID", "Error Log"],
            ["Topic 1", "Keyword 1", "Category 1", "Success", "url1.com", "123", ""],
            ["Topic 2", "Keyword 2", "Category 2", "Failed", "url2.com", "124", "Error"],
        ]
        
        sheets = SheetsManager("test_sheet_id", "path/to/creds.json", "Sheet1")
        sheets.get_all_rows = Mock(return_value=test_data)
        sheets.get_rows_by_status = Mock(return_value=test_data)
        sheets.update_dashboard_filtered_results = Mock()
        
        # Test
        results = sheets.display_rows_by_status("Success")
        
        # Verify
        sheets.get_rows_by_status.assert_called_once_with("Success")
        sheets.update_dashboard_filtered_results.assert_called_once_with("Success")
        self.assertEqual(len(results), 2)

    @patch('core.sheets_manager.Credentials')
    @patch('core.sheets_manager.build')
    def test_status_filter_case_insensitive(self, mock_build, mock_creds):
        """Test that status filtering is case-insensitive"""
        mock_build.return_value.spreadsheets.return_value = self.mock_sheet
        mock_creds.from_service_account_file.return_value = self.mock_creds
        
        test_data = [
            ["Topic", "Keyword", "Category", "Status"],
            ["Topic 1", "Keyword 1", "Category 1", "Success"],
            ["Topic 2", "Keyword 2", "Category 2", "SUCCESS"],
            ["Topic 3", "Keyword 3", "Category 3", "PENDING"],
        ]
        
        sheets = SheetsManager("test_sheet_id", "path/to/creds.json", "Sheet1")
        sheets.get_all_rows = Mock(return_value=test_data)
        
        # Test - search for lowercase
        results = sheets.get_rows_by_status("success")
        
        # Verify - should find both "Success" and "SUCCESS"
        self.assertEqual(len(results), 3)  # Headers + 2 matching rows


if __name__ == '__main__':
    unittest.main()
