#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Test BBMD
---------
"""

import unittest

from bacpypes.debugging import bacpypes_debugging, ModuleLogger, xtob

from bacpypes.pdu import Address, PDU, LocalBroadcast
from bacpypes.vlan import IPNetwork, IPRouter
from bacpypes.bvll import ReadForeignDeviceTable, ReadForeignDeviceTableAck

from ..state_machine import StateMachineGroup
from ..time_machine import reset_time_machine, run_time_machine

from .helpers import (
    SnifferStateMachine, BIPSimpleStateMachine,
    BIPForeignStateMachine, BIPBBMDStateMachine, BIPBBMDNode,
    )

# some debugging
_debug = 0
_log = ModuleLogger(globals())


#
#   TNetwork
#

@bacpypes_debugging
class TNetwork(StateMachineGroup):

    def __init__(self):
        if _debug: TNetwork._debug("__init__")
        StateMachineGroup.__init__(self)

        # reset the time machine
        reset_time_machine()
        if _debug: TNetwork._debug("    - time machine reset")

        # make a router
        self.router = IPRouter()

        # make a network
        self.vlan_7 = IPNetwork()
        self.router.add_network(Address("192.168.7.1/24"), self.vlan_7)

        # bbmd on network 7
        self.bbmd_7 = BIPBBMDStateMachine("192.168.7.3/24", self.vlan_7)
        self.bbmd_7.bip.add_peer(Address("192.168.8.3"))
        self.append(self.bbmd_7)

        # make a network
        self.vlan_8 = IPNetwork()
        self.router.add_network(Address("192.168.8.1/24"), self.vlan_8)

        # bbmd on network 8
        self.bbmd_8 = BIPBBMDNode("192.168.8.3/24", self.vlan_8)
        self.bbmd_8.bip.add_peer(Address("192.168.7.3"))

        # make a network
        self.vlan_9 = IPNetwork()
        self.router.add_network(Address("192.168.9.1/24"), self.vlan_9)

        # the foreign device
        self.fd_9 = BIPForeignStateMachine("192.168.9.2/24", self.vlan_9)
        self.append(self.fd_9)

    def run(self, time_limit=60.0):
        if _debug: TNetwork._debug("run %r", time_limit)

        # run the group
        super(TNetwork, self).run()

        # run it for some time
        run_time_machine(time_limit)
        if _debug: TNetwork._debug("    - time machine finished")

        # check for success
        all_success, some_failed = super(TNetwork, self).check_for_success()
        assert all_success


@bacpypes_debugging
class TestBBMD(unittest.TestCase):

    def test_idle(self):
        """Test an idle network, nothing happens is success."""
        if _debug: TestBBMD._debug("test_idle")

        # create a network
        tnet = TNetwork()

        # all start states are successful
        tnet.bbmd_7.start_state.success()
        tnet.fd_9.start_state.success()

        # run the group
        tnet.run()

