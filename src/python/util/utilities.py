from rdflib import URIRef, BNode
import re
from github import PaginatedList
import json
import logging

# Namespaces
bibo_ns = 'http://purl.org/ontology/bibo/'
dcmitype_ns = "http://purl.org/dc/dcmitype/"
datacite_ns = 'http://purl.org/spar/datacite/'
pav_ns = 'http://purl.org/pav/'
adms_ns = 'http://www.w3.org/ns/adms#'
roh_ns = 'http://w3id.org/roh#'
our_ns = 'http://ns.inria.fr/kg/works/'
orcid_ns = "https://orcid.org/"
hal_ns = "https://hal.science/"
hal_author_ns = "https://shs.hal.science/search/index/q/*/authIdHal_s/"
arxiv_ns = "https://arxiv.org/abs/"
idref_ns = "https://www.idref.fr/"
ror_ns = "https://ror.org/"
gscholar_ns = "https://scholar.google.com/citations?user="
cc_ns = "http://creativecommons.org/ns#"

# classes
bibo_Document = URIRef(bibo_ns + 'Document')
dcmitype_Software = URIRef(dcmitype_ns + 'Software')
datacite_OrganizationIdentifier = URIRef(datacite_ns + 'OrganizationIdentifier')
cc_License = URIRef(cc_ns + 'License')
local_RepositoryId = URIRef(our_ns + 'RepositoryIdentifier')
local_Source = URIRef(our_ns + 'Source')
local_Orcid = URIRef(our_ns + 'ORCID')
local_ArXiv = URIRef(our_ns + 'Arxiv')
local_GScholar = URIRef(our_ns + 'GoogleScholar')
local_IdRef = URIRef(our_ns + 'IdRef')
local_IdHal = URIRef(our_ns + 'IdHal')
local_HalOrganization = URIRef(our_ns + 'HalOrganization')
local_GithubUser = URIRef(our_ns + 'GitHubUser')
local_GithubRepo = URIRef(our_ns + 'GitHubRepository')
local_GitlabUser = URIRef(our_ns + 'GitLabUser')
local_GitlabRepo = URIRef(our_ns + 'GitLabRepository')
local_repository_stars = URIRef(our_ns + 'repositoryStars')
local_repository_forks = URIRef(our_ns + 'repositoryForks')

# Properties
# pav:retrievedFrom
pav_retrievedFrom = URIRef(pav_ns + 'retrievedFrom')
pav_importedFrom = URIRef(pav_ns + 'importedFrom')
pav_lastRefreshedOn = URIRef(pav_ns + 'lastRefreshedOn')
roh_platform = URIRef(roh_ns + 'platform')
# adms:identifier
adms_identifier = URIRef(adms_ns + 'identifier')


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
        return BNode()
    return URIRef(sanitize_uri(s))

def json_encode_paginated_list(paginated_list: PaginatedList):
    json_list = []
    try:
        for item in paginated_list:
            json_list.append(item.raw_data)
    except Exception as e:
        logging.error(f"Error: {e}")

    return json.JSONEncoder().encode(json_list)