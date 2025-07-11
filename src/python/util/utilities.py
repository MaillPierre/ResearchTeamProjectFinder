import uuid
from rdflib import URIRef, BNode, Namespace
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