import ast

class SafePyFunction(object):
    def __init__(self, args, body, env, whitelist):
        self.args = args
        self.body = body
        self.env = env
        self.whitelist = whitelist
    def call(self, *argvals):
        env = self.env.push()
        for k, v in zip(self.args.args, argvals):
            env.assign(k.id, v)

        evaluate(self.body, env, self.whitelist)
        return env.returnval

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

def assign(tree, env, whitelist, val):
    if isinstance(tree, ast.Name):
        env.assign(tree.id, val)
    elif isinstance(tree, ast.Attribute):
        obj = evaluate(tree.value, env, whitelist)
        setter = 'set_' + tree.attr
        if hasattr(obj, 'set_' + tree.attr):
            getattr(obj, setter)(val)
        else:
            setattr(obj, tree.attr, val)
    else:
        print 'unsupported assignment', tree

def evaluate(tree, env, whitelist):
    if isinstance(tree, ast.Module):
        return evaluate(tree.body, env, whitelist)
    elif isinstance(tree, list):
        results = []
        for statement in tree:
            if isinstance(statement, ast.Expr):
                results.append(evaluate(statement.value, env, whitelist))
            elif isinstance(statement, ast.FunctionDef):
                env.assign(statement.name, SafePyFunction(statement.args, statement.body, env, whitelist))
            elif isinstance(statement, ast.Assign):
                v = evaluate(statement.value, env, whitelist)
                if isinstance(v, int) or isinstance(v, float) or isinstance(v, SafePyFunction):
                    assign(statement.targets[0], env, whitelist, v)
                else:
                    print "unsafe assignment rejected", v
            elif isinstance(statement, ast.If):
                test = evaluate(statement.test, env, whitelist)
                if test:
                    evaluate(statement.body, env, whitelist)
                else:
                    evaluate(statement.orelse, env, whitelist)
                if env.returnval is not None:
                    return results
            elif isinstance(statement, ast.Return):
                env.returnval = evaluate(statement.value, env, whitelist)
                return results
            else:
                print statement
        return results
    elif isinstance(tree, ast.Name):
        return env.lookup(tree.id)
    elif isinstance(tree, ast.BinOp):
        left = evaluate(tree.left, env, whitelist)
        right = evaluate(tree.right, env, whitelist)
        if isinstance(tree.op, ast.Add):
            return left + right
        elif isinstance(tree.op, ast.Sub):
            return left - right
        else:
            print "unknown operator", tree.op
    elif isinstance(tree, ast.Num):
        return tree.n
    elif isinstance(tree, ast.Attribute):
        obj = evaluate(tree.value, env, whitelist)
        return getattr(obj, tree.attr)
    elif isinstance(tree, ast.Compare):
        left = evaluate(tree.left, env, whitelist)
        right = evaluate(tree.comparators[0], env, whitelist)
        if isinstance(tree.ops[0], ast.Eq):
            return left == right
        elif isinstance(tree.ops[0], ast.LtE):
            return left <= right
        else:
            print 'unsupported compare', tree.ops[0]
    elif isinstance(tree, ast.Call):
        if isinstance(tree.func, ast.Name):
            if not env.contains(tree.func.id) and tree.func.id in whitelist:
                return whitelist[tree.func.id](*[evaluate(arg, env, whitelist) for arg in tree.args])
        f = evaluate(tree.func, env, whitelist)
        if isinstance(f, SafePyFunction):
            return f.call(*[evaluate(arg, env, whitelist) for arg in tree.args])
        elif hasattr(f, '__call__'):
            raise Exception('unsafe function call', f)
    else:
        print "unsupported syntax", type(tree)

def safe_eval(script, env=None, whitelist=None):
    if env is None:
        env = Env()
    if whitelist is None:
        whitelist = {}
    return evaluate(ast.parse(script), env, whitelist), env

