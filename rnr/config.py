import os

OPENER = 'xdg-open'
PAGER = os.environ.get('PAGER', 'less')
EDITOR = os.environ.get('VISUAL', os.environ.get('EDITOR', 'vi'))

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
DIR_SYMLINK_FG = 'white'
EXECUTABLE_FG = 'light green'
SYMLINK_FG = 'light gray'
STALELINK_FG = 'light red'
DEVICE_FG = 'light magenta'
SPECIAL_FG = 'black'
ARCHIVE_FG = 'light magenta'

HOTKEY_FG = 'white'
HOTKEY_BG = 'black'

ERROR_FG = 'white'
ERROR_BG = 'dark red'
ERROR_TITLE_FG = 'yellow'
ERROR_FOCUS_FG = 'black'
ERROR_FOCUS_BG = 'light gray'

DIALOG_FG = 'black'
DIALOG_BG = 'light gray'
DIALOG_TITLE_FG = 'dark blue'
DIALOG_FOCUS_FG = 'black'
DIALOG_FOCUS_BG = 'dark cyan'

INPUT_FG = 'black'
INPUT_BG = 'dark cyan'

