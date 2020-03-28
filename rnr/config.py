import os

OPENER = 'xdg-open'
PAGER = os.environ.get('PAGER', 'less')
EDITOR = os.environ.get('VISUAL', 'vi')

# Theme
SHOW_BUTTONBAR = True

PANEL_FG = 'light gray'
PANEL_BG = 'dark blue'
REVERSE_FG = 'black'
REVERSE_BG = 'light gray'
SELECTED_FG = 'black'
SELECTED_BG = ('dark cyan' if os.geteuid() else 'dark red')

MARKED_FG = 'yellow'
MARKSELECT_FG = 'yellow'

DIRECTORY_FG = 'white'
EXECUTABLE_FG = 'light green'
SYMLINK_FG = 'light gray'
STALELINK_FG = 'light red'
DEVICE_FG = 'light magenta'
SPECIAL_FG = 'black'
ARCHIVE_FG = 'light magenta'

HOTKEY_FG = 'white'
HOTKEY_BG = 'black'

