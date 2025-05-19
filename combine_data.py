import xml.etree.ElementTree as ElementTree
from datetime import datetime, timedelta
from pathlib import Path
import pandas
import logging
from logger_utils import *
from zoneinfo import ZoneInfo


#Filter Function
def filter_type_category(train_type):
    
    #define excluded categories list
    excluded_categories = ["S", "U", "Bus"]
    
    return train_type not in excluded_categories

#getWeekday Function
def get_weekday(time):

    #define weekdays list
    weekdays = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]

    if not time or len(time) != 10:
        return None
    year = int("20" + time[:2]) 
    month = int(time[2:4])
    day = int(time[4:6])
    hour = int(time[6:8])
    minute = int(time[8:10])

    #create datetime object
    dt = datetime(year, month, day, hour, minute)

    #return weekday
    return weekdays[dt.weekday()]   


#getPlannedStopsForSingleStation Function 
def get_planned_stops(file):

    plannedstops = []

    #parse XML file
    tree = ElementTree.parse(file)
    
    #get Root Element (timetable) of XML file
    root = tree.getroot()

    #get station name
    station_name = root.get("station")    

    #iterate over all stops
    for stop in root.findall("s"):

        #get unique identifier for a stop like ICE-1001-3
        stop_id = stop.get("id")

        #get train type ICE from trip label
        train_type = stop.find("tl").get("c") if stop.find("tl") is not None else None      

        #skip S, U, Tram and Bus 
        if not filter_type_category(train_type):  
            continue  

        #get train number like 1001 from trip label 
        train_number = stop.find("tl").get("n") if stop.find("tl") is not None else None
       
        #create train name and differ between long distance and local trains
        if train_type in ["ICE", "IC", "EC"]:
            train_name = f"{train_type} {train_number}"

        #local train
        else:
            
            #get line number from arrival or departure
            arrival_train_line_number = stop.find("ar").get("l") if stop.find("ar") is not None else None
            departure_train_line_number = stop.find("dp").get("l") if stop.find("dp") is not None else None    

            if arrival_train_line_number is not None:
                train_name = f"{train_type} {arrival_train_line_number}"
            elif departure_train_line_number is not None:
                train_name = f"{train_type} {departure_train_line_number}"
            else:
                train_name = train_type

       
        #identify destination via ppth (planed route)like ("4000145|400200|4000250")
        departure_ppth = stop.find("dp").get("ppth") if stop.find("dp") is not None else None  

        #determine destination station
        if departure_ppth is None:
            #current station is destination
            final_destination_station = station_name
        else:
           #last entry of ppth is destination
            final_destination_station = departure_ppth.split("|")[-1]

        #get arrival time
        arrival_time = stop.find("ar").get("pt") if stop.find("ar") is not None else None

        #get departure time
        departure_time = stop.find("dp").get("pt") if stop.find("dp") is not None else None

        #get time 
        time = arrival_time or departure_time

        #add a stop with his data as dictionary to the list    
        plannedstops.append(
            {
                "id": stop_id,
                "station": station_name,
                "final_destination_station": final_destination_station,
                "train_name": train_name,                
                "train_type": train_type,   
                "train_line_ride_id": "-".join(stop_id.split("-")[:-1]),
                "train_line_station_num": int(stop_id.split("-")[-1]),
                "arrival_planned_time": arrival_time,
                "departure_planned_time": departure_time,  
                "weekday": get_weekday(time),
            }
        )

    return plannedstops

#getChangedStopsForSingleStation Function
def get_changed_stops(file, changed_stops):

    root = ElementTree.parse(file).getroot()

    for stop in root.findall("s"):
        
        stop_id = stop.get("id")
        
        #get train type from trip label
        train_type = stop.find("tl").get("c") if stop.find("tl") is not None else None

        #skip S, U, Tram and Bus 
        if not filter_type_category(train_type): 
            continue 
            
        #arrival time changed?
        arrival_change_time = stop.find("ar").get("ct") if stop.find("ar") is not None else None  

        #arrival cancellation time?
        arrival_cancellation_time = stop.find("ar").get("clt") if stop.find("ar") is not None else None  

        #departure time changed?
        departure_change_time = stop.find("dp").get("ct") if stop.find("dp") is not None else None  

        #departure cancellation time?
        departure_cancellation_time = stop.find("dp").get("clt") if stop.find("dp") is not None else None 

        #stop canceled?
        if arrival_cancellation_time is None and departure_cancellation_time is None:
            canceled = False
        else:
            canceled = True

        #skip stop if nothing happend 
        if arrival_change_time is None and departure_change_time is None and not canceled:
            continue

        #set new stop data
        changed_stops[stop_id] = {
            "id": stop_id,
            "arrival_change_time": arrival_change_time,
            "departure_change_time": departure_change_time,
            "canceled": canceled,
        }


