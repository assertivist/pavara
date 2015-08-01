import os
from panda3d.core import *
from pandac.PandaModules import WindowProperties
from direct.showbase import Audio3DManager
from direct.filter.CommonFilters import CommonFilters
from direct.interval.LerpInterval import *
from direct.interval.IntervalGlobal import *
from pavara.network import Server, Client
from pavara.constants import TCP_PORT
from pavara.maps import load_maps
from pavara.utils.geom import GeomBuilder
from pavara.local_player import LocalPlayer
from pavara.walker import Walker
from pavara.world import ClientWorld

# below globals needed because of a bug in librocket:
# the library expects these three variables set in the
# global scope of the class that holds callback methods
# http://www.panda3d.org/forums/viewtopic.php?f=4&t=16412
event = None
self = None
document = None

class Splash (object):
    def __init__(self, base, showbase, in_map):
        self.showbase = showbase
        self.win = showbase.win
        self.render = showbase.render
        self.base = base
        self.cam = showbase.cam
        self.camera = showbase.camera
        self.doc = False
        self.map = False
        self.audio3d = showbase.audio3d
        self.mouseWatcherNode = showbase.mouseWatcherNode

        if in_map:
            self.switch_map(in_map)
            self.start_map()
        else:
            self.switch_map("../Ui/scenes/splash.xml", audio=False)
            self.fade_in()
            incarn = self.map.world.get_incarn()
            self.map.world.attach(Walker(incarn))

    def fade_in(self):
        # blackout card
        bgeom = GeomBuilder().add_rect([0,0,0,1],-5,-5,0,5,5,0).get_geom_node()
        b = render.attach_new_node(bgeom)
        b.set_pos(self.cam.get_pos(render))
        b.set_hpr(self.cam.get_hpr(render))
        b_move_by = render.get_relative_vector(self.cam, Vec3(0,0,-2))
        b.set_pos(b, b_move_by)
        b.set_color(0,0,0)
        b.set_transparency(TransparencyAttrib.MAlpha)
        # fade from full opacity to no opacity
        cintv = LerpColorScaleInterval(b, 1.5, (1,1,1,0), (1,1,1,1))
        def _unhide_ui():
            b.detach_node()
        # show ui after lerp is finished
        showui = Func(_unhide_ui)
        Sequence(cintv,showui).start()

    def map_selected(self):
        in_map = event.current_element.GetAttribute("map")
        self.switch_map(in_map, show_info=True)
        return

    def switch_map(self, mapname, show_info=False, audio=True):
        if self.map:
            self.map.remove(self.render)
            del(self.map)
        if audio:
            w = ClientWorld(self.cam, debug=False, audio3d=self.audio3d)
            maps = load_maps('Maps/%s' % mapname, w)
        else:
            w = ClientWorld(self.cam, debug=False, audio3d=None)
            maps = load_maps('Maps/%s' % mapname, w)
        self.map = maps[0]
        self.map.show(self.render)
        self.camera.setPos(*self.map.preview_cam[0])
        self.camera.setH(self.map.preview_cam[1][0])
        self.camera.setP(self.map.preview_cam[1][1])
        if self.doc and show_info:
            title_e = self.doc.GetElementById('info_title')
            title_txt = title_e.first_child
            title_e.RemoveChild(title_txt)
            new_txt = self.map.name + " -- " + self.map.author
            new_txt = new_txt.encode('latin2', 'ignore')
            title_e.AppendChild(self.doc.CreateTextNode(new_txt))
            desc_e = self.doc.GetElementById('info_content')
            desc_txt = desc_e.first_child
            desc_e.RemoveChild(desc_txt)
            desc_e.AppendChild(self.doc.CreateTextNode(self.map.description.encode('latin2', 'ignore')))
            self.doc.GetElementById('info_box').style.display = 'block'
            self.doc.GetElementById('go').style.display = 'inline'
            self.doc.GetElementById('gametitle').style.display = 'none'

    def start_map(self):
        try:
            #self.r_region.setActive(0)
            self.ih_node.detach_node()
        except:
            # probably self.r_region isn't set because
            # we never loaded it (map arg on cmd line)
            pass
        self.lp = LocalPlayer(self.map, self.showbase)
        taskMgr.add(self.map.world.update, 'worldUpdateTask')
        props = WindowProperties()
        props.setCursorHidden(True)
        self.win.requestProperties(props)
        print self.render.analyze()

    def quit_clicked(self):
        exit()
