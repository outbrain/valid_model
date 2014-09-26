
from valid_model.utils import is_descriptor
from valid_model.descriptors import *
import types

#TODO: figure how to bind C* functions such as NOW() to a value

def patch_descriptor(desc):
	"Add cassandra comparison operators to Generic descriptor"
	def op(op):
		def inner(self, other):
			return (self.name, op, other)
		return inner
	desc.__ge__ = types.MethodType(op('<='), desc)
	desc.__gt__ = types.MethodType(op('<'), desc)
	desc.__le__ = types.MethodType(op('>='), desc)
	desc.__lt__ = types.MethodType(op('>'), desc)
	desc.__ne__ = types.MethodType(op('!='), desc)
	desc.__eq__ = types.MethodType(op('='), desc)
	desc.__contains__ = types.MethodType(op('IN'), desc)
	return desc

def apply_cassandra_model_patch():
	"Patch all descriptors in valid_model.descriptors"
	for desc in descriptor_classes():
		patch_descriptor(desc)

apply_cassandra_model_patch()

def convert_field(col):
	if isinstance(col, basestring):
		col_str = col
	elif is_descriptor(col):
		col_str = col.name
	else:
		raise TypeError('columns must be listed as a string or descriptor')
	return col_str

class QueryBuilder(object):
	def __init__(self, tablename):
		self.tablename = tablename

class Insert(QueryBuilder):
	def __init__(self, table):
		QueryBuilder.__init__(self, table)
		self.pieces = {
			'columns': [],
			'if_ne': False,
			'options': [],
		}

	def add_columns(self, columns_list):
		for column, value in columns_list:
			self.add_column(column, value)
		return self

	def add_column(self, column, value):
		self.pieces['columns'].append((column, value))
		return self

	def ttl(self, live):
		self.pieces['options'].append('TTL {}'.format(live))
		return self

	def timestamp(self, ts):
		self.pieces['options'].append('TIMESTAMP {}'.format(ts))
		return self

	def if_not_exists(self, value=True):
		self.pieces['if_ne'] = value
		return self

	def statement(self):
		columns = self.pieces['columns']
		query = 'INSERT INTO {}'.format(self.tablename)
		query += ' ({})'.format(','.join(columns))
		query += ' VALUES ({})'.format(','.join('%(name)s' for name, _ in columns))
		if self.pieces['if_ne']:
			query += ' IF NOT EXISTS'

		if self.pieces['options']:
			query += ' USING {}'.format(' AND '.join(self.pieces['options']))

		parameters = [value for _, value in columns]
		return query, parameters

def insert(table, obj, ttl=None, timestamp=None, if_not_exists=False):
	query = Insert(table)
	if ttl:
		query = query.ttl(ttl)
	if if_not_exists:
		query = query.if_not_exists()
	if timestamp:
		query = query.timestamp(timestamp)
	model = obj.__class__
	for field in model.field_names:
		query = query.add_column(field, getattr(obj, field))
	return query.statement()

class Delete(QueryBuilder):
	"""
	<delete-stmt> ::= DELETE ( <selection> ( ',' <selection> )* )?
                  FROM <tablename>
                  ( USING TIMESTAMP <integer>)?
                  WHERE <where-clause>
                  ( IF 
                  	( EXISTS | 
                  	 ( <condition> ( AND <condition> )*)
                    ) 
				   )?

	<selection> ::= <identifier> ( '[' <term> ']' )?

	<relation> ::= <identifier> '=' <term>
	             | <identifier> IN '(' ( <term> ( ',' <term> )* )? ')'
	             | <identifier> IN '?'

	<condition> ::= <identifier> '=' <term>
	              | <identifier> '[' <term> ']' '=' <term>
	"""
	def __init__(self, table):
		QueryBuilder.__init__(self, table)
		self.pieces = {
			'selection': set(),
			'where': [],
			'options': [],
			'conditions':[],
		}

	def timestamp(self, ts):
		self.pieces['options'].append('TIMESTAMP {}'.format(ts))
		return self

	def where(self, expression):
		self.pieces['where'].append(where_clause(self, expression))
		return self

	def statement(self):
		query = 'DELETE '
		if self.pieces['selection']:
			query += ','.join(self.pieces['selection'])
		query += ' FROM {}'.format(self.tablename)
		if self.pieces['options']:
			query += ' USING {}'.format(' AND '.join(self.pieces['options']))
		query += ' WHERE {}'.format(' AND '.join(self.pieces['where']))
		if self.pieces['conditions']:
			pass

		#where
		#conditions
		return query

	def add_selections(self, columns_list):
		self.pieces['selection'].update(convert_field(col) for col in columns_list)
		return self

	def add_selection(self, column):
		self.pieces['selection'].add(convert_field(column))
		return self

