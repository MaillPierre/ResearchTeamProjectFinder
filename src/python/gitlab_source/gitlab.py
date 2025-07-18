from rdflib import URIRef, Graph, Literal
from rdflib.namespace import RDF, RDFS, DCTERMS
from util.utilities import create_uri
import gitlab
from gitlab.exceptions import GitlabGetError

import os
import json
import datetime
import hashlib
import logging

g_gl_Software = Graph()
g_gl_software_filename = 'data/rdf/software/gitlab_Software.ttl'
g_gl_Person = Graph()
g_gl_person_filename = 'data/rdf/person/gitlab_Person.ttl'

def process_gitlab(gitlab_instance_url = 'https://gitlab.inria.fr', gitlab_instance_token = os.getenv('gitlab_inria_token')):

    gitlab_forge_uri = create_uri(gitlab_instance_url)

    gitlab_projects_ns = f"{gitlab_instance_url}/api/v4/projects/"
    # Connect to the Gitlab API
    gl = gitlab.Gitlab(gitlab_instance_url, private_token=gitlab_instance_token)
    # enable_console_debug_logging() # Enable debug logging
    logging.info(f'Connected to Gitlab as {gl.http_username}')

    # Get all projects
    projects_list = gl.projects.list(get_all=True, iterator=True)
    logging.info(f'Found {len(projects_list)} projects')
    # Iterate over the projects
    for project in projects_list:
        if(project.visibility != 'public'):
            logging.info(f'Skipping project {project.name} ({project.id})')
            continue
        # Get the project details
        project_id = project.id
        project_name = project.name
        project_name_literal = Literal(project_name)
        project_description = project.description
        project_description_literal = Literal(project_description)
        project_url = project.web_url
        project_uri = create_uri(project_url)

        project_query_string = f'{gitlab_projects_ns}{project_id}'
        project_query_literal = Literal(project_query_string)
        logging.info(f'Querying project {project_query_string}')
        project_query_filename = hashlib.md5(project_query_string.encode()).hexdigest()
        project_query_filepath = f'data/gitlab/{project_query_filename}.json'

        # Cache handling
        if not os.path.exists(project_query_filepath):
            try:
                full_project = gl.projects.get(project_id, visibility='public', license=True, star_count=True, forks_count=True, topics=True, last_activity_at=True)
            except GitlabGetError as e:
                logging.warning(f'Error querying project {project_query_string}: {e}')
                continue
            # Save the project details to a file
            full_project_json_file_string = full_project.to_json()
            full_project_json_file = open(project_query_filepath, 'w')
            full_project_json_file.write(full_project_json_file_string)
            full_project_json_file.close()
        else:
            full_project_json_file = open(project_query_filepath, 'r')
            full_project_json_file_string = full_project_json_file.read()
            full_project_json_file.close()
        full_project_json = json.JSONDecoder().decode(full_project_json_file_string)


        project_license_obj = full_project_json['license']
        if(project_license_obj != None and project_license_obj['html_url'] != None):
            # Add the project to the graph
            g_gl_Software.add((project_uri, RDF.type, local_GitlabRepo))
            g_gl_Software.add((project_uri, pav_importedFrom, project_query_literal))
            g_gl_Software.add((project_uri, pav_lastRefreshedOn, Literal(datetime.datetime.now().isoformat())))
            g_gl_Software.add((project_uri, pav_retrievedFrom, gitlab_forge_uri))
            g_gl_Software.add((project_uri, adms_identifier, project_uri))
            g_gl_Software.add((project_uri, RDFS.label, project_name_literal))
            g_gl_Software.add((project_uri, DCTERMS.abstract, project_description_literal))

            if('last_activity_at' in full_project_json and full_project_json['last_activity_at'] != None):
                project_last_activity_literal = Literal(full_project_json['last_activity_at'])
                g_gl_Software.add((project_uri, DCTERMS.modified, project_last_activity_literal))
            if('star_count' in full_project_json and full_project_json['star_count'] != None):
                project_star_count_literal = Literal(full_project_json['star_count'])
                g_gl_Software.add((project_uri, local_repository_stars, project_star_count_literal))
            if('forks_count' in full_project_json and full_project_json['forks_count'] != None):
                project_forks_count_literal = Literal(full_project_json['forks_count'])
                g_gl_Software.add((project_uri, local_repository_forks, project_forks_count_literal))
            if('topics' in full_project_json and full_project_json['topics'] != None):
                for topic in full_project_json['topics']:
                    topic_literal = Literal(topic)
                    g_gl_Software.add((project_uri, DCTERMS.subject, topic_literal))

            project_license_uri = create_uri(project_license_obj['html_url'])
            g_gl_Software.add((project_uri, DCTERMS.license, project_license_uri))
            g_gl_Software.add((project_license_uri, RDF.type, cc_License))
            g_gl_Software.add((project_license_uri, pav_importedFrom, project_query_literal))
            g_gl_Software.add((project_license_uri, pav_lastRefreshedOn, Literal(datetime.datetime.now().isoformat())))
            g_gl_Software.add((project_license_uri, pav_retrievedFrom, gitlab_forge_uri))
            if(project_license_obj['name'] != None):
                project_license_name_literal = Literal(project_license_obj['name'])
                g_gl_Software.add((project_license_uri, RDFS.label, project_license_name_literal))
            if(project_license_obj['nickname'] != None):
                project_license_alt_name = Literal(project_license_obj['nickname'])
                g_gl_Software.add((project_license_uri, DCTERMS.alternative, project_license_alt_name))

    write_gitlab_graph()

def write_gitlab_graph():
    # Writing the graph to a file
    if len(g_gl_Software) > 0:
        logging.info(f'Writing software graph to file {len(g_gl_Software)} triples')
        g_gl_Software.serialize(destination=g_gl_software_filename, format='turtle')
    g_gl_Software.close()
    if len(g_gl_Person) > 0:
        logging.info(f'Writing person graph to file {len(g_gl_Person)} triples')
        g_gl_Person.serialize(destination=g_gl_person_filename, format='turtle')
    g_gl_Person.close()
    if (len(g_gl_Software) > 0) or (len(g_gl_Person) > 0):
        logging.info('Gitlab graph written to file')

