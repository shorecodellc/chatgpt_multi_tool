#test_cmt_main.py
#kevin fink
#January 30 2024
#kevin@shorecode.org

import unittest
from unittest.mock import patch, MagicMock
from dataclasses import dataclass
import tkinter as tk
from tkinter import ttk
import ttkthemes
import openai
import os
import logging
import sys
from cmt_main import ChatGptWindow
from cmt_filepaths import Files

sys.path.append('../src')

@dataclass
class MockFiles:
    def get_files_list(self):
        return ['/mock/path']

class TestChatGptWindow(unittest.TestCase):


    @patch('tkinter.Tk')
    @patch('ttkthemes.ThemedStyle')
    @patch('os.getenv')
    @patch('tkinter.ttk.Style')
    @patch('cmt_logging.set_logging')
    def test_init(self, mock_set_logging, mock_style, mock_getenv, mock_themed_style, mock_tk):
        mock_getenv.return_value = 'mock_key'
        mock_set_logging.return_value = logging.getLogger('mock_logger')    
        with patch('cmt_filepaths.Files', new=MockFiles):
            self.chat_window = ChatGptWindow()
            self.assertEqual(self.chat_window.files.get_files_list(), ['/mock/path'])
            self.assertEqual(self.chat_window.data_dir, '/mock/path')
            self.assertEqual(self.chat_window.open_ai_key, 'mock_key')
            mock_tk.assert_called_once()
            mock_themed_style.assert_called_once_with(mock_tk())
            mock_set_logging.assert_called_once_with('cmt', 'cmt.log')

    def test_execute_submit(self):
        # Mock the necessary dependencies
        self.chat_window = ChatGptWindow()
        self.chat_window.logger = MagicMock()
        self.chat_window.temperature_dropdown = MagicMock()
        self.chat_window.temperature_dropdown.get.return_value = "0.8"
        self.chat_window.outputs_dropdown = MagicMock()
        self.chat_window.outputs_dropdown.get.return_value = "5"
        self.chat_window.user_input = MagicMock()
        self.chat_window.user_input.get.return_value = "Hello"
        self.chat_window.user_history = MagicMock()
        self.chat_window.prompts_dropdown = MagicMock()
        self.chat_window.prompts_dropdown.get.return_value = "Prompt 1"
        self.chat_window.get_chatgpt_response = MagicMock()

        # Call the method
        self.chat_window.execute_submit()

        # Assert that the necessary methods were called
        self.chat_window.logger.info.assert_called_with('Sending request to ChatGPT')
        self.chat_window.temperature_dropdown.get.assert_called_once()
        self.chat_window.outputs_dropdown.get.assert_called_once()
        self.chat_window.user_input.get.assert_called_with("1.0", tk.END)
        self.chat_window.user_input.delete.assert_called_with("1.0", tk.END)
        self.chat_window.user_history.delete.assert_called_with("1.0", tk.END)
        self.chat_window.user_history.insert.assert_called_with(tk.END, "Hello")
        self.chat_window.prompts_dropdown.get.assert_called_once()
        self.chat_window.get_chatgpt_response.assert_called_with("Hello", "Prompt 1", 0.8, 5)

    def test_get_chatgpt_response(self):
        self.chat_window = ChatGptWindow()
        # Mock the necessary dependencies
        self.chat_window.logger = MagicMock()
        self.chat_window.models_dropdown = MagicMock()
        self.chat_window.models_dropdown.get.return_value = "davinci"
        self.chat_window.message_history = {"Prompt 1": ["Assistant 1"]}
        self.chat_window.prompts = ["Prompt 1"]
        self.chat_window.to_csv = MagicMock()
        self.chat_window.create_window = MagicMock()
        openai.completions.create = MagicMock()
        openai.chat.completions.create = MagicMock()

        # Call the method
        self.chat_window.get_chatgpt_response("Hello", "Prompt 1", 0.8, 5)

        # Assert that the necessary methods were called
        self.chat_window.models_dropdown.get.assert_called_once()
        self.chat_window.to_csv.assert_called_with("Hello", openai.completions.create().choices, 0, 5)
        self.chat_window.create_window.assert_called_with(5, openai.completions.create().choices)

if __name__ == '__main__':
    unittest.main()