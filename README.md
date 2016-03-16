# mpfshell
2016-03-16, sw@kaltpost.de

A simple shell based file explorer for ESP8266 
[Micropython](https://github.com/micropython/micropython) based devices.

The shell is a "quick" solution for up/downloading files to the ESP8266 port
of MP. It basically offers commands to list and upload/download files on the
flash FS of the device.

__Note__: At the time of writing, only text files (no binaries) are supported.

## Requirements

* ESP8266 board running Micropython (at least mp-esp8266-firmware-v02.bin from the kickstarter)
* The [pyboard.py tool](https://github.com/micropython/micropython/tree/master/tools) from the 
  Micropython repository needs to be in the python path (for convenience, this file is included here too)
  
  
## Usage

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
