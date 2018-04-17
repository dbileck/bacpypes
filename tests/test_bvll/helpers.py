#!/usr/bin/env python

"""
B/IP VLAN Helper Classes
"""

from bacpypes.debugging import bacpypes_debugging, ModuleLogger

from bacpypes.comm import Client, Server, bind
from bacpypes.pdu import Address, LocalBroadcast, PDU, unpack_ip_addr
from bacpypes.vlan import IPNode

from ..state_machine import ClientStateMachine

from bacpypes.bvllservice import BIPSimple, BIPForeign, BIPBBMD, AnnexJCodec


# some debugging
_debug = 0
_log = ModuleLogger(globals())

#
#   FauxMultiplexer
#

@bacpypes_debugging
class FauxMultiplexer(Client, Server):

    """This class is a placeholder for UDPMultiplexer without the code that
    determines if the upstream packets are Annex-H or Annex-J packets, it
    assumes they are all Annex-J.  It creates and binds itself to an IPNode
    which is added to an IPNetwork.
    """

    def __init__(self, addr, network=None, cid=None, sid=None):
        if _debug: FauxMultiplexer._debug("__init__")

        Client.__init__(self, cid)
        Server.__init__(self, sid)

        # allow the address to be cast
        if isinstance(addr, Address):
            self.address = addr
        else:
            self.address = Address(addr)

        # get the unicast and broadcast tuples
        self.unicast_tuple = addr.addrTuple
        self.broadcast_tuple = addr.addrBroadcastTuple

        # make an internal node and bind to it, this takes the place of
        # both the direct port and broadcast port of the real UDPMultiplexer
        self.node = IPNode(addr, network)
        bind(self, self.node)

    def indication(self, pdu):
        if _debug: FauxMultiplexer._debug("indication %r", pdu)

        # check for a broadcast message
        if pdu.pduDestination.addrType == Address.localBroadcastAddr:
            dest = self.broadcast_tuple
            if _debug: FauxMultiplexer._debug("    - requesting local broadcast: %r", dest)

        elif pdu.pduDestination.addrType == Address.localStationAddr:
            dest = unpack_ip_addr(pdu.pduDestination.addrAddr)
            if _debug: FauxMultiplexer._debug("    - requesting local station: %r", dest)

        else:
            raise RuntimeError("invalid destination address type")

        # continue downstream
        self.request(PDU(pdu, source=self.unicast_tuple, destination=dest))

    def confirmation(self, pdu):
        if _debug: FauxMultiplexer._debug("confirmation %r", pdu)

        # the PDU source and destination are tuples, convert them to Address instances
        src = Address(pdu.pduSource)

        # see if the destination was our broadcast address
        if pdu.pduDestination == self.broadcast_tuple:
            dest = LocalBroadcast()
        else:
            dest = Address(pdu.pduDestination)

        # continue upstream
        self.response(PDU(pdu, source=src, destination=dest))

#
#   SnifferStateMachine
#

@bacpypes_debugging
class SnifferStateMachine(ClientStateMachine):

    """This class acts as a sniffer for BVLL messages.  The client state
    machine sits above an Annex-J codec so the send and receive PDUs are
    BVLL PDUs.
    """

    def __init__(self, address, vlan):
        if _debug: SnifferStateMachine._debug("__init__ %r %r", address, vlan)
        ClientStateMachine.__init__(self)

        # save the name and address
        self.name = address
        self.address = Address(address)

        # BACnet/IP interpreter
        self.annexj = AnnexJCodec()

        # fake multiplexer has a VLAN node in it
        self.mux = FauxMultiplexer(self.address, vlan)

        # might receive all packets and allow spoofing
        self.mux.node.promiscuous = True
        self.mux.node.spoofing = True

        # bind the stack together
        bind(self, self.annexj, self.mux)


#
#   BIPStateMachine
#

