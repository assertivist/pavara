from panda3d.core import *
from icebox.world import World
from icebox.network_twisted_udp import Server, Client
from icebox.input_manager import InputManager
from icebox.constants import *

class Clock (object):
    def __init__(self, showbase, is_client):
        #render = showbase.render
        self.time = 0
        self.is_client = is_client
        self.world = World(showbase, is_client)

        self.curr_blocks = 0

        taskMgr.add(self.update, 'ClockTask')
        if is_client:
            self.client = Client(self.world, '127.0.0.1', 23000)
            self.input_manager = InputManager(showbase, self.client.datagram_protocol)
            self.client.run() #blocks
        else:
            self.server = Server(self.world, 23000) #blocks

            
    def update(self, task):
        dt = globalClock.getDt()
        self.time += dt
        self.world.update(dt)
        return task.cont

