#!/usr/bin/env python
""" Tool to download all airports from X-Plane portal
"""

import logging
import requests
import StringIO
import base64
import zipfile
import sys
import simplejson

LATEST_DATA_FILE = "latest.json"

def save_latest_data(airport_to_scenery=None,
                     output_file_name=LATEST_DATA_FILE):
    """ Save the latest airport <-> recommendedSceneryId pairs in JSON format.
        Input data format (python dict):
        {
            "ABCD": 1234,
            "EFGH": 5678,
        }
        where
        "ABCD", "EFGH", "IJKL" are ICAO code for airports
        1234, 5678 are RecommendedSceneryId for corresponding airport.
        The entries with RecommendedSceneryId equal 0 will not be saved.
        Final data to be saved is also returned by the function.
    """
    logging.info("Saving airport <-> recommendedSceneryId pairs to %s",
                 output_file_name)
    if not (airport_to_scenery and type(airport_to_scenery) == dict):
        raise Exception("Bad data format or no input data.")
    # filter out airports with no recommendedSceneryId
    apt_to_scn_clean = {}
    for apt, scn in airport_to_scenery.iteritems():
        if scn:
            apt_to_scn_clean[apt] = scn
        else:
            logging.debug(
                "Airport %s has no recommendedSceneryId. Not saving.", apt)
    if not apt_to_scn_clean:
        raise Exception("No airport <-> scenery data to save.")

    with open(output_file_name, 'w') as latest_data_file:
        simplejson.dump(apt_to_scn_clean, latest_data_file,
                        sort_keys=True, indent=" " * 4)
    logging.info("Sucessfully saved %s airport <-> recommendedSceneryId to %s",
                 len(apt_to_scn_clean), output_file_name)

    return apt_to_scn_clean

def load_latest_data(input_file_name=LATEST_DATA_FILE):
    """ Loads the latest airport <-> recommendedSceneryId pairs in JSON format
        from the file specified. File is normally generated
        by save_latest_data(). See this function docstring for format.
    """
    logging.info("Loading airport <-> recommendedSceneryId pairs from %s",
                 input_file_name)
    with open(input_file_name, 'r') as latest_data_file:
        apt_to_scn = simplejson.load(latest_data_file)
    logging.info("Successfully loaded %s airports from %s",
                 len(apt_to_scn), input_file_name)
    return apt_to_scn

def get_json_from_api(api_request=None):
    """ Requests data from API, handles errors and tries to convert
        the JSON reply into python dict
    """
    max_retries = 3
    retries_done = 0
    while True:
        retries_done += 1
        try:
            reply = requests.get(api_request, timeout=60)
            break
        except (requests.exceptions.HTTPError, requests.exceptions.Timeout):
            if retries_done < max_retries:
                logging.warn("Error getting from %s. Retrying.", api_request)
                continue
            else:
                logging.error(
                    "Failed to get from %s after %s retries. Returning None",
                    api_request, retries_done)
                return None
        except:
            logging.error("Failed to get from %s. returning None", api_request)
            return None
    if reply.status_code != 200:
        logging.error("Failed to receive data from %s. Code %s",
                      api_request, reply.status_code)
        return None
    logging.debug("Converting reply from %s into dict", api_request)
    try:
        reply_dict = reply.json()
    except ValueError:
        logging.error("Reply from %s is not a valid JSON", api_request)
        return None
    return reply_dict

def get_airport_apt(scenery_id=None,
                    api_base="http://gateway.x-plane.com/apiv1/"):
    """ Gets scenery pack via X-Plane gateway API, unpacks it
        and returns the requested airport in apt format
    """

    if not (scenery_id and type(scenery_id) is int):
        raise Exception("Invalid scenery_id passed: {0}".format(scenery_id))

    scenery_request = api_base + "scenery/{0}".format(scenery_id)
    logging.info("Getting scenery for %s", scenery_id)
    scenery_json = get_json_from_api(scenery_request)
    if not scenery_json:
        logging.warn("No scenery received for %s", scenery_id)
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

