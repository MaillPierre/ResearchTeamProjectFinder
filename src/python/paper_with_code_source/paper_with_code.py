from util.utilities import create_uri, sanitize, sanitize_uri, adms_identifier, pav_importedFrom, pav_lastRefreshedOn, local_Source, local_RepositoryId, local_ArXiv, pav_retrievedFrom, bibo_Document, arxiv_ns
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

    for paper in paper_and_code_result:
        # Add the paper to the graph
        paper_uri = create_uri(sanitize_uri(paper['paper_url']))
        if paper_uri == None or paper_uri == '':
            continue
        paper_title_string = ""
        if paper['paper_title'] != None:
            paper_title_string = sanitize(paper['paper_title'])
        paper_label = Literal(paper_title_string)
        paper_pdf_string = paper['paper_url_pdf']
        paper_arxiv_string = paper['paper_arxiv_id']
        g_pwc_paper.add((paper_uri, RDF.type, bibo_Document))
        g_pwc_paper.add((paper_uri, pav_retrievedFrom, paper_with_code))
        g_pwc_paper.add((paper_uri, DCTERMS.title, paper_label))
        if paper_pdf_string != None:
            g_pwc_paper.add((paper_uri, DCAT.downloadURL, Literal(paper_pdf_string)))
        if paper_arxiv_string != None:
            arxiv_uri = create_uri(arxiv_ns + paper_arxiv_string)
            g_pwc_paper.add((arxiv_uri, RDF.type, local_ArXiv))
            g_pwc_paper.add((arxiv_uri, pav_retrievedFrom, paper_with_code))
            g_pwc_paper.add((paper_uri, adms_identifier, create_uri(arxiv_ns + paper_arxiv_string)))
        
        # Add the code to the graph
        paper_repo = create_uri(paper['repo_url'])
        g_pwc_code.add((paper_repo, RDF.type, local_RepositoryId))
        g_pwc_code.add((paper_repo, pav_retrievedFrom, paper_with_code))
        g_pwc_code.add((paper_repo, adms_identifier , paper_repo))

        # Add the relationship between the paper and the code
        g_pwc_paper.add((paper_uri, DCTERMS.relation, paper_repo))
        g_pwc_code.add((paper_uri, DCTERMS.relation, paper_repo))
        logging.info(f'Added paper {paper_label} and code {paper_repo} ({num_papers} remaining)')
        num_papers -= 1

    g_pwc_paper.add((paper_with_code, RDF.type, local_Source))
    g_pwc_paper.add((paper_with_code, pav_importedFrom, Literal(paper_with_code_url + 'about')))
    g_pwc_paper.add((paper_with_code, pav_lastRefreshedOn, Literal(datetime.datetime.now().isoformat())))

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
