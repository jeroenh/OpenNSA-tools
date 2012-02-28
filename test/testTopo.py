#!/usr/bin/env python
import opennsa.topology
import opennsa.setup

from twisted.internet import reactor, defer
import socket
import os

TOPOLOGY_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "../topologies/AutoGOLE-Topo.owl")
WSDL_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), '../wsdl')
PORT = 9081
class TestTopo():
    def __init__(self):
        self.topo = opennsa.topology.parseTopology([open(TOPOLOGY_FILE)])
        self.nsas = self.getNSAs()
        self.index = 0
        self.maxIndex = len(self.nsas)
        self.client,self.client_nsa = createClient()
        
    def getNSAs(self):
        result = []
        for net in self.topo.networks:
                result.append(net.nsa)
        return result
    @defer.inlineCallbacks
    def doQueries(self):
        for x in range(len(self.nsas)):
            print "doing query %s" % x
            self.doQuery(x)
        
    @defer.inlineCallbacks
    def doQuery(self, index):
        nsa = self.nsas[index]
        client, client_nsa = createClient(index)
        print "Querying %s for %s" % (nsa,None)
        qr = yield client.query(client_nsa, nsa, None, "Summary", connection_ids = [] )
        # if hasattr(qr,"reservationSummary"):
        #     for res in qr.reservationSummary:
        #         print "global-reservation-id: " + str(res.globalReservationId)
        #         if hasattr(res,"description"):
        #             print "description: " + str(res.description)
        #         print "schedule: %s -- %s" % (res.serviceParameters.schedule.startTime, res.serviceParameters.schedule.endTime)
        #         print "bandwidth: " + str(res.serviceParameters.bandwidth.desired)
        #         print "status: " + str(res.connectionState)
        #         if hasattr(res,"path"):
        #             if hasattr(res.path,"stpList"):
        #                 print "stplist: %s" % (res.path.stpList.stp)
        #             else:
        #                 print "stpList: " + str([res.path.sourceSTP.stpId,res.path.destSTP.stpId]) 
        #         print "Typeinfo: %s" % (type(res.serviceParameters.schedule.startTime))
        # else:
        print qr

def createClient(index=0):
    print "Creating client %s" % index
    # Constructing the client NSA
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    s.connect(("gmail.com",80))
    host = s.getsockname()[0]
    s.close()
    port = PORT+index
    client, factory = opennsa.setup.createClient(host, port, WSDL_DIR)
    client_nsa = opennsa.nsa.NetworkServiceAgent('OpenNSA-commandline', 'http://%s:%s/NSI/services/ConnectionService' % (host,port))
    reactor.listenTCP(port, factory)
    return client,client_nsa

def runDefer(d):
    def handleError(x):
        x.printTraceback()
    d.addErrback(handleError)
    d.addCallback(lambda _: reactor.stop())
    reactor.run()

def main():
    t = TestTopo()
    d = defer.maybeDeferred(t.doQueries)
    runDefer(d)
    

if __name__ == '__main__':
    main()
    
