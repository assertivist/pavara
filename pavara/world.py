from pandac.PandaModules import *
from panda3d.bullet import *
from pavara.utils.geom import make_box, make_dome, to_cartesian, make_square
from pavara.assets import load_model
from direct.interval.LerpInterval import *
from direct.interval.IntervalGlobal import * 
import math

DEFAULT_AMBIENT_COLOR = (0.4, 0.4, 0.4, 1)
DEFAULT_GROUND_COLOR =  (0.75, 0.5, 0.25, 1)
DEFAULT_SKY_COLOR =     (0.7, 0.8, 1, 1)
DEFAULT_HORIZON_COLOR = (1, 0.8, 0, 1)
DEFAULT_HORIZON_SCALE = 0.05

NO_COLLISION_BITS = BitMask32.all_off()
MAP_COLLIDE_BIT =   BitMask32.bit(0)
SOLID_COLLIDE_BIT = BitMask32.bit(1)
GHOST_COLLIDE_BIT = BitMask32.bit(2)

class WorldObject (object):
    """
    Base class for anything attached to a World.
    """

    world = None
    last_unique_id = 0
    collide_bits = NO_COLLISION_BITS

    def __init__(self, name=None):
        self.name = name
        if not self.name:
            self.__class__.last_unique_id += 1
            self.name = '%s:%d' % (self.__class__.__name__, self.__class__.last_unique_id)

    def __repr__(self):
        return self.name

    def attached(self):
        """
        Called when this object is actually attached to a World. By this time, self.world will have been set.
        """
        pass

    def detached(self):
        """
        """
        pass

    def update(self, dt):
        """
        Called each frame if the WorldObject has registered itself as updatable.
        """
        pass

class PhysicalObject (WorldObject):
    """
    A WorldObject subclass that represents a physical object; i.e. one that is visible and may have an associated
    solid for physics collisions.
    """

    node = None
    solid = None
    collide_bits = MAP_COLLIDE_BIT

    def create_node(self):
        """
        Called by World.attach to create a NodePath that will be re-parented to the World's render.
        """
        pass

    def create_solid(self):
        """
        Called by World.attach to create any necessary physics geometry.
        """
        pass

    def collision(self, other, manifold, first):
        """
        Called when this object is collidable, and collides with another collidable object.
        :param manifold: The "line" between the colliding objects. See
                         https://www.panda3d.org/reference/devel/python/classpanda3d.bullet.BulletManifoldPoint.php
        :param first: Whether this was the "first" (node0) object in the collision.
        """
        pass

    def rotate(self, yaw, pitch, roll):
        """
        Programmatically set the yaw, pitch, and roll of this object.
        """
        self.node.set_hpr(yaw, pitch, roll)

    def rotate_by(self, yaw, pitch, roll):
        """
        Programmatically rotate this object by the given yaw, pitch, and roll.
        """
        self.node.set_hpr(self.node, yaw, pitch, roll)

    def move(self, center):
        """
        Programmatically move this object to be centered at the given coordinates.
        """
        self.node.set_pos(*center)

    def move_by(self, x, y, z):
        """
        Programmatically move this object by the given distances in each direction.
        """
        self.node.set_pos(self.node, x, y, z)

