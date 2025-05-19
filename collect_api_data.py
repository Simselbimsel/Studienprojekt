import time
from datetime import datetime, timedelta
from pathlib import Path
from xml.dom.minidom import parseString
import pandas 
import logging
import requests
from logger_utils import *
from requests.exceptions import RequestException
from zoneinfo import ZoneInfo
import os

#get secret API key and set HTTP-Header for Request
api_key = os.getenv("DB_API_KEY")
if not api_key:
    raise ValueError("No API Key provided!")

client_id = os.getenv("DB_CLIENT_ID")
if not client_id:
    raise ValueError("No Client Id provided!")

headers = {
    "DB-Api-Key": api_key,
    "DB-Client-Id": client_id,
    "accept": "application/xml",
}

#callAPI Function 
def call_api(url, path, max_retries=3):    
   
    for retry in range(max_retries):
        try:
            
            #HTTP-GET Call
            response = requests.get(url, headers=headers, timeout=15)
            
            #throws HTTP-Error like 404 
            response.raise_for_status()             
            
            #saves API result in XML-File  
            with path.open("w", encoding="utf-8") as file:
                file.write(parseString(response.content).toprettyxml())
            
            print(f"Saved response to: {path}")
			
            #limit Request Rate - 1 Request per second
            time.sleep(1/60) 

            return 

        #Error Handling
        except (RequestException, ConnectionError) as error:

            #log error 
            print(f"Retry {retry+1} failed: {error}")

            #retry after 1 second
            if retry < max_retries-1:
                print("Retry in 1 second")
                time.sleep(1)
            
            #all retries errored
            else:
                print(f"Failed to collect data after {max_retries} Retrys")
                logger("error", f"Failed to collect data for {url}")

#main Function
def main():

    # initialisieren des loggers
    setup_logger()
    log_header()
	
    logger("info", "Data collection started.")
	
    #import EVA-File to pandas DataFrame
    dataFrame = pandas.read_json(Path("evaNumbers") / "evaNumbers.json", orient="records")

    #EVA Array
    eva_list = []
    for evas in dataFrame["evas"]:
        eva_list.extend(evas.split(",")) 

    #get date 
    date = datetime.now(ZoneInfo("Europe/Berlin")).strftime("%y%m%d")

    #get current hour
    current_hour = datetime.now(ZoneInfo("Europe/Berlin")).hour

    #create path to a folder if not existing
    api_data_folder = Path("apiData")/date
    api_data_folder.mkdir(exist_ok=True, parents=True)
    
    #define 2 API-URLs
    plan_url = "https://apis.deutschebahn.com/db-api-marketplace/apis/timetables/v1/plan/{eva}/{date}/{hour}"
    change_url = "https://apis.deutschebahn.com/db-api-marketplace/apis/timetables/v1/fchg/{eva}"

    #call API for each EVA Number and save as XML with current date + hour as path (4 calls a day) 0, 6, 12, 18
    for eva in eva_list: 

        if current_hour == 0:
            continue

        #setup change url 
        url = change_url.format(eva=eva)
        path = api_data_folder/f"{eva}_change_{date}_{current_hour:02}.xml"
        call_api(url, path)

    #call API for each EVA Number and save as XML with current date + hour as path (covers 6 hours -> 4 calls a day) 
    for eva in eva_list:
        for i in range(6):    
            if current_hour == 23:
                continue    

            hour = (current_hour + i) % 24

            #setup plan url
            url = plan_url.format(eva=eva, date=date, hour=f"{hour:02}")
            path = api_data_folder/f"{eva}_plan_{date}_{hour:02}.xml"
            call_api(url, path)

    logger("info", "Data collection completed.")
    log_footer()

main()
