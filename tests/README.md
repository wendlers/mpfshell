# mpfshell - tests
2016-06-15, sw@kaltpost.de

This directory contains the test-suite (WIP) for the mpfshell. It uses [pytest](https://pytest.org/).

## Running the tests

The tests are executed against a real MP board. Thus, the machine running the tests needs access to 
the MP board via serial line. 

Running the tests on ttyUSB0:

    py.test -v --testcon "ser:/dev/ttyUSB0"

__Note:__ The test initially wipes everything from flash, except `boot.py` and `port_config.py`.