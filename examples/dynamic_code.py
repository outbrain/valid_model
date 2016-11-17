"""
Generate classes from a specification and generate the class declaration code
"""
from datetime import datetime, timedelta
import inspect
from valid_model.base import Object, ObjectMeta
from valid_model.descriptors import (
	String, Integer, Bool, Dict, List, TimeDelta, DateTime, Set, Generic
)

class ObjectPrinter(object):
	@classmethod
	def attr_definition(cls, descriptor):
		valid_attributes = {'default', 'validator', 'mutator', 'nullable', 'key', 'value', 'class_obj'}
		full_code = []
		for name, value in inspect.getmembers(descriptor):
			if name not in valid_attributes:
				continue
			# print repr((name, value))
			if name in ('mutator', 'validator'):
				print_val = cls.func_str(name, value)
			elif name in ('key', 'value'):
				print_val = '{}()'.format(value.__class__.__name__)
			elif name == 'default':
				print_val = cls.func_str(name, value) if callable(value) and not isinstance(value, type) else cls.static_str(value)
			else:
				print_val = cls.static_str(value)
			full_code.append('\t\t{} = {},'.format(name, print_val))
		return '\n'.join(full_code)

	@staticmethod
	def static_str(value):
		if isinstance(value, type):
			return value.__name__
		else:
			return repr(value)

	@classmethod
	def func_str(cls, name, value):
		try:
			print_val = inspect.getsource(value)
		except TypeError:
			return print_val.__name__
		idx = print_val.find(name)
		print_val = print_val[idx:].split(',')[0]
		print_val = ''.join(print_val.split('=')[1:]).strip()
		print_val = print_val[:-1] if print_val.endswith(',') else print_val
		print_val = print_val[:-1] if print_val.endswith(')') else print_val
		print_val = print_val.strip()
		return print_val

	@classmethod
	def print_class(cls, klass):
		assert issubclass(klass, Object)
		print 'class {}(Object):'.format(klass.__name__)
		for attr_name, descriptor in inspect.getmembers(klass, lambda x: isinstance(x, Generic)):
			print '\t{} = {}(\n{}\n\t)'.format(attr_name, descriptor.__class__.__name__, cls.attr_definition(descriptor))
		print ''

def print_class(klass):
	return ObjectPrinter.print_class(klass)

class ObjectMaker(object):
	KLASS_MAP = {
		'string': String,
		'integer': Integer,
		'boolean': Bool,
		'datetime': DateTime,
		'timedelta': TimeDelta,
		'map': Dict,
		'list': List,
		'set': Set,
	}
	DEFAULT_MAP = {
		'string': unicode,
		'integer': int,
		'boolean': lambda x: eval(x.lower()), # TODO: This is bad
		'datetime': lambda x: datetime.strptime(x, '%Y-%m-%dT%H:%M:%S'),
		'timedelta': lambda x: timedelta(seconds=float(x)),
		'map': lambda x: x,
		'list': lambda x: x,
		'set': lambda x: x,
	}
	@staticmethod
	def create_class(name, attrs):
		return ObjectMeta.__new__(ObjectMeta, name, (Object,), dict(attrs))

	@classmethod
	def descriptor_from_spec(cls, spec):
		klass = cls.KLASS_MAP[spec['type']]
		default = cls.DEFAULT_MAP[spec['type']](spec['default']) if spec.get('default') else None
		if spec.get('required'):
			nullable = bool(spec.get('required'))
			return klass(default=default, nullable=nullable)
		else:
			return klass(default=default)

	@classmethod
	def create_class_from_spec(cls, name, spec):
		attrs = {}
		for k, v in spec.iteritems():
			attrs[k] = cls.descriptor_from_spec(v)
		return cls.create_class(name, attrs)

def create_class(name, attrs):
	return ObjectMaker.create_class(name, attrs)

def create_class_from_spec(name, spec):
	return ObjectMaker.create_class_from_spec(name, spec)

def main():
	foo_attrs = {
		'a': String(validator=lambda x: len(x) < 5, mutator=lambda x: x.lower()),
		'b': Integer(default=5),
		'c': Bool(nullable=True),
		'd': List(value=String()),
		'e': Dict(key=String(), value=Integer())
	}
	Foo = create_class('Foo', foo_attrs)
	print_class(Foo)

	bar_attrs = {
		'a': {'type': 'string', 'required': True},
		'b': {'type': 'integer', 'default': 5},
		'c': {'type': 'boolean'},
		'd': {'type': 'datetime', 'default': '1970-01-01T00:00:00'},
		'e': {'type': 'list', 'value': {'type': 'integer', 'required': True}}
	}
	Bar = create_class_from_spec('Bar', bar_attrs)
	print_class(Bar)

if __name__ == '__main__':
	main()
