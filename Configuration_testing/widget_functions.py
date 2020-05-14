#    Version:   1.0
#    Date:      12/03/2019
#    Author:    Ben Loveday and Hayley Evers-King (Plymouth Marine Laboratory)
#    Credit:    This code was developed for EUMETSAT under contracts for the 
#               Copernicus programme.
#    License:   This code is offered as open source and free-to-use in the 
#               public domain, with no warranty.

from ipywidgets import widgets
from IPython.display import display
import os
import sys

def handle_submit(sender):

    init_path = sender.value
    found_path = False
    if os.path.exists(init_path):
        print('Found path: ' + init_path)
        found_path = True
    else:
        print('Not found path: ' + init_path + '. Please check it is correct')

    if found_path:
        print("---------------------------------------------------------------")
        if '/' in init_path:
            file_list = init_path.split('/')
            path_command = "os.path.join(" \
                           + ','.join('"' + item + '"' for item in file_list) \
                           + ")"
        elif '\\' in init_path:
            file_list = init_path.split('\\')
            if ':' in file_list[0]:
            	file_list[0] = file_list[0]+'/'
            file_list = filter(None, file_list)
            path_command = "os.path.join("+','.join('"' + item \
                           + '"' for item in file_list)+")"
        print('The safe, cross-platform way to join this path in python is: ')
        print("\033[1m" + path_command + "\033[0m")
        print("")
        if 'gpt' in sender.value:
            msg = 'GPTPATH'
        else:
            msg = 'MYPATH'        
        print('Please remember the field in bold, we will refer to it as ' \
              + '"' + msg + '" in later scripts.')
        print("---------------------------------------------------------------")

def text_box(msg):
    text = widgets.Text(\
           placeholder='Please copy your ' + msg + ' path to here...')
    display(text)
    if 'GPT' in msg:
        text.on_submit(handle_submit)
    else:
        text.on_submit(handle_submit)