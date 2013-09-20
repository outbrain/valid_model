from datetime import datetime, timedelta
from .exc import ValidationError

class Generic(object):
	name = None
	def __init__(self, default=None, validator=None, mutator=None):
		self.default = default
		if validator is None:
			self.validator = lambda x: True
		elif not callable(validator):
			raise TypeError('validator must be callable')
		else:
			self.validator = validator

		if mutator is None:
			self.mutator = lambda x: x
		elif not callable(mutator):
			raise TypeError('mutator must be callable')
		else:
			self.mutator = mutator

	def __get__(self, instance, klass=None):
		if instance is None:
			return self
		return getattr(instance, '_fields')[self.name]

	def __set__(self, instance, value):
		if value is not None:
			try:
				value = self.mutator(value)
			except (TypeError, ValueError, ValidationError), ex:
				raise ValidationError("{}: {}".format(self.name, ex))
			if not self.validator(value):
				raise ValidationError(self.name)
		getattr(instance, '_fields')[self.name] = value
		return value

	def __delete__(self, instance):
		getattr(instance, '_fields')[self.name] = None

class EmbeddedObject(Generic):
	def __init__(self, class_obj, mutator=None):
		self.class_obj = class_obj
		validator = lambda x: isinstance(x, class_obj)
		Generic.__init__(
			self, default=class_obj, validator=validator, mutator=mutator
		)
	
	def __set__(self, instance, value):
		if isinstance(value, dict):
			value = self.class_obj(**value)
		return Generic.__set__(self, instance, value)

class ObjectList(Generic): 
	def __init__(self, class_obj, mutator=None):
		self.class_obj = class_obj
		validator = lambda x: all(isinstance(i, class_obj) for i in x)
		Generic.__init__(
			self, default=list, validator=validator, mutator=mutator
		)
	
	def __set__(self, instance, value):
		if not isinstance(value, list):
			raise ValidationError("{} is not a list".format(value))
		new_value = []
		for v in value:
			if isinstance(v, dict):
				new_value.append(self.class_obj(**v))
			elif isinstance(v, self.class_obj):
				new_value.append(v)
			else:
				raise ValidationError(
					"Cannot convert from {} to {}".format(
						v.__class__.__name__, self.class_obj.__name__
					)
				)
		return Generic.__set__(self, instance, new_value)

class ObjectDict(Generic): 
	def __init__(self, class_obj, mutator=None):
		self.class_obj = class_obj
		validator = lambda x: all(isinstance(i, class_obj) for i in x.itervalues())
		Generic.__init__(
			self, default=dict, validator=validator, mutator=mutator
		)
	
	def __set__(self, instance, value):
		if not isinstance(value, dict):
			raise ValidationError("{!r} is not a dict".format(value))
		new_value = {}
		for k, v in value.iteritems():
			if isinstance(v, dict):
				new_value[k] = self.class_obj(**v)
			elif isinstance(v, self.class_obj):
				new_value[k] = v
			else:
				raise ValidationError(
					"Cannot convert from {} to {}".format(
						v.__class__.__name__, self.class_obj.__name__
					)
				)
		return Generic.__set__(self, instance, new_value)

class String(Generic):
	"""
	This descriptor will convert any set value to a python unicode string before
	being mutated and validated.  If the value is type(str) it will be decoded 
	using utf-8
	"""
	def __init__(self, default=None, validator=None, mutator=None):
		Generic.__init__(
			self, default=default, validator=validator, mutator=mutator
		)
	
	def __set__(self, instance, value):
		if value is None or isinstance(value, unicode):
			pass
		elif isinstance(value, str):
			value = unicode(value, 'utf-8')
		else:
			value = unicode(value)
		return Generic.__set__(self, instance, value)

class Integer(Generic):
	"""
	This descriptor will convert any set value to a int before being mutated and
	validated.
	Note: booleans can be cast to int
	"""
	def __init__(self, default=None, validator=None, mutator=None):
		Generic.__init__(
			self, default=default, validator=validator, mutator=mutator
		)
	
	def __set__(self, instance, value):
		if value is not None:
			try:
				value = int(value)
			except ValueError:
				raise ValidationError("{!r} is not an int".format(value))
		return Generic.__set__(self, instance, value)

class Float(Generic):
	"""
	This descriptor will convert any set value to a float before being mutated 
	and validated.
	"""
	def __init__(self, default=None, validator=None, mutator=None):
		Generic.__init__(
			self, default=default, validator=validator, mutator=mutator
		)
	
	def __set__(self, instance, value):
		if value is not None:
			try:
				value = float(value)
			except ValueError:
				raise ValidationError("{!r} is not a float".format(value))
		return Generic.__set__(self, instance, value)

class Bool(Generic):
	"""
	This descriptor will convert any set value to a bool before being mutated 
	and validated.
	"""
	def __init__(self, default=None, validator=None, mutator=None):
		Generic.__init__(
			self, default=default, validator=validator, mutator=mutator
		)
	
	def __set__(self, instance, value):
		value = bool(value)
		return Generic.__set__(self, instance, value)

class DateTime(Generic):
	"""
	This descriptor will assert any set value is a datetime or None before being
	mutated and validated.
	"""
	def __init__(self, default=None, validator=None, mutator=None):
		Generic.__init__(
			self, default=default, validator=validator, mutator=mutator
		)
	
	def __set__(self, instance, value):
		if value is not None and not isinstance(value, datetime):
			raise ValidationError("{!r} is not a datetime".format(value))
		return Generic.__set__(self, instance, value)

class TimeDelta(Generic):
	"""
	This descriptor will assert any set value is a timedelta or None before 
	being mutated and validated.
	"""
	def __init__(self, default=None, validator=None, mutator=None):
		Generic.__init__(
			self, default=default, validator=validator, mutator=mutator
		)
	
	def __set__(self, instance, value):
		if value is not None and not isinstance(value, timedelta):
			raise ValidationError("{!r} is not a timedelta".format(value))
		return Generic.__set__(self, instance, value)

class List(Generic):
	def __init__(self, default=list, validator=None, mutator=None):
		Generic.__init__(
			self, default=default, validator=validator, mutator=mutator
		)
	
	def __set__(self, instance, value):
		if not isinstance(value, list):
			raise ValidationError("{!r} is not a list".format(value))
		return Generic.__set__(self, instance, value)

class Set(Generic):
	def __init__(self, default=set, validator=None, mutator=None):
		Generic.__init__(
			self, default=default, validator=validator, mutator=mutator
		)
	
	def __set__(self, instance, value):
		if not isinstance(value, set):
			raise ValidationError("{!r} is not a set".format(value))
		return Generic.__set__(self, instance, value)

class Dict(Generic):
	def __init__(self, default=dict, validator=None, mutator=None):
		Generic.__init__(
			self, default=default, validator=validator, mutator=mutator
		)
	
	def __set__(self, instance, value):
		if not isinstance(value, dict):
			raise ValidationError("{!r} is not a dict".format(value))
		return Generic.__set__(self, instance, value)


def descriptors():
	def is_descriptor(obj):
		return all((
			hasattr(obj, 'name'),
			hasattr(obj, '__delete__'),
			hasattr(obj, '__get__'),
			hasattr(obj, '__set__')
		))

	return [
		name for name, value in globals().iteritems() 
		if is_descriptor(value) and issubclass(value, Generic)
	]

__all__ = descriptors()