
import asyncore, socket
from panda3d.core import *
from pandac.PandaModules import *
from icebox.server_packet import ServerPacket
class Server(asyncore.dispatcher):
    def __init__(self, world, port):
        asyncore.dispatcher.__init__(self)

        self.create_socket(socket.AF_INET, socket.SOCK_DGRAM)
        #self.set_reuse_addr()
        self.bind(("127.0.0.1", port))
        self.address = self.socket.getsockname()
        #self.listen(5)
        print self.address
        self.world = world

        self.connections = set()
        self.connections_to_remove = []
        self.players = {}   

        self.last_pid = 0
        self.last_txid = 0
        taskMgr.doMethodLater(0.03, self.server_task, 'serverManagementTask')
        print 'server up'
        self.buffer = ""

    def server_task(self, task):
        update = ServerPacket()
        self.last_txid += 1
        update.add_int(self.last_txid)
        update.add_int(len([o for o in self.world.updatables if o.moved]))
        for obj in self.world.updatables:
            obj.add_update(update)

        for conn in self.connections:
            try:
                self.sendto(update.get_datagram(), conn)
            except:
                raise
                self.connections_to_remove.append(conn)

        for conn in self.connections_to_remove:
            self.connections.remove(conn)
        self.connections_to_remove = []

        asyncore.loop(count = 1, timeout = 0)
        return task.again

    def handle_read(self):
        try:
            data, addr = self.recvfrom(2048)
            print data
            if addr not in self.connections:
                self.connections.add(addr)
        except Exception:
            """Windows throws many exceptions when 
            attempting to recvfrom a connection that has 
            closed. I am not sure how to close the 
            connection without closing the whole socket
            which isn't necessary afaict"""
            pass 

    def handle_close(self):
        return


class ServerHandler(asyncore.dispatcher_with_send):

    def handle_read(self):
        print data
        data, addr = self.recvfrom(2048)
        if(addr not in self.server.connections):
            self.server.connections.add(addr)


class Client(asyncore.dispatcher_with_send):
    def __init__(self, world, host, port):
        self.host = host
        self.port = port
        self.world = world
        asyncore.dispatcher.__init__(self)
        self.create_socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.bind(("", 0))
        
        self.out_buffer = "hello"
        print "Connecting..."
        self.connect((self.host, self.port))
        taskMgr.doMethodLater(0.001, self.client_task, 'clientUpdateTask')

    def handle_connect(self):
        print "Connected"

    def handle_close(self):
        self.close()

    def handle_read(self):
        data = self.recv(2048)

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
        #print data

    def handle_write(self):
        if self.out_buffer != "":
            print self.out_buffer
            sent = self.sendto(self.out_buffer, (self.host, self.port))
            self.out_buffer = self.out_buffer[sent:]
            print sent

    def client_task(self, task):
        asyncore.loop(count = 1, timeout = 0)
        return task.again


