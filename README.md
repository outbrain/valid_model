valid_model
===========

The valid_model library is intended to allow declarative modeling of an object schema in a similar way to various ORM and form validation libraries while making as few assumptions as possible about the way it will be used.

Attributes in a `valid_model.Object` instance are guaranteed to have all fields exist with defined restrictions and defaults available. In addition each field can have a mutator function applied to it to enforce uniformity.  An example of this could be make a `String` attribute always be uppercase.

You can nest `Object` classes inside one another using the `EmbeddedObject`, `Set`, `Dict`, and `List` descriptors

The available descriptors are in `valid_model.descriptors` and include:
`Generic`, `String`, `Integer`, `Float`, `Bool`, `DateTime`, `TimeDelta`, `List`, `Set`, `Dict`, and `EmbeddedObject`

When initializing an `Object` all initial values should be passed in as keyword arguments.
When setting an `EmbeddedObject` attribute, it will automatically convert a `dict` to the appropriate `Object` subclass.

`Object` instances have `Object.__json__` defined to be used as a hook to convert objects into `dict` for easy serialization.

```python
class Person(Object):
  name = String(nullable=False)
  homepage = String()

class BlogPost(Object):
  title = String(nullable=False, mutator=lambda x: x.title())
  updated = DateTime(nullable=False, default=datetime.utcnow) # default to time object is created
  published = DateTime() # default value will be None
  author = EmbeddedObject(Person)
  contributors = List(value=EmbeddedObject(Person))
  tags = List(value=String(nullable=False))

  def validate(self):
    super(BlogPost, self).validate()
    if self.published is not None and self.published > self.updated:
      raise ValidationError('a post cannot be published at a later date than it was updated')

post = BlogPost(title='example post', author={'name': 'Josh'}, tags=['tag1', 'tag2'])
"""
post.__json__() would output
{
  'title': 'Example Post',
  'author': {
      'name': 'Josh',
      'homepage': None
   },
   'contributors': [],
   'updated': datetime(2014, 10, 6, 10, 23),
   'published': None,
   'tags': ['tag1', 'tag2']
}
"""
```
##Descriptor Options

|Keyword Arg | Default | Description |
|:-----------|--------|:------------------
|nullable | `True`<sup>1</sup> | determines if it is valid for an attribute to be set to None
|mutator | no mutator | allows some mutation to occur on the value. a common use case would be to format a string to always be uppercase
|validator | no validator| a function which returns truthy if the value is valid
|default | `None`<sup>2</sup>  | a scalar value or function which the attribute will be set to on object initialization if no value is specified at in the constuctor
|value| no descriptor<sup>3</sup> | a descriptor to validate values in the container attribute
| key | no descriptor<sup>4</sup> | a descriptor to validate keys in the container attribute
<sup>1</sup> Not available on `Set`, `List`, and `Dict`. If an attribute with that descriptor is set to `None` it will actually set it to an empty instance of their respective types  
<sup>2</sup> Container objects `Set`, `List`, and `Dict` initialize to an empty instance of their respective types  
<sup>3</sup> Only available on `Dict`, `List`, and `Set`  
<sup>4</sup> Only available on `Dict`  

`EmbededObject` takes one argument which is the `Object` class that is being embedded.

##How Validation Works
Validation occurs whenever an attribute is set.

1. Typechecking and any type coercion implemented occurs
2. The value is checked if it is None  
    * If it is None and nullable == False a ValidationError is raised otherwise it is set to None
3. If mutator function is defined it will run
4. If a validator function is defined it will run  
    * A ValidationError is raised if the validator function returns falsey


### Complex Validation
In addition to validators being defined on individual attributes there is a validate method on Object instances which may be overridden for more complicated validation logic that may include a combination of multiple fields.  By default it will just revalidate all attributes of an `Object` instance.

