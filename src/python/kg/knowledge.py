from rdflib import DCAT, DCMITYPE, DCTERMS, DOAP, FOAF, OWL, RDF, RDFS, XSD, Graph, Literal, URIRef, BNode
from datetime import datetime

from kg.CONSTANTS import ADMS, BIBO, CITO, DATACITE, LOCAL, OO, PAV, ROH
from util.utilities import create_uri

class RDFResource:
        
    def __init__(self, uri: URIRef | BNode):
        self.uri = uri
        self.comments: set[Literal] = set()

    def add_comment(self, comment: str):
        self.comments.add(Literal(comment))

    def to_rdf(self, graph : Graph):
        for comment in self.comments:
            graph.add((self.uri, RDFS.comment, comment))

    def __hash__(self):
        if isinstance(self.uri, URIRef):
            return hash(self.uri)
        else:
            return 0
    
    def __eq__(self, other):
        if not isinstance(other, RDFResource):
            return False
        return self.uri == other.uri


class Source (RDFResource):
        
    def __init__(self, source_uri : URIRef):
        super().__init__(source_uri)
        self.importedFrom : Literal = Literal(str(source_uri))
        self.lastRefreshedOn : datetime = datetime.now()
        self.retrievedOn : datetime = datetime.now()

    def set_importedFrom(self, importedFrom : Literal):
        self.importedFrom = importedFrom
        
    def set_lastRefreshedOn(self, lastRefreshedOn : datetime):
        self.lastRefreshedOn = lastRefreshedOn
        
    def set_retrievedOn(self, retrievedOn : datetime):
        self.retrievedOn = retrievedOn
    
    def to_rdf(self, graph: Graph):
        super().to_rdf(graph)
        graph.add((self.uri, PAV.importedFrom, self.importedFrom))
        graph.add((self.uri, PAV.lastRefreshedOn, Literal(self.lastRefreshedOn.isoformat(), datatype=XSD.dateTime)))
        graph.add((self.uri, PAV.retrievedOn, Literal(self.retrievedOn.isoformat(), datatype=XSD.dateTime)))
        super().to_rdf(graph)

    def __hash__(self):
        return super().__hash__() + hash(self.importedFrom)

class Thing(RDFResource):
        
    def __init__(self, source : Source, uri : URIRef | BNode):
        super().__init__(uri)
        self.label : str = str(uri)
        self.source : Source = source
        self.retrieved_from : Literal | None = None
        self.related : list[RDFResource] = []
        
    def set_uri(self, uri : URIRef):
        self.uri = uri
    
    def set_label(self, label: str):
        self.label = label
        
    def set_source(self, source : Source):
        self.source = source
        
    def set_retrieved_from(self, retrieved_from : Literal):
        self.retrieved_from = retrieved_from
        
    def add_related(self, related : RDFResource):
        self.related.append(related)
    
    def to_rdf(self, graph : Graph):
        super().to_rdf(graph)
        if self.label is not None:
            graph.add((self.uri, RDFS.label, Literal(self.label)))
        graph.add((self.uri, PAV.retrievedFrom, self.source.uri))
        if self.retrieved_from is not None:
            graph.add((self.uri, PAV.retrievedFrom, self.retrieved_from))
        self.source.to_rdf(graph)
        for related in self.related:
            graph.add((self.uri, DCTERMS.relation, related.uri))
            related.to_rdf(graph)

    def __eq__(self, other):
        if not isinstance(other, Thing):
            return False
        if isinstance(self.uri, URIRef):
            return self.uri == other.uri
        else:
            return self.label == other.label

    def __str__(self):
        return f"URI: {self.uri} - Label: {self.label}"
    
    def __hash__(self):
        base = super().__hash__()
        if isinstance(self.uri, URIRef):
            base += hash(self.uri)
        else:
            base += hash(self.label)
        return base + hash(self.retrieved_from) + hash(self.source)
    
class UniqueIdentifier(Thing):        
    def __init__(self, source : Source, uri: URIRef | BNode):
        super().__init__(source, uri)
        
    def to_rdf(self, graph : Graph):
        super().to_rdf(graph)
        graph.add((self.uri, RDF.type, DATACITE.Identifier))
    
    def __hash__(self):
        return super().__hash__()

