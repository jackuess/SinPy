from time import sleep

from gevent.wsgi import WSGIServer
from cherrypy.wsgiserver import CherryPyWSGIServer

from sinpy import Resource


class Site(Resource):
    def get(self):
        self.response.headers['Content-type'] = 'text/html'
        return '<p>Hello</p>'

    @Resource
    def iter(self):
        self.response.headers['Content-type'] = 'text/html'

        yield '<ul>'
        for i in 'One', 'Two', 'Three', 'Boom!':
            yield '<li>%s</li>' % i
            sleep(1)
        yield '<li>Bye</li>'
        yield '</ul>'

    @Resource()
    def list(self):
        self.response.headers['Content-type'] = 'text/html'
        return ['<p>', 'Hello', '</p>']

    class Subpage(Resource):
        def get(self):
            # self.response.headers['Content-type'] = 'text/plain'
            self.response.status_code = 500
            return 'Just kidding'

        @Resource
        def level2(self):
            return 'level2'

    level1 = Subpage()

    # sublevel1 = lambda: 'Hej'
    @Resource
    def sublevel1(self):
        return 'Hej'

    string = 'Hello'
    list_ = ['1\n', '2\n', '3\n']

if __name__ == '__main__':
    WSGIServer(('', 8080), Site()).serve_forever()
    # CherryPyWSGIServer(('0.0.0.0', 8080), Site()).start()
