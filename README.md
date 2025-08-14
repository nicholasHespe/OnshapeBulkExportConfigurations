# Onshape Bulk Export Part Studio Configurations

This script uses the Onshape API to export all part studio configurations as STLs to an out/ directory.

Create an secrets.env file with the following:

```
ONSHAPE_ACCESS_KEY=
ONSHAPE_SECRET_KEY=
DOCUMENT_ID=
WVM=w
WVMID=
EID=
```

Generate an API Key by going to the [Onshape Dev Portal](https://cad.onshape.com/appstore/dev-portal)

Open a part studio and note the URL:

```
https://cad.onshape.com/documents/<Document ID>/w/<WVMID>/e/<EID>
```

The script will grab the FIRST part in the part studio.

## How it works

```
1. Use the parts endpoint to grab the partID:
    partURL = f"https://cad.onshape.com/api/v12/parts/d/{DID}/{WVM}/{WVMID}/e/{EID}?withThumbnails=false&includePropertyDefaults=false"

2. Get all configurations for the part studio
    configurationURL = f"https://cad.onshape.com/api/v12/elements/d/{DID}/{WVM}/{WVMID}/e/{EID}/configuration"

    data = response.json()
    allConfigurationsOptions = data["configurationParameters"][0]["options"]

3. For each option, encode a configuration string to use for API requests
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

4. Get a 307 redirect URL for each option with the encoded configuration string
    getSTLURL = f"https://cad.onshape.com/api/v12/partstudios/d/{DID}/{WVM}/{WVMID}/e/{EID}/stl?partIds={partID}&version=0&includeExportIds=false&configuration={encodedId}&binaryExport=false"
    headers = {
        "Authorization": f"Basic {token}",
        "Accept": "*/*",
    }

    response = requests.get(getSTLURL, headers=headers, allow_redirects=False)

5. Authenticate and stream the redirect file
    download_url = response.headers["Location"]
    print("Download URL:", download_url)

    file_path = os.path.join("out", option["optionName"] + ".stl")
    with requests.get(download_url, headers=headers, stream=True) as r:
        r.raise_for_status()
        with open(file_path, "wb") as f:
            for chunk in r.iter_content(chunk_size=8192):
                f.write(chunk)


```
