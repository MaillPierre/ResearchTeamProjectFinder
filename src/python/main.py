from dotenv import load_dotenv
from  hal_source.hal import process_hal, write_hal_graph
from github_source.github import process_github, write_github_graph
from gitlab_source.gitlab import process_gitlab, write_gitlab_graph
from paper_with_code_source.paper_with_code import process_paper_with_code, write_paper_with_code_graph
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
    print('Graphs written to files.')

def signal_handler(sig, frame):
    print(f'Signal {sig} received. Writing graphs to files...')
    write_graphs_to_files()
    sys.exit(0)

def main():
    logging.basicConfig(filename='app.log', level=logging.INFO)
    # Loading .env variables
    load_dotenv()

    #######################################################
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)


    with concurrent.futures.ThreadPoolExecutor() as executor:
        futures = [
            executor.submit(process_paper_with_code),
            executor.submit(process_hal),
            executor.submit(process_github),
            executor.submit(process_gitlab)
        ]
        for future in concurrent.futures.as_completed(futures):
            print(f'Process completed: {future.result()}')
    
    write_graphs_to_files()

    exit()


if __name__ == '__main__':
    main()