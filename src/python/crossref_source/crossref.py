from datetime import datetime
import logging
from rdflib import Graph, Literal, Namespace, URIRef
from rdflib.namespace import RDF, RDFS, FOAF, XSD

from habanero import Crossref
cr = Crossref(mailto="pierre.maillot@inria.fr")

# List of topics of interests
topics = [ "Data science", "Machine learning", "Artificial intelligence", "Deep learning", "Natural language processing", "Knowledge Graph", "Knowledge Graph Embedding", "Graph embedding", "Knowledge Graph Completion", "Knowledge Graph Construction" , "Data wrangling", "Explicability"]

logging.basicConfig(filename='app.log', level=logging.INFO)

# Retrieve the papers from the topics of interests that have been cited the most in the last 5 years
end_date = datetime.now()
start_date = end_date.replace(year=end_date.year - 5)
start_date_str = start_date.strftime("%Y-%m-%d")
end_date_str = end_date.strftime("%Y-%m-%d")

query = f"Knowledge graph"
works_results = cr.works(query=query,
                   filter={"from-pub-date": start_date_str, "until-pub-date": end_date_str},
                   sort="is-referenced-by-count",
                   order="desc",
                   limit=1000)

for item in  works_results['message']['items']:
    title = item.get('title', ['No title'])[0]
    doi = item.get('DOI', 'No DOI')
    citation_count = item.get('is-referenced-by-count', 'No citation count')
    logging.info(f"Title: {title}, DOI: {doi}, Citation Count: {citation_count}")
# logging.info(works_results)