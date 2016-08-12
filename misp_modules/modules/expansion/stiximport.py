import json
import stix
import csv
from stix.core import STIXPackage
import re
import base64
import hashlib

misperrors = {'error': 'Error'}
userConfig = {}
inputSource = ['file']

moduleinfo = {'version': '0.1', 'author': 'Hannah Ward',
              'description': 'Import some stix stuff',
              'module-type': ['import']}

moduleconfig = []


def handler(q=False):
    #Just in case we have no data
    if q is False:
        return False

    #The return value 
    r = {'results': []}

    #Load up that JSON
    q = json.loads(q)

    #It's b64 encoded, so decode that stuff
    package = str(base64.b64decode(q.get("data", None)), 'utf-8')
     
    #If something really weird happened
    if not package:
      return json.dumps({"success":0})

    #Load up the package into STIX
    package = loadPackage(package)

    #Build all the observables
    if package.observables:
      for obs in package.observables:
        r["results"].append(buildObservable(obs))

    if package.threat_actors:
      for ta in package.threat_actors:
        r["results"].append(buildActor(ta))      
    
    if package.indicators:
      for ind in package.indicators:
        r["results"].append(buildIndicator(ind))

    if package.exploit_targets:
      for et in package.exploit_targets:
        r["results"].append(buildExploitTarget(et))

    if package.campaigns:
      for cpn in package.campaigns:
        r["results"].append(buildCampaign(cpn))
    #Clean up results
    #Don't send on anything that didn't have a value
    r["results"] = [x for x in r["results"] if len(x["values"]) != 0]
    return r

#Quick and dirty regex for IP addresses
ipre = re.compile("([0-9]{1,3}.){3}[0-9]{1,3}")

def buildCampaign(cpn):
  """
    Extract a campaign name
  """
  
  return {"values":[cpn.title], "types":["campaign-name"]}

def buildExploitTarget(et):
  """
    Extract CVEs from exploit targets
  """

  r = {"values":[], "types":["vulnerability"]}

  if et.vulnerabilities:
    for v in et.vulnerabilities:
      if v.cve_id:
        r["values"].append(v.cve_id)

  return r

def identifyHash(hsh):
  """
    What's that hash!?
  """

  possible_hashes = []

  hashes = [x for x in hashlib.algorithms_guaranteed]

  for h in hashes:
    if len(str(hsh)) == len(hashlib.new(h).hexdigest()):
      possible_hashes.append(h)
      possible_hashes.append("filename|{}".format(h))
 
  return possible_hashes

def buildIndicator(ind):
  """
    Extract hashes
    and other fun things
    like that
   """
  r = {"values":[], "types":[]}

  #Try to get hashes. I hate stix
  if ind.observable:
    return buildObservable(ind.observable)
  return r
    
def buildActor(ta):
  """
    Extract the name
    and comment of a 
    threat actor
  """
  
  r = {"values":[ta.title], "types":["threat-actor"]}
 
  return r

def buildObservable(o):
  """
    Take a STIX observable
    and extract the value
    and category
  """

  #Life is easier with json
  o = json.loads(o.to_json())
   
  #Make a new record to store values in
  r = {"values":[]}

  #Get the object properties. This contains all the
  #fun stuff like values
  props = o["object"]["properties"]

  #If it has an address_value field, it's gonna be an address
  print(props)
  #Kinda obvious really
  if "address_value" in props:
    
    #We've got ourselves a nice little address
    value = props["address_value"]

    if isinstance(value, dict):
      #Sometimes it's embedded in a dictionary
      value = value["value"]

    #Is it an IP?
    if ipre.match(str(value)):

      #Yes!
      r["values"].append(value)
      r["types"] = ["ip-src", "ip-dst"]
    else:

      #Probably a domain yo
      r["values"].append(value)
      r["types"] = ["domain", "hostname"]

  if "hashes" in props:
    for hsh in props["hashes"]:
      r["values"].append(hsh["simple_hash_value"]["value"])
      r["types"] = identifyHash(hsh["simple_hash_value"]["value"])
  return r

def loadPackage(data):
  #Write the stix package to a tmp file
  with open("/tmp/stixdump", "w") as f:
    f.write(data)
  try:
    #Try loading it into every format we know of
    try:
      package = STIXPackage().from_xml(open("/tmp/stixdump", "r"))
    except:  
      package = STIXPackage().from_json(open("/tmp/stixdump", "r"))
  except Exception as ex:
    print("Failed to load package")
    raise ValueError("COULD NOT LOAD STIX PACKAGE!")
  return package

def introspection():
    modulesetup = {}
    try:
        userConfig
        modulesetup['userConfig'] = userConfig
    except NameError:
        pass
    try:
        inputSource
        modulesetup['inputSource'] = inputSource
    except NameError:
        pass
    return modulesetup


def version():
    moduleinfo['config'] = moduleconfig
    return moduleinfo
