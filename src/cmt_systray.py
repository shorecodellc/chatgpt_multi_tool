import pystray
import threading
import psutil
import os
import subprocess
from dataclasses import dataclass
from PIL import Image
from cmt_filepaths import Files

files = Files()
filelist = files.get_files_list()
# Path to the Excel file
icon_fp = filelist[4]
cmt_main_fp = filelist[5]

def chat_main():
    subprocess.run(['python3', cmt_main_fp])
    

def on_exit(icon, pid):
    os.kill(pid, 9)
    icon.stop()
    print("Exiting")  # Or add any other code if needed
    exit(0)

@dataclass
class Cgpt:
    def run_cgpt(self):
        pids = self.get_pids()
        chat_thread = threading.Thread(target=chat_main)
        chat_thread.start()
        new_pids = self.get_pids()
        for np in new_pids:
            if np not in pids:
                self.cgpt_pid = np
    def get_pids(self):
        pids = list()
        for proc in psutil.process_iter(['pid', 'name']):
            pids.append(proc.info['pid'])
        return pids

cgpt = Cgpt()
cgpt.cgpt_pid = 0

# Create an image to be used as the tray icon
image = Image.open(icon_fp)  # Replace "icon.png" with the path to your icon image file

# Create a menu for the system tray icon
menu = (
    pystray.MenuItem('Run ChatGPT', lambda: cgpt.run_cgpt()),
    pystray.MenuItem('Exit', lambda: on_exit(icon, cgpt.cgpt_pid)))


# Create the system tray icon with the menu
icon = pystray.Icon("ChatGPT Multi Tool", image, "ChatGPT Multi Tool", menu)

# Run the script as long as the icon is visible
if __name__ == '__main__':
    icon.run()
