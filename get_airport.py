#!/usr/bin/env python 

import sys
import requests
import base64
import zipfile
import os

if len(sys.argv) < 2:
    print("Usage: {0} <airport_ICAO_code>".format(sys.argv[0]))
    sys.exit(1)

ap_icao = str(sys.argv[1])

ap_request = "http://gateway.x-plane.com/apiv1/airport/{0}".format(ap_icao)
ap_json = requests.get(ap_request).json()

sc_id = ap_json['airport'].get('recommendedSceneryId', None)
if not sc_id:
    print("Airport {0} has no recommendedSceneryId".format(ap_icao))
    sys.exit(1)

sc_request = "http://gateway.x-plane.com/apiv1/scenery/{0}".format(sc_id)
sc_json = requests.get(sc_request).json()
ap_zip_file_name = "{0}.zip".format(ap_icao)
with open(ap_zip_file_name, 'w') as ap_zip_file:
    ap_zip_file.write(base64.b64decode(sc_json['scenery']['masterZipBlob']))

with zipfile.ZipFile(ap_zip_file_name, 'r') as ap_zip:
    ap_zip.extract("{0}.dat".format(ap_icao))

os.remove(ap_zip_file_name)

sys.exit(0)
