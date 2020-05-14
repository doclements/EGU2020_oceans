"""
Description:    Universal downloader for Copernicus Sentinel-3 marine data.
Author:         Ben Loveday, Hayley Evers-King (Plymouth Marine Laboratory)
Date:           08/2019
Version:        v0.5
License:        MIT License


Copyright (c) 2019 EUMETSAT

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.

Credits:

This code utilises heavily adapted snippets of code written by Ben Loveday
for Plymouth Marine Laboratory.

This code was developed for EUMETSAT under contracts for the Copernicus
programme.

Versions history:

    - (v0.5) Improved handling of global searches to still acquire polygons
             that may not display correctly on CODA.
    - (v0.5) Minor bug fixes

    - (v0.4) Minor bug fixes

    - (v0.3) Allow filtering by polygon overlap coverage.
    - (v0.3) Allow filtering by ASC/DEC passes.
    - (v0.3) Allow band selection by list.


    - (v0.2) User credentials passed by config file, or command line.
    - (v0.2) Filtering by OLCI L1 and SLSTR L1 flags is now supported.
    - (v0.2) Filtering by ingestion date is now supported.
    - (v0.2) CODAREP downloads are now supported.
    - (v0.2) Getting search queries only is now supported.
    - (v0.2) Minor bug fixes.

    - (v0.1) Filtering by OLCI L2 flags is now supported.

    - (v0.0) Initialisation

Usage:

    From command line:
    python3.6 Universal_Sentinel_Downloader.py - u <username> -p <password>

    From python:
    Run the script with no arguments, and set username and password in the
    configuration file (default: Universal_Sentinel_Downloader_S3.ini).

Options:

    All configured in Universal_Sentinel_Downloader_S3.ini

Please see README.md for more details.

EUMETSAT is interested in hearing about applications that make use of this code.
Please consider contacting EUMETSAT via the Copernicus Marine User Forum
(https://forums.eumetsat.int/forums/forum/copernicus-marine-calval/) if you
have comments and/or suggestions for improvements, or wish to tell us about how
we can better support your Sentinel-3 marine work.f
"""
import os
import logging
import re
from datetime import datetime, timedelta
import tempfile
import sys
import shutil
import argparse
import configparser
import numpy as np
import netCDF4 as nc
import shapely.wkt
from lxml import etree
import requests

# ------------------------------------------------------------------------------
class MyParser(configparser.ConfigParser):
    """ Define config parser """
    def as_dict(self):
        """ set dictionary """
        mydict = dict(self._sections)
        for key in mydict:
            mydict[key] = dict(self._defaults, **mydict[key])
            mydict[key].pop("__name__", None)
        return mydict

# ------------------------------------------------------------------------------
def check_overlap(search_polygon, found_polygon):
    """ check overlap of target (search) and found polygons """
    overlap_percentage = 0
    poly_1 = shapely.wkt.loads(search_polygon.replace('"Intersects(', '').replace(')"', ''))
    poly_2 = shapely.wkt.loads(found_polygon)
    overlap_percentage = poly_1.intersection(poly_2).area/poly_1.area*100.0
    return overlap_percentage

# ------------------------------------------------------------------------------
def flag_data_fast(flags_we_want, flag_names, flag_values, \
                   flag_data, flag_type='WQSF'):
    """ Implement flag masking processor """

    flag_bits = np.uint64()
    if flag_type == 'SST':
        flag_bits = np.uint8()
    elif flag_type == 'WQSF_lsb' or flag_type == 'quality_flags'\
      or flag_type == 'c2rcc_flags':
        flag_bits = np.uint32()
    elif flag_type == 'pixel_classif_flags':
        flag_bits = np.uint16()

    for flag in flags_we_want:
        try:
            flag_bits = flag_bits | flag_values[flag_names.index(flag)]
        except:
            print(flag + " not present")

    return (flag_data & flag_bits) > 0
