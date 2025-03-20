# Loads all the RDF files in data/rdf and creates a graph
# that can be queried using SPARQL

from rdflib import Graph, URIRef, Literal
from rdflib.plugins.sparql import prepareQuery
from rdflib.namespace import RDF, RDFS, OWL, DCTERMS, DCAT, FOAF
import os
import json
import re
import datetime
import requests

# Namespaces
bibo_ns = 'http://purl.org/ontology/bibo/'
datacite_ns = 'http://purl.org/spar/datacite/'
pav_ns = 'http://purl.org/pav/'
adms_ns = 'http://www.w3.org/ns/adms#'
roh_ns = 'http://w3id.org/roh#'
our_ns = 'http://ns.inria.fr/kg/works/'
orcid_ns = "https://orcid.org/"
hal_author_ns = "https://shs.hal.science/search/index/q/*/authIdHal_s/"

# classes
biboDocument = URIRef(bibo_ns + 'Document')
localRepository = URIRef(our_ns + 'RepositoryIdentifier')
localSource = URIRef(our_ns + 'Source')
localOrcid = URIRef(our_ns + 'ORCID')
localGScholar = URIRef(our_ns + 'GoogleScholar')
localIdRef = URIRef(our_ns + 'IdRef')

# Properties
# pav:retrievedFrom
pavRetrievedFrom = URIRef(pav_ns + 'retrievedFrom')
pavImportedFrom = URIRef(pav_ns + 'importedFrom')
pavLastRefreshedOn = URIRef(pav_ns + 'lastRefreshedOn')
rohPlatform = URIRef(roh_ns + 'platform')
# adms:identifier
admsIdentifier = URIRef(adms_ns + 'identifier')

# sources url
paper_with_code_url = 'http://paperwithcode.com/'


# Helper functions

def sanitize_uri(s):
    return re.search(r"^((([^:/?#\s]+):)(\/\/([^/?#\s]*))?([^?#\s=]*)(\?([^#\s]*))?(#(\w*))?)", s).group(1)

def sanitize(s):
    return re.sub(r"\\[ux][0-9A-Fa-f]+", '', s)

def create_uri(s):
    return URIRef(sanitize_uri(s))

