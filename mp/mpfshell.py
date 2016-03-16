#!/usr/bin/env python

"""
2016-03-16, sw@kaltpost.de

Simple file shell for Micropython.

For usage details see the README.md
"""

import cmd
import os
import sys
import pyboard


class MpFileShell(cmd.Cmd):

    intro = '\n** Micropython File Shell v0.1, 2016 sw@kaltpost.de **\n'
    prompt = 'mpfs> '

    def __init__(self):

        cmd.Cmd.__init__(self)
        self.pb = None

    def __del__(self):

        self.__disconnect()

    def __error(self, msg):

        sys.stderr.write("\n" + msg + "\n\n")

    def __connect(self, port):

        try:
            self.__disconnect()
            self.pb = pyboard.Pyboard(port)
            self.pb.enter_raw_repl()
            self.pb.exec_("import os, sys")
        except pyboard.PyboardError:
            self.__error("Error while executing command on device")

    def __disconnect(self):

        if self.pb is not None:
            try:
                self.pb.exit_raw_repl()
                self.pb.close()
                self.pb = None
            except pyboard.PyboardError:
                self.__error("Error while executing command on device")

    def __is_open(self):

        if self.pb is None:
            self.__error("Not connected to device. Use 'open' first.")
            return False

        return True

    def do_exit(self, args):
        """exit
        Exit this shell.
        """

        return True

    def do_open(self, args):
        """open <PORT>
        Open connection to device with given serial port.
        """

        if not len(args):
            self.__error("Missing argument: <PORT>")
        else:
            self.__connect(args)

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
                files = eval(self.pb.eval("os.listdir('')"))

                print("\nRemote files:\n")

                for f in files:
                    print(" %s" % f)

                print("")

            except pyboard.PyboardError:
                self.__error("Error while executing command on device")

    def do_lls(self, args):
        """lls
        List files in current local directory.
        """

        files = os.listdir(".")

        print("\nLocal files:\n")

        for f in files:
            print(" %s" % f)

        print("")

    def do_lcd(self, args):
        """lcd <TARGET DIR>
        Change current local directory to given target.
        """

        if not len(args):
            self.__error("Missing argument: <TARGET DIR>")
        else:
            try:
                os.chdir(args)
            except OSError as e:
                self.__error(str(e).split("] ")[-1])

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
            s_args = args.split(" ")

            lfile_name = s_args[0]

            if len(s_args) > 1:
                rfile_name = s_args[1]
            else:
                rfile_name = lfile_name

            try:
                lfile = open(lfile_name, "r")
                lines = lfile.readlines()
                lfile.close()

                files = eval(self.pb.eval("os.listdir('')"))

                if rfile_name in files:
                    # remove the remote file first if it is already there
                    self.pb.eval("os.remove('%s')" % rfile_name)

                self.pb.exec_("f = open('%s', 'w')" % rfile_name)

                for l in lines:
                    sline = l.strip()

                    if sline != "":
                        # print("f.write('%s')" % l.encode("string-escape"))
                        self.pb.exec_("f.write('%s')" % l.encode("string-escape"))

                self.pb.exec_("f.close()")

            except pyboard.PyboardError:
                self.__error("Error while executing command on device")
            except IOError as e:
                self.__error(str(e).split("] ")[-1])

    def do_get(self, args):
        """get <REMOTE FILE> [<LOCAL FILE>]
        Download remote file. If the second parameter is given,
        its value is used for the local file name. Otherwise the
        locale file will be named the same as the remote file.
        """

        if not len(args):
            self.__error("Missing arguments: <REMOTE FILE> [<LOCAL FILE>]")
        elif self.__is_open():

            s_args = args.split(" ")

            rfile_name = s_args[0]

            if len(s_args) > 1:
                lfile_name = s_args[1]
            else:
                lfile_name = rfile_name

            try:
                files = eval(self.pb.eval("os.listdir('')"))

                if rfile_name not in files:
                    self.__error("File not found on remote: %s " % args)
                    return

                lfile = open(lfile_name, "w")

                self.pb.exec_("f = open('%s', 'r')" % rfile_name)
                ret = self.pb.exec_("for l in f: sys.stdout.write(l),")

                lfile.write(ret)
                lfile.close()

            except pyboard.PyboardError:
                self.__error("Error while executing command on device")
            except IOError as e:
                self.__error(str(e).split("] ")[-1])

    def do_rm(self, args):
        """rm <REMOTE FILE>
        Delete a remote file.
        """

        if not len(args):
            self.__error("Missing argument: <REMOTE FILE>")
        elif self.__is_open():

            try:
                files = eval(self.pb.eval("os.listdir('')"))

                if args in files:
                    self.pb.eval("os.remove('%s')" % args)
                else:
                    self.__error("File not found on remote: %s " % args)

            except pyboard.PyboardError:
                self.__error("Error while executing command on device")


if __name__ == '__main__':
    mpfs = MpFileShell()
    mpfs.cmdloop()
