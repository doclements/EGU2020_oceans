import os, time, fnmatch, datetime, logging, shutil, requests, re, json, urllib3, sys, zipfile, random
import urllib.parse
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

CONST_HTTP_SUCCESS_CODE = 200
# HDA-API endpoint
wekeo_apis_endpoint="https://apis.wekeo.eu"

# Data broker address
broker_address = wekeo_apis_endpoint + "/databroker/0.1.0"

# Terms and conditions
acceptTandC_address = wekeo_apis_endpoint + "/dcsi-tac/0.1.0/termsaccepted/Copernicus_General_License"

# Access-token address
accessToken_address = wekeo_apis_endpoint + '/token'

#The following is the default key which will be disabled in future when each of the WEkEO user can get their API key via WEkEO portal  
api_key = "aTMzOHdPZUViZFQ0UmtBWnZ4Zjl1VV9XX1JjYTpmVzJSUW92d09NZHBXN3BDZzlCcjI1MFVMS3Nh"  


# Class to store query response
class QueryResponse:
    def __init__(self, accessToken):
        self.token=accessToken
        self.tokenHeader = {
        'Authorization': 'Bearer ' + accessToken,
        }
        
    def setDownloadUrl(self, url):
        self.downloadUrl = url
        
    def setProductName(self, name):
        self.productName=name
        
    def setProductSize(self, size):
        self.productSize = size
        
    def setJobId(self,jobId):
        self.jobId=jobId  


# function to get filename from HTTP response header - content disposition
def get_filename_from_cd(cd):
    if not cd:
        return None
    fname = re.findall('filename=(.+)', cd)
    if len(fname) == 0:
        return None
    filename=fname[0].replace('\"',"").strip()
    return filename
	
# function to get token to access HDA API
def get_access_token(api_key):
    auth_header = {
	    'Authorization': 'Basic ' + api_key
    }
    
    grant_type = [
	    ('grant_type', 'client_credentials'),
	]
    
    print("Getting an access token")
    response = requests.post(accessToken_address, headers=auth_header, data=grant_type, verify=False)
	# If the HTTP response code is 200 (i.e. success), then retrive the token from the response
    if (response.status_code == CONST_HTTP_SUCCESS_CODE):
        access_token = json.loads(response.text)['access_token']
        print("Success: Access token is " + access_token)
    else:
	    access_token = None
	    print("Error: Unexpected response {}".format(response))
	    print("Unable to get access token for accessing HDA API ")
	    print(response.headers)
	    
    return access_token
    	

#  function to get and print metadata for a dataset
def get_metadata(dataset_id,token_header):
    # escape sequence for ":" is %3A. So encoded "EO:MO:DAT:SEAICE_GLO_SEAICE_L4_NRT_OBSERVATIONS_011_001" is EO%3AMO%3ADAT%3ASEAICE_GLO_SEAICE_L4_NRT_OBSERVATIONS_011_001
    metadata = None
    encoded_dataset_id = urllib.parse.quote(dataset_id)
    print("token_header : ", token_header)
    response = requests.get(broker_address + '/querymetadata/' + encoded_dataset_id, headers=token_header)
    
    if (response.status_code == CONST_HTTP_SUCCESS_CODE):
        metadata = json.loads(response.text)        
    else:
        print("Error in getting Metadata for dataset : " + dataset_id)
        print("Error: Unexpected response {}".format(response))
    
    return metadata

def has_job_completed(job_id, token_header):
    response = requests.get(broker_address + '/datarequest/status/' + job_id, headers=token_header)
    results = json.loads(response.text)['resultNumber']
    isComplete = json.loads(response.text)['complete']
    return isComplete
		
		
#  function to accept Terms and Conditions for the dataset
def accept_terms_conditions(token_header):
    response = requests.get(acceptTandC_address, headers=token_header)
    isTandCAccepted = json.loads(response.text)['accepted']
	
    if isTandCAccepted is False:
        print("Accepting Terms and Conditions of Copernicus_General_License")
        response = requests.put(acceptTandC_address, headers=token_header)
    else:
        print("Copernicus_General_License Terms and Conditions already accepted")
		
# function to submit dataset query as JSON object		
def submit_query(jsonQuery, token_header):
    response = requests.post(broker_address + '/datarequest', headers=token_header, json=jsonQuery, verify=False)
    if (response.status_code == CONST_HTTP_SUCCESS_CODE):
        job_id = json.loads(response.text)['jobId']
        print ("Query successfully submitted. Job ID is " + job_id)
    else:
	    job_id = None
	    print("Error: Query submission failed. ".format(response))
	    print(response.text)

    return job_id
	

def get_results(job_id, params, token_header):
    results = None
    response = requests.get(broker_address + '/datarequest/jobs/' + job_id + '/result', headers=token_header, params = params)
    if (response.status_code == CONST_HTTP_SUCCESS_CODE):
        results = json.loads(response.text)
    else:
        print("Error in getting results. HTTP response code is " +  str(response.status_code))
        print(response.text)
    return results
	
def build_download_url(job_id, externalUri, access_token):
    url=broker_address + '/datarequest/result/' + job_id + '?externalUri=' + urllib.parse.quote(externalUri) +"&access_token="+access_token
    return url

# function to retrieve results based on job ID
def get_job_results(job_id, queryResponse):
    pageNumber=0
    pageSize=5    
    params = {'page':pageNumber, 'size':pageSize}
    
    response = requests.get(broker_address + '/datarequest/jobs/' + job_id + '/result', headers=queryResponse.tokenHeader, params = params)
    results = json.loads(response.text)
    totalRes = len(results['content'])
    if(totalRes>0):
        print("Selecting randomly a product for plotting ")
        randomInt = random.randint(0,totalRes-1)
        firstResult = results['content'][randomInt]
        product_name = firstResult['fileName']
        product_size = firstResult['fileSize']/(1024*1024)
        externalUri = firstResult['externalUri']
        downloadUrl = broker_address + '/datarequest/result/' + job_id + '?externalUri=' + urllib.parse.quote(externalUri) +"&access_token="+queryResponse.token
        queryResponse.setProductName(product_name)
        queryResponse.setProductSize(product_size)
        queryResponse.setDownloadUrl(downloadUrl)
    else:
        print("Job " + job_id +" returned empty results")
        queryResponse = None
              
        
    return queryResponse    
    
# function to return the response of the submitted query
def get_query_response(api_key, jsonQuery):
    access_token = get_access_token(api_key)
    if access_token:
	    queryResponse = QueryResponse(access_token)
	    token_header = queryResponse.tokenHeader
	    accept_terms_conditions(token_header)
	    job_id = submit_query(jsonQuery, token_header)
	    if job_id:
	        print("Waiting for the query response.....")
	        isComplete = False
	        while not isComplete:
	            response = requests.get(broker_address + '/datarequest/status/' + job_id, headers=token_header)
	            results = json.loads(response.text)['resultNumber']
	            isComplete = json.loads(response.text)['complete']
	            # sleep for 2 seconds before checking the job status again
	            if not isComplete:
	                time.sleep(2)
	        print("Job " + job_id + " successfully completed.")
	        
	       
				
    return get_job_results(job_id, queryResponse)

