from datetime import datetime
import logging
from rdflib import  URIRef, Variable
from rdflib.plugins.sparql import prepareQuery
from rdflib.plugins.sparql.results.jsonresults import JSONResultParser, JSONResultSerializer
from rdflib.query import Result, ResultRow

from kg.knowledge import CitationCount, UniqueIdentifier, Source, Paper
from util.utilities import sparql_cached

logging.basicConfig(filename='app.log', level=logging.DEBUG)

dblp_source_obj = Source(URIRef("https://sparql.dblp.org/sparql"))

def get_article_per_year_sparql_result(publication_year: int, limit: int = 1000, offset: int = 0) -> Result:
    dblp_article_per_year_query = f"""
    ## Most cited publications
    PREFIX dblp: <https://dblp.org/rdf/schema#>
    PREFIX cito: <http://purl.org/spar/cito/>
    PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
    PREFIX rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#>
    PREFIX owl: <http://www.w3.org/2002/07/owl#>
    SELECT ?publ ?title ?doi ?cites {{
        SERVICE <https://sparql.dblp.org/sparql> {{
            {{
                SELECT ?publ ?title (COUNT(?citation) as ?cites) ?doi WHERE {{
                    ?publ rdf:type dblp:Publication .
                    ?publ dblp:title ?title .
                    ?publ dblp:yearOfPublication "{str(publication_year)}"^^<http://www.w3.org/2001/XMLSchema#gYear> .
                    ?publ dblp:omid ?omid .
                    ?citation rdf:type cito:Citation .
                    ?citation cito:hasCitedEntity ?omid .
                    OPTIONAL {{
                        ?publ dblp:doi ?doi .
                    }}
                }}
                GROUP BY ?publ ?title ?doi 
                ORDER BY DESC(?cites)
                LIMIT {limit}
                OFFSET {offset}
            }}
        }}
    }}
    """
    logging.debug(dblp_article_per_year_query)
    return sparql_cached(dblp_article_per_year_query)

def get_article_same_as_sparql_result(article_list: list[Paper]) -> Result:
    value_list = ""
    for articl_obj in article_list:
        value_list += '<' + articl_obj.uri + '> '
    dblp_article_sameAs_query = f"""
    PREFIX owl: <http://www.w3.org/2002/07/owl#>
    SELECT ?paper ?sameAs {{
        SERVICE <https://sparql.dblp.org/sparql> {{
            {{
                SELECT DISTINCT ?paper ?sameAs WHERE {{
                    ?paper owl:sameAs ?sameAs .
                    VALUES ?paper {{ { value_list }}}
                }}
                LIMIT 1000
            }}
        }}
    }}
    """
    logging.debug(dblp_article_sameAs_query)
    return sparql_cached(dblp_article_sameAs_query)

def get_article_same_as(papers: dict[URIRef, Paper]) -> set[Paper]:
    sameas_variable = Variable("sameAs")
    paper_variable = Variable("paper")
    paper_list = list(set(papers.values()))
    split_papers = [paper_list[i:i + 5] for i in range(0, len(paper_list), 5)] # split paper set into chunks of 5
    for paper_chunk in split_papers:
        paper_sameas_result = get_article_same_as_sparql_result(paper_chunk)
        for binding in paper_sameas_result.bindings:
            if paper_sameas_result.vars is None:
                logging.info("No results found")
                continue
            paper_uri = None
            paper_identifier = None
            for variable in paper_sameas_result.vars:
                if variable == paper_variable:
                    paper_uri = binding[paper_variable]
                if variable == sameas_variable:
                    paper_identifier = UniqueIdentifier(dblp_source_obj, URIRef(binding[sameas_variable]))
            if paper_uri != None and paper_identifier != None:
                papers[paper_uri].add_identifier(paper_identifier) # type: ignore
    return set(papers.values())



def get_article_per_year(year: int, limit: int, offset=0)-> set[Paper]:
    result_dict: dict[URIRef, Paper] = {}
    sparql_results: Result = get_article_per_year_sparql_result(publication_year=year, limit=limit, offset=offset)
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
            article_citation_count = CitationCount(source=dblp_source_obj,count=paper_cites)
            if paper_uri not in result_dict:
                article_obj = Paper(dblp_source_obj, URIRef(paper_uri))
                article_obj.set_title(paper_title)
                article_citation_count = CitationCount(source=dblp_source_obj,count=paper_cites)
                article_citation_count = article_citation_count
                article_obj.add_citation_count(article_citation_count)
                if paper_doi != None:
                    article_obj.set_doi(URIRef(paper_doi))
                result_dict[paper_uri] = article_obj
            else:
                result_dict[paper_uri].add_citation_count(article_citation_count)

    result = get_article_same_as(result_dict)
    return result

def dblp_most_cited_articles(start_year:int, sparql_limit = 1000) -> set[Paper]:
    current_year = datetime.now().year
    dblp_results: set[Paper] = get_article_per_year(year=start_year, limit=sparql_limit)
    for inter_year in range(start_year+1, current_year+1):
        dblp_results = dblp_results.union(get_article_per_year(year=inter_year, limit=sparql_limit))
    return dblp_results
