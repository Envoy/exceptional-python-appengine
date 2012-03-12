from cStringIO import StringIO
import datetime
import gzip
import logging
import os
import sys
import traceback
import types
import urllib

from google.appengine.api import urlfetch

try:
    import json
except ImportError:
    import simplejson as json

__version__ = '0.1.0'

EXCEPTIONAL_PROTOCOL_VERSION = 6
EXCEPTIONAL_API_ENDPOINT = "http://api.getexceptional.com/api/errors"

def memoize(func):
    """A simple memoize decorator (with no support for keyword arguments)."""

    cache = {}

    def wrapper(*args):
        if args in cache:
            return cache[args]
        cache[args] = value = func(*args)
        return value

    wrapper.__name__ = func.__name__
    wrapper.__doc__ = func.__doc__
    if hasattr(func, '__module__'):
        wrapper.__module__ = func.__module__
    wrapper.clear = cache.clear

    return wrapper


class Exceptional(object):

    def __init__(self, api_key, deadline=5):
        self.deadline = deadline

        try:
            self.api_key = api_key
            self.api_endpoint = EXCEPTIONAL_API_ENDPOINT + "?" + urllib.urlencode({
                    "api_key": self.api_key,
                    "protocol_version": EXCEPTIONAL_PROTOCOL_VERSION
                    })
        except AttributeError:
            pass

    def submit(self, exc, class_name=None, func_name=None, request=None):
        """Submit the exception to exceptional
        """
        info = {}

        try:
            info.update(self.request_info(class_name, func_name, request))
            info.update(self.environment_info())
            info.update(self.exception_info(exc, sys.exc_info()[2]))

            logging.debug(info)

            payload = self.compress(json.dumps(info))
            headers = {}
            headers['Content-Encoding'] = 'gzip'
            headers['Content-Type'] = 'application/json'

            result = urlfetch.fetch(self.api_endpoint, deadline=self.deadline, payload=payload, method=urlfetch.POST, headers=headers)
            logging.debug('exceptional post result:' + str(result.status_code))
        except Exception, e:
            raise Exception("Cannot submit %s because of %s" % (info, e), e)

    @staticmethod
    def compress(bytes):
        """Compress a bytestring using gzip."""

        stream = StringIO()
        # Use `compresslevel=1`; it's the least compressive but it's fast.
        gzstream = gzip.GzipFile(fileobj=stream, compresslevel=1, mode='wb')
        try:
            try:
                gzstream.write(bytes)
            finally:
                gzstream.close()
            return stream.getvalue()
        finally:
            stream.close()

    # http://docs.exceptional.io/api/publish/
    def request_info(self, class_name, func_name, request):
        info = {}
        info['request'] = {}

        # use class_name to mimic Ruby controller
        if class_name:
            info['request']['controller'] = class_name

        # use func_name to mimic Ruby action
        if func_name:
            info['request']['action'] = func_name

        if request:
            info['request']['request_method'] = request.method
            info['request']['parameters'] = dict(request.params)
            info['request']['url'] = request.url
            info['request']['headers'] = dict(request.headers)

        # doesn't seem to show up anywhere in the dashboard
        info['request']['remote_ip'] = 'NOT IMPLEMENTED'

        return info

    @memoize
    def environment_info(self):
        """
        Return a dictionary representing the server environment.

        The idea is that the result of this function will rarely (if ever)
        change for a given app instance. Ergo, the result can be cached between
        requests.
        """

        return {
                "application_environment": {
                    "framework": "appengine",
                    "env": dict(os.environ),
                    "language": "python",
                    "language_version": sys.version.replace('\n', ''),
                    "application_root_directory": self.project_root()
                    },
                "client": {
                    "name": "exceptional-python-appengine",
                    "version": __version__,
                    "protocol_version": EXCEPTIONAL_PROTOCOL_VERSION
                    }
                }

    def exception_info(self, exception, tb, timestamp=None):
        backtrace = []
        for tb_part in traceback.format_tb(tb):
            backtrace.extend(tb_part.rstrip().splitlines())

        if timestamp is None:
            timestamp = datetime.datetime.utcnow()

        return {
                "exception": {
                    "occurred_at": timestamp.isoformat(),
                    "message": str(exception),
                    "backtrace": backtrace,
                    "exception_class": self.exception_class(exception)
                    }
                }

    def exception_class(self, exception):
        """Return a name representing the class of an exception."""

        cls = type(exception)
        if cls.__module__ == 'exceptions':  # Built-in exception.
            return cls.__name__
        return "%s.%s" % (cls.__module__, cls.__name__)

    @memoize
    def project_root(self):

        """
        Return the root of the current pylons project on the filesystem.
        """

        return os.path.dirname(__file__)

    @staticmethod
    def filter_params(params):
        """Filter sensitive information out of parameter dictionaries.
        """

        for key in params.keys():
            if "password" in key:
                del params[key]
        return params