import unittest

class TestValidationError(unittest.TestCase):
	def _make_one(self, msg, field=None):
		from valid_model import ValidationError
		return ValidationError(msg, field=field)

	def test___str__(self):
		self.assertEquals(str(self._make_one('foo')), 'foo')
		self.assertEquals(str(self._make_one('foo', 'bar')), 'bar: foo')

	def test___unicode__(self):
		self.assertEquals(unicode(self._make_one('foo')), u'foo')
		self.assertEquals(unicode(self._make_one('foo', 'bar')), u'bar: foo')

	def test___repr__(self):
		self.assertEquals(repr(self._make_one('foo')), "ValidationError('foo', None)")
		self.assertEquals(repr(self._make_one('foo', 'bar')), "ValidationError('foo', 'bar')")

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
					raise ValidationError('bad stuff')
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
					raise ValidationError('bad stuff 2')

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
					raise ValidationError('bad stuff 3')


		class Foo(Object):
			basic = Generic()
			default = Generic(5)
			embedded = EmbeddedObject(Bar)
			def validate(self):
				Object.validate(self)
				if self.basic == self.default:
					raise ValidationError('bad stuff 4')

		return Foo, Bar

	def _make_list(self):
		from valid_model import Object, ValidationError
		from valid_model.descriptors import Generic, List, EmbeddedObject
		class Bar(Object):
			t1 = Generic()
			t2 = Generic(10)
			def validate(self):
				Object.validate(self)
				if self.t1 == self.t2:
					raise ValidationError('bad stuff 5')


		class Foo(Object):
			basic = Generic()
			default = Generic(5)
			embedded = List(value=EmbeddedObject(Bar))
			def validate(self):
				Object.validate(self)
				if self.basic == self.default:
					raise ValidationError('bad stuff 6')

		return Foo, Bar

	def _make_dict(self):
		from valid_model import Object
		from valid_model.descriptors import Generic, Dict
		class Foo(Object):
			basic = Generic()
			default = Generic(5)
			embedded = Dict()

		return Foo

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

	def test_descriptor_name(self):
		Foo = self._make_one()
		self.assertEquals(str(Foo.basic), 'basic')

	def test___str__(self):
		Foo = self._make_one()
		instance = Foo(basic='test')
		self.assertEquals(str(instance), str(instance.__json__()))

	def test___json__(self):
		from valid_model import ValidationError
		Foo = self._make_dict()
		instance = Foo(embedded={'a': 'b'})
		self.assertDictEqual(instance.__json__(), {'basic': None, 'default': 5, 'embedded': {'a': 'b'}})

class TestGeneric(unittest.TestCase):
	@staticmethod
	def _make_one(default=None, validator=None, mutator=None, nullable=True):
		from valid_model.descriptors import Generic
		from valid_model import Object
		class Foo(Object):
			test = Generic(
				default=default, validator=validator, mutator=mutator, nullable=nullable
			)
		return Foo()

	def test_nullable(self):
		from valid_model import ValidationError
		instance = self._make_one(nullable=False)
		self.assertRaises(ValidationError, setattr, instance, 'test', None)

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
	def _make_one():
		from valid_model.descriptors import EmbeddedObject
		from valid_model import Object
		class Foo(Object):
			test = EmbeddedObject(Object)
		return Foo()

	def test___delete__(self):
		instance = self._make_one()
		del instance.test
		self.assertEquals(instance.test, None)

class TestObjectList(unittest.TestCase):
	@staticmethod
	def _make_one(mutator=None):
		from valid_model.descriptors import List, EmbeddedObject
		from valid_model import Object
		class Foo(Object):
			test = List(value=EmbeddedObject(Object), mutator=mutator)
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

