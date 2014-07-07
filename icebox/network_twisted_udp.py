from twisted.internet.protocol import DatagramProtocol
from twisted.internet.task import LoopingCall
from twisted.internet import reactor
from panda3d.core import *
from pandac.PandaModules import *
from icebox.server_packet import ServerPacket
from icebox.constants import *

import signal, random

FPS = 60.0

class Player (object):
    def __init__(self, pid, tank):
        self.pid = pid
        self.tank = tank

    def __repr__(self):
        return 'Player %s' % self.pid

    def handle_command(self, direction, pressed):
        print 'PLAYER %s GOT CMD %s %s' % (self.pid, direction, pressed)
        self.tank.handle_command(direction, pressed)

class Server(object):
    def __init__(self, world, port):
        s = ServerDatagramProtocol(world)
        reactor.listenUDP(port, s)
        LoopingCall(taskMgr.step).start(1/FPS)
        reactor.run() #blocks

class ServerDatagramProtocol(DatagramProtocol):
    def __init__(self, world):
        self.world = world
        self.connections = set()
        self.players = {}
        self.last_pid = 0
        self.last_txid = 0
        taskMgr.doMethodLater(0.03, self.server_task, 'serverManagementTask')

    def datagramReceived(self, data, addr):
        print data, addr
        if addr not in self.connections:
            self.add_player(addr)
        #receive input from client
        player = self.players[addr]
        dgram = ServerPacket(values = data)
        command = dgram.get_string()
        value = dgram.get_bool()
        player.handle_command(command, value)

    def add_player(self, addr):
        self.connections.add(addr)
        self.last_pid += 1
        tank = self.world.add_tank([random.randint(0,50), 1, random.randint(0,50)], random.randint(0, 359))
        self.players[addr] = Player(self.last_pid, tank)


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
        self.datagram_protocol = ClientDatagramProtocol(world, host, port)
        LoopingCall(taskMgr.step).start(1/FPS)
        reactor.listenUDP(0, self.datagram_protocol)

    def run(self):
        reactor.run()

class ClientDatagramProtocol(DatagramProtocol):
    def __init__(self, world, host, port):
        self.world = world
        self.host = host
        self.port = port
        self.last_txid = 0
        #taskMgr.doMethodLater(0.001, self.client_task, 'clientUpdateTask')

    def startProtocol(self):
        self.transport.connect(self.host, self.port)
        self.transport.write("hello^1")


    def send(self, key, value):
        input_dgram = ServerPacket()
        input_dgram.add_string(key)
        input_dgram.add_bool(value)
        self.transport.write(input_dgram.get_datagram())

    def datagramReceived(self, data, addr):
        update = ServerPacket(values = data)
        #print data
        txid = update.get_int()
        if txid != self.last_txid+1:
            if self.last_txid == 0:
                print "First packet: ", txid
            else:
                print "Lost packets: ", self.last_txid, " -> ", txid
        self.last_txid = txid
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
                self.world.add_tank([0,0,0], 0, name = name)
            if name.startswith('Block') and name not in self.world.objects:
                self.world.add_block([0,0,0], name = name)
            if name.startswith('Projectile') and name not in self.world.objects:
                self.world.add_proj(GREEN_COLOR, [0, 0, 0], 0, 0, None, name = name)
            obj = self.world.objects.get(name)
            if obj:
                obj.move((x, y, z))
                obj.rotate((h, p, r))

    def connectionRefused(self):
        print "Connection was refused"

    def client_task(self, task):

        return task.again