# ------------------------------------------------------------------------------
def download_file(req_ses, url_str, req_config, arc_dir):
    """ downloads full file or fragment of a file """
    download_success = False
    # ----------------------------------------------------------------------
    # Create temp_dir
    temp_dir = tempfile.mkdtemp(suffix="_sentinel_downloader")

    try:
        req_ret = req_ses.get(url_str,\
                    auth=(req_config["account_options"]["username"],\
                    req_config["account_options"]["password"]),\
                    stream=True)
        download_success = True
    except:
        logging.warning("Hub misbehaving (1), skipping this url")
        logging.info(">>> %s", url_str)
        return download_success, ""

    # check file size
    file_size = -1
    try:
        base_fname = req_ret.headers["content-disposition"].split("=")[1].strip('"')
        file_size = int(req_ret.headers["content-range"].split("/")[1])
    except:
        logging.info("Hub misbehaving (2), skipping this url")
        logging.info(">>> %s", url_str)
        download_success = False
        return download_success, ""

    # download file to temp dir
    temp_fname = os.path.join(temp_dir, base_fname)
    logging.info("Downloading %s ... ", base_fname)

    chunk_count = 0.
    chunk_size = 1024
    iters = np.arange(0, 110, 10)
    niter = 0
    with open(temp_fname, "wb") as the_file:
        for chunk in req_ret.iter_content(chunk_size=chunk_size):
            chunk_count = chunk_count + chunk_size
            if chunk: # filter out keep-alive new chunks
                percent_done = float(chunk_count)/float(file_size)*100.
                if percent_done >= iters[niter]:
                    logging.info("%s percent complete", str(int(percent_done)))
                    logging.info("%s Mb downloaded", str(float(chunk_count/(1024.*1024.))))
                    niter = niter+1
            the_file.write(chunk)
        the_file.flush()

    # copy from temp to archive
    if not os.path.exists(arc_dir):
        os.makedirs(arc_dir)

    try:
        shutil.move(temp_fname, arc_dir)
    except:
        #remnant of old file:
        os.remove(arc_dir+"/"+os.path.basename(temp_fname))
        shutil.move(temp_fname, arc_dir)

    # delete temp_dir
    shutil.rmtree(temp_dir)

    return download_success, os.path.join(arc_dir, os.path.basename(temp_fname))

# ------------------------------------------------------------------------------
def Define_request(req_config, url_hub):
    """ Defines a search request """
    url_str = url_hub + "/search?q="

    if req_config["download_options"]["satellite"] != "":
        url_str += "%s"%(req_config["download_options"]["satellite"]+"*")

    for key in req_config["search"].keys():
        if req_config["search"][key] != "":
            if key == "footprint" and req_config["global_search"] == True:
                continue
            if url_str[-3:] != "?q=":
                url_str += " AND "
            url_str += "%s:%s"%(key, req_config["search"][key])

    url_str += "&rows=%i&start=0"%req_config["max_rows"]

    return url_str

# ------------------------------------------------------------------------------
def parse_xml(xml_text):
    """ parses search query xml """
    # this line is python version dependant!!
    if sys.version_info[0] == 3:
        xml_str = re.sub(b' xmlns="[^"]+"', b"", xml_text, count=1)
    else:
        xml_str = re.sub(' xmlns="[^"]+"', "", xml_text, count=1)

    root = etree.fromstring(xml_str)
    entry_list = root.xpath("//entry")

    res = []
    for entry in entry_list:
        try:
            this_entry = {
                "uuid": entry.xpath("str[@name='uuid']/text()")[0],
                "identifier": entry.xpath("str[@name='identifier']/text()")[0],
                "beginposition": entry.xpath("date[@name='beginposition']/text()")[0],
                "endposition": entry.xpath("date[@name='endposition']/text()")[0],
                "footprint": entry.xpath("str[@name='footprint']/text()")[0]
                }
        except:
            # cater for missing footprints, a CODA issue that can cause problems!
            this_entry = {
                "uuid": entry.xpath("str[@name='uuid']/text()")[0],
                "identifier": entry.xpath("str[@name='identifier']/text()")[0],
                "beginposition": entry.xpath("date[@name='beginposition']/text()")[0],
                "endposition": entry.xpath("date[@name='endposition']/text()")[0],
                }
        res.append(this_entry)

    return res

