import os
import base64
import requests
import wget
from dotenv import load_dotenv

load_dotenv("secrets.env")

ACCESS_KEY = os.getenv("ONSHAPE_ACCESS_KEY")
SECRET_KEY = os.getenv("ONSHAPE_SECRET_KEY")
DID = os.getenv("DOCUMENT_ID")
WVM = os.getenv("WVM")
WVMID = os.getenv("WVMID")
EID = os.getenv("EID")

token = base64.b64encode(f"{ACCESS_KEY}:{SECRET_KEY}".encode()).decode()

## Get partID
partURL = f"https://cad.onshape.com/api/v12/parts/d/{DID}/{WVM}/{WVMID}/e/{EID}?withThumbnails=false&includePropertyDefaults=false"
headers = {"Authorization": f"Basic {token}", "Accept": "application/json"}
response = requests.get(partURL, headers=headers)

# print(response.status_code, response.json())

data = response.json()
partID = data[0]["partId"]

## Get all available configuration options
configurationURL = f"https://cad.onshape.com/api/v12/elements/d/{DID}/{WVM}/{WVMID}/e/{EID}/configuration"
headers = {"Authorization": f"Basic {token}", "Accept": "application/json"}
response = requests.get(configurationURL, headers=headers)

# print(response.status_code, response.json())

data = response.json()
allConfigurationsOptions = data["configurationParameters"][0]["options"]

# print(allConfigurationsOptions)
# print(data["configurationParameters"][0]["parameterId"])

for option in allConfigurationsOptions:
    # print(option["option"])

    ## Get encoded configuration string
    encodeConfigurationURL = f"https://cad.onshape.com/api/v12/elements/d/{DID}/e/{EID}/configurationencodings"
    headers = {"Authorization": f"Basic {token}", "Accept": "application/json"}
    payload = {
        "parameters": [
            {
                "parameterId": data["configurationParameters"][0]["parameterId"],
                "parameterValue": option["option"],
            }
        ],
    }

    response = requests.post(encodeConfigurationURL, headers=headers, json=payload)

    encodedId = response.json()["encodedId"]
    queryParam = response.json()["queryParam"]

    # print(encodedId, queryParam)

    ## Export part as STL Synchronously
    getSTLURL = f"https://cad.onshape.com/api/v12/partstudios/d/{DID}/{WVM}/{WVMID}/e/{EID}/stl?partIds={partID}&version=0&includeExportIds=false&configuration={encodedId}&binaryExport=false"
    headers = {
        "Authorization": f"Basic {token}",
        "Accept": "*/*",
    }

    response = requests.get(getSTLURL, headers=headers, allow_redirects=False)

    os.makedirs("out", exist_ok=True)

    download_url = response.headers["Location"]
    print("Download URL:", download_url)

    file_path = os.path.join("out", option["optionName"] + ".stl")
    with requests.get(download_url, headers=headers, stream=True) as r:
        r.raise_for_status()
        with open(file_path, "wb") as f:
            for chunk in r.iter_content(chunk_size=8192):
                f.write(chunk)
