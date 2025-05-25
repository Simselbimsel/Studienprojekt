
CREATE TABLE IF NOT EXISTS stations (
    station_id SERIAL PRIMARY KEY,
    station_name VARCHAR(64) NOT NULL
);

CREATE TABLE IF NOT EXISTS train_types (
    train_type_id SERIAL PRIMARY KEY,
    train_type_name VARCHAR(64) NOT NULL
);

CREATE TABLE IF NOT EXISTS trains (
    train_id SERIAL PRIMARY KEY,
    train_name VARCHAR(50) NOT NULL,
    train_type_id INT NOT NULL REFERENCES train_types (train_type_id)
);

CREATE TABLE IF NOT EXISTS train_rides (
    ride_id VARCHAR(64) PRIMARY KEY, 
    train_id INT REFERENCES trains(train_id),
    final_destination_station_id INT REFERENCES stations (station_id),
    date DATE NOT NULL,    
    canceled BOOLEAN DEFAULT FALSE	
);


CREATE TABLE IF NOT EXISTS stops (
    stop_id SERIAL PRIMARY KEY, 
    ride_id VARCHAR(64) REFERENCES train_rides (ride_id),
    station_id INT REFERENCES stations (station_id),
    station_num INT NOT NULL,
    is_start BOOLEAN DEFAULT FALSE,
    is_end BOOLEAN DEFAULT FALSE,
    canceled BOOLEAN DEFAULT FALSE,

    arrival_planned_time TIMESTAMP,
    arrival_change_time TIMESTAMP,
    arrival_delay_min INT,

    departure_planned_time TIMESTAMP,
    departure_change_time TIMESTAMP,
    departure_delay_min INT
);
