import unittest
from unittest.mock import Mock, patch
from core.deepseek_client import DeepseekHttpClient, DeepseekResponse


class DeepseekClientTests(unittest.TestCase):
    def test_chat_completions_create_parses_response(self):
        client = DeepseekHttpClient(api_key="test-key")
        fake_response = Mock()
        fake_response.raise_for_status = Mock()
        fake_response.json.return_value = {
            "choices": [
                {"message": {"content": "Hello from Deepseek"}}
            ]
        }

        with patch.object(client.session, "post", return_value=fake_response) as mock_post:
            response = client.chat.completions.create(
                model="deepseek-v4-flash",
                messages=[{"role": "user", "content": "Write a short greeting."}],
                temperature=0.5,
            )

        mock_post.assert_called_once()
        self.assertEqual(response.choices[0].message.content, "Hello from Deepseek")
        self.assertEqual(response.raw["choices"][0]["message"]["content"], "Hello from Deepseek")

    def test_image_generate_parses_response(self):
        client = DeepseekHttpClient(api_key="test-key")
        fake_response = Mock()
        fake_response.raise_for_status = Mock()
        fake_response.json.return_value = {
            "data": [
                {"url": "https://example.com/image.png"}
            ]
        }

        with patch.object(client.session, "post", return_value=fake_response) as mock_post:
            response = client.images.generate(
                model="deepseek-v4-flash",
                prompt="A sample image",
                size="1024x1024",
                quality="standard",
                n=1,
            )

        mock_post.assert_called_once()
        self.assertEqual(response.data[0].url, "https://example.com/image.png")

    def test_to_response_handles_plain_string(self):
        response = DeepseekResponse("simple text")
        self.assertEqual(response.choices[0].message.content, "simple text")

    def test_client_to_response_handles_plain_string(self):
        client = DeepseekHttpClient(api_key="test-key")
        response = client._to_response("simple text")
        self.assertEqual(response.choices[0].message.content, "simple text")


if __name__ == "__main__":
    unittest.main()
