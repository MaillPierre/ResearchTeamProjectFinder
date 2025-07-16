from rdflib import DCMITYPE, DCTERMS, FOAF, OWL, RDF, RDFS, XSD, Graph, Literal, URIRef, BNode
from datetime import datetime

from kg.CONSTANTS import ADMS, BIBO, DATACITE, LOCAL, PAV
from util.utilities import create_uri

class RDF_Resource:
    
    class Builder:
        def __init__(self, uri: URIRef | BNode):
            self.uri = uri

        def build(self):
            return RDF_Resource(self)
        
    def __init__(self, builder: Builder):
        self.builder = builder
    
    def uri(self):
        return self.builder.uri

    def to_rdf(self, graph : Graph):
        pass

    def __hash__(self):
        return hash(self.uri())
    
    def __eq__(self, other):
        if not isinstance(other, RDF_Resource):
            return False
        return self.uri() == other.uri()


class Source (RDF_Resource):
    class Builder(RDF_Resource.Builder):
        def __init__(self, source_uri : URIRef):
            super().__init__(source_uri)
            self.importedFrom : Literal = Literal(str(source_uri))
            self.lastRefreshedOn : datetime = datetime.now()
            self.retrievedOn : datetime = datetime.now()

        def set_importedFrom(self, importedFrom : Literal):
            self.importedFrom = importedFrom
            return self
        
        def set_lastRefreshedOn(self, lastRefreshedOn : datetime):
            self.lastRefreshedOn = lastRefreshedOn
            return self
        
        def set_retrievedOn(self, retrievedOn : datetime):
            self.retrievedOn = retrievedOn
            return self
        
        def build(self):
            return Source(self)
        
    def __init__(self, builder : Builder):
        self.builder = builder

    def importedFrom(self) -> Literal:
        return self.builder.importedFrom
    
    def lastRefreshedOn(self) -> datetime:
        return self.builder.lastRefreshedOn
    
    def retrievedOn(self) -> datetime:
        return self.builder.retrievedOn
    
    def to_rdf(self, graph: Graph):
        graph.add((self.uri(), PAV.importedFrom, self.importedFrom()))
        graph.add((self.uri(), PAV.lastRefreshedOn, Literal(self.lastRefreshedOn(), datatype=XSD.dateTime)))
        graph.add((self.uri(), PAV.retrievedOn, Literal(self.retrievedOn(), datatype=XSD.dateTime)))
        super().to_rdf(graph)

class Thing(RDF_Resource):
    class Builder(RDF_Resource.Builder):
        def __init__(self, source : Source, uri : URIRef | BNode):
            super().__init__(uri)
            self.label : str = str(uri)
            self.source : Source = source
            self.retrieved_from : Literal | None = None
        
        def set_uri(self, uri : URIRef):
            self.uri = uri
            return self
        
        def set_label(self, label: str):
            self.label = label
            return self
        
        def set_source(self, source : Source):
            self.source = source
            return self
        
        def set_retrieved_from(self, retrieved_from : Literal):
            self.retrieved_from = retrieved_from
            return self
        
    def __init__(self, builder : Builder):
        self.builder = builder
        
    def label(self) -> str:
        return self.builder.label
    
    def source(self) -> Source:
        return self.builder.source
    
    def retrieved_from(self) -> Literal | None:
        return self.builder.retrieved_from
    
    def to_rdf(self, graph : Graph):
        if self.label() is not None:
            graph.add((self.uri(), RDFS.label, Literal(self.label())))
            graph.add((self.uri(), PAV.retrievedFrom, self.source().uri()))
            if self.retrieved_from() is not None:
                graph.add((self.uri(), PAV.retrievedFrom, self.retrieved_from())) # type: ignore
            self.source().to_rdf(graph)

    def __eq__(self, other):
        if not isinstance(other, Thing):
            return False
        if isinstance(self.uri(), URIRef):
            return self.uri() == other.uri()
        else:
            return self.label() == other.label()

    def __str__(self):
        return f"URI: {self.builder.uri} - Label: {self.builder.label}"
    
    def __hash__(self):
        if isinstance(self.uri(), URIRef):
            return hash(self.uri())
        else:
            return hash(self.label())
    
