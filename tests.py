import unittest

class TestObject(unittest.TestCase):
	def _make_one(self):
		from valid_model import Object, ValidationError
		from valid_model.descriptors import Generic
		class Foo(Object):
			basic = Generic()
			default = Generic(5)
			called_default = Generic(lambda: 'hello')
			def validate(self):
				if self.basic == self.default:
					raise ValidationError
		return Foo

	def _make_inherited(self):
		from valid_model import Object, ValidationError
		from valid_model.descriptors import Generic
		class Bar(Object):
			basic = Generic()
			default = Generic(5)
			called_default = Generic(lambda: 'hello')
			def validate(self):
				Object.validate(self)
				if self.basic == self.default:
					raise ValidationError

		class Foo(Bar):
			new_attr = Generic()
			default = Generic(10)


		return Foo

	def _make_nested(self):
		from valid_model import Object, ValidationError
		from valid_model.descriptors import Generic, EmbeddedObject
		class Bar(Object):
			t1 = Generic()
			t2 = Generic(10)
			def validate(self):
				Object.validate(self)
				if self.t1 == self.t2:
					raise ValidationError


		class Foo(Object):
			basic = Generic()
			default = Generic(5)
			embedded = EmbeddedObject(Bar)
			def validate(self):
				Object.validate(self)
				if self.basic == self.default:
					raise ValidationError

		return Foo, Bar

	def _make_list(self):
		from valid_model import Object, ValidationError
		from valid_model.descriptors import Generic, ObjectList
		class Bar(Object):
			t1 = Generic()
			t2 = Generic(10)
			def validate(self):
				Object.validate(self)
				if self.t1 == self.t2:
					raise ValidationError


		class Foo(Object):
			basic = Generic()
			default = Generic(5)
			embedded = ObjectList(Bar)
			def validate(self):
				Object.validate(self)
				if self.basic == self.default:
					raise ValidationError

		return Foo, Bar

	def test_basic(self):
		Foo = self._make_one()
		instance = Foo(basic='test')

		# simple attribute
		self.assertEquals(instance.basic, 'test')

		# attributed with default value
		self.assertEquals(instance.default, 5)

		# attributed with callable default value
		self.assertEquals(instance.called_default, 'hello') 

		# field_names was populated by the metaclass properly
		self.assertSetEqual(
			instance.field_names, 
			{'basic', 'default', 'called_default'}
		)
		self.assertSetEqual(
			Foo.field_names, 
			{'basic', 'default', 'called_default'}
		)

		# __json__
		self.assertDictEqual(
			instance.__json__(), 
			{'default': 5, 'called_default': 'hello', 'basic': 'test'}
		)

		# update
		instance.update({'default': 300})
		self.assertEquals(instance.default, 300)

	def test_scoping(self):
		# test that values are being assigned to instance and not class
		Foo = self._make_one()
		instance1 = Foo()
		instance2 = Foo()
		instance1.basic = 100
		self.assertNotEquals(instance2.basic, 100)
		self.assertNotEquals(Foo.basic, 100)

	def test_validate(self):
		from valid_model import ValidationError
		Foo = self._make_one()
		instance = Foo()
		instance.validate()
		instance.basic = instance.default = 5
		self.assertRaises(ValidationError, instance.validate)

	def test_inheritance(self):
		Foo = self._make_inherited()
		instance = Foo()
		self.assertEquals(instance.default, 10)
		self.assertSetEqual(
			instance.field_names, 
			{'basic', 'default', 'called_default', 'new_attr'}
		)
		self.assertSetEqual(
			Foo.field_names, 
			{'basic', 'default', 'called_default', 'new_attr'}
		)

	def test_nested_object(self):
		# test initization from dict
		Foo, Bar = self._make_nested()
		instance = Foo(embedded={'t1':20})
		self.assertEquals(instance.embedded.t1, 20)

		# test initization from Object
		instance2 = Foo(embedded=Bar(t1=20))
		self.assertEquals(instance2.embedded.t1, 20)

		# test update from dict
		instance2.update({'embedded': {'t2': 80}})
		self.assertEquals(instance2.embedded.t2, 80)

		# test update from Object
		instance.update({'embedded': Bar(t2=80)})
		self.assertEquals(instance.embedded.t2, 80)
		# default values overwrite old values too
		self.assertEquals(instance.embedded.t1, None)

		self.assertDictEqual(
			instance.__json__(),
			{'basic': None, 'default': 5, 'embedded': {'t1': None, 't2': 80}}
		)
	
	def test_nested_validate(self):
		# test that nested object calls validate method
		from valid_model import ValidationError
		Foo, Bar = self._make_nested()
		instance = Foo(embedded=Bar(t1=20, t2=20))
		self.assertRaises(ValidationError, instance.validate)

	def test_object_list(self):
		# test initization from list of dict
		Foo, Bar = self._make_list()
		instance = Foo(embedded=[{'t1':20}])
		self.assertEquals(instance.embedded[0].t1, 20)

		# test initization from list of Object
		instance2 = Foo(embedded=[Bar(t1=20)])
		self.assertEquals(instance2.embedded[0].t1, 20)

		# test update from list of dict
		instance2.update({'embedded': [{'t2': 80}]})
		self.assertEquals(instance2.embedded[0].t2, 80)

		# test update from list of Object
		instance.update({'embedded': [Bar(t2=80)]})
		self.assertEquals(instance.embedded[0].t2, 80)
		# default values overwrite old values too
		self.assertEquals(instance.embedded[0].t1, None)

		self.assertDictEqual(
			instance.__json__(),
			{'basic': None, 'default': 5, 'embedded': [{'t1': None, 't2': 80}]}
		)

	def test_object_list_validate(self):
		# test that object list calls validate method on each instance
		from valid_model import ValidationError
		Foo, Bar = self._make_list()
		instance = Foo(embedded=[Bar(t1=20, t2=20)])
		self.assertRaises(ValidationError, instance.validate)

