import unittest
from unittest.mock import patch, MagicMock, mock_open
from cmt_main import ChatGptWindow
import os
import csv
import datetime
import pyperclip
import cmt_main
import tkinter as tk
from tkinter import ttk
import openai

class MockNotebook:
    def __init__(self):
        window = tk.Tk()
        results_notebook = ttk.Notebook(window)
        tab = ttk.Frame(results_notebook)
        results_notebook.add(tab, text="tab1")
        self.result = tk.Text(tab, background='#cccccc', selectbackground='#ffc266', wrap=tk.WORD)
        self.results_notebook = results_notebook
    
    def select(self):
        return 'tab1'
    
    def get_notebook(self):
        return self.results_notebook
    
    def insert_text(self, text):
        self.result.insert(tk.END, text)
        
class TestChatGptWindow(unittest.TestCase):
    @patch('cmt_main.tk.Tk')
    @patch('cmt_main.Files')
    @patch('cmt_main.set_logging')

    def setUp(self, mock_tk, mock_files, mock_set_logging):
        self.chat_gpt_window = ChatGptWindow()
        self.chat_gpt_window.progress_bar = MagicMock()
        self.chat_gpt_window.text_entry = MagicMock()
        self.chat_gpt_window.sound_effect = MagicMock()
        self.chat_gpt_window.create_window = MagicMock()
        self.chat_gpt_window.notebooks = [MagicMock()]
        self.chat_gpt_window.windows = []
        self.chat_gpt_window.data_dir = './'  # Set a test directory
        self.chat_gpt_window.resp_dir = './'   # Set a test directory
        self.chat_gpt_window.data_dir = './data/'

    def test_init(self):
        self.assertIsNotNone(self.chat_gpt_window.window)
        self.assertIsNotNone(self.chat_gpt_window.files)
        self.assertIsNotNone(self.chat_gpt_window.logger)        
        self.assertIsNotNone(self.chat_gpt_window.sound_effect)

    @patch('openai.chat.completions.create')
    def test_get_chatgpt_response(self, mock_create):
        # Arrange        
        mock_response = MagicMock()
        mock_response.message.content = 'mock response'
        mock_create.return_value.choices = [mock_response]        
        self.chat_gpt_window = ChatGptWindow()
        self.chat_gpt_window.progress_bar = MagicMock()
        self.chat_gpt_window.create_window = MagicMock()
        user_input_value = 'test input'
        prompt_value = 'test prompt'
        temperature_value = 0.5
        outputs_value = 1
        model = 'gpt-4o'
        self.chat_gpt_window.prompts = {'test': 'test prompt'}

        # Act
        response = self.chat_gpt_window.get_chatgpt_response(user_input_value, prompt_value, temperature_value, outputs_value, model)        

        # Assert        
        mock_create.assert_called_once_with(
            model='gpt-4o',
            messages=[
                {'role': 'system', 'content': prompt_value},
                {'role': 'user', 'content': ''},
                {'role': 'assistant', 'content': ''},
                {'role': 'user', 'content': user_input_value},
            ],
            n=outputs_value,
            stop=None,
            temperature=temperature_value
        )
        self.assertEqual(response[0].message.content, 'mock response')

    @patch('threading.Thread')
    def test_execute_submit(self, mock_thread):
        self.chat_gpt_window.create_all_widgets()
        # Set up mock objects
        mock_thread.return_value = MagicMock()

        # Call the method
        self.chat_gpt_window.execute_submit()

        # Check that the thread was created and started
        self.assertEqual(mock_thread.call_count, 2)
        self.assertEqual(mock_thread.return_value.start.call_count, 2)        

    def test_progress_bar(self):
        # Call the method
        self.chat_gpt_window.progress_bar()

        # Check that the progress bar was created
        self.assertIsNotNone(self.chat_gpt_window.progress_bar)

    @patch('openai.images.generate')
    def test_get_dalle_response_success(self, mock_generate):
        # Arrange
        user_input_value = "A beautiful landscape"
        outputs_value = 1
        model = "dall-e"
        mock_response = MagicMock()
        mock_response.data = [MagicMock(url="http://example.com/image1.png")]
        mock_generate.return_value = mock_response

        # Act
        self.chat_gpt_window.get_dalle_response(user_input_value, outputs_value, model)

        # Assert
        self.chat_gpt_window.progress_bar.start.assert_called_once_with(11)
        mock_generate.assert_any_call(model=model, prompt=user_input_value, n=outputs_value, size='1792x1024', quality="hd")
        mock_generate.assert_any_call(model=model, prompt=user_input_value, n=outputs_value, size='1024x1024', quality="hd")
        self.chat_gpt_window.create_window.assert_called_once()
        self.chat_gpt_window.progress_bar.stop.assert_called_once()

    @patch('openai.images.generate')
    def test_get_dalle_response_rate_limit_error(self, mock_generate):
        # Arrange
        user_input_value = "A beautiful landscape"
        outputs_value = 1
        model = "dall-e"
        response = MagicMock()
        mock_generate.side_effect = openai.RateLimitError("Rate limit exceeded", response=response, body='test')

        # Act
        self.chat_gpt_window.get_dalle_response(user_input_value, outputs_value, model)

        # Assert
        self.chat_gpt_window.text_entry.insert.assert_called_with(tk.END, 'Likely out of OpenAI tokens, error: Rate limit exceeded')
        self.assertEqual(self.chat_gpt_window.text_entry.insert.call_count, 2)

    @patch('time.sleep')
    def test_get_gemini_response_success(self, mock_sleep):
        # Arrange
        self.chat_gpt_window.chat.send_message = MagicMock()
        self.chat_gpt_window.to_csv = MagicMock()
        mock_response = MagicMock
        mock_response.text = "Gemini response text"
        self.chat_gpt_window.chat.send_message.return_value = mock_response        
        user_input_value = "Hello"
        prompt_value = "Greeting"
        temperature_value = 0.7
        outputs_value = 1
        
        # Act
        self.chat_gpt_window.get_gemini_response(user_input_value, prompt_value, temperature_value, outputs_value)

        # Assert
        self.chat_gpt_window.chat.send_message.assert_called_once()
        self.assertEqual(self.chat_gpt_window.gemini_response, "Gemini response text")

    def test_add_gemini_to_nb(self):
        # Arrange
        response = "This is a response"
        title = "Response Title"

        # Act
        self.chat_gpt_window.add_gemini_to_nb(response, title)

        # Assert
        self.assertEqual(len(self.chat_gpt_window.notebooks), 1)
        self.chat_gpt_window.notebooks[-1].add.assert_called_once()
        
    def test_temperature_dropdown_init(self):
        # Act
        self.chat_gpt_window.temperature_dropdown_init()

        # Assert
        temperature_label = self.chat_gpt_window.window.children['!label']  # Get the label
        self.assertEqual(temperature_label.cget("text"), "Temperature:")
        self.assertIsInstance(self.chat_gpt_window.temperature_dropdown, ttk.Combobox)
        self.assertEqual(self.chat_gpt_window.temperature_dropdown.get(), '0.3')  # Default value

    def test_num_outputs_dropdown(self):
        # Act
        self.chat_gpt_window.num_outputs_dropdown()

        # Assert
        outputs_label = self.chat_gpt_window.window.children['!label']  # Get the label
        self.assertEqual(outputs_label.cget("text"), "Number of Outputs:")
        self.assertIsInstance(self.chat_gpt_window.outputs_dropdown, ttk.Combobox)
        self.assertEqual(self.chat_gpt_window.outputs_dropdown.get(), '1')  # Default value

    def test_models_dropdown(self):
        # Act
        self.chat_gpt_window.models_dropdown()

        # Assert
        models_label = self.chat_gpt_window.window.children['!label']  # Get the label
        self.assertEqual(models_label.cget("text"), "OpenAI model:")
        self.assertIsInstance(self.chat_gpt_window.models_dropdown, ttk.Combobox)
        self.assertEqual(self.chat_gpt_window.models_dropdown.get(), 'gpt-4o-mini')  # Default value

    def test_prompts_dropdown(self):
        # Mock the prompts dictionary
        self.chat_gpt_window.prompts = {'Prompt 1': 'Description 1', 'Prompt 2': 'Description 2'}
        
        # Act
        self.chat_gpt_window.prompts_dropdown()

        # Assert
        prompts_label = self.chat_gpt_window.window.children['!label']  # Get the label
        self.assertEqual(prompts_label.cget("text"), "Prompt:")
        self.assertIsInstance(self.chat_gpt_window.prompts_dropdown, ttk.Combobox)
        self.assertEqual(self.chat_gpt_window.prompts_dropdown.get(), 'Prompt 1')  # Default value

    def test_user_input(self):
        # Act
        self.chat_gpt_window.user_input()

        # Assert for user input label
        user_input_label = self.chat_gpt_window.window.children['!label']  # Get the label
        self.assertEqual(user_input_label.cget("text"), "User Input:")

        # Assert for text entry widget
        self.assertIsInstance(self.chat_gpt_window.text_entry, tk.Text)
        self.assertEqual(self.chat_gpt_window.text_entry.cget("height"), 10)

        # Assert for user history widget
        self.assertIsInstance(self.chat_gpt_window.user_history, tk.Text)
        self.assertEqual(self.chat_gpt_window.user_history.cget("height"), 4)

    def test_results_notebook(self):
        self.chat_gpt_window.add_gemini_to_nb = MagicMock()
        self.chat_gpt_window.notebooks = list()
        # Mock parameters
        window_id = 0
        output_values = 2
        cgpt_response = ["Response 1", "Response 2"]
        prompt_key = "test_prompt"

        # Act
        self.chat_gpt_window.windows.append(tk.Toplevel(self.chat_gpt_window.window))  # Create a new window for the notebook
        self.chat_gpt_window.results_notebook(window_id, output_values, cgpt_response, prompt_key)

        # Assert for notebook creation
        self.assertEqual(len(self.chat_gpt_window.notebooks), 1)
        self.assertIsInstance(self.chat_gpt_window.notebooks[window_id], ttk.Notebook)

        # Assert for tab creation
        self.assertEqual(len(self.chat_gpt_window.notebooks[window_id].tabs()), 2)

    def test_submit_button(self):
        # Act
        self.chat_gpt_window.submit_button()

        # Assert for submit button creation
        submit_button = self.chat_gpt_window.window.children['!button']  # Get the button
        self.assertEqual(submit_button.cget("text"), "Submit")
        self.assertEqual(submit_button.cget("style"), 'TButton')

    def test_create_all_widgets(self):
        # Act
        self.chat_gpt_window.create_all_widgets()

        # Assert for the presence of all widgets
        self.assertIn('!combobox', self.chat_gpt_window.window.children)  # Check for prompts dropdown
        self.assertIn('!label', self.chat_gpt_window.window.children)  # Check for user input text
        self.assertIn('!button', self.chat_gpt_window.window.children)  # Check for submit button
        self.assertIn('!label2', self.chat_gpt_window.window.children)  # Check for submit button
        self.assertIn('!frame', self.chat_gpt_window.window.children)  # Check for submit button
        self.assertIn('!frame2', self.chat_gpt_window.window.children)  # Check for submit button
        self.assertIn('!label3', self.chat_gpt_window.window.children)  # Check for submit button
        self.assertIn('!combobox2', self.chat_gpt_window.window.children)  # Check for submit button
        self.assertIn('!label4', self.chat_gpt_window.window.children)  # Check for submit button
        self.assertIn('!combobox3', self.chat_gpt_window.window.children)  # Check for submit button
        self.assertIn('!label5', self.chat_gpt_window.window.children)  # Check for submit button
        self.assertIn('!combobox4', self.chat_gpt_window.window.children)  # Check for submit button
        self.assertIn('!progressbar', self.chat_gpt_window.window.children)  # Check for submit button
        
    @patch('builtins.open', new_callable=mock_open, read_data='header1,header2\nvalue1,value2\nvalue3,value4\n')
    def test_get_from_csv(self, mock_file):
        # Test valid CSV retrieval
        result = self.chat_gpt_window.get_from_csv('test_prompt')
        self.assertEqual(result, ['value3', 'value4'])
        mock_file.assert_called_once_with('./data/test_prompt.csv', 'r', encoding='utf-8')

    @patch('builtins.open', side_effect=FileNotFoundError)
    def test_get_from_csv_file_not_found(self, mock_file):
        # Test handling of FileNotFoundError
        result = self.chat_gpt_window.get_from_csv('non_existent_prompt')
        self.assertEqual(result, ['No history', 'No history'])

    @patch('builtins.open', new_callable=mock_open, read_data='')
    def test_get_from_csv_empty_row(self, mock_file):
        # Test CSV with only headers
        result = self.chat_gpt_window.get_from_csv('empty_prompt')
        self.assertEqual(result, ['No history', 'No history'])

    @patch('pyperclip.copy')
    def test_copy_to_clipboard(self, mock_copy):
        notebook_class = MockNotebook()
        notebook_class.insert_text("Sample text to copy")
        notebook = notebook_class.get_notebook()

        self.chat_gpt_window.notebooks.append(notebook)

        # Act
        self.chat_gpt_window.copy_to_clipboard(notebook)

        # Assert
        mock_copy.assert_called_once_with("Sample text to copy")

    @patch('pyperclip.copy')
    def test_code_copy(self, mock_copy):
        notebook_class = MockNotebook()
        notebook_class.insert_text("```PYTHON\nprint('Hello World')\n```")
        notebook = notebook_class.get_notebook()
        
        self.chat_gpt_window.notebooks.append(notebook)

        # Act
        self.chat_gpt_window.code_copy(notebook)

        # Assert
        mock_copy.assert_called_once_with("\nprint('Hello World')\n")

    @patch('builtins.open', new_callable=mock_open)
    @patch('os.path.exists')
    def test_to_csv(self, mock_exists, mock_file):
        self.chat_gpt_window.prompts = {'test_key': 'test_prompt',}
        user_input_value = 'User input'
        cgpt_response = [MagicMock(message=MagicMock(content='Response 1')),
                         MagicMock(message=MagicMock(content='Response 2'))]
        prompt_value = 'test_prompt'
        outputs_value = 2
        prompt_key = 'test_key'        
        
        mock_exists.return_value = False  # Simulate that the file does not exist

        self.chat_gpt_window.to_csv(user_input_value, cgpt_response, prompt_value, outputs_value)

        # Check that the file was created and written to
        mock_file.assert_called_once_with(f'./data/{prompt_key}.csv', 'w', encoding='utf-8')
        handle = mock_file()
        self.assertEqual(handle.write.call_count, 4)
        
if __name__ == '__main__':
    unittest.main()