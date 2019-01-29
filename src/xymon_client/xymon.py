#!/usr/bin/env python
r'''a minimalist Xymon client library in Python

Examples
########

Queries to one Xymon server::

   >>> x = Xymon('xymonserver01.example.net')
   >>> x.ping()
   'xymond 4.3.18\n'

'''
# Note:
# In case of minimalistic needs, this file can be shipped alone.

# stdlib
import collections
import functools
import logging
import multiprocessing.pool
import platform
import socket
import sys
import time

if sys.version_info[0] == 2:
	StringTypes = (str, unicode, bytearray)
elif sys.version_info[0] == 3:
	StringTypes = (str, bytearray)





__version__ = '0.2.dev0'
logger = logging.getLogger('xymon')





class Ghost(collections.namedtuple('Ghost', ('hostname', 'address', 'timestamp'))):
	__slots__ = ()

	def __new__(cls, hostname, address, timestamp):
		return super(Ghost, cls).__new__(cls, hostname, address, int(timestamp))


	def __str__(self):
		return '|'.join(map(str, self))



class Xymon(object):
	'''thin library over Xymon protocol

	Attempt to reflect :manpage:`xymon(1)` [#]_.

	.. [#] http://xymon.sourceforge.net/xymon/help/manpages/man1/xymon.1.html

	General concepts

	:colors: Valid colors are defined in :data:`color_map`.
	:times: Called "duration", "lifetime".
	           If given as a number followed by ``s``/``m``/``h``/``d``,
	           it is interpreted as being in seconds/minutes/hours/days respectively.
	           For "until OK", use -1.
	'''
	def __init__(self, server='localhost', port=1984, sender=None):
		'''
		:param str server: xymon server to send the events to
		:param int port: xymon server port
		:param str sender: name of the sender,
		                   call :func:`platform.node` when empty
		'''
		self.sender = sender or platform.node()
		self.target = (server, port)


	def __str__(self):
		return str(self.target[0])


	def __repr__(self):
		return '<Xymon %s to %s:%s>' % (
			self.sender,
			self.target[0],
			self.target[1],
		)


	def __hash__(self):
		return hash((self.sender, self.target))


	def __call__(self, data, blind=False, timeout=3):
		'''wrapper to send a message to an address (TCP)

		:param data: data to be sent
		:type data: str or unicode or bytearray
		:param bool blind: if True, does not wait an answer from the server
		:param int timeout: connection timeout
		:return: answer
		:rtype: str
		'''
		result = []
		sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
		sock.settimeout(timeout)
		sock.connect(self.target)
		if isinstance(data, bytearray):
			try:
				data = data.decode('utf8')
			except UnicodeDecodeError:
				data = data.decode(errors='ignore')
		# xymon does not know utf8
		sock.sendall(data.encode('ascii', 'xmlcharrefreplace'))
		if not blind:
			sock.shutdown(socket.SHUT_WR)
			while True:
				chunk = sock.recv(4096)
				if not chunk:
					break
				result+= [chunk.decode('ascii', 'replace')]
		sock.close()
		return ''.join(result)


	@property
	def headline(self):
		return 'Message generated by %s at %s' % (
			self.sender,
			time.strftime('%FT%T'),
		)


	def status(self, hostname, testname, color, text='', lifetime=None, group=None):
		'''
		:param str hostname:
		:param str testname:
		:param str color:
		:param str text:
		:param lifetime: defines how long this status is valid after
		                 being received by the Xymon server
		:type lifetime: None or integer or str
		:param group: direct alerts from the status to a specific group
		:type group: str or None
		'''
		data = ['status']
		if lifetime:
			data+= ['+%s' % (lifetime,)]
		if group:
			data+= ['/group:%s' % (group,)]
		data+= [
			' %s.%s %s %s' % (
				hostname,
				testname,
				color,
				self.headline,
			)
		]
		if text:
			data+= ['\n%s' % (text,)]
		return self(''.join(data))


	def notify(self, hostname, testname, text=''):
		return self(
			'notify %s.%s %s' % (
				hostname,
				testname,
				text,
			)
		)


	def data(self, hostname, dataname, text=''):
		return self(
			'data %s.%s\n%s' % (
				hostname,
				dataname,
				text,
			)
		)


	def disable(self, hostname, testname='*', duration=-1, text=''):
		'''
		:param str hostname:
		:param str testname: use an asterisk (``*``) to disable all tests
		:param duration:
		:type duration: integer or str
		:param str text:
		'''
		return self(
			'disable %s.%s %s %s' % (
				hostname,
				testname,
				duration,
				text,
			)
		)


	def enable(self, hostname, testname):
		'''re-enables a test that had been disabled

		:param str hostname:
		:param str testname:
		'''
		return self(
			'%s.%s' % (hostname, testname)
		)


	def query(self, hostname, testname):
		'''query the Xymon server for the latest status reported for
		this particular test

		:param str hostname:
		:param str testname:
		'''
		return self(
			'query %s.%s' % (hostname, testname)
		)


	def config(self, filename):
		return self(
			'config %s' % (filename,)
		)


	def drop(self, hostname, testname=None):
		'''remove all data stored about this status

		When removing an `hostname` as whole, it is assumed that you
		have already deleted the host from the :file:`hosts.cfg`
		configuration file.

		:param str hostname:
		:param str testname:
		'''
		if testname:
			return self('drop %s' % (hostname,))
		return self('drop %s %s' % (hostname, testname))


	def rename(self, old, new, hostname=None):
		if hostname:
			return self(
				'rename %s %s %s' % (
					hostname,
					old,
					new,
				)
			)
		return self('rename %s %s' % ( old, new,))


	def xymondlog(self, hostname, testname):
		return self(
			'xymondlog %s.%s' % (hostname, testname)
		)


	def xymondxlog(self, hostname, testname):
		return self(
			'xymondxlog %s.%s' % (hostname, testname)
		)


	def xymondboard(self, criteria=None, fields=None):
		'''
		:param criteria: (example: color=red)
		:type criteria: str or dict or list
		:param fields: (example: hostname,testname,cookie,ackmsg,dismsg)
		:type fields: str or list
		:rtype: list
		'''
		query = ['xymondboard']
		if criteria:
			if isinstance(criteria, dict):
				criteria = [
					'%s=%s' % item
					for item in criteria.items()
				]
			query.append(
				joiniterable(criteria, ' ')
			)

		if fields:
			query.append(
				'fields=%s' % (
					joiniterable(fields, ','),
				)
			)

		result = self(' '.join(query)).splitlines()
		if fields:
			return [
				row.split('|')
				for row in result
			]

		return result


	def xymondxboard(self, criteria=None, fields=None):
		'''
		Same as :meth:`xymondboard`
		:rtype: str
		:return: the board **XML serialized**
		'''
		return self('xymondxboard %s %s' % (criteria, fields))


	def hostinfo(self, criteria=None):
		'''
		:param str criteria:
		:rtype: list(list(str))
		'''
		return [
			line.split('|')
			for line in self(
				'hostinfo %s' % (criteria,)
			).splitlines()
		]


	def download(self, filename):
		return self('download %s' % (filename,))


	def client(self, hostname, ostype, collectorid=None, hostclass=None):
		raise NotImplementedError
	def clientlog(self, hostname, *sectioname):
		raise NotImplementedError


	def ping(self):
		'''ping the server which should return it's version

		:rtype: str
		'''
		return self('ping')


	def pullclient(self):
		raise NotImplementedError


	def ghostlist(self):
		'''list of ghost clients seen by the Xymon server

		Ghosts are systems that report data to the Xymon server,
		but are not listed in the hosts.cfg file.

		https://www.xymon.com/help/manpages/man1/ghostlist.cgi.1.html

		:rtype: list(Ghost)
		'''
		data = []
		for line in self('ghostlist').splitlines():
			try:
				data.append(Ghost(*line.split('|', 2)))
			except:
				logger.error(
					'invalid ghostlist line: %r',
					line,
					exc_info=True
				)
		return data


	def schedule(self, timestamp=None, command=None):
		'''schedule command for execution at a later time

		E.g. used to schedule disabling of a host or service at sometime in the future.
		If no parameters are given, the currently scheduled tasks are listed in the response.

		:param command: a complete Xymon command such as the ones listed above or
		                'cancel JOBID' to cancel a previously scheduled command
		:type command: str or None
		:param timestamp: the Unix epoch time when the command will be executed
		:param timestamp: int or None
		'''
		if timestamp and command:
			return self('schedule %s %s' % (timestamp, command))
		return self('schedule')


	def notes(self, filename):
		return self('notes %s' % (filename,))


	def usermsg(self, identifier):
		return self('usermsg %s' % (identifier,))


	def modify(self, hostname, testname, color, source, cause):
		return self(
			'modify %s.%s %s %s %s' % (
				hostname,
				testname,
				color,
				source,
				cause,
			)
		)