# Uses the HAL api to download data about authors, structures and papers
def process_hal():
    # Create a graph
    g = Graph()


    def process_hal_authors():
        ## Prepare the HAL API query for authors
        page_size = 100
        page = 0

        author_api_query = "*"
        author_api_fields = "fullName_s,fullName_sci,firstName_s,lastName_s,idHal_s,orcidId_s,google+scholarId_s,idrefId_s"
        author_api_filter = "idHal_s:[\"\" TO *]"
        author_api_sort = "fullName_s+asc"
        author_api_endpoint = "http://api.archives-ouvertes.fr/ref/author/?wt=json"
        author_api_url = f'{author_api_endpoint}&fl={author_api_fields}&rows={page_size}&start={page * page_size}&sort={author_api_sort}&fq={author_api_filter}&q={author_api_query}'
        author_api_uri = create_uri("http://api.archives-ouvertes.fr/ref/author/")
        
        # Send GET request to the HAL API
        author_api_response = requests.get(author_api_url)
        author_api_result = author_api_response.json()
        num_authors = author_api_result['response']['numFound']

        # Add the source to the graph
        g.add((author_api_uri, RDF.type, localSource))
        g.add((author_api_uri, pavLastRefreshedOn, Literal(datetime.datetime.now().isoformat())))
        print(f'Processing {num_authors} authors')
        while page * page_size < num_authors:
            print(f'Processing authors {page * page_size} to {min((page + 1) * page_size, num_authors)} of {num_authors}')
            # Add to the graph the info relevant to the authors
            author_query_literal = Literal(author_api_url)
            for author in author_api_result['response']['docs']:
                if('idHal_s' in author and author["idHal_s"] != None):
                    author_uri = create_uri(hal_author_ns + author['idHal_s'])
                    g.add((author_uri, RDF.type, FOAF.Person))
                    g.add((author_uri, pavRetrievedFrom, author_query_literal))
                    g.add((author_uri, pavRetrievedFrom, author_api_uri))
                    g.add((author_uri, FOAF.name, Literal(author['fullName_s'])))
                    g.add((author_uri, FOAF.firstName, Literal(author['firstName_s'])))
                    g.add((author_uri, FOAF.lastName, Literal(author['lastName_s'])))
                    g.add((author_uri, DCTERMS.alternative, Literal(author['fullName_sci'])))
                    if('orcidId_s' in author and author['orcidId_s'] != None):
                        for orcid in author['orcidId_s']:
                            orcid_uri = create_uri(orcid_ns + orcid)
                            g.add((author_uri, admsIdentifier, orcid_uri))
                            g.add((orcid_uri, RDF.type, localOrcid))
                            g.add((orcid_uri, pavRetrievedFrom, author_query_literal))
                            g.add((orcid_uri, pavRetrievedFrom, author_api_uri))
                    if('google scholarId_s' in author and author['google scholarId_s'] != None):
                        for gscholar in author['google scholarId_s']:
                            gscholar_uri = create_uri(gscholar)
                            g.add((author_uri, admsIdentifier, gscholar_uri))
                            g.add((gscholar_uri, RDF.type, localGScholar))
                            g.add((gscholar_uri, pavRetrievedFrom, author_query_literal))
                            g.add((gscholar_uri, pavRetrievedFrom, author_api_uri))
                    if('idrefId_s' in author and author['idrefId_s'] != None):
                        for idref in author['idrefId_s']:
                            idref_uri = create_uri(idref)
                            g.add((author_uri, admsIdentifier, idref_uri))
                            g.add((idref_uri, RDF.type, localIdRef))
                            g.add((idref_uri, pavRetrievedFrom, author_query_literal))
                            g.add((idref_uri, pavRetrievedFrom, author_api_uri))
                    print(f'Added author {author["fullName_s"]}')
            page += 1

            g.add((author_api_uri, pavImportedFrom, Literal(author_api_url)))
            author_api_url = f'{author_api_endpoint}&fl={author_api_fields}&rows={page_size}&start={page * page_size}&sort={author_api_sort}&fq={author_api_filter}&q={author_api_query}'
            ## Check if the result of the next query is in the cache
            author_api_page_file = f"data/hal/author/{hash(author_api_url)}.json"
            if(os.path.exists(author_api_page_file)):
                author_api_page = open(author_api_page_file, 'r')
                author_api_result = json.load(author_api_page)
                author_api_page.close()
            else:
                author_api_response = requests.get(author_api_url)
                author_api_result = author_api_response.json()
                author_api_page = open(author_api_page_file, 'w')
                json.dump(author_api_result, author_api_page)
                author_api_page.close()

    def process_hal_software():
        # Prepare the HAL API query for softwares
        page_size = 100
        page = 0

        # Software API fields
        uri_field = "uri_s"
        title_field = "title_s"
        abstract_field = "abstract_s"
        keyword_field = "keyword_s"
        author_fullname_field = "authFullName_s"
        author_idhal_field = "authIdHal_s"
        author_orcid_field = "authORCIDIdExt_s"
        author_gscholar_field = "authGoogle ScholarIdExt_s"
        code_repo_field = "softCodeRepository_s"
        programming_language_field = "softProgrammingLanguage_s"
        platform_field = "softPlatform_s"
        modified_date_field = "modifiedDate_tdate"
        released_date_field = "releasedDate_tdate"
        publication_date_field = "publicationDate_tdate"
        struct_ror_field = "structRorIdExt_s"
        struct_idref_field = "structIdrefIdExtUrl_s"
        lab_struct_ror_field = "labStructRorIdExt_s"
        lab_struct_idref_field = "labStructIdrefIdExtUrl_s"

        software_api_query = "*"
        software_api_fields = f"{uri_field},{title_field},{abstract_field},{keyword_field},{author_fullname_field},{author_idhal_field},{author_orcid_field},{author_gscholar_field},{code_repo_field},{programming_language_field},{platform_field},{modified_date_field},{released_date_field},{publication_date_field},{struct_ror_field},{struct_idref_field},{lab_struct_ror_field},{lab_struct_idref_field}"
        software_api_filter = f"docType_s:SOFTWARE AND {uri_field}:[\"\" TO *] AND openAccess_bool:true"
        software_api_sort = "uri_s+asc"
        software_api_url = f"https://api.archives-ouvertes.fr/search/?wt=json&fq={software_api_filter}&fl={software_api_fields}&rows={page_size}&start={page * page_size}&sort={software_api_sort}&q={software_api_query}"
        software_api_uri = create_uri("https://api.archives-ouvertes.fr/search/?fq=docType_s:SOFTWARE")

        # Send GET request to the HAL API
        software_api_response = requests.get(software_api_url)
        software_api_result = software_api_response.json()
        num_softwares = software_api_result['response']['numFound']

        # Add the source to the graph
        g.add((software_api_uri, RDF.type, localSource))
        g.add((software_api_uri, pavLastRefreshedOn, Literal(datetime.datetime.now().isoformat())))
        print(f'Processing {num_softwares} softwares')
        while page * page_size < num_softwares:
            software_query_literal = Literal(software_api_url)
            for software in software_api_result['response']['docs']:
                software_uri = create_uri(software[uri_field])
                g.add((software_uri, RDF.type, biboDocument))
                g.add((software_uri, pavRetrievedFrom, software_api_uri))
                g.add((software_uri, pavRetrievedFrom, software_query_literal))
                # Title
                g.add((software_uri, DCTERMS.title, Literal(software[title_field])))
                # Abstract
                if(abstract_field in software and software[abstract_field] != None):
                    for abstract in software[abstract_field]:
                        g.add((software_uri, DCTERMS.abstract, Literal(abstract)))
                # Keywords
                if(keyword_field in software and software[keyword_field] != None):
                    for keyword in software[keyword_field]:
                        g.add((software_uri, DCTERMS.subject, Literal(keyword)))
                # Author Fullname
                if(author_fullname_field in software and software[author_fullname_field] != None):
                    for fullname in software[author_fullname_field]:
                        fullname_literal = Literal(fullname)
                        g.add((software_uri, DCTERMS.creator, fullname_literal))
                # Author IdHal
                if(author_idhal_field in software and software[author_idhal_field] != None):
                    for idhal in software[author_idhal_field]:
                        idhal_literal = create_uri(hal_author_ns + idhal)
                        g.add((software_uri, DCTERMS.creator, idhal_literal))
                # Author ORCID
                if(author_orcid_field in software and software[author_orcid_field] != None):
                    for orcid in software[author_orcid_field]:
                        orcid_uri = create_uri(orcid_ns + orcid)
                        g.add((software_uri, DCTERMS.creator, orcid_uri))
                # Author Google Scholar
                if(author_gscholar_field in software and software[author_gscholar_field] != None):
                    for gscholar in software[author_gscholar_field]:
                        gscholar_uri = create_uri( gscholar)
                        g.add((software_uri, DCTERMS.creator, gscholar_uri))
                # Code repository
                if(code_repo_field in software and software[code_repo_field] != None):
                    for repo in software[code_repo_field]:
                        repo_uri = create_uri(repo)
                        g.add((software_uri, DCTERMS.source, repo_uri))
                # Programming language
                if(programming_language_field in software and software[programming_language_field] != None):
                    for language in software[programming_language_field]:
                        g.add((software_uri, DCTERMS.language, Literal(language)))
                # Platform
                if(platform_field in software and software[platform_field] != None):
                    for platform in software[platform_field]:
                        g.add((software_uri, rohPlatform, Literal(platform)))
                # Modified date
                if(modified_date_field in software and software[modified_date_field] != None):
                    for modified_date in software[modified_date_field]:
                        g.add((software_uri, DCTERMS.modified, Literal(modified_date)))
                # Released date
                if(released_date_field in software and software[released_date_field] != None):
                    for released_date in software[released_date_field]:
                        g.add((software_uri, DCTERMS.available, Literal(released_date)))
                # Publication date
                if(publication_date_field in software and software[publication_date_field] != None):
                    for publication_date in software[publication_date_field]:
                        g.add((software_uri, DCTERMS.issued, Literal(publication_date)))
                # Structure ROR
                if(struct_ror_field in software and software[struct_ror_field] != None):
                    for ror in software[struct_ror_field]:
                        ror_uri = create_uri(ror)
                        g.add((software_uri, admsIdentifier, ror_uri))
                        g.add((ror_uri, RDF.type, FOAF.Organization))
                # Structure IdRef
                if(struct_idref_field in software and software[struct_idref_field] != None):
                    for idref in software[struct_idref_field]:
                        idref_uri = create_uri(idref)
                        g.add((software_uri, admsIdentifier, idref_uri))
                        g.add((idref_uri, RDF.type, FOAF.Organization))
                # Lab Structure ROR
                if(lab_struct_ror_field in software and software[lab_struct_ror_field] != None):
                    for ror in software[lab_struct_ror_field]:
                        lab_ror_uri = create_uri(ror)
                        g.add((software_uri, admsIdentifier, lab_ror_uri))
                        g.add((lab_ror_uri, RDF.type, FOAF.Organization))
                # Lab Structure IdRef
                if(lab_struct_idref_field in software and software[lab_struct_idref_field] != None):
                    for idref in software[lab_struct_idref_field]:
                        idref_uri = create_uri(idref)
                        g.add((software_uri, admsIdentifier, idref_uri))
                print(f'Added software {software[title_field]}')
            page += 1
                

    process_hal_authors()
    process_hal_software()
    # writing g to a file
    print(f'Writing graph to file {len(g)} triples')
    g.serialize(destination='data/rdf/hal.ttl', format='turtle')
    print('Graph written to file')

