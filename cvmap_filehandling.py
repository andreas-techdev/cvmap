#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Thu Aug 21 18:22:00 2025

some general file handling helper functions 

@author: andreas
"""

import sys, os
import tkinter as tk
from tkinter import filedialog

def open_file_dialog():
    """
    Opens a file selection dialogue

    Returns
    -------
        STRING: the file path

    """
    root = tk.Tk()
    root.withdraw()
    
    file_path = filedialog.askopenfilename(
        title = "Choose SVG file",
        initialfile  = "example/CVTintin.svg",
        filetypes=[
            ("SVG files", "*.svg"),
            ("All files", "*.*")
        ]
    )
    root.destroy()
    
    if file_path:
        return file_path
    else:
        print("No file chosen. Aborting")
        sys.exit()

def get_filename():
    """
    Tries to retrieve the filename from the command line, otherwise opens file dialogue

    Returns
    -------
    STRING: file path

    """ 
    if len(sys.argv) > 1:
        file_path = sys.argv[0]
        if os.path.exists(file_path):
            return file_path
    file_path = open_file_dialog()
    return file_path

    
if __name__ == "__main__":
    filename= get_filename()
    print(filename)