# ------------------------------------------------------------------------------
def process_request(config, logging):
    """ processes a request to a url """
    # open requests session
    with requests.Session() as req_ses:

        # define transport adaptor
        adaptor = requests.adapters.HTTPAdapter(\
                  max_retries=int(config["download_options"]["retries"]))

        # define URL
        url_str = Define_request(config, \
                  config["download_options"]["url"])

        # ----------------------------------------------------------------------
        # Request available files
        logging.info("Processing request at specified data HUB ... ")

        # try to connect to primary hub first:
        req_ses.mount(config["download_options"]["url"], adaptor)
        logging.info("Querying data at: %s", config["download_options"]["url"])
        logging.info("Query: %s", url_str)
        req_ret = req_ses.get(url_str, auth=(config["account_options"]["username"],\
                    config["account_options"]["password"]),\
                    timeout=None)

        logging.info("Code %(string1)s : %(string2)s", \
            dict(string1=config["download_options"]["url"],\
            string2=str(req_ret.status_code)))

        if req_ret.status_code != 200:
            req_ses.close()
            logging.error("Data query to %(string1)s was not successful! (%(string2)s retries)", \
                dict(string1=config["download_options"]["url"], \
                string2=str(config["download_options"]["retries"])))
            if req_ret.status_code != 401:
                logging.error('Your login credentials may be wrong, please check them')

        logging.info("Done")
        if req_ret.status_code == 200:
            # parse xml code: extract image names and UUID
            entries = parse_xml(req_ret.content)

            if len(entries) >= config["max_rows"]:
                logging.error("Number of scenes (%(string1)s) > than maximum (%(string2)s)",\
                    dict(string1=str(len(entries)), string2=str(config["max_rows"])))
                logging.error("Increase max_rows!")
                req_ses.close()
                raise Exception("The number of scenes (" \
                                + str(len(entries)) \
                                + ") is greater than maximum (" \
                                + str(config["max_rows"]) \
                                + "): increase max_rows!")
        else:
            entries = False

    return entries

