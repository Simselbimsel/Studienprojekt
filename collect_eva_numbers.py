from asyncio.log import logger
import time
from datetime import datetime
from pathlib import Path
import pandas 
import requests
from requests.exceptions import RequestException
from logger_utils import *
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
    "accept": "application/json",
}

#callAPI Function
def call_api(max_retries=3):
   
    #define API-URL
    url = "https://apis.deutschebahn.com/db-api-marketplace/apis/station-data/v2/stations"
   
    for retry in range(max_retries):
        try:

            params = {
                "category": "1-2",
                "federalstate": "bayern",
                "logicaloperator": "or"
            }
		
            response = requests.get(url, headers=headers, params=params, timeout=15)
	        #raises error if HTTP-Request has an errorcode
            response.raise_for_status()

            logger("info", f"{response.status_code}: Connection successfull after {retry} attempts")

            #transform API result to json 
            api_data = response.json()

            #process stations
            stations = []
            for station in api_data["result"]:
                evas = []                

                for eva in station["evaNumbers"]:
                    evas.append(f"{eva.get('number')}")  

		        #dictionary with 3 entries
                single_station = {
                    "name": station.get("name"),
                    "category": station.get("category"),
                    "evas": ",".join(evas)                    
                }
                stations.append(single_station)

            #return 
            return pandas.DataFrame(stations)

        #Error Handling
        except (RequestException, ConnectionError) as error:

            # Versuche, den Statuscode zu holen (falls verfügbar)
            status_code = getattr(getattr(error, 'response', None), 'status_code', 'N/A')
            #log error 
            print(f"Retry {retry+1} failed: {error}")

            if retry+1 < max_retries:
                print("Retry in 1 second")
                time.sleep(1)
            else:
                logger("error", f"Connection unsuccessfull:")
                logger("error", f"failed with status code {status_code} and error: {error}")				
                return None

        #finally:
            #limit Request Rate - 1 Request per second
           # time.sleep(1)

    return None

#main Function
def main():

    # initialisieren des loggers
    setup_logger()
    log_header()

    logger("info", f"started collecting EVA-Numbers")
    #call API 
    dataFrame = call_api()

    if dataFrame is not None:

        path = Path("evaNumbers")
        path.mkdir(parents=True, exist_ok=True) 

        dataFrame.to_json(
            path/"evaNumbers.json",
            orient="records",
            force_ascii=False,
            indent=4
        )
        logger("info", f"Successfully collected EVA-Numbers")
    
    else:
        logger("error", f"failed to collect EVA-Numbers")

    log_footer()
main()
