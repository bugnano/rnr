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

* Connect to SFTP servers and transfer files to/from them
* Explore compressed files
* A simple file and directory preview in the other panel

