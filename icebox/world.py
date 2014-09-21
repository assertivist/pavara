from icebox.objects import Arena, Block, Tank, Projectile
from icebox.constants import *
from icebox.script import Script
from panda3d.core import VBase4, AmbientLight, NodePath, TextNode
from panda3d.core import ColorAttrib, DirectionalLight, Vec4, Vec3
from panda3d.bullet import BulletWorld, BulletPlaneShape, BulletRigidBodyNode, BulletGhostNode, BulletDebugNode
from direct.gui.OnscreenText import OnscreenText

class Message_Display(object):
    def __init__(self):
        self.prev_text_to_display = ""
        self.text_to_display = ""
        self.has_changed = False
        self.text_options = dict(text = 'hello', pos = (-.9, .9), scale = 0.07, mayChange = True, fg=(1,1,1,1), bg=(0,0,0,1))
        self.text_object = OnscreenText(**self.text_options)

    def update(self, dt):
        if self.prev_text_to_display == self.text_to_display:
            self.has_changed = False
        else:
            self.has_changed = True
            print self.text_to_display
            self.text_object.destroy()
            self.text_object = OnscreenText(**self.text_options)
            self.text_object.setText(self.text_to_display)
            self.prev_text_to_display = self.text_to_display

    def set_text(self, text):
        self.text_to_display = text

class World (object):
    def __init__(self, showbase, is_client):
        self.is_client = is_client
        self.objects = {}
        self.updatables = set()
        self.render = showbase.render
        self.cam = showbase.cam
        self.curr_blocks = 0
        self.time_since_last_block = 0
        self.bullet_world = BulletWorld()

        self.message_display = Message_Display()

        if is_client:
            self.init_visual()
        
        self.bullet_world.setGravity(Vec3(0, -9.81, 0))

        self.updatables_to_add = {}
        self.updatables_to_remove = {}

        self.arena = Arena('ground')
        self.attach(self.arena)
        self.arena.np.set_pos(0,0,0)

        if not is_client:
            self.display = ""
            self.previous_display = ""
            self.display_updated = False

            self.red_goal = self.arena.red_goal
            self.blue_goal = self.arena.blue_goal
            self.red_goal_np = self.render.attach_new_node(self.red_goal)
            self.bullet_world.attach_ghost(self.red_goal)
            self.blue_goal_np = self.render.attach_new_node(self.blue_goal)
            self.bullet_world.attach_ghost(self.blue_goal)
            self.red_goal_np.set_pos(0, 0, -ARENA_SIZE/4.0)
            self.blue_goal_np.set_pos(0, 0, ARENA_SIZE/4.0)

            self.script = Script(self)
        

    def attach(self, obj):
        assert(obj.name not in self.objects)
        self.objects[obj.name] = obj
        obj.np = self.render.attach_new_node(obj.node)
        if isinstance(obj.node, BulletRigidBodyNode):
            if self.is_client:
                obj.node.set_mass(0.0)
            self.bullet_world.attach_rigid_body(obj.node)
        if isinstance(obj.node, BulletGhostNode):
            self.bullet_world.attach_ghost(obj.node)
        if self.is_client:
            if hasattr(obj, 'text'):
                text = TextNode(obj.name+'text')
                text.set_text(obj.text)
                text.setTextColor(1, .3, .3, 1)
                text.setShadow(0.05, 0.05)
                text.setShadowColor(0, 0, 0, 1)
                textNodePath = obj.np.attach_new_node(text)
                textNodePath.setScale(1.6)
                textNodePath.set_pos(0, 2.3, 0)
                obj.text_node_path = textNodePath
                print obj.text
            NodePath(obj.geom).reparent_to(obj.np)
        obj.world = self
        obj.attached = True

    def add_block(self, pos, name = None):
        self.curr_blocks += 1
        block = Block(name)
        self.attach(block)
        self.updatables.add(block) 
        block.move(pos)

    def add_tank(self, pos, rot, name = None, nick = None, team = None):
        tank = None
        if team == 'blue':
            tank = Tank(BLUE_COLOR, name, nick)
        else:
            tank = Tank(RED_COLOR, name, nick)
        self.attach(tank)
        self.updatables.add(tank)
        tank.move(pos)
        tank.rotate([rot, 0, 0])
        return tank

    def add_proj(self, color, pos, rot, speed_pitch, owner, name = None):
        proj = Projectile(color, name = name)
        self.attach(proj)
        self.updatables_to_add[proj.name] = proj
        proj.move(pos)
        proj.rotate([rot, 0, 0])

    def init_visual(self):
        alight = AmbientLight('ambient')
        alight.set_color(VBase4(0.6, 0.6, 0.6, 1))
        node = self.render.attach_new_node(alight)
        self.render.set_light(node)

        directional_light = DirectionalLight('directionalLight')
        directional_light.set_color(Vec4(0.7, 0.7, 0.7, 1))
        directional_light_np = self.render.attach_new_node(directional_light)
        directional_light_np.set_hpr(0, -80, 0)
        self.render.set_light(directional_light_np)
        self.render.setColorOff()
        self.render.setShaderAuto()
        self.render.node().setAttrib(ColorAttrib.makeVertex())

        self.message = Message_Display()

        if DEBUG:
            debug_node = BulletDebugNode('Debug')
            debug_node.showWireframe(True)
            debug_node.showConstraints(True)
            debug_node.showBoundingBoxes(False)
            debug_node.showNormals(True)
            debug_np = self.render.attach_new_node(debug_node)
            debug_np.show()
            self.bullet_world.setDebugNode(debug_np.node())

    def remove(self, obj):
        self.updatables_to_remove[obj.name] = obj

        obj.np.detach_node()
        obj.np.remove_node()
        if(isinstance(obj.node, BulletGhostNode)):
            self.bullet_world.remove_ghost(obj.node)
        if(isinstance(obj.node, BulletRigidBodyNode)):
            self.bullet_world.remove_rigid_body(obj.node)
        obj.attached = False
        obj.world = False
        

    def update(self, dt):
        
        self.bullet_world.doPhysics(dt)
        for obj in self.updatables:
            obj.update(dt)

        if len(self.updatables_to_remove) > 0:
            for key, updatable in self.updatables_to_remove.items():
                self.updatables.remove(updatable)
            self.updatables_to_remove = {}

        if len(self.updatables_to_add) > 0:
            for key, updatable in self.updatables_to_add.items():
                self.updatables.add(updatable)
            self.updatables_to_add = {}

        if not self.is_client:
            if self.curr_blocks < MAX_BLOCKS and self.time_since_last_block > 5:
                self.add_block([0,25,0])
                self.time_since_last_block = 0
            else:
                self.time_since_last_block += dt

            self.script.update(dt)
            if self.display == self.previous_display:
                pass
            else:
                self.display_updated = True
                #print "New display text: ", self.display
        else:
            self.message_display.update(dt)

    def get_object(self, name):
        return self.objects[name]