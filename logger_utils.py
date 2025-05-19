# logger_utils.py
import logging
import os
import inspect
from pathlib import Path
from datetime import datetime
from zoneinfo import ZoneInfo


# Skriptname für Format
caller_script = os.path.basename(inspect.stack()[-1].filename)

def setup_logger():
    # Log-Dateiname erzeugen
    date_str = datetime.now(ZoneInfo("Europe/Berlin")).strftime("%y%m%d")
    log_filename = f"logs/{date_str}.txt"

    # logs-Ordner anlegen
    Path("logs").mkdir(exist_ok=True)

    # Format definieren
    log_format = "%(asctime)s %(levelname)s %(message)s"

    # Logger konfigurieren (nur 1× pro Laufzeit)
    logging.basicConfig(
        level=logging.INFO,
        format=log_format,
        datefmt='%Y-%m-%d %H:%M:%S',
        handlers=[
            logging.FileHandler(log_filename, encoding="utf-8"),
            logging.StreamHandler()
        ]
    )

    return logging.getLogger()

def logger(type, logstring):
	
    #logtime = datetime.now(ZoneInfo("Europe/Berlin")).strftime("%H:%M:%S")
    log_methods = {
        "error": logging.error,
        "warning": logging.warning,
        "info": logging.info,
        "debug": logging.debug
    }

    log_func = log_methods.get(type, logging.debug)
    #log_func(f"{logtime}: {logstring}")
    log_func(f"{logstring}")

def raw_log(msg):
    for handler in logging.getLogger().handlers:
        handler.stream.write(msg + '\n')
        handler.flush()

def log_header():
    now = datetime.now(ZoneInfo("Europe/Berlin")).strftime('%Y-%m-%d %H:%M:%S')
    for handler in logging.getLogger().handlers:
        handler.stream.write(f"----- [{caller_script}] Start:{now} ------\n")
        handler.flush()

def log_footer():
    now = datetime.now(ZoneInfo("Europe/Berlin")).strftime('%Y-%m-%d %H:%M:%S')
    for handler in logging.getLogger().handlers:
        handler.stream.write(f"----- [{caller_script}] End:{now} ------\n")
        handler.flush()


# def log_header2():
    # timestamp = datetime.now(ZoneInfo("Europe/Berlin")).strftime("%Y-%m-%d %H:%M:%S")
    # header = f"----- [{caller_script}] Start:{timestamp} ------"
    # print(header)
    # logging.info(header)  # write it to file and terminal



# def log_footer2():
    # timestamp = datetime.now(ZoneInfo("Europe/Berlin")).strftime("%Y-%m-%d %H:%M:%S")
    # footer = f"----- [{caller_script}] End:{timestamp} ------"
    # print(footer)
    # logging.info(footer)
    # logging.info(footer)


def checklogs():
    #create path to a folder if not existing
    folder = Path("logs")
    folder.mkdir(exist_ok=True, parents=True)
	

    date = datetime.now(ZoneInfo("Europe/Berlin")).strftime("%Y-%m-%d").replace("-", "")[2:]

    file_path = Path("logs") / f"{date}.txt"
    if file_path.is_file():
        print(f"{file_path.name} exists.")
    else:
        print(f"{file_path.name} does not exist.")
	
    #setup plan url
    url = plan_url.format(eva=eva, date=date, hour=f"{hour:02}")
    file_path = folder/f"{date}.txt"

	
	
def check_connection(url):
    try:
        response = requests.get(url, timeout=10)  # Timeout in case the request takes too long
        if response.status_code == 200:
            logger("info", f"Successfully connected to {url}")
        else:
            logger("error", f"Failed to connect to {url} with status code {response.status_code}")
    except requests.exceptions.RequestException as e:
        # This will catch any exception related to the request (e.g., network issues, invalid URL)
        logger("error", f"Error occurred while connecting to {url}: {e}")
