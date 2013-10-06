Wouldn't it be nice to write web applications like this:

```python
class Handler(HttpHandler):
    def get(self):
        return 'Index'

    a_page = response('A page')

    @response
    def another_page_html(self):
        return 'Another page'

    @another_page_html.post
    def another_page_html(self):
        return 'Another page (POST request)'

    style_css = static_file('css/style.css')
    static = static_dir('static/*.html')
```

Ẁith SinPy you can.
