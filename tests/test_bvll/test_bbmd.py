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
from bacpypes.bvll import (
    Result,
    RegisterForeignDevice, ReadForeignDeviceTable, ReadForeignDeviceTableAck,
    DeleteForeignDeviceTableEntry, DistributeBroadcastToNetwork,
    ReadBroadcastDistributionTable, ReadBroadcastDistributionTableAck,
    )

from ..state_machine import StateMachineGroup, TrafficLog
from ..time_machine import reset_time_machine, run_time_machine

from .helpers import (
    SnifferStateMachine, BIPStateMachine, BIPSimpleStateMachine,
    BIPForeignStateMachine, BIPBBMDStateMachine,
    BIPSimpleNode, BIPBBMDNode,
    )

# some debugging
_debug = 0
_log = ModuleLogger(globals())


#
#   TNetwork1
#

@bacpypes_debugging
class TNetwork1(StateMachineGroup):

    def __init__(self):
        if _debug: TNetwork1._debug("__init__")
        StateMachineGroup.__init__(self)

        # reset the time machine
        reset_time_machine()
        if _debug: TNetwork1._debug("    - time machine reset")

        # create a traffic log
        self.traffic_log = TrafficLog()

        # make a network
        self.vlan_1 = IPNetwork("192.168.1.0/24")
        self.vlan_1.traffic_log = self.traffic_log

    def run(self, time_limit=60.0):
        if _debug: TNetwork1._debug("run %r", time_limit)

        # run the group
        super(TNetwork1, self).run()

        # run it for some time
        run_time_machine(time_limit)
        if _debug: TNetwork1._debug("    - time machine finished")

        # check for success
        all_success, some_failed = super(TNetwork1, self).check_for_success()
        if _debug:
            TNetwork1._debug("    - all_success, some_failed: %r, %r", all_success, some_failed)
            for state_machine in self.state_machines:
                if state_machine.running:
                    TNetwork1._debug("    %r (running)", state_machine)
                elif not state_machine.current_state:
                    TNetwork1._debug("    %r (not started)", state_machine)
                else:
                    TNetwork1._debug("    %r", state_machine)
                for direction, pdu in state_machine.transaction_log:
                    TNetwork1._debug("        %s %s", direction, str(pdu))

            # traffic log has what was processed on each vlan
            self.traffic_log.dump(TNetwork1._debug)

        assert all_success


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
        self.vlan_7 = IPNetwork("192.168.7.0/24")
        self.router.add_network(Address("192.168.7.1/24"), self.vlan_7)

        # bbmd on network 7
        self.bbmd_7 = BIPBBMDStateMachine("192.168.7.3/24", self.vlan_7)
        self.bbmd_7.bip.add_peer(Address("192.168.8.3"))
        self.append(self.bbmd_7)

        # make a network
        self.vlan_8 = IPNetwork("192.168.8.0/24")
        self.router.add_network(Address("192.168.8.1/24"), self.vlan_8)

        # bbmd on network 8
        self.bbmd_8 = BIPBBMDNode("192.168.8.3/24", self.vlan_8)
        self.bbmd_8.bip.add_peer(Address("192.168.7.3"))

        # make a network
        self.vlan_9 = IPNetwork("192.168.9.0/24")
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
class TestNonBBMD(unittest.TestCase):

    def test_read_bdt_fail(self):
        """Test reading a BDT."""
        if _debug: TestNonBBMD._debug("test_read_bdt_success")

        # create a network
        tnet = TNetwork1()

        # test device
        td = BIPStateMachine("192.168.1.2/24", tnet.vlan_1)
        tnet.append(td)

        # implementation under test
        iut = BIPSimpleNode("192.168.1.3/24", tnet.vlan_1)

        # read the broadcast distribution table, get a nack
        td.start_state.doc("1-1-0") \
            .send(ReadBroadcastDistributionTable(destination=iut.address)).doc("1-1-1") \
            .receive(Result, bvlciResultCode=0x0020).doc("1-1-2") \
            .success()

        # run the group
        tnet.run()

    def test_read_fdt_fail(self):
        """Test reading an FDT from a non-BBMD."""
        if _debug: TestNonBBMD._debug("test_read_fdt_success")

        # create a network
        tnet = TNetwork1()

        # test device
        td = BIPStateMachine("192.168.1.2/24", tnet.vlan_1)
        tnet.append(td)

        # implementation under test
        iut = BIPSimpleNode("192.168.1.3/24", tnet.vlan_1)

        # read the broadcast distribution table, get a nack
        td.start_state.doc("1-2-0") \
            .send(ReadForeignDeviceTable(destination=iut.address)).doc("1-2-1") \
            .receive(Result, bvlciResultCode=0x0040).doc("1-2-2") \
            .success()

        # run the group
        tnet.run()

    def test_register_fail(self):
        """Test registering as a foreign device to a non-BBMD."""
        if _debug: TestNonBBMD._debug("test_read_fdt_success")

        # create a network
        tnet = TNetwork1()

        # test device
        td = BIPStateMachine("192.168.1.2/24", tnet.vlan_1)
        tnet.append(td)

        # implementation under test
        iut = BIPSimpleNode("192.168.1.3/24", tnet.vlan_1)

        # read the broadcast distribution table, get a nack
        td.start_state.doc("1-3-0") \
            .send(RegisterForeignDevice(10, destination=iut.address)).doc("1-3-1") \
            .receive(Result, bvlciResultCode=0x0030).doc("1-3-2") \
            .success()

        # run the group
        tnet.run()

    def test_delete_fail(self):
        """Test deleting an FDT entry from a non-BBMD."""
        if _debug: TestNonBBMD._debug("test_delete_fail")

        # create a network
        tnet = TNetwork1()

        # test device
        td = BIPStateMachine("192.168.1.2/24", tnet.vlan_1)
        tnet.append(td)

        # implementation under test
        iut = BIPSimpleNode("192.168.1.3/24", tnet.vlan_1)

        # read the broadcast distribution table, get a nack
        td.start_state.doc("1-4-0") \
            .send(DeleteForeignDeviceTableEntry(Address("1.2.3.4"), destination=iut.address)).doc("1-4-1") \
            .receive(Result, bvlciResultCode=0x0050).doc("1-4-2") \
            .success()

        # run the group
        tnet.run()

    def test_distribute_fail(self):
        """Test asking a non-BBMD to distribute a broadcast."""
        if _debug: TestNonBBMD._debug("test_delete_fail")

        # create a network
        tnet = TNetwork1()

        # test device
        td = BIPStateMachine("192.168.1.2/24", tnet.vlan_1)
        tnet.append(td)

        # implementation under test
        iut = BIPSimpleNode("192.168.1.3/24", tnet.vlan_1)

        # read the broadcast distribution table, get a nack
        td.start_state.doc("1-4-0") \
            .send(DistributeBroadcastToNetwork(xtob('deadbeef'), destination=iut.address)).doc("1-4-1") \
            .receive(Result, bvlciResultCode=0x0060).doc("1-4-2") \
            .success()

        # run the group
        tnet.run()


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

    def test_read_bdt_success(self):
        """Test reading a BDT."""
        if _debug: TestBBMD._debug("test_read_bdt_success")

        # create a network
        tnet = TNetwork1()

        # test device
        td = BIPStateMachine("192.168.1.2/24", tnet.vlan_1)
        tnet.append(td)

        # implementation under test
        iut = BIPBBMDNode("192.168.1.3/24", tnet.vlan_1)

        # read the broadcast distribution table
        td.start_state.doc("2-1-0") \
            .send(ReadBroadcastDistributionTable(destination=iut.address)).doc("2-1-1") \
            .receive(ReadBroadcastDistributionTableAck).doc("2-1-2") \
            .success()

        # run the group
        tnet.run()

    def test_read_fdt_success(self):
        """Test reading a FDT."""
        if _debug: TestBBMD._debug("test_read_fdt_success")

        # create a network
        tnet = TNetwork1()

        # test device
        td = BIPStateMachine("192.168.1.2/24", tnet.vlan_1)
        tnet.append(td)

        # implementation under test
        iut = BIPBBMDNode("192.168.1.3/24", tnet.vlan_1)

        # read the broadcast distribution table
        td.start_state.doc("2-2-0") \
            .send(ReadForeignDeviceTable(destination=iut.address)).doc("2-2-1") \
            .receive(ReadForeignDeviceTableAck).doc("2-2-2") \
            .success()

        # run the group
        tnet.run()

