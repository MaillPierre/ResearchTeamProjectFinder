import logging
from rdflib import Graph, URIRef, Variable
from rdflib.plugins.sparql import prepareQuery
from rdflib.query import Result, ResultRow

from kg.knowledge import Source, Paper

logging.basicConfig(filename='app.log', level=logging.DEBUG)

g_h_article = Graph()
g_h_article_filename = 'data/rdf/article/dblp_Article.ttl'

dblp_source_obj = Source.Builder(URIRef("https://sparql.dblp.org/sparql")).build()

def get_article_per_year_sparql_result(year: int, limit: int = 10, offset: int = 0) -> Result:
    dblp_article_per_year_query = f"""
    ## Most cited publications with title keyword "database"
    PREFIX dblp: <https://dblp.org/rdf/schema#>
    PREFIX cito: <http://purl.org/spar/cito/>
    PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
    PREFIX rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#>
    SELECT ?publ ?title ?cites {{
        SERVICE <https://sparql.dblp.org/sparql> {{
            {{
                SELECT ?publ ?label (COUNT(?citation) as ?cites) WHERE {{
                    ?publ rdf:type dblp:Publication .
                    ?publ dblp:title ?title .
                    ?publ dblp:yearOfPublication "{year}"^^<http://www.w3.org/2001/XMLSchema#gYear> .
                    ?publ dblp:omid ?omid .
                    ?publ rdfs:label ?label .
                    ?citation rdf:type cito:Citation .
                    ?citation cito:hasCitedEntity ?omid .
                }}
                GROUP BY ?publ ?label
                ORDER BY DESC(?cites)
                LIMIT {limit}
                OFFSET {offset}
            }}
        }}
    }}
    """


    # Send GET request to the HAL API
    dblp_sparql_query = prepareQuery(dblp_article_per_year_query)
    logging.info(f"Sending query to HAL SPARQL endpoint: {dblp_article_per_year_query}")
    return g_h_article.query(dblp_sparql_query)

def get_article_per_year(year: int, limit: int, offset=0)-> set[Paper]:
    sparql_results: Result = get_article_per_year_sparql_result(year, limit, offset)
    publ_variable = Variable("publ")
    title_variable = Variable("title")
    cites_variable = Variable("cites")
    result: set[Paper] = set()

    for binding in sparql_results.bindings:
        if sparql_results.vars is None:
            logging.info("No results found")
            continue
        paper_uri = None
        paper_title = None
        paper_cites = None
        for variable in sparql_results.vars:
            if variable == publ_variable:
                paper_uri = binding[variable]
            elif variable == title_variable:
                paper_title = binding[variable]
            elif variable == cites_variable:
                paper_cites = int(binding[variable])
        if paper_uri is None or paper_title is None or paper_cites is None:
            pass
        else:
            article_obj_builder = Paper.Builder(dblp_source_obj, URIRef(paper_uri))
            article_obj_builder.set_title(paper_title)
            article_obj_builder.set_citation_count(paper_cites)
            result.add(article_obj_builder.build())
    return result
    
def dblp_test():
    dblp_results: set[Paper] = get_article_per_year(2020, 1000)
    for paper in dblp_results:
        logging.info(paper)