class TestGeneric(unittest.TestCase):
	@staticmethod
	def _make_one(default=None, validator=None, mutator=None):
		from valid_model.descriptors import Generic
		from valid_model import Object
		class Foo(Object):
			test = Generic(
				default=default, validator=validator, mutator=mutator
			)
		return Foo()

	def test___delete__(self):
		instance = self._make_one(5)
		self.assertEquals(instance.test, 5)
		del instance.test
		self.assertEquals(instance.test, None)

	def test___set___validator(self):
		from valid_model import ValidationError
		validator = bool
		non_callable = 'not a validator'
		instance = self._make_one(validator=validator)
		self.assertRaises(TypeError, self._make_one, validator=non_callable)
		self.assertRaises(ValidationError, setattr, instance, 'test', False)

	def test___set___mutator(self):
		from valid_model import ValidationError
		def mutator(x):
			#try:
			return int(x)
			#except:
			#	raise ValidationError('not an int')
		#mutator = int
		non_callable = 'not a mutator'
		instance = self._make_one(mutator=mutator)
		self.assertRaises(TypeError, self._make_one, mutator=non_callable)
		self.assertRaises(ValidationError, setattr, instance, 'test', 'NaN')

class TestEmbeddedObject(unittest.TestCase):
	@staticmethod
	def _make_one(mutator=None):
		from valid_model.descriptors import EmbeddedObject
		from valid_model import Object
		class Foo(Object):
			test = EmbeddedObject(Object, mutator=mutator)
		return Foo()
	
	def test___set___validator(self):
		from valid_model import ValidationError
		# validator = bool
		# instance = self._make_one(validator=validator)
		# try:
		# 	instance.test = False
		# except ValidationError:
		# 	pass
		# else:
		# 	raise AssertionError('Validator should have fired')
		# self.assertRaises(TypeError, self._make_one, non_callable)

	def test___delete__(self):
		instance = self._make_one()
		del instance.test
		self.assertEquals(instance.test, None)

class TestObjectList(unittest.TestCase):
	@staticmethod
	def _make_one(mutator=None):
		from valid_model.descriptors import ObjectList
		from valid_model import Object
		class Foo(Object):
			test = ObjectList(Object, mutator=mutator)
		return Foo()
	
	def test___set___validator(self):
		from valid_model import ValidationError
		instance = self._make_one()
		self.assertRaises(ValidationError, setattr, instance, 'test', 10)
		self.assertRaises(ValidationError, setattr, instance, 'test', [10])

	def test___delete__(self):
		instance = self._make_one()
		del instance.test
		self.assertEquals(instance.test, None)

class TestString(unittest.TestCase):
	@staticmethod
	def _make_one(default=None, validator=None, mutator=None):
		from valid_model.descriptors import String
		from valid_model import Object
		class Foo(Object):
			test = String(default=default, validator=validator, mutator=mutator)
		return Foo()
	
	def test___set___validator(self):
		from valid_model import ValidationError
		instance = self._make_one()
		instance.test = u'hello'
		instance.test = 'hello'
		self.assertTrue(isinstance(instance.test, unicode))
		instance.test = 10
		self.assertEquals(instance.test, u'10')
		self.assertTrue(isinstance(instance.test, unicode))
		# validator = bool
		# instance = self._make_one(validator=validator)
		# try:
		# 	instance.test = False
		# except ValidationError:
		# 	pass
		# else:
		# 	raise AssertionError('Validator should have fired')
		# self.assertRaises(TypeError, self._make_one, non_callable)

