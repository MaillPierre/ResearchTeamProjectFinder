from datetime import datetime
import logging
import os
from rdflib import Graph, Literal, Namespace, URIRef
from rdflib.namespace import RDF, RDFS, FOAF, XSD, OWL, DCAT, DCTERMS
from util.utilities import create_uri, create_bnode, pav_importedFrom, pav_lastRefreshedOn, pav_retrievedFrom, pav_authoredOn, local_Source, hal_author_ns, local_HalOrganization, local_IdHal, adms_identifier, local_GScholar, local_Orcid, local_IdRef, hal_ns, orcid_ns, dcmitype_Software, datacite_OrganizationIdentifier, local_RepositoryId, roh_platform, bibo_Document
import json
import hashlib

from habanero import Crossref
cr = Crossref(mailto="pierre.maillot@inria.fr", timeout=10000)


data_path="data/crossref/"

g_c_papers = Graph()
g_c_papers_filename = 'data/rdf/paper/crossref_Papers.ttl'

# List of topics of interests
topics = [ "Data science", "Machine learning", "Artificial intelligence", "Deep learning", "Natural language processing", "Knowledge Graph", "Knowledge Graph Embedding", "Graph embedding", "Knowledge Graph Completion", "Knowledge Graph Construction" , "Data wrangling", "Explicability"]

logging.basicConfig(filename='app.log', level=logging.INFO)


def store_crossref_answer(crossref_answer: dict, query: str, start_date: str, end_date: str, limit: int, order="desc"):
    crossref_query_id=query + start_date + end_date + str(limit) + order
    crossref_data_filepath=f'{data_path}{hashlib.md5(crossref_query_id.encode()).hexdigest()}.json'
    crossref_query_file = open(crossref_data_filepath, 'w')
    json.dump(crossref_answer, crossref_query_file)
    crossref_query_file.close()

def retrieve_crossref_answer(query: str, start_date: str, end_date: str, limit: int, order="desc"):
    crossref_query_id=query + start_date + end_date + str(limit) + order
    crossref_data_filepath=f'{data_path}{hashlib.md5(crossref_query_id.encode()).hexdigest()}.json'
    if os.path.exists(crossref_data_filepath):
        crossref_query_file = open(crossref_data_filepath, 'r')
        crossref_answer = json.load(crossref_query_file)
        crossref_query_file.close()
        return crossref_answer
    else:
        return dict()

def check_crossref_answer_exists(query: str, start_date: str, end_date: str, limit: int, order="desc"):
    logging.info(f"Checking if Crossref answer exists for query: {query}, start_date: {start_date}, end_date: {end_date}, limit: {limit}, order: {order}")
    crossref_query_id=query + start_date + end_date + str(limit) + order
    crossref_data_filepath=f'{data_path}{hashlib.md5(crossref_query_id.encode()).hexdigest()}.json'
    return os.path.exists(crossref_data_filepath)

def retrieve_articles_from_crossref(query: str, start_date: str, end_date: str, limit: int, order="desc") -> dict:
    logging.info(f"Retrieving articles from Crossref with query: {query}, start_date: {start_date}, end_date: {end_date}, limit: {limit}, order: {order}")
    if check_crossref_answer_exists(query, start_date, end_date, limit, order):
        crossref_answer = retrieve_crossref_answer(query, start_date, end_date, limit, order)
    else:
        crossref_answer = cr.works(query=query,
                   filter={"from-pub-date": start_date, "until-pub-date": end_date},
                   sort="is-referenced-by-count",
                   limit=10,
                   order="desc")
        store_crossref_answer(crossref_answer=crossref_answer, query=query, start_date=start_date, end_date=end_date, limit=limit, order=order)
        
    
    # Ensure the result is a list of dictionaries
    return crossref_answer if isinstance(crossref_answer, dict) else crossref_answer.to_dict()

def process_top_articles_by_domains(domains, nb_years, limit):
    logging.info(f"Processing the top {limit} articles for domains: {domains} of the last {nb_years} years")
    for domain in domains:
        end_date = datetime.now()
        start_date = end_date.replace(year=end_date.year - nb_years)
        start_date_str = start_date.strftime("%Y-%m-%d")
        end_date_str = end_date.strftime("%Y-%m-%d")
        top_domain_articles = retrieve_articles_from_crossref(domain, start_date_str, end_date_str, limit)

        logging.info(f'Processing {len(top_domain_articles)} articles for domain {domain}')

        # Process article to RDF
        for article in top_domain_articles["message"]["items"]:
            process_article_to_rdf(article)

def process_article_to_rdf(article):
    if "DOI" in article:
        doi_string = article["DOI"]
        article_uri = create_uri("http://doi.org/" + doi_string)
        g_c_papers.add((article_uri, RDF.type, bibo_Document))
        g_c_papers.add((article_uri, pav_lastRefreshedOn, Literal(datetime.now())))
        g_c_papers.add((article_uri, pav_retrievedFrom, URIRef(create_uri(cr.base_url))))
        titles = article["title"]
        for title in titles:
            title_str = title
            g_c_papers.add((article_uri, DCTERMS.title, Literal(title_str)))
        citation_count = article["is-referenced-by-count"]
        g_c_papers.add((article_uri, DCTERMS.bibliographicCitation, Literal(citation_count)))
        for author in article['author']:
            author_uri = create_bnode("author")
            if "ORCID" in author:
                orcid_str = author["ORCID"]
                author_uri = create_uri(orcid_str)
                g_c_papers.add((author_uri, adms_identifier, author_uri))
                g_c_papers.add((author_uri, RDF.type, local_Orcid))
            g_c_papers.add((article_uri, DCTERMS.creator, author_uri))
            g_c_papers.add((author_uri, RDF.type, FOAF.Person))
            if "given" in author:
                given_str = author["given"]
                g_c_papers.add((author_uri, FOAF.firstName, Literal(given_str)))
            if "family" in author:
                family_str = author["family"]
                g_c_papers.add((author_uri, FOAF.lastName, Literal(family_str)))
            if "given" in author and "family" in author:
                given_str = author["given"]
                family_str = author["family"]
                g_c_papers.add((author_uri, FOAF.name, Literal(given_str + " " + family_str)))
            if "affiliation" in author:
                for affiliation in author["affiliation"]:
                    affiliation_name_str = affiliation["name"]
        if "license" in article:
            licenses = article["license"]
            for license in licenses:
                if "URL" in license:
                    license_url = license["URL"]

        created_str = crossref_datepart_to_datetime(article["created"]["date-time"])
        g_c_papers.add((article_uri, pav_authoredOn, Literal(created_str, datatype=XSD.dateTime)))

        if "abstract" in article:
            abstract_str = article["abstract"]
            g_c_papers.add((article_uri, DCTERMS.abstract, Literal(abstract_str)))

        if "funder" in article:
            for funder in article["funder"]:
                if "DOI" in funder:
                    funder_doi = funder["DOI"]
                if "name" in funder:
                    funder_name = funder["name"]

        if "link" in article:
            for link in article["link"]:
                if "URL" in link:
                    link_url = link["URL"]
                if "content-type" in link:
                    link_content_type = link["content-type"]
                if "intended-application" in link:
                    intended_application = link["intended-application"]

        
        
    # authors_full_name = [f'{author["family"]}, {author["given"]}' for author in article['author']]

    logging.info(f"Processing article {doi_string} with title {titles} and citation count {citation_count}")


def crossref_datepart_to_datetime(datepart: list[int]):
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
    process_top_articles_by_domains(topics, limit=500, nb_years=5)
    write_crossref_graph()