class Hector (PhysicalObject):

    collide_bits = SOLID_COLLIDE_BIT

    def __init__(self):
        super(Hector, self).__init__()

        self.on_ground = False
        self.mass = 150.0 # 220.0 for heavy
        self.factors = {
            'forward': 0.1,
            'backward': -0.1,
            'left': 2.0,
            'right': -2.0,
            'crouch': 0.0,
        }
        self.movement = {
            'forward': 0.0,
            'backward': 0.0,
            'left': 0.0,
            'right': 0.0,
            'crouch': 0.0,
        }
        self.walk_phase = 0
        self.placing = False

    def create_node(self):
        from direct.actor.Actor import Actor
        self.actor = Actor('hector.egg')
        self.actor.listJoints()
        self.barrels = self.actor.find("**/barrels")
        self.barrel_trim = self.actor.find("**/barrelTrim")
        self.visor = self.actor.find("**/visor")
        self.hull = self.actor.find("**/hull")
        self.crotch = self.actor.find("**/crotch")
        self.head = self.actor.attachNewNode("hector_head_node")
        self.barrels.reparentTo(self.head)
        self.barrel_trim.reparentTo(self.head)
        self.visor.reparentTo(self.head)
        self.hull.reparentTo(self.head)
        self.crotch.reparentTo(self.head)
        self.left_top = self.actor.find("**/leftTop")
        self.right_top = self.actor.find("**/rightTop")
        self.left_middle = self.actor.find("**/leftMiddle")
        self.left_middle.reparentTo(self.left_top)
        self.right_middle = self.actor.find("**/rightMiddle")
        self.right_middle.reparentTo(self.right_top)
        self.left_bottom = self.actor.find("**/leftBottom")
        self.left_bottom.reparentTo(self.left_middle)
        self.right_bottom = self.actor.find("**/rightBottom")
        self.right_bottom.reparentTo(self.right_middle)
        
        self.walk_playing = False
        
        def getJoint(name):
            return self.actor.controlJoint(None, "modelRoot", name)
        self.right_top_bone = getJoint("rightTopBone")
        self.left_top_bone = getJoint("leftTopBone")
        self.right_middle_bone = getJoint("rightMidBone")
        self.left_middle_bone = getJoint("leftMidBone")
        self.right_bottom_bone = getJoint("rightBottomBone")
        self.left_bottom_bone = getJoint("leftBottomBone")
        self.head_bone = getJoint("headBone")
        self.torso_rest_y = [self.head_bone.get_pos(), self.left_top_bone.get_pos(), self.right_top_bone.get_pos()]
        self.legs_rest_mat = [ [self.right_top_bone.get_hpr(), self.right_middle_bone.get_hpr(), self.right_bottom_bone.get_hpr()],
                               [self.left_top_bone.get_hpr(), self.left_middle_bone.get_hpr(), self.left_bottom_bone.get_hpr()] ]

        def make_return_sequence():
            return_speed = .2
            y_return_head_int = LerpPosInterval(self.head_bone, return_speed, self.torso_rest_y[0])
            y_return_left_int = LerpPosInterval(self.left_top_bone, return_speed, self.torso_rest_y[1])
            y_return_right_int = LerpPosInterval(self.right_top_bone, return_speed, self.torso_rest_y[2])
            
            r_top_return_int = LerpHprInterval(self.right_top_bone, return_speed, self.legs_rest_mat[0][0])
            r_mid_return_int = LerpHprInterval(self.right_middle_bone, return_speed, self.legs_rest_mat[0][1])   
            r_bot_return_int = LerpHprInterval(self.right_bottom_bone, return_speed, self.legs_rest_mat[0][2])      
            
            l_top_return_int = LerpHprInterval(self.left_top_bone, return_speed, self.legs_rest_mat[1][0])
            l_mid_return_int = LerpHprInterval(self.left_middle_bone, return_speed, self.legs_rest_mat[1][1])
            l_bot_return_int = LerpHprInterval(self.left_bottom_bone, return_speed, self.legs_rest_mat[1][2])
            
            return Parallel(r_top_return_int, r_mid_return_int, r_bot_return_int, 
            			    l_top_return_int, l_mid_return_int, l_bot_return_int,
            			    y_return_head_int, y_return_left_int, y_return_right_int)         
            
        self.return_seq = make_return_sequence()
        
        def make_walk_sequence():
            walk_cycle_speed = .8
            
            y_bob_down_head_int = LerpPosInterval(self.head_bone, walk_cycle_speed/4.0,  self.torso_rest_y[0] + Vec3(0,-.03,0))
            y_bob_down_left_int = LerpPosInterval(self.left_top_bone, walk_cycle_speed/4.0,  self.torso_rest_y[1] + Vec3(0,-.03,0))
            y_bob_down_right_int = LerpPosInterval(self.right_top_bone, walk_cycle_speed/4.0,  self.torso_rest_y[2] + Vec3(0,-.03,0))
            
            y_bob_up_head_int = LerpPosInterval(self.head_bone, walk_cycle_speed/4.0,  self.torso_rest_y[0] + Vec3(0,.03,0))
            y_bob_up_left_int = LerpPosInterval(self.left_top_bone, walk_cycle_speed/4.0,  self.torso_rest_y[1] + Vec3(0,.03,0))
            y_bob_up_right_int = LerpPosInterval(self.right_top_bone, walk_cycle_speed/4.0,  self.torso_rest_y[2] + Vec3(0,.03,0))
            
            
            r_top_forward_int_1 = LerpHprInterval(self.right_top_bone, walk_cycle_speed/4.0, self.legs_rest_mat[0][0] + Vec3(0, 30, 0))
            r_mid_forward_int_1 = LerpHprInterval(self.right_middle_bone, walk_cycle_speed/4.0, self.legs_rest_mat[0][1] + Vec3(0, 4, 0))
            r_bot_forward_int_1 = LerpHprInterval(self.right_bottom_bone, walk_cycle_speed/4.0, self.legs_rest_mat[0][2] + Vec3(0, 10, 0))
            
            r_top_forward_int_2 = LerpHprInterval(self.right_top_bone, walk_cycle_speed/4.0, self.legs_rest_mat[0][0] + Vec3(0, 28, 0))
            r_mid_forward_int_2 = LerpHprInterval(self.right_middle_bone, walk_cycle_speed/4.0, self.legs_rest_mat[0][1] + Vec3(0, -10, 0))
            r_bot_forward_int_2 = LerpHprInterval(self.right_bottom_bone, walk_cycle_speed/4.0, self.legs_rest_mat[0][2] + Vec3(0, -2, 0))
            
            r_top_forward_int_3 = LerpHprInterval(self.right_top_bone, walk_cycle_speed/4.0, self.legs_rest_mat[0][0] + Vec3(0, -40, 0))
            r_mid_forward_int_3 = LerpHprInterval(self.right_middle_bone, walk_cycle_speed/4.0, self.legs_rest_mat[0][1] + Vec3(0, -4, 0))
            r_bot_forward_int_3 = LerpHprInterval(self.right_bottom_bone, walk_cycle_speed/4.0, self.legs_rest_mat[0][2] + Vec3(0, -20, 0))
            
            r_top_forward_int_4 = LerpHprInterval(self.right_top_bone, walk_cycle_speed/4.0, self.legs_rest_mat[0][0] + Vec3(0, -5, 0))
            r_mid_forward_int_4 = LerpHprInterval(self.right_middle_bone, walk_cycle_speed/4.0, self.legs_rest_mat[0][1] + Vec3(0, 0, 0))
            r_bot_forward_int_4 = LerpHprInterval(self.right_bottom_bone, walk_cycle_speed/4.0, self.legs_rest_mat[0][2] + Vec3(0, -10, 0))
            
            l_top_forward_int_1 = LerpHprInterval(self.left_top_bone, walk_cycle_speed/4.0, self.legs_rest_mat[1][0] + Vec3(0, 30, 0))
            l_mid_forward_int_1 = LerpHprInterval(self.left_middle_bone, walk_cycle_speed/4.0, self.legs_rest_mat[1][1] + Vec3(0, 4, 0))
            l_bot_forward_int_1 = LerpHprInterval(self.left_bottom_bone, walk_cycle_speed/4.0, self.legs_rest_mat[1][2] + Vec3(0, 10, 0))
            
            l_top_forward_int_2 = LerpHprInterval(self.left_top_bone, walk_cycle_speed/4.0, self.legs_rest_mat[1][0] + Vec3(0, 28, 0))
            l_mid_forward_int_2 = LerpHprInterval(self.left_middle_bone, walk_cycle_speed/4.0, self.legs_rest_mat[1][1] + Vec3(0, -10, 0))
            l_bot_forward_int_2 = LerpHprInterval(self.left_bottom_bone, walk_cycle_speed/4.0, self.legs_rest_mat[1][2] + Vec3(0, -2, 0))
            
            l_top_forward_int_3 = LerpHprInterval(self.left_top_bone, walk_cycle_speed/4.0, self.legs_rest_mat[1][0] + Vec3(0, -40, 0))
            l_mid_forward_int_3 = LerpHprInterval(self.left_middle_bone, walk_cycle_speed/4.0, self.legs_rest_mat[1][1] + Vec3(0, -4, 0))
            l_bot_forward_int_3 = LerpHprInterval(self.left_bottom_bone, walk_cycle_speed/4.0, self.legs_rest_mat[1][2] + Vec3(0, -20, 0))
            
            l_top_forward_int_4 = LerpHprInterval(self.left_top_bone, walk_cycle_speed/4.0, self.legs_rest_mat[1][0] + Vec3(0, -5, 0))
            l_mid_forward_int_4 = LerpHprInterval(self.left_middle_bone, walk_cycle_speed/4.0, self.legs_rest_mat[1][1] + Vec3(0, 0, 0))
            l_bot_forward_int_4 = LerpHprInterval(self.left_bottom_bone, walk_cycle_speed/4.0, self.legs_rest_mat[1][2] + Vec3(0, -10, 0))
            
            return Sequence(
                            Parallel(r_top_forward_int_1, r_mid_forward_int_1, r_bot_forward_int_1,
                                    l_top_forward_int_3, l_mid_forward_int_3, l_bot_forward_int_3,
                                    y_bob_down_head_int, y_bob_down_left_int, y_bob_down_right_int),
                            Parallel(r_top_forward_int_2, r_mid_forward_int_2, r_bot_forward_int_2,
                                    l_top_forward_int_4, l_mid_forward_int_4, l_bot_forward_int_4,
                                    y_bob_up_head_int, y_bob_up_left_int, y_bob_up_right_int),
                            Parallel(r_top_forward_int_3, r_mid_forward_int_3, r_bot_forward_int_3,
                                    l_top_forward_int_1, l_mid_forward_int_1, l_bot_forward_int_1,
                                    y_bob_down_head_int, y_bob_down_left_int, y_bob_down_right_int),
                            Parallel(r_top_forward_int_4, r_mid_forward_int_4, r_bot_forward_int_4,
                                    l_top_forward_int_2, l_mid_forward_int_2, l_bot_forward_int_2,
                                    y_bob_up_head_int, y_bob_up_left_int, y_bob_up_right_int)
                           )
                           
        self.walk_forward_seq = make_walk_sequence()                    

        return self.actor

    def create_solid(self):
        node = BulletRigidBodyNode(self.name)
        node.add_shape(self.b_shape_from_node_path(self.visor))
        node.add_shape(self.b_shape_from_node_path(self.hull))
        node.add_shape(self.b_shape_from_node_path(self.crotch))
        node.add_shape(self.b_shape_from_node_path(self.barrels))
        node.add_shape(self.b_shape_from_node_path(self.barrel_trim))
        node.add_shape(self.b_shape_from_node_path(self.right_top))
        node.add_shape(self.b_shape_from_node_path(self.right_middle))
        node.add_shape(self.b_shape_from_node_path(self.right_bottom))
        node.add_shape(self.b_shape_from_node_path(self.left_top))
        node.add_shape(self.b_shape_from_node_path(self.left_middle))
        node.add_shape(self.b_shape_from_node_path(self.left_bottom))
        return node
        
    def b_shape_from_node_path(self, nodepath):
        node = nodepath.node()
        geom = node.getGeom(0)
        shape = BulletConvexHullShape()
        shape.addGeom(geom)
        return shape
    
    def setupColor(self, colordict):
        if colordict.has_key("barrel_color"):
            self.barrels.setColor(*colordict.get("barrel_color"))
        if colordict.has_key("barrel_trim_color"):
            self.barrel_trim.setColor(*colordict.get("barrel_trim_color"))
        if colordict.has_key("visor_color"):
            self.visor.setColor(*colordict.get("visor_color"))
        if colordict.has_key("body_color"):
            color = colordict.get("body_color")
            self.hull.setColor(*color)
            self.crotch.setColor(*color)
            self.left_top.setColor(*color)
            self.right_top.setColor(*color)
            self.left_middle.setColor(*color)
            self.right_middle.setColor(*color)
            self.left_bottom.setColor(*color)
            self.right_bottom.setColor(*color)
        if colordict.has_key("hull_color"):
            self.hull.setColor(*colordict.get("hull_color"))
            self.crotch.setColor(*colordict.get("hull_color"))
        if colordict.has_key("top_leg_color"):
            color = colordict.get("top_leg_color")
            self.left_top.setColor(*color)
            self.right_top.setColor(*color)
        if colordict.has_key("middle_leg_color"):
            color = colordict.get("middle_leg_color")
            self.left_middle.setColor(*color)
            self.right_middle.setColor(*color)   
        if colordict.has_key("bottom_leg_color"):
            color = colordict.get("bottom_leg_color")
            self.left_bottom.setColor(*color)
            self.right_bottom.setColor(*color)
        return

    def attached(self):
        self.node.set_scale(3.0)
        self.world.register_collider(self)
        self.world.register_updater(self)

    def collision(self, other, manifold, first):
        world_pt = manifold.get_position_world_on_a() if first else manifold.get_position_world_on_b()
        print self, 'HIT BY', other, 'AT', world_pt

    def handle_command(self, cmd, pressed):
        self.movement[cmd] = self.factors[cmd] if pressed else 0.0

    def update(self, dt):
        yaw = self.movement['left'] + self.movement['right']
        self.rotate_by(yaw, 0, 0)
        walk = self.movement['forward'] + self.movement['backward']
        self.move_by(0, 0, walk)
        # Cast a ray from just above our feet to just below them, see if anything hits.
        pt_from = self.node.get_pos() + Vec3(0, 0.2, 0)
        pt_to = pt_from + Vec3(0, -0.4, 0)
        result = self.world.physics.ray_test_closest(pt_from, pt_to, MAP_COLLIDE_BIT | SOLID_COLLIDE_BIT)
        self.update_legs(walk,dt)
        if result.has_hit():
            self.on_ground = True
            self.move(result.get_hit_pos())
        else:
            self.move_by(0, -0.05, 0)
    
    def update_legs(self, walk, dt):
        if walk != 0:
            if not self.walk_playing:
                self.walk_playing = True
                self.walk_forward_seq.loop()
        else:
            if self.walk_playing:
                self.walk_playing = False
                self.walk_forward_seq.pause()
                self.return_seq.start()
        
        

