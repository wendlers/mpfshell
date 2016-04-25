# mpfshell / mpfmount
2016-03-25, sw@kaltpost.de

A simple shell based file explorer and FUSE based mounter for ESP8266 
[Micropython](https://github.com/micropython/micropython) based devices.

The shell is a "quick" solution for up/downloading files to the ESP8266 port
of MP. It basically offers commands to list and upload/download files on the
flash FS of the device.

The FUSE integration allows to mount a ESP8266 based Micropython device into
the file system. It currently offers basic operations like read, write, delete
and rename, as well as some special functions (all provided tough the filesystem).

__Note__: The software is tested on Ubunto 16.04 LTS.

## Requirements

General:

* ESP8266 board running latest [Micropython](https://github.com/micropython/micropython)

For the shell:

* Python 2.7
* The PySerial library >= 3.0 (sudo pip install pyserial)
* The colorama library >= 0.3.6 (sudo pip install colorama)

Additionally for the FuseMount:

* OS supporting fuse (Linux, Mac OS)
* The fusepy library >= 2.0 (sudo pip install fusepy)
  
__Note__: The tools only work if the REPL is accessible on the device!

## Installing

To install this tool execute the following:

    sudo pip install fusepy
    sudo pip install colorama
    sudo python setup.py install
    
## General

The shell supports TAB completion for commands and file names.
So it totally is worth it pressing TAB-TAB every now and then :-)
    
## Shell Usage

Start the shell with:

    mpfshell

At the shell prompt, first connect to the device:

    mpfs> open ttyUSB0

Now you can list the files on the device with:

    mpfs> ls

To upload e.g. the local file "boot.py" to the device use:

    mpfs> put boot.py

If you like to use a different filename on the device, you could use this:

    mpfs> put boot.py main.py

Or to upload all files that match a regular expression from the 
current local directory to the current remote directory:

    mpfs> mput .*\.py

And to download e.g. the file "boot.py" from the device use:

    mpfs> get boot.py
    
Using a different local file name:

    mpfs> get boot.py my_boot.py

Or to download all files that match a regular expression from the 
current remote directory to the current local directory:

    mpfs> mget .*\.py

To remove a file (or directory) on the device use:

    mpfs> rm boot.py

Or remove all remote files that match a regular expression:

    mpfs> mrm test.*\.py

To create a new remote directory:

    mpfs> md test

To navigate remote directories:

    mpfs> cd test
    mpfs> cd ..
    mpfs> cd /some/full/path
    
See which is the curren remote directory:

    mpfs> pwd

Remove a remote directory:

    mpfs> rm test
    
__Note__: The directory to delete needs to be empty!

To navigate on the local filesystem, use:

    lls, lcd lpwd

Enter REPL:

    repl
    
To exit REPL and return to the file shell use Ctrl+Alt+] 

For a full list of commands use:

    mpfs> help
    mpfs> help <command>

The shell is also scriptable.

E.g. to execute a command, and then enter the shell:

    mpfshell -c "open ttyUSB0"
    
Or to copy the file "boot.py" to the device, and don't enter the shell at all:

    mpfshell -n -c "open ttyUSB0; put boot.py"

It is also possible to put a bunch of shell commands in a file, and then execute
them from that file.
 
E.g. creating a file called "myscript.mpf":

    open ttyUSB0 
    put boot.py
    put main.py
    ls
    
And execute it with:

    mpfshell -s myscript.mpf    

## FUSE Mount Usage

Mount device on port "/dev/ttyUSB0" to "$HOME/mp":

    test -d $HOME/mp || mkdir $HOME/mp
    mpfmount -p /dev/ttyUSB0 -m $HOME/mp
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