class Identifier(Thing):
    class Builder(Thing.Builder):
        def __init__(self, source : Source, uri: URIRef | BNode):
            super().__init__(source, uri)

        def build(self):
            return Identifier(self)
        
    def __init__(self, builder: Builder):
        super().__init__(builder)
        
    def to_rdf(self, graph : Graph):
        super().to_rdf(graph)
        graph.add((self.uri(), RDF.type, DATACITE.Identifier))

class Resource (Thing):

    class Builder (Thing.Builder):

        def __init__(self, source : Source, uri: URIRef | BNode):
            super().__init__(source, uri)
            self.abstract : str | None = None
            self.license: str | None = None
            self.keywords : set[str]  = set()
            self.created : str | None = None
            self.modified : str | None = None
            self.version : str | None = None
            self.related : list[URIRef | BNode] = []
            self.identifiers : set[Identifier] = set()
            self.referenced_by : set[Resource] = set()

        def build(self):
            return Resource(self)
        
        def set_abstract(self, abstract : str):
            self.abstract = abstract
            return self
        
        def set_license(self, license : str):
            self.license = license
            return self
        
        def add_keyword(self, keyword : str):
            self.keywords.add(keyword)
            return self
        
        def set_created(self, created : str):
            self.created = created
            return self
        
        def set_modified(self, modified : str):
            self.modified = modified
            return self
        
        def set_version(self, version : str):
            self.version = version
            return self
        
        def add_related(self, related : URIRef | BNode):
            self.related.append(related)
            return self
        
        def add_identifier(self, identifier : Identifier):
            self.identifiers.add(identifier)
            return self
        
        def add_referenced_by(self, referenced_by):
            self.referenced_by.add(referenced_by)
            return self
        
    def __init__(self, builder : Builder):
        super().__init__(builder)
        self.builder = builder
    
    def abstract(self):
        return self.builder.abstract
    
    def license(self):
        return self.builder.license
    
    def keywords(self):
        return self.builder.keywords
    
    def created(self):
        return self.builder.created
    
    def modified(self):
        return self.builder.modified
    
    def version(self):
        return self.builder.version
    
    def related(self):
        return self.builder.related
    
    def identifiers(self):
        return self.builder.identifiers
    
    def referenced_by(self):
        return self.builder.referenced_by
    
    def to_rdf(self, graph : Graph):
        super().to_rdf(graph)
        if self.abstract() is not None:
            graph.add((self.uri(), DCTERMS.abstract, Literal(self.abstract())))
        if self.license() is not None:
            graph.add((self.uri(), DCTERMS.license, Literal(self.license())))
        for keyword in self.keywords():
            graph.add((self.uri(), DCTERMS.subject, Literal(keyword)))
        if self.created() is not None:
            graph.add((self.uri(), PAV.retrievedFrom, Literal(self.created())))
        if self.modified() is not None:
            graph.add((self.uri(), DCTERMS.modified, Literal(self.modified())))
        if self.version() is not None:
            graph.add((self.uri(), OWL.versionInfo, Literal(self.version())))
        for related in self.related():
            graph.add((self.uri(), DCTERMS.relation, related))
        for identifier in self.identifiers():
            graph.add((self.uri(), ADMS.identifier, identifier.uri()))
        for referenced_by in self.referenced_by():
            graph.add((self.uri(), DCTERMS.isReferencedBy, referenced_by.uri()))
            referenced_by.to_rdf(graph)

    def __str__(self):
        return super().__str__() + f"Abstract: {self.abstract()} License: {self.license()} Keywords: {self.keywords()} Created: {self.created()} Modified: {self.modified()} Version: {self.version()} Related: {self.related()} Identifiers: {self.identifiers()} Referenced by: {self.referenced_by()}"
    
