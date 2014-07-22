import ast

class SafePyFunction(object):
    def __init__(self, args, body, env):
        self.args = args
        self.body = body
        self.env = env
    def call(self, *argvals):
        env = self.env.push()
        for k, v in zip(self.args.args, argvals):
            env.assign(k.id, v)

        evaluate(self.body, env)
        return env.returnval

class WrappedFunction(object):
    def __init__(self, f):
        self.f = f

    def call(self, *argvals):
        return self.f(*argvals)

class Env(object):
    def __init__(self, variables=None):
        if variables is None:
            variables = [{}]
        self.variables = variables
        self.returnval = None

    def contains(self, name):
        for env in self.variables:
            if name in env:
                return True
        return False

    def lookup(self, name):
        for env in reversed(self.variables):
            if name in env:
                return env[name]
        else:
            raise Exception("variable not found: %s" % name)

    def assign(self, name, value):
        for env in reversed(self.variables):
            if name in env:
                env[name] = value
                return
        self.variables[-1][name] = value

    def push(self):
        return Env(self.variables + [{}])

def assign(tree, env, val):
    if isinstance(tree, ast.Name):
        env.assign(tree.id, val)
    elif isinstance(tree, ast.Attribute):
        obj = evaluate(tree.value, env)
        setter = 'set_' + tree.attr
        if hasattr(obj, 'set_' + tree.attr):
            getattr(obj, setter)(val)
        else:
            setattr(obj, tree.attr, val)
    else:
        print 'unsupported assignment', tree

def aug_assign(tree, env, op, val):
    if isinstance(tree, ast.Name):
        if isinstance(op, ast.Add):
            old = env.lookup(tree.id)
            old += val
            env.assign(tree.id, old)
    else:
        print 'unsupported augmentation', tree


def evaluate(tree, env):
    if isinstance(tree, ast.Module):
        return evaluate(tree.body, env)
    elif isinstance(tree, list):
        results = []
        for statement in tree:
            if isinstance(statement, ast.Expr):
                results.append(evaluate(statement.value, env))
            elif isinstance(statement, ast.FunctionDef):
                env.assign(statement.name, SafePyFunction(statement.args, statement.body, env))
            elif isinstance(statement, ast.Assign):
                v = evaluate(statement.value, env)
                if isinstance(v, int) or isinstance(v, float) or isinstance(v, SafePyFunction) or isinstance(v, str):
                    assign(statement.targets[0], env, v)
                else:
                    print "unsafe assignment rejected", v
            elif isinstance(statement, ast.If):
                test = evaluate(statement.test, env)
                if test:
                    evaluate(statement.body, env)
                else:
                    evaluate(statement.orelse, env)
                if env.returnval is not None:
                    return results
            elif isinstance(statement, ast.Return):
                env.returnval = evaluate(statement.value, env)
                return results
            elif isinstance(statement, ast.AugAssign):
                v = evaluate(statement.value, env)
                aug_assign(statement.target, env, statement.op, v)
            else:
                print 'unknown statement', statement
        return results
    elif isinstance(tree, ast.Name):
        return env.lookup(tree.id)
    elif isinstance(tree, ast.BinOp):
        left = evaluate(tree.left, env)
        right = evaluate(tree.right, env)
        if isinstance(tree.op, ast.Add):
            return left + right
        elif isinstance(tree.op, ast.Sub):
            return left - right
        else:
            print "unknown operator", tree.op
    elif isinstance(tree, ast.Num):
        return tree.n
    elif isinstance(tree, ast.Str):
        return tree.s
    elif isinstance(tree, ast.Attribute):
        obj = evaluate(tree.value, env)
        return getattr(obj, tree.attr)
    elif isinstance(tree, ast.Compare):
        left = evaluate(tree.left, env)
        right = evaluate(tree.comparators[0], env)
        if isinstance(tree.ops[0], ast.Eq):
            return left == right
        elif isinstance(tree.ops[0], ast.LtE):
            return left <= right
        elif isinstance(tree.ops[0], ast.Lt):
            return left < right
        elif isinstance(tree.ops[0], ast.NotEq):
            return left != right
        elif isinstance(tree.ops[0], ast.Gt):
            return left > right
        elif isinstance(tree.ops[0], ast.GtE):
            return left >= right
        else:
            print 'unsupported compare', tree.ops[0]
    elif isinstance(tree, ast.Call):
        f = evaluate(tree.func, env)
        if isinstance(f, SafePyFunction):
            return f.call(*[evaluate(arg, env) for arg in tree.args])
        elif isinstance(f, WrappedFunction):
            return f.call(*[evaluate(arg, env) for arg in tree.args])
        elif hasattr(f, '__call__'):
            raise Exception('unsafe function call', f)
    else:
        print "unsupported syntax", type(tree)

def safe_eval(script, env=None, whitelist=None):
    if env is None:
        env = Env()
    if whitelist is not None:
        for name, f in whitelist.items():
            env.assign(name, WrappedFunction(f))
    env.assign('True', True)
    env.assign('False', False)
    return evaluate(ast.parse(script), env), env
