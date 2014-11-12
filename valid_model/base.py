# encoding: utf-8
"""
The purpose of the Object class is to be able to create objects from arbitrary 
dictionaries and be able to validate them.  Primarily this is for being used 
with MongoDB to validate documents and to ensure that all expected fields exists
 and only those defined fields exist.

There is no direct tie into MongoDB though so this can be used for any class 
which contains state that ought to be validated.

When an attribute on the Object instance is set (if the value is not None) a 
mutator function may be executed to transform the value being set.  A simple
example of this would be to make sure that a String attribute is always 
lowercase.

After the value is mutated it is then validated.  A ValidationError will be 
raised if the mutator fails or the value being set fails the attribute's
validator.

Each Object also has a validate method which can check conditions that deal with
multiple attributes within an Object.
"""
from .exc import ValidationError

class Generic(object):
	"""
	Base descriptor class for all valid_model descriptors.

	default: a scalar or callable that an attribute will be initialized to when
	         an object is constructed
	mutator: function that will alter value being set prior to validator 
	         function being executed
	validator: function that must return truthy or a ValidationError will be 
	           raised
	nullable: determines if None is a valid value for this attribute
	"""
	name = None
	def __init__(self, default=None, validator=None, mutator=None, nullable=True):
		if not callable(default):
			self.default = lambda: default
		else:
			self.default = default
		self.nullable = nullable
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

	def get_default(self):
		return self.default()

	def __get__(self, instance, klass=None):
		if instance is None:
			return self
		return getattr(instance, '_fields')[self.name]

	def __set__(self, instance, value):
		if value is None and not self.nullable:
			raise ValidationError("{} is not nullable".format(self.name))
		elif value is not None:
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

	def __str__(self):
		return self.name

class ObjectMeta(type):
	"""
	Metaclass used to set the attribute name to each descriptor in the Object
	class
	"""
	def __new__(mcs, name, bases, attrs):
		field_names = set()
		for attr, value in attrs.iteritems():
			if isinstance(value, Generic):
				value.name = attr
				attrs[attr] = value
				field_names.add(attr)

		for base in bases:
			parent = base.__mro__[0]
			for attr, value in vars(parent).iteritems():
				if isinstance(value, Generic) and attr not in attrs:
					value.name = attr
					attrs[attr] = value
					field_names.add(attr)
		attrs['field_names'] = field_names
		return type.__new__(mcs, name, bases, attrs)

class Object(object):
	"""
	Base class for creating object models
	"""
	__metaclass__ = ObjectMeta
	field_names = None # stub gets set in ObjectMeta.__new__

	def __init__(self, **kwargs):
		self._fields = {}
		cls = self.__class__
		for field in cls.field_names:
			self._fields[field] = getattr(cls, field).default()
		for key, value in kwargs.items():
			if key in self._fields:
				setattr(self, key, value)

	def __str__(self):
		return str(self.__json__())

	def __json__(self):
		"""
		Convert the Object instance and any nested Objects into a dict.
		"""
		json_doc = {}
		for key, value in self._fields.iteritems():
			if hasattr(value, '__json__'):
				json_doc[key] = value.__json__()
			elif isinstance(value, list):
				json_doc[key] = [
					v.__json__() if hasattr(v, '__json__') else v
					for v in value
				]
			elif isinstance(value, dict):
				json_doc[key] = dict(
					(k, v.__json__()) if hasattr(v, '__json__') else (k, v)
					for k, v in value.iteritems()
				)
			else:
				json_doc[key] = value
				
		return json_doc
	
	def update(self, doc):
		"""
		Update attributes from a dict-like object
		"""
		for key, value in doc.iteritems():
			if key in self._fields:
				setattr(self, key, value)

	def validate(self):
		"""
		Allows for multi-field validation
		"""
		for key in self._fields:
			setattr(self, key, self._fields[key])
		for key, value in self._fields.iteritems():
			if hasattr(value, 'validate'):
				value.validate()
			elif isinstance(value, list):
				for v in value:
					if hasattr(v, 'validate'):
						v.validate()


__all__ = ['Object']