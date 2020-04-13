# The RNR File Manager (RNR's Not Ranger)

The RNR File Manager (RNR's Not Ranger) is a text based file manager that
combines the best features of
[Midnight Commander](https://midnight-commander.org/) and
[Ranger](https://ranger.github.io/)


## Features

* Very fast file and directory browser with Vim-style keys and powerful fuzzy filter

## Goals

* The most robust file copier in existence (TO DO)
* Work on remote servers via ssh (TO DO)

## Non-Goals

* Transfer Speed: In the speed/reliability tradeoff it will choose reliability first.
* Portability: It is intended for use in Linux, and, although it may work on
  other POSIX-compatible operating systems, errors on non-Linux systems are not
  considered bugs.
* Configurability: Apart from choosing a colour scheme, and custom bookmarks,
  it is not intended to be configurable, so no custom commands or keybindings.
  This has the advantage that rnr will work the same everywhere it is installed.

## Development status

This project is still in its infancy and it's only a directory changer for the
moment.

## Roadmap

* A robust file copying engine
* A simple file and directory preview in the other panel

## Future Roadmap

* Connect to SFTP servers and transfer files to/from them
* Explore compressed files

## Key bindings

### General

* **ESC**: Return to normal mode (like Vim)
* **q**, **Q**, **F10**: Exit
* **CTRL-R**: Reload panels
* **TAB**: Change active panel
* **ALT-I**: Set the other panel to the current directory
* **ALT-O**: Set the other panel to the highlited directory
* **F3**: View file with the selected pager / Enter directory
* **F4**: Edit file/directory with the selected editor
* **F7**: Make directory

### Panel

* **h**, **LEFT**: Go to the parent directory
* **j**, **DOWN**: Go to the next list element
* **k**, **UP**: Go to the previous list element
* **l**, **RIGHT**, **ENTER**: Enter directory / Open file with the selected opener
* **g**, **HOME**: Go to the top of the list
* **G**, **END**: Go to the bottom of the list
* **CTRL-B**, **PAGE UP**: Go up a page in the list
* **CTRL-F**, **PAGE DOWN**: Go down a page in the list
* **f**, **/**: Filter list (fuzzy finder like [fzf](https://github.com/junegunn/fzf))
* **BACKSPACE**: Show/Hide hidden files

#### Sorting

* **sn**: Sort by Name
* **sN**: Sort by Name (Reverse)
* **se**: Sort by Extension
* **sE**: Sort by Extension (Reverse)
* **sd**: Sort by Date & Time
* **sD**: Sort by Date & Time (Reverse)
* **ss**: Sort by Size
* **sS**: Sort by Size (Reverse)

#### Bookmarks

* **m`<KEY>`**: Add current directory to the bookmark named `<KEY>`
* **'`<KEY>`**: Go to the bookmark named `<KEY>`
* **''**: Go to the previous directory (2 times ', not ")

#### Rename

* **r**, **c**: Rename file (replace)
* **i**, **I**: Rename file (insert)
* **a**: Rename file (append before extension)
* **A**: Rename file (append after extension)

#### Select (Tag) files

* **INSERT**, **SPACE**: Toggle tag on selected file
* __*__, **v**: Toggle tag on all files
* **+**: Tag files that match the shell wildcard pattern
* **-**, **\\**: Untag files that match the shell wildcard pattern
* **uv**: Untag all files

#### Operations on tagged files

* **F8**: Delete tagged files (or selected file)

#### Shell

* **!**: Execute a shell command

The shell command accepts the following substitutions:

* `$f`: The current file
* `$d`: The current directory
* `$s`,`$t`: The tagged files
* `$F`: The file in the other panel
* `$D`: The directory of the other panel
* `$S`,`$T`: The tagged files of the other panel

There is no need to enclose these substitutions in quotes, as they are already being quoted by rnr

