from wsgiref.simple_server import make_server

from sinpy import HttpHandler, response, route_suffix


class Handler(HttpHandler):
    def get(self):
        return 'Index'

    index_html = response('Hej')

    @response
    def test_html(self):
        self.start_response(headers=[('Content-type', 'text/html')])
        yield 'Test!'
        yield 'Test!'

    @response
    def test2_html(self):
        self.start_response(headers=[('Content-type', 'text/html')])
        return 'Test igen!'

    @test2_html.post
    def test2_html(self, var=None):
        if var is not None:
            print('Var: %s' % var)
        return 'Test (POST) igen!'

    @route_suffix('\d*')
    class Test3(HttpHandler):
        def get(self):
            return 'Test3'

        about = response('About this page!')

        @route_suffix('/(?P<id_>\d+)')
        @response
        def contact(self, id_):
            r = '%s: Keep in touch!' % id_
            return r

    test3 = Test3()

handler = Handler()
Handler.test4_html = response('Hej')
handler.test5_html = response('Hej')
from pprint import pprint
pprint(handler.map_)

print
print(handler._call_url('GET', 'test.html'))
print(handler._call_url('GET', 'test.html'))
print(handler._call_url('GET', 'test2.html'))
print(handler._call_url('POST', 'test2.html'))
print(handler._call_url('GET', 'test35/about'))
print(handler._call_url('GET', 'test355/contact/666'))

if __name__ == '__main__':
    httpd = make_server('', 8000, handler)
    print("Serving on port 8000...")

    # Serve until process is killed
    httpd.serve_forever()
