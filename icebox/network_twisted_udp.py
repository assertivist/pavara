from twisted.internet.protocol import DatagramProtocol
from twisted.internet.task import LoopingCall
from twisted.internet import reactor
from panda3d.core import *
from panda3d.core import ConfigVariableString
from pandac.PandaModules import *
from icebox.server_packet import ServerPacket
from icebox.constants import *
import sys
import signal, random

FPS = 60.0

class Player (object):
    def __init__(self, pid, tank, nick, team):
        self.pid = pid
        self.tank = tank
        self.nick = nick
        self.team = team

    def __repr__(self):
        return 'Player %s' % self.pid

    def handle_command(self, direction, pressed):
        #print 'PLAYER %s GOT CMD %s %s' % (self.pid, direction, pressed)
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
        self.red_team = []
        self.blue_team = []
        self.last_pid = 0
        self.last_txid = 0
        taskMgr.doMethodLater(0.03, self.server_task, 'serverManagementTask')

    def datagramReceived(self, data, addr):
        #print data, addr

        dgram = ServerPacket(values = data)
        if addr not in self.connections:
            print data, addr
            nick = dgram.get_string()
            self.add_player(addr, nick)
            return
        #receive input from client
        player = self.players[addr]
        command = dgram.get_string()
        if command == "WHOIS":
            self.lookup_player(dgram.get_string())
            return
        value = dgram.get_bool()
        player.handle_command(command, value)

    def add_player(self, addr, nick):
        self.connections.add(addr)
        self.last_pid += 1
        team = 'red'
        if len(self.blue_team) > len(self.red_team):
            self.red_team.append(self.last_pid)
        else:
            self.blue_team.append(self.last_pid)
            team = 'blue'
        pos = [random.randint(0,50), 1, random.randint(0,50)]
        angle = random.randint(0, 359)
        tank = self.world.add_tank(pos, angle)
        player = Player(self.last_pid, tank, nick, team)
        self.players[addr] = player
        self.send_new_player(nick, tank.name, team)

    def lookup_player(self, tank_name):
        for key, p in self.players.iteritems():
            if p.tank.name == tank_name:
                self.send_new_player(p.nick, p.tank.name, p.team)

    def server_task(self, task):
        moved = len([o for o in self.world.updatables if o.moved])
        if moved > 0:
            self.send_obj_update(moved)
        if self.world.display_updated:
            self.world.display_updated = False
            self.send_display_update(self.world.display)
        return task.again

    def new_packet(self):
        update = ServerPacket()
        self.last_txid += 1
        update.add_int(self.last_txid)
        return update

    def send_obj_update(self, moved):
        update = self.new_packet()
        update.add_int(ServerPacket().OBJ_UPDATE) # type
        update.add_int(moved) # number of objects updated
        for obj in self.world.updatables:
            obj.add_update(update)
        size = sys.getsizeof(update)
        if size > 1000:
            print "sending a big packet with size: ", size
        self.send_to_all(update)
        
    
    def send_new_player(self, name, obj_name, team):
        update = self.new_packet()
        update.add_int(ServerPacket().NEW_PLAYER)
        update.add_string(name)
        update.add_string(obj_name)
        update.add_string(team)
        self.send_to_all(update)

    def send_display_update(self, text):
        update = self.new_packet()
        update.add_int(ServerPacket().DISPLAY_TEXT)
        update.add_string(text)
        self.send_to_all(update)

    def send_to_all(self, update):
        for addr in self.connections:
            self.transport.write(update.get_datagram(), addr)

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

    def startProtocol(self):
        self.transport.connect(self.host, self.port)
        nick = ConfigVariableString('nick', 'SomeJerk').getValue()
        self.transport.write(nick+"^1")


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

        update_type = update.get_int()

        if update_type is ServerPacket().OBJ_UPDATE:
            self.obj_update(update)

        if update_type is ServerPacket().DISPLAY_TEXT:
            #print update.get_datagram()
            self.world.message_display.set_text(update.get_string())

        if update_type is ServerPacket().NEW_PLAYER:
            self.new_player(update)
        
    def obj_update(self, update):
        num_objects = update.get_int()

        for i in range(num_objects):
            name = update.get_string()

            does_rotate = not name.startswith('Projectile')
 
            x = update.get_float()
            y = update.get_float()
            z = update.get_float()
            
            if does_rotate:
                h = update.get_float()
                p = update.get_float()
                r = update.get_float()

            if name.startswith('Tank') and name not in self.world.objects:
                self.whois(name)
                #self.world.add_tank([0,0,0], 0, name = name)
            if name.startswith('Block') and name not in self.world.objects:
                self.world.add_block([0,0,0], name = name)
            if name.startswith('Projectile') and name not in self.world.objects:
                self.world.add_proj(GREEN_COLOR, [0, 0, 0], 0, 0, None, name = name)

            obj = self.world.objects.get(name)
            if obj:
                obj.move((x, y, z))
                if does_rotate:
                    obj.rotate((h, p, r))

    def new_player(self, update):
        print update.get_datagram()
        nick = update.get_string()
        obj_name = update.get_string()
        team = update.get_string()
        self.world.add_tank([0,0,0], 0, name = obj_name, nick = nick, team = team)

    def whois(self, name):
        whois_dgram = ServerPacket()
        whois_dgram.add_string('WHOIS')
        whois_dgram.add_string(name);
        self.transport.write(whois_dgram.get_datagram())


    def connectionRefused(self):
        print "Connection was refused"

    def client_task(self, task):

        return task.again
