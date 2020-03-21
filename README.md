# The RNR File Manager (RNR's Not Ranger)

The RNR File Manager (RNR's Not Ranger) is a text based file manager that
combines the best features of
[Midnight Commander](https://midnight-commander.org/) and
[Ranger](https://ranger.github.io/)


## Features

* Fast directory navigation with Vim-style keys and powerful fuzzy filter

## Goals

* Very fast file and directory browser
* The most robust file copier in existence (TO DO)
* Work on remote servers via ssh (TO DO)

## Non-Goals

* Transfer Speed: In the speed/reliability tradeoff it will choose reliability first.
* Portability: It is intended for use in Linux, and compatibility to other
  operating systems is not a goal.
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

* **ESC**: Return to command mode (like Vim)
* **q**, **Q**, **F10**: Exit
* **TAB**: Change active panel
* **ALT-I**: Set the other panel to the current directory

### Panel

* **h**, **LEFT**: Go to the parent directory
* **j**, **DOWN**: Go to the next list element
* **k**, **UP**: Go to the previous list element
* **l**, **RIGHT**, **ENTER**: Enter directory / Open file with xdg-open
* **g**, **HOME**: Go to the top of the list
* **G**, **END**: Go to the bottom of the list
* **CTRL-B**, **PAGE UP**: Go up a page in the list
* **CTRL-F**, **PAGE DOWN**: Go down a page in the list
* **f**, **/**: Filter list (fuzzy finder like [fzf](https://github.com/junegunn/fzf))
* **BACKSPACE**: Show/Hide hidden files

* **sn**: Sort by Name
* **sN**: Sort by Name (Reverse)
* **se**: Sort by Extension
* **sE**: Sort by Extension (Reverse)
* **sd**: Sort by Date & Time
* **sD**: Sort by Date & Time (Reverse)
* **ss**: Sort by Size
* **sS**: Sort by Size (Reverse)

