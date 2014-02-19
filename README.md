patrol
======

A web app for monitoring new pages in a wiki.

Dependencies:
- [webapp2](http://webapp-improved.appspot.com/), which requires WebOb and Paste
- [mwclient](https://github.com/mwclient/mwclient) for accessing the MediaWiki API
- [Jinja2](http://jinja.pocoo.org/) for templates

Once you have the dependencies, you should be able to run it with

 python wikipatrol.py

It should start serving on [port 8081 of your localhost](http://127.0.0.1:8081).