#main Function call at 1am to combine data from lastDay
def main():    

    # initialisieren des loggers
    setup_logger()
    log_header()

    logger("info", "Combining Data started.")
    
    #yesterday = datetime.now(ZoneInfo("Europe/Berlin")).strftime("%y%m%d")
    yesterday = (datetime.now(ZoneInfo("Europe/Berlin")) - timedelta(days=1)).strftime("%y%m%d")

    path = Path("apiData")/yesterday

    if not path.exists():
        logger("error", f"Folder {path} doesnt exist")	
        return  
       
    #collect planned and changed files
    planned_files = []
    changed_files = []

    for file in path.iterdir():
        if yesterday in file.name and file.suffix == ".xml":
            if "plan" in file.name:
                planned_files.append(file)
            elif "change" in file.name:
                changed_files.append(file)


    #no plan and change files found
    if not planned_files and not changed_files:
        logger("error", f"No files for {yesterday} found")	
        return

    #process planned stops 
    planned_stops = []
    for file in planned_files:
        planned_stops.extend(get_planned_stops(file))

    planned_dataFrame = pandas.DataFrame(planned_stops)

    if not planned_dataFrame.empty:
        #convert planned time like 2505081530 to 2025-05-08 15:30
        if 'arrival_planned_time' in planned_dataFrame.columns:
            planned_dataFrame["arrival_planned_time"] = pandas.to_datetime(planned_dataFrame["arrival_planned_time"], format="%y%m%d%H%M", errors="coerce")
        if 'departure_planned_time' in planned_dataFrame.columns:
            planned_dataFrame["departure_planned_time"] = pandas.to_datetime(planned_dataFrame["departure_planned_time"], format="%y%m%d%H%M", errors="coerce")

        planned_dataFrame = planned_dataFrame.drop_duplicates()

    #process changed stops
    changed_stops = {}
    for file in changed_files:
        get_changed_stops(file, changed_stops)

    changed_dataFrame = pandas.DataFrame(changed_stops.values())

    if not changed_dataFrame.empty:
        #convert change time like 2505081530 to 2025-05-08 15:30  
        if 'arrival_change_time' in changed_dataFrame.columns:
            changed_dataFrame["arrival_change_time"] = pandas.to_datetime(changed_dataFrame["arrival_change_time"], format="%y%m%d%H%M", errors="coerce")
        if 'departure_change_time' in changed_dataFrame.columns:
            changed_dataFrame["departure_change_time"] = pandas.to_datetime(changed_dataFrame["departure_change_time"], format="%y%m%d%H%M", errors="coerce")

        changed_dataFrame = changed_dataFrame.drop_duplicates()   

    merge_frames(planned_dataFrame, changed_dataFrame, yesterday)

    logger("info", f"Combining Data completed.")
    log_footer()

#mergeDataFrames Function
def merge_frames(planned_frame, changed_frame, date):  
    
    dataFrame = pandas.merge(planned_frame, changed_frame, on="id", how="left")
    
    dataFrame["arrival_change_time"] = dataFrame["arrival_change_time"].fillna(dataFrame["arrival_planned_time"])
    dataFrame["departure_change_time"] = dataFrame["departure_change_time"].fillna(dataFrame["departure_planned_time"])
    dataFrame["canceled"] = dataFrame["canceled"].astype("boolean").fillna(False)    

    #calculate arrival delay in minutes 
    arrival_delay_minutes = (
        dataFrame["arrival_change_time"] - dataFrame["arrival_planned_time"]
    ).dt.total_seconds()/60

    #calculate departure delay in minutes 
    departure_delay_minutes = (
        dataFrame["departure_change_time"] - dataFrame["departure_planned_time"]
    ).dt.total_seconds()/60

    #set delays 
    dataFrame["arrival_delay_min"] = arrival_delay_minutes.fillna(0)
    dataFrame["departure_delay_min"] = departure_delay_minutes.fillna(0)

    #set date 
    dataFrame["date"] = dataFrame["arrival_planned_time"].dt.strftime('%Y-%m-%d').fillna(dataFrame["departure_planned_time"].dt.strftime('%Y-%m-%d'))
    
    #remove id column
    dataFrame = dataFrame.drop("id", axis=1)

    #set relevant infos and their type for a stop
    dataFrame = dataFrame[
        [
            "station",
            "final_destination_station",
            "train_name",
            "train_type",       
            "train_line_ride_id",
            "train_line_station_num",
            "arrival_delay_min",   
            "arrival_planned_time",
            "arrival_change_time",            
            "departure_delay_min", 
            "departure_planned_time",
            "departure_change_time",    
            "canceled", 
            "weekday",
            "date",
        ]
    ].astype(
        {
            "station": "string",
            "final_destination_station": "string",
            "train_name": "string",
            "train_type": "string",    
            "train_line_ride_id": "string",
            "train_line_station_num": "int32",
            "arrival_delay_min": "int32",
            "arrival_planned_time": "datetime64[ns]", 
            "arrival_change_time": "datetime64[ns]",
            "departure_delay_min": "int32",
            "departure_planned_time": "datetime64[ns]",  
            "departure_change_time": "datetime64[ns]",
            "canceled": "boolean",
            "weekday": "string",
            "date": "datetime64[ns]",
        }
    )
    
    #create parquet file for a single day
    parquet_file = Path("daily_data")/f"{date}.parquet"
    parquet_file.parent.mkdir(parents=True, exist_ok=True)
    
    dataFrame.to_parquet(parquet_file,index=False,compression="brotli")
  
    logger("info", f"File saved as {parquet_file}")	

main()        