class Repository (Resource):
    class Builder(Resource.Builder):
        def __init__(self, source : Source, uri: URIRef | BNode):
            super().__init__(source, uri)

        def build(self):
            return Repository(self)
        
    def __init__(self, builder: Builder):
        super().__init__(builder)
        
    def to_rdf(self, graph : Graph):
        super().to_rdf(graph)
        graph.add((self.uri(), RDF.type, DCMITYPE.Software))

class Organization (Thing):

    class Builder(Thing.Builder):
        def __init__(self, source: Source, label: str):
            super().__init__(source, create_uri(label))
            self.set_label(label)
            self.alternatives: set[str] = set()
            self.identifiers: set[Identifier] = set()

        def add_alternative(self, alternative: str):
            self.alternatives.add(alternative)
            return self
        
        def set_identifier(self, identifier: URIRef | BNode):
            self.identifier = identifier
            return self
        
        def build(self):
            return Organization(self)


    def __init__(self, builder: Builder):
        super().__init__(builder)
        self.builder = builder

    def __eq__(self, value: object) -> bool:
        if not isinstance(value, Organization):
            return False
        return super().__eq__(value)

    def alternatives(self):
        return self.builder.alternatives
    
    def to_rdf(self, graph: Graph):
        super().to_rdf(graph)
        graph.add((self.uri(), RDF.type, FOAF.Organization))
        graph.add((self.uri(), RDFS.label, Literal(self.label())))
        for alternative in self.alternatives():
            graph.add((self.uri(), DCTERMS.alternative, Literal(alternative)))
        for identifier in self.builder.identifiers:
            graph.add((self.uri(), ADMS.identifier, identifier.uri()))
            identifier.to_rdf(graph)

class Person (Thing):

    class Builder (Thing.Builder):
        def __init__(self, source : Source, uri : URIRef | BNode):
            super().__init__(source, uri)
            self.first_name : str | None = None
            self.last_name : str | None = None
            self.alternatives : list[str] = []
            self.orcid : str | URIRef | None = None
            self.affiliations : list[Organization] = []
            self.identifiers : list[Identifier]  = []

        def set_first_name(self, first_name : str):
            self.first_name = first_name
            return self
        
        def set_last_name(self, last_name : str):
            self.last_name = last_name
            return self
        
        def add_alternative(self, alternative : str):
            self.alternatives.append(alternative)
            return self
        
        def set_orcid(self, orcid : str | URIRef):
            self.orcid = orcid
            return self
        
        def add_affiliation(self, affiliation : Organization):
            self.affiliations.append(affiliation)
            return self
        
        def add_identifier(self, identifier : Identifier):
            self.identifiers.append(identifier)
            return self
        
        def set_uri(self, uri : URIRef):
            self.uri = uri
            return self
        
        def build(self):
            return Person(self)

    def __init__(self, builder: Builder):
        super().__init__(builder)
        self.builder = builder

    def first_name(self) -> str | None:
        return self.builder.first_name
    
    def last_name(self) -> str | None:
        return self.builder.last_name
    
    def alternatives(self) -> list[str]:
        return self.builder.alternatives
    
    def orcid(self) -> URIRef | str | None:
        return self.builder.orcid
    
    def affiliations(self) -> list[Organization]:
        return self.builder.affiliations
    
    def identifiers(self) -> list[Identifier]:
        return self.builder.identifiers
    
    def source(self) -> Source | None:
        return self.builder.source
    
    def to_rdf(self, graph: Graph):
        super().to_rdf(graph)
        graph.add((self.uri(), RDF.type, FOAF.Person))
        graph.add((self.uri(), FOAF.firstName, Literal(self.first_name())))
        graph.add((self.uri(), FOAF.lastName, Literal(self.last_name())))
        for alternative in self.alternatives():
            graph.add((self.uri(), DCTERMS.alternative, Literal(alternative)))
        if self.orcid() != None:
            if isinstance(self.orcid(), URIRef):
                graph.add((self.uri(), OWL.sameAs, self.orcid())) # type: ignore
            else:
                graph.add((self.uri(), LOCAL.orcid, Literal(self.orcid())))
        for affiliation in self.affiliations():
            graph.add((self.uri(), FOAF.member, affiliation.uri()))
            affiliation.to_rdf(graph)
        for identifier in self.identifiers():
            graph.add((self.uri(), ADMS.identifier, identifier.uri()))
            identifier.to_rdf(graph)
        

