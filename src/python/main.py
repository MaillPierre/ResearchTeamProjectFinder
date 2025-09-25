from dotenv import load_dotenv
from rdflib import Graph
from dblp_source.dblp import dblp_most_cited_articles
from hal_source.hal import process_hal, write_hal_graph
from github_source.github import process_github, write_github_graph
from gitlab_source.gitlab import process_gitlab, write_gitlab_graph
from kg.CONSTANTS import LOCAL
from paper_with_code_source.paper_with_code import process_paper_with_code, write_paper_with_code_graph
from crossref_source.crossref import process_crossref, write_crossref_graph
import logging
import concurrent.futures
import signal
import sys

def write_graphs_to_files():
    print('Writing graphs to files...')
    write_hal_graph()
    write_github_graph()
    write_gitlab_graph()
    write_paper_with_code_graph()
    write_crossref_graph()
    print('Graphs written to files.')

def signal_handler(sig, frame):
    print(f'Signal {sig} received. Writing graphs to files...')
    write_graphs_to_files()
    sys.exit(0)

def main():
    logging.basicConfig(filename='app.log', level=logging.DEBUG)
    # Loading .env variables
    load_dotenv()

    #######################################################
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)

    final_graph = Graph()
    
    papers = dblp_most_cited_articles(start_year=2020)
    for paper in papers:
        logging.debug(f"Converting {paper.uri()} to RDF")
        paper.to_rdf(final_graph)

    final_graph.serialize("tmp/test.ttl", "turtle", str(LOCAL))

    exit()


if __name__ == '__main__':
    main()