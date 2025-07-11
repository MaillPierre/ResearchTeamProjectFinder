from rdflib import DCTERMS, FOAF, OWL, PROV, RDF, RDFS, Graph, Literal, URIRef, BNode
from datetime import datetime

from kg.CONSTANTS import ADMS, BIBO, LOCAL, PAV

class Thing:
    class Builder:
        def __init__(self, uri):
            self.uri : URIRef | BNode = uri
            self.label : str | None = None
        
        def set_uri(self, uri : URIRef):
            self.uri = uri
            return self
        
        def set_label(self, label: str):
            self.label = label
            return self
        
    def __init__(self, builder : Builder):
        self.builder = builder

    def uri(self) -> URIRef | BNode:
        return self.builder.uri
        
    def label(self):
        return self.builder.label
    
    def write(self, graph : Graph):
        if self.label() is not None:
            graph.add((self.uri(), RDFS.label, Literal(self.label())))

    def __str__(self):
        return f"URI: {self.builder.uri} - Label: {self.builder.label}"

class Resource (Thing):

    class Builder (Thing.Builder):

        def __init__(self, uri):
            super().__init__(uri)
            self.abstract : str | None = None
            self.license: str | None = None
            self.keywords : list[str]  = []
            self.created : str | None = None
            self.modified : str | None = None
            self.version : str | None = None
            self.related : list[URIRef | BNode] = []
            self.identifiers : list[URIRef] = []
            self.referenced_by : list[URIRef | BNode] = []

        def build(self):
            return Resource(self)
        
        def set_abstract(self, abstract : str):
            self.abstract = abstract
            return self
        
        def set_license(self, license : str):
            self.license = license
            return self
        
        def add_keyword(self, keyword : str):
            self.keywords.append(keyword)
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
        
        def add_identifier(self, identifier : URIRef):
            self.identifiers.append(identifier)
            return self
        
        def add_referenced_by(self, referenced_by):
            self.referenced_by.append(referenced_by)
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
    
    def write(self, graph : Graph):
        super().write(graph)
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
            graph.add((self.uri(), ADMS.identifier, identifier))
        for referenced_by in self.referenced_by():
            graph.add((self.uri(), DCTERMS.isReferencedBy, referenced_by))


    def __str__(self):
        return super().__str__() + f"Abstract: {self.abstract()} License: {self.license()} Keywords: {self.keywords()} Created: {self.created()} Modified: {self.modified()} Version: {self.version()} Related: {self.related()} Identifiers: {self.identifiers()} Referenced by: {self.referenced_by()}"
        