# Class to store a paper
class Paper (Resource):

    class Builder (Resource.Builder):
        def __init__(self, source: Source, uri: URIRef | BNode):
            super().__init__(source, uri)
            self.title : str | None = None
            self.authors : set[Person] = set()
            self.publication_date : str | None = None
            self.venue : URIRef | BNode | None = None
            self.doi : URIRef | None = None
            self.identifiers : set[Identifier] = set()
            self.related_works : list[Paper] = []
            self.citation_count : int = 0
            self.repositories : list[URIRef] = []

        def build(self):
            return Paper(self)
        
        def set_title(self, title : str):
            self.title = title
            return self
        
        def add_author(self, author : Person):
            self.authors.add(author)
            return self
        
        def set_abstract(self, abstract : str):
            self.abstract = abstract
            return self
        
        def add_keyword(self, keyword : str):
            self.keywords.add(keyword)
            return self
        
        def set_publication_date(self, publication_date : str):
            self.publication_date = publication_date
            return self
        
        def set_venue(self, venue : URIRef | BNode):
            self.venue = venue
            return self
        
        def set_doi(self, doi : URIRef):
            self.doi = doi
            return self
        
        def add_identifier(self, identifier : Identifier):
            self.identifiers.add(identifier)
            return self
        
        def add_related_work(self, related_work):
            self.related_works.append(related_work)
            return self
        
        def set_citation_count(self, citation_count : int):
            self.citation_count = citation_count
            return self
        
        def add_repository(self, repository : URIRef):
            self.repositories.append(repository)
            return self
        
    def __init__(self, builder : Builder):
        super().__init__(builder)
        self.builder = builder
    
    def title(self) -> str | None:
        return self.builder.title
    
    def authors(self) -> set[Person]:
        return self.builder.authors
    
    def publication_date(self) -> str | None:
        return self.builder.publication_date
    
    def venue(self) -> URIRef | BNode | None:
        return self.builder.venue
    
    def doi(self) -> URIRef | None:
        return self.builder.doi
    
    def identifiers(self) -> set[Identifier]:
        return self.builder.identifiers
    
    def related_works(self):
        return self.builder.related_works
    
    def citation_count(self) -> int :
        return self.builder.citation_count
    
    def repositories(self) -> list[URIRef]:
        return self.builder.repositories
    
    
    def __eq__(self, other):
        if not isinstance(other, Paper):
            return False
        return self.uri == other.uri
    
    def __hash__(self):
        return hash(self.uri)
    
    def to_rdf(self, graph : Graph):
        super().to_rdf(graph)
        graph.add((self.uri(), RDF.type, BIBO.Document))
        graph.add((self.uri(), DCTERMS.title, Literal(self.title())))
        for author in self.authors():
            graph.add((self.uri(), DCTERMS.contributor, author.uri()))
            author.to_rdf(graph)
        if self.publication_date() is not None:
            graph.add((self.uri(), DCTERMS.date, Literal(self.publication_date())))
            graph.add((self.uri(), PAV.authoredOn, Literal(self.publication_date())))
        if self.venue() is not None:
            graph.add((self.uri(), DCTERMS.isPartOf, Literal(self.venue())))
        if self.doi() is not None:
            graph.add((self.uri(), DCTERMS.identifier, Literal(self.doi())))
            graph.add((self.uri(), BIBO.doi, Literal(self.doi())))
        
        for related_work in self.related_works():
            graph.add((self.uri(), DCTERMS.relation, related_work.uri()))
            related_work.to_rdf(graph)

    def __str__(self):
        return f"{super().__str__()} Paper({self.title()}, {self.authors()}, {self.publication_date()}, {self.venue()}, {self.doi()})"
