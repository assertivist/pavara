from twisted.internet.protocol import DatagramProtocol
from twisted.internet.task import LoopingCall
from twisted.internet import reactor
from panda3d.core import *
from pandac.PandaModules import *
from icebox.server_packet import ServerPacket

import signal

def die(signal, frame):
    reactor.stop()
    exit()
signal.signal(signal.SIGINT, die)

FPS = 60.0

class Server(object):
    def __init__(self, world, port):
        s = ServerDatagramProtocol(world)
        reactor.listenUDP(port, s)
        LoopingCall(taskMgr.step).start(1/FPS)
        reactor.run() #blocks

class ServerDatagramProtocol(DatagramProtocol):
    def __init__(self, world):
        self.world = world
        #DatagramProtocol.__init__(self)
        self.connections = set()
        self.last_pid = 0
        self.last_txid = 0
        taskMgr.doMethodLater(0.03, self.server_task, 'serverManagementTask')

    def datagramReceived(self, data, addr):
        print data, addr
        if addr not in self.connections:
            self.connections.add(addr)

    def server_task(self, task):
        update = ServerPacket()
        self.last_txid += 1
        update.add_int(self.last_txid)
        update.add_int(len([o for o in self.world.updatables if o.moved]))
        for obj in self.world.updatables:
            obj.add_update(update)

        for addr in self.connections:
            self.transport.write(update.get_datagram(), addr)
        return task.again


class Client(object):
    def __init__(self, world, host, port):
        c = ClientDatagramProtocol(world, host, port)
        LoopingCall(taskMgr.step).start(1/FPS)
        reactor.listenUDP(0, c)
        reactor.run()

class ClientDatagramProtocol(DatagramProtocol):
    def __init__(self, world, host, port):
        #DatagramProtocol.__init__(self)
        self.world = world
        self.host = host
        self.port = port
        #taskMgr.doMethodLater(0.001, self.client_task, 'clientUpdateTask')

    def startProtocol(self):
        self.transport.connect(self.host, self.port)
        self.transport.write("hello")

    def datagramReceived(self, data, addr):
        update = ServerPacket(values = data)

        txid = update.get_int()
        print txid
        num_objects = update.get_int()

        for i in range(num_objects):
            name = update.get_string()
            x = update.get_float()
            y = update.get_float()
            z = update.get_float()
            h = update.get_float()
            p = update.get_float()
            r = update.get_float()
            if name.startswith('Tank') and name not in self.world.objects:
                self.world.add_tank([0,0,0], name=name)
            if name.startswith('Block') and name not in self.world.objects:
                self.world.add_block([0,0,0], name=name)
            obj = self.world.objects.get(name)
            if obj:
                obj.move((x, y, z))
                obj.rotate((h, p, r))

    def connectionRefused(self):
        print "Connection was refused"

    def client_task(self):

        return task.again
