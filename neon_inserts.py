import os
import pandas 
import sqlalchemy
from pathlib import Path
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo
from logger_utils import setup_logger, log_header, log_footer, logger

def main():
    # Initialize logger and write header
    log = setup_logger()
    log_header()
    logger('info', 'Starting daily data load script')

    #get DB URL
    db_url = os.getenv("DATABASE_URL")
    if not db_url:
        logger('error', 'DATABASE_URL environment varaible not set')
        log_footer()
        raise Exception('DATABSE_URL environment variable not set')
    logger('info', 'Using database URL from environment')
    

    try:
        #encrypted db connection
        logger('info', 'Creating database engine')
        engine = sqlalchemy.create_engine(db_url, connect_args={"sslmode": "require"})
        logger('info', 'Database engine created successfully')
        with engine.connect() as connection:
            logger('info', 'Database connection established')
            # Encrypted DB connection
            yesterday = (datetime.now(ZoneInfo("Europe/Berlin")) - timedelta(days=1)).strftime('%y%m%d')
            file_path = Path("daily_data")/f"{yesterday}.parquet"
            #file_path = Path("daily_data")/"250628.parquet"
            logger('debug', f'Looking for parquet file: {file_path}')

            if not file_path.exists():
                logger('error', f'Parquet file not found: {file_path}')
                log_footer()
                raise FileNotFoundError(f"Parquet file not found: {file_path}")
            logger('info', f'Found parquet file: {file_path}')
            
            df = pandas.read_parquet(file_path)
            logger('info', f'Read dataframe with {len(df)} rows')

            #PROCESS stations

            logger('info', 'Processing stations')
            #drop duplicates
            stations_df = df.drop_duplicates(subset=["station"])

            #only column station
            stations_df = stations_df[["station"]]

            #rename column and sorting
            stations_df.rename(columns={"station": "station_name"}, inplace=True)
            stations_df = stations_df.sort_values(by="station_name", ascending=True)

            #get existing stations
            existing_stations = pandas.read_sql("SELECT station_name FROM stations", con=engine)

            #get new stations
            new_stations = stations_df[~stations_df["station_name"].isin(existing_stations["station_name"])]

            if not new_stations.empty:
                logger('info', f'Inserting {len(new_stations)} new stations')
                new_stations.to_sql("stations", con=engine, if_exists="append", index=False)
            else:
                logger('info', 'No new stations to insert')


            
            
            #PROCESS train types

            #drop duplicates
            train_types_df = df.drop_duplicates(subset=["train_type"])

            #only column train_type
            train_types_df = train_types_df[["train_type"]]

            #rename column and sorting
            train_types_df.rename(columns={"train_type": "train_type_name"}, inplace=True)
            train_types_df = train_types_df.sort_values(by="train_type_name", ascending=True)

            #get existing train_types
            existing_train_types = pandas.read_sql("SELECT train_type_name FROM train_types", engine)

            #get new train_types
            new_train_types = train_types_df[~train_types_df["train_type_name"].isin(existing_train_types["train_type_name"])]

            if not new_train_types.empty:
                logger('info', f'Inserting {len(new_stations)} new stations')
                new_train_types.to_sql("train_types", engine, if_exists="append", index=False)
            else:
                logger('info', 'No new stations to insert')



            #PROCESS trains
      
            #drop duplicates
            logger('info', 'Processing train types')
            trains_df = df.drop_duplicates(subset=["train_name"])

            #2 columns 
            trains_df = trains_df[["train_name", "train_type"]]

            #rename columns
            trains_df = trains_df.rename(columns={"train_type": "train_type_name"})

            #get train_types
            train_types_df = pandas.read_sql("SELECT * FROM train_types", engine)        

            #merge to get train_type_id
            trains_df = trains_df.merge(train_types_df, on="train_type_name", how="left")

            #get existing trains
            existing_trains = pandas.read_sql("SELECT train_name FROM trains", engine)

            #get new trains
            new_trains = trains_df[~trains_df["train_name"].isin(existing_trains["train_name"])]
        
            #sort
            new_trains = new_trains.sort_values(by="train_name", ascending=True)

            if not new_trains.empty:
                logger('info', f'Inserting {len(new_train_types)} new train types')
                new_trains[["train_name", "train_type_id"]].to_sql("trains", engine, if_exists="append", index=False)
            else:
                logger('info', 'No new train types to insert')




            #PROCESS train rides            

            logger('info', 'Processing train rides')
            
            #group by ride id to check if all stops got canceled -result a dataframe with ride_id and canceled
            canceled_per_ride = (
                df.groupby("train_line_ride_id")["canceled"]
                    .all()
                    .reset_index()
                    .rename(columns={"train_line_ride_id": "ride_id"})
            )

            #drop duplicates
            train_rides_df = df.drop_duplicates(subset=["train_line_ride_id"]) 

            #rename column
            train_rides_df = train_rides_df.rename(columns={"train_line_ride_id": "ride_id"})

            #remove "Old" canceled column
            train_rides_df = train_rides_df.drop(columns=["canceled"], errors="ignore")

            #merge canceled per ride on ride id
            train_rides_df = train_rides_df.merge(canceled_per_ride, on="ride_id", how="left")

            #4 columns 
            train_rides_df = train_rides_df[["ride_id", "train_name", "final_destination_station", "date", "canceled"]]

            #get trains und station
            trains_df = pandas.read_sql("SELECT train_id, train_name FROM trains", engine)
            stations_df = pandas.read_sql("SELECT * FROM stations", engine)

            #merge IDs
            train_rides_df = train_rides_df.merge(trains_df, on="train_name", how="left")
            train_rides_df = train_rides_df.merge(stations_df, left_on="final_destination_station", right_on="station_name", how="left")

            #rename column for table structure
            train_rides_df = train_rides_df.rename(columns={"station_id": "final_destination_station_id"})

            #choose only needed columns 
            train_rides_df = train_rides_df[[
                "ride_id", 
                "train_id", 
                "final_destination_station_id", 
                "date", 
                "canceled"
            ]]

            #get existing train rides
            existing_train_rides = pandas.read_sql("SELECT ride_id FROM train_rides", engine)

            #get new train rides
            new_train_rides = train_rides_df[~train_rides_df["ride_id"].isin(existing_train_rides["ride_id"])]

            if not new_train_rides.empty:
                logger('info', f'Inserting {len(new_train_rides)} new train rides')
                new_train_rides.to_sql("train_rides", engine, if_exists="append", index=False)
            else:
                logger('info', 'No new train rides to insert')



            #PROCESS stops          

            logger('info', 'Processing stops')
            #get start station - dataframe with ride_id and min_num
            start_num = df.groupby("train_line_ride_id")["train_line_station_num"].min().reset_index(name="start_num")

            #get end station - dataframe with ride_id and max_num
            end_num = df.groupby("train_line_ride_id")["train_line_station_num"].max().reset_index(name="end_num")

            #merge with original dataframe
            df = df.merge(start_num, on="train_line_ride_id", how="left")
            df = df.merge(end_num, on="train_line_ride_id", how="left")

            #set true if station_num equals start/end num 
            df["is_start"] = df["train_line_station_num"] == df["start_num"]    
            df["is_end"] = df["train_line_station_num"] == df["end_num"]
        
            #remove columns
            df = df.drop(columns=[
                "start_num", 
                "end_num",
                "weekday",
                "date",
                "train_type", 
                "train_name",
                "final_destination_station",            
                "train_name",
                "train_type"
            ])

            #rename columns for table structure
            stops_df = df.rename(columns={
                "train_line_ride_id": "ride_id",
                "train_line_station_num": "station_num",
            })

            #get stations and merge 
            stations_df = pandas.read_sql("SELECT * FROM stations", engine)
            stops_df = stops_df.merge(stations_df, left_on="station", right_on="station_name", how="left")

            #remove columns
            stops_df = stops_df.drop(columns=[
                "station_name",
                "station"
            ])

            #get existing stops
            existing_stops = pandas.read_sql("SELECT ride_id, station_id FROM stops", engine)

            #create keys for comparison
            stops_df["key"] = stops_df["ride_id"].astype(str) + "-" + stops_df["station_id"].astype(str)
            existing_stops["key"] = existing_stops["ride_id"].astype(str) + "-" + existing_stops["station_id"].astype(str)

            #get new stops
            new_stops = stops_df[~stops_df["key"].isin(existing_stops["key"])]

            #remove key column 
            new_stops = new_stops.drop(columns=["key"], errors="ignore")

            if not new_stops.empty:
                logger('info', f'Inserting {len(new_stops)} new stops')
                new_stops.to_sql("stops", engine, if_exists="append", index=False)  
            else:
                logger('info', 'No new stops to insert')
            

    except Exception as e:
        logger('error', f'Unhandled exception: {e}')
        log_footer()
        exit(1)

    # Write footer and exit
    logger('info', 'Daily data load script completed successfully')
    log_footer()

if __name__ == "__main__":
    main()