class TestInteger(unittest.TestCase):
	@staticmethod
	def _make_one(default=None, validator=None, mutator=None):
		from valid_model.descriptors import Integer
		from valid_model import Object
		class Foo(Object):
			test = Integer(
				default=default, validator=validator, mutator=mutator
			)
		return Foo()
	
	def test___set___validator(self):
		from valid_model import ValidationError
		instance = self._make_one()
		instance.test = 5
		self.assertEquals(instance.test, 5)
		instance.test = '15'
		self.assertEquals(instance.test, 15)
		instance.test = 3.5
		self.assertEquals(instance.test, 3)
		self.assertRaises(ValidationError, setattr, instance, 'test', 'hello')

class TestFloat(unittest.TestCase):
	@staticmethod
	def _make_one(default=None, validator=None, mutator=None):
		from valid_model.descriptors import Float
		from valid_model import Object
		class Foo(Object):
			test = Float(default=default, validator=validator, mutator=mutator)
		return Foo()
	
	def test___set___validator(self):
		from valid_model import ValidationError
		instance = self._make_one()
		instance.test = 5.0
		self.assertEquals(instance.test, 5.0)
		instance.test = 10
		self.assertEquals(instance.test, 10.0)
		self.assertRaises(ValidationError, setattr, instance, 'test', 'hello')

class TestBool(unittest.TestCase):
	@staticmethod
	def _make_one(default=None, validator=None, mutator=None):
		from valid_model.descriptors import Bool
		from valid_model import Object
		class Foo(Object):
			test = Bool(default=default, validator=validator, mutator=mutator)
		return Foo()
	
	def test___set___validator(self):
		from valid_model import ValidationError
		instance = self._make_one()
		instance.test = object()
		self.assertEquals(instance.test, True)
		instance.test = True
		self.assertEquals(instance.test, True)
		instance.test = False
		self.assertEquals(instance.test, False)
		# validator = bool
		# instance = self._make_one(validator=validator)
		# try:
		# 	instance.test = False
		# except ValidationError:
		# 	pass
		# else:
		# 	raise AssertionError('Validator should have fired')
		# self.assertRaises(TypeError, self._make_one, non_callable)

class TestDateTime(unittest.TestCase):
	@staticmethod
	def _make_one(default=None, validator=None, mutator=None):
		from valid_model.descriptors import DateTime
		from valid_model import Object
		class Foo(Object):
			test = DateTime(
				default=default, validator=validator, mutator=mutator
			)
		return Foo()
	
	def test___set___validator(self):
		from valid_model import ValidationError
		from datetime import datetime
		instance = self._make_one()
		today = datetime.utcnow()
		instance.test = today
		self.assertEquals(instance.test, today)
		self.assertRaises(ValidationError, setattr, instance, 'test', 10)
	
class TestTimeDelta(unittest.TestCase):
	@staticmethod
	def _make_one(default=None, validator=None, mutator=None):
		from valid_model.descriptors import TimeDelta
		from valid_model import Object
		class Foo(Object):
			test = TimeDelta(
				default=default, validator=validator, mutator=mutator
			)
		return Foo()
	
	def test___set___validator(self):
		from valid_model import ValidationError
		from datetime import timedelta
		instance = self._make_one()
		one_minute = timedelta(minutes=1)
		instance.test = one_minute
		self.assertEquals(instance.test, one_minute)
		self.assertRaises(ValidationError, setattr, instance, 'test', 10)

class TestList(unittest.TestCase):
	@staticmethod
	def _make_one(validator=None, mutator=None):
		from valid_model.descriptors import List
		from valid_model import Object
		class Foo(Object):
			test = List(validator=validator, mutator=mutator)
		return Foo()

	def test___set___validator(self):
		from valid_model import ValidationError
		instance = self._make_one()
		instance.test = [True, 10]
		self.assertRaises(ValidationError, setattr, instance, 'test', 10)
	
class TestSet(unittest.TestCase):
	@staticmethod
	def _make_one(validator=None, mutator=None):
		from valid_model.descriptors import Set
		from valid_model import Object
		class Foo(Object):
			test = Set(validator=validator, mutator=mutator)
		return Foo()
	
	def test___set___validator(self):
		from valid_model import ValidationError
		instance = self._make_one()
		instance.test = set([True, 10])
		self.assertRaises(ValidationError, setattr, instance, 'test', 10)
	
	def test___delete__(self):
		instance = self._make_one()
		del instance.test
		self.assertEquals(instance.test, None)

class TestDict(unittest.TestCase):
	@staticmethod
	def _make_one(default=None, validator=None, mutator=None):
		from valid_model.descriptors import Dict
		from valid_model import Object
		class Foo(Object):
			test = Dict(
				default=default, validator=validator, mutator=mutator
			)
		return Foo()
	
	def test___set___validator(self):
		from valid_model import ValidationError
		instance = self._make_one()
		instance.test = {'a': 1, 'b': 2}
		self.assertRaises(ValidationError, setattr, instance, 'test', 10)
