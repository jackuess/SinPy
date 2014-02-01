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

        parts = path.split('/', 1)

        if len(parts) == 2:
            return tuple(parts)
        else:
            return parts[0], None

    def __call__(self, obj, method, path=None, fullpath=None):
        if fullpath is None:
            fullpath = path

        dispatcher = getattr(obj, '_dispatcher', Dispatcher())

        try:
            path = path.strip('/')
        except AttributeError:
            pass

        if path:
            member, ctx = dispatcher.get(obj, path)
            if member:
                return get_response(member, method, None, fullpath)

        part1, part2 = self._split_path(path)

        if not part1:
            obj.request.path = fullpath
            member, ctx = dispatcher.get(obj, method.lower(), NotFound())
            obj.response.body = member()
            return obj.response

        handler, ctx = dispatcher.get(obj, part1, NotFound())
        return get_response(handler, method, part2, fullpath)
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


class Request(object):
    pass


class Resource(threading.local):
    def __init__(self, fget=None, fpost=None, fput=None, fdelete=None,
                 obj=None, custom_routes=None):
        if obj:
            self.response = obj.response
            self.response.start()
            self.request = obj.request
        else:
            self.response = Response()
            self.request = Request()

        self._fget = fget
        self._fpost = fpost
        self._fput = fput
        self._fdelete = fdelete
        if obj:
            self._obj = obj

        if custom_routes:
            self._sp_custom_routes = custom_routes
        else:
            self._sp_custom_routes = []

    def __get__(self, obj, objtype):
        if obj is None or self._fget is None:
            return self
        else:
            return type(self)(self._fget, self._fpost, self._fput,
                              self._fdelete, obj, self._sp_custom_routes)

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


class Dispatcher(object):
    def route(self, route=None, re=None):
        if re and not re.endswith('$'):
            re += '$'
        if re and not re.startswith('^'):
            re = '^' + re

        def decorator(obj):
            def set_route(obj_):
                if not hasattr(obj, '_sp_custom_routes'):
                    obj_._sp_custom_routes = []
                if route:
                    obj_._sp_custom_routes.append(route)
                if re:
                    obj_._sp_custom_routes.append(re_compile(re))

            set_route(getattr(obj, '__func__', obj))
            return obj

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

        for custom_obj, paths in custom_routes.iteritems():
            if path in paths:
                return custom_obj, {}

            for p in paths:
                try:
                    match = p.search(path)
                    if match:
                        return custom_obj, match.groupdict()
                except AttributeError:
                    continue
        else:
            return default, {}


class Static(Resource):
    _dispatcher = Dispatcher()

    def __init__(self, path, rel=''):
        super(Static, self).__init__()

        self._path = os.path.join(os.path.dirname(rel), path)
        self._mime_type, _ = guess_type(path)
        self._sp_custom_routes = [os.path.basename(path)]

    def get(self):
        return self._get(self._path)

    @_dispatcher.route(re='.+')
    @Resource
    def default(self):
        return self._get(
            os.path.join(self._path,
                         self.request.path.strip('/')
                                          .split('/', 1)[1]))

    def _get(self, path):
        if os.path.isdir(path):
            return self._iter_dir(path)
        else:
            return self._iter_file(path)

    def _iter_dir(self, path):
        self.response.headers['Content-type'] = 'text/html'

        yield '<h1>Directory listing</h1><ul>'
        for p in os.listdir(path):
            yield '<li><a href="%s">%s</a></li>' % (
                os.path.join(self.request.path, p),
                p)
        yield '</ul>'

    def _iter_file(self, path):
        try:
            f = open(path, 'r')
        except IOError as e:
            if e.errno == errno.ENOENT:
                self.response.status_code = 404
                yield 'Not found'
            else:
                raise
        else:
            self.response.headers['Content-type'] = self._mime_type
            with  f:
                yield f.read()
