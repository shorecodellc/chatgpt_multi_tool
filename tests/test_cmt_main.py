import unittest
from unittest.mock import patch, MagicMock
from cmt_main import ChatGptWindow
import openai

class TestChatGptWindow(unittest.TestCase):
    @patch('cmt_main.tk.Tk')
    @patch('cmt_main.Files')
    @patch('cmt_main.set_logging')

    def setUp(self, mock_tk, mock_files, mock_set_logging):
        self.chat_gpt_window = ChatGptWindow()

    def test_init(self):
        self.assertIsNotNone(self.chat_gpt_window.window)
        self.assertIsNotNone(self.chat_gpt_window.files)
        self.assertIsNotNone(self.chat_gpt_window.logger)

    @patch('openai.ChatCompletion.create')
    def test_get_chatgpt_response(self, mock_create):
        # Arrange
        mock_create.return_value = 'mock response'
        window = ChatGptWindow()
        user_input_value = 'test input'
        prompt_value = 'test prompt'
        temperature_value = 0.5
        outputs_value = 1

        # Act
        response = window.get_chatgpt_response(user_input_value, prompt_value, temperature_value, outputs_value)

        # Assert
        mock_create.assert_called_once_with(
            model='gpt',
            messages=[
                {'role': 'system', 'content': prompt_value},
                {'role': 'user', 'content': user_input_value},
                {'role': 'assistant', 'content': window.message_history[prompt_key][-1]}
            ],
            n=outputs_value,
            stop=None,
            temperature=temperature_value
        )
        self.assertEqual(response, 'mock response')

    @patch('threading.Thread')
    def test_execute_submit(self, mock_thread):
        # Set up mock objects
        mock_thread.return_value = MagicMock()

        # Call the method
        self.chat_gpt_window.execute_submit()

        # Check that the thread was created and started
        mock_thread.assert_called_once()
        mock_thread.return_value.start.assert_called_once()

    def test_progress_bar(self):
        # Call the method
        self.chat_gpt_window.progress_bar()

        # Check that the progress bar was created
        self.assertIsNotNone(self.chat_gpt_window.progress_bar)

if __name__ == '__main__':
    unittest.main()