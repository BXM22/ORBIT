from orbit.extract import extract
from orbit.validate import validate
from orbit.load import load

def main():
    payload = extract()
    validate(payload)
    load(payload)
    print("loaded", payload["timestamp"])

if __name__ == "__main__":
    main()
