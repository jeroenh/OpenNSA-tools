import web
import json
import datetime
import time
import uuid
from mimerender import mimerender

render_xml = lambda result: "<result>%s</result>"%result
render_json = lambda **result: json.dumps(result,sort_keys=True,indent=4)
render_html = lambda result: "<html><body>%s</body></html>"%result
render_txt = lambda result: result



class Registrations(object):
    def __init__(self):
        self.registrations = []
        self.restoreRegistrations()
    def register(self, res_id, nsa_id):
        if res_id and nsa_id:
            self.registrations.append((res_id,nsa_id))
            self.writeOut()
    def unregister(self,res_id,nsa_id):
        if not nsa_id:
            for resnsa in self.registrations[:]:
                if res_id == resnsa[0]:
                    print "Unregistering (%s,%s) from %s" % (res_id,resnsa[1], self.registrations)
                    self.registrations.remove(resnsa)
            self.writeOut()
        else:
            for resnsa in self.registrations[:]:
                if res_id == resnsa[0] and nsa_id == resnsa[1]:
                    self.registrations.remove(resnsa)
            self.writeOut()
    def getRegistrations(self):
        return self.registrations[:]
    def restoreRegistrations(self):
        try:
            self.registrations = json.load(open("reservationIDs.json",'r'))
        except ValueError:
            pass
    def writeOut(self):
        json.dump(self.registrations,open("reservationIDs.json",'w'))

urls = (
    "/(.*)", "querier"
)
REGS = Registrations()
app = web.application(urls, globals())

class querier:
    @mimerender(
        default = "json",
        # html = render_html,
        html = render_json,
        xml  = render_xml,
        json = render_json,
        txt  = render_txt
    )
    def GET(self,name):
        if name == "register":
            webin =  web.input(urn=None,nsa=None)
            REGS.register(webin.urn,webin.nsa)
            # self.register(webin.urn,web_in.nsa)
            result = {"result":"Hello, world!"}
            return result
        elif name == "unregister":
            webin =  web.input(urn=None,nsa=None)
            REGS.unregister(webin.urn,webin.nsa)
            # self.register(webin.urn,web_in.nsa)
            result = {"result":"Hello, world!"}
            return result            
        elif name == "query":
            return doQuery()
        elif name == "registrations":
            return {"result": REGS.getRegistrations()}
        else:
            return {"result":"Hello world!"}
    def POST(self,name):
        if name == "register":
            webin = web.input()
            REGS.register(webin.urn,webin.nsa)
            # return REGS.getRegistrations()
        elif name == "unregister":
            webin =  web.input()
            REGS.unregister(webin.urn,webin.nsa)

def doQuery():
    res = json.loads(file("reservations.json").read())
    return {"result":res}

    

if __name__ == "__main__":
    app.run()
