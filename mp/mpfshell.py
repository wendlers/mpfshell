##
# The MIT License (MIT)
#
# Copyright (c) 2016 Stefan Wendler
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in
# all copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN
# THE SOFTWARE.
##


import io
import cmd
import os
import argparse
import colorama
import glob
import sys
import serial
import logging
import platform
import time

from mp import version
from mp.mpfexp import MpFileExplorer
from mp.mpfexp import MpFileExplorerCaching
from mp.mpfexp import RemoteIOError
from mp.pyboard import PyboardError
from mp.conbase import ConError
from mp.tokenizer import Tokenizer


class MpFileShell(cmd.Cmd):

    def view_all_serial(self):
        import serial.tools.list_ports
        print(colorama.Fore.LIGHTCYAN_EX + "\nlooking for computer port...")
        plist = list(serial.tools.list_ports.comports())

        if len(plist) <= 0:
            print("serial not found!")
        else:
            for serial in plist:
                print("serial name :", serial[0].split('/')[-1])
            print("input ' open", plist[len(plist) - 1][0].split('/')[-1], "' and enter connect your board.")

    def __init__(self, color=False, caching=False, reset=False):
        if color:
            colorama.init()
            cmd.Cmd.__init__(self, stdout=colorama.initialise.wrapped_stdout)
        else:
            cmd.Cmd.__init__(self)

        self.color = color
        self.caching = caching
        self.reset = reset
        self.open_args = None
        self.fe = None
        self.repl = None
        self.tokenizer = Tokenizer()

        if platform.system() == 'Windows':
            self.use_rawinput = False

        if platform.system() == 'Darwin':
            self.reset = True

        self.__intro()
        self.__set_prompt_path()

        self.do_help(None)
        print(colorama.Fore.YELLOW + "All support commands, can input help ls or other command if you don't know how to use it(ls).")
        self.view_all_serial()

    def __del__(self):
        self.__disconnect()

    def __intro(self):

        if self.color:
            self.intro = '\n' + colorama.Fore.GREEN + \
                         '** Micropython File Shell v%s, sw@kaltpost.de & juwan@banana-pi.com ** ' % version.FULL + \
                         colorama.Fore.RESET + '\n'
        else:
            self.intro = '\n** Micropython File Shell v%s, sw@kaltpost.de & juwan@banana-pi.com **\n' % version.FULL

        self.intro += '-- Running on Python %d.%d using PySerial %s --\n' \
                       % (sys.version_info[0], sys.version_info[1], serial.VERSION)

    def __set_prompt_path(self):

        if self.fe is not None:
            pwd = self.fe.pwd()
        else:
            pwd = "/"

        if self.color:
            self.prompt = colorama.Fore.BLUE + "mpfs [" + \
                          colorama.Fore.YELLOW + pwd + \
                          colorama.Fore.BLUE + "]> " + colorama.Fore.RESET
        else:
            self.prompt = "mpfs [" + pwd + "]> "

    def __error(self, msg):

        if self.color:
            print('\n' + colorama.Fore.RED + msg + colorama.Fore.RESET + '\n')
        else:
            print('\n' + msg + '\n')

    def __connect(self, port):

        try:
            self.__disconnect()
            if(port is None):
                port = self.open_args
            if self.reset:
                print("Hard resetting device ...")
            if self.caching:
                self.fe = MpFileExplorerCaching(port, self.reset)
            else:
                self.fe = MpFileExplorer(port, self.reset)
            print("Connected to %s" % self.fe.sysname)
            self.__set_prompt_path()
        except PyboardError as e:
            logging.error(e)
            self.__error(str(e))
        except ConError as e:
            logging.error(e)
            self.__error("Failed to open: %s" % port)
        except AttributeError as e:
            logging.error(e)
            self.__error("Failed to open: %s" % port)

        if self.__is_open() == False:
            time.sleep(3)
            self.__connect(None)



    def __reconnect(self):
        import time
        for a in range(3):
            self.__connect(None)
            if self.__is_open():
                break
            print(colorama.Fore.GREEN + 'try reconnect... ' + colorama.Fore.RESET)
            time.sleep(3)

    def __disconnect(self):

        if self.fe is not None:
            try:
                self.fe.close()
                self.fe = None
                self.__set_prompt_path()
            except RemoteIOError as e:
                self.__error(str(e))

    def __is_open(self):

        if self.fe is None:
            self.__error("Not connected to device. Use 'open' first.")
            return False

        return True

    def __parse_file_names(self, args):

        tokens, rest = self.tokenizer.tokenize(args)

        if rest != '':
            self.__error("Invalid filename given: %s" % rest)
        else:
            return [token.value for token in tokens]

        return None

    def do_q(self, args):
        return self.do_quit(args)

    def do_quit(self, args):
        """quit(q)
        Exit this shell.
        """
        self.__disconnect()

        return True

    do_EOF = do_quit

    def do_o(self, args):
        return self.do_open(args)

    def do_open(self, args):
        """open(o) <TARGET>
        Open connection to device with given target. TARGET might be:

        - a serial port, e.g.       ttyUSB0, ser:/dev/ttyUSB0
        - a telnet host, e.g        tn:192.168.1.1 or tn:192.168.1.1,login,passwd
        - a websocket host, e.g.    ws:192.168.1.1 or ws:192.168.1.1,passwd
        """

        if not len(args):
            self.__error("Missing argument: <PORT>")
        else:
            if not args.startswith("ser:/dev/") \
                    and not args.startswith("ser:COM") \
                    and not args.startswith("tn:") \
                    and not args.startswith("ws:"):

                if platform.system() == "Windows":
                    args = "ser:" + args
                elif '/dev' in args:
                    args = "ser:" + args
                else:
                    args = "ser:/dev/" + args

            self.open_args = args

            self.__connect(args)

    def complete_open(self, *args):
        ports = glob.glob('/dev/ttyUSB*') + glob.glob('/dev/ttyACM*')
        return [i[5:] for i in ports if i[5:].startswith(args[0])]

    def do_close(self, args):
        """close
        Close connection to device.
        """

        self.__disconnect()

    def do_ls(self, args):
        """ls
        List remote files.
        """

        if self.__is_open():
            try:
                files = self.fe.ls(add_details=True)

                if self.fe.pwd() != "/":
                    files = [("..", "D")] + files

                print("\nRemote files in '%s':\n" % self.fe.pwd())

                for elem, type in files:
                    if type == 'F':
                        if self.color:
                            print(colorama.Fore.CYAN + ("       %s" % elem) + colorama.Fore.RESET)
                        else:
                            print("       %s" % elem)
                    else:
                        if self.color:
                            print(colorama.Fore.MAGENTA + (" <dir> %s" % elem) + colorama.Fore.RESET)
                        else:
                            print(" <dir> %s" % elem)

                print("")

            except IOError as e:
                self.__error(str(e))

    def do_pwd(self, args):
        """pwd
         Print current remote directory.
         """
        if self.__is_open():
            print(self.fe.pwd())

    def do_cd(self, args):
        """cd <TARGET DIR>
        Change current remote directory to given target.
        """
        if not len(args):
            self.__error("Missing argument: <REMOTE DIR>")
        elif self.__is_open():
            try:
                s_args = self.__parse_file_names(args)
                if not s_args:
                    return
                elif len(s_args) > 1:
                    self.__error("Only one argument allowed: <REMOTE DIR>")
                    return

                self.fe.cd(s_args[0])
                self.__set_prompt_path()
            except IOError as e:
                self.__error(str(e))

    def complete_cd(self, *args):

        try:
            files = self.fe.ls(add_files=False)
        except Exception:
            files = []

        return [i for i in files if i.startswith(args[0])]

    def do_md(self, args):
        """md <TARGET DIR>
        Create new remote directory.
        """
        if not len(args):
            self.__error("Missing argument: <REMOTE DIR>")
        elif self.__is_open():
            try:
                s_args = self.__parse_file_names(args)
                if not s_args:
                    return
                elif len(s_args) > 1:
                    self.__error("Only one argument allowed: <REMOTE DIR>")
                    return

                self.fe.md(s_args[0])
            except IOError as e:
                self.__error(str(e))

    def do_lls(self, args):
        """lls
        List files in current local directory.
        """

        files = os.listdir(".")

        print("\nLocal files:\n")

        for f in files:
            if os.path.isdir(f):
                if self.color:
                    print(colorama.Fore.MAGENTA + (" <dir> %s" % f) + colorama.Fore.RESET)
                else:
                    print(" <dir> %s" % f)
        for f in files:
            if os.path.isfile(f):
                if self.color:
                    print(colorama.Fore.CYAN + ("       %s" % f) + colorama.Fore.RESET)
                else:
                    print("       %s" % f)
        print("")

    def do_lcd(self, args):
        """lcd <TARGET DIR>
        Change current local directory to given target.
        """

        if not len(args):
            self.__error("Missing argument: <LOCAL DIR>")
        else:
            try:
                s_args = self.__parse_file_names(args)
                if not s_args:
                    return
                elif len(s_args) > 1:
                    self.__error("Only one argument allowed: <LOCAL DIR>")
                    return

                os.chdir(s_args[0])
            except OSError as e:
                self.__error(str(e).split("] ")[-1])

    def complete_lcd(self, *args):
        dirs = [o for o in os.listdir(".") if os.path.isdir(os.path.join(".", o))]
        return [i for i in dirs if i.startswith(args[0])]

    def do_lpwd(self, args):
        """lpwd
        Print current local directory.
        """

        print(os.getcwd())

    def do_put(self, args):
        """put <LOCAL FILE> [<REMOTE FILE>]
        Upload local file. If the second parameter is given,
        its value is used for the remote file name. Otherwise the
        remote file will be named the same as the local file.
        """

        if not len(args):
            self.__error("Missing arguments: <LOCAL FILE> [<REMOTE FILE>]")

        elif self.__is_open():

            s_args = self.__parse_file_names(args)
            if not s_args:
                return
            elif len(s_args) > 2:
                self.__error("Only one ore two arguments allowed: <LOCAL FILE> [<REMOTE FILE>]")
                return

            lfile_name = s_args[0]

            if len(s_args) > 1:
                rfile_name = s_args[1]
            else:
                rfile_name = lfile_name
            try:
                self.fe.put(lfile_name, rfile_name)
            except IOError as e:
                self.__error(str(e))

    def complete_put(self, *args):
        files = [o for o in os.listdir(".") if os.path.isfile(os.path.join(".", o))]
        return [i for i in files if i.startswith(args[0])]

    def do_mput(self, args):
        """mput <SELECTION REGEX>
        Upload all local files that match the given regular expression.
        The remote files will be named the same as the local files.

        "mput" does not get directories, and it is not recursive.
        """

        if not len(args):
            self.__error("Missing argument: <SELECTION REGEX>")

        elif self.__is_open():

            try:
                self.fe.mput(os.getcwd(), args, True)
            except IOError as e:
                self.__error(str(e))

    def do_get(self, args):
        """get <REMOTE FILE> [<LOCAL FILE>]
        Download remote file. If the second parameter is given,
        its value is used for the local file name. Otherwise the
        locale file will be named the same as the remote file.
        """

        if not len(args):
            self.__error("Missing arguments: <REMOTE FILE> [<LOCAL FILE>]")

        elif self.__is_open():

            s_args = self.__parse_file_names(args)
            if not s_args:
                return
            elif len(s_args) > 2:
                self.__error("Only one ore two arguments allowed: <REMOTE FILE> [<LOCAL FILE>]")
                return

            rfile_name = s_args[0]

            if len(s_args) > 1:
                lfile_name = s_args[1]
            else:
                lfile_name = rfile_name

            try:
                self.fe.get(rfile_name, lfile_name)
            except IOError as e:
                self.__error(str(e))

    def do_mget(self, args):
        """mget <SELECTION REGEX>
        Download all remote files that match the given regular expression.
        The local files will be named the same as the remote files.

        "mget" does not get directories, and it is not recursive.
        """

        if not len(args):
            self.__error("Missing argument: <SELECTION REGEX>")

        elif self.__is_open():

            try:
                self.fe.mget(os.getcwd(), args, True)
            except IOError as e:
                self.__error(str(e))

    def complete_get(self, *args):

        try:
            files = self.fe.ls(add_dirs=False)
        except Exception:
            files = []

        return [i for i in files if i.startswith(args[0])]

    def do_rm(self, args):
        """rm <REMOTE FILE or DIR>
        Delete a remote file or directory.

        Note: only empty directories could be removed.
        """

        if not len(args):
            self.__error("Missing argument: <REMOTE FILE>")
        elif self.__is_open():

            s_args = self.__parse_file_names(args)
            if not s_args:
                return
            elif len(s_args) > 1:
                self.__error("Only one argument allowed: <REMOTE FILE>")
                return

            try:
                self.fe.rm(s_args[0])
            except IOError as e:
                self.__error(str(e))
            except PyboardError:
                self.__error("Unable to send request to %s" % self.fe.sysname)

    def do_mrm(self, args):
        """mrm <SELECTION REGEX>
        Delete all remote files that match the given regular expression.

        "mrm" does not delete directories, and it is not recursive.
        """

        if not len(args):
            self.__error("Missing argument: <SELECTION REGEX>")

        elif self.__is_open():

            try:
                self.fe.mrm(args, True)
            except IOError as e:
                self.__error(str(e))

    def complete_rm(self, *args):

        try:
            files = self.fe.ls()
        except Exception:
            files = []

        return [i for i in files if i.startswith(args[0])]

    def do_c(self, args):
        self.do_cat(args)

    def do_cat(self, args):
        """cat(c) <REMOTE FILE>
        Print the contents of a remote file.
        """

        if not len(args):
            self.__error("Missing argument: <REMOTE FILE>")
        elif self.__is_open():

            s_args = self.__parse_file_names(args)
            if not s_args:
                return
            elif len(s_args) > 1:
                self.__error("Only one argument allowed: <REMOTE FILE>")
                return

            try:
                print(self.fe.gets(s_args[0]))
            except IOError as e:
                self.__error(str(e))

    complete_cat = complete_get

    def do_rf(self, args):
        self.do_runfile(args)

    def do_runfile(self, args):
        """runfile(rf) <LOCAL FILE>
        download and running local file in board.
        """
        
        if not len(args):
            self.__error("Missing arguments: <LOCAL FILE>")

        elif self.__is_open():

            s_args = self.__parse_file_names(args)
            if not s_args:
                return
            elif len(s_args) > 1:
                self.__error("Only one ore one arguments allowed: <LOCAL FILE> ")
                return

            lfile_name = s_args[0]

            try:
                self.fe.put(lfile_name, lfile_name)
                self.do_ef(args)
            except IOError as e:
                self.__error(str(e))

    def do_ef(self, args):
        self.do_execfile(args)

    def do_execfile(self, args):
        """execfile(ef) <REMOTE FILE>
        Execute a Python filename on remote.
        """
        if self.__is_open():
            try:
                self.do_exec("execfile('%s')" % args)
                ret = self.fe.follow(2)
                if len(ret[-1]):
                    self.__error(str(ret[-1].decode('utf-8')))
            except KeyboardInterrupt as e:
                self.fe.keyboard_interrupt()
            except PyboardError as e:
                print(e)
            finally:
                if(self.open_args.startswith("ser:")):
                    self.__reconnect()
                if(self.__is_open()):
                    self.fe.enter_raw_repl()

    def do_lef(self, args):
        self.do_lexecfile(args)

    def do_lexecfile(self, args):
        """execfile(ef) <LOCAL FILE>
        Execute a Python filename on local.
        """
        if self.__is_open():

            s_args = self.__parse_file_names(args)
            if not s_args:
                return
            elif len(s_args) > 1:
                self.__error("Only one ore one arguments allowed: <LOCAL FILE> ")
                return

            lfile_name = s_args[0]

            try:
                self.fe.put(lfile_name, lfile_name)

                self.do_repl('execfile("{0}")\r\n'.format(args))

            except IOError as e:
                self.__error(str(e))

    def do_e(self, args):
        self.do_exec(args)

    def do_exec(self, args):
        """exec(e) <Python CODE>
        Execute a Python CODE on remote.
        """

        def data_consumer(data):
            data = str(data.decode('utf-8'))
            sys.stdout.write(data.strip("\x04"))

        if not len(args):
            self.__error("Missing argument: <Python CODE>")
        elif self.__is_open():

            try:
                self.fe.exec_raw_no_follow("print('Enter remote execution and stop using Ctrl+C.')\n"+ args + "\n")
                ret = self.fe.follow(None, data_consumer)
                
                if len(ret[-1]):
                    self.__error(str(ret[-1].decode('utf-8')))

            except IOError as e:
                self.__error(str(e))
            except PyboardError as e:
                self.__error(str(e))
            except Exception as e:
                self.__error(str(e))

    def do_r(self, args):
        self.do_repl(args)

    def do_repl(self, args):
        """repl(r)
        Enter Micropython REPL.
        """

        import serial

        ver = serial.VERSION.split(".")

        if int(ver[0]) < 2 or (int(ver[0]) == 2 and int(ver[1]) < 7):
            self.__error("REPL needs PySerial version >= 2.7, found %s" % serial.VERSION)
            return

        if self.__is_open():

            if self.repl is None:

                from mp.term import Term
                self.repl = Term(self.fe.con)

                if platform.system() == "Windows":
                    self.repl.exit_character = chr(0x11)
                else:
                    self.repl.exit_character = chr(0x1d)

                self.repl.raw = True
                self.repl.set_rx_encoding('UTF-8')
                self.repl.set_tx_encoding('UTF-8')

            else:
                self.repl.serial = self.fe.con

            self.fe.teardown()
            self.repl.start()

            if self.repl.exit_character == chr(0x11):
                print("\n*** Exit REPL with Ctrl+Q ***")
            else:
                print("\n*** Exit REPL with Ctrl+] ***")

            try:
                if args != None:
                    self.fe.con.write(bytes(args, encoding = "utf8"))
                self.repl.join(True)
            except Exception as e:
                # print(e)
                pass

            self.repl.console.cleanup()

            self.fe.setup()
            print("")

    def do_mpyc(self, args):
        """mpyc <LOCAL PYTHON FILE>
        Compile a Python file into byte-code by using mpy-cross (which needs to be in the path).
        The compiled file has the same name as the original file but with extension '.mpy'.
        """

        if not len(args):
            self.__error("Missing argument: <LOCAL FILE>")
        else:

            s_args = self.__parse_file_names(args)
            if not s_args:
                return
            elif len(s_args) > 1:
                self.__error("Only one argument allowed: <LOCAL FILE>")
                return

            try:
                self.fe.mpy_cross(s_args[0])
            except IOError as e:
                self.__error(str(e))

    def complete_mpyc(self, *args):
        files = [o for o in os.listdir(".") if (os.path.isfile(os.path.join(".", o)) and o.endswith(".py"))]
        return [i for i in files if i.startswith(args[0])]