@bacpypes_debugging
class BIPStateMachine(ClientStateMachine):

    """This class is an application layer for BVLL messages that has no BVLL
    processing like the 'simple', 'foreign', or 'bbmd' versions.  The client
    state machine sits above and Annex-J codec so the send and receive PDUs are
    BVLL PDUs.
    """

    def __init__(self, address, vlan):
        if _debug: BIPStateMachine._debug("__init__ %r %r", address, vlan)
        ClientStateMachine.__init__(self)

        # save the name and address
        self.name = address
        self.address = Address(address)

        # BACnet/IP interpreter
        self.annexj = AnnexJCodec()

        # fake multiplexer has a VLAN node in it
        self.mux = FauxMultiplexer(self.address, vlan)

        # bind the stack together
        bind(self, self.annexj, self.mux)


#
#   BIPSimpleStateMachine
#

@bacpypes_debugging
class BIPSimpleStateMachine(ClientStateMachine):

    """This class sits on a BIPSimple instance, the send() and receive()
    parameters are NPDUs.
    """

    def __init__(self, address, vlan):
        if _debug: BIPSimpleStateMachine._debug("__init__ %r %r", address, vlan)
        ClientStateMachine.__init__(self)

        # save the name and address
        self.name = address
        self.address = Address(address)

        # BACnet/IP interpreter
        self.bip = BIPSimple()
        self.annexj = AnnexJCodec()

        # fake multiplexer has a VLAN node in it
        self.mux = FauxMultiplexer(self.address, vlan)

        # bind the stack together
        bind(self, self.bip, self.annexj, self.mux)


#
#   BIPForeignStateMachine
#

@bacpypes_debugging
class BIPForeignStateMachine(ClientStateMachine):

    """This class sits on a BIPForeign instance, the send() and receive()
    parameters are NPDUs.
    """

    def __init__(self, address, vlan):
        if _debug: BIPForeignStateMachine._debug("__init__ %r %r", address, vlan)
        ClientStateMachine.__init__(self)

        # save the name and address
        self.name = address
        self.address = Address(address)

        # BACnet/IP interpreter
        self.bip = BIPForeign()
        self.annexj = AnnexJCodec()

        # fake multiplexer has a VLAN node in it
        self.mux = FauxMultiplexer(self.address, vlan)

        # bind the stack together
        bind(self, self.bip, self.annexj, self.mux)

#
#   BIPBBMDStateMachine
#

@bacpypes_debugging
class BIPBBMDStateMachine(ClientStateMachine):

    """This class sits on a BIPBBMD instance, the send() and receive()
    parameters are NPDUs.
    """

    def __init__(self, address, vlan):
        if _debug: BIPBBMDStateMachine._debug("__init__ %r %r", address, vlan)
        ClientStateMachine.__init__(self)

        # save the name and address
        self.name = address
        self.address = Address(address)

        # BACnet/IP interpreter
        self.bip = BIPBBMD(self.address)
        self.annexj = AnnexJCodec()

        # build an address, full mask
        bdt_address = "%s/32:%d" % self.address.addrTuple
        if _debug: BIPBBMDStateMachine._debug("    - bdt_address: %r", bdt_address)

        # add itself as the first entry in the BDT
        self.bip.add_peer(Address(bdt_address))

        # fake multiplexer has a VLAN node in it
        self.mux = FauxMultiplexer(self.address, vlan)

        # bind the stack together
        bind(self, self.bip, self.annexj, self.mux)

#
#   BIPBBMDNode
#

@bacpypes_debugging
class BIPBBMDNode:

    """This class is a BIPBBMD instance that is not bound to a state machine."""

    def __init__(self, address, vlan):
        if _debug: BIPBBMDNode._debug("__init__ %r %r", address, vlan)

        # save the name and address
        self.name = address
        self.address = Address(address)

        # BACnet/IP interpreter
        self.bip = BIPBBMD(self.address)
        self.annexj = AnnexJCodec()

        # build an address, full mask
        bdt_address = "%s/32:%d" % self.address.addrTuple
        if _debug: BIPBBMDNode._debug("    - bdt_address: %r", bdt_address)

        # add itself as the first entry in the BDT
        self.bip.add_peer(Address(bdt_address))

        # fake multiplexer has a VLAN node in it
        self.mux = FauxMultiplexer(self.address, vlan)

        # bind the stack together
        bind(self.bip, self.annexj, self.mux)


