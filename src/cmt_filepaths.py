#kevin fink
#feb 6 2024
#kevin @shorecode.org
#filepaths_template.py

import os
import platform
from dataclasses import dataclass

@dataclass
class Files:
    platform = platform.system()
    filepaths = ['data/output/','data/output/saved_resp/', 'data/radiance/radiance.tcl',
                 'data/prompts.yaml', 'data/icon.png', 'cmt_main.py', 'data/laser.mp3']
    win_filepaths = list()
    for f in filepaths:
        f = f.replace('/', '\\')
        f = os.path.dirname(os.path.abspath(__file__)) + '\\' + f
        win_filepaths.append(f)
    for f in filepaths:
        idx = filepaths.index(f)
        f = os.path.dirname(os.path.abspath(__file__)) + '/' + f
        filepaths.pop(idx)
        filepaths.insert(idx, f)

    def get_files_list(self) -> list:
        if self.platform == 'Windows':
            return self.win_filepaths
        elif self.platform == 'Linux':
            return self.filepaths
        
    def get_file_by_index(self, idx: int) ->list:
        if self.platform == 'Windows':
            return self.win_filepaths[idx]
        elif self.platform == 'Linux':
            return self.filepaths[idx]
