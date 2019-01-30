#!/usr/bin/env python
r'''helpers for the Xymon Python-based library
'''
# stdlib
import functools
import re





class Color(float):
	'''describe a Xymon color (status)
	'''
	name = None
	'''textual representation of the color
	'''

	def __new__(cls, x, name):
		result = float.__new__(cls, x)
		result.name = name
		return result


	def __str__(self):
		return self.name


	def __repr__(self):
		return '<Color %s>' % (self.name,)



class Helper(object):
	r'''
	Examples::

	   # create an object with default hostname and default service
	   >>> x = Helper(Xymon('xymon.example.net'), 'www.intra.example.net', 'http')
	   # add a message
	   >>> x+= '&red something gone pear shaped\n'
	   # send the content of the current buffer with text added at the end
	   # override the global color of the message (from red to yellow)
	   # clear the buffer
	   >>> x.status('but it is not *that* bad', color=yellow)
	   # now the buffer has been cleared
	   # send another message, same hostname but different service name
	   >>> x.status('do not shoott the messenger!', service='logs')
	'''
	r_color = re.compile(r'&(green|yellow|red|clear)\b')
	'''extract status identifiers
	'''

	def __init__(self, xymon, hostname=None, testname=None):
		self.defaults = {}
		if hostname:
			self.defaults['hostname'] = hostname
		if testname:
			self.defaults['testname'] = testname
		self.data = ''
		self.xymon = xymon


	def __iadd__(self, other):
		self.data+= other
		return self


	@property
	def color(self):
		'''current highest level color or :data:`clear` if none found
		'''
		return max(self.get_colors(self.data, clear))


	def get_colors(self, text, default=None):
		'''extract all colors from text

		:param str text:
		:param default:
		:type default: None or :class:`Color`
		:rtype: list(:class:`Color`)
		'''
		result = [
			color_map['%s' % color]
			for color in self.r_color.findall(text)
		]
		if not result and default is not None:
			result+= [default]
		return result


	def status(self, message='', **kwargs):
		'''call :meth:`Xymon.status`

		Generate the query from merging :attr:`defaults`
		with any additionnal `kwargs` given.
		The final message is the addition of `message` to
		any existing :attr:`data` and `kwargs['text']`.
		Status `color` will be guessed from message text
		if not explicitely set in the `kwargs`.

		:param str message:
		:param dict kwargs: additionnal parameters
		'''
		params = self.defaults.copy()
		params.update(kwargs)
		# build the message
		params['text'] = '%s%s%s' % (
			self.data,
			message,
			kwargs.get('text', ''),
		)
		# empty the buffer
		self.data = ''

		if 'color' not in kwargs:
			# no color has been explicitely set, find it from the text
			colors = self.get_colors(params['text'], clear)
			params['color'] = max(colors)

		return self.xymon.status(**params)


	def __getattr__(self, name):
		def _host(name, **kwargs):
			params = {'hostname': self.defaults['hostname']}
			params.update(kwargs)
			return getattr(self.xymon, name)(**params)

		def _host_test(name, **kwargs):
			params = self.defaults.copy()
			params.update(kwargs)
			return getattr(self.xymon, name)(**params)

		def _host_test_text(name, message='', **kwargs):
			params = self.defaults.copy()
			params.update(kwargs)
			# build the message
			params['text'] = '%s%s%s' % (
				self.data,
				message,
				kwargs.get('text', ''),
			)
			# empty the buffer
			self.data = ''
			return getattr(self.xymon, name)(**params)

		if name in {'rename', 'client', 'clientlot', 'modify'}:
			return functools.partial(_host, name)

		if name in {'disable', 'enable', 'query', 'drop', 'xymondlog', 'xymondxlog', 'modify'}:
			return functools.partial(_host_test, name)

		if name in {'notify', 'data'}:
			return functools.partial(_host_test_text, name)

		return getattr(self.xymon, name)





purple = Color('inf', 'purple')
blue = Color('nan', 'blue')
clear = Color(0, 'clear')
green = Color(1, 'green')
yellow = Color(2, 'yellow')
red = Color(3, 'red')

color_map = {
	purple: purple,
	blue: blue,
	clear: clear,
	green: green,
	yellow: yellow,
	red: red,

	'purple': purple,
	'blue': blue,
	'clear': clear,
	'green': green,
	'yellow': yellow,
	'red': red,
}
