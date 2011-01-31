"""A simple wrapper for Asterisk call files."""


from shutil import move
from time import mktime
from pwd import getpwnam
from tempfile import mkstemp
from os import chown, utime, fdopen

from path import path

from .call import Call
from .actions import Action
from .errors import ValidationError


class CallFile(object):
	"""Stores and manipulates Asterisk call files."""

	#: The default spooling directory (should be OK for most systems).
	DEFAULT_SPOOL_DIR = '/var/spool/asterisk/outgoing'

	def __init__(self, call, action, archive=None, user=None, spool_dir=None):
		"""Create a new `CallFile` obeject.

		:param obj call: A `pycall.Call` instance.
		:param obj action: Either a `pycall.actions.Application` instance
			or a `pycall.actions.Context` instance.
		:param bool archive: Should Asterisk archive the call file?
		:param str user: Username to spool the call file as.
		:param str spool_dir: Directory to spool the call file to.
		:rtype: `CallFile` object.
		"""
		self.call = call
		self.action = action
		self.archive = archive
		self.user = user
		self.spool_dir = spool_dir or self.DEFAULT_SPOOL_DIR

	def __str__(self):
		"""Render this call file object for developers.

		:returns: String representation of this object.
		:rtype: String.
		"""
		return 'CallFile-> archive: %s, user: %s, spool_dir: %s' % (
				self.archive, self.user, self.spool_dir)

	def is_valid(self):
		"""Check to see if all attributes are valid.

		:returns: True if all attributes are valid, False otherwise.
		:rtype: Boolean.
		"""
		if not isinstance(self.call, Call):
			return False

		if not isinstance(self.action, Action):
			return False

		if self.spool_dir and not path(self.spool_dir).abspath().isdir():
			return False

		if not self.call.is_valid():
			return False

		return True

	def buildfile(self):
		"""Build a call file in memory.

		:raises: `ValidationError` if this call file can not be validated.
		:returns: A list of call file directives as they will be written to the
			disk.
		:rtype: List of strings.
		"""
		if not self.is_valid():
			raise ValidationError

		cf = []
		cf += self.call.__str__()
		cf += self.action.__str__()

		if self.archive:
			cf.append('Archive: yes')

		return cf

	@property
	def contents(self):
		"""Get the contents of this call file.

		:returns: Call file contents.
		:rtype: String.
		"""
		return '\n'.join(self.buildfile())

	def writefile(self):
		"""
		Write a temporary call file to disk.

		:returns: Absolute path name of the temporary call file.
		:rtype: String.
		"""
		try:
			self.f[0]
		except AttributeError:
			self.filename

		with fdopen(self.f[0], 'w') as f:
			f.write(self.contents)
		return self.f[1]

	def spool(self):
		"""Spool the call file with Asterisk."""

		raise NoActionDefinedError

	def run(self, time=None):
		"""
		Uses the class attributes to submit this `CallFile` to the Asterisk
		spooling directory.

		:param datetime time: [optional] The date and time to spool this call
			file.
		:rtype: Boolean.
		"""
		fname = self._writefile(self._buildfile())

		if self.user:
			try:
				pwd = getpwnam(self.user)
				uid = pwd[2]
				gid = pwd[3]

				try:
					chown(fname, uid, gid)
				except:
					raise NoUserPermissionError
			except:
				raise NoUserError

		# Change the modification and access time on the file so that Asterisk
		# knows when to place the call. If time is not specified, then we place
		# the call immediately.
		try:
			time = mktime(time.timetuple())
			utime(fname, (time, time))
		except:
			pass

		try:
			move(fname, self.spool_dir+path.basename(fname))
		except:
			raise NoSpoolPermissionError

		return True
