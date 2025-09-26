from datetime import datetime
import logging
import os
from rdflib import Graph, Literal, Namespace, URIRef
from rdflib.namespace import RDF, RDFS, FOAF, XSD, OWL, DCAT, DCTERMS
from kg.knowledge import CitationCount, Organization, Paper, Person, Source, UniqueIdentifier
from util.utilities import create_uri, create_bnode
from kg.CONSTANTS import DOI
import json
import hashlib

from habanero import Crossref
cr = Crossref(mailto="pierre.maillot@inria.fr", timeout=10000)


data_path="data/crossref/"

g_c_papers = Graph()
g_c_papers_filename = 'data/rdf/paper/crossref_Papers.ttl'
uri_c_source: URIRef = URIRef(cr.base_url)
crossref_source_obj = Source(uri_c_source)

# List of topics of interests
topics = [ "Data science"]
# topics = [ "Data science", "Machine learning", "Artificial intelligence", "Deep learning", "Natural language processing", "Knowledge Graph", "Knowledge Graph Embedding", "Graph embedding", "Knowledge Graph Completion", "Knowledge Graph Construction" , "Data wrangling", "Explicability"]

logging.basicConfig(filename='app.log', level=logging.INFO)

def create_crossref_query_id(ids: list[str] | None = None, query: str | None = None, start_date: str | None = None, end_date: str | None = None, sort : str | None = None , limit: int | None = None, order : str | None = None) -> str:
    crossref_query_id = ""
    if ids != None:
        crossref_query_id += str(ids)
    if query != None:
        crossref_query_id += query
    if start_date != None:
        crossref_query_id += start_date
    if end_date != None:
        crossref_query_id += end_date
    if sort != None:
        crossref_query_id += sort
    if limit != None:
        crossref_query_id += str(limit)
    if order != None:
        crossref_query_id += order
    return crossref_query_id


def store_crossref_answer(crossref_answer: dict, ids: list[str] | None = None, query: str | None = None, start_date: str | None = None, end_date: str | None = None, sort : str | None = None , limit: int | None = None, order : str | None = None):
    crossref_query_id=create_crossref_query_id(ids=ids, query=query, start_date=start_date, end_date=end_date, sort=sort, limit=limit, order=order)
    crossref_data_filepath=f'{data_path}{hashlib.md5(crossref_query_id.encode()).hexdigest()}.json'
    crossref_query_file = open(crossref_data_filepath, 'w')
    json.dump(crossref_answer, crossref_query_file)
    crossref_query_file.close()

def retrieve_crossref_answer(ids: list[str] | None = None, query: str | None = None, start_date: str | None = None, end_date: str | None = None, sort : str | None = None , limit: int | None = None, order : str | None = None):
    crossref_query_id=create_crossref_query_id(ids=ids, query=query, start_date=start_date, end_date=end_date, sort=sort, limit=limit, order=order)
    crossref_data_filepath=f'{data_path}{hashlib.md5(crossref_query_id.encode()).hexdigest()}.json'
    if os.path.exists(crossref_data_filepath):
        crossref_query_file = open(crossref_data_filepath, 'r')
        crossref_answer = json.load(crossref_query_file)
        crossref_query_file.close()
        return crossref_answer
    else:
        return {}

def check_crossref_answer_exists(ids: list[str] | None = None, query: str | None = None, start_date: str | None = None, end_date: str | None = None, sort : str | None = None , limit: int | None  = None, order : str | None = None):
    crossref_query_id = create_crossref_query_id(ids=ids, query=query, start_date=start_date, end_date=end_date, sort=sort, limit=limit, order=order)
    crossref_data_filepath=f'{data_path}{hashlib.md5(crossref_query_id.encode()).hexdigest()}.json'
    return os.path.exists(crossref_data_filepath)

def retrieve_articles_from_crossref(ids: list[str] | None = None, query: str | None = None, start_date: str | None = None, end_date: str | None = None, sort : str | None  = None, limit: int | None = None, order=None) -> dict:
    filter = {}
    if start_date != None:
        filter["from-pub-date"] = start_date
    if end_date != None:
        filter["until-pub-date"] = end_date
    if check_crossref_answer_exists(ids=ids, query=query, start_date=start_date, end_date=end_date, sort=sort, limit=limit, order=order):
        crossref_answer = retrieve_crossref_answer(query=query, start_date=start_date, end_date=end_date, limit=limit, order=order)
    else:
        crossref_answer = cr.works(
                   ids=ids,
                   query=query,
                   filter=filter,
                   sort=sort,
                   limit=limit,
                   order=order)
        store_crossref_answer(crossref_answer=crossref_answer, query=query, start_date=start_date, end_date=end_date, limit=limit, order=order)
        
    
    # Ensure the result is a list of dictionaries
    return crossref_answer

def process_top_articles_by_domains(domains, nb_years, limit):
    logging.info(f"Processing the top {limit} articles for domains: {domains} of the last {nb_years} years")
    for domain in domains:
        end_date = datetime.now()
        start_date = end_date.replace(year=end_date.year - nb_years)
        start_date_str = start_date.strftime("%Y-%m-%d")
        end_date_str = end_date.strftime("%Y-%m-%d")
        top_domain_articles = retrieve_articles_from_crossref(domain, start_date_str, end_date_str, limit, sort="is-referenced-by-count")

        logging.info(f'Processing {len(top_domain_articles)} articles for domain {domain}')

        # Process article to RDF
        for article in top_domain_articles["message"]["items"]:
            process_crossref_article_to_obj(article)

