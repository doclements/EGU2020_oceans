**PYTHON UNIVERSAL SENTINEL DOWNLOADER**
---
|Description	| Python script to download Sentinel-3 marine data via CODA/CODAREP |
| :-------------| :----------------------------------------------------------- |
|Author		| Ben Loveday, Hayley Evers-King (Plymouth Marine Laboratory and EUMETSAT) |
|Date		| 02/2019 |
|Version	| v2.1 |
|Project use	| Copernicus projects for EUMETSAT, funded under the Copernicus programme of the European Commission | 

*Notes*

1. Code in its current form supports Python2.7 and Python3.6 - in future, only the latter will be supported.
2. This code is designed primarily for use with Sentinel-3 and CODA/CODAREP, but in principle it will work with other Sentinel data portals that share the same backend.
3. The main script is hard limited to return 99 search results (due to existing portal search limits). If more data is required, it is recommended  
   to launch the download script with looping start and end dates. The Multi_day_launch.run wrapper has been provide to support this.
4. Python code has been tested in OSx, Linux and Windows 10 environments. In the latter case, care must be taken with path construction and length!. The
   Multi_day_launcher.run script is only suitable for operating systems that support bash (git_bash can offer this for windows 10).

---
**MODULES:**
---
| Module                               | Job                                       |
| :----------------------------------- | :---------------------------------------- |
|Universal_Sentinel_Downloader.py      |	Main script for downloading          |
|Universal_Sentinel_Downloader_S3.ini  |	Configuration script for single use downloading |
|Universal_Sentinel_Downloader_S3_template.ini  |	Configuration script for multiple, date-looping downloads (for use with Multi_day_launcher.run/Multi_day_launcher_OSX.run) |
|Multi_day_launcher.run  |	Bash wrapper to facilitate multiple downloads or for when > 100 files are requested |
|Multi_day_launcher_OSX.run  |  Bash wrapper to facilitate multiple downloads or for when > 100 files are requested (using OSX rather than GNU date tools) |

**Instructions for use:**
---
The "Universal Sentinel Downloader" is designed to be a user-configurable, cross platform solution to downloading EUMETSAT
Sentinel-3 marine data from both CODA and CODAREP. In typical usage, the user should not have to configure the main script
as all available options are configurable in the Universal_Sentinel_Downloader_S3.ini file. The main script will call
this configuration script by default, though users can pass their own as an argument from the command line.

When receiving automated queries, both CODA and CODAREP will fail to return reliable URLs if the number of requested 
products that match the query exceeds 99 entries. In this case, it is necessary to launch multiple, consecutive downloaders 
each associated with a 'time-slice' of data. The Multi_day_launcher.run script acts as a wrapper that will handle this situation.

The Universal_Sentinel_Downloader_S3.in configuration file has a sibling (Universal_Sentinel_Downloader_S3_template.ini)
that is designed for use with the Multi_day_launcher.run. The only difference between these two files is that the start and end date 
strings in the template file should not be altered. All other values can be altered as the user requires.

When launching a query, the user has the following options to set in Universal_Sentinel_Downloader_S3.ini:

| options                              | usage                                       |
| :----------------------------------- | :---------------------------------------- |
|[account_options]      		|	User login credentials for CODA are passed to the script in two way; either via the command line (preferred), or by completing the username and password fields under this heading. |
|[storage_options]  			|	Here the user determines where to dowload the data to (output_root_directory), whether or not to store it in a YYYY/MM/DD directory structure, and what prefix to use for log files. |
|[download_options]  			|	Here the user selects the spatial (footprint) and temporal (date_start and sate_end) for the data search. Either ingestion or sensing date can be used (or both in concert). The user also selects the platform (e.g. Sentinel-3) and satellite to find data for. The user can also provide a selctable url if the data is required from a source other than the default (https://coda.eumetsat.int/), i.e. if products are required from CODAREP. If get_xml_only is set to true, only the xml manifest file will be downloaded. Otherwise, the full product will be downloaded. If search_data_only is set to true, the script will return a list of products that match the query with no downloading. |
|[flag_options]					|	Where separate flag files are available (e.g. OLCI and SLSTR L1), these can be used to filter data for coverage prior to downloading the full product. Users must set filter_by_flag to "True" to allow this functionality, and ensure that the netCDF file containing the flags (flag_file), variable in the netCDF file containing flag data (flag_variable), and the required flag to be used (filter_flag). The flag codes used to populate "filter_flag" can be found in the flag_file. More information on flags can be found in the EUMETSAT marine product guides for the relevant sensor: https://www.eumetsat.int/website/home/Satellites/CurrentSatellites/Sentinel3/index.html. To allow for flag testing across defined areas, the user must also provide the relevant geo-coordinates file (coords_file) and the variable names for latitude (coords_lat) and longitude (coords_lon). |
|[sentinel3_request_options]  	|	Here the user can refine the product searched for based on various parameters, e.g. producttype and/or timeliness. |

---