def strip_airport_apt(raw_airport_apt=None):
    """ gets airport data in APT format and strips away the header and footer:
        A
        1000 Generated by WorldEditor
        <airport data>
        99
        Returns the striped string
        """
    if not raw_airport_apt:
        raise Exception("Function called with no input data")

    # strip whitespaces and newlines, then split into lines
    apt_lines = raw_airport_apt.strip().split("\n")
    if len(apt_lines) < 4:
        raise Exception("apt format error. Less than 4 lines in the file")
    # check if the file has correct format (header and footer)
    if not (apt_lines[0].startswith("I") or apt_lines[0].startswith("A")):
        raise Exception("apt format error. First line is neither A nor I")
    if not apt_lines[1].startswith("1000"):
        raise Exception(
            "apt format error. Second line does not start with 1000")
    if not apt_lines[-1].startswith("99"):
        raise Exception("apt format error. Last line does not start with 99")

    # return airport apt data without header and footer.
    # Also remove leading and trailing newlines and spaces
    return "\n".join(apt_lines[2:-1]).strip()

def print_apt_header():
    """ outputs apt file header to STDOUT
    """
    sys.stdout.write("I\n1000 Version\n\n")

def print_apt_footer():
    """ outputs apt file footer to STDOUT
    """
    sys.stdout.write("\n99")


def print_combined_apt_file(apt_list=None):
    """ Function receives a list of airports' APT data free from headers
        and footers (after strip_airport_apt() call), adds a common
        header and footer and outputs all the airports combined to STDOUT
    """
    if not apt_list:
        raise Exception("No airport's APTs passed")

    # write header
    print_apt_header()
    # write each airport passed adding an empty line at end of each
    for airport in apt_list:
        sys.stdout.write(airport)
        sys.stdout.write("\n\n")
    # write footer
    print_apt_footer()
    return 0

def get_airports(api_base="http://gateway.x-plane.com/apiv1/"):
    """ Gets all airports from X-plane API and forms a dict:
        {
            "ABCD": 1234,
            "EFGH": 5678,
            "IJKL": 0,
        }
        where
        "ABCD", "EFGH", "IJKL" are ICAO code for airports
        1234, 5678 and 0 are RecommendedSceneryId for corresponding airport.
        The Id may be zero - no good apt for this airport
    """
#this may be used for debugging not to put load on servers
#
#    return simplejson.loads("""
#{
#"E46": 13794,
#"SSOK": 29829,
#"1RSU": 4095
#}
#""".strip())

    airport_to_scenery = {} # this will be returned in the end
    airports_request = api_base + "airports"
    logging.info("Requesting all airports list")
    airports_json = get_json_from_api(airports_request)
    if not airports_json:
        logging.error("No airports received")
        return None
    logging.info("Received list of %s airports",
                 airports_json.get('total', 0))
    # now check each wirport if it has scenery
    for airport in airports_json.get('airports', []):
        logging.debug("Looking for RecommendedSceneryId for %s",
                      airport['AirportCode'])
        if not airport.get('RecommendedSceneryId', None):
            logging.warn("Airport %s has no RecommendedSceneryId.",
                         airport['AirportCode'])
        # add the airport code and corresponding scenery ID to resulting dict
        airport_to_scenery[airport['AirportCode']] = (
            airport.get('RecommendedSceneryId', 0))

    logging.info("Finished looking for RecommendedSceneryId. %s found",
                 len(airport_to_scenery))
    return airport_to_scenery

def main():
    """ Fetch all airports APT data and put in to STDOUT
    """
    # set logging to INFO. May be set to DEBUG if required
    logging.basicConfig(level=logging.INFO)
    # suppress lb3.connectionpool logging
    logging.getLogger("urllib3.connectionpool").setLevel(logging.WARNING)
    # get mapping of airport-to-sceneryID
    all_airports = get_airports()
    airports_total = len(all_airports)
    airports_processed = 0 # will count processed airports
    current_airport = 0 # will display the current airport number in list

    print_apt_header() # let's start writing our big APT file

    for code, scenery in get_airports().iteritems():
        current_airport += 1
        logging.info("[%s/%s] %s is being processed",
                     current_airport, airports_total, code)
        if not scenery:
            logging.warn("%s has no RecommendedSceneryId", code)
            continue
        logging.info("Getting APT data for %s", code)
        apt_data = get_airport_apt(scenery)
        if not apt_data:
            logging.warn("Failed to get APT data for %s", code)
            continue
        sys.stdout.write("\n")
        sys.stdout.write(
            strip_airport_apt(apt_data))
        sys.stdout.write("\n")

        airports_processed += 1 # we've processed this airport

    logging.info("Finished processing airports. Processed %s airports",
                 airports_processed)
    print_apt_footer() # print footer of a big APT file
    logging.info("APT file generation is complete.")

if __name__ == "__main__":
    main()