def main():

    parser = argparse.ArgumentParser()
    parser.add_argument("-c", "--command", help="execute given commands (separated by ;)", default=None, nargs="*")
    parser.add_argument("-s", "--script", help="execute commands from file", default=None)
    parser.add_argument("-n", "--noninteractive", help="non interactive mode (don't enter shell)",
                        action="store_true", default=False)

    parser.add_argument("--nocolor", help="disable color", action="store_true", default=False)
    parser.add_argument("--nocache", help="disable cache", action="store_true", default=False)

    parser.add_argument("--logfile", help="write log to file", default=None)
    parser.add_argument("--loglevel", help="loglevel (CRITICAL, ERROR, WARNING, INFO, DEBUG)", default="INFO")

    parser.add_argument("--reset", help="hard reset device via DTR (serial connection only)", action="store_true",
                        default=False)
    
    parser.add_argument("-o", "--open", help="directly opens board", metavar="BOARD", action="store", default=None)
    parser.add_argument("board", help="directly opens board", nargs="?", action="store", default=None)
    

    args = parser.parse_args()

    format = '%(asctime)s\t%(levelname)s\t%(message)s'

    if args.logfile is not None:
        logging.basicConfig(format=format, filename=args.logfile,level=args.loglevel)
    else:
        logging.basicConfig(format=format, level=logging.CRITICAL)

    logging.info('Micropython File Shell v%s started' % version.FULL)
    logging.info('Running on Python %d.%d using PySerial %s' \
              % (sys.version_info[0], sys.version_info[1], serial.VERSION))

    mpfs = MpFileShell(not args.nocolor, not args.nocache, args.reset)
    
    if args.open is not None:
        if args.board is None:
            mpfs.do_open(args.open)
        else:
            print("Positional argument ({}) takes precedence over --open.".format(args.board))
    if args.board is not None:
        mpfs.do_open(args.board)
    

    if args.command is not None:

        for cmd in ' '.join(args.command).split(';'):
            scmd = cmd.strip()
            if len(scmd) > 0 and not scmd.startswith('#'):
                mpfs.onecmd(scmd)

    elif args.script is not None:

        f = open(args.script, 'r')
        script = ""

        for line in f:

            sline = line.strip()

            if len(sline) > 0 and not sline.startswith('#'):
                script += sline + '\n'

        if sys.version_info < (3, 0):
            sys.stdin = io.StringIO(script.decode('utf-8'))
        else:
            sys.stdin = io.StringIO(script)

        mpfs.intro = ''
        mpfs.prompt = ''

    if not args.noninteractive:

        try:
            mpfs.cmdloop()
        except KeyboardInterrupt:
            print("")


if __name__ == '__main__':

    main()
