score_red = 0
score_blue = 0

#timers = {}

def incr_red():
    score_red = score_red + 1
    if score_red > 100:
        display.message = '!!RED WINS!!'
    game.winner = 'red'

def incr_blue():
    score_blue = score_blue + 1
    if score_blue > 100:
        display.message = '!!BLUE WINS!!'
    game.winner = 'blue'

def enter_red(obj):
    if obj.is_block:
        add_timer(1000, obj.name, incr_red)

def enter_blue(obj):
    if obj.is_block:
        add_timer(1000, obj.name, incr_blue)

def exit_goal(obj):
    if is_timer(obj.name):
        stop_timer(obj.name)

goal_red.on_enter = enter_red
goal_blue.on_enter = enter_blue
goal_red.on_exit = exit_goal
goal_blue.on_exit = exit_goal
