
import time
import sys
import os
from contextlib import suppress
from typing import List, Iterable, TypeVar, Sequence, Set

def main(args: List[str]) -> None:

    from mp.mpfshell import main

    sys.argv = [args[0], '-c', 'open', args[4] + ';', 'lcd', args[2][args[2].find('/'):] + ';', 'runfile', os.path.basename(args[5]) + ';', '-n']
    main()

if __name__ == '__main__':
    main(sys.argv)
