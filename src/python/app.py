from dotenv import load_dotenv
from hal_source.hal import process_hal
from github_source.github import process_github
from gitlab_source.gitlab import process_gitlab
from paper_with_code_source.paper_with_code import process_paper_with_code
import logging

def main():
    logging.basicConfig(filename='app.log', level=logging.INFO)
    # Loading .env variables
    load_dotenv()

    #######################################################


    process_paper_with_code()
    print('Paper with code processed')
    process_hal()
    print('HAL processed')
    process_github()
    print('Github processed')
    process_gitlab()
    print('Gitlab processed')

    exit()


if __name__ == '__main__':
    main()