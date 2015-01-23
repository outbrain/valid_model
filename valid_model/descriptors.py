from datetime import datetime, timedelta
import warnings
from .exc import ValidationError
from .base import Object, Generic
from .utils import is_descriptor


class EmbeddedObject(Generic):
	def __init__(self, class_obj):
		self.class_obj = class_obj
		validator = lambda x: isinstance(x, class_obj)
		Generic.__init__(
			self, default=class_obj, validator=validator
		)

	def __set__(self, instance, value):
		if isinstance(value, dict):
			value = self.class_obj(**value)
		return Generic.__set__(self, instance, value)

class ObjectList(Generic): # pragma: no cover
	def __init__(self, class_obj, mutator=None):
		warnings.warn("ObjectList(class_obj) should be replaced with List(value=EmbeddedObject(class_obj))", DeprecationWarning)
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

class ObjectDict(Generic): # pragma: no cover
	def __init__(self, class_obj, mutator=None):
		warnings.warn("ObjectDict(class_obj) should be replaced with Dict(value=EmbeddedObject(class_obj))", DeprecationWarning)
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
	def __init__(self, default=None, validator=None, mutator=None, nullable=True):
		Generic.__init__(
			self, default=default, validator=validator, mutator=mutator, nullable=nullable
		)

	def __set__(self, instance, value):
		if value is None or isinstance(value, unicode):
			pass
		elif isinstance(value, str):
			value = unicode(value, 'utf-8')
		else:
			raise ValidationError("{!r} is not a string".format(value))
		return Generic.__set__(self, instance, value)

class Integer(Generic):
	"""
	This descriptor will convert any set value to an int before being mutated and
	validated.
	"""
	def __init__(self, default=None, validator=None, mutator=None, nullable=True):
		Generic.__init__(
			self, default=default, validator=validator, mutator=mutator, nullable=nullable
		)

	def __set__(self, instance, value):
		if value is not None:
			if not isinstance(value, (int, long, float)) or isinstance(value, bool):
				raise ValidationError("{!r} is not an int".format(value))
			else:
				value = int(value)
		return Generic.__set__(self, instance, value)

class Float(Generic):
	"""
	This descriptor will convert any set value to a float before being mutated
	and validated.
	"""
	def __init__(self, default=None, validator=None, mutator=None, nullable=True):
		Generic.__init__(
			self, default=default, validator=validator, mutator=mutator, nullable=nullable
		)

	def __set__(self, instance, value):
		if value is not None:
			if not isinstance(value, (int, long, float)) or isinstance(value, bool):
				raise ValidationError("{!r} is not a float".format(value))
			else:
				value = float(value)
		return Generic.__set__(self, instance, value)

class Bool(Generic):
	"""
	This descriptor will convert any set value to a bool before being mutated
	and validated.
	"""
	def __init__(self, default=None, validator=None, mutator=None, nullable=True):
		Generic.__init__(
			self, default=default, validator=validator, mutator=mutator, nullable=nullable
		)

	def __set__(self, instance, value):
		if value is not None:
			if value in (0, 1) or isinstance(value, bool):
				value = bool(value)
			else:
				raise ValidationError("{!r} is not a bool".format(value))
		return Generic.__set__(self, instance, value)

class DateTime(Generic):
	"""
	This descriptor will assert any set value is a datetime or None before being
	mutated and validated.
	"""
	def __init__(self, default=None, validator=None, mutator=None, nullable=True):
		Generic.__init__(
			self, default=default, validator=validator, mutator=mutator, nullable=nullable
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
	def __init__(self, default=None, validator=None, mutator=None, nullable=True):
		Generic.__init__(
			self, default=default, validator=validator, mutator=mutator, nullable=nullable
		)

	def __set__(self, instance, value):
		if value is not None and not isinstance(value, timedelta):
			raise ValidationError("{!r} is not a timedelta".format(value))
		return Generic.__set__(self, instance, value)

class List(Generic):
	def __init__(self, default=list, value=None, validator=None, mutator=None):
		Generic.__init__(
			self, default=default, validator=validator, mutator=mutator, nullable=False
		)
		if value is not None and not isinstance(value, Generic):
			raise TypeError('value must be None or an instance of Generic')
		self.value = value

	def __set__(self, instance, value):
		if value is None:
			value = []
		elif not isinstance(value, list):
			raise ValidationError("{!r} is not a list".format(value))

		if self.value is not None:
			new_value = self.get_default()
			dummy = Object()
			for v in value:
				v = self.value.__set__(dummy, v)
				new_value.append(v)
			value = new_value
		return Generic.__set__(self, instance, value)

class Set(Generic):
	def __init__(self, default=set, value=None, validator=None, mutator=None):
		Generic.__init__(
			self, default=default, validator=validator, mutator=mutator, nullable=False
		)
		if value is not None and not isinstance(value, Generic):
			raise TypeError('value must be None or an instance of Generic')
		self.value = value

	def __set__(self, instance, value):
		if value is None:
			value = set()
		elif not isinstance(value, set):
			raise ValidationError("{!r} is not a set".format(value))
		if self.value is not None:
			new_value = self.get_default()
			dummy = Object()
			for v in value:
				v = self.value.__set__(dummy, v)
				new_value.add(v)
			value = new_value
		return Generic.__set__(self, instance, value)

class Dict(Generic):
	def __init__(self, default=dict, key=None, value=None, validator=None, mutator=None):
		Generic.__init__(
			self, default=default, validator=validator, mutator=mutator, nullable=False
		)
		if key is not None and not isinstance(key, Generic):
			raise TypeError('key must be None or an instance of Generic')
		self.key = key
		if value is not None and not isinstance(value, Generic):
			raise TypeError('value must be None or an instance of Generic')
		self.value = value

	def __set__(self, instance, value):
		if value is None:
			value = {}
		elif not isinstance(value, dict):
			raise ValidationError("{!r} is not a dict".format(value))
		new_value = self.get_default()
		dummy = Object()
		for k, v in value.iteritems():
			if self.key is not None:
				k = self.key.__set__(dummy, k)
			if self.value is not None:
				v = self.value.__set__(dummy, v)
			new_value[k] = v
		return Generic.__set__(self, instance, new_value)


def descriptors():
	return [
		name for name, value in globals().iteritems()
		if is_descriptor(value) and issubclass(value, Generic)
	]

def descriptor_classes():
	return [
		value for value in globals().itervalues()
		if is_descriptor(value) and issubclass(value, Generic)
	]

__all__ = ['descriptor_classes'] + descriptors()
