
from scripting.evaluator import *

class Goal(object):
	def __init__(self, bullet_node, world):
		self.node = bullet_node
		self.world = world
		self.on_enter = None
		self.on_exit = None
		self.inside = set()

	def update(self, dt):
		overlaps = self.node.getNumOverlappingNodes()
		if overlaps > 0 or len(self.inside) > 0:
			nodes = set(self.node.getOverlappingNodes())
			entered = nodes.difference(self.inside)
			exited = self.inside.difference(nodes)
			if len(entered) > 0:
				for n in entered:
					print "Entered: ", n
					if self.on_enter is not None:
						key = n.get_name()
						wobject = self.world.get_object(key)
						self.on_enter.call(wobject)
			if len(exited) > 0:
				for n in exited:
					print "Exited: ", n
					if self.on_exit is not None:
						key = n.get_name()
						wobject = self.world.get_object(key)
						self.on_exit.call(wobject)
			self.inside = nodes

class Timer(object):
	def __init__(self, interval, f):
		self.t = 0
		self.interval = interval
		self.f = f

	def update(self, dt):
		self.t += dt * 60
		if self.t > self.interval:
			self.f.call()
			self.t = 0

class Script(object):
	def __init__(self, world):
		self.world = world
		self.red_goal = Goal(world.arena.red_goal, world)
		self.blue_goal = Goal(world.arena.blue_goal, world)

		self.env = Env()

		self.env.assign('goal_red', self.red_goal)
		self.env.assign('goal_blue', self.blue_goal)
		self.env.assign('display', self.world.message_display)
		self.whitelist = {
			'add_timer': self.add_timer,
			'stop_timer': self.stop_timer,
			'is_timer': self.is_timer
		}
		
		self.timers = {}
		script = file('icebox_script.py').read()
		_, self.env = safe_eval(script, env = self.env, whitelist = self.whitelist)

	def update(self, dt):
		self.red_goal.update(dt)
		self.blue_goal.update(dt)
		for k,t in self.timers.iteritems():
			t.update(dt)
		pass
	
	def add_timer(self, t, key, f):
		self.timers[key] = Timer(t, f)

	def stop_timer(self, key):
		del self.timers[key]

	def is_timer(self, key):
		return key in self.timers
