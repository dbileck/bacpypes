#!/usr/bin/python

"""
"""

from bacpypes.debugging import bacpypes_debugging, ModuleLogger
from bacpypes.consolelogging import ArgumentParser
from bacpypes.consolecmd import ConsoleCmd

from bacpypes.comm import Client, Server, Debug, bind
from bacpypes.core import run, enable_sleeping

# some debugging
_debug = 0
_log = ModuleLogger(globals())

# globals
this_console = None
this_switch = None

#
#    Switch
#

@bacpypes_debugging
class Switch(Client, Server):

    class TerminalWrapper(Client, Server):

        def __init__(self, switch, terminal):
            self.switch = switch
            self.terminal = terminal

            bind(self, terminal, self)

        def indication(self, *args, **kwargs):
            self.switch.request(*args, **kwargs)

        def confirmation(self, *args, **kwargs):
            self.switch.response(*args, **kwargs)

    def __init__(self, *terminals):
        if _debug: Switch._debug("__init__ %r", terminals)

        Client.__init__(self)
        Server.__init__(self)

        # wrap the terminals
        self.terminals = [Switch.TerminalWrapper(self, terminal) for terminal in terminals]
        self.current_terminal = 0

    def switch_terminal(self, indx):
        if (indx < 0) or (indx >= len(self.terminals)):
            raise IndexError("terminal index out of range")

        self.current_terminal = indx

    def indication(self, *args, **kwargs):
        """Downstream packet, send to current terminal."""
        self.terminals[self.current_terminal].terminal.indication(*args, **kwargs)

    def confirmation(self, *args, **kwargs):
        """Upstream packet, send to current terminal."""
        self.terminals[self.current_terminal].terminal.confirmation(*args, **kwargs)

#
#   TestConsoleCmd
#

@bacpypes_debugging
class TestConsoleCmd(Client, Server, ConsoleCmd):

    def __init__(self):
        Client.__init__(self)
        Server.__init__(self)
        ConsoleCmd.__init__(self)

    def do_request(self, args):
        """request <msg>"""
        args = args.split()
        if _debug: TestConsoleCmd._debug("do_request %r", args)

        # send the request down the stack
        self.request(args[0])

    def do_response(self, args):
        """response <msg>"""
        args = args.split()
        if _debug: TestConsoleCmd._debug("do_response %r", args)

        # send the response up the stack
        self.response(args[0])

    def do_switch(self, args):
        """switch <arg>"""
        args = args.split()
        if _debug: TestConsoleCmd._debug("do_switch %r", args)
        global this_switch

        this_switch.switch_terminal(int(args[0]))
        print("switched")

    def indication(self, arg):
        """Got a request, echo it back up the stack."""
        print("indication: {}".format(arg))

    def confirmation(self, arg):
        print("confirmation: {}".format(arg))

#
#   main
#

@bacpypes_debugging
def main():
    # parse the command line arguments
    args = ArgumentParser(description=__doc__).parse_args()
    global this_switch, this_console

    if _debug: _log.debug("initialization")
    if _debug: _log.debug("    - args: %r", args)

    # make some debugging terminals
    debug1 = Debug("1")
    debug2 = Debug("2")

    # make a switch with them
    this_switch = Switch(debug1, debug2)
    if _debug: _log.debug("    this_switch: %r", this_switch)

    # make a test console
    this_console = TestConsoleCmd()
    if _debug: _log.debug("    this_console: %r", this_console)

    # bind the console to the top and bottom of the switch
    bind(this_console, this_switch, this_console)

    # enable sleeping will help with threads
    enable_sleeping()

    _log.debug("running")

    run()

    _log.debug("fini")

if __name__ == "__main__":
    main()

