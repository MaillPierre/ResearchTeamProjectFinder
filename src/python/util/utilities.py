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

import requests


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
    query_result_filename = f"data/sparql_cache/{sparql_query_hash}.json"

    if(os.path.exists(query_result_filename)):
        result_parser = JSONResultParser()
        query_result_page = open(query_result_filename, 'r')
        query_result = result_parser.parse(source=query_result_page)
        query_result_page.close()
        return query_result
    else:
        sparql_query = prepareQuery(query)
        logging.info(f"Sending query to DBLP SPARQL endpoint: {query}")
        query_result = Graph().query(sparql_query)
        if len(query_result) > 0:
            result_serializer = JSONResultSerializer(query_result)
            query_result_file = open(query_result_filename, "x", encoding="utf-8")
            result_serializer.serialize(query_result_file, encoding="utf-8")
        return query_result
    
def api_cached_query(api_url: str, api_query_file_prefix: str ):
    api_result = None

    api_query_file = f"{api_query_file_prefix}{hashlib.md5((api_url.encode())).hexdigest()}.json"
    if(os.path.exists(api_query_file)):
        api_page = open(api_query_file, 'r')
        api_result = json.load(api_page)
        api_page.close()
    else:
        api_response = requests.get(api_url)
        api_result = api_response.json()
        api_page = open(api_query_file, 'w')
        json.dump(api_result, api_page)
        api_page.close()
    return api_result