from rdflib import DCMITYPE, Graph, URIRef, Literal, BNode
from rdflib.plugins.sparql import prepareQuery
from rdflib.namespace import RDF, RDFS, OWL, DCTERMS, DCAT, FOAF
from rdflib.query import Result, ResultRow
from kg.knowledge import Paper, UniqueIdentifier, Organization, Person, Software, Source
from util.utilities import api_cached_query, create_uri, sparql_cached
from kg.CONSTANTS import DOI, GSCHOLAR, HAL_AUTHOR, HAL, ORCID
import os
import logging
import configparser
import xml.etree.ElementTree as ET

logging.basicConfig(filename='app.log', level=logging.DEBUG)

g_h_person = Graph()
g_h_person_filename = 'data/rdf/person/hal_Person.ttl'
g_h_organization = Graph()
g_h_organization_filename = 'data/rdf/organization/hal_Organization.ttl'
g_h_software = Graph()
g_h_software_filename = 'data/rdf/software/hal_Software.ttl'
g_h_article = Graph()
g_h_article_filename = 'data/rdf/article/hal_Article.ttl'

hal_sparql_endpoint = "http://sparql.archives-ouvertes.fr/sparql"
hal_sparql_source_obj = Source(URIRef(hal_sparql_endpoint))

# config = configparser.ConfigParser()
# page_size = config['HAL'].getint('page_size')
# if page_size is None:
page_size = 100

abstract_field = "abstract_s"
all_code_domain = 'en_domainAllCodeLabel_fs'
author_fullname_field = "authFullName_s"
# author_gscholar_field = "authGoogle ScholarIdExt_s"
author_idhal_field = "authIdHal_s"
author_orcid_field = "authORCIDIdExt_s"
author_organism_field = "authOrganism_s"
code_repo_field = "softCodeRepository_s"
docid_field = "docid"
doctype_field = "docType_s"
doiId_field = "doiId_s"
keyword_field = 'keyword_s'
firstname_field = "firstName_s"
fullname_field = "fullName_s"
fullname_sci_field = "fullName_sci"
gscholar_field = "google scholarId_s"
halid_field = "halId_s"
idhal_field = "idHal_s"
idref_field = 'idrefId_s'
keyword_field = "keyword_s"
label_field = "label_s"
lab_struct_ror_field = "labStructRorIdExt_s"
lab_struct_idref_field = "labStructIdrefIdExtUrl_s"
lastname_field = "lastName_s"
modified_date_field = "modifiedDate_tdate"
orcid_field = "orcidId_s"
oa_field = "openAccess_bool"
platform_field = "softPlatform_s"
programming_language_field = "softProgrammingLanguage_s"
publication_date_field = "publicationDate_tdate"
uri_field = "uri_s"
released_date_field = "releasedDate_tdate"
struct_ror_field = "structRorIdExt_s"
struct_idref_field = "structIdrefIdExtUrl_s"
title_field = "title_s"
xml_field = "label_xml"

