#!/usr/bin/env python

# from optparse import OptionParser
from twisted.internet import reactor, defer, task
import uuid
import random
import os.path
import socket
import datetime
import time
import sys
import urllib
import random
import logging
import exceptions

import topology
import opennsa.setup
import opennsa.nsa
import opennsa.cli.commands
import opennsa.error

SCHEDULE = [
            (("aist.ets","ps-80"),("aist.ets","tok-80"),"aist.ets"),
            (("czechlight.ets","ps-80"),("czechlight.ets","ams-80"),"czechlight.ets"),
            (("esnet.ets","ps-80"),("esnet.ets","chi-80"),"esnet.ets"),
            (("geant.ets","ps-80"),("geant.ets","poz-80"),"geant.ets"),
            (("gloriad.ets","ps-80-chi"),("gloriad.ets","sl.0"),"gloriad.ets"),
            (("jgnx.ets","ps-80"),("jgnx.ets","chi-80"),"jgnx.ets"),
            (("kddi-labs.ets","ps-80"),("kddi-labs.ets","tok-80"),"kddi-labs.ets"),
            (("krlight.ets","ps-80"),("krlight.ets","glo-80"),"krlight.ets"),
            (("netherlight.ets","ps-80"),("netherlight.ets","cph-80"),"netherlight.ets"),
            (("northernlight.ets","ps-80"),("northernlight.ets","ams-80"),"northernlight.ets"),
            (("pionier.ets","ps-80"),("pionier.ets","ams-80"),"pionier.ets"),
            (("starlight.ets","ps-80"),("starlight.ets","ams-80"),"starlight.ets"),
            (("uvalight.ets","ps-80"),("uvalight.ets","ams-80"),"uvalight.ets"),
           ]

TOPOLOGY_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)),"../topologies/AutoGOLE-Topo.owl")
WSDL_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), '../wsdl')
NO_DEFERS = len(SCHEDULE)

def handleAttributeError(failure):
    e = failure.trap(exceptions.AttributeError)
    # print e.message

class Tester(object):
    def __init__(self,reservation,port):
        self.topo = topology.parseGOLERDFTopology(TOPOLOGY_FILE)

        self.counter = 201
        self.index = 0
        self.connection_id = None
        self.provider_nsa = None
        self.reservation = reservation
        self.nsa = reservation[-1]
        self.port = port
        if reservation[2] == "northernlight.ets":
            self.createSSLClient()
        else:
            self.createClient()
        self.setupLogging()
        self.startTime = datetime.datetime.now()

    def setupLogging(self):
        logging.basicConfig(filename="scheduler.log", format='%(asctime)-15s %(message)s')
        self.logger = logging.getLogger("scheduler")
        self.logger.setLevel(10)
    def getTimeDiff(self):
        return datetime.datetime.now() - self.startTime

    @defer.inlineCallbacks
    def doReserveTest(self):
        
        # reservation = options.reserve
        srcNet = self.topo.getNetwork(self.reservation[0][0])
        srcSTP = srcNet.getEndpoint(self.reservation[0][1])
        dstNet = self.topo.getNetwork(self.reservation[1][0])
        dstSTP = dstNet.getEndpoint(self.reservation[1][1])
        provider_nsa = self.topo.getNetwork(self.reservation[2]).nsa
        # Setting some defaults for now, to fill in later
        start_time=None
        end_time=None
        description='Scheduled Connection'
        # Constructing the ServiceParamaters
        if not start_time:
            start_time = datetime.datetime.utcfromtimestamp(time.time() + 60 ) # one minutes from now
        if not end_time:
            end_time   = start_time + datetime.timedelta(minutes=3)
        global_reservation_id = 'uva-scheduler:gid-%s' % uuid.uuid1()
        self.counter += 1
        connection_id = "urn:uuid:%s" % uuid.uuid1()
        bwp = opennsa.nsa.BandwidthParameters(200)
        service_params  = opennsa.nsa.ServiceParameters(start_time, end_time, srcSTP, dstSTP, bandwidth=bwp)
        # Send the reservation and wait for response
        self.reservationDescr = "Reservation %s: (%s,%s) to (%s,%s) at %s (%s)" % (global_reservation_id, srcNet.name,srcSTP.endpoint,dstNet.name,dstSTP.endpoint, provider_nsa.identity,provider_nsa.url().strip())
        # print self.reservationDescr
        try:
            r = yield self.client.reserve(self.client_nsa, provider_nsa, None, global_reservation_id, description, connection_id, service_params)
        except opennsa.error.ReserveError, e:
            print "%s is failing (%s) [%s]" % (self.nsa, e,self.getTimeDiff())
            self.logger.info("Reserving %s" % self.reservationDescr)
            self.logger.info("ReserveError at %s: %s" % (self.nsa, e))
            return
        if r:
            # print "Terminating %s at %s" % (connection_id, provider_nsa)
            try:
                qr = yield self.client.terminate(self.client_nsa, provider_nsa, None , connection_id =  connection_id )
                print "%s is operational [%s]" % (self.nsa,self.getTimeDiff())
            except opennsa.error.TerminateError, e:
                print "%s is failing (%s) [%s]" % (self.nsa, e,self.getTimeDiff())
                self.logger.info("Terminating %s" % self.reservationDescr)
                self.logger.info("TerminateError at %s: %s" % (self.nsa,e))
        else:
            print "Reservation failed at %s." % self.nsa


        
    def createClient(self):
        # Constructing the client NSA
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("gmail.com",80))
        host = s.getsockname()[0]
        s.close()
        self.client, factory = opennsa.setup.createClient(host, self.port, WSDL_DIR)
        self.client_nsa = opennsa.nsa.NetworkServiceAgent('AutoScheduler', 'http://%s:%s/NSI/services/ConnectionService' % (host,self.port))
        reactor.listenTCP(self.port, factory)
        # return client,client_nsa

    def createSSLClient(self):
        # Constructing the client NSA
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("gmail.com",80))
        host = s.getsockname()[0]
        s.close()
        from opennsa import ctxfactory
        ctx_factory = ctxfactory.ContextFactory("./server.key", "./server.crt", ".", verify=False)
        self.client, factory = opennsa.setup.createClient(host, self.port, WSDL_DIR,True, ctx_factory)
        self.client_nsa = opennsa.nsa.NetworkServiceAgent('AutoScheduler', 'http://%s:%s/NSI/services/ConnectionService' % (host,self.port))
        reactor.listenSSL(self.port, factory, ctx_factory)
        # return client,client_nsa
        

def testDefers():
    global NO_DEFERS
    if NO_DEFERS <= 0:
        reactor.stop()
    else:
        # print "Still running %s defers" % NO_DEFERS
        reactor.callLater(1, testDefers)
        

def removeDefer():
    global NO_DEFERS
    NO_DEFERS -= 1
    
def runDefer(d):
    def handleError(x):
        x.printTraceback()
    d.addErrback(handleError)
    d.addCallback(lambda _: removeDefer())

def main():
    PORT = 7080
    for res in SCHEDULE:
        # print res
        s = Tester(res,PORT)
        d = defer.maybeDeferred(s.doReserveTest)
        runDefer(d)
        PORT += 1
    defer.maybeDeferred(testDefers)
    reactor.run()

if __name__ == '__main__':
    main()
