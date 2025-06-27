from rdflib import Graph, Literal, BNode
from rdflib.plugins.sparql import prepareQuery
from rdflib.namespace import RDF, RDFS, DCTERMS, FOAF
from github import Github
from util.utilities import create_uri, json_encode_paginated_list, adms_identifier, pav_importedFrom, pav_lastRefreshedOn, local_GithubUser
import os
import json
import datetime
import hashlib
import logging

# Limits
# # Limit the number of results from github when looking for the ids of one person. Above this limit, the results are not added to the graph
github_user_results_limit = int(os.getenv('github_user_results_limit'))

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

        def search_for_person(current_person_uri, person_names):
            # Search for the person in Github
            person_query_string_list = list(map(lambda x: f'{x}', person_names))
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
            for user in user_results:
                user_github_id_uri = create_uri(user['url'])
                user_github_id_url = Literal(user['url'])
                logging.info(f'Adding user {user["login"]} to the graph')
                g_gh_Person.add((current_person_uri, adms_identifier, user_github_id_uri))
                g_gh_Person.add((user_github_id_uri, RDF.type, local_GithubUser))
                g_gh_Person.add((user_github_id_uri, pav_importedFrom, user_github_id_url))
                g_gh_Person.add((user_github_id_uri, pav_lastRefreshedOn, Literal(datetime.datetime.now().isoformat())))
                g_gh_Person.add((user_github_id_uri, RDFS.label, Literal(user['login'])))
                if(user['name'] != None):
                    g_gh_Person.add((user_github_id_uri, FOAF.name, Literal(user['name'])))
                if(user['blog'] != None):
                    g_gh_Person.add((user_github_id_uri, FOAF.homepage, Literal(user['blog'])))
                if(user['email'] != None):
                    g_gh_Person.add((user_github_id_uri, FOAF.mbox_sha1sum, Literal(user['email'])))
                if(user['bio'] != None):
                    g_gh_Person.add((user_github_id_uri, RDFS.comment, Literal(user['bio'])))
                if(user['company'] != None):
                    user_company_node = BNode()
                    g_gh_Person.add((user_company_node, RDF.type, FOAF.Organization))
                    g_gh_Person.add((user_company_node, RDFS.label, Literal(user['company'])))
                    g_gh_Person.add((user_company_node, pav_importedFrom, user_github_id_url))
                    g_gh_Person.add((user_company_node, pav_lastRefreshedOn, Literal(datetime.datetime.now().isoformat())))
                    g_gh_Person.add((user_github_id_uri, FOAF.member, user_company_node))
                if(user['location'] != None):
                    g_gh_Person.add((user_github_id_uri, DCTERMS.coverage, Literal(user['location'])))

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
    # TODO: Process github organizations and open-source repositories front pages
    write_github_graph()


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