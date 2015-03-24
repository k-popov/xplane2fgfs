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
import os

LATEST_DATA_FILE = "latest.json"
APT_DIR = "airports"
APT_FILENAME_TEMPLATE = "{0}.dat"

def init_dir_structure():
    """ Created directories structure for script to work with.
        Currently it is only a directory for individual airport .dat files
    """
    if os.path.isdir(APT_DIR):
        return
    logging.info("Creating %s to store airports .dat files in it.", APT_DIR)
    os.mkdir(APT_DIR)

def save_local_ap_data(airport_to_scenery=None,
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
    logging.debug("Saving airport <-> recommendedSceneryId pairs to %s",
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
    logging.debug("Sucessfully saved %s airport <-> recommendedSceneryId to %s",
                  len(apt_to_scn_clean), output_file_name)

    return apt_to_scn_clean

def load_local_ap_data(input_file_name=LATEST_DATA_FILE):
    """ Loads the latest airport <-> recommendedSceneryId pairs in JSON format
        from the file specified. File is normally generated
        by save_latest_data(). See this function docstring for format.
    """
    logging.debug("Loading airport <-> recommendedSceneryId pairs from %s",
                  input_file_name)
    try:
        with open(input_file_name, 'r') as input_file:
            apt_to_scn = simplejson.load(input_file)
    except IOError:
        logging.warn("File %s can't be read.", input_file_name)
        logging.info("The previous message may be ignored if you're downloading airports for the 1st time.") #pylint: disable=line-too-long
        return {}
    logging.debug("Successfully loaded %s airports from %s",
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
        except (requests.exceptions.HTTPError,
                requests.exceptions.Timeout,
                requests.exceptions.ConnectionError):
            if retries_done < max_retries:
                logging.warn("Error getting from %s. Retrying.", api_request)
                continue
            else:
                logging.error(
                    "Failed to get from %s after %s retries. Returning None",
                    api_request, retries_done)
                return None
        except requests.exceptions.RequestException:
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

def get_ap_data(scenery_id=None,
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

def get_gateway_ap_list(api_base="http://gateway.x-plane.com/apiv1/"):
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
    # set DEBUG environmental variable to anything non-empty to have debug log
    if os.environ.get("DEBUG", None):
        logging.basicConfig(level=logging.DEBUG)
    else:
        logging.basicConfig(level=logging.INFO)
        # suppress lb3.connectionpool logging
        logging.getLogger("urllib3.connectionpool").setLevel(logging.WARNING)
        # suppress requests logging
        logging.getLogger("requests").setLevel(logging.INFO)

    # create required directories
    init_dir_structure()
    # get mapping of airport-to-sceneryID from x-plane gateway
    logging.debug("Getting a list of all airports from gateway.")
    all_airports_gw = get_gateway_ap_list()
    # loadairport-to-sceneryID data that is already on local disk.
    logging.debug("Loading list of local airports.")
    all_airports_local = load_local_ap_data()
    airports_total = len(all_airports_gw)
    airports_processed = 0 # will count processed airports
    # save AP ICAO codes we didn't get data for (excl. up-to-date ones)
    airports_failed = []
    for code, scenery in all_airports_gw.iteritems():
        airports_processed += 1
        logging.info("[%s/%s] Processing airport %s", airports_processed,
                     airports_total, code)
        if not scenery:
            logging.warn("%s has no RecommendedSceneryId. Skipping.", code)
            if code not in airports_failed:
                airports_failed.append(code)
            continue
        local_ap_scenery_id = all_airports_local.get(code, None)
        logging.debug("Airport %s, local scenery %s, remote scenery %s",
                      code, local_ap_scenery_id, scenery)
        if local_ap_scenery_id == scenery:
            logging.info("Airport %s is up-to-date. Not updating.", code)
            continue
        logging.debug("Getting airport %s scenery from gateway.", code)
        airport_apt_data = get_ap_data(scenery)
        if not airport_apt_data:
            logging.error("Failed to get APT data for %s", code)
            if code not in airports_failed:
                airports_failed.append(code)
            continue
        # construct path to file that stores airport data
        apt_file_path = os.path.sep.join(
            [APT_DIR, APT_FILENAME_TEMPLATE.format(code)])
        try:
            # save the received airport data to file
            logging.debug("Saving %s data into %s", code, apt_file_path)
            with open(apt_file_path, 'w') as apt_file:
                apt_file.write(airport_apt_data)
            # save information about the airport just downloaded
            # This happens after each airport download but gives
            # more consistency in case of a download or write issue
            logging.debug("Updating local list of airports.")
            all_airports_local[code] = scenery
            logging.debug("Writing local list of airports into file.")
            save_local_ap_data(all_airports_local)
        except IOError:
            logging.error("Error saving %s to file. Leaving as is.", code)
            if code not in airports_failed:
                airports_failed.append(code)

    logging.info("Finished processing airports. Processed %s airports",
                 airports_processed)
    logging.debug("Problem airports (see log): %s", str(airports_failed))
    logging.info("APT file generation is complete.")

if __name__ == "__main__":
    main()