def hal_expand_article_ref(article_obj: Paper) -> Paper:
    logging.info(f"HAL expanding {article_obj.uri}")
    paper_api_query = "*"
    # If paper has a DOI, then look for it by DOI
    if article_obj.doi != None:
        article_doi = article_obj.doi
        if isinstance(article_obj.doi, URIRef):
            article_doi = article_obj.doi.replace(f"{DOI}", "")
        paper_api_query = f"{doiId_field}:{article_doi}"
    elif article_obj.title != None:
    # If paper has no DOI, the look for it by name
        paper_api_query = f"{title_field}:{article_obj.title}"
    else:
        return article_obj
    page = 0
    paper_api_fields = f"{halid_field},{docid_field},{label_field},{uri_field},{abstract_field},{keyword_field},{author_fullname_field},{author_idhal_field},{author_orcid_field},{doiId_field},{author_organism_field},{publication_date_field},{struct_ror_field},{struct_idref_field},{lab_struct_ror_field},{lab_struct_idref_field}"
    # paper_api_filter = f"{doctype_field}:COM,ART,THESE,MEM,REPORT"
    paper_api_filter = "*:*"
    paper_api_sort = f"{docid_field}+asc"
    paper_api_url = f"https://api.archives-ouvertes.fr/search/?wt=json&q={paper_api_query}&fq={paper_api_filter}&fl={paper_api_fields}&rows={page_size}&start={page * page_size}&sort={paper_api_sort}" # type: ignore
        
    paper_api_uri = create_uri(f"https://api.archives-ouvertes.fr/search/?fq={paper_api_filter}")
    paper_api_source_obj = Source(paper_api_uri) # type: ignore
    # Send GET request to the HAL API
    paper_api_result = api_cached_query(api_url=paper_api_url, api_query_file_prefix="data/hal/paper/")
    num_papers = paper_api_result['response']['numFound']

    logging.info(f"{num_papers} for {paper_api_url}")

    while page * page_size < num_papers: # type: ignore
        logging.info(paper_api_url)

        for paper_json in paper_api_result['response']['docs']:
            if uri_field in paper_json:
                paper_uri = create_uri(uri_field)
                article_obj.add_identifier(identifier=UniqueIdentifier(uri=paper_uri,source=paper_api_source_obj))
            if halid_field in paper_json:
                paper_halid_uri = create_uri(HAL + paper_json[halid_field])
                article_obj.add_identifier(identifier=UniqueIdentifier(uri=paper_halid_uri,source=paper_api_source_obj))
            if label_field in paper_json:
                article_obj.set_label(paper_json[label_field])
            if abstract_field in paper_json:
                article_obj.set_abstract(paper_json[abstract_field])
            if keyword_field in paper_json:
                for keyword_str in paper_json[keyword_field]:
                    article_obj.add_keyword(keyword_str)
            # if author_gscholar_field in paper_json:
            #     for author_gscholar in paper_json[author_gscholar_field]:
            #         author_gscholar_uri = URIRef(GSCHOLAR + author_gscholar)
            #         author_obj = Person(uri=author_gscholar_uri, source=paper_api_source_obj)
            #         author_obj.add_identifier(UniqueIdentifier(uri=author_gscholar_uri,source=paper_api_source_obj))
            #         article_obj.add_author(author_obj)
            if author_idhal_field in paper_json:
                for author_idhal in paper_json[author_idhal_field]:
                    author_idhal_uri = create_uri(HAL_AUTHOR + author_idhal)
                    author_obj = Person(uri=author_idhal_uri, source=paper_api_source_obj)
                    author_obj.add_identifier(UniqueIdentifier(uri=author_idhal_uri,source=paper_api_source_obj))
                    article_obj.add_author(author_obj)
            if author_orcid_field in paper_json:
                for author_orcid in paper_json[author_orcid_field]:
                    author_orcid_uri = create_uri(ORCID + author_orcid)
                    author_obj = Person(uri=author_orcid_uri, source=paper_api_source_obj)
                    author_obj.add_identifier(UniqueIdentifier(uri=author_orcid_uri,source=paper_api_source_obj))
                    article_obj.add_author(author_obj)
            if doiId_field in paper_json:
                article_obj.add_identifier(UniqueIdentifier(uri=create_uri(DOI + paper_json[doiId_field]), source=paper_api_source_obj))
            if author_organism_field in paper_json:
                for author_organism in paper_json[author_organism_field]:
                    org_obj = Organization(source=paper_api_source_obj)
                    org_obj.set_label(author_organism)
                    article_obj.add_related(org_obj)
            if publication_date_field in paper_json:
                article_obj.set_publication_date(paper_json[publication_date_field])
            if struct_ror_field in paper_json:
                for author_organism in paper_json[struct_ror_field]:
                    org_obj = Organization(source=paper_api_source_obj)
                    org_obj.set_uri(create_uri(author_organism))
                    article_obj.add_related(org_obj)
            if struct_idref_field in paper_json:
                for author_organism in paper_json[struct_idref_field]:
                    org_obj = Organization(source=paper_api_source_obj)
                    org_obj.set_uri(create_uri(author_organism))
                    article_obj.add_related(org_obj)
        page += 1
        paper_api_url = f"https://api.archives-ouvertes.fr/search/?wt=json&q={paper_api_query}&fq={paper_api_filter}&fl={paper_api_fields}&rows={page_size}&start={page * page_size}&sort={paper_api_sort}" # type: ignore

        paper_api_result = api_cached_query(api_query_file_prefix="data/hal/software/", api_url=paper_api_url)
    return article_obj

