"""
Basic validators which can compose other validators
Any function which returns a boolean can be used as a validator.

All of the defined functions other than truthy and falsey take a parameter to
define a validator function.

# x is not None
not_identity(None)

# x >= 100 or x < 20
any_of(gte(100), lt(20))

# isinstance(x, dict) and (not x or x in ['a', 'b', 'c'])
all_of(is_instance(dict), any_of(falsey, is_in(['a', 'b', 'c'])))
"""
def truthy(value):
	return bool(value)

def falsey(value):
	return not bool(value)

def identity(value):
	return lambda x: x is value

def not_identity(value):
	return lambda x: x is not value

def is_instance(value):
	return lambda x: isinstance(x, value)

def equals(value):
	return lambda x: x == value

def not_equals(value):
	return lambda x: x != value

def gt(value):
	return lambda x: x > value

def gte(value):
	return lambda x: x >= value

def lt(value):
	return lambda x: x < value

def lte(value):
	return lambda x: x <= value

def contains(value):
	return lambda x: value in x

def not_contains(value):
	return lambda x: value not in x

def is_in(value):
	return lambda x: x in value

def is_not_in(value):
	return lambda x: x not in value

def any_of(value):
	return lambda x: any(v(x) for v in value)

def all_of(value):
	return lambda x: all(v(x) for v in value)

