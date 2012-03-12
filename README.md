# exceptional-python-appengine

`exceptional-python-appengine` is a python appengine client for [Exceptional][], a service which
tracks errors in your web apps.

  [exceptional]: http://www.exceptional.io/

It is adapted from `exceptional-python`. https://github.com/joshfire/exceptional-python

## Usage

Vanilla

    exceptional = Exceptional('YOUR_API_KEY_HERE')
    try:
        1/0
    except Exception, e:
        exceptional.submit(e)
        raise

With optional parameters

	exceptional = Exceptional('YOUR_API_KEY_HERE', deadline=optional_urlfetch_deadline_in_seconds)
	try:
  		1/0
	except Exception, e:
  		# optional parameters to get more info on the dashboard for your exception
  		class_name = 'MyAwesomeClass' # mimics 'controller' from Ruby implementation
  		func_name = 'do_something_sweet' # mimics 'action' from Ruby implementation
  		request = None # pass in self.request if calling directly from a webapp.RequestHandler
  		exceptional.submit(e, class_name=class_name, func_name=func_name, request=request)
  		raise
