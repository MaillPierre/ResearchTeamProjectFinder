from rdflib import DCMITYPE, Graph, URIRef, Literal, BNode
from rdflib.plugins.sparql import prepareQuery
from rdflib.namespace import RDF, RDFS, OWL, DCTERMS, DCAT, FOAF
from rdflib.query import Result, ResultRow
from util.utilities import create_uri
from kg.CONSTANTS import pav_importedFrom, pav_lastRefreshedOn, pav_retrievedFrom, local_Source, HAL_AUTHOR, local_HalOrganization, local_IdHal, adms_identifier, local_GScholar, local_Orcid, local_IdRef, HAL, ORCID, datacite_OrganizationIdentifier, local_RepositoryId, roh_platform
import requests
import json
import datetime
import hashlib
import os
import logging
import xml.etree.ElementTree as ET

g_h_person = Graph()
g_h_person_filename = 'data/rdf/person/hal_Person.ttl'
g_h_organization = Graph()
g_h_organization_filename = 'data/rdf/organization/hal_Organization.ttl'
g_h_software = Graph()
g_h_software_filename = 'data/rdf/software/hal_Software.ttl'
g_h_article = Graph()
g_h_article_filename = 'data/rdf/article/hal_Article.ttl'

# Uses the HAL api to download data about authors, structures and papers
def process_hal():

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
        g_h_person.add((author_api_uri, RDF.type, local_Source))
        g_h_person.add((author_api_uri, pav_lastRefreshedOn, Literal(datetime.datetime.now().isoformat())))
        logging.info(f'Processing {num_authors} authors')
        while page * page_size < num_authors:
            logging.info(f'Processing authors {page * page_size} to {min((page + 1) * page_size, num_authors)} of {num_authors}')
            # Add to the graph the info relevant to the authors
            author_query_literal = Literal(author_api_url)
            for author in author_api_result['response']['docs']:
                if(idhal_field in author and author[idhal_field] != None):
                    author_uri = create_uri(HAL_AUTHOR + author[idhal_field])
                    g_h_person.add((author_uri, RDF.type, FOAF.Person))
                    g_h_person.add((author_uri, pav_retrievedFrom, author_query_literal))
                    g_h_person.add((author_uri, pav_retrievedFrom, author_api_uri))
                    if(fullname_field in author and author[fullname_field] != None):
                        g_h_person.add((author_uri, FOAF.name, Literal(author[fullname_field])))
                    if(firstname_field in author and author[firstname_field] != None):
                        g_h_person.add((author_uri, FOAF.firstName, Literal(author[firstname_field])))
                    if(lastname_field in author and author[lastname_field] != None):
                        g_h_person.add((author_uri, FOAF.lastName, Literal(author[lastname_field])))
                    if(fullname_sci_field in author and author[fullname_sci_field] != None):
                        g_h_person.add((author_uri, DCTERMS.alternative, Literal(author[fullname_sci_field])))
                    if(orcid_field in author and author[orcid_field] != None):
                        for orcid in author[orcid_field]:
                            orcid_uri = create_uri(ORCID + orcid)
                            g_h_person.add((author_uri, adms_identifier, orcid_uri))
                            g_h_person.add((orcid_uri, RDF.type, local_Orcid))
                            g_h_person.add((orcid_uri, pav_retrievedFrom, author_query_literal))
                            g_h_person.add((orcid_uri, pav_retrievedFrom, author_api_uri))
                    if(gscholar_field in author and author[gscholar_field] != None):
                        for gscholar in author[gscholar_field]:
                            gscholar_uri = create_uri(gscholar)
                            g_h_person.add((author_uri, adms_identifier, gscholar_uri))
                            g_h_person.add((gscholar_uri, RDF.type, local_GScholar))
                            g_h_person.add((gscholar_uri, pav_retrievedFrom, author_query_literal))
                            g_h_person.add((gscholar_uri, pav_retrievedFrom, author_api_uri))
                    if(idref_field in author and author[idref_field] != None):
                        for idref in author[idref_field]:
                            idref_uri = create_uri(idref)
                            g_h_person.add((author_uri, adms_identifier, idref_uri))
                            g_h_person.add((idref_uri, RDF.type, local_IdRef))
                            g_h_person.add((idref_uri, pav_retrievedFrom, author_query_literal))
                            g_h_person.add((idref_uri, pav_retrievedFrom, author_api_uri))
                    logging.info(f'Added author {author_uri}')
            page += 1

            g_h_person.add((author_api_uri, pav_importedFrom, Literal(author_api_url)))
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
        g_h_software.add((software_api_uri, RDF.type, local_Source))
        g_h_software.add((software_api_uri, pav_lastRefreshedOn, Literal(datetime.datetime.now().isoformat())))
        logging.info(f'Processing {num_softwares} softwares')
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
                software_uri = create_uri(HAL + software[halid_field])
                logging.info(f'Adding software {software_uri}')
                g_h_software.add((software_uri, RDF.type, DCMITYPE.Software))
                g_h_software.add((software_uri, pav_retrievedFrom, software_api_uri))
                g_h_software.add((software_uri, pav_retrievedFrom, software_query_literal))
                # Title
                if(title_field in software and software[title_field] != None and len(software[title_field]) > 0):
                    for title in software[title_field]:
                        g_h_software.add((software_uri, DCTERMS.title, Literal(title)))
                # Abstract
                if(abstract_field in software and software[abstract_field] != None and len(software[abstract_field]) > 0):
                    for abstract in software[abstract_field]:
                        g_h_software.add((software_uri, DCTERMS.abstract, Literal(abstract)))
                # Keywords
                if(keyword_field in software and software[keyword_field] != None and len(software[keyword_field]) > 0):
                    for keyword in software[keyword_field]:
                        g_h_software.add((software_uri, DCTERMS.subject, Literal(keyword)))
                # Author Fullname
                if(author_fullname_field in software and software[author_fullname_field] != None and len(software[author_fullname_field]) > 0):
                    for fullname in software[author_fullname_field]:
                        fullname_literal = Literal(fullname)
                        author_bnode = BNode()
                        g_h_software.add((author_bnode, RDF.type, FOAF.Person))
                        g_h_software.add((author_bnode, FOAF.name, fullname_literal))
                        g_h_software.add((author_bnode, pav_retrievedFrom, software_query_literal))
                        g_h_software.add((author_bnode, pav_retrievedFrom, software_api_uri))
                        g_h_software.add((software_uri, DCTERMS.creator, author_bnode))
                # Author IdHal
                if(author_idhal_field in software and software[author_idhal_field] != None and len(software[author_idhal_field]) > 0):
                    for idhal in software[author_idhal_field]:
                        idhal_uri = create_uri(HAL_AUTHOR + idhal)
                        author_bnode = BNode()
                        g_h_software.add((author_bnode, RDF.type, FOAF.Person))
                        g_h_software.add((author_bnode, adms_identifier, idhal_uri))
                        g_h_software.add((author_bnode, pav_retrievedFrom, software_query_literal))
                        g_h_software.add((author_bnode, pav_retrievedFrom, software_api_uri))
                        g_h_person.add((idhal_uri, RDF.type, local_IdHal))
                        g_h_person.add((idhal_uri, pav_retrievedFrom, software_query_literal))
                        g_h_person.add((idhal_uri, pav_retrievedFrom, software_api_uri))
                        g_h_software.add((software_uri, DCTERMS.creator, author_bnode))
                # Author ORCID
                if(author_orcid_field in software and software[author_orcid_field] != None and len(software[author_orcid_field]) > 0):
                    for orcid in software[author_orcid_field]:
                        orcid_uri = create_uri(ORCID + orcid)
                        author_bnode = BNode()
                        g_h_software.add((author_bnode, RDF.type, FOAF.Person))
                        g_h_software.add((author_bnode, adms_identifier, orcid_uri))
                        g_h_person.add((orcid_uri, RDF.type, local_Orcid))
                        g_h_software.add((author_bnode, pav_retrievedFrom, software_query_literal))
                        g_h_software.add((author_bnode, pav_retrievedFrom, software_api_uri))
                        g_h_person.add((orcid_uri, pav_retrievedFrom, software_query_literal))
                        g_h_person.add((orcid_uri, pav_retrievedFrom, software_api_uri))
                        g_h_software.add((software_uri, DCTERMS.creator, author_bnode))
                # Author Google Scholar
                if(author_gscholar_field in software and software[author_gscholar_field] != None and len(software[author_gscholar_field]) > 0):
                    for gscholar in software[author_gscholar_field]:
                        gscholar_uri = create_uri( gscholar)
                        author_bnode = BNode()
                        g_h_software.add((author_bnode, RDF.type, FOAF.Person))
                        g_h_software.add((author_bnode, adms_identifier, gscholar_uri))
                        g_h_person.add((gscholar_uri, RDF.type, local_GScholar))
                        g_h_software.add((author_bnode, pav_retrievedFrom, software_query_literal))
                        g_h_software.add((author_bnode, pav_retrievedFrom, software_api_uri))
                        g_h_person.add((gscholar_uri, pav_retrievedFrom, software_query_literal))
                        g_h_person.add((gscholar_uri, pav_retrievedFrom, software_api_uri))
                        g_h_software.add((software_uri, DCTERMS.creator, author_bnode))
                # Code repository
                if(code_repo_field in software and software[code_repo_field] != None and len(software[code_repo_field]) > 0):
                    for repo in software[code_repo_field]:
                        repo_uri = create_uri(repo)
                        g_h_software.add((repo_uri, RDF.type, local_RepositoryId))
                        g_h_software.add((repo_uri, pav_retrievedFrom, software_query_literal))
                        g_h_software.add((repo_uri, pav_retrievedFrom, software_api_uri))
                        g_h_software.add((software_uri, DCTERMS.source, repo_uri))
                # Programming language
                if(programming_language_field in software and software[programming_language_field] != None and len(software[programming_language_field]) > 0):
                    for language in software[programming_language_field]:
                        g_h_software.add((software_uri, DCTERMS.language, Literal(language)))
                # Platform
                if(platform_field in software and software[platform_field] != None and len(software[platform_field]) > 0):
                    for platform in software[platform_field]:
                        g_h_software.add((software_uri, roh_platform, Literal(platform)))
                # Modified date
                if(modified_date_field in software and software[modified_date_field] != None):
                    g_h_software.add((software_uri, DCTERMS.modified, Literal(software[modified_date_field])))
                # Released date
                if(released_date_field in software and software[released_date_field] != None and len(software[released_date_field]) > 0):
                    g_h_software.add((software_uri, DCTERMS.available, Literal(software[released_date_field])))
                # Publication date
                if(publication_date_field in software and software[publication_date_field] != None and len(software[publication_date_field]) > 0):
                    g_h_software.add((software_uri, DCTERMS.issued, Literal(software[publication_date_field])))
                # Structure ROR
                if(struct_ror_field in software and software[struct_ror_field] != None and len(software[struct_ror_field]) > 0):
                    for ror in software[struct_ror_field]:
                        ror_uri = create_uri(ror)
                        org_bnode = BNode()
                        g_h_software.add((org_bnode, RDF.type, FOAF.Organization))
                        g_h_software.add((org_bnode, pav_retrievedFrom, software_query_literal))
                        g_h_software.add((org_bnode, pav_retrievedFrom, software_api_uri))
                        g_h_software.add((software_uri, DCTERMS.publisher, org_bnode))
                        g_h_software.add((org_bnode, adms_identifier, ror_uri))
                        g_h_organization.add((ror_uri, RDF.type, datacite_OrganizationIdentifier))
                        g_h_organization.add((ror_uri, pav_retrievedFrom, software_query_literal))
                        g_h_organization.add((ror_uri, pav_retrievedFrom, software_api_uri))
                # Structure IdRef
                if(struct_idref_field in software and software[struct_idref_field] != None and len(software[struct_idref_field]) > 0):
                    for idref in software[struct_idref_field]:
                        idref_uri = create_uri(idref)
                        org_bnode = BNode()
                        g_h_software.add((org_bnode, RDF.type, FOAF.Organization))
                        g_h_software.add((org_bnode, pav_retrievedFrom, software_query_literal))
                        g_h_software.add((org_bnode, pav_retrievedFrom, software_api_uri))
                        g_h_software.add((software_uri, DCTERMS.publisher, org_bnode))
                        g_h_software.add((org_bnode, adms_identifier, idref_uri))
                        g_h_organization.add((idref_uri, RDF.type, datacite_OrganizationIdentifier))
                        g_h_organization.add((idref_uri, pav_retrievedFrom, software_query_literal))
                        g_h_organization.add((idref_uri, pav_retrievedFrom, software_api_uri))
                # Lab Structure ROR
                if(lab_struct_ror_field in software and software[lab_struct_ror_field] != None and len(software[lab_struct_ror_field]) > 0):
                    for lab_ror in software[lab_struct_ror_field]:
                        lab_ror_uri = create_uri(lab_ror)
                        org_bnode = BNode()
                        g_h_software.add((org_bnode, RDF.type, FOAF.Organization))
                        g_h_software.add((org_bnode, pav_retrievedFrom, software_query_literal))
                        g_h_software.add((org_bnode, pav_retrievedFrom, software_api_uri))
                        g_h_software.add((software_uri, DCTERMS.publisher, org_bnode))
                        g_h_software.add((org_bnode, adms_identifier, lab_ror_uri))
                        g_h_organization.add((lab_ror_uri, RDF.type, datacite_OrganizationIdentifier))
                        g_h_organization.add((lab_ror_uri, pav_retrievedFrom, software_query_literal))
                        g_h_organization.add((lab_ror_uri, pav_retrievedFrom, software_api_uri))
                # Lab Structure IdRef
                if(lab_struct_idref_field in software and software[lab_struct_idref_field] != None and len(software[lab_struct_idref_field]) > 0):
                    for lab_idref in software[lab_struct_idref_field]:
                        lab_idref_uri = create_uri(lab_idref)
                        org_bnode = BNode()
                        g_h_software.add((org_bnode, RDF.type, FOAF.Organization))
                        g_h_software.add((org_bnode, pav_retrievedFrom, software_query_literal))
                        g_h_software.add((org_bnode, pav_retrievedFrom, software_api_uri))
                        g_h_software.add((software_uri, DCTERMS.publisher, org_bnode))
                        g_h_software.add((org_bnode, adms_identifier, lab_idref_uri))
                        g_h_organization.add((lab_idref_uri, RDF.type, datacite_OrganizationIdentifier))
                        g_h_organization.add((lab_idref_uri, pav_retrievedFrom, software_query_literal))
                        g_h_organization.add((lab_idref_uri, pav_retrievedFrom, software_api_uri))
                # Open Access
                if(oa_field in software and software[oa_field] != None and software[oa_field] == True):
                    g_h_software.add((software_uri, DCTERMS.rights, Literal("Open Access")))
                # XML
                # Attempte to extract the license from the XML
                if(xml_field in software and software[xml_field] != None):
                    xml_string = software[xml_field]
                    xml_string = xml_string.replace('\\"', '"')
                    xml = ET.fromstring(xml_string)
                    xml_stmts = xml.findall(".//TEI/biblFull/publicationStmt/availability/licence")
                    for child in xml_stmts:
                        if(child.tag == "licence"):
                            license_uri = create_uri(child.get("target"))
                            g_h_software.add((software_uri, DCTERMS.license, license_uri))
                            g_h_software.add((license_uri, RDFS.label, Literal(child.text)))
                logging.info(f'Added software {software[title_field]}')
            page += 1

    def process_hal_organization():
        # load existing organisations from the graph in rdf/organization
        logging.info("Loading existing organisations from the graph")
        for file in os.listdir('data/rdf/organization/'):
            if file.endswith('.ttl'):
                g_h_organization.parse('data/rdf/organization/' + file, format='turtle')
        logging.info(f'Loaded {len(g_h_organization)} triples about organizations from the graph')

        hal_sparql_endpoint = "http://sparql.archives-ouvertes.fr/sparql"
        hal_sparql_endpoint_uri = create_uri(hal_sparql_endpoint)
        hal_org_sparql_query_string = f'''
        PREFIX dct: <http://purl.org/dc/terms/>
        PREFIX dc: <http://purl.org/dc/elements/1.1/>
        PREFIX owl: <http://www.w3.org/2002/07/owl#>
        PREFIX org: <http://www.w3.org/ns/org#>
        PREFIX skos: <http://www.w3.org/2004/02/skos/core#>
        PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
        PREFIX foaf: <http://xmlns.com/foaf/0.1/>
        PREFIX halschema: <http://data.archives-ouvertes.fr/schema/>

        SELECT DISTINCT ?org ?label ?acronym ?id ?superOrg ?superOrgId ?superOrgLabel {{
            SERVICE <{hal_sparql_endpoint}> {{
                ?org a org:Organization ;
                    skos:prefLabel ?label ;
                    owl:sameAs ?id .
                OPTIONAL {{
                    ?org org:unitOf ?superOrg .
                    ?superOrg owl:sameAs ?superOrgId ;
                        skos:prefLabel ?superOrgLabel .
                }}
                OPTIONAL {{
                    ?org skos:altLabel ?acronym .
                }}
            }}
        }}'''

        # Check if the result of the query is not already in the cache
        hal_sparql_query_result_filename = f"data/hal/organization/{hashlib.md5(hal_org_sparql_query_string.encode()).hexdigest()}.json"
        if(os.path.exists(hal_sparql_query_result_filename)):
            hal_sparql_query_file = open(hal_sparql_query_result_filename, 'r')
            hal_org_results = Result.parse(hal_sparql_query_file, format='json')
            hal_sparql_query_file.close()
        else:
            # Send GET request to the HAL API
            hal_sparql_query = prepareQuery(hal_org_sparql_query_string)
            logging.info(f"Sending query to HAL SPARQL endpoint: {hal_org_sparql_query_string}")
            hal_org_results = g_h_organization.query(hal_sparql_query)
            logging.info(f"Query result: {len(hal_org_results)} results")
            hal_sparql_query_file = open(hal_sparql_query_result_filename, 'w')
            hal_org_results.serialize(hal_sparql_query_file, format='json')
            hal_sparql_query_file.close()

        # Send GET request to the HAL API
        for binding in hal_org_results:
            if isinstance(binding, ResultRow):
                binding = binding.asdict()
                org_uri = create_uri(str(binding['org']))
                org_id_uri = create_uri(str(binding['id']))
                if( (org_uri, RDF.type, local_HalOrganization) not in g_h_organization):
                    g_h_organization.add((org_uri, RDF.type, local_HalOrganization))
                    g_h_organization.add((org_uri, adms_identifier, org_id_uri))
                    g_h_organization.add((org_id_uri, RDF.type, datacite_OrganizationIdentifier))
                    g_h_organization.add((org_uri, pav_retrievedFrom, Literal(hal_org_sparql_query_string)))
                    g_h_organization.add((org_uri, pav_retrievedFrom, hal_sparql_endpoint_uri))
                    g_h_organization.add((org_uri, RDFS.label, Literal(binding['label'])))
                    if(binding['acronym'] != None):
                        g_h_organization.add((org_uri, FOAF.name, Literal(binding['acronym'])))
                    if(binding['superOrg'] != None):
                        super_org_uri = create_uri(str(binding['superOrg']))
                        super_org_id_uri = create_uri(str(binding['superOrgId']))
                        super_org_label = Literal(binding['superOrgLabel'])
                        g_h_organization.add((org_uri, DCTERMS.relation, super_org_uri))
                        g_h_organization.add((super_org_uri, RDF.type, local_HalOrganization))
                        g_h_organization.add((super_org_uri, pav_retrievedFrom, Literal(hal_org_sparql_query_string)))
                        g_h_organization.add((super_org_uri, pav_retrievedFrom, hal_sparql_endpoint_uri))
                        g_h_organization.add((super_org_uri, adms_identifier, super_org_id_uri))
                        g_h_organization.add((super_org_id_uri, RDF.type, datacite_OrganizationIdentifier))
                        g_h_organization.add((super_org_uri, RDFS.label, super_org_label))
        # writing Hal roganisation to file
        logging.info(f'Writing organization graph to file {len(g_h_organization)} triples')
        g_h_organization.serialize(destination=g_h_organization_filename, format='turtle')
        logging.info('Graph written to file')

                

    process_hal_authors()
    process_hal_software()
    process_hal_organization()

    write_hal_graph()
    
def write_hal_graph():
    # writing g to a file
    if len(g_h_software) > 0:
        logging.info(f'Writing software graph to file {len(g_h_software)} triples')
        g_h_software.serialize(destination=g_h_software_filename, format='turtle')
    g_h_software.close()
    if len(g_h_person) > 0:
        logging.info(f'Writing person graph to file {len(g_h_person)} triples')
        g_h_person.serialize(destination=g_h_person_filename, format='turtle')
    g_h_person.close()
    if len(g_h_organization) > 0:
        logging.info(f'Writing organization graph to file {len(g_h_organization)} triples')
        g_h_organization.serialize(destination=g_h_organization_filename, format='turtle')
    g_h_organization.close()
    if len(g_h_article) > 0:
        logging.info(f'Writing article graph to file {len(g_h_article)} triples')
        g_h_article.serialize(destination=g_h_article_filename, format='turtle')
    g_h_article.close()
    if len(g_h_software) > 0 or len(g_h_person) > 0 or len(g_h_organization) > 0 or len(g_h_article) > 0:
        logging.info('Hal graphs written to file')
