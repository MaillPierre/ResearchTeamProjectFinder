from util.utilities import create_uri, sanitize, sanitize_uri, adms_identifier, pav_importedFrom, pav_lastRefreshedOn, local_Source, local_RepositoryId, local_ArXiv, pav_retrievedFrom, bibo_Document, arxiv_ns
from rdflib import Graph, Literal, URIRef
from rdflib.namespace import DCTERMS, DCAT, RDF, RDFS
import json
import datetime
import os
import logging

# sources url
paper_with_code_url = 'http://paperwithcode.com/'

# Parse the Paper with code json files and creates the corresponding data containing information on the papers and the code
def process_paper_with_code():
    # Create a graph
    g_paper = Graph()
    g_paper_filename = 'data/rdf/paper/paper_with_code_Papers.ttl'
    g_code = Graph()
    g_code_filename = 'data/rdf/software/paper_with_code_Code.ttl'

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
        g_paper.add((paper_uri, RDF.type, bibo_Document))
        g_paper.add((paper_uri, pav_retrievedFrom, paper_with_code))
        g_paper.add((paper_uri, DCTERMS.title, paper_label))
        if paper_pdf_string != None:
            g_paper.add((paper_uri, DCAT.downloadURL, Literal(paper_pdf_string)))
        if paper_arxiv_string != None:
            arxiv_uri = create_uri(arxiv_ns + paper_arxiv_string)
            g_paper.add((arxiv_uri, RDF.type, local_ArXiv))
            g_paper.add((arxiv_uri, pav_retrievedFrom, paper_with_code))
            g_paper.add((paper_uri, adms_identifier, create_uri(arxiv_ns + paper_arxiv_string)))
        
        # Add the code to the graph
        paper_repo = create_uri(paper['repo_url'])
        g_code.add((paper_repo, RDF.type, local_RepositoryId))
        g_code.add((paper_repo, pav_retrievedFrom, paper_with_code))
        g_code.add((paper_repo, adms_identifier , paper_repo))

        # Add the relationship between the paper and the code
        g_paper.add((paper_uri, DCTERMS.relation, paper_repo))
        g_code.add((paper_uri, DCTERMS.relation, paper_repo))
        logging.info(f'Added paper {paper_label} and code {paper_repo} ({num_papers} remaining)')
        num_papers -= 1

    g_paper.add((paper_with_code, RDF.type, local_Source))
    g_paper.add((paper_with_code, pav_importedFrom, Literal(paper_with_code_url + 'about')))
    g_paper.add((paper_with_code, pav_lastRefreshedOn, Literal(datetime.datetime.now().isoformat())))

    # writing g to a file
    logging.info(f'Writing paper graph to file {len(g_paper)} triples')
    g_paper.serialize(destination=g_paper_filename, format='turtle')
    logging.info(f'Writing code graph to file {len(g_code)} triples')
    g_code.serialize(destination=g_code_filename, format='turtle')
    logging.info('Graph written to file')
    g_code.close()
    g_paper.close()
