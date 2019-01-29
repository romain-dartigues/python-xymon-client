#!/usr/bin/env python
'''a CLI for the library
'''
# stdlib
import argparse
import collections
import inspect
import logging
import pprint
import sys

if sys.version_info[0] == 2:
	from itertools import izip_longest as zip_longest
elif sys.version_info[0] == 3:
	from itertools import zip_longest

# local
from . import xymon





logger = logging.getLogger('xymon')
REQUIRED = object()





class XymonServer(collections.namedtuple('XymonServer', ('hostname', 'port'))):
	__slots__ = ()

	def __new__(cls, hostname, port):
		return super(XymonServer, cls).__new__(cls, hostname, int(port or 1984))

	def __str__(self):
		return '{}:{}'.format(self.hostname, self.port)


class ActionServer(argparse.Action):
	'''separate hostname and port
	'''
	def __call__(self, parser, namespace, values, option_string=None):
		server, port = values.partition(':')[::2]
		if getattr(namespace, self.dest) is None:
			setattr(namespace, self.dest, [])
		getattr(namespace, self.dest).append(XymonServer(server, port))


class KWArgs(dict):
	@classmethod
	def from_namespace(cls, namespace, exclude):
		'''
		:param argparse.Namespace namespace:
		:param set exclude: key to be excluded
		:rtype: KWArgs
		'''
		return KWArgs(
			(k, v)
			for k, v in namespace._get_kwargs()
			if k not in exclude
		)

	def __str__(self):
		return ', '.join(
			'{}={!r}'.format(k, self[k])
			for k in sorted(self)
		)


def build_parser_for(parser, obj):
	'''
	:param argparse._SubParsersAction parser:
	:param type obj: a class to generate parser for
	:rtype: None
	'''
	for k, v in obj.__dict__.items():
		if k[0] != '_' and callable(v):
			sub = parser.add_parser(k, help=v.__doc__)
			sub.usage = v.__doc__
			argspec = inspect.getargspec(v)
			args = zip_longest(
				argspec.args[::-1],
				() if argspec.defaults is None else argspec.defaults[::-1],
				fillvalue=REQUIRED
			)

			for arg, default in list(args)[::-1]:
				if arg not in {'self', 'cls'}:
					kwargs = {}
					if default is REQUIRED:
						kwargs['required'] = True
						kwargs['help'] = 'required'
					else:
						kwargs['default'] = default
						kwargs['help'] = 'default: %(default)r'
						kwargs['type'] = type(default)
					sub.add_argument('--{}'.format(arg), **kwargs)


def get_parser():
	'''
	:rtype: list(argparse.ArgumentParser, set)
	'''
	parser = argparse.ArgumentParser(
		description='A Xymon client',
		formatter_class=argparse.RawDescriptionHelpFormatter,
	)
	parser.add_argument('-q', '--quiet',
		action='store_const', const=0, dest='verbose', default=1)
	parser.add_argument('-v', '--verbose', action='count')
	parser.add_argument('-n', '--dry-run', dest='noop', action='store_true')
	parser.add_argument('-s', '--server', action=ActionServer,
		help='comma separated list of Xymon servers (host:port)', required=True)
	parser.add_argument('--sender',
		help='sender name exposed to Xymon (default: current machine hostname)')

	subparsers = parser.add_subparsers(
		title='Commands', dest='action',
		help='Command passed to Xymon server(s); refer to https://www.xymon.com/help/manpages/man1/xymon.1.html',
		metavar='[ACTION]',
	)

	parser_flags = {action.dest for action in parser._actions}

	build_parser_for(subparsers, xymon.Xymon)

	return (parser, parser_flags)


def main():
	parser, exclude = get_parser()
	arg = parser.parse_args()

	logging.basicConfig(
		format='%(levelname)s: %(message)s',
		datefmt='%F %T',
		level=min(max(logging.CRITICAL - (arg.verbose * 10), logging.DEBUG), logging.CRITICAL)
	)

	if len(arg.server) > 1:
		# FIXME: the port is not per server
		x = xymon.Xymons([_.hostname for _ in arg.server], arg.server[0].port, arg.sender)
	else:
		x = xymon.Xymon(arg.server[0].hostname, arg.server[0].port, arg.sender)

	func = getattr(x, arg.action)
	kwargs = KWArgs.from_namespace(arg, exclude)

	logger.debug('going to execute: {}({})'.format(arg.action, kwargs))
	if arg.noop:
		logger.info('dry-run mode, no further action is performed')
	else:
		result = func(**kwargs)
		if isinstance(result, str):
			print(result)
		else:
			pprint.pprint(result)






if __name__ == '__main__':
	main()
