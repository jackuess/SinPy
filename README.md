SinPy
=====

Usage
-----
Ẁith SinPy you can write web applications like this:

```python
class Handler(HttpHandler):
    def get(self):
        return 'Serving GET /'

    def post(self):
        return 'Serving POST /'

    def put(self):
        return 'Serving PUT /'

    def delete(self):
        return 'Serving DELETE /'

application = Handler()
```

### Subpages


```python
class Handler(HttpHandler):
    a_page = response('Serving POST /a_page')
    another_page_html = response('Serving GET /another_page.html')
    yet_another = response('Serving GET /yet_another',
                           'Serving POST /yet_another')
```

### Subpages as decorators

```python
class Handler(HttpHandler):
    @response
    def another_page_html(self):
        return 'Serving GET /another_page.html'

    @another_page_html.post
    def another_page_html(self):
        return 'Serving POST /another_page.html'
```

### Static files

```python
class Handler(HttpHandler):
    # GET /style.css
    style_css = static_file('css/style.css')

    # GET /static/*.html
    static = static_dir('static/*.html')
```


