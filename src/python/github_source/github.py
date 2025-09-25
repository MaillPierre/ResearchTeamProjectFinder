from rdflib import Graph, Literal, BNode, URIRef
from rdflib.plugins.sparql import prepareQuery
from rdflib.namespace import RDF, RDFS, DCTERMS, FOAF
from rdflib.query import Result, ResultRow
from github import Github
from kg.knowledge import UniqueIdentifier, Organization, Person, Source
from util.utilities import create_uri, json_encode_paginated_list
from kg.CONSTANTS import ADMS, PAV , LOCAL
import os
import json
import datetime
import hashlib
import logging

# Limits
# # Limit the number of results from github when looking for the ids of one person. Above this limit, the results are not added to the graph
if os.getenv('github_user_results_limit') is None:
    logging.error('No limit set for github results')
    github_user_results_limit = 100 
else:
    github_user_results_limit = int(os.getenv('github_user_results_limit')) # type: ignore

g_gh_Software = Graph()
g_gh_software_filename = 'data/rdf/software/github_Software.ttl'
g_gh_Person = Graph()
g_gh_person_filename = 'data/rdf/person/github_Person.ttl'
g_gh_Organization = Graph()
g_gh_organization_filename = 'data/rdf/organization/github_Organization.ttl'


def process_github():
    max_query_length = 256


    # Connect to the Github API
    github_token = os.getenv('github_token')
    g = Github(github_token)
    # enable_console_debug_logging() # Enable debug logging
    logging.info(f'Connected to Github as {g.get_user().login}')

    def process_github_person():
        # Search for specific users
        ## Load existing users from the graph in rdf/person
        logging.info("Loading existing users from the graph")
        g_known_person = Graph()
        for file in os.listdir('data/rdf/person/'):
            if file.endswith('.ttl'):
                g_known_person.parse('data/rdf/person/' + file, format='turtle')
        logging.info(f'Loaded {len(g_known_person)} triples about people from the graph')

        def search_for_person(current_person_uri, person_names: list[str]):
            # Search for the person in Github
            person_query_string_list = [ f'{x}' for x in person_names ]
            person_query_string_list = sorted(person_query_string_list, key=len, reverse=True)[:5]
            person_query = " OR ".join(person_query_string_list)
            if(len(person_query) > max_query_length):
                person_query = person_query[:max_query_length - 1]
            user_results_json_filename = 'data/github/' + hashlib.md5(person_query.encode()).hexdigest() + '.json'
            user_results = None
            if not os.path.exists(user_results_json_filename):
                user_results = g.search_users(person_query)
                user_results_json = ""
                logging.info(f'Found {user_results.totalCount} users for {person_query}')
                if(user_results.totalCount > github_user_results_limit):
                    user_results = []
                    user_results_json = json.JSONEncoder().encode(user_results)
                else:
                    user_results_json = json_encode_paginated_list(user_results)
                user_results_json_file = open(user_results_json_filename, 'w')
                user_results_json_file.write(user_results_json)
                user_results_json_file.close()
            else:
                user_results_json_file = open(user_results_json_filename, 'r')
                user_results_json = user_results_json_file.read()
                user_results_json_file.close()
            user_results = json.JSONDecoder().decode(user_results_json)

            gh_source_obj = Source.Builder(URIRef('https://github.com')).build()
            for user in user_results:
                user_github_id_uri = create_uri(user['url'])
                gh_person_obj_builder = Person.Builder(gh_source_obj, user_github_id_uri)
                gh_person_id = UniqueIdentifier.Builder(gh_source_obj, user_github_id_uri).build()
                logging.info(f'Adding user {user["login"]} to the graph')
                gh_person_obj_builder.add_identifier(gh_person_id)
                gh_person_obj_builder.add_alternative(user['login'])
                if(user['name'] != None):
                    gh_person_obj_builder.set_label(user['name'])
                if(user['blog'] != None):
                    gh_person_obj_builder.add_contact(Literal(user['blog']))
                if(user['email'] != None):
                    gh_person_obj_builder.add_contact(Literal(user['email']))
                if(user['bio'] != None):
                    gh_person_obj_builder.add_comment(user['bio'])
                if(user['company'] != None):
                    user_company_node = BNode()
                    user_org_obj_builder = Organization.Builder(gh_source_obj, user_company_node)
                    user_org_obj_builder.set_label(user['company'])
                    gh_person_obj_builder.add_affiliation(user_org_obj_builder.build())
                if(user['location'] != None):
                    gh_person_obj_builder.add_location(Literal(user['location']))
                gh_person_obj = gh_person_obj_builder.build()
                gh_person_obj.to_rdf(g_gh_Person)

        # Retrieve the list of users from the graph
        query = prepareQuery('''
            SELECT DISTINCT ?person ?name
            WHERE {
                ?person a foaf:Person .
                { ?person foaf:firstName ?first ;
                                foaf:lastName ?last .
                    BIND( CONCAT(CONCAT(?first, " "), ?last) AS ?name )
                }
            } ORDER BY DESC(?name)
        ''', initNs={'foaf': FOAF})
        current_person_uri = None
        current_person_names = []

        iterator = iter(g_known_person.query(query))
        # Iterate over the results
        while True:
            try:
                row = next(iterator)
                if isinstance(row, ResultRow):
                    if(current_person_uri == None):
                        current_person_uri = row.person
                        current_person_names.append(row.name)
                    if(current_person_uri != row.person or current_person_uri == None):
                        if(len(current_person_names) > 0):
                            # We have a person with at least some known names
                            # prepare the query to the Github API
                            search_for_person(current_person_uri, current_person_names)
                        current_person_uri = row.person
                        current_person_names = []
                        current_person_names.append(row.name)
                    else:
                        current_person_names.append(row.name)
            except StopIteration:
                if(len(current_person_names) > 0):
                    search_for_person(current_person_uri, current_person_names)
                break

    process_github_person()


def write_github_graph():
    if len(g_gh_Person) > 0:
        logging.info(f"Writing github person graph to file, {len(g_gh_Person)} triples")
        g_gh_Person.serialize(destination=g_gh_person_filename, format='turtle')
        logging.info("Github person graph written to file")
    g_gh_Person.close()
    if len(g_gh_Software) > 0:
        logging.info(f"Writing github software graph to file, {len(g_gh_Software)} triples")
        g_gh_Software.serialize(destination=g_gh_software_filename, format='turtle')
        logging.info("Github software graph written to file")
    g_gh_Software.close()
    if len(g_gh_Organization) > 0:
        logging.info(f"Writing github organization graph to file, {len(g_gh_Organization)} triples")
        g_gh_Organization.serialize(destination=g_gh_organization_filename, format='turtle')
        logging.info("Github organization graph written to file")
    g_gh_Organization.close()