# ------------------------------------------------------------------------------
def download_files(config, entries, logging):
    """ downloads the files """
    # open requests session
    with requests.Session() as req_ses:

        # ----------------------------------------------------------------------
        # download files
        logging.info("Started downloading %i files ...", len(entries))
        for entry in entries:
            split_id = entry["identifier"].split("_")
            sensor = split_id[0][:2]

            # check if the file already exists in the archive
            try:
                if sensor.lower() == "s1":
                    dtime = datetime.strptime(split_id[5], "%Y%m%dT%H%M%S")
                elif sensor.lower() == "s2":
                    # annoying date format change
                    try:
                        logging.info("Trying for old date format")
                        dtime = datetime.strptime(split_id[5], "%Y%m%dT%H%M%S")
                    except:
                        logging.info("Failed: Trying for new date format")
                        dtime = datetime.strptime(split_id[6], "%Y%m%dT%H%M%S")
                elif sensor.lower() == "s3":
                    dtime = datetime.strptime(entry["identifier"][16:31], \
                            "%Y%m%dT%H%M%S")
                else:
                    logging.error("Not a Sentinel file name!")
                    raise Exception("Not a Sentinel file name!")
            except:
                logging.warning("Unknown file format...skipping this url: %s", \
                                entry["identifier"])
                continue

            if config["storage_options"]["output_sub_directory"] == "True":
                arc_dir = os.path.join(config["storage_options"]\
                          ["output_root_directory"], dtime.strftime("%Y/%m/%d"))
            else:
                arc_dir = config["storage_options"]["output_root_directory"]

            url_str = config["download_options"]["url"] \
                      + "/odata/v1/Products('%s')/$value"%entry['uuid']

            download_path = os.path.join(arc_dir, entry["identifier"] + ".SEN3")

            # download the xml manifest file only: preemptive filtering
            url_xml_str = config["download_options"]["url"] \
                    + "/odata/v1/Products('%s')"%entry['uuid'] \
                    + "/Nodes('" + entry["identifier"] \
                    + ".SEN3" + "')/Nodes('xfdumanifest.xml')/$value"

            download_success, xml_out = download_file(req_ses, \
                                   url_xml_str, config, download_path)

            if not download_success:
                print("No xml file found: something is wrong, moving to next file")
                logging.info(url_xml_str)
                continue

            # filtering based on xml parameters
            print("Checking pass against polygon overlap requirements...")
            if config["global_search"]:
                overlap_percentage = 100
            else:
                try:
                    overlap_percentage = check_overlap(config["search"]["footprint"], \
                        entry["footprint"])
                except:
                    overlap_percentage = 100

            if overlap_percentage < config["overlap"]:
                print("Overlap with specified polygon (" + \
                    str(overlap_percentage)+")is too small; skipping this file")
                logging.info("Overlap with specified polygon is too small; skipping this file")
                continue

            print('Passed ('+str(overlap_percentage)+')')

            print("Checking pass against orbit direction requirements...")
            # READ XML INTO STRING AND CHECK FOR ORBIT TERMS; EG ASCENDING, DON'T BOTHER WITH XML

            if config["pass_direction"] != "BOTH":
                with open(xml_out, 'r') as xml_file:
                    xml_string = xml_file.read()
                if config["pass_direction"] not in xml_string:
                    print("Wrong orbital direction; skipping this file")
                    logging.info("Wrong orbital direction; skipping this file")
                    continue

            if config["download_options"]["get_xml_only"] == "True":
                continue

            # build url string & isolate file
            if config["flag_options"]["filter_by_flag"] == "True":
                print('Checking flags...')
                url_flag_str = config["download_options"]["url"] \
                               + "/odata/v1/Products('%s')"%entry['uuid'] \
                               + "/Nodes('" + entry["identifier"] \
                               + ".SEN3"+"')/Nodes('" \
                               + config["flag_options"]["flag_file"] \
                               + "')/$value"

                url_coords_str = config["download_options"]["url"] \
                               + "/odata/v1/Products('%s')"%entry['uuid'] \
                               + "/Nodes('" + entry["identifier"] + ".SEN3" \
                               + "')/Nodes('" \
                               + config["flag_options"]["coords_file"] \
                               + "')/$value"

                download_success, xml_out = download_file(req_ses, url_flag_str, \
                                            config, download_path)
                if not download_success:
                    continue

                download_success, xml_out = download_file(req_ses, url_coords_str, \
                                            config, download_path)
                if not download_success:
                    continue

                flag_file = os.path.join(arc_dir, entry["identifier"] \
                            + ".SEN3", config["flag_options"]["flag_file"])
                coords_file = os.path.join(arc_dir, entry["identifier"] \
                              + ".SEN3", config["flag_options"]["coords_file"])
                # open the coords data
                cf_fid = nc.Dataset(coords_file, 'r')
                longitude = cf_fid.variables[config["flag_options"]["coords_lon"]][:]
                latitude = cf_fid.variables[config["flag_options"]["coords_lat"]][:]
                cf_fid.close()

                # open the flag data
                ff_fid = nc.Dataset(flag_file, 'r')
                flags_we_want = config["flag_options"]["filter_flag"].split(",")
                flag_names = ff_fid[config["flag_options"]\
                                   ["flag_variable"]].flag_meanings.split(' ')
                flag_vals = ff_fid[config["flag_options"]\
                                  ["flag_variable"]].flag_masks
                flags = ff_fid.variables[config["flag_options"]\
                                        ["flag_variable"]][:]
                ff_fid.close()
                shutil.rmtree(download_path)

                flag_mask = flag_data_fast(flags_we_want, flag_names, \
                            flag_vals, flags, \
                            flag_type=config["flag_options"]["flag_variable"])
                flag_mask = flag_mask.astype(float)
                flag_mask[longitude < float(config["lon1"])] = np.nan
                flag_mask[longitude > float(config["lon2"])] = np.nan
                flag_mask[latitude < float(config["lat1"])] = np.nan
                flag_mask[latitude > float(config["lat2"])] = np.nan

                bad_pixels = np.float(np.nansum(flag_mask))
                flag_mask[flag_mask == 0] = 1.0
                all_pixels = np.float(np.nansum(flag_mask))

                if all_pixels == 0.0:
                    print("Area too small to determine scene clarity")
                    print("setting to 100% clear")
                    logging.info("Area too small to determine scene clarity")
                    logging.info("setting to 100% clear")
                    percent_clear = 100.0
                else:
                    percent_clear = (all_pixels - bad_pixels) / \
                                    all_pixels * 100.0

                logging.info("Percent clear of flag(s): %s", str(percent_clear))
                print("Percent clear of flag(s): "+str(percent_clear))
                if percent_clear < float(config["flag_options"]\
                                               ["flag_percentage"]):
                    print("Not clear enough; skipping scene")
                    continue

            url_str = config["download_options"]["url"] \
                      + "/odata/v1/Products('%s')/$value"%entry['uuid']

            if config["download_options"]["get_specified_bands"] == "True":
                mybands = config["download_options"]["specified_bands"].split(',')
                for myband in mybands:
                    print("Downloading band: "+myband)
                    url_band_str = config["download_options"]["url"] \
                                   + "/odata/v1/Products('%s')"%entry['uuid'] \
                                   + "/Nodes('" + entry["identifier"] \
                                   + ".SEN3"+"')/Nodes('" \
                                   + myband \
                                   + "')/$value"
                    download_success, xml_out = download_file(req_ses, url_band_str, \
                                                config, download_path)
            else:
                print("Downloading entire SAFE product")
                download_success, xml_out = download_file(req_ses, url_str, config, arc_dir)
            if not download_success:
                continue

        logging.info("Finished downloading!")

    return

