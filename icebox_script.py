score_red = 0
score_blue = 0

timers = {}

def incr_red():
    score_red = score_red + 1
    if score_red > 100:
        display.message = '!!RED WINS!!'
    game.winner = red

def incr_blue():
    score_blue = score_blue + 1
    if score_blue > 100:
        display.message = '!!BLUE WINS!!'
    game.winner = blue

def enter_red(obj):
    if obj.type == 'block':
        timers[obj.id] = timer(1000, incr_red)

def enter_blue(obj):
    if obj.type == 'obj':
        timers[obj.id] = timer(1000, incr_blue)

def exit_goal(obj):
    if obj.id in timers:
        t = timers[obj.id]
        t.stop()
        del timers[obj.id]

goal_red.on_enter = enter_red
goal_blue.on_enter = enter_blue
goal_red.on_exit = exit_goal
goal_blue.on_exit = exit_goal