# Parse the Paper with code json files and creates the corresponding data containing information on the papers and the code
def process_paper_with_code():
    # Create a graph
    g = Graph()

    # Load the json files
    paper_and_code_file = open("data/PaperWithCode/links-between-papers-and-code.json", 'r')
    paper_and_code_result = json.load(paper_and_code_file)

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
        g.add((paper_uri, RDF.type, biboDocument))
        g.add((paper_uri, pavRetrievedFrom, paper_with_code))
        g.add((paper_uri, DCTERMS.title, paper_label))
        if paper_pdf_string != None:
            g.add((paper_uri, DCAT.downloadURL, Literal(paper_pdf_string)))
        if paper_arxiv_string != None:
            g.add((paper_uri, admsIdentifier, create_uri('https://arxiv.org/abs/' + paper_arxiv_string)))
        
        # Add the code to the graph
        paper_repo = create_uri(paper['repo_url'])
        g.add((paper_repo, RDF.type, localRepository))
        g.add((paper_repo, pavRetrievedFrom, paper_with_code))
        g.add((paper_repo, admsIdentifier , paper_repo))

        # Add the relationship between the paper and the code
        g.add((paper_uri, DCTERMS.relation, paper_repo))
        print(f'Added paper {paper_label} and code {paper_repo} ({num_papers} remaining)')
        num_papers -= 1

    g.add((paper_with_code, RDF.type, localSource))
    g.add((paper_with_code, pavImportedFrom, Literal(paper_with_code_url + 'about')))
    g.add((paper_with_code, pavLastRefreshedOn, Literal(datetime.datetime.now().isoformat())))

    # writing g to a file
    print(f'Writing graph to file {len(g)} triples')
    g.serialize(destination='data/rdf/paper_with_code.ttl', format='turtle')
    print('Graph written to file')






