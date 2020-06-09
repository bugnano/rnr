import os

OPENER = 'xdg-open'
PAGER = os.environ.get('PAGER', 'less')
EDITOR = os.environ.get('VISUAL', os.environ.get('EDITOR', 'vi'))

USE_INTERNAL_VIEWER = True

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

# Config for rnrview
TAB_SIZE = 4

# Theme for rnrview
TEXT_FG = 'light gray'
TEXT_BG = 'dark blue'
NAMESPACE_FG = 'light green'
KEYWORD_FG = 'yellow'
CLASS_FG = 'light red'
OPERATOR_FG = 'white'
STRING_FG = 'light cyan'
LITERAL_FG = 'light magenta'
COMMENT_FG = 'dark cyan'
LINENO_FG = 'white'