def expand_article_obj_from_crossref(article_obj : Paper) -> Paper:
    id_list = list(filter( lambda id_str: "doi.org" in id_str, [ str(uid.uri) for uid in article_obj.identifiers ]))
    logging.debug(f"Expanding for article with ids {id_list}")
    article_from_crossref = retrieve_articles_from_crossref(ids=id_list)
    for article_json_message in article_from_crossref:
        article_json = article_json_message["message"]
        article_obj.set_created(datetime.now().isoformat())
        titles = article_json["title"]
        for title in titles:
            title_str = title
            article_obj.set_title(title_str)
        
        citation_count = CitationCount(int(article_json["is-referenced-by-count"]), crossref_source_obj)
        article_obj.add_citation_count(citation_count)

        created_str = crossref_datepart_to_datetime(article_json["created"]["date-time"])
        if created_str is not None:
            article_obj.set_created(created_str.isoformat())

        if "abstract" in article_json:
            abstract_str = article_json["abstract"]
            article_obj.set_abstract(abstract_str)

        if "funder" in article_json:
            for funder in article_json["funder"]:
                if "name" in funder:
                    funder_name = funder["name"]
                    funder_obj = Organization(crossref_source_obj, funder_name)
                    if "DOI" in funder:
                        funder_doi = funder["DOI"]
                        if "http://" not in funder_doi:
                            funder_doi = DOI + funder_doi
                        funder_id = UniqueIdentifier(crossref_source_obj, URIRef(funder_doi))
                        funder_obj.add_identifier(funder_id)
                    article_obj.add_related(funder_obj)

        if "link" in article_json:
            for link in article_json["link"]:
                if "URL" in link:
                    link_url = link["URL"]
                if "content-type" in link:
                    link_content_type = link["content-type"]
                if "intended-application" in link:
                    intended_application = link["intended-application"]

        for author in article_json['author']:
            add_authors_to_article(author, article_obj)
    return article_obj

def process_crossref_article_to_obj(article) -> Paper | None:
    if "DOI" in article:
        doi_string = article["DOI"]
        article_uri = create_uri(DOI + doi_string)
        article_obj = Paper(crossref_source_obj, article_uri)
        article_obj.set_doi(doi_string)
        article_obj.set_created(datetime.now().isoformat())
        titles = article["title"]
        for title in titles:
            title_str = title
            article_obj.set_title(title_str)
        citation_count = CitationCount(int(article["is-referenced-by-count"]), crossref_source_obj)
        article_obj.add_citation_count(citation_count)

        created_str = crossref_datepart_to_datetime(article["created"]["date-time"])
        if created_str is not None:
            article_obj.set_created(created_str.isoformat())

        if "abstract" in article:
            abstract_str = article["abstract"]
            article_obj.set_abstract(abstract_str)

        if "funder" in article:
            for funder in article["funder"]:
                if "name" in funder:
                    funder_name = funder["name"]
                    funder_obj = Organization(crossref_source_obj, funder_name)
                    if "DOI" in funder:
                        funder_doi = funder["DOI"]
                        funder_id = UniqueIdentifier(crossref_source_obj, funder_doi)
                        funder_obj.add_identifier(funder_id)
                    article_obj.add_related(funder_obj)

        if "link" in article:
            for link in article["link"]:
                if "URL" in link:
                    link_url = link["URL"]
                if "content-type" in link:
                    link_content_type = link["content-type"]
                if "intended-application" in link:
                    intended_application = link["intended-application"]

        for author in article['author']:
            add_authors_to_article(author, article_obj)

        logging.info(f"Processing article {doi_string} with title {titles} and citation count {citation_count}")
        return article_obj


def add_authors_to_article(author, article_obj: Paper):
    author_uri = create_bnode("author")
    if "ORCID" in author:
        orcid_str = author["ORCID"]
        author_uri = create_uri(orcid_str)
    author_obj = Person(crossref_source_obj, author_uri)
    if "ORCID" in author:
        orcid_str = author["ORCID"]
        author_obj.set_orcid(orcid_str)
    if "given" in author:
        given_str = author["given"]
        author_obj.set_first_name(given_str)
    if "family" in author:
        family_str = author["family"]
        author_obj.set_last_name(family_str)
    if "given" in author and "family" in author:
        given_str = author["given"]
        family_str = author["family"]
        author_obj.set_label(given_str + " " + family_str)
    if "affiliation" in author:
        for affiliation in author["affiliation"]:
            affiliation_name_str = affiliation["name"]
            affiliation_obj = Organization(crossref_source_obj, affiliation_name_str)
            author_obj.add_affiliation(affiliation_obj)
    article_obj.add_author(author_obj)


def crossref_datepart_to_datetime(datepart: list[int]) -> datetime | None:
    if len(datepart) == 3:
        return datetime(datepart[0], datepart[1], datepart[2])
    if len(datepart) == 2:
        return datetime(datepart[0], datepart[1], 1)
    if len(datepart) == 1:
        return datetime(datepart[0], 1, 1)
    
def write_crossref_graph():
    if len(g_c_papers) > 0:
        logging.info(f"Writing {len(g_c_papers)} papers to {g_c_papers_filename}")
        g_c_papers.serialize(destination=g_c_papers_filename, format="turtle")

def process_crossref():
    logging.info("Processing Crossref")
    process_top_articles_by_domains(topics, limit=10, nb_years=5)
    write_crossref_graph()