class Resource (Thing):        
    def __init__(self, source : Source, uri: URIRef | BNode):
        super().__init__(source, uri)
        self.abstract : str | None = None
        self.license: str | None = None
        self.keywords : set[str]  = set()
        self.created : str | None = None
        self.modified : str | None = None
        self.version : str | None = None
        self.referenced_by : set[Resource] = set()
        self.identifiers : set[UniqueIdentifier] = set()
        
    def set_abstract(self, abstract : str):
        self.abstract = abstract
        
    def set_license(self, license : str):
        self.license = license
        
    def add_keyword(self, keyword : str):
        self.keywords.add(keyword)
        
    def set_created(self, created : str):
        self.created = created
        
    def set_modified(self, modified : str):
        self.modified = modified
        
    def set_version(self, version : str):
        self.version = version
        
    def add_referenced_by(self, referenced_by):
        self.referenced_by.add(referenced_by)
        
    def add_identifier(self, identifier : UniqueIdentifier):
        self.identifiers.add(identifier)
    
    def to_rdf(self, graph : Graph):
        super().to_rdf(graph)
        if self.abstract is not None:
            graph.add((self.uri, DCTERMS.abstract, Literal(self.abstract)))
        if self.license is not None:
            graph.add((self.uri, DCTERMS.license, Literal(self.license)))
        for keyword in self.keywords:
            graph.add((self.uri, DCTERMS.subject, Literal(keyword)))
        if self.created is not None:
            graph.add((self.uri, PAV.retrievedFrom, Literal(self.created)))
        if self.modified is not None:
            graph.add((self.uri, DCTERMS.modified, Literal(self.modified)))
        if self.version is not None:
            graph.add((self.uri, OWL.versionInfo, Literal(self.version)))
        for identifier in self.identifiers:
            graph.add((self.uri, ADMS.identifier, identifier.uri))
        for referenced_by in self.referenced_by:
            graph.add((self.uri, DCTERMS.isReferencedBy, referenced_by.uri))
            referenced_by.to_rdf(graph)

    def __str__(self):
        return super().__str__() + f"Abstract: {self.abstract} License: {self.license} Keywords: {self.keywords} Created: {self.created} Modified: {self.modified} Version: {self.version} Related: {self.related} Identifiers: {self.identifiers} Referenced by: {self.referenced_by}"
    
    def __hash__(self):
        return super().__hash__() + hash(self.abstract) + hash(self.version)
    
class Repository (Resource):
        
    def __init__(self, source : Source, uri: URIRef | BNode):
        super().__init__(source, uri)
        
    def to_rdf(self, graph : Graph):
        super().to_rdf(graph)
        graph.add((self.uri, RDF.type, DCMITYPE.Software))

class Agent(Thing):
    def __init__(self, source: Source, uri: URIRef | BNode):
        super().__init__(source, uri)
        self.locations: set[URIRef| Literal] = set()

    def add_location(self, location: URIRef | Literal):
        self.locations.add(location)
    
    def __hash__(self):
        return super().__hash__()
    
    def to_rdf(self, graph: Graph):
        super().to_rdf(graph)
        for location in self.locations:
            graph.add((self.uri, DCTERMS.coverage, location))

class Organization (Agent):
    def __init__(self, source: Source, label: str):
            super().__init__(source, create_uri(label))
            self.set_label(label)
            self.alternatives: set[str] = set()
            self.identifiers: set[UniqueIdentifier] = set()

    def add_alternative(self, alternative: str):
        self.alternatives.add(alternative)
        
    def add_identifier(self, identifier: UniqueIdentifier):
        self.identifiers.add(identifier)

    def __eq__(self, value: object) -> bool:
        if not isinstance(value, Organization):
            return False
        return super().__eq__(value)
    
    def __hash__(self):
        return super().__hash__() + hash(self.identifiers)
    
    def to_rdf(self, graph: Graph):
        super().to_rdf(graph)
        graph.add((self.uri, RDF.type, FOAF.Organization))
        graph.add((self.uri, RDFS.label, Literal(self.label)))
        for alternative in self.alternatives:
            graph.add((self.uri, DCTERMS.alternative, Literal(alternative)))
        for identifier in self.identifiers:
            graph.add((self.uri, ADMS.identifier, identifier.uri))
            identifier.to_rdf(graph)

