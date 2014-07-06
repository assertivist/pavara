from panda3d.core import *
from icebox.clock import Clock
from direct.showbase.ShowBase import ShowBase

class Icebox_Server(ShowBase):
    def __init__(self):
        ShowBase.__init__(self)
        c = Clock(self, False)

if __name__ == '__main__':
    loadPrcFile('icebox_server.prc')
    i = Icebox_Server()
    i.run()