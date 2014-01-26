import re
from unittest import TestCase

from mock import Mock, patch

from sinpy import Dispatcher, get_response, NotFound, Resource, Response


class TestGetResponse(TestCase):
    def test_get_response(self):
        class Site(Resource):
            level1 = Resource()
            level1.level2 = Resource()
            level1.level2.get = lambda: 'RESPONSE'

        response = get_response(Site(), 'GET', 'level1/level2')
        self.assertEqual(response.body,
                         ['RESPONSE'])
        self.assertEqual(response.status_code,
                         200)
        self.assertEqual(response.headers,
                         {'Content-type': 'text/plain'})

    def test_get_reponse_not_found(self):
        with patch('sinpy.NotFound') as get_response:
            get_response.return_value = 'MOCK NOT FOUND'
            response = get_response(Resource(), 'GET', 'path')

        self.assertEqual(response,
                         'MOCK NOT FOUND')

    def test__split_path(self):
        l1l2 = ('level1', 'level2')
        self.assertEqual(get_response._split_path('/level1/level2/'),
                         l1l2)
        self.assertEqual(get_response._split_path('level1/level2/'),
                         l1l2)
        self.assertEqual(get_response._split_path('/level1/level2'),
                         l1l2)
        self.assertEqual(get_response._split_path('level1/level2'),
                         l1l2)

        l1l2 = ('level1', None)
        self.assertEqual(get_response._split_path('/level1/'),
                         l1l2)
        self.assertEqual(get_response._split_path('level1/'),
                         l1l2)
        self.assertEqual(get_response._split_path('/level1'),
                         l1l2)
        self.assertEqual(get_response._split_path('level1'),
                         l1l2)

        l1l2 = ('', None)
        self.assertEqual(get_response._split_path('/'),
                         l1l2)
        self.assertEqual(get_response._split_path('//'),
                         l1l2)
        self.assertEqual(get_response._split_path('///'),
                         l1l2)

        l1l2 = (None, None)
        self.assertEqual(get_response._split_path(''),
                         l1l2)
        self.assertEqual(get_response._split_path(None),
                         l1l2)


class TestResponse(TestCase):
    def setUp(self):
        self.response = Response()

    def test_defaults(self):
        self.assertEqual(self.response.status_code, 200)
        self.assertEqual(self.response.headers, {'Content-type': 'text/plain'})

    def test_headers_list(self):
        self.response.headers = {'Header-1': 'Value 1',
                                 'Header-2': 'Value 2'}
        self.assertEqual(self.response.headers_list, [('Header-1', 'Value 1'),
                                                      ('Header-2', 'Value 2')])

    def test_status(self):
        self.response.status_code = 404
        self.assertEqual(self.response.status, '404 NOT FOUND')


class TestResource(TestCase):
    def test_response_decorator(self):
        class Site(Resource):
            class Subpage(Resource):
                @Resource
                def level2(self):
                    return 'GET'

                @level2.post
                def level2(self):
                    return 'POST'

                @level2.put
                def level2(self):
                    return 'PUT'

                @level2.delete
                def level2(self):
                    return 'DELETE'

            level1 = Subpage()

        s = Site()
        self.assertEqual(get_response(s, 'GET', 'level1/level2').body,
                         ['GET'])
        self.assertEqual(get_response(s, 'POST', 'level1/level2').body,
                         ['POST'])
        self.assertEqual(get_response(s, 'PUT', 'level1/level2').body,
                         ['PUT'])
        self.assertEqual(get_response(s, 'DELETE', 'level1/level2').body,
                         ['DELETE'])

@patch('sinpy.get_response')
class TestResourceWSGI(TestCase):
    def setUp(self):
        self.environ = {'REQUEST_METHOD': 'REQUEST_METHOD', 'PATH_INFO': 'PATH_INFO'}
        self.start_response = Mock()
        self.site = Resource()

    def test___call__(self, get_response):
        get_response.return_value.body = ['RETURN']

        r = [part for part in self.site(self.environ, self.start_response)]

        self.assertEqual(r, ['RETURN'])
        get_response.assert_called_once_with(self.site,
                                             'REQUEST_METHOD',
                                             'PATH_INFO')

    def test___call__iter(self, get_response):
        get_response.return_value.body = iter(['RETURN'])

        r = [part for part in self.site(self.environ, self.start_response)]

        self.assertEqual(r, ['RETURN'])
        get_response.assert_called_once_with(self.site,
                                             'REQUEST_METHOD',
                                             'PATH_INFO')


