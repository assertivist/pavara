from twisted.internet.protocol import DatagramProtocol
from twisted.internet.task import LoopingCall
from twisted.internet import reactor
from panda3d.core import *
from panda3d.core import ConfigVariableString
from pandac.PandaModules import *
from pavara.packets import ServerPacket, ClientPacket
from pavara.constants import *
import sys
import signal, random

FPS = 60.0

class Player (object):
	def __init__(self, server, address, pid, name):
		self.server = server
		self.address = address
		self.pid = pid
		self.name = name
		self.last_seq = 0
		self.pending = {}
		self.received = []

	def send(self, packet, transport):
		transport.send(packet.flatten())

	def __repr__(self):
		return 'Player<%s:%s>' % (self.name, self.pid)


class Server(object):
	def __init__(self, port):
		s = ServerDatagramProtocol()
		reactor.listenUDP(port, s)
		LoopingCall(taskMgr.step).start(1/FPS)
		reactor.run() #blocks

class ServerDatagramProtocol(DatagramProtocol):
	def __init__(self):
		#self.world = world
		self.connections = set()
		self.players = {}

		self.last_pid = 0
		self.last_txid = 0

		self.updates = []

		taskMgr.doMethodLater(.03, self.server_task, 'server_task')

	@property
	def next_pid(self):
		self.last_pid += 1
		return self.last_pid

	@property
	def next_txid(self):
		self.last_txid += 1
		return self.last_txid

	def datagramReceived(self, data, addr):
		if addr not in self.connections:
			name = get_join_packet(data)
			if name:
				self.add_player(addr, name)
			return
		else:
			pass

	def add_player(self, addr, name):
		print "Player '%s' joined from" % name, addr
		p = Player(self, addr, self.next_pid, name)
		self.players[addr] = p

	def server_task(self, task):

		for u in self.updates:
			self.send_update(u);

		return task.again

	def send_update(self, packet):
		self.send_to_all(packet)

	def send_to_all(self, packet):
		for player in self.players:
			player.send(packet, self.transport)

class Client(object):
	def __init__(self, host, port):
		self.datagram_protocol = ClientDatagramProtocol(host,port)
		LoopingCall(taskMgr.step).start(1/FPS)
		reactor.listenUDP(0, self.datagram_protocol)

		taskMgr.doMethodLater(.03, self.datagram_protocol.client_task, 'client_task')


	def run(self):
		reactor.run()

class ClientDatagramProtocol(DatagramProtocol):
	def __init__(self, host, port):
		self.host = host
		self.port = port
		self.last_txid = 0

	@property
	def next_txid(self):
		self.last_txid += 1
	    return self.last_txid

	def startProtocol(self):
		self.transport.connect(self.host, self.port)
		nick = ConfigVariableString('nick', 'Some Jerk').getValue()
		self.join_server(nick)

	def datagram_received(self, data, addr):
		p = parse_packet(data)

		if p.kind == KIND_PLAYER_JOINED:
			pass
		if p.kind == KIND_GAME_STARTED:
			pass
		if p.kind == KIND_PLAYER_UPDATE:
			pass
		if p.kind == KIND_WORLD_UPDATE:
			pass
		if p.kind == KIND_PROJECTILE_SPAWN:
			pass
		if p.kind == KIND_PROJECTILE_HIT:
			pass

	def join_server(self, nick):
		self.transport.write(join_packet(nick))

	def send_input(self):
		pass

	def send_chat_chars(self, chars):
		self.transport.write(chat_packet(chars))

	def client_task(self, task):

		return task.again