class Block (PhysicalObject):
    """
    A block. Blocks with non-zero mass will be treated as freesolids.
    """

    def __init__(self, size, color, mass, name=None):
        super(Block, self).__init__(name)
        self.size = size
        self.color = color
        self.mass = mass
        if self.mass > 0.0:
            self.collide_bits = MAP_COLLIDE_BIT | SOLID_COLLIDE_BIT

    def create_node(self):
        return NodePath(make_box(self.color, (0, 0, 0), *self.size))

    def create_solid(self):
        node = BulletRigidBodyNode(self.name)
        node.add_shape(BulletBoxShape(Vec3(self.size[0] / 2.0, self.size[1] / 2.0, self.size[2] / 2.0)))
        node.set_mass(self.mass)
        return node

class Dome (PhysicalObject):
    """
    A dome.
    """

    def __init__(self, radius, color, name=None):
        super(Dome, self).__init__(name)
        self.radius = radius
        self.color = color
        self.geom = make_dome(self.color, self.radius, 8, 5)

    def create_node(self):
        return NodePath(self.geom)

    def create_solid(self):
        node = BulletRigidBodyNode(self.name)
        mesh = BulletTriangleMesh()
        mesh.add_geom(self.geom.get_geom(0))
        node.add_shape(BulletTriangleMeshShape(mesh, dynamic=False))
        return node

