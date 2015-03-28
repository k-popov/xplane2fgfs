#!/usr/bin/env python2

import sys
import requests
import base64
import zipfile
import StringIO

if len(sys.argv) < 2:
    sys.stderr.write("Usage: {0} <airport_ICAO_code>\n".format(sys.argv[0]))
    sys.exit(1)

ap_icao = str(sys.argv[1])

ap_request = "http://gateway.x-plane.com/apiv1/airport/{0}".format(ap_icao)
ap_json = requests.get(ap_request).json()

sc_id = ap_json['airport'].get('recommendedSceneryId', None)
if not sc_id:
    sys.stderr.write(
        "Airport {0} has no recommendedSceneryId\n".format(ap_icao))
    sys.exit(1)

sc_request = "http://gateway.x-plane.com/apiv1/scenery/{0}".format(sc_id)
sc_json = requests.get(sc_request).json()
ap_zip_stringio = StringIO.StringIO(
    base64.b64decode(sc_json['scenery']['masterZipBlob']))

with zipfile.ZipFile(ap_zip_stringio, 'r') as ap_zip:
    sys.stdout.write(
        ap_zip.open("{0}.dat".format(ap_icao)).read()
        )

sys.exit(0)