# ------------------------------------------------------------------------------
def parse_date(date_str, midnight=False):
    """ performs date checking """
    if date_str != "":
        if date_str[:3].upper() == "NOW":
            if len(date_str) == 3:
                this_date = datetime.now()
            elif date_str[3] == "-":
                this_date = datetime.now() - timedelta(days=int(date_str[4:]))
            else:
                raise Exception("Incorrect date!")
        else:
            if len(date_str) == 8:
                this_date = datetime.strptime(date_str, "%Y%m%d")
                if midnight:
                    this_date += timedelta(hours=23, minutes=59, seconds=59.999)
            else:
                this_date = datetime.strptime(date_str, "%Y%m%dT%H%M%S")
    else:
        raise Exception("Date not set!")

    return this_date

# ------------------------------------------------------------------------------
def parse_config(config, username, userpwrd):
    """ parses the initialisation config file """
    # check and update config setup if required

    if username:
        config["account_options"]["username"] = username
    if config["account_options"]["username"] == "":
        raise Exception("No username selected, please define one")

    if userpwrd:
        config["account_options"]["password"] = userpwrd
    if config["account_options"]["password"] == "":
        raise Exception("No password selected, please define one")

    if config["download_options"]["platform"] == "":
        raise Exception("No platform selected, please define one")

    if "Sentinel-1" in config["download_options"]["platform"]:
        config_key = "sentinel1_request_options"
        if config["download_options"]["url"] == "":
            config["download_options"]["url"] = \
                                           "https://scihub.copernicus.eu/apihub"

    if "Sentinel-2" in config["download_options"]["platform"]:
        config_key = "sentinel2_request_options"
        if config["download_options"]["url"] == "":
            config["download_options"]["url"] = \
                                           "https://scihub.copernicus.eu/apihub"

    if "Sentinel-3" in config["download_options"]["platform"]:
        config_key = "sentinel3_request_options"
        if config["download_options"]["url"] == "":
            config["download_options"]["url"] = "https://coda.eumetsat.int/"

        # check flags against expected values to help user selection.
        if config["flag_options"]["filter_by_flag"] == "True":
            if "OL_2" in config[config_key]["producttype"]:
                if "wqsf" not in config["flag_options"]["flag_file"]:
                    print("WARNING: check flag selection for this product")
            if "OL_1" in config[config_key]["producttype"]:
                if "qualityFlags" not in config["flag_options"]["flag_file"]:
                    print("WARNING: check flag selection for this product")

    config["search"] = config[config_key]
    config["search"]["footprint"] = config["download_options"]["footprint"]

    if config["download_options"]["footprint"] == "":
        logging.info("No region selected, using global")
        config["global_search"] = True
    else:
        latlon = config["download_options"]["footprint"].split(":")
        config["lon1"] = latlon[0].split(",")[0]
        config["lat1"] = latlon[0].split(",")[-1]
        config["lon2"] = latlon[1].split(",")[0]
        config["lat2"] = latlon[1].split(",")[-1]
        config["global_search"] = False

        # must split queries in CODA, it can't search across Greenwich Meridien!
        if float(config["lon1"]) <= 0.0 and float(config["lon2"]) >= 0.0:
            config["search"]["footprint"] = \
                '"Intersects(POLYGON((%(lon1)s %(lat1)s, %(lont)s %(lat1)s, %(lont)s %(lat2)s, %(lon1)s %(lat2)s, %(lon1)s %(lat1)s)))"' \
                %{"lon1":config["lon1"], "lat1":config["lat1"], "lat2":config["lat2"], "lont":"0"} \
                +' OR footprint:"Intersects(POLYGON((%(lont)s %(lat1)s,%(lon2)s %(lat1)s,%(lon2)s %(lat2)s,%(lont)s %(lat2)s,%(lont)s %(lat1)s)))"' \
                %{"lat1":config["lat1"], "lon2":config["lon2"], "lat2":config["lat2"], "lont":"0"}
        else:
            config["search"]["footprint"] = \
                '"Intersects(POLYGON((%(lon1)s %(lat1)s,%(lon2)s %(lat1)s,%(lon2)s %(lat2)s,%(lon1)s %(lat2)s,%(lon1)s %(lat1)s)))"'\
                %{"lon1":config["lon1"], "lat1":config["lat1"], "lon2":config["lon2"], "lat2":config["lat2"]}

    if config["download_options"]["sensing_date_start"] != "" \
      and config["download_options"]["sensing_date_end"] != "":
        sdt_from = parse_date(config["download_options"]["sensing_date_start"])
        sdt_to = parse_date(config["download_options"]["sensing_date_end"], \
                 midnight=True)
        config["search"]["beginPosition"] = "[" \
                                 + sdt_from.strftime("%Y-%m-%dT%H:%M:%S") \
                                 + sdt_from.strftime(".%f")[:4] + "Z TO " \
                                 + sdt_to.strftime("%Y-%m-%dT%H:%M:%S") \
                                 + sdt_to.strftime(".%f")[:4]+"Z]"

    if config["download_options"]["ingestion_date_start"] != "" \
      and config["download_options"]["ingestion_date_end"] != "":
        idt_from = parse_date(config["download_options"]\
                                    ["ingestion_date_start"])
        idt_to = parse_date(config["download_options"]\
                                    ["ingestion_date_end"], midnight=True)
        config["search"]["ingestionDate"] = "[" \
                                 + idt_from.strftime("%Y-%m-%dT%H:%M:%S") \
                                 + idt_from.strftime(".%f")[:4] + "Z TO " \
                                 + idt_to.strftime("%Y-%m-%dT%H:%M:%S") \
                                 + idt_to.strftime(".%f")[:4] + "Z]"

    if config["download_options"]["polygon_overlap_percentage"] != "":
        config["overlap"] = float(config["download_options"]["polygon_overlap_percentage"])
    else:
        config["overlap"] = 0.0

    if config["download_options"]["pass_direction_filter"].lower() == "ascending":
        config["pass_direction"] = 'groundTrackDirection="ascending"'
    elif config["download_options"]["pass_direction_filter"].lower() == "descending":
        config["pass_direction"] = 'groundTrackDirection="descending"'
    else:
        config["pass_direction"] = "BOTH"

    config["max_rows"] = 99

    return config

