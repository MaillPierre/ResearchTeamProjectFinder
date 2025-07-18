from kg.knowledge import Identifier, Paper, Repository, Source
from util.utilities import create_uri, sanitize, sanitize_uri
from kg.CONSTANTS import ARXIV
from rdflib import Graph, Literal, URIRef
from rdflib.namespace import DCTERMS, DCAT, RDF, RDFS
import json
import datetime
import os
import logging

# sources url
paper_with_code_url = 'http://paperwithcode.com/'

g_pwc_paper = Graph()
g_pwc_paper_filename = 'data/rdf/paper/paper_with_code_Papers.ttl'
g_pwc_code = Graph()
g_pwc_code_filename = 'data/rdf/software/paper_with_code_Code.ttl'

# Parse the Paper with code json files and creates the corresponding data containing information on the papers and the code
def process_paper_with_code():

    # Load the json files
    paper_and_code_file = open("data/PaperWithCode/links-between-papers-and-code.json", 'r')
    paper_and_code_result = json.load(paper_and_code_file)
    paper_and_code_file.close()

    paper_with_code = create_uri(paper_with_code_url)
    num_papers = len(paper_and_code_result)
    pwc_source_obj = Source.Builder(URIRef(paper_with_code)).build()

    for paper in paper_and_code_result:
        # Add the paper to the graph
        paper_uri = create_uri(sanitize_uri(paper['paper_url']))
        pwc_paper_obj_builder = Paper.Builder(pwc_source_obj, paper_uri)
        if paper_uri == None or paper_uri == '':
            continue
        paper_title_string = ""
        if paper['paper_title'] != None:
            paper_title_string = sanitize(paper['paper_title'])
        pwc_paper_obj_builder.set_title(paper_title_string)
        paper_pdf_string = paper['paper_url_pdf']
        paper_arxiv_string = paper['paper_arxiv_id']
        if paper_pdf_string != None:
            pwc_paper_obj_builder.add_download_url(paper_pdf_string)
        if paper_arxiv_string != None:
            arxiv_uri = create_uri(ARXIV + paper_arxiv_string)
            arxiv_id_obj = Identifier.Builder(pwc_source_obj, arxiv_uri).build()
            pwc_paper_obj_builder.add_identifier(arxiv_id_obj)
        
        # Add the code to the graph
        paper_repo = create_uri(paper['repo_url'])
        repo_obj_obj = Repository.Builder(pwc_source_obj, paper_repo).build()
        pwc_paper_obj_builder.add_related(repo_obj_obj)
        repo_obj_obj.to_rdf(g_pwc_code)

        pwc_paper_obj = pwc_paper_obj_builder.build()
        pwc_paper_obj.to_rdf(g_pwc_paper)
        logging.info(f'Added paper {paper_title_string} and code {paper_repo} ({num_papers} remaining)')
        num_papers -= 1

    write_paper_with_code_graph()

def write_paper_with_code_graph():
    # writing g to a file
    if len(g_pwc_paper) > 0:
        logging.info(f'Writing paper with code paper graph to file {len(g_pwc_paper)} triples')
        g_pwc_paper.serialize(destination=g_pwc_paper_filename, format='turtle')
    g_pwc_paper.close()
    if len(g_pwc_code) > 0:
        logging.info(f'Writing paper with code paper code graph to file {len(g_pwc_code)} triples')
        g_pwc_code.serialize(destination=g_pwc_code_filename, format='turtle')
    g_pwc_code.close()
    if len(g_pwc_paper) > 0 or len(g_pwc_code) > 0:
        logging.info('Paper with code paper graph written to file')