def hal_json_author_to_person(hal_json_author, hal_json_query_url: str, hal_api_source: Source) -> Person | None:
    author_query_literal = Literal(hal_json_query_url)
    if(idhal_field in hal_json_author and hal_json_author[idhal_field] != None):
        author_uri = create_uri(HAL_AUTHOR + hal_json_author[idhal_field])
        author_obj = Person(hal_api_source, author_uri)
        author_obj.set_retrieved_from(author_query_literal)
        if(fullname_field in hal_json_author and hal_json_author[fullname_field] != None):
            author_obj.set_label(hal_json_author[fullname_field])
        if(firstname_field in hal_json_author and hal_json_author[firstname_field] != None):
            author_obj.set_first_name(hal_json_author[firstname_field])
        if(lastname_field in hal_json_author and hal_json_author[lastname_field] != None):
            author_obj.set_last_name(hal_json_author[lastname_field])
        if(fullname_sci_field in hal_json_author and hal_json_author[fullname_sci_field] != None):
            author_obj.add_alternative(hal_json_author[fullname_sci_field])
        if(orcid_field in hal_json_author and hal_json_author[orcid_field] != None):
            for orcid in hal_json_author[orcid_field]:
                orcid_uri = create_uri(ORCID + orcid)
                orcid_id = UniqueIdentifier(hal_api_source, orcid_uri)
                orcid_id.set_retrieved_from(author_query_literal)
                author_obj.add_identifier(orcid_id)
        if(gscholar_field in hal_json_author and hal_json_author[gscholar_field] != None):
            for gscholar in hal_json_author[gscholar_field]:
                gscholar_uri = create_uri(gscholar)
                gscholar_id = UniqueIdentifier(hal_api_source, gscholar_uri)
                gscholar_id.set_retrieved_from(author_query_literal)
                author_obj.add_identifier(gscholar_id)
        if(idref_field in hal_json_author and hal_json_author[idref_field] != None):
            for idref in hal_json_author[idref_field]:
                idref_uri = create_uri(idref)
                idref_id = UniqueIdentifier(hal_api_source, idref_uri)
                idref_id.set_retrieved_from(author_query_literal)
                author_obj.add_identifier(idref_id)
        return author_obj
    
