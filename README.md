# The RNR File Manager (RNR's Not Ranger)

The RNR File Manager (RNR's Not Ranger) is a text based file manager that
combines the best features of
[Midnight Commander](https://midnight-commander.org/) and
[Ranger](https://ranger.github.io/).

Its main goal is to be the most robust file copier in existence.


## Features

* Very fast file and directory browser with Vim-style keys and powerful fuzzy filter
* Fast directory jumping with bookmarks
* Many file rename options
* Robust file copy engine with minimal user interaction. Great for copying
  large amounts of data reliably.
* View files with the selected pager (default: less)
* Edit files with the selected editor (default: vi)
* Open files with the selected opener (default: xdg-open)
* Execute shell commands on the selected files
* cd to the last visited directory on exit (compatible with bash and fish)

## Screenshots

![ranger-like](https://raw.githubusercontent.com/bugnano/rnr/master/doc/ranger-like.png)

![mc-like](https://raw.githubusercontent.com/bugnano/rnr/master/doc/mc-like.png)

## System requirements

* Linux (a POSIX-compatible OS like macOS, FreeBSD or Cygwin may work, but
  it's not officially supported)
* Python 3.6 or greater

## Installation and running

```bash
# To install
pip3 install --user rnr

# To run
rnr
```

If you're using bash and you want to change directory on exit, you have to add
a line like this in your `~/.bashrc`:

```bash
source ~/.local/share/rnr/rnr.sh
```

If you're using fish, then simply copy the file `~/.local/share/rnr/rnr.fish`
to `~/.config/fish/functions/` (create the directory if it does not exist).

## Documentation

The rnr man page can be invoked with the command:

```bash
man rnr
```

[Here is a text version of the man page](https://github.com/bugnano/rnr/blob/master/doc/rnr.1.adoc)

## Non-Goals

* Transfer Speed: In the speed/reliability tradeoff it will choose reliability first.
* Portability: It is intended for use in Linux, and, although it may work on
  other POSIX-compatible operating systems, errors on non-Linux systems are not
  considered bugs.
* Configurability: Apart from choosing the pager, opener and editor, a colour
  scheme and custom bookmarks, it is not intended to be configurable, so no
  custom commands or keybindings.  This has the advantage that rnr will work the
  same everywhere it is installed.

## Roadmap

* Connect to SFTP servers and transfer files to/from them
* Explore/create compressed archives
* A simple file and directory preview in the other panel