class TestNotFound(TestCase):
    def setUp(self):
        self.nf = NotFound()
        self.nf.response = Mock()

    def test_get(self):
        r = self.nf.get()

        self.assertEqual(self.nf.response.status_code, 404)
        self.assertEqual(r, 'Not found')

    def test_post_put_delete(self):
        for method in ['post', 'put', 'delete']:
            self.assertEqual(getattr(self.nf, method),
                             self.nf.get)


class TestThreadSafe(TestCase):
    def test(self):
        from multiprocessing.pool import ThreadPool
        from time import sleep

        class Site(Resource):
            def get(self, static=[]):
                if static:
                    self.response.status_code = 500
                else:
                    static.append(True)
                    sleep(.1)
                return 'RESPONSE'

        site = Site()
        pool = ThreadPool(processes=2)
        result1 = pool.apply_async(get_response, (site, 'GET', ''))
        result2 = pool.apply_async(get_response, (site, 'GET', ''))

        self.assertEqual(result1.get().status_code, 200)
        self.assertEqual(result2.get().status_code, 500)


class TestDispatcher(TestCase):
    # def test_add_route(self):
    #     dispatcher = Dispatcher()
    #     f = lambda: None

    #     dispatcher.add_route('custom route 1')(f)
    #     dispatcher.add_route('custom route 2')(f)

    #     self.assertEqual(dispatcher.custom_routes, {f: ['custom route 1',
    #                                                     'custom route 2']})

    # def test_add_re_route(self):
    #     dispatcher = Dispatcher()
    #     f = lambda: None

    #     dispatcher.add_route(re='.*')(f)

    #     self.assertEqual(dispatcher.custom_routes, {f: [re.compile('^.*$')]})

    # def test_remove_member(self):
    #     dct = {'member': 123}
    #     dispatcher = Dispatcher()

    #     dispatcher.add_route('custom')(dct['member'])

    #     dispatcher.remove_reference(dct['member'])
    #     self.assertNotIn(dct['member'], dispatcher.custom_routes)

    def test_get(self):
        class C(object):
            _private = 'PRIVATE'
            member1 = lambda: 123
            member2 = lambda: 321

            def __init__(self):
                self.member3 = lambda: '456'
        c = C()
        C.member3 = lambda: 456

        dispatcher = Dispatcher()
        dispatcher.add_route('custom')(C.member1)
        dispatcher.add_route(re='cust(?P<digit>\d)m')(C.member1)
        dispatcher.add_route(re.compile('^(cus)+$'))(C.member1)
        dispatcher.add_route('_notprivate')(C.member1)
        dispatcher.add_route('_C__notprivate')(C.member1)

        self.assertEqual(dispatcher.get(c, 'member1'), (c.member1, {}))
        self.assertEqual(dispatcher.get(c, 'custom'), (c.member1, {}))
        self.assertEqual(dispatcher.get(c, 'member2'), (c.member2, {}))
        self.assertEqual(dispatcher.get(c, 'member3'), (c.member3, {}))
        self.assertEqual(dispatcher.get(c, 'non-member'), (None, {}))
        self.assertEqual(dispatcher.get(c, 'non-member', 456), (456, {}))
        self.assertEqual(dispatcher.get(c, 'cust0m'), (c.member1, {'digit': '0'}))
        self.assertEqual(dispatcher.get(c, 'cust0mMMMM'), (None, {}))
        self.assertEqual(dispatcher.get(c, 'cuscuscus'), (c.member1, {}))
        self.assertEqual(dispatcher.get(c, '_private'), (None, {}))
        self.assertEqual(dispatcher.get(c, '_C__notprivate'), (c.member1, {}))
        self.assertEqual(dispatcher.get(c, '_notprivate'), (c.member1, {}))
