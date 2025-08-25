# Onshape Bulk Export Configurations

This script uses the Onshape API to export all configurations to an out/ directory.

Credit to ([ZimengXiong](https://github.com/ZimengXiong)), project was based on their repo https://github.com/ZimengXiong/OnshapeBulkExportConfigurations

Git clone/download the repository

Create an secrets.env file with the following:

```
ONSHAPE_ACCESS_KEY=
ONSHAPE_SECRET_KEY=
```

Generate an API Key by going to the [Onshape Dev Portal](https://cad.onshape.com/appstore/dev-portal)

Open a part studio and copy the URL:

```
https://cad.onshape.com/documents/<Document ID>/w/<WVMID>/e/<EID>
```

Run

```bash
python3 -m venv .venv
source .venv/bin/activate

pip3 install -r requirements.txt
python3 ExportOnshapeConfigs.py
```

When prompted, enter your document URL then select the output format

## Program Overview

This script automates exporting **all configurations** of an Onshape Part Studio or Assembly into selected CAD formats.  

### Key Steps
1. **User Input**  
   - Prompt for Onshape document link.  
   - Prompt for desired export format (`STEP`, `OBJ`, `GLTF`, `SolidWorks`).  

2. **Document Parsing**  
   - Extract document/workspace/version/element IDs from the provided link.  
   - Detect whether the element is a Part Studio or Assembly.  

3. **Configuration Retrieval**  
   - Query the Onshape API to get all available configuration options.  

4. **Export Loop**  
   For each configuration:  
   - Encode configuration ID.  
   - Build the appropriate export URL (different for Part Studios vs Assemblies).  
   - Create an export request with format-specific parameters.  
   - Poll the Onshape API until translation/export is complete.  
   - Download the exported file to the `out/` directory.  

5. **Output**  
   - Each configuration is saved as a separate file named after its configuration option.  
   - All exports are stored in the `out/` folder.  

### Highlights
- Supports **multiple export formats**.  
- Handles **both Part Studios and Assemblies**.  
- Automatically polls until the export is complete.  
- Saves results locally with descriptive filenames.  

### Furtue Upgrades
 - Drawing
 - STLs
 - Any filetype