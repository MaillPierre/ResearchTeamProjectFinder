
from rdflib import URIRef, BNode, Namespace

# Namespaces
BIBO = Namespace('http://purl.org/ontology/bibo/')
DATACITE = Namespace('http://purl.org/spar/datacite/')
PAV = Namespace('http://purl.org/pav/')
ADMS = Namespace('http://www.w3.org/ns/adms#')
ROH = Namespace('http://w3id.org/roh#')
LOCAL = Namespace('http://ns.inria.fr/kg/works/')
ORCID = Namespace("https://orcid.org/")
HAL = Namespace("https://hal.science/")
HAL_AUTHOR = Namespace("https://shs.hal.science/search/index/q/*/authIdHal_s/")
ARXIV = Namespace("https://arxiv.org/abs/")
IDREF = Namespace("https://www.idref.fr/")
ROR = Namespace("https://ror.org/")
GSCHOLAR = Namespace("https://scholar.google.com/citations?user=")
CC = Namespace("http://creativecommons.org/ns#")

# classes
bibo_Document = BIBO.Document
bibo_doi = BIBO.doi
datacite_OrganizationIdentifier = DATACITE.OrganizationIdentifier
cc_License = CC.License
local_RepositoryId = LOCAL.RepositoryIdentifier
local_Source = LOCAL.Source
local_Orcid = LOCAL.ORCID
local_ArXiv = LOCAL.Arxiv
local_GScholar = LOCAL.GoogleScholar
local_IdRef = LOCAL.IdRef
local_IdHal = LOCAL.IdHal
local_HalOrganization = LOCAL.HalOrganization
local_GithubUser = LOCAL.GitHubUser
local_GithubRepo = LOCAL.GitHubRepository
local_GitlabUser = LOCAL.GitLabUser
local_GitlabRepo = LOCAL.GitLabRepository
local_repository_stars = LOCAL.repositoryStars
local_repository_forks = LOCAL.repositoryForks

# Properties
# pav:retrievedFrom
pav_retrievedFrom = PAV.retrievedFrom
pav_importedFrom = PAV.importedFrom
pav_lastRefreshedOn = PAV.lastRefreshedOn
pav_authoredOn = PAV.authoredOn
# roh:platform
roh_platform = ROH.platform
# adms:identifier
adms_identifier = ADMS.identifier