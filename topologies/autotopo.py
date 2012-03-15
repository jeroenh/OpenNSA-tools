#!/usr/bin/env python
import rdflib

RDFS = rdflib.Namespace("http://www.w3.org/2000/01/rdf-schema#")

class AGTopology:
    def __init__(self, url):
        self.url = url
        self.store = rdflib.Graph()
        try:
            self.store.parse(url)
        except Exception as e:
            print e

class MasterTopology(object):
    def __init__(self, mastertopologyfile):
        super(MasterTopology, self).__init__()
        self.mastertopologyfile = mastertopologyfile
        self.store = rdflib.Graph()
        try:
            self.store.parse(mastertopologyfile)
        except Exception as e:
            print e
    def getSeeAlsoLinks(self):
        "Return all URIs that are the target of seeAlso links in this Topology."
        links = []
        for s,o in self.store.subject_objects(predicate=RDFS["seeAlso"]):
            links.append(o)
        return links

                
def mergeTopologies(masterFile):
    "Parse the masterfile and open all the separate topologies."
    m = MasterTopology(masterFile)
    g = rdflib.Graph()
    for l in m.getSeeAlsoLinks():
        g.parse(l,format='xml')
    print g.serialize()
    
def crawlTopology(startTopo):
    """
    Crawl all topologies and return the list of all locations and all connections between them.
        
    First we crawl through all rdfs:seeAlso links, gathering all the topologies.
    Then for each topology, we gather all Locations.
    For each Location, we get all the external connections, these are given as (Loc, Loc)
        
    Returns: (List of all Locations, List of all connections)"""
    alltops = startTopo.getAllTopologies()
    allLocs = []
    conList = []
    for top in alltops:
        for loc in top.getLocations():
            if loc not in allLocs:
                allLocs.append(loc)
            cons = top.getConnections()
            for con in cons:
                # Check if (a,b) or (b,a) is already in the list
                # Might be better to use a special object, but this works too
                if not conInConnectionList(con, conList):
                    conList.append(con)
    return allLocs, conList

def main():
    mergeTopologies("master.owl")
    
if __name__ == '__main__':
    main()
