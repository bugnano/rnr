# The RNR File Manager (RNR's Not Ranger)

The RNR File Manager (RNR's Not Ranger) is a text based file manager that
combines the best features of
[Midnight Commander](https://midnight-commander.org/) and
[Ranger](https://ranger.github.io/).

Its main goal is to be the most robust file copier in existence.


## Features

* Very fast file and directory browser with Vim-style keys and powerful fuzzy filter
* Explore compressed archives as normal read-only directories (requires archivemount)
* Fast directory jumping with bookmarks
* Many file rename options
* Robust file copy engine with minimal user interaction. Great for copying
  large amounts of data reliably.
* Text and binary file viewer with line numbers and syntax highlighting for
  text, and masked data for binary, with optional hex display mode for both
  formats
* Optional file and directory preview in the other panel
* If the internal file viewer is not used, view files with the selected pager
  (default: less)
* Edit files with the selected editor (default: vi)
* Open files with the selected opener (default: xdg-open)
* Execute shell commands, with macro substitutions to easily manipulate the
  tagged files
* cd to the last visited directory on exit (compatible with bash and fish)

## Screenshots

![ranger-like](https://raw.githubusercontent.com/bugnano/rnr/master/doc/ranger-like.png)

![mc-like](https://raw.githubusercontent.com/bugnano/rnr/master/doc/mc-like.png)

## System requirements

* Linux (a POSIX-compatible OS like macOS, FreeBSD or Cygwin may work, but
  it's not officially supported)
* Python 3.6 or greater
* archivemount (Optional, but recommended)

## Installation and running

```bash
# To install or upgrade
pip3 install --user --upgrade rnr

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

## Robust file copy

File copying looks like a simple operation, but there are many cases where it could go wrong.

To better understand the situation, let me tell you a couple of stories:

You have several big, multi-gigabyte files that you need to copy from one hard
drive to another.  This operation is very time consuming, so you start the
copy process in the evening, and let it run overnight.

The next day, you wake up, and see that the copy process is stuck at 10% and
you see a window prompting you what to do, as there already is a file with the
same name in the destination directory (or an error has occurred during the
copy, and the program is asking you if you want to continue or abort).

Result: you wasted almost the whole night, as the copy process was waiting for
your input.

Now imagine instead that you wake up and see that your computer shows an empty
desktop because the power went down in the night.

Result: The copy process has been interrupted and you have no idea which files
have been copied and which files not.

> There must be a better way! - Raymond Hettinger

So rnr addresses these problems in 2 ways:

1. The copy operation is completely non-interactive, the action to be done in
   case of conflict is decided before the copy process starts. Once the copy
   process starts, all the conflicts are handled automatically, and all the
   errors are skipped. At the end of the process, you will see a report window
   that shows all the actions taken by the copy engine (for example
   renaming/overwriting a file, or skipping a file due to an error). The
   report can be saved to a text file, and analized as required.
2. Every file operation is logged to a on-disk database, so when the power
   goes off (and it will...), you will know where the copy process was at, and
   resume from that.

Now, let's address the elephant in the room: The on-disk database slows down
operations considerably in the case of many small files.

While rnr defaults to using a database file, it is in fact optional, and can
be disabled by a command line switch, or by the "No DB" button.

Of course, everything said about the file copy is applied to the file move
operation as well.

## Non-Goals

* Transfer Speed: In the speed/reliability tradeoff it will choose reliability first.
* Portability: It is intended for use in Linux, and, although it may work on
  other POSIX-compatible operating systems, errors on non-Linux systems are not
  considered bugs.
* Configurability: Apart from choosing the pager, opener and editor, a colour
  scheme and custom bookmarks, it is not intended to be configurable, so no
  custom commands or keybindings.  This has the advantage that rnr will work the
  same everywhere it is installed.

