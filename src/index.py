import os,sys
import tempfile
from cStringIO import StringIO
from urllib import quote

import web
from web.contrib.template import render_cheetah

SOURCE_DIR = os.path.dirname(os.path.abspath(__file__))
os.chdir(SOURCE_DIR)
sys.path.append(SOURCE_DIR)

from config import NS
import server
import view
import logging
logging.basicConfig(filename = 'app.log', level=logging.DEBUG, format='%(asctime)s %(message)s')

def log(s):
    logging.info(s)
urls = (
    '/', 'index',
    '/favicon.ico', 'favicon',
    '/(hudongbaike/.*)', 'deref',
    '/(baidubaike/.*)', 'deref',
    '/(zhwiki/.*)', 'deref',
    '/(ontology/.*)', 'deref',
    '/data/(.*)', 'xml',
    '/sparql/?', 'sparql',
    '/api/sparql', 'sparqlapi',
    '/lookup/?', 'lookup',
    '/lookup/(.*)', 'lookup',
    '/resource/temp', 'deref', # for merged request
    '/apex_wiki.*', 'home',
    '/static/([^\.].*)', 'static',
    '/(credits|downloads|support|publications)', 'page',
)

conn = server.connect('zhishi291')
conn_lookup = server.connect('lookup29')

app = web.application(urls, globals())
application = web.application(urls, globals(), autoreload=False).wsgifunc()

render = render_cheetah('./')

class index:
    def GET(self):
        return render.__getattr__('index')()

class page:
    def GET(self,path):
        if path=='credits':
            return render.credits()
        elif path=='downloads':
            return render.downloads()
        elif path=='support':
            return render.support()
        elif path=='publications':
            return render.publications()

class home:
    def GET(self):
        #log(web.ctx.env)
        raise web.redirect('/')

class favicon:
    def GET(self):
        return web.notfound()

class static:
    def GET(self, path):
        try:
            f = open('./static/' + path, 'r')
            r = f.read()
            f.close()
            return r
        except:
            return web.notfound()

class test:
    def GET(self, r):
        subj = u"<%s/%s>" % (NS, quote(r.encode('utf8')))
        results = conn.query([subj])
        return "\n".join([unicode(s) for s in results])

class lookup:
    def GET(self, q=""):
        results = []
        if q:
            results = conn_lookup.lookup(q)
            results = view.lookup(q, results)
            results = list(results)
        web.header('Content-Type', 'text/html')
        return render.lookup(query=q, results=results)

class xml:
    def GET(self, r):
        if '/property/' in r:
            #name = r[r.rfind('/')+1:]
            #xxx = "".join(['\\u' + hex(ord(o))[2:] for o in name])
            #r = r[:r.rfind('/')+1] + xxx
            #subj = u"<%s/%s>" % (NS, r)
            subj = u"<%s/%s>" % (NS, r)
        else:
            subj = u"<%s/%s>" % (NS, quote(r.encode('utf8')))
        q = [subj.encode('utf8')]
        (tempfd, temppath) = tempfile.mkstemp()
        os.close(tempfd)
        conn.queryxml(temppath,q)
        with open(temppath) as f:
            r = f.read()
        os.remove(temppath)
        web.header('Content-Type', 'application/rdf+xml')
        return r

class deref:
    def run(self, r, q):
        results = set(conn.query(q))
        if not results:
            raise web.notfound()
        objs = view.transform(q,results)
        return render.deref(req=r, merged=len(q)>1, **objs)

    def GET(self, r=None):
        if not r:
            raise web.notfound()
        #log(web.ctx.env)
        if '/property/' in r:
            name = r[r.rfind('/')+1:]
            xxx = "".join(['\\u' + hex(ord(o))[2:] for o in name])
            r = r[:r.rfind('/')+1] + xxx
            subj = u"<%s/%s>" % (NS, r)
        else:
            subj = u"<%s/%s>" % (NS, quote(r.encode('utf8')))
        q = [subj.encode('utf8')]
        if 'HTTP_ACCEPT' in web.ctx.env and 'application/rdf+xml' in web.ctx.env['HTTP_ACCEPT'].lower():
            raise web.seeother('/data/' + r) # 303
        else:
            return self.run(r, q)
    def POST(self):
        q = []
        for k,v in web.input().iteritems():
            if v == 'T':
                q.append('<'+k+'>')
        return self.run(None, q)

class sparql:
    def GET(self):
        web.header('Content-Type', 'text/html')
        return render.sparql(bs=[],query=None,msg=None)

    def POST(self):
        q = web.input().query
        msg, results = conn.sparql(q)
        if results:
            bs = view.sparql(q, results)
        else:
            bs = None
        web.header('Content-Type', 'text/html')
        return render.sparql(bs=bs,query=q,msg=msg)

ACCEPT_LIST = ['application/json', 'application/sparql-results+xml',
                     'application/sparql-results+json', 'text/csv']
class sparqlapi:
    def GET(self):
        try:
            query = web.input().query
        except:
            raise web.HTTPError("400 REQUEST ERROR: No query supplied")
        if 'HTTP_ACCEPT' in web.ctx.env:
            accept = web.ctx.env['HTTP_ACCEPT']
        else:
            accept = 'application/sparql-results+xml'
        if accept not in ACCEPT_LIST:
            raise web.notacceptable(data='No suitable response format available. (Supported formats:' + ', '.join(ACCEPT_LIST) + ')')

        web.header('Content-Type', accept)
        msg, response = conn.sparqlapi(query,accept)
        if msg:
            raise web.HTTPError("400 REQUEST ERROR: " + msg)
        else:
            return response

if __name__ == "__main__":
    app.run()
