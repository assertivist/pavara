import struct

FLAG_NEEDS_ACK = 0x0001


class Packet(object):
	HEADER_FORMAT = '!BHL'

	def __init__(self):

		pass
	def flatten(self):
		pass

KIND_PLAYER_JOINED = 0xA1
KIND_GAME_STARTED = 0xA2
KIND_PLAYER_UPDATE = 0xA3
KIND_WORLD_UPDATE = 0xA3
KIND_PROJECTILE_SPAWN = 0xA4
KIND_PROJECTILE_HIT = 0xA5

class ServerPacket(Packet):
	pass

KIND_PLAYER_JOIN = 0x01
KIND_LOAD_MAP = 0x02
KIND_GAME_START = 0x03

class ClientPacket(Packet):
	pass