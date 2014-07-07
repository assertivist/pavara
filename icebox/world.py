from icebox.objects import Arena, Block, Tank, Projectile
from icebox.constants import *
from panda3d.core import VBase4, AmbientLight, NodePath
from panda3d.core import ColorAttrib, DirectionalLight, Vec4, Vec3
from panda3d.bullet import BulletWorld, BulletPlaneShape, BulletRigidBodyNode, BulletGhostNode, BulletDebugNode

class World (object):
    def __init__(self, showbase, is_client):
        self.is_client = is_client
        self.objects = {}
        self.updatables = set()
        self.render = showbase.render
        self.curr_blocks = 0
        self.bullet_world = BulletWorld()

        if is_client:
            self.init_visual()
        #else:
        self.bullet_world.setGravity(Vec3(0, -9.81, 0))

        self.arena = Arena('arena')
        self.attach(self.arena)
        self.arena.np.set_pos(0,0,0)
        self.updatables_to_add = []
        self.updatables_to_remove = []

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
            NodePath(obj.geom).reparent_to(obj.np)
        obj.world = self
        obj.attached = True

    def add_block(self, pos, name = None):
        block = Block(name)
        self.attach(block)
        self.updatables.add(block)
        block.move(pos)

    def add_tank(self, pos, rot, name = None):
        tank = Tank(RED_COLOR, name)
        self.attach(tank)
        self.updatables.add(tank)
        tank.move(pos)
        tank.rotate([rot, 0, 0])
        return tank

    def add_proj(self, color, pos, rot, speed_pitch, owner, name = None):
        proj = Projectile(color, name = name)
        self.attach(proj)
        #self.updatables.add(proj)
        self.updatables_to_add.append(proj)
        proj.move(pos)
        proj.rotate([rot, 0, 0])
        if not self.is_client:
            v = self.render.get_relative_vector(proj.np, Vec3(0, 0, 1))
            proj.node.applyCentralImpulse(v*(24 + (12 * speed_pitch)))

    def init_visual(self):
        self.objects_node = NodePath('VisibleObjects')

        alight = AmbientLight('ambient')
        alight.set_color(VBase4(0.6, 0.6, 0.6, 1))
        node = self.render.attach_new_node(alight)
        self.render.set_light(node)

        directional_light = DirectionalLight('directionalLight')
        directional_light.set_color(Vec4(0.7, 0.7, 0.7, 1))
        directional_light_np = self.render.attach_new_node(directional_light)
        directional_light_np.set_hpr(0, -80, 0)
        self.render.set_light(directional_light_np)

        self.arena = Arena(self.objects_node)

        self.render.setColorOff()
        self.render.setShaderAuto()
        self.render.node().setAttrib(ColorAttrib.makeVertex())

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
        self.updatables_to_remove.append(obj)

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
            for updatable in self.updatables_to_remove:
                self.updatables.remove(updatable)
            self.updatables_to_remove = []

        if len(self.updatables_to_add) > 0:
            for updatable in self.updatables_to_add:
                self.updatables.add(updatable)
            self.updatables_to_add = []