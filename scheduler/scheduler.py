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

import topology
import opennsa.setup
import opennsa.nsa
import opennsa.cli.commands

SCHEDULE = [
             (("aist.ets","ps-83"),("starlight.ets","ps-83"),"starlight.ets"),
             (("geant.ets","ps-83"), ("kddi-labs.ets","ps-83"),"aist.ets"),
            (("starlight.ets","ps-83"),("uvalight.ets","ps-83"),"starlight.ets"),
            (("uvalight.ets","ps-83"),("krlight.ets","ps-83"),"starlight.ets"),
             (("uvalight.ets","ps-83"),("kddi-labs.ets","ps-83"),"starlight.ets"),
            (("uvalight.ets","ps-83"),("northernlight.ets","ps-83"),"uvalight.ets"),
             (("aist.ets","ps-83"),("northernlight.ets","ps-83"),"aist.ets"),
           (("uvalight.ets","ps-83"),("czechlight.ets","ps-83"),"aist.ets"),
            (("starlight.ets","ps-83"),("geant.ets","ps-83"),"starlight.ets"),
           ]

TOPOLOGY_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)),"../topologies/AutoGOLE-Topo.owl")
WSDL_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), '../wsdl')
PORT = 6080

class Scheduler(object):
    def __init__(self,schedule,port):
        self.topo = topology.parseGOLERDFTopology(TOPOLOGY_FILE)

        self.counter = 201
        self.index = 0
        self.connection_id = None
        self.provider_nsa = None
        self.schedule = schedule
        self.port = port
        self.createClient()
        self.setupLogging()

    def runSchedule(self):
        res = random.choice(self.schedule)
        # reserve adds callLater for Provision, which callLaters Terminate
        reactor.callLater(0,self.doReserve,res)
    
    def setupLogging(self):
        logging.basicConfig(filename="scheduler.log", format='%(asctime)-15s %(message)s')
        self.logger = logging.getLogger("scheduler")
        self.logger.setLevel(10)

    @defer.inlineCallbacks
    def doReserve(self,reservation):
        # reservation = options.reserve
        srcNet = self.topo.getNetwork(reservation[0][0])
        srcSTP = srcNet.getEndpoint(reservation[0][1])
        dstNet = self.topo.getNetwork(reservation[1][0])
        dstSTP = dstNet.getEndpoint(reservation[1][1])
        provider_nsa = self.topo.getNetwork(reservation[2]).nsa
        # Setting some defaults for now, to fill in later
        start_time=None
        end_time=None
        description='Scheduled Connection'
        # Constructing the ServiceParamaters
        if not start_time:
            start_time = datetime.datetime.utcfromtimestamp(time.time() + 60 ) # one minutes from now
        if not end_time:
            end_time   = start_time + datetime.timedelta(minutes=3)
        global_reservation_id = 'uva-scheduler:gid-%s' % self.counter
        self.counter += 1
        connection_id = "urn:uuid:%s" % uuid.uuid1()
        bwp = opennsa.nsa.BandwidthParameters(200)
        service_params  = opennsa.nsa.ServiceParameters(start_time, end_time, srcSTP, dstSTP, bandwidth=bwp)
        # Send the reservation and wait for response
        print "Reserving (%s,%s) to (%s,%s) at %s (%s)" % (srcNet.name,srcSTP.endpoint,dstNet.name,dstSTP.endpoint, provider_nsa.identity,provider_nsa.url().strip())
        try:
            r = yield self.client.reserve(self.client_nsa, provider_nsa, None, global_reservation_id, description, connection_id, service_params)
        except opennsa.error.ReserveError, e:
            print "Failure: %s" % e 
            self.logger.info("Reserving (%s,%s) to (%s,%s) at %s (%s)" % (srcNet.name,srcSTP.endpoint,dstNet.name,dstSTP.endpoint, provider_nsa.identity,provider_nsa.url().strip()))
            self.logger.info("ReserveError: %s" % e)
            return
        if r:
            print "Reservation created.\nReservation ID: %s\nConnection ID: %s" % (global_reservation_id,connection_id)
            urllib.urlopen("http://rembrandt0.uva.netherlight.nl:8080/register",
                urllib.urlencode({"urn": global_reservation_id,"nsa": provider_nsa.urn()}))
            reactor.callLater(60, self.doProvision, provider_nsa, connection_id)
            unregister_time = (end_time - datetime.datetime.utcnow()).total_seconds()
            reactor.callLater(unregister_time, self.doUnregister, global_reservation_id, provider_nsa.urn())
        else:
            print "Reservation failed."

    @defer.inlineCallbacks
    def doProvision(self,provider_nsa,connection_id):
        if connection_id:
            print "Provisioning %s at %s" % (connection_id, provider_nsa)
            qr = yield self.client.provision(self.client_nsa, provider_nsa, None , connection_id =  connection_id )
            reactor.callLater(100, self.doTerminate, provider_nsa, connection_id)
        else:
            print "Reservation failed, skipping provision."
            
    @defer.inlineCallbacks
    def doTerminate(self, provider_nsa, connection_id):
        if connection_id:
            print "Terminating %s at %s" % (connection_id, provider_nsa)
            qr = yield self.client.terminate(self.client_nsa, provider_nsa, None , connection_id =  connection_id )
        else:
            print "Reservation failed, skipping termination."

    @defer.inlineCallbacks
    def doUnregister(self, global_reservation_id, provider_nsa):
        print "Unregistering reservation ID: %s" % (global_reservation_id)
        urllib.urlopen("http://rembrandt0.uva.netherlight.nl:8080/unregister",
            urllib.urlencode({"urn": global_reservation_id,"nsa": provider_nsa}))
        
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

def main():
    def handleError(x):
        x.printTraceback()
        reactor.stop()
    s = Scheduler(SCHEDULE,PORT)
    l = task.LoopingCall(s.runSchedule)
    l.start(200.0) # call every four minutes

    reactor.run()

if __name__ == '__main__':
    main()