def hal_software_to_software_obj(hal_sofware_json, hal_api_url: str, source: Source) -> Software:
    software_query_literal = Literal(hal_api_url)
    software_uri = create_uri(HAL + hal_sofware_json[halid_field])
    software_obj = Software(source, software_uri)
    software_obj.set_retrieved_from(Literal(hal_api_url))
    # Title
    if(title_field in hal_sofware_json and hal_sofware_json[title_field] != None and len(hal_sofware_json[title_field]) > 0):
        for title in hal_sofware_json[title_field]:
            software_obj.set_label(title)
        # Abstract
        if(abstract_field in hal_sofware_json and hal_sofware_json[abstract_field] != None and len(hal_sofware_json[abstract_field]) > 0):
            for abstract in hal_sofware_json[abstract_field]:
                software_obj.set_abstract(abstract)
        # Keywords
        if(keyword_field in hal_sofware_json and hal_sofware_json[keyword_field] != None and len(hal_sofware_json[keyword_field]) > 0):
            for keyword in hal_sofware_json[keyword_field]:
                software_obj.add_keyword(keyword)
        # Author Fullname
        if(author_fullname_field in hal_sofware_json and hal_sofware_json[author_fullname_field] != None and len(hal_sofware_json[author_fullname_field]) > 0):
            for fullname in hal_sofware_json[author_fullname_field]:
                fullname_literal = Literal(fullname)
                author_bnode = BNode()
                author_obj = Person(source, author_bnode)
                author_obj.set_label(fullname_literal)
                author_obj.set_retrieved_from(software_query_literal)
                software_obj.add_creator(author_obj)
        # Author IdHal
        if(author_idhal_field in hal_sofware_json and hal_sofware_json[author_idhal_field] != None and len(hal_sofware_json[author_idhal_field]) > 0):
            for idhal in hal_sofware_json[author_idhal_field]:
                idhal_uri = create_uri(HAL_AUTHOR + idhal)
                author_bnode = BNode()
                author_obj = Person(source, author_bnode)
                idhal_obj = UniqueIdentifier(source, idhal_uri)
                idhal_obj.set_retrieved_from(software_query_literal)
                author_obj.set_retrieved_from(software_query_literal)
                author_obj.add_identifier(idhal_obj)
                software_obj.add_creator(author_obj)
        # Author ORCID
        if(author_orcid_field in hal_sofware_json and hal_sofware_json[author_orcid_field] != None and len(hal_sofware_json[author_orcid_field]) > 0):
            for orcid in hal_sofware_json[author_orcid_field]:
                orcid_uri = create_uri(ORCID + orcid)
                author_bnode = BNode()
                author_obj = Person(source, author_bnode)
                orcid_obj = UniqueIdentifier(source, orcid_uri)
                orcid_obj.set_retrieved_from(software_query_literal)
                author_obj.set_retrieved_from(software_query_literal)
                author_obj.add_identifier(orcid_obj)
                software_obj.add_creator(author_obj)
        # # Author Google Scholar
        # if(author_gscholar_field in hal_sofware_json and hal_sofware_json[author_gscholar_field] != None and len(hal_sofware_json[author_gscholar_field]) > 0):
        #     for gscholar in hal_sofware_json[author_gscholar_field]:
        #         gscholar_uri = create_uri( gscholar)
        #         author_bnode = BNode()
        #         author_obj = Person(source, author_bnode)
        #         gscholar_obj = UniqueIdentifier(source, gscholar_uri)
        #         gscholar_obj.set_retrieved_from(software_query_literal)
        #         author_obj.set_retrieved_from(software_query_literal)
        #         author_obj.add_identifier(gscholar_obj)
        #         software_obj.add_creator(author_obj)
        # Code repository
        if(code_repo_field in hal_sofware_json and hal_sofware_json[code_repo_field] != None and len(hal_sofware_json[code_repo_field]) > 0):
            for repo in hal_sofware_json[code_repo_field]:
                software_obj.add_repository(repo)
        # Programming language
        if(programming_language_field in hal_sofware_json and hal_sofware_json[programming_language_field] != None and len(hal_sofware_json[programming_language_field]) > 0):
            for language in hal_sofware_json[programming_language_field]:
                software_obj.add_language(language)
        # Platform
        if(platform_field in hal_sofware_json and hal_sofware_json[platform_field] != None and len(hal_sofware_json[platform_field]) > 0):
            for platform in hal_sofware_json[platform_field]:
                software_obj.add_platform(platform)
        # Modified date
        if(modified_date_field in hal_sofware_json and hal_sofware_json[modified_date_field] != None):
            software_obj.set_modified(hal_sofware_json[modified_date_field])
        # Released date
        if(released_date_field in hal_sofware_json and hal_sofware_json[released_date_field] != None and len(hal_sofware_json[released_date_field]) > 0):
            software_obj.add_available_at(hal_sofware_json[released_date_field])
        # Publication date
        if(publication_date_field in hal_sofware_json and hal_sofware_json[publication_date_field] != None and len(hal_sofware_json[publication_date_field]) > 0):
            software_obj.set_publication(hal_sofware_json[publication_date_field])
        # Structure ROR
        if(struct_ror_field in hal_sofware_json and hal_sofware_json[struct_ror_field] != None and len(hal_sofware_json[struct_ror_field]) > 0):
            for ror in hal_sofware_json[struct_ror_field]:
                ror_uri = create_uri(ror)
                org_obj = Organization(source)
                org_ror_id_obj = UniqueIdentifier(source, ror_uri)
                org_ror_id_obj.set_retrieved_from(software_query_literal)
                org_obj.set_retrieved_from(software_query_literal)
                org_obj.add_identifier(org_ror_id_obj)
                software_obj.add_creator(org_obj)
        # Structure IdRef
        if(struct_idref_field in hal_sofware_json and hal_sofware_json[struct_idref_field] != None and len(hal_sofware_json[struct_idref_field]) > 0):
            for idref in hal_sofware_json[struct_idref_field]:
                idref_uri = create_uri(idref)
                org_obj = Organization(source)
                org_obj.set_retrieved_from(software_query_literal)
                org_idref_id_obj = UniqueIdentifier(source, idref_uri)
                org_idref_id_obj.set_retrieved_from(software_query_literal)
                org_obj.add_identifier(org_idref_id_obj)
                software_obj.add_creator(org_obj)
        # Lab Structure ROR
        if(lab_struct_ror_field in hal_sofware_json and hal_sofware_json[lab_struct_ror_field] != None and len(hal_sofware_json[lab_struct_ror_field]) > 0):
            for lab_ror in hal_sofware_json[lab_struct_ror_field]:
                lab_ror_uri = create_uri(lab_ror)
                org_obj = Organization(source)
                org_obj.set_retrieved_from(software_query_literal)
                org_ror_id_obj = UniqueIdentifier(source, lab_ror_uri)
                org_ror_id_obj.set_retrieved_from(software_query_literal)
                org_obj.add_identifier(org_ror_id_obj)
                software_obj.add_creator(org_obj)
        # Lab Structure IdRef
        if(lab_struct_idref_field in hal_sofware_json and hal_sofware_json[lab_struct_idref_field] != None and len(hal_sofware_json[lab_struct_idref_field]) > 0):
            for lab_idref in hal_sofware_json[lab_struct_idref_field]:
                lab_idref_uri = create_uri(lab_idref)
                org_obj = Organization(source)
                org_obj.set_retrieved_from(software_query_literal)
                org_idref_id_obj = UniqueIdentifier(source, lab_idref_uri)
                org_idref_id_obj.set_retrieved_from(software_query_literal)
                org_obj.add_identifier(org_idref_id_obj)
                software_obj.add_creator(org_obj)
        # Open Access
        if(oa_field in hal_sofware_json and hal_sofware_json[oa_field] != None and hal_sofware_json[oa_field] == True):
            software_obj.set_rights("Open Access")
    return software_obj

