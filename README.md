# Custom MCP ArcGIS

## Requirements
- ArcGIS Pro 3.7
- Python
- An ArcGIS API key

## Setup
```bash
pip install -r requirements.txt
```
Run (exact command):
```bash
fastmcp run -t streamable-http --host 0.0.0.0 -p 8000 mcp_server.py
```

Then open http://localhost:8000/mcp.

## Configuration
**Copy `.env.sample` to `.env`**. Set the value for variables.
```
MCP_SERVER_NAME=
API_KEY=
GEOCODE_FIND_ADDRESS_URL=
ARCGIS_WORKSPACE=
TEMPORARY_DIR=
```

**ArcGIS API key**
1. Sign in at https://location.arcgis.com or https://www.arcgis.com (an ArcGIS Location Platform or ArcGIS Online account).
2. Go to **Credentials → API key credentials → Create API key**.
3. Enable the Location services. 