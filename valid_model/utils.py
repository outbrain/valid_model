def is_descriptor(obj):
	return all((
		hasattr(obj, 'name'),
		hasattr(obj, '__delete__'),
		hasattr(obj, '__get__'),
		hasattr(obj, '__set__')
	))