class Person (Agent):

    def __init__(self, source : Source, uri : URIRef | BNode):
        super().__init__(source, uri)
        self.first_name : str | None = None
        self.last_name : str | None = None
        self.alternatives : set[str] = set()
        self.orcid : str | URIRef | None = None
        self.affiliations : set[Organization] = set()
        self.identifiers : set[UniqueIdentifier]  = set()
        self.contacts: set[Literal | URIRef] = set()

    def set_first_name(self, first_name : str):
        self.first_name = first_name
        
    def set_last_name(self, last_name : str):
        self.last_name = last_name

    def add_alternative(self, alternative : str):
        self.alternatives.add(alternative)
        
    def set_orcid(self, orcid : str | URIRef):
        self.orcid = orcid
        
    def add_affiliation(self, affiliation : Organization):
        self.affiliations.add(affiliation)
        
    def add_identifier(self, identifier : UniqueIdentifier):
        self.identifiers.add(identifier)
        
    def add_contact(self, contact : Literal | URIRef):
        self.contacts.add(contact)
    
    def to_rdf(self, graph: Graph):
        super().to_rdf(graph)
        graph.add((self.uri, RDF.type, FOAF.Person))
        graph.add((self.uri, FOAF.firstName, Literal(self.first_name)))
        graph.add((self.uri, FOAF.lastName, Literal(self.last_name)))
        for alternative in self.alternatives:
            graph.add((self.uri, DCTERMS.alternative, Literal(alternative)))
        if self.orcid != None:
            if isinstance(self.orcid, URIRef):
                graph.add((self.uri, OWL.sameAs, self.orcid)) # type: ignore
            else:
                graph.add((self.uri, ROH.ORCID, Literal(self.orcid)))
        for affiliation in self.affiliations:
            graph.add((self.uri, FOAF.member, affiliation.uri))
            affiliation.to_rdf(graph)
        for identifier in self.identifiers:
            graph.add((self.uri, ADMS.identifier, identifier.uri))
            identifier.to_rdf(graph)
        for contact in self.contacts:
            graph.add((self.uri, OO.contact, contact))
    
    def __hash__(self):
        base = super().__hash__()
        if self.orcid != None:
            base += hash(self.orcid)
        return base + hash(self.first_name) + hash(self.last_name)
        

class CitationCount(RDFResource):
    def __init__(self, count: int, source: Source):
        super().__init__(BNode())
        self.count: int = count
        self.source: Source = source
        self.date_of_citation: Literal | None = None

    def set_date_of_citation(self, date: str):
        self.date_of_citation = Literal(date)
    
    def to_rdf(self, graph: Graph):
        graph.add((self.uri, DCTERMS.source, self.source.uri))
        graph.add((self.uri, RDF.value, Literal(self.count)))
        if self.date_of_citation != None:
            graph.add((self.uri, DCTERMS.date, Literal(self.date_of_citation)))
        self.source.to_rdf(graph)
        return super().to_rdf(graph)
    
    def __hash__(self):
        return super().__hash__() + hash(self.source) + hash(self.count)

    def __str__(self):
        return f"{self.source} {self.count} {self.comments}"
    
    def __eq__(self, other):
        if isinstance(other, CitationCount):
            return self.source == other.source and self.count == other.count and self.date_of_citation == other.date_of_citation
        else:
            return False
        