_type_map = {
	String: 'text',
	Integer: 'int',
	Float: 'float',
	Bool: 'boolean',
	DateTime: 'timestamp',
}
_container_map = {
	ObjectList: 'list',
	ObjectDict: 'map',
	EmbeddedObject: 'map',
	List: 'list',
	Set: 'set',
	Dict: 'map',
}
def cassandra_model(klass):
	def generate_ddl(cls):
		tablename = getattr(cls, '__cassandra_table__', cls.__name__.lower())
		if not tablename:
			raise ValueError('__cassandra_table__ must be defined with a non-empty string')
		partition = getattr(cls, '__cassandra_partition__', None)
		if not partition:
			raise ValueError('__cassandra_partition__ must be defined as a tuple of 2 tuples')
		ordering = getattr(cls, '__cassandra_order__', None) or None
		options = getattr(cls, '__cassandra_options__', None) or []
		columns = {}
		for field in cls.field_names:
			desc = getattr(cls, field)
			desc_class = desc.__class__
			if desc_class in _container_map:
				cass_type = _container_map[desc_class]
				try:
					value_desc = desc_class.value.__class__
				except AttributeError:
					value_desc = String
				value_name = _type_map[value_desc]
				if cass_type == 'map':
					try:
						key_desc = desc_class.key.__class__
					except AttributeError:
						key_desc = String
					key_name = _type_map[key_desc]
					columns[field] = "map<{},{}>".format(key_name, value_name)
				else:
					columns[field] = "{}<{}>".format(cass_type, value_name)
			else:
				columns[field] = _type_map[desc_class]

		ddl = "CREATE TABLE {} (".format(tablename)
		for name, type_ in columns.iteritems():
			ddl += "\n\t{} {},".format(name, type_)
		ddl += "\n\tPRIMARY KEY (({})".format(','.join(partition[0]))
		if partition[1]:
			ddl += ", {}".format(','.join(partition[1]))
		ddl += ")\n)"
		if options or ordering:
			ddl += " WITH "
			if ordering:
				ddl += "CLUSTERING ORDER BY ({})".format(ordering)
			if ordering and options:
				ddl += "\nAND "	
			if options:
				ddl += "\nAND {}".join(options)

		return ddl

	setattr(klass, 'generate_ddl', classmethod(generate_ddl))
	return klass

