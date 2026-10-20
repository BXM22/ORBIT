import requests

from orbit.config import API

def extract():
    resp = requests.get(API,timeout = 10) #request and timesout for 10 sec
    resp.raise_for_status()
    return resp.json() #getting the data
