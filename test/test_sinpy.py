from copy import deepcopy
import unittest

from mock import Mock, patch

from sinpy import HttpHandler, response, stringwrapper


class TestHttpHandler(unittest.TestCase):
    def setUp(self):
        self.httpHandler = HttpHandler()
        self.httpHandler._call = Mock()

    def test_get(self):
        self.httpHandler.get(1, 2, 3, name='Name')
        self.httpHandler._call.assert_called_once_with(
            'GET', 1, 2, 3, name='Name')

    def test_post(self):
        self.httpHandler.post(1, 2, 3, name='Name')
        self.httpHandler._call.assert_called_once_with(
            'POST', 1, 2, 3, name='Name')

    def test_put(self):
        self.httpHandler.put(1, 2, 3, name='Name')
        self.httpHandler._call.assert_called_once_with(
            'PUT', 1, 2, 3, name='Name')

    def test_delete(self):
        self.httpHandler.delete(1, 2, 3, name='Name')
        self.httpHandler._call.assert_called_once_with(
            'DELETE', 1, 2, 3, name='Name')


class TestHttpHandlerCall(unittest.TestCase):
    def test_get(self):
        my_obj = object()
        my_get = Mock()
        httpHandler = HttpHandler(obj=my_obj, fget=my_get)
        httpHandler._call('GET', 1, 2, 3, name='Name')
        my_get.assert_called_once_with(my_obj, 1, 2, 3, name='Name')

    def test_post(self):
        my_obj = object()
        my_post = Mock()
        httpHandler = HttpHandler(obj=my_obj, fpost=my_post)
        httpHandler._call('POST', 1, 2, 3, name='Name')
        my_post.assert_called_once_with(my_obj, 1, 2, 3, name='Name')

    def test_put(self):
        my_obj = object()
        my_put = Mock()
        httpHandler = HttpHandler(obj=my_obj, fput=my_put)
        httpHandler._call('PUT', 1, 2, 3, name='Name')
        my_put.assert_called_once_with(my_obj, 1, 2, 3, name='Name')

    def test_delete(self):
        my_obj = object()
        my_delete = Mock()
        httpHandler = HttpHandler(obj=my_obj, fdelete=my_delete)
        httpHandler._call('DELETE', 1, 2, 3, name='Name')
        my_delete.assert_called_once_with(my_obj, 1, 2, 3, name='Name')

    def test_raises_not_implemented(self):
        my_obj = object()
        httpHandler = HttpHandler(obj=my_obj)
        with self.assertRaises(NotImplementedError) as cm:
            httpHandler._call('DELETE', 1, 2, 3, name='Name')
        self.assertEqual(str(cm.exception),
                         'DELETE has not been implemented for %r' % httpHandler)


class TestStringWrapper(unittest.TestCase):
    def __init__(self, methodName='runTest'):
        self.expected = 'Hej'
        self.wrapped = stringwrapper(self.expected)
        super(TestStringWrapper, self).__init__(methodName)

    def test_obj_arg(self):
        class Self(object):
            # This makes makes Self raise an AttributeError if stringwrapper
            # tries to manipulate the class instance it is passed
            __slots__ = []

        self.assertEqual(self.wrapped(Self()), self.expected)

    def test_no_arg(self):
        self.assertEqual(self.wrapped(), self.expected)

    def test_kwargs(self):
        wrapped = stringwrapper('Hej {name}!')
        self.assertEqual(wrapped(name='Jacques'), 'Hej Jacques!')


class TestResponse(unittest.TestCase):
    def test_descriptor_type(self):
        class C(object):
            desc = response('Hej')
        c = C()
        self.assertTrue(isinstance(C.desc, HttpHandler))
        self.assertTrue(isinstance(c.desc, HttpHandler))

    def test_descriptor(self):
        def get():
            pass
        def post():
            pass

        def put():
            pass

        def delete():
            pass

        class C(object):
            desc = response(get, post, put, delete)

        c = C()
        with patch('sinpy.HttpHandler.__init__') as init:
            init.return_value = None
            c.desc
            init.assert_called_once_with(c, get, post, put, delete)

    def test_descriptor_decorator_post(self):
        def get():
            pass
        def post():
            pass

        def put():
            pass

        def delete():
            pass

        class C(object):
            desc = response(get)
            desc = desc.post(post)
            desc = desc.put(put)
            desc = desc.delete(delete)
        c = C()

        with patch('sinpy.HttpHandler.__init__') as init:
            init.return_value = None
            c.desc
            init.assert_called_once_with(c, get, post, put, delete)

    def test_wrapped_string_values(self):
        with patch('sinpy.stringwrapper') as mock_stringwrapper:
            mock_wrapped = Mock()
            mock_stringwrapper.return_value = mock_wrapped
            class C(object):
                desc = response('GET', 'POST', 'PUT', 'DELETE')
            c = C()
            c.desc.get(name='Name')
            mock_wrapped.assert_called_once_with(c, name='Name')
            mock_wrapped.reset_mock()
            c.desc.post(name='Name')
            mock_wrapped.assert_called_once_with(c, name='Name')
            mock_wrapped.reset_mock()
            c.desc.put(name='Name')
            mock_wrapped.assert_called_once_with(c, name='Name')
            mock_wrapped.reset_mock()
            c.desc.delete(name='Name')
            mock_wrapped.assert_called_once_with(c, name='Name')

if __name__ == '__main__':
    unittest.main()
