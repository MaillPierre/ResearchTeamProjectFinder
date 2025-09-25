from datetime import datetime
import logging
from rdflib import  URIRef, Variable
from rdflib.plugins.sparql import prepareQuery
from rdflib.plugins.sparql.results.jsonresults import JSONResultParser, JSONResultSerializer
from rdflib.query import Result, ResultRow

from kg.knowledge import CitationCount, UniqueIdentifier, Source, Paper
from util.utilities import sparql_cached

logging.basicConfig(filename='app.log', level=logging.DEBUG)

dblp_source_obj = Source.Builder(URIRef("https://sparql.dblp.org/sparql")).build()

def get_article_per_year_sparql_result(publication_year: int, limit: int = 10, oldest_citation_year: int = datetime.now().year-1, offset: int = 0) -> Result:
    dblp_article_per_year_query = f"""
    ## Most cited publications with title keyword "database"
    PREFIX dblp: <https://dblp.org/rdf/schema#>
    PREFIX cito: <http://purl.org/spar/cito/>
    PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
    PREFIX rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#>
    PREFIX owl: <http://www.w3.org/2002/07/owl#>
    SELECT ?publ ?title ?doi ?cites {{
        SERVICE <https://sparql.dblp.org/sparql> {{
            {{
                SELECT ?publ ?title (COUNT(?citation) as ?cites) ?doi ?sameAs WHERE {{
                    ?publ rdf:type dblp:Publication .
                    ?publ dblp:title ?title .
                    ?publ dblp:yearOfPublication "{publication_year}"^^<http://www.w3.org/2001/XMLSchema#gYear> .
                    ?publ dblp:omid ?omid .
                    ?publ owl:sameAs ?sameAs .
                    ?citation rdf:type cito:Citation .
                    ?citation cito:hasCitedEntity ?omid .
					?citation cito:hasCitationCreationDate ?citationDate .
                    OPTIONAL {{
                        ?publ dblp:doi ?doi .
                    }}
					FILTER(?citationDate >= "{oldest_citation_year}"^^xsd:gYear)
                }}
                GROUP BY ?publ ?title ?doi
                ORDER BY DESC(?cites)
                LIMIT {limit}
                OFFSET {offset}
            }}
        }}
    }}
    """

    return sparql_cached(dblp_article_per_year_query)

def get_article_per_year(year: int, limit: int, offset=0)-> set[Paper]:
    result_dict: dict[URIRef, Paper] = {}
    sparql_results: Result = get_article_per_year_sparql_result(year, limit, offset)
    publ_variable = Variable("publ")
    title_variable = Variable("title")
    cites_variable = Variable("cites")
    doi_variable = Variable("doi")

    logging.debug(f"{len(sparql_results.bindings)} articles found.")

    for binding in sparql_results.bindings:
        if sparql_results.vars is None:
            logging.info("No results found")
            continue
        paper_uri = None
        paper_title = None
        paper_cites = None
        paper_doi = None
        for variable in sparql_results.vars:
            if variable == publ_variable:
                paper_uri = URIRef(binding[variable])
            elif variable == title_variable:
                paper_title = binding[variable]
            elif variable == cites_variable:
                paper_cites = int(binding[variable])
            elif variable == doi_variable and doi_variable in binding:
                paper_doi = binding[variable]
        if paper_uri is None or paper_title is None or paper_cites is None:
            pass
        else:
            article_citation_count_builder = CitationCount.Builder(source=dblp_source_obj,count=paper_cites)
            article_citation_count = article_citation_count_builder.build()
            if paper_uri not in result_dict:
                article_obj_builder = Paper.Builder(dblp_source_obj, URIRef(paper_uri))
                article_obj_builder.set_title(paper_title)
                article_citation_count_builder = CitationCount.Builder(source=dblp_source_obj,count=paper_cites)
                article_citation_count = article_citation_count_builder.build()
                article_obj_builder.add_citation_count(article_citation_count)
                if paper_doi != None:
                    article_obj_builder.set_doi(URIRef(paper_doi))
                result_dict[paper_uri] = article_obj_builder.build()
            else:
                result_dict[paper_uri].add_citation_count(article_citation_count)
    result = set(result_dict.values())
    return result

def dblp_most_cited_articles(start_year:int, sparql_limit = 1000) -> set[Paper]:
    current_year = datetime.now().year
    dblp_results: set[Paper] = get_article_per_year(year=start_year, limit=sparql_limit)
    for year in range(start_year+1, current_year+1):
        dblp_results = dblp_results.union(get_article_per_year(year=year, limit=sparql_limit))

    return dblp_results
