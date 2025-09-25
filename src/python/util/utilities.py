import hashlib
import os
import uuid
from rdflib import Graph, URIRef, BNode, Namespace
from rdflib.plugins.sparql import prepareQuery
from rdflib.plugins.sparql.results.jsonresults import JSONResultParser, JSONResultSerializer
from rdflib.query import Result, ResultRow
import re
from github import PaginatedList
import json
import logging


# Helper functions

def sanitize_uri(s):
    malformed_uri_repeating_domains = r"(https?://[\w./]+)(https?://[\w./]+)"
    standard_uri_regex = r"(^(([^:/?#\s]+):)(\/\/([^/?#\s]*))?([^?#\s=]*)(\?([^#\s]*))?(#(\w*))?)"

    # Remove malformed uri
    s = re.sub(malformed_uri_repeating_domains, r"\2", s)

    match_standard_uri = re.search(standard_uri_regex, s)
    if match_standard_uri == None:
        return None
    return match_standard_uri.group(1)

def sanitize(s):
    return re.sub(r"\\[ux][0-9A-Fa-f]+", '', s)

def create_uri(s):
    healthy_uri = sanitize_uri(s)
    if healthy_uri == None:
        return create_bnode()
    return URIRef(healthy_uri)

def create_bnode(prefix= ""):
    return BNode(prefix + str(uuid.uuid4()))

def json_encode_paginated_list(paginated_list: PaginatedList.PaginatedList):
    json_list = []
    try:
        for item in paginated_list:
            json_list.append(item.raw_data)
    except Exception as e:
        logging.error(f"Error: {e}")

    return json.JSONEncoder().encode(json_list)

def sparql_cached(query: str) -> Result:
    sparql_query_hash = hashlib.md5(query.encode()).hexdigest()
    dblp_article_query_result_filename = f"data/sparql_cache/{sparql_query_hash}.json"

    if(os.path.exists(dblp_article_query_result_filename)):
        result_parser = JSONResultParser()
        dblp_article_query_result_page = open(dblp_article_query_result_filename, 'r')
        dblp_article_query_result = result_parser.parse(source=dblp_article_query_result_page)
        dblp_article_query_result_page.close()
        return dblp_article_query_result
    else:
        # Send GET request to the DBLP API
        dblp_sparql_query = prepareQuery(query)
        logging.info(f"Sending query to DBLP SPARQL endpoint: {query}")
        dblp_article_query_result = Graph().query(dblp_sparql_query)
        result_serializer = JSONResultSerializer(dblp_article_query_result)
        dblp_article_query_result_file = open(dblp_article_query_result_filename, "x", encoding="utf-8")
        result_serializer.serialize(dblp_article_query_result_file, encoding="utf-8")
        return dblp_article_query_result