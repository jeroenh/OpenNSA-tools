#!/usr/bin/env python

import opennsa.topology
# import os
import re

topo = opennsa.topology.parseGOLERDFTopology("SC2011-Topo-v5f.owl")

wsstringlist = []
for net in topo:
    print '"%s": "%s",' % (net.nsa.identity, net.nsa.url())
    wsstringlist.append(re.search("http://(.*):.*",net.nsa.url()).group(1))

print 80*"-"
print "host "+ " or host ".join(wsstringlist)

print 80*"-"
for net in topo:
    print net.location
    for ep in net.getEndpoints():
        print "nsa.STP('%s','%s')" % (net.name,ep)
    print 80*"-"

# print '<?xml version="1.0" encoding="UTF-8"?>\n<tns:nsaConfigurationList xmlns:tns="http://schemas.opendrac.org/nsi/2011/09/nsaConfiguration"\n     xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance">'
# for net in topo:
#     print "<nsaConfiguration>"
#     print "\t<nsaIdentifier>%s</nsaIdentifier>" % net.nsa.urn()
#     print "\t<label>%s</label>" % net.nsa.identity
#     print "\t<nsNetwork>urn:ogf:network:nsnetwork:%s</nsNetwork>" % net.name
#     print "\t<adminContact>See OWL file</adminContact>"
#     print "\t<connectedTo>TODO</connectedTo>"
#     print "\t<endpoints>"
#     print "\t\t<csProviderEndpoint>%s</csProviderEndpoint>" % net.nsa.url()
#     print "\t\t<csRequesterEndpoint>%s</csRequesterEndpoint>" % net.nsa.url()
#     print "\t<endpoints>"
#     print "\t<authentication>"
#     print "\t\t<userId>nsidemo</userId>"
#     print "\t\t<password>RioPlug-Fest2011!</password>"
#     print "\t</authentication>"
#     print "</nsaConfiguration>"
# print "</tns:nsaConfigurationList>"
#     # 
    # <nsaConfiguration>
    #         <nsaIdentifier>urn:ogf:network:nsa:Aruba-OpenNSA</nsaIdentifier>
    #         <label>OpenNSA (NORDUnet)</label>
    #         <nsNetwork>urn:ogf:network:nsnetwork:Aruba</nsNetwork>
    #         <adminContact>6. OpenNSA (NORDUnet) 6.1.  Implementation name: OpenNSA 6.2.   Project manager:     name: Jerry Sobieski email: jerry@nordu.net mobile:  1-301-346-1849 skype: jerry.sobieski 6.3. Key software engineer: name: Henrik Thostrup-Jensen email: htj@nordu.net skype: henrik.thostrup.jensen</adminContact>
    #         <connectedTo>urn:ogf:network:nsa:Martinique-DynamicKL</connectedTo>
    #         <connectedTo>urn:ogf:network:nsa:Bonaire-OpenDRAC</connectedTo>
    #         <endpoints>
    #             <csProviderEndpoint>http://orval.grid.aau.dk:9080/NSI/services/ConnectionService</csProviderEndpoint>
    #             <csRequesterEndpoint>http://orval.grid.aau.dk:9080/NSI/services/ConnectionService</csRequesterEndpoint>
    #         </endpoints>
    #         <authentication>
    #             <userId>nsidemo</userId>
    #             <password>RioPlug-Fest2011!</password>
    #         </authentication>
    #     </nsaConfiguration>

# src = topo.getEndpoint("starlight.ets","ams-81")
# dst = topo.getEndpoint("aist.ets","ps-81")
# paths.sort(key=lambda e : len(e.endpoint_pairs))
# 
# selected_path = topo.findPaths(src,dst)[0]
# print selected_path
# prev_source_stp = selected_path.source_stp
# 
# for stp_pair in selected_path.endpoint_pairs:
#     print "setting up conn between %s and %s" % (prev_source_stp.urn(),stp_pair.stp1.urn())
#     #setupSubConnection(prev_source_stp, stp_pair.stp1, conn, service_parameters)
#     prev_source_stp = stp_pair.stp2
# # last hop
# # setupSubConnection(prev_source_stp, selected_path.dest_stp, conn, service_parameters)
# print "setting up conn between %s and %s" % (prev_source_stp.urn(),selected_path.dest_stp.urn())
