import os
from dotenv import load_dotenv

load_dotenv()

API = "https://api.wheretheiss.at/v1/satellites/25544"
DSN = os.environ.get("ORBIT_DSN","postgresql://postgres:postgres@localhost:5432/iss")