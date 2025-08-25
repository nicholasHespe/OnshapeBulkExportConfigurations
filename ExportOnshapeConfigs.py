import os
import base64
import requests
import time
import json
import zipfile
from dotenv import load_dotenv

load_dotenv("secrets.env")

ACCESS_KEY = os.getenv("ONSHAPE_ACCESS_KEY")
SECRET_KEY = os.getenv("ONSHAPE_SECRET_KEY")

token = base64.b64encode(f"{ACCESS_KEY}:{SECRET_KEY}".encode()).decode()
headers_json = {"Authorization": f"Basic {token}", "Accept": "application/json"}

# ----------------------------------------------------------------------
# Step 0a: Ask user for document link
# ----------------------------------------------------------------------

print("Please enter the OnShape document link (e.g. https://cad.onshape.com/documents/xxxx/w/yyyy/e/zzzz):")
doc_link = input("Link: ").strip()
if not doc_link:
    raise Exception("No link provided")

# Parse the link to extract DID, WVM, WVMID, EID
try:
    parts = doc_link.split("/")
    DID = parts[4]
    WVM = parts[5]
    WVMID = parts[6]
    EID = parts[8]
except Exception as e:
    raise Exception("Invalid link format") from e

# ----------------------------------------------------------------------
# Step 0b: Ask user for export type
# ----------------------------------------------------------------------
print("Please select file format:")
print("1 - step")
print("2 - obj")
print("3 - gltf")
print("4 - solidworks")

choice = input("Enter number: ").strip()
export_map = {
    "1": ("step", "step"),
    "2": ("obj", "obj"),
    "3": ("gltf", "gltf"),
    "4": ("sldprt", "sldprt"),
}

if choice not in export_map:
    raise Exception("Invalid choice")

export_format, file_ext = export_map[choice]
print(f"Selected export format: {export_format}")

# ----------------------------------------------------------------------
# Step 1: Detect element type (Part Studio vs Assembly)
# ----------------------------------------------------------------------
elementURL = f"https://cad.onshape.com/api/v12/documents/d/{DID}/w/{WVMID}/elements"
response = requests.get(elementURL, headers=headers_json)
response.raise_for_status()
elements = response.json()

elementType = None
for e in elements:
    if e["id"] == EID:
        elementType = e["elementType"]
        break

if not elementType:
    raise Exception(f"Could not find element {EID} in document {DID}")

print("Element type:", elementType)

# ----------------------------------------------------------------------
# Step 2: For Part Studios, get partId (Assemblies don't need this)
# ----------------------------------------------------------------------
partID = None
if elementType == "PARTSTUDIO":
    partURL = f"https://cad.onshape.com/api/v12/parts/d/{DID}/{WVM}/{WVMID}/e/{EID}?withThumbnails=false&includePropertyDefaults=false"
    response = requests.get(partURL, headers=headers_json)
    response.raise_for_status()
    data = response.json()
    partID = data[0]["partId"]

# ----------------------------------------------------------------------
# Step 3: Get all configuration options (works for both Part Studios & Assemblies)
# ----------------------------------------------------------------------
print("Getting all configs...")
configurationURL = f"https://cad.onshape.com/api/v12/elements/d/{DID}/{WVM}/{WVMID}/e/{EID}/configuration"
response = requests.get(configurationURL, headers=headers_json)
response.raise_for_status()
configData = response.json()

print("Configuration data:", json.dumps(configData, indent=2))

allConfigurationsOptions = configData["configurationParameters"][0]["options"]
parameterId = configData["configurationParameters"][0]["parameterId"]

# ----------------------------------------------------------------------
# Step 4: Loop over configs, encode them, export file
# ----------------------------------------------------------------------
os.makedirs("out", exist_ok=True)

print(f"Found {len(allConfigurationsOptions)} configurations")
#print(allConfigurationsOptions)

