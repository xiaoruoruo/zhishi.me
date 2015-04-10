import os
import sys
from time import time
from urllib import quote
import logging

from franz.openrdf.sail.allegrographserver import AllegroGraphServer
from franz.openrdf.repository.repository import Repository
from franz.miniclient.request import RequestError
from franz.openrdf.query.query import QueryLanguage
from franz.openrdf.model import URI
from franz.openrdf.model.statement import Statement
from franz.openrdf.rio.rdfxmlwriter import RDFXMLWriter

def log(s):
    logging.info(s.encode('utf8'))

class Server:
    def __init__(self, repo):
        self.repo = repo
    def wrap(self, callee, *args):
        conn = self.repo.getConnection()
        r = callee(conn, *args)
        conn.close()
        return r

    def query(self, *args):
        return self.wrap(query, *args)
    def queryxml(self, *args):
        return self.wrap(queryxml, *args)
    def lookup(self, *args):
        return self.wrap(lookup, *args)
    def sparql(self, *args):
        return self.wrap(sparql, *args)
    def sparqlapi(self, *args):
        return self.wrap(sparqlapi, *args)


def connect(repo):
    server = AllegroGraphServer('172.16.2.21', user='web', password=os.environ['AG_PASSWORD'])
    catalog = server.openCatalog('zhishime')
    myRepository = catalog.getRepository(repo, Repository.OPEN)
    myRepository.initialize()

    log("Repository %s is up!" % (
        myRepository.getDatabaseName(),))
    return Server(myRepository)

def query(conn, subjList):
    for subj in subjList:
        start = time()
        results = conn.getStatements(subj, None, None)
        results = list(results)
        log('Subject query %s cost %d return %d' % (subj, int(time()*1000-start*1000), len(results)))
        for result in results:
            yield result
        if '/category/' in subj:
            results = conn.getStatements(None, None, subj)
            for result in results:
                if result.getPredicate().getURI() == 'http://www.w3.org/2004/02/skos/core#broader':
                    yield Statement(result.getObject(), URI('http://www.w3.org/2004/02/skos/core#narrower'), result.getSubject())

def queryxml(conn, out, subjList):
    for subj in subjList:
        start = time()
        conn.exportStatements(subj, None, None, False, RDFXMLWriter(out))
        # TODO output 404 with empty response if no results
        log('Subject query %s cost %d' % (subj, int(time()*1000-start*1000)))

def lookup(conn, query):
    log('Lookup: %s' % query)
    subj = '<'+quote(query.encode('utf8'))+'>'
    results = conn.getStatements(subj, '<lookup>', None)
    for result in results:
        yield result.getObject()

def sparql(conn, q):
    # limit excution time: 10 seconds
    q = "prefix franzOption_queryTimeout: <franz:10>\n" + q
    start = time()
    tupleQuery = conn.prepareTupleQuery(QueryLanguage.SPARQL, q)
    msg = ''
    try:
        results = tupleQuery.evaluate()
    except RequestError as e:
        msg = e.message
        results = None
    log(u'SPARQL query %s cost %d' % (q, int(time()*1000-start*1000)))
    return msg, results

def sparqlapi(conn, q, accept):
    tupleQuery = conn.prepareTupleQuery(QueryLanguage.SPARQL, q)
    msg = ''
    try:
        response = tupleQuery.evaluate_generic_query(accept=accept)
    except RequestError as e:
        msg = e.message
        response = None
    return msg, response

def test():
    print "\n".join([unicode(s) for s in server.query(server.connect(),['<http://zhishi.me/hudongbaike/resource/Apple>'])])