# Class to store a paper
class Paper (Resource):

    class Builder (Resource.Builder):
        def __init__(self, uri):
            super().__init__(uri)
            self.title : str | None = None
            self.authors : list[URIRef | BNode] = []
            self.publication_date : str | None = None
            self.venue : URIRef | BNode | None = None
            self.doi : URIRef | None = None
            self.identifiers : list[URIRef] = []
            self.related_works : list[URIRef | BNode] = []
            self.citation_count : int = 0
            self.source : URIRef | None = None
            self.repositories : list[URIRef] = []

        def build(self):
            return Paper(self)
        
        def set_title(self, title : str):
            self.title = title
            return self
        
        def add_author(self, author : URIRef | BNode):
            self.authors.append(author)
            return self
        
        def set_abstract(self, abstract : str):
            self.abstract = abstract
            return self
        
        def add_keyword(self, keyword : str):
            self.keywords.append(keyword)
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
        
        def add_identifier(self, identifier : URIRef):
            self.identifiers.append(identifier)
            return self
        
        def add_related_work(self, related_work : URIRef):
            self.related_works.append(related_work)
            return self
        
        def set_citation_count(self, citation_count : int):
            self.citation_count = citation_count
            return self
        
        def set_source(self, source : URIRef):
            self.source = source
            return self
        
        def add_repository(self, repository : URIRef):
            self.repositories.append(repository)
            return self
        
    def __init__(self, builder : Builder):
        super().__init__(builder)
        self.builder = builder
    
    def title(self) -> str | None:
        return self.builder.title
    
    def authors(self) -> list[URIRef | BNode]:
        return self.builder.authors
    
    def publication_date(self) -> str | None:
        return self.builder.publication_date
    
    def venue(self) -> URIRef | BNode | None:
        return self.builder.venue
    
    def doi(self) -> URIRef | None:
        return self.builder.doi
    
    def identifiers(self) -> list[URIRef]:
        return self.builder.identifiers
    
    def related_works(self) -> list[URIRef | BNode]:
        return self.builder.related_works
    
    def citation_count(self) -> int :
        return self.builder.citation_count
    
    def source(self) -> URIRef | None:
        return self.builder.source
    
    def repositories(self) -> list[URIRef]:
        return self.builder.repositories
    
    
    def __eq__(self, other):
        if not isinstance(other, Paper):
            return False
        return self.uri == other.uri
    
    def __hash__(self):
        return hash(self.uri)
    
    def write(self, graph : Graph):
        super().write(graph)
        graph.add((self.uri(), RDF.type, BIBO.Document))
        graph.add((self.uri(), DCTERMS.title, Literal(self.title())))
        for author in self.authors():
            graph.add((self.uri(), DCTERMS.contributor, author))
        if self.publication_date() is not None:
            graph.add((self.uri(), DCTERMS.date, Literal(self.publication_date())))
            graph.add((self.uri(), PAV.authoredOn, Literal(self.publication_date())))
        if self.venue() is not None:
            graph.add((self.uri(), DCTERMS.isPartOf, Literal(self.venue())))
        if self.doi() is not None:
            graph.add((self.uri(), DCTERMS.identifier, Literal(self.doi())))
            graph.add((self.uri(), BIBO.doi, Literal(self.doi())))
        
        for related_work in self.related_works():
            graph.add((self.uri(), DCTERMS.relation, related_work))

    def __str__(self):
        return f"{super().__str__()} Paper({self.title()}, {self.authors()}, {self.publication_date()}, {self.venue()}, {self.doi()})"

class Person (Thing):

    class Builder (Thing.Builder):
        def __init__(self, uri : URIRef | BNode):
            super().__init__(uri)
            self.first_name : str | None = None
            self.last_name : str | None = None
            self.alternatives : list[str] = []
            self.orcid : str | URIRef | None = None
            self.affiliations : list[URIRef | BNode] = []
            self.identifiers : list[URIRef]  = []
            self.source : URIRef | None = None

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
        
        def add_affiliation(self, affiliation : URIRef | BNode):
            self.affiliations.append(affiliation)
            return self
        
        def add_identifier(self, identifier : URIRef):
            self.identifiers.append(identifier)
            return self
        
        def set_source(self, source : URIRef):
            self.source = source
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
    
    def affiliations(self) -> list[URIRef | BNode]:
        return self.builder.affiliations
    
    def identifiers(self) -> list[URIRef]:
        return self.builder.identifiers
    
    def source(self) -> URIRef | None:
        return self.builder.source
    
    def write(self, graph: Graph):
        super().write(graph)
        graph.add((self.uri(), RDF.type, FOAF.Person))
        graph.add((self.uri(), FOAF.firstName, Literal(self.first_name())))
        graph.add((self.uri(), FOAF.lastName, Literal(self.last_name())))
        for alternative in self.alternatives():
            graph.add((self.uri(), DCTERMS.alternative, Literal(alternative)))
        if self.orcid() is not None:
            if isinstance(self.orcid(), URIRef):
                graph.add((self.uri(), OWL.sameAs, self.orcid()))
            else:
                graph.add((self.uri(), LOCAL.orcid, Literal(self.orcid())))
        for affiliation in self.affiliations():
            graph.add((self.uri(), FOAF.member, affiliation))
        for identifier in self.identifiers():
            graph.add((self.uri(), ADMS.identifier, identifier))
        if self.source() is not None:
            graph.add((self.uri(), PAV.importedFrom, self.source()))

