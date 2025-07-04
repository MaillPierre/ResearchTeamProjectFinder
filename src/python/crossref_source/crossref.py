import logging
from rdflib import Graph, Literal, Namespace, URIRef
from rdflib.namespace import RDF, RDFS, FOAF, XSD

from habanero import Crossref
cr = Crossref(mailto="pierre.maillot@inria.fr")

# List of topics of interests
topics = [ "Data science", "Machine learning", "Artificial intelligence", "Deep learning", "Natural language processing", "Knowledge Graph", "Knowledge Graph Embedding", "Graph embedding", "Knowledge Graph Completion", "Knowledge Graph Construction" , "Data wrangling", "Explicability"]

logging.basicConfig(filename='app.log', level=logging.INFO)

# Retrieve the papers from the topics of interests that have been cited the most in the last 5
works_results = cr.works(query="Knowledge Graph", limit=5, sort="is-referenced-by-count")
for item in  works_results['message']['items']:
    logging.info(item)
# logging.info(works_results)