# Uses the HAL api to download data about authors, structures and papers
def process_hal():

    def process_hal_authors():
        ## Prepare the HAL API query for authors
        page = 0

        # Author API fields
        author_api_query = "*"
        author_api_fields = f"{firstname_field},{fullname_sci_field},{firstname_field},{lastname_field},{idhal_field},{orcid_field},{gscholar_field.replace(' ', '+')},{idref_field}"
        author_api_filter = f"{idhal_field}:[\"\" TO *]"
        author_api_sort = f"{fullname_field}+asc"
        author_api_endpoint = "http://api.archives-ouvertes.fr/ref/author/?wt=json"
        author_api_url = f'{author_api_endpoint}&fl={author_api_fields}&rows={page_size}&start={page * page_size}&sort={author_api_sort}&fq={author_api_filter}&q={author_api_query}' # type: ignore
        author_api_uri = URIRef("http://api.archives-ouvertes.fr/ref/author/")
        hal_author_api_source_obj = Source(author_api_uri)
        
        # Send GET request to the HAL API
        author_api_result = api_cached_query(api_url=author_api_url, api_query_file_prefix="data/hal/author/")
        num_authors = author_api_result['response']['numFound']

        # Add the source to the graph
        logging.info(f'Processing {num_authors} authors')
        while page * page_size < num_authors: # type: ignore
            logging.info(f'Processing authors {page * page_size} to {min((page + 1) * page_size, num_authors)} of {num_authors}') # type: ignore
            # Add to the graph the info relevant to the authors
            for author in author_api_result['response']['docs']:
                author_obj = hal_json_author_to_person(hal_json_author=author, hal_json_query_url=author_api_url, hal_api_source=hal_author_api_source_obj)
                if author_obj != None:
                    author_obj.to_rdf(g_h_person)
            page += 1

            author_api_url = f'{author_api_endpoint}&fl={author_api_fields}&rows={page_size}&start={page * page_size}&sort={author_api_sort}&fq={author_api_filter}&q={author_api_query}' # type: ignore
            
            author_api_result = api_cached_query(api_url=author_api_url, api_query_file_prefix="data/hal/author/")

    def process_hal_software():
        # Prepare the HAL API query for softwares
        page = 0

        software_api_query = "*"
        software_api_fields = f"{halid_field},{docid_field},{label_field},{uri_field},{title_field},{abstract_field},{keyword_field},{author_fullname_field},{author_idhal_field},{author_orcid_field},{code_repo_field},{programming_language_field},{platform_field},{modified_date_field},{released_date_field},{publication_date_field},{struct_ror_field},{struct_idref_field},{lab_struct_ror_field},{lab_struct_idref_field},{oa_field},{xml_field}"
        software_api_filter = f"{doctype_field}:SOFTWARE"
        software_api_sort = f"{docid_field}+asc"
        software_api_url = f"https://api.archives-ouvertes.fr/search/?wt=json&q={software_api_query}&fq={software_api_filter}&fl={software_api_fields}&rows={page_size}&start={page * page_size}&sort={software_api_sort}" # type: ignore

        software_api_uri = URIRef("https://api.archives-ouvertes.fr/search/?fq=docType_s:SOFTWARE")
        software_api_source_obj = Source(software_api_uri)

        # Send GET request to the HAL API
        software_api_result = api_cached_query(api_url=software_api_url, api_query_file_prefix="data/hal/software/")
        num_softwares = software_api_result['response']['numFound']

        # Add the source to the graph
        logging.info(f'Processing {num_softwares} softwares')
        while page * page_size < num_softwares: # type: ignore
            software_api_url = f"https://api.archives-ouvertes.fr/search/?wt=json&fq={software_api_filter}&fl={software_api_fields}&rows={page_size}&start={page * page_size}&sort={software_api_sort}&q={software_api_query}" # type: ignore

            software_api_result = api_cached_query(api_query_file_prefix="data/hal/software/", api_url=software_api_url)

            for software in software_api_result['response']['docs']:
                software_obj = hal_software_to_software_obj(hal_sofware_json=software, hal_api_url=software_api_url, source=software_api_source_obj)
                software_obj.to_rdf(g_h_software)
                logging.info(f'Added software {software_obj.label}')
            page += 1

    def process_hal_organization():
        # load existing organisations from the graph in rdf/organization
        logging.info("Loading existing organisations from the graph")
        for file in os.listdir('data/rdf/organization/'):
            if file.endswith('.ttl'):
                g_h_organization.parse('data/rdf/organization/' + file, format='turtle')
        logging.info(f'Loaded {len(g_h_organization)} triples about organizations from the graph')

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

        hal_org_results = sparql_cached(hal_org_sparql_query_string)


        # Send GET request to the HAL API
        for binding in hal_org_results:
            if isinstance(binding, ResultRow):
                binding = binding.asdict()
                org_uri = create_uri(str(binding['org']))
                org_id_uri = create_uri(str(binding['id']))
                org_obj = Organization(hal_sparql_source_obj)
                org_obj.set_uri(org_uri)
                org_id_obj = UniqueIdentifier(hal_sparql_source_obj, org_id_uri)
                if( (org_uri, RDF.type, HAL.Organization) not in g_h_organization):
                    org_obj.add_identifier(org_id_obj)
                    org_obj.set_retrieved_from(Literal(hal_org_sparql_query_string))
                    org_obj.set_label(Literal(binding['label']))
                    if('acronym' in binding and binding['acronym'] != None):
                        org_obj.add_alternative(Literal(binding['acronym']))
                    if('superOrg' in binding and binding['superOrg'] != None):
                        super_org_uri = create_uri(str(binding['superOrg']))
                        super_org_id_uri = create_uri(str(binding['superOrgId']))
                        super_org_label = Literal(binding['superOrgLabel'])
                        super_org_obj = Organization(hal_sparql_source_obj)
                        super_org_obj.set_uri(super_org_uri)
                        super_org_id_obj = UniqueIdentifier(hal_sparql_source_obj, super_org_id_uri)
                        super_org_obj.add_identifier(super_org_id_obj)
                        super_org_obj.set_label(super_org_label)
                        super_org_obj.set_retrieved_from(Literal(hal_org_sparql_query_string))
                        org_obj.add_related(super_org_obj)
                org_obj.to_rdf(g_h_organization)                

    process_hal_authors()
    process_hal_software()
    process_hal_organization()
    
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