class Paper (Resource):        
    def __init__(self, source: Source, uri: URIRef | BNode):
        super().__init__(source, uri)
        self.title : str | None = None
        self.authors : set[Person] = set()
        self.publication_date : str | None = None
        self.venue : URIRef | BNode | None = None
        self.doi : URIRef | str | None = None
        self.related_works : set[Paper] = set()
        self.citation_count : set[CitationCount] = set()
        self.repositories : set[URIRef] = set()
        self.download_url : set[Literal] = set()
        
    def set_title(self, title : str):
        self.title = title
        
    def add_author(self, author : Person):
        self.authors.add(author)
        
    def set_abstract(self, abstract : str):
        self.abstract = abstract
        
    def add_keyword(self, keyword : str):
        self.keywords.add(keyword)
        
    def set_publication_date(self, publication_date : str):
        self.publication_date = publication_date
        
    def set_venue(self, venue : URIRef | BNode):
        self.venue = venue
        
    def set_doi(self, doi : URIRef | str):
        self.doi = doi
        
    def add_related_work(self, related_work):
        self.related_works.add(related_work)
        
    def add_citation_count(self, citation_count : CitationCount):
        self.citation_count.add(citation_count)
        
    def add_repository(self, repository : URIRef):
        self.repositories.add(repository)
        
    def add_download_url(self, download_url : str):
        self.download_url.add(Literal(download_url))
    
    def __eq__(self, other):
        if not isinstance(other, Paper):
            return False
        return self.uri == other.uri
    
    def __hash__(self):
        return super().__hash__() +  hash(self.uri)
    
    def to_rdf(self, graph : Graph):
        super().to_rdf(graph)
        graph.add((self.uri, RDF.type, BIBO.Document))
        graph.add((self.uri, DCTERMS.title, Literal(self.title)))
        for author in self.authors:
            graph.add((self.uri, DCTERMS.contributor, author.uri))
            author.to_rdf(graph)
        if self.publication_date is not None:
            graph.add((self.uri, DCTERMS.date, Literal(self.publication_date)))
            graph.add((self.uri, PAV.authoredOn, Literal(self.publication_date)))
        if self.venue is not None:
            graph.add((self.uri, DCTERMS.isPartOf, Literal(self.venue)))
        if self.doi is not None:
            graph.add((self.uri, DCTERMS.identifier, self.doi)) # type: ignore
            graph.add((self.uri, BIBO.doi, self.doi)) # type: ignore
        for download_url in self.download_url:
            graph.add((self.uri, DCAT.downloadURL, download_url))
        for related_work in self.related_works:
            graph.add((self.uri, DCTERMS.relation, related_work.uri))
            related_work.to_rdf(graph)
        for citation in self.citation_count:
            graph.add((self.uri, DCTERMS.bibliographicCitation, citation.uri))
            citation.to_rdf(graph)

    def __str__(self):
        return f"{super().__str__()} Paper({self.title}, {self.authors}, {self.publication_date}, {self.venue}, {self.doi})"
    

class Software(Resource):
    def __init__(self, source: Source, uri: URIRef | BNode):
        super().__init__(source, uri)
        self.creators: set[Agent] = set()
        self.language: set[Literal] = set()
        self.platform: set[Literal] = set()
        self.repository: set[Literal] = set()
        self.available_at: set[Literal] = set()
        self.publication: Literal | None = None
        self.rights: Literal | None = None

    def add_creator(self, creator: Agent):
        self.creators.add(creator)
        
    def add_language(self, language: str):
        self.language.add(Literal(language))
        
    def add_platform(self, platform: str):
        self.platform.add(Literal(platform))
        
    def add_repository(self, repository: str):
        self.repository.add(Literal(repository))
        
    def add_available_at(self, available_at: str):
        self.available_at.add(Literal(available_at))
        
    def set_publication(self, publication: str):
        self.publication = Literal(publication)
        
    def set_rights(self, rights: str):
        self.rights = Literal(rights)

    def to_rdf(self, graph: Graph):
        super().to_rdf(graph)
        for creator in self.creators:
            graph.add((self.uri, DCTERMS.creator, creator.uri))
            creator.to_rdf(graph)
        for language in self.language:
            graph.add((self.uri, DCTERMS.language, language))
        for platform in self.platform:
            graph.add((self.uri, DCTERMS.source, platform))
        for repository in self.repository:
            graph.add((self.uri, DOAP.repository, repository))
        for available_at in self.available_at:
            graph.add((self.uri, DCTERMS.available, available_at))
        if self.publication is not None:
            graph.add((self.uri, DCTERMS.issued, self.publication)) # type: ignore
        if self.rights is not None:
            graph.add((self.uri, DCTERMS.rights, self.rights)) # type: ignore

    def __str__(self):
        return f"{super().__str__()} Software({self.creators})"
    
    def __eq__(self, other):
        return super().__eq__(other) and self.creators == other.creators()
    
    def __hash__(self):
        return hash((super().__hash__(), tuple(self.creators)))
    
