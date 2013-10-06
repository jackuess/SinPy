import os
import re

from six import add_metaclass, iteritems, string_types


def add_handler(_routes, name, handler):
    if isinstance(handler, BaseHttpHandler):
        if hasattr(handler, 'route_suffix'):
            _routes[name + handler.route_suffix] = name
        else:
            _routes[name] = name


def route_suffix(suffix):
    def decorator(f):
        f.route_suffix = suffix
        return f
    return decorator


class BaseHttpHandler(object):
    def __setattr__(self, name, value):
        add_handler(self._routes, name, value)
        return super(BaseHttpHandler, self).__setattr__(name, value)


class MetaHttpHandler(type):
    def __new__(cls, clsname, bases, dct):
        if '_routes' not in dct:
            _routes = {'': ''}
            for key, value in iteritems(dct):
                add_handler(_routes, key, value)
            dct['_routes'] = _routes
        return type.__new__(cls, clsname, bases, dct)

    def __setattr__(self, name, value):
        add_handler(self._routes, name, value)
        return super(MetaHttpHandler, self).__setattr__(name, value)


@add_metaclass(MetaHttpHandler)
class HttpHandler(BaseHttpHandler):
    def __init__(self, obj=None, fget=None, fpost=None, fput=None, fdelete=None):
        self._obj = obj
        self._fget = fget
        self._fpost = fpost
        self._fput = fput
        self._fdelete = fdelete
        self._start_response = None

    def get(self, *args, **kwargs):
        return self._call('GET', *args, **kwargs)

    def post(self, *args, **kwargs):
        return self._call('POST', *args, **kwargs)

    def put(self, *args, **kwargs):
        return self._call('PUT', *args, **kwargs)

    def delete(self, *args, **kwargs):
        return self._call('DELETE', *args, **kwargs)

    def _call(self, method, *args, **kwargs):
        f = getattr(self, '_f' + method.lower())
        try:
            return f(self._obj, *args, **kwargs)
        except TypeError:
            raise NotImplementedError(
                '%s has not been implemented for %r' % (method, self))

    def start_response(self, status='200 OK', headers=[('Content-type', 'text/plain')]):
        if self._start_response is not None:
            self._start_response(status, headers)
            self._start_response = None

    def __call__(self, environ, start_response):
        self._start_response = start_response
        self.path = environ['PATH_INFO'].strip('/')
        try:
            resp = self._call_url(environ['REQUEST_METHOD'],
                                  self.path,
                                  {})
            if isinstance(resp, string_types):
                resp = [resp]
                self.start_response()
        except NotImplementedError:
            self.start_response('404 NOT FOUND')
            resp = ['Not found']
        return resp

    def _call_url(self, method, url, ctx={}):
        ctx_, new_handler = dispatch(self, url, ctx)
        ctx.update(ctx_)
        if method in ['GET', 'POST', 'PUT', 'DELETE']:
            f = getattr(new_handler, method.lower())
            return f(**ctx)
        raise RuntimeError('Unsupported HTTP method: %s' % method)


def stringwrapper(s, format_template=True):
    def wrapped(self=None, **kwargs):
        if format_template:
            return s.format(**kwargs)
        return s
    return wrapped


@add_metaclass(MetaHttpHandler)
class response(BaseHttpHandler):
    def __init__(self, get, post=None, put=None, delete=None):
        if isinstance(get, string_types):
            get = stringwrapper(get)
        if isinstance(post, string_types):
            post = stringwrapper(post)
        if isinstance(put, string_types):
            put = stringwrapper(put)
        if isinstance(delete, string_types):
            delete = stringwrapper(delete)

        self._fget = get
        self._fpost = post
        self._fput = put
        self._fdelete = delete

    def __get__(self, obj, cls):
        return HttpHandler(
            obj, self._fget, self._fpost, self._fput, self._fdelete)

    def post(self, f):
        return response(self._fget, f, self._fput, self._fdelete)

    def put(self, f):
        return response(self._fget, self._fpost, f, self._fdelete)

    def delete(self, f):
        return response(self._fget, self._fpost, self._fput, f)


@add_metaclass(MetaHttpHandler)
class static_file(BaseHttpHandler):
    def __init__(self, path):
        self._path = path

    def __get__(self, obj, cls):
        with open(self._path, 'r') as f:
            fget = stringwrapper(f.read(), format_template=False)
        return HttpHandler(obj, fget)


class static_dir(HttpHandler):
    _routes = {'(?P<path>.+)': '_serve_file'}

    def __init__(self, path):
        self._path = path
        super(static_dir, self).__init__()

    def get(self):
        self.start_response(headers=[('Content-type', 'text/html')])
        ls = os.listdir(self._path)
        return '\n'.join(
            '<li><a href="{path}">{path}</a></li>'.format(path=p)
            for p in ls)

    @response
    def _serve_file(self, path):
        path = os.path.join(self._path, path)
        with open(path, 'r') as f:
            content = f.read()
        return content


class ReplaceUndescore(object):
    def __init__(self):
        self._in_group = False

    def __call__(self, pattern):
        r = ''
        for c in pattern:
            if c == '<':
                self._in_group = True
            elif c == '>':
                self._in_group = False
            elif c == '_' and not self._in_group:
                c = '[_.]'
            r += c
        return r


def dispatch(handler, path, ctx={}):
    for pattern, member in iteritems(handler._routes):
        pattern = ReplaceUndescore()(pattern)
        pattern = r'^%s$' % pattern
        match = re.match(pattern, path)
        if match is not None:
            ctx.update(match.groupdict())
            if member == '':
                obj = handler
            else:
                obj = getattr(handler, member)
            return ctx, obj
    try:
        path, next_path = path.split('/', 1)
    except ValueError:
        raise NotImplementedError

    for pattern, member in iteritems(handler._routes):
        pattern = r'^%s$' % pattern
        match = re.match(pattern, path)
        if match is not None:
            ctx.update(match.groupdict())
            return dispatch(getattr(handler, member), next_path, ctx)

    raise NotImplementedError
