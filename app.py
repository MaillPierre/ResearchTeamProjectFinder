# Loads all the RDF files in data/rdf and creates a graph
# that can be queried using SPARQL

from rdflib import Graph, URIRef, Literal, BNode
from rdflib.plugins.sparql import prepareQuery
from rdflib.namespace import RDF, RDFS, OWL, DCTERMS, DCAT, FOAF
import xml.etree.ElementTree as ET
from github import Github, PaginatedList, NamedUser, enable_console_debug_logging
from github import Auth
import os
import json
import re
import datetime
import requests
import hashlib
from dotenv import load_dotenv
from urllib.parse import quote_plus, urlencode

load_dotenv()

# Namespaces
bibo_ns = 'http://purl.org/ontology/bibo/'
dcmitype_ns = "http://purl.org/dc/dcmitype/"
datacite_ns = 'http://purl.org/spar/datacite/'
pav_ns = 'http://purl.org/pav/'
adms_ns = 'http://www.w3.org/ns/adms#'
roh_ns = 'http://w3id.org/roh#'
our_ns = 'http://ns.inria.fr/kg/works/'
orcid_ns = "https://orcid.org/"
hal_ns = "https://hal.science/"
hal_author_ns = "https://shs.hal.science/search/index/q/*/authIdHal_s/"
arxiv_ns = "https://arxiv.org/abs/"

# classes
biboDocument = URIRef(bibo_ns + 'Document')
dcmitypeSoftware = URIRef(dcmitype_ns + 'Software')
dataciteOrganizationIdentifier = URIRef(datacite_ns + 'OrganizationIdentifier')
localRepository = URIRef(our_ns + 'RepositoryIdentifier')
localSource = URIRef(our_ns + 'Source')
localOrcid = URIRef(our_ns + 'ORCID')
localArXiv = URIRef(our_ns + 'Arxiv')
localGScholar = URIRef(our_ns + 'GoogleScholar')
localIdRef = URIRef(our_ns + 'IdRef')
localIdHal = URIRef(our_ns + 'IdHal')
localIdHal = URIRef(our_ns + 'GitHubIdentifier')

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
    match = re.search(r"(^(([^:/?#\s]+):)(\/\/([^/?#\s]*))?([^?#\s=]*)(\?([^#\s]*))?(#(\w*))?)", s)
    if match == None:
        return None
    return match.group(1)

def sanitize(s):
    return re.sub(r"\\[ux][0-9A-Fa-f]+", '', s)

def create_uri(s):
    healthy_uri = sanitize_uri(s)
    if healthy_uri == None:
        return BNode()
    return URIRef(sanitize_uri(s))

def json_encode_paginated_list(paginated_list: PaginatedList):
    print("encoding paginated list", paginated_list.totalCount)
    json_list = []
    for item in paginated_list:
        json_list.append(item.raw_data)

    return json.JSONEncoder().encode(json_list)

