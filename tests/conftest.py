"""Pytest configuration for RemoteProstor tests."""

import pytest
import sys
import os
from unittest.mock import Mock, MagicMock

# Add project root to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

# Configure logging for tests
import logging
logging.basicConfig(level=logging.WARNING)

# Mock external dependencies for tests
@pytest.fixture(autouse=True)
def mock_external_services(monkeypatch):
    """Mock external API calls for unit tests."""
    # Mock Deepseek client
    import core.deepseek_client
    mock_client = Mock()
    mock_client.chat.completions.create.return_value = MagicMock(
        choices=[MagicMock(message=MagicMock(content='{"test": "response"}'))]
    )
    monkeypatch.setattr(core.deepseek_client, 'DeepseekHttpClient', lambda *a, **kw: mock_client)
    
    # Mock requests for scraper
    import requests
    mock_response = Mock()
    mock_response.text = "<html></html>"
    mock_response.raise_for_status = Mock()
    monkeypatch.setattr(requests, 'get', Mock(return_value=mock_response))
    
    # Mock Google API clients
    monkeypatch.setattr('googleapiclient.discovery.build', Mock())
    monkeypatch.setattr('google.oauth2.service_account.Credentials.from_service_account_file', Mock())
    monkeypatch.setattr('google.oauth2.service_account.Credentials.from_service_account_info', Mock())
    monkeypatch.setattr('google.oauth2.credentials.Credentials', Mock())
    
    # Mock PIL Image operations
    from PIL import Image
    def mock_open(*args, **kwargs):
        img = Mock(spec=Image.Image)
        img.size = (800, 600)
        img.mode = 'RGB'
        img.convert = Mock(return_value=img)
        img.filter = Mock(return_value=img)
        img.resize = Mock(return_value=img)
        img.save = Mock()
        return img
    monkeypatch.setattr(Image, 'open', mock_open)
    
    # Mock slugify
    import slugify
    monkeypatch.setattr(slugify, 'slugify', lambda x: x.lower().replace(' ', '-'))

# Import pytest here to ensure fixtures work
import pytest