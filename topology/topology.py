"""
OpenNSA topology database and parser.

Author: Henrik Thostrup Jensen <htj@nordu.net>
		Jeroen van der Ham <vdham@uva.nl>

Copyright: NORDUnet (2011)
"""

import rdflib
from opennsa import nsa, error


# Constants for parsing GOLE topology format
OWL_NS  = 'http://www.w3.org/2002/07/owl#'
RDF_NS  = 'http://www.w3.org/1999/02/22-rdf-syntax-ns#'

GLIF_PREFIX = 'http://www.glif.is/working-groups/tech/dtox#'



class Topology:

    def __init__(self):
        self.networks = []
        self.stps = {}

    def addSTP(self,urn,stp):
        self.stps[urn] = stp
        
    def addNetwork(self, network):
        # network is of type nsa.Network
        if network.name in [ n.name for n in self.networks ]:
            raise error.TopologyError('Network name must be unique (name: %s)' % network.name)

        self.networks.append(network)


    def getNetwork(self, network_name):
        for network in self.networks:
            if network.name == network_name:
                return network

        raise error.TopologyError('No network named %s' % network_name)


    def getEndpoint(self, network, endpoint):

        nw = self.getNetwork(network)
        for ep in nw.endpoints:
            if ep.endpoint == endpoint:
                return ep
    def getSTP(self,urn):
        return self.stps[urn]
        
    def convertSDPRouteToLinks(self, source_ep, dest_ep, route):

        nl_route = []
        prev_source_ep = source_ep

        for sdp in route:
            nl_route.append( nsa.Link(prev_source_ep, sdp.stp1) )
            prev_source_ep = sdp.stp2
        # last hop
        nl_route.append( nsa.Link(prev_source_ep, dest_ep) )

        return nl_route


    def findPaths(self, source_stp, dest_stp, bandwidth=None):
        """
        Find possible paths between two endpoints.
        """
        # check that STPs exist
        snw = self.getNetwork(source_stp.network)
        sep = snw.getEndpoint(source_stp.endpoint)

        dnw = self.getNetwork(dest_stp.network)
        dep = dnw.getEndpoint(dest_stp.endpoint)

        # find endpoint pairs
        #print "FIND PATH", source_stp, dest_stp

        if snw == dnw:
            # same network, make direct connection and nothing else
            routes = [ [] ]
        else:
            routes = self.findPathEndpoints(source_stp, dest_stp)

        if bandwidth is not None:
            routes = self.filterBandwidth(routes, bandwidth)

        network_paths = [ self.convertSDPRouteToLinks(sep, dep, route) for route in routes ]

        # topology cannot represent vlans properly yet
        # this means that all ports can be matched with all ports internally in a network
        # this is incorrect if the network does not support vlan rewriting
        # currently only netherlight supports vlan rewriting (nov. 2011)
        network_paths = self._pruneMismatchedPorts(network_paths)

        paths = [ nsa.Path(np) for np in network_paths ]

        return paths



    def _pruneMismatchedPorts(self, network_paths):

        valid_routes = []

        for np in network_paths:

            for link in np:
                if not link.stp1.network.endswith('.ets'):
                    continue # not a vlan capable network, STPs can connect
                source_vlan = link.stp1.endpoint.split('-')[-1]
                dest_vlan   = link.stp2.endpoint.split('-')[-1]
                if source_vlan == dest_vlan or link.stp1.network in ('netherlight.ets'):
                    continue # STPs can connect
                else:
                    break

            else: # only choosen if no break occurs in the loop
                valid_routes.append(np)

        return valid_routes



    def findPathEndpoints(self, source_stp, dest_stp, visited_networks=None):

        #print "FIND PATH EPS", source_stp, visited_networks

        snw = self.getNetwork(source_stp.network)
        routes = []

        for ep in snw.endpoints:

            #print "  Path:", ep, " ", dest_stp

            if ep.dest_stp is None:
                #print "    Rejecting endpoint due to no pairing"
                continue

            if visited_networks is None:
                visited_networks = [ source_stp.network ]

            if ep.dest_stp.network in visited_networks:
                #print "    Rejecting endpoint due to loop"
                continue

            if ep.dest_stp.network == dest_stp.network:
                dest_ep = self.getEndpoint(ep.dest_stp.network, ep.dest_stp.endpoint)
                sp = nsa.SDP(ep, dest_ep)
                routes.append( [ sp ] )
            else:
                nvn = visited_networks[:] + [ ep.dest_stp.network ]
                subroutes = self.findPathEndpoints(ep.dest_stp, dest_stp, nvn)
                if subroutes:
                    for sr in subroutes:
                        src = sr[:]
                        dest_ep = self.getEndpoint(ep.dest_stp.network, ep.dest_stp.endpoint)
                        sp = nsa.SDP(ep, dest_ep)
                        src.insert(0, sp)
                        routes.append(  src  )

        return routes


    def filterBandwidth(self, paths_sdps, bandwidths):

        def hasBandwidth(route, bandwidths):
            for sdp in route:
                if sdp.stp1.available_capacity is not None and bandwidths.minimum is not None and sdp.stp1.available_capacity < bandwidths.minimum:
                    return False
                if sdp.stp2.available_capacity is not None and bandwidths.minimum is not None and sdp.stp2.available_capacity < bandwidths.minimum:
                    return False
            return True

        filtered_routes = [ route for route in paths_sdps if hasBandwidth(route, bandwidths) ]
        return filtered_routes


    def __str__(self):
        return '\n'.join( [ str(n) for n in self.networks ] )