class TestObjectDict(unittest.TestCase):
	@staticmethod
	def _make_one(mutator=None):
		from valid_model.descriptors import EmbeddedObject, Dict
		from valid_model import Object
		class Foo(Object):
			test = Dict(value=EmbeddedObject(Object), mutator=mutator)
		return Foo()

	@staticmethod
	def _make_two(mutator=None):
		from valid_model.descriptors import Dict, Integer
		from valid_model import Object
		class Foo(Object):
			test = Dict(key=Integer(validator=lambda x: x > 5), mutator=mutator)
		return Foo()

	def test___set___validator(self):
		from valid_model import ValidationError
		instance = self._make_one()
		nested_instance = self._make_one()
		self.assertRaises(ValidationError, setattr, instance, 'test', 10)
		self.assertRaises(ValidationError, setattr, instance, 'test', {'foo': 10})
		instance.test = {'foo': nested_instance}

		instance2 = self._make_two()
		self.assertRaises(ValidationError, setattr, instance2, 'test', 10)
		self.assertRaises(ValidationError, setattr, instance2, 'test', {'abc': 10})
		self.assertRaises(ValidationError, setattr, instance2, 'test', {2: 10})
		instance2.test[8] = 5

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
		self.assertRaises(ValidationError, setattr, instance, 'test', 10)

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
		instance.test = 3.5
		self.assertEquals(instance.test, 3)
		instance.test = None
		self.assertEquals(instance.test, None)
		self.assertRaises(ValidationError, setattr, instance, 'test', True)
		self.assertRaises(ValidationError, setattr, instance, 'test', 'hello')
		self.assertRaises(ValidationError, setattr, instance, 'test', '15')

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
		instance.test = None
		self.assertEquals(instance.test, None)
		self.assertRaises(ValidationError, setattr, instance, 'test', True)
		self.assertRaises(ValidationError, setattr, instance, 'test', 'hello')
		self.assertRaises(ValidationError, setattr, instance, 'test', '15')

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
		self.assertEquals(instance.test, None)
		instance.test = True
		self.assertEquals(instance.test, True)
		instance.test = False
		self.assertEquals(instance.test, False)
		instance.test = None
		self.assertEquals(instance.test, None)
		instance.test = 0
		self.assertIs(instance.test, False)
		instance.test = 1
		self.assertIs(instance.test, True)
		instance = self._make_one()
		self.assertRaises(ValidationError, setattr, instance, 'test', object())

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
	def _make_one(validator=None, mutator=None, value=None):
		from valid_model.descriptors import List
		from valid_model import Object
		class Foo(Object):
			test = List(value=value, validator=validator, mutator=mutator)
		return Foo()

	def test___set___validator(self):
		from valid_model import ValidationError
		instance = self._make_one()
		instance.test = [True, 10]
		self.assertRaises(ValidationError, setattr, instance, 'test', 10)

	def test_invalid_descriptor(self):
		self.assertRaises(TypeError, self._make_one, value=5)

	def test_none(self):
		instance = self._make_one()
		instance.test = None
		self.assertEquals(instance.test, [])

class TestSet(unittest.TestCase):
	@staticmethod
	def _make_one(validator=None, mutator=None, value=None):
		from valid_model.descriptors import Set
		from valid_model import Object
		class Foo(Object):
			test = Set(value=value, validator=validator, mutator=mutator)
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

	def test_invalid_descriptor(self):
		self.assertRaises(TypeError, self._make_one, value=5)

	def test_descriptor(self):
		from valid_model import ValidationError
		from valid_model.descriptors import Integer
		instance = self._make_one(value=Integer())
		self.assertRaises(ValidationError, setattr, instance, 'test', set(['f', 'o', 'o']))
		instance.test = {1, 2, 3}

	def test_none(self):
		instance = self._make_one()
		instance.test = None
		self.assertEquals(instance.test, set())

class TestDict(unittest.TestCase):
	@staticmethod
	def _make_one(default=dict, validator=None, mutator=None, value=None, key=None):
		from valid_model.descriptors import Dict
		from valid_model import Object
		class Foo(Object):
			test = Dict(
				default=default, validator=validator, mutator=mutator, key=key, value=value
			)
		return Foo()

	def test___set___validator(self):
		from valid_model import ValidationError
		instance = self._make_one()
		instance.test = {'a': 1, 'b': 2}
		self.assertRaises(ValidationError, setattr, instance, 'test', 10)

	def test_invalid_descriptor(self):
		self.assertRaises(TypeError, self._make_one, value=5)
		self.assertRaises(TypeError, self._make_one, key=5)

	def test_none(self):
		instance = self._make_one()
		instance.test = None
		self.assertEquals(instance.test, {})