# -args-------------------------------------------------------------------------
PARSER = argparse.ArgumentParser()
# ------------------------ input args: file names and vars ---------------------
# source (background)
PARSER.add_argument("-c", "--config_file", type=str, \
                    help="configuration_file", \
                    default="Universal_Sentinel_Downloader_S3.ini")
PARSER.add_argument("-u", "--username", type=str, \
                    help="user name", default=None)
PARSER.add_argument("-p", "--password", type=str, \
                    help="password", default=None)

# -args-done--------------------------------------------------------------------
ARGS = PARSER.parse_args()

#-------------------------------------------------------------------------------
#-main----
if __name__ == "__main__":
    # --------------------------------------------------------------------------
    # parse options
    F_PARSE = MyParser()
    F_PARSE.read(ARGS.config_file)
    CONFIG = F_PARSE.as_dict()
    CONFIG = parse_config(CONFIG, ARGS.username, ARGS.password)
    LOGFILE = CONFIG["storage_options"]["logfile"] + "_" \
              + datetime.now().strftime("%Y%m%d_%H%M%S")+".log"

    # set file logger
    try:
        if os.path.exists(LOGFILE):
            os.remove(LOGFILE)
        logging.basicConfig(filename=LOGFILE, level=logging.INFO)
        print("Logging to: "+LOGFILE)
    except:
        raise Exception("Failed to set logger")

    # start the downloads
    ENTRIES = process_request(CONFIG, logging)

    logging.info('Available files:')
    logging.info('=======================================')

    if ENTRIES:
        for ENTRY in ENTRIES:
            logging.info("%(string1)s (uuid: %(string2)s)", \
                dict(string1=ENTRY["identifier"], string2=ENTRY["uuid"]))

        if CONFIG["download_options"]["search_data_only"] == "True":
            print('Available files: '+str(len(ENTRIES)))
            print('=======================================')
            for ENTRY in ENTRIES:
                print(ENTRY["identifier"] + ' (uuid: '+ENTRY["uuid"]+ ')')
            sys.exit()

        download_files(CONFIG, ENTRIES, logging)
    else:
        print("No matching files found")

    logging.info("Done")

#-EOF
