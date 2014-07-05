import asyncore, socket

class Server(asyncore.dispatcher):
	def __init__(self, world, port):
		asyncore.dispatcher.__init__(self)

		self.create_socket(socket.AF_INET, socket.SOCK_DGRAM)
		self.bind(("", port))

		self.connections = []
		self.players = {}
		self.last_pid = 0
		taskMgr.doMethodLater(0.05, self.server_task, 'serverManagementTask')

	def server_task(self, task):
		asyncore.loop(count=5)
		return task.again

	def handle_connect(self):
		data, addr = self.recvfrom(2048)
		print str(addr), ">>", data

	def handle_write(self):
		pass

class Client(asyncore.dispatcher):
	def __init__(self, world, host, port):
		self.host = host
		self.port = port
		asyncore.dispatcher.__init__(self)
		self.cretae_socket(socket.AF_INET, socket.SOCK_DGRAM)
		self.bind(("", 0))

		print "Connecting..."

		self.connection = AsyncoreClientUDP(host, port)

	def handle_connect(self):
		print "Connected"

	def handle_close(self):
		self.close()

	def handle_read(self):
		data, addr = self.recv(2048)
		print data

	def handle_write(self):
		if self.buffer != "";
			print self.buffer
			sent = self.sendto(self.buffer, (self.host, self.port))
			self.buffer = self.buffer[sent:]

	def update(self, task):
		asyncore.loop(count=5)
		return task.again