class TestDescriptorFuncs(unittest.TestCase):
	def test_descriptor_finders(self):
		from valid_model.descriptors import descriptor_classes, descriptors
		descriptors_list = descriptors()
		descriptor_cls_list = descriptor_classes()
		for cls in descriptor_cls_list:
			self.assert_(cls.__name__ in descriptors_list)
			descriptors_list.remove(cls.__name__)
		self.assertEquals(len(descriptors_list), 0)

class TestValidators(unittest.TestCase):
	def test_truthy(self):
		from valid_model.validators import truthy
		self.assertTrue(truthy(True))
		self.assertFalse(truthy(False))

	def test_falsey(self):
		from valid_model.validators import falsey
		self.assertFalse(falsey(True))
		self.assertTrue(falsey(False))

	def test_identity(self):
		from valid_model.validators import identity
		self.assertTrue(identity(True)(True))
		self.assertTrue(identity(None)(None))
		self.assertFalse(identity(True)(False))

	def test_not_identity(self):
		from valid_model.validators import not_identity
		self.assertFalse(not_identity(True)(True))
		self.assertFalse(not_identity(None)(None))
		self.assertTrue(not_identity(True)(False))

	def test_is_instance(self):
		from valid_model.validators import is_instance
		self.assertTrue(is_instance(int)(25))
		self.assertFalse(is_instance(float)("hello"))

	def test_equals(self):
		from valid_model.validators import equals
		self.assertTrue(equals(12)(12))
		self.assertFalse(equals(12)(13))

	def test_not_equals(self):
		from valid_model.validators import not_equals
		self.assertTrue(not_equals(12)(13))
		self.assertFalse(not_equals(12)(12))

	def test_gt(self):
		from valid_model.validators import gt
		self.assertTrue(gt(12)(13))
		self.assertFalse(gt(12)(12))
		self.assertFalse(gt(12)(11))

	def test_gte(self):
		from valid_model.validators import gte
		self.assertTrue(gte(12)(13))
		self.assertTrue(gte(12)(12))
		self.assertFalse(gte(12)(11))

	def test_lt(self):
		from valid_model.validators import lt
		self.assertFalse(lt(12)(13))
		self.assertFalse(lt(12)(12))
		self.assertTrue(lt(12)(11))

	def test_lte(self):
		from valid_model.validators import lte
		self.assertFalse(lte(12)(13))
		self.assertTrue(lte(12)(12))
		self.assertTrue(lte(12)(11))

	def test_contains(self):
		from valid_model.validators import contains
		self.assertTrue(contains(12)([12, 13]))
		self.assertFalse(contains(11)([12, 13]))

	def test_not_contains(self):
		from valid_model.validators import not_contains
		self.assertFalse(not_contains(12)([12, 13]))
		self.assertTrue(not_contains(11)([12, 13]))

	def test_is_in(self):
		from valid_model.validators import is_in
		self.assertTrue(is_in([12, 13])(12))
		self.assertFalse(is_in([12, 13])(11))

	def test_is_not_in(self):
		from valid_model.validators import is_not_in
		self.assertFalse(is_not_in([12, 13])(12))
		self.assertTrue(is_not_in([12, 13])(11))

	def test_any_of(self):
		from valid_model.validators import any_of, lt, gte
		v = any_of([lt(5), gte(12)])
		self.assertTrue(v(2))
		self.assertTrue(v(15))
		self.assertFalse(v(10))

	def test_compound(self):
		from valid_model.validators import all_of, any_of, lt, gte, is_instance
		range_validator = any_of([lt(5), gte(12)])
		v = all_of([is_instance(int), range_validator])
		self.assertTrue(v(2))
		self.assertTrue(v(150))
		self.assertFalse(v(10))
		self.assertFalse(v("hello"))

if __name__ == '__main__':
	unittest.main()