class Ground (PhysicalObject):
    """
    The ground. This is not a visible object, but does create a physical solid.
    """

    def __init__(self, radius, color, name=None):
        super(Ground, self).__init__(name)
        self.color = color

    def create_solid(self):
        node = BulletRigidBodyNode(self.name)
        node.add_shape(BulletPlaneShape(Vec3(0, 1, 0), 1))
        return node

    def attached(self):
        self.move((0, -1.0, 0))
        # We need to tell the sky shader what color we are.
        self.world.sky.set_ground(self.color)

class Ramp (PhysicalObject):
    """
    A ramp. Basically a block that is rotated, and specified differently in XML. Should maybe be a Block subclass?
    """

    def __init__(self, base, top, width, thickness, color, name=None):
        super(Ramp, self).__init__(name)
        self.base = Point3(*base)
        self.top = Point3(*top)
        self.thickness = thickness
        self.color = color
        self.width = width
        self.length = (self.top - self.base).length()

    def create_node(self):
        return NodePath(make_box(self.color, (0, 0, 0), self.thickness, self.width, self.length))

    def create_solid(self):
        node = BulletRigidBodyNode(self.name)
        node.add_shape(BulletBoxShape(Vec3(self.thickness / 2.0, self.width / 2.0, self.length / 2.0)))
        return node

    def attached(self):
        # Do the block rotation after we've been attached (i.e. have a NodePath), so we can use node.look_at.
        v1 = self.top - self.base
        if self.base.get_x() != self.top.get_x():
            p3 = Point3(self.top.get_x()+100, self.top.get_y(), self.top.get_z())
        else:
            p3 = Point3(self.top.get_x(), self.top.get_y(), self.top.get_z() + 100)
        v2 = self.top - p3
        up = v1.cross(v2)
        up.normalize()
        midpoint = Point3((self.base + self.top) / 2.0)
        self.node.set_pos(midpoint)
        self.node.look_at(self.top, up)