class Xymons(object):
	def __init__(self, servers, port=1984, sender=platform.node(), thread=False):
		'''
		:param list server: list of xymon servers to send the events to
		:param int port: xymon server port
		:param str sender: name of the sender
		:param bool thread: parallelize the calls
		'''
		self.thread = thread
		self.children = [
			Xymon(server, port, sender)
			for server in servers
		]


	def _apply(self, name, *args, **kwargs):
		'''
		:param str name: name of the function to be called on each :attr:`children`
		:rtype: dict
		'''
		result = {}
		for child in self.children:
			try:
				result[child] = getattr(child, name)(*args, **kwargs)
			except:
				logger.error(
					'while calling: %s: %s(*%r, **%r)',
					child,
					name,
					args,
					kwargs,
					exc_info=True,
				)
		return result


	def _apply_async(self, name, *args, **kwargs):
		'''
		Same as :meth:`_apply`, but call each children in a different thread.
		Will be faster on slow networks or when at least one child is expected to fail.
		'''
		result = {}
		try:
			pool = multiprocessing.pool.ThreadPool(
				processes=len(self.children)
			)
			tasks = {
				child: pool.apply_async(
					getattr(child, name),
					args, kwargs,
				)
				for child in self.children
			}
			for child, task in tasks.items():
				try:
					result[child] = task.get()
				except:
					logger.error(
						'while calling: %s: %s(*%r, **%r)',
						child,
						name,
						args,
						kwargs,
						exc_info=True,
					)
		finally:
			pool.close()
		return result


	def __getattr__(self, name):
		if not self.thread:
			return functools.partial(self._apply, name)
		return functools.partial(self._apply_async, name)



def joiniterable(obj, sep=','):
	'''join `obj` with `sep` if it is a non-string iterable

	:param mixed obj: object to be joined
	:param sep str:
	:rtype: str
	'''
	if hasattr(obj, '__iter__') \
	and not isinstance(obj, StringTypes):
		return sep.join(obj)
	return str(obj)
