# ResearchTeamProjectFinder

The aim of this project is to create a tool able to use the different APIs available to find the public Git repositories of INRIA research teams. Further development will aim to extend this approach to all european research teams.

## Plan

- HAL
  - [ ] List people and organizations
  - [ ] List softwares declared
  - [ ] Scan papers abstract in search for repositories URLs

- CrossRef
  - [ ] Scan papers abstract in search for repositories URLs

- Papers with code
  - [ ] List papers and their codes

- Github & GitLab
  - [ ] Retrieve Github account of known people
  - [ ] Retrieve repositories mentioning known organizations
  - [ ] Retrieve repositories mentioning known people

## Data

### Semantic Scholar

latest version: 2025-02-18
https://api.semanticscholar.org/datasets/v1/release/2025-02-18/dataset/papers

Waiting for an API key

### HAL

#### SPARQL
SPARQL endpoint: https://data.hal.science/doc/sparql

Research team list:

```sparql
PREFIX org: <http://www.w3.org/ns/org#>
PREFIX skos: <http://www.w3.org/2004/02/skos/core#>
PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
SELECT DISTINCT ?org ?label ?alt{
  ?org a <http://www.w3.org/ns/org#OrganizationalUnit> ;
  	skos:prefLabel ?label ;
   skos:altLabel ?alt ;
   org:classification <https://data.archives-ouvertes.fr/vocabulary/StructureTypeResearchteam> .
}
```

List of the names of team members:

```sparql
PREFIX org: <http://www.w3.org/ns/org#>
PREFIX skos: <http://www.w3.org/2004/02/skos/core#>
PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
PREFIX foaf: <http://xmlns.com/foaf/0.1/>
PREFIX halschema: <http://data.archives-ouvertes.fr/schema/>

SELECT DISTINCT ?authorName {
  ?org org:classification <https://data.archives-ouvertes.fr/vocabulary/StructureTypeResearchteam> ;
  	skos:prefLabel ?teamLabel ;
   skos:altLabel ?altTeamLabel .

  ?author halschema:structure ?org ;
      foaf:name ?authorName .
}
ORDER BY DESC(?nom)
LIMIT 50
```

#### API

Portail INRIA: `inria`
```shell
curl "https://api.archives-ouvertes.fr/search/inria?q=*:*&rows=100&start=0&wt=json&fl=*"
```

Referential author
```shell
curl "http://api.archives-ouvertes.fr/ref/author/?q=*:*&rows=100&start=0&wt=json&fl=*"
```

Structure referential
```shell
curl "http://api.archives-ouvertes.fr/ref/structure?rows=100&start=0&wt=json&fl=*"
```

Author-structure link
```shell
curl "http://api.archives-ouvertes.fr/search/authorstructure/?firstName_t=*&lastName_t=*&rows=100&start=0&wt=json&fl=*"
```

Referential document
```shell
curl "http://api.archives-ouvertes.fr/ref/document/?q=*:*&rows=100&start=0&wt=json&fl=*"
```

### Paper with code

Download links: https://paperswithcode.com/about

### Code archive

### ORCID

XML Bulk files:
https://info.orcid.org/documentation/integration-guide/working-with-bulk-data/

Conversion from XML to JSON:
https://github.com/ORCID/orcid-conversion-lib

### BIL

