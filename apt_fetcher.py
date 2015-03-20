#!/usr/bin/env python

import logging
import requests
import simplejson
import StringIO
import base64
import zipfile

def get_airport_apt(scenery_id=None,
                    api_base="http://gateway.x-plane.com/apiv1/"):
    """ Gets scenery pack via X-Plane gateway API, unpacks it
        and returns the requested airport in apt format
    """

    if not (scenery_id and type(scenery_id) is int):
        raise Exception("Invalid scenery_id passed: {0}".format(scenery_id))

    scenery_request = api_base + "scenery/{0}".format(scenery_id)
    logging.debug("Getting scenery from %s", scenery_request)
    scenery_reply = requests.get(scenery_request)
    if scenery_reply.status_code != 200:
        logging.error("Failed to receive scenery %s. Code %s",
                      scenery_id, scenery_reply.status_code)
        return None
    logging.debug("Converting reply from %sinto dict", scenery_request)
    try:
        scenery_json = scenery_reply.json()
    except simplejson.scanner.JSONDecodeError:
        logging.error("Reply from %s is not a valid JSON", scenery_request)
        return None

    scenery_blob = scenery_json.get('scenery', {}).get('masterZipBlob', None)
    if not scenery_blob:
        logging.error("Scenery JSON has no airport data")
        return None
    airport_icao = scenery_json.get('scenery', {}).get('icao', None)
    if not airport_icao:
        logging.error("Scenery JSON has no airport ICAO code")
        return None

    logging.debug("Decoding apt data for %s from base64 into zip",
                  airport_icao)
    scenery_zip_stringio = StringIO.StringIO(base64.b64decode(scenery_blob))

    logging.debug("Extracting %s.dat from scenery zip file", airport_icao)
    with zipfile.ZipFile(scenery_zip_stringio, 'r') as ap_zip:
        airport_apt = ap_zip.open("{0}.dat".format(airport_icao)).read()
    logging.debug("Returning airport data in apt format for %s", airport_icao)
    return airport_apt

