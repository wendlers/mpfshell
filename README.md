# mpfshell / mpfmount
2016-03-22, sw@kaltpost.de

A simple shell based file explorer and FUSE based mounter for ESP8266 
[Micropython](https://github.com/micropython/micropython) based devices.

The shell is a "quick" solution for up/downloading files to the ESP8266 port
of MP. It basically offers commands to list and upload/download files on the
flash FS of the device.

The FUSE integration allows to mount a ESP8266 based Micropython device into
the file system. It currently offers basic operations like read, write, delete
and rename, as well as some special functions (all provided tough the filesystem).

__Note__: At the time of writing, only text files (no binaries) are supported. 
Also this will not work with the current code from the Micropython repository,
but only with the ALPHA v02 from the kickstarter.


## Requirements

* ESP8266 board running Micropython (at least mp-esp8266-firmware-v02.bin from the kickstarter)
* OS supporting fuse (Linux, Mac OS)
* The fusepy library (sudo pip install fusepy)
* The [pyboard.py] (https://github.com/micropython/micropython/tree/master/tools) tool from the 
  Micropython repository needs to be in the python path (for convenience, this file is included here too)
  
__Note__: The tools only work if the REPL is accessible on the device!

## Shell Usage

Start the shell with:

    ./mpfshell.sh

At the shell prompt, first connect to the device:

    mpfs> open /dev/ttyUSB0

Now you can list the files on the device with:

    mpfs> ls

    Remote files:

     boot.py

To upload e.g. the local file "boot.py" to the device use:

    mpfs> put boot.py

If you like to use a different filename on the device, you could use this:

    mpfs> put boot.py main.py

And to download e.g. the file "boot.py" from the device use:

    mpfs> get boot.py
    
Using a different local file name:

    mpfs> get boot.py my_boot.py

To remove a file on the device use:

    mpfs> rm boot.py

To navigate on the local filesystem, use:

    lls, lcd lpwd

For a full list of commands use:

    mpfs> help
    mpfs> help <command>


__Note__: While in the shell, the REPL is not accessible by terminal.


## FUSE Mount Usage

Mount device on port "/dev/ttyUSB0" to "$HOME/mp":

    test -d $HOME/mp || mkdir $HOME/mp
    ./mpmount.sh -p /dev/ttyUSB0 -m $HOME/mp
    cd $HOME/mp
      
Now, work with the files as if they where normal files. When done
editing, creating etc. commit your changes back to the MP board.
    
Commit a single file (e.g. "boot.py"):

    echo "boot.py" > $HOME/mnt/.commit

Commit all changed files:

    echo "*" > $HOME/mp/.commit

Or, as a short-cut for the above, jsut execute the ".commit" file:

    ./.commit

__Note__: Changes are not committed before un-mounting will be lost!

While the MP board is FUSE mounted, the serial line (to the REPL) is
occupied. To overcome this problem, there is an other special file
in the mounted FS called ".release". This file could be used to 
make the FUSE mounter release the serial line to allow terminal access,
and later reattach the line (while the serial line is released,
no commits to the MP board are possible).
 
Relase the serial line, access REPL with terminal (miniterm.py from pyserial):

    echo "1" > .release
    miniterm.py -p /dev/ttyUSB0 -b 115200

When done with the terminal, reattach the serial line:

    echo "0" > .release

For the above three commands, there is an other shortcut called ".terminal".
If executed, it will release the serial line, connect miniterm to the REPL, and
when minierm is ended by the user reattaches the serial line:

    ./.terminal