# Uses the HAL api to download data about authors, structures and papers
def process_hal():
    # Create a graph
    g_person = Graph()
    g_person_filename = 'data/rdf/person/hal_Person.ttl'
    g_organization = Graph()
    g_organization_filename = 'data/rdf/organization/hal_Organization.ttl'
    g_software = Graph()
    g_software_filename = 'data/rdf/software/hal_Software.ttl'
    g_article = Graph()
    g_article_filename = 'data/rdf/article/hal_Article.ttl'

    def process_hal_authors():
        ## Prepare the HAL API query for authors
        page_size = 100
        page = 0

        # Author API fields
        firstname_field = "firstName_s"
        lastname_field = "lastName_s"
        fullname_field = "fullName_s"
        fullname_sci_field = "fullName_sci"
        idhal_field = "idHal_s"
        orcid_field = "orcidId_s"
        gscholar_field = 'google scholarId_s'
        idref_field = 'idrefId_s'

        author_api_query = "*"
        author_api_fields = f"{firstname_field},{fullname_sci_field},{firstname_field},{lastname_field},{idhal_field},{orcid_field},{gscholar_field.replace(' ', '+')},{idref_field}"
        author_api_filter = f"{idhal_field}:[\"\" TO *]"
        author_api_sort = f"{fullname_field}+asc"
        author_api_endpoint = "http://api.archives-ouvertes.fr/ref/author/?wt=json"
        author_api_url = f'{author_api_endpoint}&fl={author_api_fields}&rows={page_size}&start={page * page_size}&sort={author_api_sort}&fq={author_api_filter}&q={author_api_query}'
        author_api_uri = create_uri("http://api.archives-ouvertes.fr/ref/author/")
        
        # Send GET request to the HAL API
        author_api_response = requests.get(author_api_url)
        author_api_result = author_api_response.json()
        num_authors = author_api_result['response']['numFound']

        # Add the source to the graph
        g_person.add((author_api_uri, RDF.type, localSource))
        g_person.add((author_api_uri, pavLastRefreshedOn, Literal(datetime.datetime.now().isoformat())))
        print(f'Processing {num_authors} authors')
        while page * page_size < num_authors:
            print(f'Processing authors {page * page_size} to {min((page + 1) * page_size, num_authors)} of {num_authors}')
            # Add to the graph the info relevant to the authors
            author_query_literal = Literal(author_api_url)
            for author in author_api_result['response']['docs']:
                if(idhal_field in author and author[idhal_field] != None):
                    author_uri = create_uri(hal_author_ns + author[idhal_field])
                    g_person.add((author_uri, RDF.type, FOAF.Person))
                    g_person.add((author_uri, pavRetrievedFrom, author_query_literal))
                    g_person.add((author_uri, pavRetrievedFrom, author_api_uri))
                    if(fullname_field in author and author[fullname_field] != None):
                        g_person.add((author_uri, FOAF.name, Literal(author[fullname_field])))
                    if(firstname_field in author and author[firstname_field] != None):
                        g_person.add((author_uri, FOAF.firstName, Literal(author[firstname_field])))
                    if(lastname_field in author and author[lastname_field] != None):
                        g_person.add((author_uri, FOAF.lastName, Literal(author[lastname_field])))
                    if(fullname_sci_field in author and author[fullname_sci_field] != None):
                        g_person.add((author_uri, DCTERMS.alternative, Literal(author[fullname_sci_field])))
                    if(orcid_field in author and author[orcid_field] != None):
                        for orcid in author[orcid_field]:
                            orcid_uri = create_uri(orcid_ns + orcid)
                            g_person.add((author_uri, admsIdentifier, orcid_uri))
                            g_person.add((orcid_uri, RDF.type, localOrcid))
                            g_person.add((orcid_uri, pavRetrievedFrom, author_query_literal))
                            g_person.add((orcid_uri, pavRetrievedFrom, author_api_uri))
                    if(gscholar_field in author and author[gscholar_field] != None):
                        for gscholar in author[gscholar_field]:
                            gscholar_uri = create_uri(gscholar)
                            g_person.add((author_uri, admsIdentifier, gscholar_uri))
                            g_person.add((gscholar_uri, RDF.type, localGScholar))
                            g_person.add((gscholar_uri, pavRetrievedFrom, author_query_literal))
                            g_person.add((gscholar_uri, pavRetrievedFrom, author_api_uri))
                    if(idref_field in author and author[idref_field] != None):
                        for idref in author[idref_field]:
                            idref_uri = create_uri(idref)
                            g_person.add((author_uri, admsIdentifier, idref_uri))
                            g_person.add((idref_uri, RDF.type, localIdRef))
                            g_person.add((idref_uri, pavRetrievedFrom, author_query_literal))
                            g_person.add((idref_uri, pavRetrievedFrom, author_api_uri))
                    print(f'Added author {author_uri}')
            page += 1

            g_person.add((author_api_uri, pavImportedFrom, Literal(author_api_url)))
            author_api_url = f'{author_api_endpoint}&fl={author_api_fields}&rows={page_size}&start={page * page_size}&sort={author_api_sort}&fq={author_api_filter}&q={author_api_query}'

            ## Check if the result of the next query is in the cache
            author_api_page_file = f"data/hal/author/{hashlib.md5(author_api_url.encode()).hexdigest()}.json"
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
        oa_field = "openAccess_bool"
        halid_field = "halId_s"
        docid_field = "docid"
        doctype_field = "docType_s"
        label_field = "label_s"
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
        xml_field = "label_xml"

        software_api_query = "*"
        software_api_fields = f"{halid_field},{docid_field},{label_field},{uri_field},{title_field},{abstract_field},{keyword_field},{author_fullname_field},{author_idhal_field},{author_orcid_field},{author_gscholar_field},{code_repo_field},{programming_language_field},{platform_field},{modified_date_field},{released_date_field},{publication_date_field},{struct_ror_field},{struct_idref_field},{lab_struct_ror_field},{lab_struct_idref_field},{oa_field},{xml_field}"
        software_api_filter = f"{doctype_field}:SOFTWARE"
        software_api_sort = f"{docid_field}+asc"
        software_api_url = f"https://api.archives-ouvertes.fr/search/?wt=json&q={software_api_query}&fq={software_api_filter}&fl={software_api_fields}&rows={page_size}&start={page * page_size}&sort={software_api_sort}"

        software_api_uri = create_uri("https://api.archives-ouvertes.fr/search/?fq=docType_s:SOFTWARE")

        # Send GET request to the HAL API
        software_api_response = requests.get(software_api_url)
        software_api_result = software_api_response.json()
        num_softwares = software_api_result['response']['numFound']

        # Add the source to the graph
        g_software.add((software_api_uri, RDF.type, localSource))
        g_software.add((software_api_uri, pavLastRefreshedOn, Literal(datetime.datetime.now().isoformat())))
        print(f'Processing {num_softwares} softwares')
        while page * page_size < num_softwares:
            software_api_url = f"https://api.archives-ouvertes.fr/search/?wt=json&fq={software_api_filter}&fl={software_api_fields}&rows={page_size}&start={page * page_size}&sort={software_api_sort}&q={software_api_query}"

            ## Check if the result of the next query is in the cache
            software_api_page_file = f"data/hal/software/{hashlib.md5((software_api_url.encode())).hexdigest()}.json"
            if(os.path.exists(software_api_page_file)):
                software_api_page = open(software_api_page_file, 'r')
                software_api_result = json.load(software_api_page)
                software_api_page.close()
            else:
                software_api_response = requests.get(software_api_url)
                software_api_result = software_api_response.json()
                software_api_page = open(software_api_page_file, 'w')
                json.dump(software_api_result, software_api_page)
                software_api_page.close()

            software_query_literal = Literal(software_api_url)
            for software in software_api_result['response']['docs']:
                software_uri = create_uri(hal_ns + software[halid_field])
                print(f'Adding software {software_uri}')
                g_software.add((software_uri, RDF.type, dcmitypeSoftware))
                g_software.add((software_uri, pavRetrievedFrom, software_api_uri))
                g_software.add((software_uri, pavRetrievedFrom, software_query_literal))
                # Title
                if(title_field in software and software[title_field] != None and len(software[title_field]) > 0):
                    for title in software[title_field]:
                        g_software.add((software_uri, DCTERMS.title, Literal(title)))
                # Abstract
                if(abstract_field in software and software[abstract_field] != None and len(software[abstract_field]) > 0):
                    for abstract in software[abstract_field]:
                        g_software.add((software_uri, DCTERMS.abstract, Literal(abstract)))
                # Keywords
                if(keyword_field in software and software[keyword_field] != None and len(software[keyword_field]) > 0):
                    for keyword in software[keyword_field]:
                        g_software.add((software_uri, DCTERMS.subject, Literal(keyword)))
                # Author Fullname
                if(author_fullname_field in software and software[author_fullname_field] != None and len(software[author_fullname_field]) > 0):
                    for fullname in software[author_fullname_field]:
                        fullname_literal = Literal(fullname)
                        author_bnode = BNode()
                        g_software.add((author_bnode, RDF.type, FOAF.Person))
                        g_software.add((author_bnode, FOAF.name, fullname_literal))
                        g_software.add((author_bnode, pavRetrievedFrom, software_query_literal))
                        g_software.add((author_bnode, pavRetrievedFrom, software_api_uri))
                        g_software.add((software_uri, DCTERMS.creator, author_bnode))
                # Author IdHal
                if(author_idhal_field in software and software[author_idhal_field] != None and len(software[author_idhal_field]) > 0):
                    for idhal in software[author_idhal_field]:
                        idhal_uri = create_uri(hal_author_ns + idhal)
                        author_bnode = BNode()
                        g_software.add((author_bnode, RDF.type, FOAF.Person))
                        g_software.add((author_bnode, admsIdentifier, idhal_uri))
                        g_software.add((author_bnode, pavRetrievedFrom, software_query_literal))
                        g_software.add((author_bnode, pavRetrievedFrom, software_api_uri))
                        g_person.add((idhal_uri, RDF.type, localIdHal))
                        g_person.add((idhal_uri, pavRetrievedFrom, software_query_literal))
                        g_person.add((idhal_uri, pavRetrievedFrom, software_api_uri))
                        g_software.add((software_uri, DCTERMS.creator, author_bnode))
                # Author ORCID
                if(author_orcid_field in software and software[author_orcid_field] != None and len(software[author_orcid_field]) > 0):
                    for orcid in software[author_orcid_field]:
                        orcid_uri = create_uri(orcid_ns + orcid)
                        author_bnode = BNode()
                        g_software.add((author_bnode, RDF.type, FOAF.Person))
                        g_software.add((author_bnode, admsIdentifier, orcid_uri))
                        g_person.add((orcid_uri, RDF.type, localOrcid))
                        g_software.add((author_bnode, pavRetrievedFrom, software_query_literal))
                        g_software.add((author_bnode, pavRetrievedFrom, software_api_uri))
                        g_person.add((orcid_uri, pavRetrievedFrom, software_query_literal))
                        g_person.add((orcid_uri, pavRetrievedFrom, software_api_uri))
                        g_software.add((software_uri, DCTERMS.creator, author_bnode))
                # Author Google Scholar
                if(author_gscholar_field in software and software[author_gscholar_field] != None and len(software[author_gscholar_field]) > 0):
                    for gscholar in software[author_gscholar_field]:
                        gscholar_uri = create_uri( gscholar)
                        author_bnode = BNode()
                        g_software.add((author_bnode, RDF.type, FOAF.Person))
                        g_software.add((author_bnode, admsIdentifier, gscholar_uri))
                        g_person.add((gscholar_uri, RDF.type, localGScholar))
                        g_software.add((author_bnode, pavRetrievedFrom, software_query_literal))
                        g_software.add((author_bnode, pavRetrievedFrom, software_api_uri))
                        g_person.add((gscholar_uri, pavRetrievedFrom, software_query_literal))
                        g_person.add((gscholar_uri, pavRetrievedFrom, software_api_uri))
                        g_software.add((software_uri, DCTERMS.creator, author_bnode))
                # Code repository
                if(code_repo_field in software and software[code_repo_field] != None and len(software[code_repo_field]) > 0):
                    for repo in software[code_repo_field]:
                        repo_uri = create_uri(repo)
                        g_software.add((repo_uri, RDF.type, localRepository))
                        g_software.add((repo_uri, pavRetrievedFrom, software_query_literal))
                        g_software.add((repo_uri, pavRetrievedFrom, software_api_uri))
                        g_software.add((software_uri, DCTERMS.source, repo_uri))
                # Programming language
                if(programming_language_field in software and software[programming_language_field] != None and len(software[programming_language_field]) > 0):
                    for language in software[programming_language_field]:
                        g_software.add((software_uri, DCTERMS.language, Literal(language)))
                # Platform
                if(platform_field in software and software[platform_field] != None and len(software[platform_field]) > 0):
                    for platform in software[platform_field]:
                        g_software.add((software_uri, rohPlatform, Literal(platform)))
                # Modified date
                if(modified_date_field in software and software[modified_date_field] != None):
                    g_software.add((software_uri, DCTERMS.modified, Literal(software[modified_date_field])))
                # Released date
                if(released_date_field in software and software[released_date_field] != None and len(software[released_date_field]) > 0):
                    g_software.add((software_uri, DCTERMS.available, Literal(software[released_date_field])))
                # Publication date
                if(publication_date_field in software and software[publication_date_field] != None and len(software[publication_date_field]) > 0):
                    g_software.add((software_uri, DCTERMS.issued, Literal(software[publication_date_field])))
                # Structure ROR
                if(struct_ror_field in software and software[struct_ror_field] != None and len(software[struct_ror_field]) > 0):
                    for ror in software[struct_ror_field]:
                        ror_uri = create_uri(ror)
                        org_bnode = BNode()
                        g_software.add((org_bnode, RDF.type, FOAF.Organization))
                        g_software.add((org_bnode, pavRetrievedFrom, software_query_literal))
                        g_software.add((org_bnode, pavRetrievedFrom, software_api_uri))
                        g_software.add((software_uri, DCTERMS.publisher, org_bnode))
                        g_software.add((org_bnode, admsIdentifier, ror_uri))
                        g_organization.add((ror_uri, RDF.type, dataciteOrganizationIdentifier))
                        g_organization.add((ror_uri, pavRetrievedFrom, software_query_literal))
                        g_organization.add((ror_uri, pavRetrievedFrom, software_api_uri))
                # Structure IdRef
                if(struct_idref_field in software and software[struct_idref_field] != None and len(software[struct_idref_field]) > 0):
                    for idref in software[struct_idref_field]:
                        idref_uri = create_uri(idref)
                        org_bnode = BNode()
                        g_software.add((org_bnode, RDF.type, FOAF.Organization))
                        g_software.add((org_bnode, pavRetrievedFrom, software_query_literal))
                        g_software.add((org_bnode, pavRetrievedFrom, software_api_uri))
                        g_software.add((software_uri, DCTERMS.publisher, org_bnode))
                        g_software.add((org_bnode, admsIdentifier, idref_uri))
                        g_organization.add((idref_uri, RDF.type, dataciteOrganizationIdentifier))
                        g_organization.add((idref_uri, pavRetrievedFrom, software_query_literal))
                        g_organization.add((idref_uri, pavRetrievedFrom, software_api_uri))
                # Lab Structure ROR
                if(lab_struct_ror_field in software and software[lab_struct_ror_field] != None and len(software[lab_struct_ror_field]) > 0):
                    for lab_ror in software[lab_struct_ror_field]:
                        lab_ror_uri = create_uri(lab_ror)
                        org_bnode = BNode()
                        g_software.add((org_bnode, RDF.type, FOAF.Organization))
                        g_software.add((org_bnode, pavRetrievedFrom, software_query_literal))
                        g_software.add((org_bnode, pavRetrievedFrom, software_api_uri))
                        g_software.add((software_uri, DCTERMS.publisher, org_bnode))
                        g_software.add((org_bnode, admsIdentifier, lab_ror_uri))
                        g_organization.add((lab_ror_uri, RDF.type, dataciteOrganizationIdentifier))
                        g_organization.add((lab_ror_uri, pavRetrievedFrom, software_query_literal))
                        g_organization.add((lab_ror_uri, pavRetrievedFrom, software_api_uri))
                # Lab Structure IdRef
                if(lab_struct_idref_field in software and software[lab_struct_idref_field] != None and len(software[lab_struct_idref_field]) > 0):
                    for lab_idref in software[lab_struct_idref_field]:
                        lab_idref_uri = create_uri(lab_idref)
                        org_bnode = BNode()
                        g_software.add((org_bnode, RDF.type, FOAF.Organization))
                        g_software.add((org_bnode, pavRetrievedFrom, software_query_literal))
                        g_software.add((org_bnode, pavRetrievedFrom, software_api_uri))
                        g_software.add((software_uri, DCTERMS.publisher, org_bnode))
                        g_software.add((org_bnode, admsIdentifier, lab_idref_uri))
                        g_organization.add((lab_idref_uri, RDF.type, dataciteOrganizationIdentifier))
                        g_organization.add((lab_idref_uri, pavRetrievedFrom, software_query_literal))
                        g_organization.add((lab_idref_uri, pavRetrievedFrom, software_api_uri))
                # Open Access
                if(oa_field in software and software[oa_field] != None and software[oa_field] == True):
                    g_software.add((software_uri, DCTERMS.rights, Literal("Open Access")))
                # XML
                # Attempte to extract the license from the XML
                if(xml_field in software and software[xml_field] != None):
                    xml_string = software[xml_field]
                    xml_string = xml_string.replace('\\"', '"')
                    # print(xml_string)
                    xml = ET.fromstring(xml_string)
                    # print(xml)
                    xml_stmts = xml.findall(".//TEI/biblFull/publicationStmt/availability/licence")
                    for child in xml_stmts:
                        if(child.tag == "licence"):
                            license_uri = create_uri(child.get("target"))
                            g_software.add((software_uri, DCTERMS.license, license_uri))
                            g_software.add((license_uri, RDFS.label, Literal(child.text)))
                print(f'Added software {software[title_field]}')
            page += 1

                

    process_hal_authors()
    process_hal_software()
    
    # writing g to a file
    print(f'Writing software graph to file {len(g_software)} triples')
    g_software.serialize(destination=g_software_filename, format='turtle')
    print(f'Writing person graph to file {len(g_person)} triples')
    g_person.serialize(destination=g_person_filename, format='turtle')
    print(f'Writing organization graph to file {len(g_organization)} triples')
    g_organization.serialize(destination=g_organization_filename, format='turtle')
    print(f'Writing article graph to file {len(g_article)} triples')
    g_article.serialize(destination=g_article_filename, format='turtle')
    print('Graphs written to file')

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
        g_paper.add((paper_uri, RDF.type, biboDocument))
        g_paper.add((paper_uri, pavRetrievedFrom, paper_with_code))
        g_paper.add((paper_uri, DCTERMS.title, paper_label))
        if paper_pdf_string != None:
            g_paper.add((paper_uri, DCAT.downloadURL, Literal(paper_pdf_string)))
        if paper_arxiv_string != None:
            arxiv_uri = create_uri(arxiv_ns + paper_arxiv_string)
            g_paper.add((arxiv_uri, RDF.type, localArXiv))
            g_paper.add((arxiv_uri, pavRetrievedFrom, paper_with_code))
            g_paper.add((paper_uri, admsIdentifier, create_uri(arxiv_ns + paper_arxiv_string)))
        
        # Add the code to the graph
        paper_repo = create_uri(paper['repo_url'])
        g_code.add((paper_repo, RDF.type, localRepository))
        g_code.add((paper_repo, pavRetrievedFrom, paper_with_code))
        g_code.add((paper_repo, admsIdentifier , paper_repo))

        # Add the relationship between the paper and the code
        g_paper.add((paper_uri, DCTERMS.relation, paper_repo))
        g_code.add((paper_uri, DCTERMS.relation, paper_repo))
        print(f'Added paper {paper_label} and code {paper_repo} ({num_papers} remaining)')
        num_papers -= 1

    g_paper.add((paper_with_code, RDF.type, localSource))
    g_paper.add((paper_with_code, pavImportedFrom, Literal(paper_with_code_url + 'about')))
    g_paper.add((paper_with_code, pavLastRefreshedOn, Literal(datetime.datetime.now().isoformat())))

    # writing g to a file
    print(f'Writing paper graph to file {len(g)} triples')
    g_paper.serialize(destination=g_paper_filename, format='turtle')
    print(f'Writing code graph to file {len(g)} triples')
    g_code.serialize(destination=g_code_filename, format='turtle')
    print('Graph written to file')

