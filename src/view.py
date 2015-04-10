import sys
from itertools import izip,count
from franz.openrdf.model.literal import Literal
from franz.openrdf.model.value import URI
from urllib import unquote
import md5

def log(s):
    print >>sys.stderr, s

def getLocalName(uri):
    try:
        return unicode(unquote(str(uri.getLocalName())),'utf8')
    except:
        return uri.getLocalName()

def getNamespace(uri):
    s = lambda prefix: uri.getURI().startswith(prefix)
    if s('http://zhishi.me/hudongbaike/'):
        return 'hudong'
    elif s('http://zhishi.me/baidubaike/'):
        return 'baidu'
    elif s('http://zhishi.me/zhwiki/'):
        return 'zhwiki'
    elif s('http://dbpedia.org/'):
        return 'dbpedia'
    elif s('http://xmlns.com/foaf/0.1/'):
        return 'foaf'
    elif s('http://zhishi.me/ontology/'):
        return 'zhishi'
    elif s('http://www.w3.org/2000/01/rdf-schema'):
        return 'rdfs'
    elif s('http://www.w3.org/1999/02/22-rdf-syntax-ns'):
        return 'rdf'
    elif s('http://purl.org/dc/terms/'):
        return 'dcterms'
    elif s('http://www.w3.org/2004/02/skos/'):
        return 'skos'
    else:
        return None

class Value:
    def __init__(self, subj, obj):
        self.subj = subj
        self.obj = obj
    def isLiteralObj(self):
        return isinstance(self.obj, Literal)
    def getObjName(self):
        return getLocalName(self.obj)
    def getObjShort(self,w=30):
        if self.isLiteralObj():
            s = self.obj.getLabel()
        else:
            s = unicode(self.obj.getURI())
        if len(s)>w:
            s = s[:w] + '...' + s[-20:]
        return s
    def getObjNamespace(self):
        return getNamespace(self.obj)
    def isObjCheckable(self):
        return getNamespace(self.obj) in ['baidu','hudong','zhwiki']
    def isSubjThis(self):
        return any(s.id==0 for s in self.subj)
    def getImageURL(self):
        ns = getNamespace(self.subj.subj)
        if ns=='zhwiki':
            page = self.obj.getURI()
            assert page.startswith('http://zh.wikipedia.org/wiki/')
            filename = page[page.find(':',10)+1:]
            code = md5.new(filename).digest()[0].encode('hex')
            url = 'http://upload.wikimedia.org/wikipedia/commons/thumb/%s/%s/%s/100px-%s' % (code[0], code, filename, filename)
            return url
        elif ns=='hudong':
            page = self.obj.getURI()
            url = page.replace('.jpg','_140.jpg')
            return url
        else:
            return self.obj.getURI()
    def getSubjects(self):
        if isinstance(self.subj,list):
            return self.subj
        else:
            return [self.subj]

class Subject:
    def __init__(self, id, subj):
        self.id = id
        self.subj = subj
    def getSource(self):
        u = self.subj.getURI()
        u = u[7:]
        u = u[u.find('/')+1:]
        u = u[:u.find('/')]
        return u
    def getNamespace(self):
        return getNamespace(self.subj)
    def getName(self):
        return getLocalName(self.subj)

class Property:
    def __init__(self, pred):
        self.pred = pred
        self.values = []
    def add(self, subj, obj):
        self.values.append(Value(subj, obj))
    def addAll(self, property):
        self.values = self.values + property.values
    def getPredName(self):
        return getLocalName(self.pred)
    def getPredNS(self):
        return getNamespace(self.pred)
    def isSpecial(self):
        "if this predicate should be displayed a label and no 'show more'"
        return self.pred.getURI() == 'http://zhishi.me/ontology/pageRedirects' or self.pred.getURI() == 'http://zhishi.me/ontology/pageDisambiguates'
    def isResourceLink(self):
        "if this predicate should be displayed a label"
        return self.pred.getURI() == 'http://zhishi.me/ontology/relatedPage' or self.pred.getURI() == 'http://zhishi.me/ontology/internalLink' or self.pred.getURI() == 'http://www.w3.org/2004/02/skos/core#broader' or self.pred.getURI() == 'http://www.w3.org/2004/02/skos/core#narrower'
    def merge(self):
        m = {}
        for v in self.values:
            k = unicode(v.obj)
            if not k in m:
                m[k] = Value([v.subj], v.obj)
            else:
                m[k].subj.append(v.subj)
        self.values = m.values()

class BindingSet:
    def __init__(self, names):
        self.names = names
        self.aaValues = []
    def addBindingSet(self, b):
        v = []
        for name in self.names:
            v.append(Value(name, b.getValue(name)))
        self.aaValues.append(v)

def extract(r, pred, merge=False):
    "return a list of Value"
    if pred in r:
        if merge:
            r[pred].merge()
        x = r[pred].values
        del r[pred]
        return x
    else:
        return []

def transform(query, results):
    subj_id_map = dict(izip(query, count(1)))
    r = {}
    # construct map of predURI => list of (s,o)
    for stat in results:
        pred = stat.getPredicate()
        if not pred.getURI() in r:
            r[pred.getURI()] = Property(pred)
        subj = stat.getSubject()
        uri = unicode(subj.getURI())
        if '/property/' in uri:
            name = uri[uri.rfind('/')+1:]
            xxx = "".join(['\\u' + hex(ord(o))[2:] for o in name])
            uri = uri[:uri.rfind('/')+1] + xxx
        subj_id = subj_id_map[u'<%s>'%uri]
        r[pred.getURI()].add(Subject(subj_id,subj), stat.getObject())

    # add sameAs for themselves
    if u'http://www.w3.org/2002/07/owl#sameAs' in r:
        for subj in query:
            subj = subj[1:-1]
            r[u'http://www.w3.org/2002/07/owl#sameAs'].add(Subject(0,None), URI(subj))

    infobox = {}
    for pred in r.keys():
        if '/property/' in pred:
            uri = URI(pred)
            label = getLocalName(uri)
            if not label in infobox:
                infobox[label] = Property(uri)
            infobox[label].addAll(r[pred])
            del r[pred]
    infobox = infobox.values()
    for b in infobox:
        b.merge()
    infobox.sort(key=lambda b: sum(10**len(v.subj) for v in b.values), reverse=True)

    # delete revisionID
    extract(r,'http://zhishi.me/ontology/revisionID')
    return {'labels': extract(r,'http://www.w3.org/2000/01/rdf-schema#label',True),
            'query': [Subject(id,URI(subj[1:-1])) for subj,id in izip(query, count(1))],
            'cats': extract(r,'http://purl.org/dc/terms/subject'),
            'abstracts': extract(r, 'http://zhishi.me/ontology/abstract'),
            'sameAs': extract(r, 'http://www.w3.org/2002/07/owl#sameAs',True),
            # foaf:page in front
            'page': extract(r, 'http://xmlns.com/foaf/0.1/page'),
            'depiction': extract(r, 'http://zhishi.me/ontology/depictionThumbnail'),
            'thumbnail': extract(r, 'http://zhishi.me/ontology/thumbnail'),
            'infobox': infobox,
            'category': extract(r, 'http://zhishi.me/ontology/category', True),
            'relatedImage': extract(r, 'http://zhishi.me/ontology/relatedImage'),
            'props':r.values()
           }

def sparql(query, results):
    "Transform sparql results"
    bs = BindingSet(results.getBindingNames())
    for bindingSet in results:
        bs.addBindingSet(bindingSet)
    return bs

def lookup(query, results):
    for result in results:
        yield Value(None, result)