class Sky (WorldObject):
    """
    The sky is actually just a square re-parented onto the camera, with a shader to handle the coloring and gradient.
    """

    def __init__(self, ground=DEFAULT_GROUND_COLOR, color=DEFAULT_SKY_COLOR, horizon=DEFAULT_HORIZON_COLOR, scale=DEFAULT_HORIZON_SCALE):
        super(Sky, self).__init__('sky')
        self.ground = ground
        self.color = color
        self.horizon = horizon
        self.scale = scale

    def attached(self):
        geom = GeomNode('sky')
        bounds = self.world.camera.node().get_lens().make_bounds()
        dl = bounds.getMin()
        ur = bounds.getMax()
        z = dl.getZ() * 0.99
        geom.add_geom(make_square((1, 1, 1, 1), dl.getX(), dl.getY(), 0, ur.getX(), ur.getY(), 0))
        self.node = self.world.render.attach_new_node(geom)
        self.node.set_shader(Shader.load('Shaders/Sky.sha'))
        self.node.set_shader_input('camera', self.world.camera)
        self.node.set_shader_input('sky', self.node)
        self.node.set_shader_input('groundColor', *self.ground)
        self.node.set_shader_input('skyColor', *self.color)
        self.node.set_shader_input('horizonColor', *self.horizon)
        self.node.set_shader_input('gradientHeight', self.scale, 0, 0, 0)
        self.node.reparent_to(self.world.camera)
        self.node.set_pos(self.world.camera, 0, 0, z)

    def set_ground(self, color):
        self.ground = color
        self.node.set_shader_input('groundColor', *self.ground)

    def set_color(self, color):
        self.color = color
        self.node.set_shader_input('skyColor', *self.color)

    def set_horizon(self, color):
        self.horizon = color
        self.node.set_shader_input('horizonColor', *self.horizon)

    def set_scale(self, height):
        self.scale = height
        self.node.set_shader_input('gradientHeight', self.scale, 0, 0, 0)

