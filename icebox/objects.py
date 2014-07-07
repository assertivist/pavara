from pavara.utils.geom import GeomBuilder
from panda3d.core import NodePath, ColorAttrib, Vec3, LRotationf
from panda3d.bullet import BulletRigidBodyNode, BulletBoxShape, BulletPlaneShape, BulletGhostNode, BulletSphereShape
from icebox.constants import *

class WorldObject(object):
    world = None
    last_unique_id = 0
    attached = False
    moved = False

    def __init__(self, name=None):
        self.name = name
        if not self.name:
            self.name = '%s:%d' % (self.__class__.__name__, self.__class__.last_unique_id)
        self.__class__.last_unique_id += 1

    def update(self, dt):
        pass

    def move(self, pos):
        assert(self.attached)
        self.moved = True
        self.np.set_pos(*pos)

    def move_by(self, pos):
        assert(self.attached)
        self.moved = True
        self.np.set_fluid_pos(self.np, pos[0], pos[1], pos[2])

    def rotate(self, hpr):
        assert(self.attached)
        self.moved = True
        self.np.set_hpr(*hpr)

    def rotate_by(self, hpr):
        assert(self.attached)
        self.moved = True
        self.np.set_hpr(self.np, hpr[0], hpr[1], hpr[2])

    def add_update(self, datagram):
        pos = self.np.get_pos()
        hpr = self.np.get_hpr()
        if not self.moved:
            return
        datagram.add_string(self.name)
        datagram.add_float(pos.x)
        datagram.add_float(pos.y)
        datagram.add_float(pos.z)
        datagram.add_float(hpr.x)
        datagram.add_float(hpr.y)
        datagram.add_float(hpr.z)
        self.moved = False

    def __repr__(self):
        return self.name

class Tank(WorldObject):
    def __init__(self, color, name = None):
        super(Tank, self).__init__(name)
        self.color = color
        b = GeomBuilder('tank')
        b.add_dome(self.color, (0, 0, 0), 2, 6, 4)
        b.add_block([.3, .3, .3, 1], (0, 0.6, 2.2), (.7, .7, 2))
        self.geom = b.get_geom_node()
        self.node = BulletGhostNode(self.name)

        self.hello = False
        self.left = False
        self.right = False
        self.forward = False
        self.backward = False
        self.fire = False
        self.fired = False


    def update(self, dt):
        if self.attached:
            angle = self.np.get_h()
            if self.left and not self.right:
                new_angle = angle + (TURN_RATE * dt)
                if new_angle < 0:
                    new_angle += 360
                self.rotate([new_angle, 0, 0])
            if self.right and not self.left:
                new_angle = angle + (-TURN_RATE * dt)
                if new_angle > 360:
                    new_angle -= 360
                self.rotate([new_angle, 0, 0])
            if self.forward and not self.backward:
                self.move_by([0, 0, SPEED * dt])
            if self.backward and not self.forward:
                self.move_by([0, 0, -SPEED * dt])
            if self.fire and not self.fired:
                self.fired = True
                self.fire_projectile()
            if not self.fire:
                self.fired = False

    def fire_projectile(self):
        pos = self.np.get_pos()
        rot = self.np.get_h()

        speed_pitch = 0
        if self.forward and not self.backward:
            speed_pitch = 1 
        if self.backward and not self.forward:
            speed_pitch = -1 

        self.world.add_proj(GREEN_COLOR, pos, rot, speed_pitch, self.name)

    def handle_command(self, command, value):
        setattr(self, command, value)

class Projectile(WorldObject):
    def __init__(self, color, name = None):
        super(Projectile, self).__init__(name)
        self.color = color
        b = GeomBuilder('proj')
        b.add_dome(self.color, (0, 0, 0), .5, 6, 4)
        b.add_dome(self.color, (0, 0, 0), .5, 6, 4, rot = LRotationf(0, 180, 0))
        self.geom = b.get_geom_node()

        shape = BulletSphereShape(.5)
        self.node = BulletRigidBodyNode(self.name)
        self.node.set_mass(.6)
        self.node.addShape(shape)
        self.pos = (0, 0, 0)
        self.timer = 0

    def update(self, dt):
        self.timer += dt
        if self.timer > 5:
            self.world.remove(self)
            self.moved = False
        else:
            self.moved = True

class Block(WorldObject):
    def __init__(self, name=None):
        super(Block, self).__init__(name)

        b = GeomBuilder('block')
        b.add_block(BLOCK_COLOR, (0, 0, 0), BLOCK_SIZE)
        self.geom = b.get_geom_node()

        shape = BulletBoxShape(Vec3(*[x/2.0 for x in BLOCK_SIZE]))
        self.node = BulletRigidBodyNode(self.name)
        self.node.set_mass(1.0)
        self.node.addShape(shape)
        self.pos = (0, 0, 0)

    def update(self, dt):
        new_pos = self.np.get_pos()
        if not new_pos == self.pos and self.attached:
            self.moved = True
        self.pos = new_pos
        if self.pos.x > 50 or self.pos.y > 50 or self.pos.z > 50:
            self.world.curr_blocks -= 1
            self.world.remove(self)


class Arena(WorldObject):
    def __init__(self, name=None):
        super(Arena, self).__init__(name)

        b = GeomBuilder('floor')
        b.add_block(FLOOR_COLOR, (0, 0, 0), (ARENA_SIZE, 1, ARENA_SIZE))
        floor_geom = b.get_geom_node()
        floor_np = NodePath('floor_np')
        floor_np.attach_new_node(floor_geom)

        b = GeomBuilder('halfcourt')
        b.add_block(LINE_COLOR, (0, .6, 0), (ARENA_SIZE, .2, 1))
        line_geom = b.get_geom_node()
        floor_np.attach_new_node(line_geom)

        b = GeomBuilder('redgoal')
        b.add_block(RED_COLOR, (0, .6, -ARENA_SIZE/4.0), (GOAL_SIZE[0], .1, GOAL_SIZE[1]))
        redgoal_geom = b.get_geom_node()
        b = GeomBuilder('redgoal_overlay')
        b.add_block(FLOOR_COLOR, (0, .65, -ARENA_SIZE/4.0), (GOAL_SIZE[0] - .8, .1, GOAL_SIZE[1] - .8))
        redgoal_overlay_geom = b.get_geom_node()
        floor_np.attach_new_node(redgoal_geom)
        floor_np.attach_new_node(redgoal_overlay_geom)

        b = GeomBuilder('bluegoal')
        b.add_block(BLUE_COLOR, (0, .6, ARENA_SIZE/4.0), (GOAL_SIZE[0], .1, GOAL_SIZE[1]))
        bluegoal_geom = b.get_geom_node()
        b = GeomBuilder('bluegoal_overlay')
        b.add_block(FLOOR_COLOR, (0, .65, ARENA_SIZE/4.0), (GOAL_SIZE[0] - .8, .1, GOAL_SIZE[1] - .8,))
        bluegoal_overlay_geom = b.get_geom_node()
        floor_np.attach_new_node(bluegoal_geom)
        floor_np.attach_new_node(bluegoal_overlay_geom)

        self.geom = floor_np

        ground_shape = BulletPlaneShape(Vec3(0, 1, 0), 1)
        self.node = BulletRigidBodyNode('ground')
        self.node.add_shape(ground_shape)
        self.node.set_mass(0)






