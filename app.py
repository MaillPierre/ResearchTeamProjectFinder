# Loads all the RDF files in data/rdf and creates a graph
# that can be queried using SPARQL

from rdflib import Graph, URIRef, Literal
from rdflib.plugins.sparql import prepareQuery
from rdflib.namespace import RDF, RDFS, OWL, DCTERMS, DCAT, FOAF
import os
import json
import re
import datetime

# Namespaces
bibo_ns = 'http://purl.org/ontology/bibo/'
datacite_ns = 'http://purl.org/spar/datacite/'
pav_ns = 'http://purl.org/pav/'
adms_ns = 'http://www.w3.org/ns/adms#'
our_ns = 'http://ns.inria.fr/kg/works/'

# classes
biboDocument = URIRef(bibo_ns + 'Document')
localRepository = URIRef(our_ns + 'RepositoryIdentifier')
localSource = URIRef(our_ns + 'Source')

# Properties
# pav:retrievedFrom
pavRetrievedFrom = URIRef(pav_ns + 'retrievedFrom')
pavImportedFrom = URIRef(pav_ns + 'importedFrom')
pavLastRefreshedOn = URIRef(pav_ns + 'lastRefreshedOn')
# adms:identifier
admsIdentifier = URIRef(adms_ns + 'identifier')

# sources url
paper_with_code_url = 'http://paperwithcode.com/'

def sanitize_uri(s):
    return re.search(r"^((([^:/?#\s]+):)(\/\/([^/?#\s]*))?([^?#\s=]*)(\?([^#\s]*))?(#(\w*))?)", s).group(1)

def sanitize(s):
    return re.sub(r"\\[ux][0-9A-Fa-f]+", '', s)

def create_uri(s):
    return URIRef(sanitize_uri(s))

# Create a graph
g = Graph()

# Uses the HAL api to download data about authors, structures and papers
def process_hal():
    page_size = 100
    page = 0
    format = 'json'
    author_api_endpoint = "http://api.archives-ouvertes.fr/ref/author/?wt=json"

# Parse the Paper with code json files and creates the corresponding data containing information on the papers and the code
def process_paper_with_code():
    # Load the json files
    paper_and_code_file = open("data/PaperWithCode/links-between-papers-and-code.json", 'r')
    paper_and_code_result = json.load(paper_and_code_file)

    paper_with_code = create_uri(paper_with_code_url)
    num_papers = len(paper_and_code_result)

    for paper in paper_and_code_result:
        # Add the paper to the graph
        paper_uri = create_uri(sanitize_uri(paper['paper_url']))
        if paper_uri == None or paper_uri == '':
            continue
        paper_title_string = ""
        if paper['paper_title'] != None:
            paper_title_string = sanitize(paper['paper_title'])
        paper_label = Literal(paper_title_string)
        paper_pdf_string = paper['paper_url_pdf']
        paper_arxiv_string = paper['paper_arxiv_id']
        g.add((paper_uri, RDF.type, biboDocument))
        g.add((paper_uri, pavRetrievedFrom, paper_with_code))
        g.add((paper_uri, DCTERMS.title, paper_label))
        if paper_pdf_string != None:
            g.add((paper_uri, DCAT.downloadURL, Literal(paper_pdf_string)))
        if paper_arxiv_string != None:
            g.add((paper_uri, admsIdentifier, create_uri('https://arxiv.org/abs/' + paper_arxiv_string)))
        
        # Add the code to the graph
        paper_repo = create_uri(paper['repo_url'])
        g.add((paper_repo, RDF.type, localRepository))
        g.add((paper_repo, pavRetrievedFrom, paper_with_code))
        g.add((paper_repo, admsIdentifier , paper_repo))

        # Add the relationship between the paper and the code
        g.add((paper_uri, DCTERMS.relation, paper_repo))
        print(f'Added paper {paper_label} and code {paper_repo} ({num_papers} remaining)')
        num_papers -= 1

    g.add((paper_with_code, RDF.type, localSource))
    g.add((paper_with_code, pavImportedFrom, Literal(paper_with_code_url + 'about')))
    g.add((paper_with_code, pavLastRefreshedOn, Literal(datetime.datetime.now().isoformat())))






#######################################################
# Load all RDF files in data/rdf and display data

# Query the graph

# Query 1: Get all the classes in the graph
q1 = prepareQuery('''
    PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
    PREFIX owl: <http://www.w3.org/2002/07/owl#>
    SELECT DISTINCT ?class
    WHERE {
        { ?s a ?class }
        UNION { ?class a rdfs:Class }
        UNION { ?class a owl:Class }
        UNION { ?class rdfs:subClassOf ?superclass }
        UNION { ?subClass rdfs:subClassOf ?class }
    }
''')

# Query 2: Get all the properties in the graph

q2 = prepareQuery('''
    SELECT DISTINCT ?property
    WHERE {
        ?s ?property ?o
    }
''')

# Send the query to the graph
def query(q):
    return g.query(q)

# Get all the classes in the graph
def get_classes():
    return query(q1)

# Get all the properties in the graph
def get_properties():
    return query(q2)

# Get all the instances of a class
def get_instances(class_name):
    q3 = prepareQuery(f'''
        SELECT DISTINCT ?instance
        WHERE {{
            ?instance a <{class_name}>
        }}
    ''')
    return query(q3)

# Load all RDF files in data/rdf
for file in os.listdir('data/rdf'):
    if file.endswith('.ttl'):
        g.parse(f'data/rdf/{file}', format='turtle')
    elif file.endswith('.rdf'):
        g.parse(f'data/rdf/{file}', format='xml')
        # classes = get_classes()
        # for r in classes:
        #     print(r)
        # properties = get_properties()
        # for r in properties:
        #     print(r)

print('Graph loaded')

process_paper_with_code()
print('Paper with code processed')
# process_hal()
# print('HAL processed')

# writing g to a file
print(f'Writing graph to file {len(g)} triples')
g.serialize(destination='data/graph.ttl', format='ntriples')
print('Graph written to file')

exit()