def process_github():
    max_query_length = 256

    g_Software = Graph()
    g_Person = Graph()
    g_Organization = Graph()

    # Connect to the Github API
    github_token = os.getenv('github_token')
    g = Github(github_token)
    # enable_console_debug_logging() # Enable debug logging
    print(f'Connected to Github as {g.get_user().login}')
    
    # Sandbox query: list the repositories including INRIA
    # repos_query = g.search_repositories(query="INRIA", sort="updated", order="asc")
    # print(f'Found {repos_query.totalCount} repositories')
    # for repo in repos_query.get_page(0):
    #     print(f'{repo.full_name} - {repo.description}')
    #     print("topics:", repo.get_topics())
    #     print("language:", repo.get_languages())
    #     print("contributors:", repo.get_contributors())
    #     print("content:", repo.get_contents(''))
    #     print("release:", repo.get_releases())

    # Search for specific users
    ## Load existing users from the graph in rdf/person
    print("Loading existing users from the graph")
    g_known_person = Graph()
    for file in os.listdir('data/rdf/person/'):
        if file.endswith('.ttl'):
            g_known_person.parse('data/rdf/person/' + file, format='turtle')
    print(f'Loaded {len(g_known_person)} triples about people from the graph')

    # Retrieve the list of users from the graph
    query = prepareQuery('''
        SELECT DISTINCT ?person ?name
        WHERE {
            ?person a foaf:Person .
            { ?person foaf:firstName ?first ;
                            foaf:lastName ?last .
                BIND( CONCAT(CONCAT(?first, " "), ?last) AS ?name )
            }
        }
    ''', initNs={'foaf': FOAF})
    print("Known people:")
    current_person_uri = None
    current_person_names = []

    def search_for_person(person_names):
        # Search for the person in Github
        person_query_string_list = list(map(lambda x: f'{x}', person_names))
        person_query_string_list = sorted(person_query_string_list, key=len, reverse=True)[:5]
        person_query = " OR ".join(person_query_string_list)
        if(len(person_query) > max_query_length):
            person_query = person_query[:max_query_length - 1]
        print(person_query)
        user_results_json_filename = 'data/github/' + hashlib.md5(person_query.encode()).hexdigest() + '.json'
        user_results = None
        if not os.path.exists(user_results_json_filename):
            user_results = g.search_users(person_query)
            print(f'Found {user_results.totalCount} users')
            print(user_results)
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
            print(user)
            # print(user.raw_data)
            # print(user.get_json())
            # print(user.get_json()['login'])
            # print(user.get_json()['name'])

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
                    search_for_person(current_person_names)
                current_person_uri = row.person
                current_person_names = []
                current_person_names.append(row.name)
            else:
                current_person_names.append(row.name)
        except StopIteration:
            if(len(current_person_names) > 0):
                search_for_person(current_person_names)
            break





#######################################################

# Load all RDF files in data/rdf and display data


# process_paper_with_code()
# print('Paper with code processed')
# process_hal()
# print('HAL processed')
process_github()
print('Github processed')

exit()