def parseGOLERDFTopology(topology_source):
    def stripURNPrefix(text):
        URN_PREFIX = 'urn:ogf:network:'
        assert text.startswith(URN_PREFIX)
        return text.split(':')[-1]

    OWL_NS = rdflib.namespace.Namespace("http://www.w3.org/2002/07/owl#")
    RDF_NS = rdflib.namespace.Namespace('http://www.w3.org/1999/02/22-rdf-syntax-ns#')
    DTOX_NS = rdflib.namespace.Namespace('http://www.glif.is/working-groups/tech/dtox#')

    graph = rdflib.Graph()
    # TODO: Change this to some configurable option.
    # graph.open("/Users/jeroen/Projects/OpenNSA-UvA/opennsa/rdfdb")
    try:
        graph.parse(topology_source)
    except:
        raise error.TopologyError('Invalid topology source')

    topo = Topology()
    topo.graph = graph

    for nsnetwork in graph.subjects(RDF_NS['type'],DTOX_NS['NSNetwork']):
        # Setup the base network object, with NSA
        nsaId = graph.value(subject=nsnetwork, predicate=DTOX_NS['managedBy'])
        network_name = stripURNPrefix(str(nsnetwork))
        network_nsa_ep = graph.value(subject=nsaId, predicate=DTOX_NS['csProviderEndpoint'])
        network_nsa = nsa.NetworkServiceAgent(stripURNPrefix(str(nsaId)), str(network_nsa_ep))
        network = nsa.Network(network_name, network_nsa)
        loc = graph.value(subject=nsnetwork, predicate=DTOX_NS["locatedAt"])
        network.location = (graph.value(subject=loc,predicate=DTOX_NS["lat"]),
                            graph.value(subject=loc,predicate=DTOX_NS["long"]))

        # Add all the STPs and connections to the network
        for stp in graph.objects(nsnetwork, DTOX_NS['hasSTP']):
            stp_name = stripURNPrefix(str(stp))
            dest_stp = graph.value(subject=stp, predicate=DTOX_NS['connectedTo'])
            # If there is a destination, add that, otherwise the value stays None.
            if dest_stp:
                dest_network = graph.value(predicate=DTOX_NS['hasSTP'], object=dest_stp)
                dest_stp = nsa.STP(stripURNPrefix(str(dest_network)), stripURNPrefix(str(dest_stp)))
            ep = nsa.NetworkEndpoint(network_name, stp_name, None, dest_stp, None, None)
            network.addEndpoint(ep)
            topo.addSTP(str(stp),ep)

        topo.addNetwork(network)

    return topo
