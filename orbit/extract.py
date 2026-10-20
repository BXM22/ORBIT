from math import log
import requests
import logging

from orbit.config import API

log=logging.getLogger(__name__)

def extract():
    try:
        resp = requests.get(API,timeout = 10) #request and timesout for 10 sec
        resp.raise_for_status()
    except requests.RequestException:
        log.exception("API request failed")
        raise
    
    return resp.json() #getting the data
