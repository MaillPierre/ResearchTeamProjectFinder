# ResearchTeamProjectFinder

The aim of this project is to create a tool able to use the different APIs available to find the public Git repositories of INRIA research teams. Further development will aim to extend this approach to all european research teams.

## Data

### Semantic Scholar

latest version: 2025-02-18
https://api.semanticscholar.org/datasets/v1/release/2025-02-18/dataset/papers

Waiting for an API key

### HAL

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

### Paper with code

Dowlnload links: https://paperswithcode.com/about

### Code archive

### ORCID

XML Bulk files:
https://info.orcid.org/documentation/integration-guide/working-with-bulk-data/

Conversion from XML to JSON:
https://github.com/ORCID/orcid-conversion-lib

### BIL

Must be done manually
[BIL](https://bil.inria.fr/fr/catalog/listby/researcherWebPage)

## Knowledge Graph

#### Source ogranization:

```mermaid
graph LR;
  ORCID --- Org.rdf
  ORCID --- Person.rdf
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
```mermaid
---
  config:
    class:
      hideEmptyMembersBox: true
---
classDiagram
  class Person {
    foaf:firstName : xsd:string [1]
    foaf:lastName : xsd:string [1]
    foaf:fullName : xsd:string [1]
    dct:alternative : xsd:string [1]
  }
  Person "1" --> "1..*" Organization : foaf member
  Person "1" --> "0..*" PersonalIdentifier : adms identifier
  
  class foafOrg["foaf:Organization"]
  foafOrg <|-- Organization
  class Organization {
    owl:sameAs : datacite:OrganizationIdentifier [1..*]
    foaf:fullName : xsd:string [1]
    dct:alternative : xsd:string [1]
  }
  Organization "1" --> "0..*" OrganizationIdentifier : adms identifier

  class PersonalIdentifier["datacite:PersonalIdentifier"]
  PersonalIdentifier <|-- ORCID
  PersonalIdentifier <|-- HALPerson
  PersonalIdentifier <|-- GitHubUser

  class OrganizationIdentifier["datacite:OrganizationIdentifier"]
  OrganizationIdentifier <|-- HALOrg
  OrganizationIdentifier <|-- GitHubOrg

  class ResourceIdentifier["datacite:ResourceIdentifier"] {
  }

  ResourceIdentifier <|-- ZenodoResource
  ResourceIdentifier <|-- GitHubRepository
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

  class Code["dctype:Software"]
  Code "1" --> "1" ResourceIdentifier : adms identifier
  dcatDataset "1" --> "1" ResourceIdentifier : adms identifier
  Resource <|-- Code
  Resource <|-- dcatDataset
  Resource "1" --> "0..*" Person : dct contributor
  Resource "1" --> "0..*" Resource : dct isReferencedBy
  Resource <|-- Publication

  class Publication["bibo:Document"] {
    dct:title : xsd:string [1]
  }
  Publication "1" --> "1" PublicationIdentifier : adms identifier
  ResourceIdentifier <|-- PublicationIdentifier
  PublicationIdentifier <|-- DOI
  PublicationIdentifier <|-- HALArticle
  PublicationIdentifier <|-- ArXiv

  class dcatDataset["dcat:Dataset"] {
  }
  
```

For later: 
- Extract URLs from publications using python code
- Use of [OpenRefine](https://openrefine.org/)

Note:
- ORKG judged too poor to be used. too few Organization, schema and API inconsistent