class World (object):
    """
    The World models basically everything about a map, including gravity, ambient light, the sky, and all map objects.
    """

    def __init__(self, camera, debug=False):
        self.objects = {}
        self.collidables = set()
        self.updatables = set()
        self.render = NodePath('world')
        self.camera = camera
        self.ambient = self._make_ambient()
        self.sky = self.attach(Sky())
        # Set up the physics world. TODO: let maps set gravity.
        self.physics = BulletWorld()
        self.physics.set_gravity(Vec3(0, -9.81, 0))
        if debug:
            debug_node = BulletDebugNode('Debug')
            debug_node.show_wireframe(True)
            debug_node.show_constraints(True)
            debug_node.show_bounding_boxes(False)
            debug_node.show_normals(False)
            np = self.render.attach_new_node(debug_node)
            np.show()
            self.physics.set_debug_node(debug_node)

    def _make_ambient(self):
        alight = AmbientLight('ambient')
        alight.set_color(VBase4(*DEFAULT_AMBIENT_COLOR))
        node = self.render.attach_new_node(alight)
        self.render.set_light(node)
        return node

    def attach(self, obj):
        assert isinstance(obj, WorldObject)
        assert obj.name not in self.objects
        obj.world = self
        if isinstance(obj, PhysicalObject):
            # Let each object define it's own NodePath, then reparent them.
            obj.node = obj.create_node()
            obj.solid = obj.create_solid()
            if obj.solid:
                if isinstance(obj.solid, BulletRigidBodyNode):
                    self.physics.attach_rigid_body(obj.solid)
                elif isinstance(obj.solid, BulletGhostNode):
                    self.physics.attach_ghost(obj.solid)
            if obj.node:
                if obj.solid:
                    # If this is a solid visible object, create a new physics node and reparent the visual node to that.
                    phys_node = self.render.attach_new_node(obj.solid)
                    obj.node.reparent_to(phys_node)
                    obj.node = phys_node
                else:
                    # Otherwise just reparent the visual node to the root.
                    obj.node.reparent_to(self.render)
            elif obj.solid:
                obj.node = self.render.attach_new_node(obj.solid)
            if obj.solid and obj.collide_bits is not None:
                obj.solid.set_into_collide_mask(obj.collide_bits)
        self.objects[obj.name] = obj
        # Let the object know it has been attached.
        obj.attached()
        return obj

    def set_ambient(self, color):
        """
        Sets the ambient light to the given color.
        """
        self.ambient.node().set_color(VBase4(*color))

    def add_celestial(self, azimuth, elevation, color, intensity, radius, visible):
        """
        Adds a celestial light source to the scene. If it is a visible celestial, also add a sphere model.
        """
        location = Vec3(to_cartesian(azimuth, elevation, 1000.0 * 255.0 / 256.0))
        dlight = DirectionalLight('celestial')
        dlight.set_color((color[0]*intensity, color[1]*intensity, color[2]*intensity, 1.0))
        node = self.render.attach_new_node(dlight)
        node.look_at(*(location * -1))
        self.render.set_light(node)
        if visible:
            sphere = load_model('misc/sphere')
            sphere.set_transparency(TransparencyAttrib.MAlpha)
            sphere.reparent_to(self.render)
            sphere.set_light_off()
            sphere.set_effect(CompassEffect.make(self.camera, CompassEffect.PPos))
            sphere.set_scale(45*radius)
            sphere.set_color(*color)
            sphere.set_pos(location)

    def register_collider(self, obj):
        assert isinstance(obj, PhysicalObject)
        self.collidables.add(obj)

    def register_updater(self, obj):
        assert isinstance(obj, WorldObject)
        self.updatables.add(obj)

    def update(self, task):
        """
        Called every frame to update the physics, etc.
        """
        dt = globalClock.getDt()
        for obj in self.updatables:
            obj.update(dt)
        self.physics.do_physics(dt)
        for obj in self.collidables:
            result = self.physics.contact_test(obj.node.node())
            for contact in result.get_contacts():
                obj1 = self.objects.get(contact.get_node0().get_name())
                obj2 = self.objects.get(contact.get_node1().get_name())
                if obj1 and obj2:
                    # Check the collision bits to see if the two objects should collide.
                    should_collide = obj1.collide_bits & obj2.collide_bits
                    if not should_collide.is_zero():
                        pt = contact.get_manifold_point()
                        if obj1 in self.collidables:
                            obj1.collision(obj2, pt, True)
                        if obj2 in self.collidables:
                            obj2.collision(obj1, pt, False)
        return task.cont