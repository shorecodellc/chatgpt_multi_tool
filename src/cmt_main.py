#cmt_main.py
#kevin fink
#January 30 2024
#kevin@shorecode.org

#todo:
#unit tests
#readme

import time
import pygame
import datetime
import threading
from pprint import pprint
import os
import yaml
import csv
import google.generativeai as genai
import tkinter as tk
from tkinter import ttk
from dataclasses import dataclass
import pyperclip
import openai
from valdec.decorators import validate
from cmt_logging import set_logging
from cmt_filepaths import Files

@dataclass
class ChatGptWindow:
    """
    A GUI application for interacting with OpenAI's ChatGPT models.

    Attributes:
        files (Files): An instance of the Files class to get file paths.
        filepaths (list): A list of file paths for data directory, response directory, theme, prompts, and icon.
        data_dir (str): The directory path for storing data.
        resp_dir (str): The directory path for storing responses.
        theme_fp (str): The file path for the GUI theme.
        prompts_fp (str): The file path for prompts.
        icon_fp (str): The file path for the window icon.
        window (tk.Tk): The main application window.
        prompts (dict): A dictionary of prompts loaded from the prompts file.
        message_history (dict): A dictionary to store message history for each prompt.
        windows (list): A list to store references to additional windows.
        notebooks (list): A list to store references to ttk.Notebook widgets.
        open_ai_key (str): The OpenAI API key.
        logger (Logger): A logger instance for logging information.
    """    
    # Gets the list of filepaths from the filepaths.py file
    files = Files()
    filepaths = files.get_files_list()
    # data/output directory
    data_dir = filepaths[0]
    # saved responses directory
    resp_dir = filepaths[1]
    # radiance theme fp
    theme_fp = filepaths[2]
    # prompts yaml fp
    prompts_fp = filepaths[3]
    # icon fp
    icon_fp = filepaths[4]
    sound_fp = filepaths[6]
    

    logger = set_logging('cmt', 'cmt.log')
    # Init main window and theme it
    window = tk.Tk()
    window.title('ChatGPT Multi Tool')
    window.iconphoto(True, tk.PhotoImage(file=filepaths[4]))
    window.configure(bg='#262626')
    window.geometry("800x655")  # Set width as 800 pixels and height as 655 pixels

    # Add radiance style to list of themes
    window.call('source', filepaths[2])
    # Apply the style to the window
    style = ttk.Style(window)
    style.theme_use('radiance')
    # TLabel is ttk.Label
    style.configure('TLabel', background = '#262626', foreground='#f2f2f2')
    # TButton is ttk.Button
    style.map("TButton", relief=[('pressed', '!disabled', 'sunken'),('active', 'raised')])
    style.configure('TNotebook', background='#262626')

    pygame.mixer.init()
    sound_effect = pygame.mixer.Sound(sound_fp)
    
    gemini_response = str()

    # Sets prompts
    with open(prompts_fp, 'r', encoding='utf-8') as fn:
        prompts = yaml.safe_load(fn)
    # Prepares the message history dict
    message_history = dict()
    for p in prompts.keys():
        message_history[p] = {'user': [], 'assistant': []}
    # Initializes lists for results windows and notebooks
    windows = []
    notebooks = []
    # Sets OpenAI key
    open_ai_key = os.getenv('OPENAI_API_KEY')
    
    gem_model = genai.GenerativeModel('gemini-pro')
    chat = gem_model.start_chat(history=[])

    @validate
    def execute_submit(self):
        """
        Handles the submit action, sending the user input and selected options to ChatGPT and displaying the response.
        """ 
        # Gets temperature values from the combobox
        temperature_value = self.temperature_dropdown.get()
        # Gets number of responses to request from combobox
        outputs_value = self.outputs_dropdown.get()
        # Gets user's text input
        user_input_value = self.text_entry.get("1.0", tk.END)
        # Deletes the contents of hte user entry text box
        self.text_entry.delete("1.0", tk.END)
        # Deletes old contents and adds the recent prompt to the history box
        self.user_history.config(state='normal')
        self.user_history.delete("1.0", tk.END)
        self.user_history.insert(tk.END, user_input_value)
        self.user_history.config(state='disabled')
        # Gets the prompt to use from the combobox
        prompt_choice = self.prompts_dropdown.get()
        prompt_value = self.prompts[prompt_choice]
        model = self.models_dropdown.get()
        if model == 'dall-e-3':
            self.logger.info('Sending request to Dalle')
            dalle_thread = threading.Thread(target=lambda: self.get_dalle_response(user_input_value,
                        int(outputs_value), model))
            dalle_thread.start()
        else:
            self.logger.info(f'Sending request to {model} and Gemini')
            # Retrieves the response from ChatGPT
            cgpt_thread = threading.Thread(target=lambda: self.get_chatgpt_response(user_input_value,
                            prompt_value, float(temperature_value), int(outputs_value), model))
            gemini_thread = threading.Thread(target=lambda: self.get_gemini_response(user_input_value,
                            prompt_value, float(temperature_value), int(outputs_value)))
            gemini_thread.start()
            cgpt_thread.start()
    
    def keypad_execute(self, event):
        self.execute_submit()
        return 'break'
    
    def get_dalle_response(self, user_input_value, outputs_value, model):
        self.progress_bar.start(11)  # Start the progress bar animation
        sizes = ['1792x1024', '1024x1024'] 
        responses = list()
        for size in sizes:
            try:
                response = openai.images.generate(
                    model=model,
                    prompt=user_input_value,
                    n=outputs_value,
                    size=size,
                    quality="hd"
                )        
                responses.append(response)
            except openai.RateLimitError as e:
                self.text_entry.insert(tk.END, f'Likely out of OpenAI tokens, error: {e}')
            except openai.AuthenticationError as e:
                self.text_entry.insert(tk.END, f'Failed auth, error: {e}')
            except Exception as e:
                self.create_window(int(outputs_value), e, 'Dalle Error')
        # Play the sound
        self.sound_effect.play()
        # Creates a window to display the results
        result1 = [r.data[0].url for r in responses]
        result = ['\n\n'.join(result1)]
        self.progress_bar.stop()  # Stop the progress bar animation
        self.create_window(int(outputs_value), result, 'Dalle')

    def get_gemini_response(self, user_input_value, prompt_value, temperature_value, outputs_value):
        try:            
            window_count = len(self.windows)
            response = self.chat.send_message(f'[Persona for gemini: {prompt_value}], [User text: {user_input_value}]', 
                    generation_config=genai.types.GenerationConfig(candidate_count=outputs_value, temperature=temperature_value))
            self.to_csv(user_input_value, [response.text], prompt_value, int(outputs_value))
            i = 0
            while window_count == len(self.windows):
                time.sleep(3)
                i += 1
                if i > 40:
                    break
            self.gemini_response = response.text
        except:            
            pass

    def add_gemini_to_nb(self, response, title):
        try:
            tab = ttk.Frame(self.notebooks[-1])
            self.notebooks[-1].add(tab, text=title)
            result = tk.Text(tab, background='#cccccc', selectbackground='#ffc266', wrap=tk.WORD)
            result.bind("<Control-Key-a>", lambda event: self.select_all(event, result))
            # Create a Scrollbar widget
            scrollbar = ttk.Scrollbar(tab, command=result.yview, orient='vertical')
            scrollbar.grid(column=5, row=0, sticky='ns')
            result.grid(column=0, row =0, columnspan=5)
            result.configure(yscrollcommand=scrollbar.set)
            result.insert(tk.END, response)
        except IndexError as e:
            pass

    @validate
    def get_chatgpt_response(self, user_input_value: str, prompt_value: str,
                                temperature_value: float, outputs_value: int, model: str) -> list:
        """
        Sends a request to ChatGPT based on the user's input and selected options, and handles the response.

        Parameters:
            user_input_value (str): The user's input text.
            prompt_value (str): The selected prompt.
            temperature_value (float): The temperature setting for the response generation.
            outputs_value (int): The number of responses to generate.
        """        
        start_time = time.time()

        # Gets the prompt key
        prompt_key = str()
        for k, v in self.prompts.items():
            if prompt_value == v:
                prompt_key = k        
        # Gets the last prompt sent for the category of prompts
        try:
            user_message = f"{self.message_history[prompt_key]['user'][-1]}"
            assistant_message = f"{self.message_history[prompt_key]['assistant'][-1]}"
        except IndexError as e:            
            user_message = self.get_from_csv(prompt_key)[0].replace("\n", " ")
            assistant_message = self.get_from_csv(prompt_key)[1].replace("\n", " ")
        except KeyError:
            user_message = str()
            assistant_message = str()

        self.progress_bar.start(11)  # Start the progress bar animation
        try:
            response = openai.chat.completions.create(
                model=model,
                messages=[{'role': 'system', 'content': prompt_value},
                {'role': 'user', 'content': user_message},
                {'role': 'assistant', 'content': assistant_message},
                {'role': 'user', 'content': user_input_value}],
                n=outputs_value,
                stop=None,
                temperature=temperature_value
            )
    
            end_time = time.time()
            elapsed_time = end_time - start_time
            self.logger.info(f'OpenAI `{model}` took {elapsed_time//60} minutes\
and {elapsed_time % 60} seconds to respond')
    
            try:                
                # Adds the prompt to the history
                self.message_history[prompt_key]['user'].append(user_input_value)
        
                # Adds the response and prompt to csv
                self.to_csv(user_input_value, response.choices, 
                            prompt_value, int(outputs_value))
            except:
                pass
        
            # Play the sound
            self.sound_effect.play()
            result = [r.message.content.strip() for r in response.choices]
            # Creates a window to display the results
            self.create_window(int(outputs_value), result, prompt_key)
            self.progress_bar.stop()  # Stop the progress bar animation
            return response.choices
        
        except openai.RateLimitError as e:
            self.text_entry.insert(tk.END, f'Likely out of OpenAI tokens, error: {e}')
        except openai.AuthenticationError as e:
            self.text_entry.insert(tk.END, f'Failed auth, error: {e}')

    @validate
    def progress_bar_init(self):
        """
        Initializes and displays a progress bar widget.
        """        
        # Create a progress bar widget
        self.progress_bar = ttk.Progressbar(self.window, orient='horizontal', 
                                       length=300, mode='indeterminate')
        self.progress_bar.pack(pady=10)

    @validate
    def temperature_dropdown(self):
        """
        Creates and displays a dropdown widget for selecting the temperature setting.
        """    
        # Dropdown selection for temperature
        temperature_label = ttk.Label(self.window, text="Temperature:")
        temperature_label.pack(pady=3)
        temperature_values = [i/10 for i in range(1, 11)]
        self.temperature_dropdown = ttk.Combobox(self.window, values=temperature_values,
                    width=3, state='readonly')
        # Sets the default value
        self.temperature_dropdown.set(temperature_values[2])
        self.temperature_dropdown.pack(pady=3)

    @validate
    def num_outputs_dropdown(self):
        """
        Creates and displays a dropdown widget for selecting the number of outputs.
        """        
        # Dropdown selection for number of outputs
        outputs_label = ttk.Label(self.window, text="Number of Outputs:")
        outputs_label.pack(pady=3)
        outputs_values = [i for i in range(1, 6)]
        self.outputs_dropdown = ttk.Combobox(self.window, values=outputs_values, width=3,
                                state='readonly')
        # Sets the default value
        self.outputs_dropdown.set(outputs_values[0])
        self.outputs_dropdown.pack(pady=3)

    @validate
    def models_dropdown(self):
        """
         Creates and displays a dropdown widget for selecting the OpenAI model.
         """        
        # Dropdown selection for OpenAI model
        models_label = ttk.Label(self.window, text="OpenAI model:")
        models_label.pack(pady=3)
        models_values = ['gpt-4o-mini', 'o1-mini-2024-09-12', 'gpt-4o', 'gpt-4-turbo-preview', 'dall-e-3']
        self.models_dropdown = ttk.Combobox(self.window, values=models_values, width=15, 
                                            state='readonly')
        # Sets the default value
        self.models_dropdown.set(models_values[0])
        self.models_dropdown.pack(pady=3)

    @validate
    def prompts_dropdown(self):
        """
        Creates and displays a dropdown widget for selecting a prompt.
        """        
        # Dropdown selection for number of outputs
        prompts_label = ttk.Label(self.window, text="Prompt:")
        prompts_label.pack(pady=5)
        self.prompts_dropdown = ttk.Combobox(self.window, 
                values=list(self.prompts.keys()), width=70, state='readonly', height=len(self.prompts.keys()))
        # Sets the default value
        self.prompts_dropdown.set(list(self.prompts.keys())[0])
        self.prompts_dropdown.pack(pady=3)

    @validate
    def user_input(self):
        """
         Creates and displays a text input widget for the user's input.
         """        
        # User input box
        user_input_label = ttk.Label(self.window, text="User Input:")
        user_input_label.pack(pady=3)
        # Creates a frame to enable the scrollbar to be attached
        # to the text entry widget
        frame = ttk.Frame(self.window)
        frame.pack()
        self.text_entry = tk.Text(frame, height =10, wrap=tk.WORD)
        # Create a Scrollbar widget
        scrollbar = ttk.Scrollbar(frame, command=self.text_entry.yview)
        scrollbar.pack(side=tk.RIGHT, fill='y')
        self.text_entry.pack(ipadx=100, pady=5)
        
        self.text_entry.bind("<Control-Key-a>", lambda event: self.select_all(event, self.text_entry))
        self.text_entry.bind("<KP_Enter>", self.keypad_execute)
        # Enable undo on the text widget
        self.text_entry.config(undo=True)    
        # Bind Ctrl+Z to the undo operation
        self.text_entry.bind('<Control-z>', lambda event: text_widget.edit_undo())    
        # Optional: Bind Ctrl+Shift+Z or Ctrl+Y to redo operation
        self.text_entry.bind('<Control-y>', lambda event: text_widget.edit_redo())
        
        # Configure the Text widget to use the Scrollbar
        self.text_entry.configure(yscrollcommand=scrollbar.set)

        # Creates a frame to enable the scrollbar to be attached
        # to the text entry widget
        frame_2 = ttk.Frame(self.window)
        frame_2.pack()
        self.user_history = tk.Text(frame_2, height=4, state='disabled', wrap=tk.WORD)
        # Create a Scrollbar widget
        scrollbar_2 = ttk.Scrollbar(frame_2, command=self.user_history.yview)
        scrollbar_2.pack(side=tk.RIGHT, fill='y')        
        self.user_history.pack(ipadx=100, pady=5)
        self.user_history.configure(yscrollcommand=scrollbar_2.set)
        self.user_history.bind("<Control-Key-a>", lambda event: self.select_all(event, self.user_history))

    @validate
    def results_notebook(self, window_id: int, output_values: int,
                         cgpt_response: list, prompt_key: str):
        """
        Creates a notebook widget in a new window to display the ChatGPT response(s).

        Parameters:
            window_id (int): The index of the new window in the windows list.
            output_values (int): The number of responses to display.
            cgpt_response (list): The list of responses from ChatGPT.
        """        
        # Notebook with 5 tabs
        # Pops up after submitting the request
        results_notebook = ttk.Notebook(self.windows[window_id])
        results_notebook.pack(pady=3)
        self.notebooks.append(results_notebook)
        # Creates the save button to save the selected tab
        save_button = ttk.Button(self.windows[window_id], text="Save",
                                 command=lambda: self.save_to_txt(results_notebook))
        save_button.pack(fill='x')
        # Create a separator widget
        separator = ttk.Separator(self.windows[window_id], orient='horizontal')
        separator.pack(fill='x', pady=1)
        # Create a button to copy the text to the clipboard
        copy_button = ttk.Button(self.windows[window_id], text="Copy",
                                 command=lambda: self.copy_to_clipboard(results_notebook))
        copy_button.pack(fill='x')
        separator2 = ttk.Separator(self.windows[window_id], orient='horizontal')
        separator2.pack(fill='x', pady=1)        
        copy_code = ttk.Button(self.windows[window_id], text='Copy Code', command=lambda: self.code_copy(results_notebook))
        copy_code.pack(fill='x')
        try:
            self.message_history[prompt_key]['assistant'].append(cgpt_response[0])
        except:
            pass
        
        for i in range(output_values):
            # Adds a frame to the notebook tabs
            tab = ttk.Frame(self.notebooks[window_id])
            self.notebooks[window_id].add(tab, text="Choice " + str(i+1))
            # Adds a text box to the frame in the tab
            result = tk.Text(tab, background='#cccccc', selectbackground='#ffc266', wrap=tk.WORD)
            result.bind("<Control-Key-a>", lambda event: self.select_all(event, result))
            # Enable undo on the text widget
            result.config(undo=True)        
            # Bind Ctrl+Z to the undo operation
            result.bind('<Control-z>', lambda event: text_widget.edit_undo())        
            # Optional: Bind Ctrl+Shift+Z or Ctrl+Y to redo operation
            result.bind('<Control-y>', lambda event: text_widget.edit_redo())            
            # Create a Scrollbar widget
            scrollbar = ttk.Scrollbar(tab, command=result.yview, orient='vertical')
            scrollbar.grid(column=5, row=0, sticky='ns')
            result.grid(column=0, row =0, columnspan=5)
            result.configure(yscrollcommand=scrollbar.set)
            # Gets the response content, the exception is for davinci
            # responses
            try:
                response = cgpt_response[i]
            except AttributeError as e:
                response = cgpt_response[i]
            result.insert(tk.END, response)
        self.add_gemini_to_nb(self.gemini_response, 'Gemini')

    @validate
    def submit_button(self):
        """
         Creates and displays a submit button.
         """        
        # Submit button
        submit_button = ttk.Button(self.window, text="Submit", command=self.execute_submit, style='TButton')
        submit_button.pack(pady=8)

    @validate
    def create_all_widgets(self):
        """
        Calls methods to create and display all widgets in the main application window.
        """        
        self.prompts_dropdown()
        self.user_input()
        self.temperature_dropdown()
        self.num_outputs_dropdown()
        self.models_dropdown()
        self.progress_bar_init()
        self.submit_button()

    @validate
    def create_window(self, output_values: int, 
                      cgpt_response: list, prompt_key):
        """
        Creates a new window to display the ChatGPT response(s).

        Parameters:
            output_values (int): The number of responses to display.
            cgpt_response (list): The list of responses from ChatGPT.
        """        
        # Create a new window
        new_window = tk.Toplevel(self.window)
        style = ttk.Style(new_window)
        style.map("TButton", relief=[('pressed', '!disabled', 'sunken'),('active', 'groove')])
        new_window.configure(bg='#262626')
        new_window.geometry('670x565')
        # Add the window to the list
        self.windows.append(new_window)
        new_window.title(f"{prompt_key} Results #{len(self.windows)}")
        # Creates a notebook using an index of the amount of windows
        # created to get the last window in the list
        self.results_notebook(len(self.windows)-1, output_values, cgpt_response, prompt_key)

    @validate
    def to_csv(self, user_input_value: str, cgpt_response: list, 
               prompt_value: str, outputs_value: int):
        """
        Saves the user input and ChatGPT response(s) to a CSV file.

        Parameters:
            user_input_value (str): The user's input text.
            cgpt_response (list): The list of responses from ChatGPT.
            prompt_value (str): The selected prompt.
            outputs_value (int): The number of responses.
        """
        # Gets the prompt key
        for key, val in self.prompts.items():
            if val == prompt_value:
                prompt_key = key
        # Write the response and query to a csv file named with the prompt key
        if os.path.exists(f'{self.data_dir}{prompt_key}.csv'):
            with open(f'{self.data_dir}{prompt_key}.csv', 'a', encoding='utf-8') as fn:
                writer = csv.writer(fn)
                for i in range(outputs_value):
                    try:
                        writer.writerow([user_input_value, cgpt_response[i].message.content.strip()])
                    except AttributeError as e:
                        writer.writerow([user_input_value, cgpt_response[0]])
        else:
            with open(f'{self.data_dir}{prompt_key}.csv', 'w', encoding='utf-8') as fn:
                writer = csv.writer(fn)
                for i in range(outputs_value):
                    writer.writerow(['User input', 'ChatGPT response'])
                    try:
                        writer.writerow([user_input_value, cgpt_response[i].message.content.strip()])
                    except AttributeError as e:
                        writer.writerow([user_input_value, cgpt_response[0]])

    @validate
    def save_to_txt(self, nb: ttk.Notebook):
        """
         Saves the content of the active tab in a notebook widget to a text file.
 
         Parameters:
             nb (ttk.Notebook): The notebook widget containing the content to save.
         """
        # WRites the contents of the selected notebook to a txt file
        filepath = self.resp_dir + str(int(datetime.datetime.now().timestamp())) + '.txt'
        # The index of the active notebook
        nb_idx = self.notebooks.index(nb)
        active_tab = self.notebooks[nb_idx].select()
        active_tab = active_tab.split('.')[-1]
        text_widget = self.notebooks[nb_idx].children[active_tab].children['!text']
        content = text_widget.get('1.0', 'end-1c')        
        with open(filepath, 'w', encoding='utf-8') as fn:
            fn.write(content)

    @validate
    def get_from_csv(self, prompt_key: str) -> list:
        """This method retrieves the last row from a CSV file based on a given prompt key.
     
         Args:
             prompt_key (str): The key used to identify the CSV file.
     
         Returns:
             str: The last row from the CSV file if it exists, otherwise 'No history'.
     
         Raises:
             FileNotFoundError: If the CSV file with the given prompt key does not exist.
     
         """        
        try:
            rows = []
            with open(f'{self.data_dir}{prompt_key}.csv', 'r', encoding='utf-8') as fn:
                reader = csv.reader(fn)
                for row in reader:
                    rows.append(row)
        except FileNotFoundError as e:
            return ['No history', 'No history']
        except csv.Error:
            return ['No history', 'No history']
        if len(rows) > 0:
            return rows[-1]
        return ['No history', 'No history']

    @validate
    def copy_to_clipboard(self, nb: ttk.Notebook):
        """
        Copies the content of the active tab in a notebook widget to the clipboard.

        Parameters:
            nb (ttk.Notebook): The notebook widget containing the content to copy.
        """        
        # Active notebook index
        nb_idx = self.notebooks.index(nb)
        active_tab = self.notebooks[nb_idx].select()
        active_tab = active_tab.split('.')[-1]
        text_widget = self.notebooks[nb_idx].children[active_tab].children['!text']
        content = text_widget.get('1.0', 'end-1c')
        pyperclip.copy(content)  # Copy the text to the clipboard

    @validate
    def code_copy(self, nb: ttk.Notebook):
        """
        Copies the content of the active tab in a notebook widget to the clipboard.

        Parameters:
            nb (ttk.Notebook): The notebook widget containing the content to copy.
        """
        # Active notebook index
        nb_idx = self.notebooks.index(nb)
        active_tab = self.notebooks[nb_idx].select()
        active_tab = active_tab.split('.')[-1]
        text_widget = self.notebooks[nb_idx].children[active_tab].children['!text']
        content = text_widget.get('1.0', 'end-1c')
        split_content = content.split('```')
        for content in split_content:
            if 'PYTHON' in content.upper()[:6]:
                code = split_content[1][6:]
        pyperclip.copy(code)  # Copy the text to the clipboard        

    def select_all(self, event, text_widget):
        text_widget.tag_add(tk.SEL, "1.0", tk.END)
        text_widget.mark_set(tk.INSERT, "1.0")
        text_widget.see(tk.INSERT)
        return 'break'

if __name__ == '__main__':
    chat_gpt_window = ChatGptWindow()
    chat_gpt_window.create_all_widgets()
    chat_gpt_window.window.mainloop()