Must be done manually
[BIL](https://bil.inria.fr/fr/catalog/listby/researcherWebPage)

### IdRef

Example: Author id : https://www.idref.fr/061775509
Corresponding rdf file: https://www.idref.fr/061775509.rdf

### GitHub

Search API endpoint: https://docs.github.com/en/rest/search/search?apiVersion=2022-11-28

Github python API library: https://pygithub.readthedocs.io/en/stable/github_objects.html

### Gitlab

[Gitlab](https://gitlab.inria.fr/)

```shell
curl --header "PRIVATE-TOKEN: <TOKEN>" "https://gitlab.inria.fr/api/v4/search?scope=projects&search=flight"
```


## Knowledge Graph

#### Source ogranization:

```mermaid
graph LR;
  ORCID --- Org.rdf
  ORCID --- Person.rdf
  IdRef --- Person.rdf
  GoogleScholar --- Person.rdf
  HAL --- Org.rdf
  HAL --- Person.rdf
  HAL --- Article.rdf
  OpenAlex --- Org.rdf
  OpenAlex --- Person.rdf
  OpenAlex --- Article.rdf
  PaperWithCode[Paper with code] --- Article.rdf
  PaperWithCode[Paper with code] --- Resource.rdf
  PaperWithCode[Paper with code] --- Person.rdf
  GitHub --- Resource.rdf
  Zenodo --- Resource.rdf
  GitLab[GitLab ?]
  SoftwareArchive[Software Archive ?]

```

#### Schema:

##### Data:
```mermaid
---
  config:
    class:
      hideEmptyMembersBox: true
---
classDiagram
  class Resource {
    rdfs:label : xsd:string [1]
    dct:abstract : xsd:string [1]
    dct:license : xsd:string [0..1]
    dcat:keyword : xsd:string [0..*]
    dct:created : xsd:date [0..1]
    dct:modified : xsd:date [0..1]
    dcat:version : xsd:string [0..1]
    dct:relation : rdfs:Resource [0..*]
  }

  class Source {
    pav:importedFrom : xsd:string [1]
    pav:retrievedOn : xsd:datetime [1]
    pav:lastRefreshedOn : xsd:datetime [1]
  }

  class ResourceIdentifier["datacite:ResourceIdentifier"]

  class GitHubIdentifier

  class RepositoryIdentifier

  class Person["foaf:Person"] {
    foaf:firstName : xsd:string [1]
    foaf:lastName : xsd:string [1]
    foaf:name : xsd:string [1]
    dct:alternative : xsd:string [1]
  }

  class PersonalIdentifier["datacite:PersonalIdentifier"]
  
  class foafOrg["foaf:Organization"] {
    foaf:fullName : xsd:string [1]
    dct:alternative : xsd:string [1]
  }

  class OrganizationIdentifier["datacite:OrganizationIdentifier"] {
    rdfs:label : xsdstring [1]
  }

  class Code["dctype:Software"]

  class dcatDataset["dcat:Dataset"] {
  }

  class Publication["bibo:Document"] {
    dct:title : xsd:string [1]
  }
  class PublicationIdentifier

  class Identifier["datacite:Identifier"]  {
    rdfs:label : xsdstring [1]
  }

  class provEntity["prov:Entity"]

  provEntity <|-- Resource
  Resource <|-- Code
  Resource <|-- dcatDataset
  Resource "1" --> "0..*" Source : pav retrievedFrom
  Resource "1" --> "0..*" Person : dct contributor
  Resource "1" --> "0..*" Resource : dct isReferencedBy
  Resource <|-- Publication
  Person "1" --> "1..*" foafOrg : foaf member
  Person "1" --> "0..*" PersonalIdentifier : adms identifier
  PersonalIdentifier <|-- ORCID
  PersonalIdentifier <|-- IdRef
  PersonalIdentifier <|-- GoogleScholar
  PersonalIdentifier <|-- HALPerson
  PersonalIdentifier <|-- GitHubUser
  Code "1" --> "1" ResourceIdentifier : adms identifier
  Code "0..*" --> "0..*" OrganizationIdentifier : dct publisher
  Code "0..*" --> "0..*" PersonalIdentifier : dct creator
  ResourceIdentifier <|-- ZenodoResource
  ResourceIdentifier <|-- RepositoryIdentifier
  ResourceIdentifier <|-- PublicationIdentifier
  Publication "1" --> "1" PublicationIdentifier : adms identifier
  foafOrg "1" --> "0..*" OrganizationIdentifier : adms identifier
  OrganizationIdentifier <|-- HALOrg
  OrganizationIdentifier <|-- GitHubOrg
  dcatDataset "1" --> "1" ResourceIdentifier : adms identifier
  PublicationIdentifier <|-- DOI
  PublicationIdentifier <|-- HALArticle
  PublicationIdentifier <|-- ArXiv
  Identifier <|-- ResourceIdentifier
  Identifier <|-- OrganizationIdentifier
  Identifier <|-- PersonalIdentifier
  Identifier <|-- PublicationIdentifier
  RepositoryIdentifier <|-- GitHubIdentifier
  
```

For later: 
- Extract URLs from publications using python code
- Use of [OpenRefine](https://openrefine.org/)
  - Search for Github URLs in abstracts
- Search for DOI in GitHub READMEs ?
- Use Tesseract to find GitHub URLs in articles

Note:
- ORKG judged too poor to be used. too few Organization, schema and API inconsistent