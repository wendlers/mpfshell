# mpfshell - hardware tests
2016-06-29, sw@kaltpost.de

This directory contains the test-suite (WIP) for the mpfshell which runs against
real hardware. It uses [pytest](https://pytest.org/).

## Running the tests

The tests are executed against a real MP board. Thus, the machine 
running the tests needs access to the MP board via serial line or 
websocket. 

The tests are currently only usable on the ESP8266 (not the WiPy).

Running the tests on ttyUSB0:

    export PYTHONPATH=$PWD/../..
    py.test -v --testcon "ser:/dev/ttyUSB0"

Or over websockets:

    export PYTHONPATH=$PWD/../..
    py.test -v --testcon "ws:192.168.1.1,passwd"

To test the caching variant of the shell commands, add the `--caching`
flag:

    export PYTHONPATH=$PWD/..
    py.test -v --caching --testcon "ws:192.168.1.1,passwd"

__Note:__ The test initially wipes everything from flash, except 
`boot.py` and `port_config.py`. To omit this, the `--nosetup` flag
could be used (but the tests will fail if certain files and directories
already exist).

