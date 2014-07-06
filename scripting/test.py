import unittest
from evaluator import safe_eval

class C(object):
    def __init__(self):
        self.v = 20
        self.open = open
        self.secretx = None

    def set_x(self, value):
        self.secretx = value

class EvaluateShould(unittest.TestCase):

    def test_evaluate1plus1(self):
        result, _ = safe_eval('1+1')
        self.assertEqual([2], result)

    def test_moduleVars(self):
        _, env = safe_eval("""x = 200""")
        self.assertEqual(200, env.lookup('x'))

    def test_addonefunction(self):
        _, env = safe_eval("""
def add1(x):
    return x + 1""")
        self.assertIsNotNone(env.lookup('add1'))
        result = env.lookup('add1').call(1)
        self.assertEqual(2, result)

    def test_not_execute_lines_after_return(self):
        _, env = safe_eval("""
def add1(x, c):
    return x + 1
    c.v = 200""")
        c = C()
        env.lookup('add1').call(1, c)
        self.assertEqual(c.v, 20)

    def test_support_local_variables(self):
        _, env = safe_eval("""
def add1(x):
    y = 101
    return x + y""")
        self.assertIsNotNone(env.lookup('add1'))
        result = env.lookup('add1').call(1)
        self.assertEqual(102, result)

    def test_modify_python_vals(self):
        _, env = safe_eval("""
def modify(obj):
    obj.open = obj.v
""")
        c = C()
        env.lookup('modify').call(c)
        self.assertEqual(c.open, 20)

    def test_not_write_python_functions(self):
        _, env = safe_eval("""
def modify(obj):
    obj.v = obj.open
""")
        c = C()
        env.lookup('modify').call(c)
        self.assertNotEqual(c.v, open)

    def test_use_setters_automatically(self):
        _, env = safe_eval("""
def modify(obj):
    obj.x = 2000
""")
        c = C()
        env.lookup('modify').call(c)
        self.assertEqual(c.secretx, 2000)

    def test_support_conditionals(self):
        _, env = safe_eval("""
def conditional():
    local = 0
    if 1 + 2 == 3:
        local = 1
    return local
""")
        result = env.lookup('conditional').call()
        self.assertEqual(result, 1)

    def test_support_returning_in_conditionals(self):
        _, env = safe_eval("""
def conditional():
    local = 0
    if 1 + 2 == 3:
        return 1
    return local
""")
        result = env.lookup('conditional').call()
        self.assertEqual(result, 1)

    def test_support_else_block(self):
        _, env = safe_eval("""
def conditional():
    local = 0
    if 1 + 2 == 4:
        return 1
    elif 2 + 2 == 1:
        return 10
    else:
        return 2
    return local
""")
        result = env.lookup('conditional').call()
        self.assertEqual(result, 2)

    def test_support_calling_safepyfuncs(self):
        _, env = safe_eval("""
def fib(n):
    if n <= 1:
        return 1
    else:
        return fib(n-1) + fib(n-2)
""")
        result = env.lookup('fib').call(2)
        self.assertEqual(result, 2)
        result = env.lookup('fib').call(3)
        self.assertEqual(result, 3)
        result = env.lookup('fib').call(4)
        self.assertEqual(result, 5)
        result = env.lookup('fib').call(5)
        self.assertEqual(result, 8)

    def test_not_allow_normal_pyfuncs_to_be_called(self):
        _, env = safe_eval("""
def naughty(c):
    c.open('yourcreditcardinfo.XLS')
""")
        c = C()
        exceptionthrown = True
        try:
            env.lookup('naughty').call(c)
            exceptionthrown = False
        except:
            pass
        self.assertTrue(exceptionthrown)

    def test_allow_only_approved_functions_to_be_called(self):
        import math
        _, env = safe_eval("""
def okay():
    return ceil(1.1)
""", whitelist={'ceil': math.ceil})
        self.assertEqual(env.lookup('okay').call(), 2.0)

    def test_not_allow_normal_pyfuncs_to_assigned_in_WrappedFunctions(self):
        import math
        _, env = safe_eval("""
def naughty(c):
    ceil.f = c.open
    return ceil.f
""", whitelist={'ceil': math.ceil})
        c = C()
        result = env.lookup('naughty').call(c)
        self.assertNotEqual(result, open)

if __name__ == '__main__':
    unittest.main()
