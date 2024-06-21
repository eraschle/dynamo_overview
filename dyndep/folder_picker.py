import os
import tkinter as tk
from tkinter import filedialog

import streamlit as st


# Folder picker button
def folder_picker(column, title: str, key: str, state_key: str) -> None:
    with column:
        st.write("Please select a folder:")
        clicked = st.button(label=title, key=key)
        if clicked:
            root = tk.Tk()
            root.withdraw()
            root.wm_attributes("-topmost", 1)
            current = st.session_state.get(state_key, None)
            if current is None:
                current = os.path.abspath("~")
            selected = filedialog.askdirectory(parent=root, initialdir=current)
            if not os.path.exists(selected):
                return
            st.session_state[state_key] = selected