for option in allConfigurationsOptions:
    if option['option'] == "Default":
        continue  # Skip default config if present
    print(f"\nProcessing configuration: {option['optionName']}")
    
    # Encode config
    encodeConfigurationURL = f"https://cad.onshape.com/api/v12/elements/d/{DID}/e/{EID}/configurationencodings"
    payload = {
        "parameters": [
            {
                "parameterId": parameterId,
                "parameterValue": option["option"],
            }
        ],
    }
    configResponse = requests.post(encodeConfigurationURL, headers=headers_json, json=payload)
    configResponse.raise_for_status()
    print(configResponse.json())



    # ------------------------------------------------------------------
    # Step 4a: Build export URL depending on element type and format
    # ------------------------------------------------------------------
    
    if elementType == "PARTSTUDIO":
        # For Part Studios, use the parts export endpoint
        if export_format == "sldprt":
            export_url = f"https://cad.onshape.com/api/v12/partstudios/d/{DID}/{WVM}/{WVMID}/e/{EID}/export/solidworks"
        else:
            export_url = f"https://cad.onshape.com/api/v12/partstudios/d/{DID}/{WVM}/{WVMID}/e/{EID}/export/{export_format}"
    else:  # ASSEMBLY
        # For Assemblies, use the assemblies export endpoint
        if export_format == "sldprt":
            export_url = f"https://cad.onshape.com/api/v12/assemblies/d/{DID}/{WVM}/{WVMID}/e/{EID}/export/solidworks"
        else:
            export_url = f"https://cad.onshape.com/api/v12/assemblies/d/{DID}/{WVM}/{WVMID}/e/{EID}/export/{export_format}"
    
    # Add configuration to URL
    if configResponse.json()["queryParam"]:
        export_url += f"?{configResponse.json()["queryParam"]}"

    #export_url = export_url.replace("=", "%3D")
    print(f"Export URL: {export_url}")
    
    # ------------------------------------------------------------------
    # Step 4b: Prepare export request body
    # ------------------------------------------------------------------
    
    export_payload = {
        "storeInDocument": False,  # Changed to False for direct download URLs
        "notifyUser": False,
        "grouping": True,
    }
    
    # Add format-specific parameters
    if export_format in ["obj", "gltf"]:
        # Mesh formats need mesh parameters
        export_payload["meshParams"] = {
            "angularTolerance": 0.1,
            "distanceTolerance": 0.1,
            "maximumChordLength": 1.0,
            "resolution": "FINE",
            "unit": "METER"
        }

    
    # For Part Studios, we need to specify which part(s) to export
    # if elementType == "PARTSTUDIO" and partID:
    #     export_payload["partIds"] = [partID]
    
    print(f"Export payload: {json.dumps(export_payload, indent=2)}")
    
    # ------------------------------------------------------------------
    # Step 4c: Make the export request
    # ------------------------------------------------------------------
    
    print("Initiating export...")
    export_response = requests.post(export_url, headers=headers_json, json=export_payload)
    export_response.raise_for_status()
    translation_data = export_response.json()
    translation_id = translation_data["id"]
    
    #print(f"Translation ID: {translation_id}")
    
    # ------------------------------------------------------------------
    # Step 4d: Poll translation status until complete
    # ------------------------------------------------------------------
    
    translation_status_url = f"https://cad.onshape.com/api/v12/translations/{translation_id}"
    print("Polling translation status...", end="", flush=True)
    
    max_attempts = 60  # Maximum number of polling attempts
    attempt = 0
    
    while attempt < max_attempts:
        status_response = requests.get(translation_status_url, headers=headers_json)
        status_response.raise_for_status()
        status_data = status_response.json()
        
        request_state = status_data["requestState"]
        
        if request_state == "DONE":
            print("   Translation completed successfully!")
            break
        elif request_state == "FAILED":
            failure_reason = status_data.get("failureReason", "Unknown error")
            raise Exception(f"Translation failed: {failure_reason}")
        elif request_state == "ACTIVE":
            print(".", end="", flush=True)
            time.sleep(1)  # Wait 1 second before next poll
            attempt += 1
        else:
            print(f"Unknown state: {request_state}, continuing to poll...")
            time.sleep(1)
            attempt += 1
    
    if attempt >= max_attempts:
        raise Exception("Translation timed out - took too long to complete")
    
    # ------------------------------------------------------------------
    # Step 4e: Download the exported file
    # ------------------------------------------------------------------
    
    # When storeInDocument=False, OnShape provides direct download URLs
    # These are found in the "resultExternalDataIds" field instead of "resultElementIds"
    
    result_external_data_ids = status_data.get("resultExternalDataIds", [])
    if not result_external_data_ids:
        raise Exception("No external data IDs found in completed translation")
    
    external_data_id = result_external_data_ids[0]  # Take the first result
    print(f"External data ID: {external_data_id}")
    print(result_external_data_ids)
    
    # Get the download URL using the external data endpoint
    download_info_url = f"https://cad.onshape.com/api/v6/documents/d/{DID}/externaldata/{external_data_id}"
    
    print(f"Downloding exported file... from {download_info_url}")
    download_info_response = requests.get(download_info_url, headers=headers_json)
    download_info_response.raise_for_status()
    
    if download_info_response.status_code == 200:
        safe_config_name = "".join(c for c in option["option"] if c.isalnum() or c in (' ', '-', '_')).rstrip()
        if export_format in ["obj", "gltf"]:
            # For mesh formats, OnShape returns a zip file
            filename = f"{safe_config_name}.zip"
            filepath = os.path.join("out", filename)
        
            # Save the downloaded zip file
            with open(filepath, "wb") as f:
                f.write(download_info_response.content)
            
            # Unzip the file
            print(f"Unzipping {filename}...")
            with zipfile.ZipFile(filepath, 'r') as zip_ref:
                # Create a subfolder with the configuration name
                extract_path = os.path.join("out", safe_config_name)
                os.makedirs(extract_path, exist_ok=True)
                zip_ref.extractall(extract_path)
            
            # Remove the zip file after extraction
            os.remove(filepath)
            print(f"Files extracted to: {extract_path}")
            filepath = extract_path  # Update filepath to the folder
        else:        
            # Create filename based on configuration and format
            filename = f"{safe_config_name}.{file_ext}"
            filepath = os.path.join("out", filename)
            
            # Save the downloaded file
            with open(filepath, "wb") as f:
                f.write(download_info_response.content)

        print(f"File saved as: {filepath}")
        print(f"File size: {os.path.getsize(filepath)} bytes")
    else:
        raise Exception(f"Failed to get download URL. Status: {download_info_response.status_code}")
    break  # Process only the first configuration for testing
    

print(f"\nAll configurations exported successfully!")
print(f"Files saved in the 'out' directory.")