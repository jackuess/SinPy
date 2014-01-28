from copy import copy
import errno
from mimetypes import guess_type
import os.path
from re import compile as re_compile
import threading
from types import FunctionType


class get_response(object):
    def _split_path(self, path):
        if not path:
            return None, None

        parts = path.strip('/').split('/', 1)

        if len(parts) == 2:
            return tuple(parts)
        else:
            return parts[0], None

    def __call__(self, obj, method, path=None):
        part1, part2 = self._split_path(path)
        dispatcher = getattr(obj, '_dispatcher', Dispatcher())

        if not part1:
            member, ctx = dispatcher.get(obj, method.lower())
            obj.response.body = member()
            return obj.response

        handler, ctx = dispatcher.get(obj, part1, NotFound())
        if isinstance(handler, (basestring, list)):
            return Response(body=handler)
        else:
            return get_response(handler, method, part2)
get_response = get_response()


class Response(object):
    def __init__(self, status_code=200, headers=None, body=None):
        self.start(status_code, headers, body)

    def start(self, status_code=200, headers=None, body=None):
        if headers is None:
            headers = {'Content-type': 'text/plain'}

        self.status_code = status_code
        self.headers = headers
        self._body = body

    @property
    def headers_list(self):
        return [(name, value)
                for name, value in self.headers.iteritems()]

    @property
    def status(self):
        return {200: '200 OK',
                404: '404 NOT FOUND',
                500: '500 INTERNAL SERVER ERROR'}[self.status_code]

    @property
    def body(self):
        if hasattr(self._body, '__iter__'):
            return self._body
        else:
            return [self._body]

    @body.setter
    def body(self, value):
        self._body = value


class Resource(threading.local):
    def __init__(self, fget=None, fpost=None, fput=None, fdelete=None, obj=None):
        if obj:
            self.response = obj.response
            self.response.start()
        else:
            self.response = Response()
        self._fget = fget
        self._fpost = fpost
        self._fput = fput
        self._fdelete = fdelete
        if obj:
            self._obj = obj

    def __get__(self, obj, objtype):
        if obj is None or self._fget is None:
            return self
        else:
            return type(self)(self._fget, self._fpost, self._fput,
                              self._fdelete, obj)

    def get(self, *args, **kwargs):
        return self._fget(self._obj, *args, **kwargs)

    def post(self, *args, **kwargs):
        if len(args) == 1 and type(args[0]) is FunctionType:
            return type(self)(self._fget, args[0], self._fput, self._fdelete)
        else:
            return self._fpost(self._obj, *args, **kwargs)

    def put(self, *args, **kwargs):
        if len(args) == 1 and type(args[0]) is FunctionType:
            return type(self)(self._fget, self._fpost, args[0], self._fdelete)
        else:
            return self._fput(self._obj, *args, **kwargs)

    def delete(self, *args, **kwargs):
        if len(args) == 1 and type(args[0]) is FunctionType:
            return type(self)(self._fget, self._fpost, self._fput, args[0])
        else:
            return self._fdelete(self._obj, *args, **kwargs)

    def __call__(self, *args):
        def application(environ, start_response):
            response = get_response(self, environ['REQUEST_METHOD'],
                                    environ['PATH_INFO'])

            try:
                first_part = response.body.next()
            except (StopIteration, AttributeError):
                start_response(response.status,
                               response.headers_list)
            else:
                start_response(response.status,
                               response.headers_list)
                yield first_part

            for part in response.body:
                yield part

        if len(args) == 1 and type(args[0]) is FunctionType:
            return type(self)(args[0])
        else:
            return application(*args[:2])


class NotFound(Resource):
    def get(self):
        self.response.status_code = 404
        return 'Not found'

    post = get
    put = get
    delete = get


class static(Resource):
    def __init__(self, path, rel=''):
        super(static, self).__init__()

        self._path = os.path.join(os.path.dirname(rel), path)
        self._mime_type, _ = guess_type(path)

    def get(self):
        try:
            f = open(self._path, 'r')
        except IOError as e:
            if e.errno == errno.ENOENT:
                self.response.status_code = 404
                return 'Not found'
            else:
                raise
        else:
            self.response.headers['Content-type'] = self._mime_type
            with  f:
                return f.read()


class Dispatcher(object):
    def add_route(self, route=None, re=None):
        if re and not re.endswith('$'):
            re += '$'
        if re and not re.startswith('^'):
            re = '^' + re

        def decorator(obj):
            if hasattr(obj, '__func__'):
                obj = obj.__func__
            if not hasattr(obj, '_sp_custom_routes'):
                obj._sp_custom_routes = []
            if route:
                obj._sp_custom_routes.append(route)
            if re:
                obj._sp_custom_routes.append(re_compile(re))
        return decorator

    def get(self, obj, path, default=None):
        if not path.startswith('_'):
            try:
                return getattr(obj, path), {}
            except AttributeError:
                pass

        custom_routes = {}
        for attr in obj.__class__.__dict__:
            attr = getattr(obj, attr)
            if hasattr(attr, '_sp_custom_routes'):
                custom_routes[attr] = attr._sp_custom_routes
        for attr in obj.__dict__:
            attr = getattr(obj, attr)
            if hasattr(attr, '_sp_custom_routes'):
                custom_routes[attr] = attr._sp_custom_routes

        for obj, paths in custom_routes.iteritems():
            if path in paths:
                return obj, {}

            for p in paths:
                try:
                    match = p.search(path)
                    if match:
                        return obj, match.groupdict()
                except AttributeError:
                    continue
        else:
            return default, {}
