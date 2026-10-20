import logging

from orbit.exceptions import ValidationError
from orbit.extract import extract
from orbit.load import load
from orbit.validate import validate

log = logging.getLogger("orbit")

def main():
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    try:
        payload = extract()
        validate(payload)
        load(payload)
        log.info("loaded: %s",payload["timestamp"])
    except ValidationError as e:
        log.error("rejected reading: %s",e)
        raise SystemExit(1)
    

if __name__ == "__main__":
    main()