#######################################################
# Load all RDF files in data/rdf and display data

# Query the graph

# Query 1: Get all the classes in the graph
q1 = prepareQuery('''
    PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
    PREFIX owl: <http://www.w3.org/2002/07/owl#>
    SELECT DISTINCT ?class
    WHERE {
        { ?s a ?class }
        UNION { ?class a rdfs:Class }
        UNION { ?class a owl:Class }
        UNION { ?class rdfs:subClassOf ?superclass }
        UNION { ?subClass rdfs:subClassOf ?class }
    }
''')

# Query 2: Get all the properties in the graph

q2 = prepareQuery('''
    SELECT DISTINCT ?property
    WHERE {
        ?s ?property ?o
    }
''')

# process_paper_with_code()
# print('Paper with code processed')
process_hal()
print('HAL processed')

# Load all RDF files in data/rdf
# Create a graph
g = Graph()
for file in os.listdir('data/rdf'):
    if file.endswith('.ttl'):
        g.parse(f'data/rdf/{file}', format='turtle')
    elif file.endswith('.rdf'):
        g.parse(f'data/rdf/{file}', format='xml')

print('Graph loaded')

# writing g to a file
print(f'Writing graph to file {len(g)} triples')
g.serialize(destination='data/data.ttl', format='turtle')
print('Graph written to file')

exit()