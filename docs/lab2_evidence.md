The browser sent an HTTP GET request for the path / to the Django development server at 127.0.0.1:8000, and the terminal logged it as GET / HTTP/1.1 with status 200.
Django checked config/urls.py, which handed the empty path over to core/urls.py, where path("", views.home, name="home") matched and selected the home view.
The home view built a context dictionary and called render() with core/home.html, which extends base.html, so the template engine filled in headline and active_requests and added the shared header, stylesheet link and footer.
Django returned an HTML document with status 200 and a text/html content type, and because the page links to styles.css, the browser then made a second, separate request that returned text/css with status 200.

# Lab 2 Evidence

## First request (Checkpoint B)
- Browser URL: http://127.0.0.1:8000/
- Method: GET
- Status: 200
- Date and time: (the time from your server log, e.g. 14/Nov/2026 21:32:06)

## HTTP evidence table
| Request | Expected | Actual |
|---|---|---|
| GET / | 200 | 200 |
| GET /about/ | 200 | 200 |
| GET /static/core/css/styles.css | 200 | 200 |
| GET /does-not-exist/ | 404 | 404 |

## Break and repair
| Change | Error name | Message / evidence |
|---|---|---|
| Rename home.html to home2.html | TemplateDoesNotExist | (fill in as you go) |
| core:about to core:about_us | NoReverseMatch | (fill in as you go) |
| views.home to views.hom | AttributeError | (fill in as you go) |
| styles.css to style.css | 404 on CSS | (fill in as you go) |