'''
########## NOT DONE START ###############

def where_clause(obj, expression):
	field, op, other = expression
	obj.parameters.append(other)
	return' {} {}{}%s'.format(conjunction, field, op)

def selection_list(selectors):
	phrase = []
	for selector in selectors:
		if isinstance(selector, tuple):
			label = convert_field(selector[0])
			alias = selector[1]
			phrase.append("{} AS {}".format(label, alias))
		else:
			phrase.append(convert_field(selector))
	return ', '.join(phrase) if phrase else '*'


class Select(QueryBuilder):
	"""
	<select-stmt> ::= SELECT <select-clause>
	                  FROM <tablename>
	                  ( WHERE <where-clause> )?
	                  ( ORDER BY <order-by> )?
	                  ( LIMIT <integer> )?
	                  ( ALLOW FILTERING )?

	<select-clause> ::= DISTINCT? <selection-list>
	                  | COUNT '(' ( '*' | '1' ) ')' (AS <identifier>)?

	<selector> ::= <identifier>
	             | WRITETIME '(' <identifier> ')'
	             | TTL '(' <identifier> ')'
	             | <function> '(' (<selector> (',' <selector>)*)? ')'

	<relation> ::= <identifier> <op> <term>
	             | '(' <identifier> (',' <identifier>)* ')' <op> <term-tuple>
	             | <identifier> IN '(' ( <term> ( ',' <term>)* )? ')'
	             | '(' <identifier> (',' <identifier>)* ')' IN '(' ( <term-tuple> ( ',' <term-tuple>)* )? ')'
	             | TOKEN '(' <identifier> ( ',' <identifer>)* ')' <op> <term>

	<op> ::= '=' | '<' | '>' | '<=' | '>='
	<order-by> ::= <ordering> ( ',' <odering> )*
	<ordering> ::= <identifer> ( ASC | DESC )?
	<term-tuple> ::= '(' <term> (',' <term>)* ')'
	"""
	action_prefix = "SELECT {columns} FROM {name}"
	def __init__(self, table, columns=None):
		QueryBuilder.__init__(self)

		if isinstance(table, basestring):
			pass
		elif hasattr(table, '__cassandra_table__'):
			table = table.__cassandra_table__
		else:
			raise TypeError('table must be a string or have __cassandra_table__ defined')

		columns_str = selection_list(columns)

		self.query = self.action_prefix.format(columns=columns_str, table=table)
		self.first_condition = True

	def where(self, expression):
		self.pieces['where'].append(where_clause(self, expression, self.first_condition))
		self.first_condition = False
		return self

	def in_(self, test_term, container_terms):
		if is_descriptor(test_term):
			in_clause = ' {} IN'.format(test_term.name)
		else:
			in_clause = ' %s IN'
			self.parameters.append(test_term)

		container = []
		for term in container_terms:
			if is_descriptor(term):
				container.append(term.name)
			else:
				container.append('%s')
				self.parameters.append(term)

		self.query += '{} ({})'.format(in_clause, ', '.join(container))
		return self

	def limit(self, limit):
		if not isinstance(int):
			raise TypeError('limit must be an int')
		elif limit < 1:
			raise ValueError('limit must be a positive number')
		self.query += ' LIMIT {}'.format(limit)
		return self

class Update(QueryBuilder):
	"""
	<update-stmt> ::= UPDATE <tablename>
                      ( USING <option> ( AND <option> )* )?
                  	  SET <assignment> ( ',' <assignment> )*
	                  WHERE <where-clause>
	                  ( IF <condition> ( AND condition )* )?

	<assignment> ::= <identifier> '=' <term>
	               | <identifier> '=' <identifier> ('+' | '-') (<int-term> | <set-literal> | <list-literal>)
	               | <identifier> '=' <identifier> '+' <map-literal>
	               | <identifier> '[' <term> ']' '=' <term>

	<condition> ::= <identifier> '=' <term>
	              | <identifier> '[' <term> ']' '=' <term>

	<relation> ::= <identifier> '=' <term>
	             | <identifier> IN '(' ( <term> ( ',' <term> )* )? ')'
	             | <identifier> IN '?'
	"""
	def __init__(self, table):
		QueryBuilder.__init__(self, table)
		self.pieces = {
			'assignments': [],
			'where': [],
			'if': [],
			'options': [],
		}

	def where(self, expression):
		self.pieces['where'].append(where_clause(self, expression, self.first_condition))
		self.first_condition = False
		return self

	def ttl(self, live):
		self.pieces['options'].append('TTL {}'.format(live))

	def timestamp(self, ts):
		self.pieces['options'].append('TIMESTAMP {}'.format(ts))

	def statement(self):
		query = 'UPDATE {}'.format(self.tablename)
		if self.pieces['options']:
			query += ' USING {}'.format(' AND '.join(self.pieces['options']))
		query += ' SET {}'.format(','.join(self.pieces['assignments']))
		query += ' WHERE {}'.format(','.join(self.pieces['where']))
		if self.pieces['if']:
			query += ' IF {}'.format(' AND '.join(self.pieces['if']))

		return SimpleStatement(query)

from examples.cassandra_example import *
from vr.common.models.currency import Currency
Insert('jobs').statement()
Insert('jobs').ttl(500).statement()
Insert('jobs').ttl(500).timestamp('foo').statement()
Insert('jobs').ttl(500).timestamp('foo').if_not_exists().statement()
q = Insert('jobs').ttl(500).timestamp('foo').if_not_exists()
q.add_columns([Currency.code, Currency.symbol]).statement()
q.add_column(Currency.code).statement()


Select('jobs').
'''