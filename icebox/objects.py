from pavara.utils.geom import GeomBuilder
from panda3d.core import NodePath, ColorAttrib, Vec3, LRotationf, Point3
from panda3d.bullet import BulletRigidBodyNode, BulletBoxShape, BulletPlaneShape, BulletGhostNode, BulletSphereShape
from icebox.constants import *

class WorldObject(object):
    world = None
    last_unique_id = 0
    attached = False
    moved = False
    does_rotate = True
    is_block = False

    def __init__(self, name=None):
        self.name = name
        if not self.name:
            self.name = '%s:%d' % (self.__class__.__name__, self.__class__.last_unique_id)
        self.__class__.last_unique_id += 1

    def update(self, dt):
        pass

    def check_attached(self):
        if not self.attached:
            print "Couldn't modify", self.name, "because it wasn't attached"
        return self.attached

    def move(self, pos):
        if self.check_attached():
            self.moved = True
            self.np.set_pos(*pos)

    def move_by(self, pos):
        if self.check_attached():
            self.moved = True
            self.np.set_fluid_pos(self.np, pos[0], pos[1], pos[2])

    def rotate(self, hpr):
        if self.check_attached():
            self.moved = True
            self.np.set_hpr(*hpr)

    def rotate_by(self, hpr):
        if self.check_attached():
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
        if self.does_rotate:
            datagram.add_float(hpr.x)
            datagram.add_float(hpr.y)
            datagram.add_float(hpr.z)
        self.moved = False

    def __repr__(self):
        return self.name

class Tank(WorldObject):
    def __init__(self, color, name = None, nick = None):
        super(Tank, self).__init__(name)
        self.color = color
        b = GeomBuilder('tank')
        b.add_dome(self.color, (0, 0, 0), 2, 6, 4)
        b.add_block([.3, .3, .3, 1], (0, 0.6, 2.2), (.7, .7, 2))
        if nick:
            self.text = nick
        self.geom = b.get_geom_node()
        self.node = BulletGhostNode(self.name)
        self.text_node_path = None
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
            if self.text_node_path:
                self.text_node_path.look_at(self.world.cam)
                self.text_node_path.set_hpr(self.text_node_path, 180, 0, 0)

    def fire_projectile(self):
        pos = self.np.get_pos()
        pos.y += .6
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
        self.does_rotate = False
        b = GeomBuilder('proj')
        b.add_dome(self.color, (0, 0, 0), .5, 3, 2)
        b.add_dome(self.color, (0, 0, 0), .5, 3, 2, rot = LRotationf(0, 180, 0))
        self.geom = b.get_geom_node()

        shape = BulletSphereShape(.5)
        self.node = BulletGhostNode(self.name)
        #self.node.set_mass(.6)
        self.node.addShape(shape)
        self.pos = (0, 0, 0)
        self.timer = 0
        self.direction = None

    def update(self, dt):
        self.timer += dt
        
        if self.timer > 5:
            self.world.remove(self)
            self.moved = False
        else:
            if not self.world.is_client:
                self.move_by([0, 0, PROJECTILE_SPEED * dt])
                contact_test_result = self.world.bullet_world.contactTest(self.node)
                for contact in contact_test_result.getContacts():
                    other_node = contact.getNode1()
                    name = other_node.get_name()
                    #print other_node
                    if name.startswith('Block'):
                        if not self.world:
                            return
                        v = self.world.render.get_relative_vector(self.np, Vec3(0, 0, 1))
                        other_np = self.world.objects[name].np
                        other_pos = other_np.get_pos()
                        local_point = (other_pos - self.np.get_pos()) * -1
                        v.normalize()
                        impulse_v = v * HIT_MAGNITUDE
                        #print impulse_v, local_point
                        other_node.set_active(True)
                        other_node.apply_impulse(impulse_v, Point3(local_point))
                        self.world.remove(self)
            self.moved = True

class Block(WorldObject):
    def __init__(self, name=None):
        super(Block, self).__init__(name)
        self.is_block = True
        b = GeomBuilder('block')
        b.add_block(BLOCK_COLOR, (0, 0, 0), BLOCK_SIZE)
        self.geom = b.get_geom_node()

        shape = BulletBoxShape(Vec3(*[x/2.0 for x in BLOCK_SIZE]))
        self.node = BulletRigidBodyNode(self.name)
        self.node.set_mass(1.0)
        self.node.addShape(shape)
        self.pos = (0, 0, 0)

    def update(self, dt):
        if not self.attached:
            return
        new_pos = self.np.get_pos()
        if not new_pos == self.pos and self.attached:
            self.moved = True
        self.pos = new_pos
        threshold = ARENA_SIZE/2.0
        if self.world.is_client:
            threshold -= .6
        dist = (self.pos - Vec3(0,0,0)).length()
        if dist > threshold:
            self.world.curr_blocks -= 1
            self.world.remove(self)


class Arena(WorldObject):
    type = 'ground'
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

        b = GeomBuilder('enclosingdome')
        b.add_dome(FLOOR_COLOR, (0, 0, 0), ARENA_SIZE/2.0, 12, 6, inverse = True)
        ceiling_geom = b.get_geom_node()
        floor_np.attach_new_node(ceiling_geom)

        self.geom = floor_np

        ground_shape = BulletPlaneShape(Vec3(0, 1, 0), 1)
        self.node = BulletRigidBodyNode('ground')
        self.node.add_shape(ground_shape)
        self.node.set_mass(0)

        goal_shape = BulletBoxShape(Vec3(GOAL_SIZE[0], GOAL_SIZE[2], GOAL_SIZE[1]))
        self.red_goal = BulletGhostNode('red_goal')
        self.red_goal.add_shape(goal_shape)
        self.blue_goal = BulletGhostNode('blue_goal')
        self.blue_goal.add_shape(goal_shape)






