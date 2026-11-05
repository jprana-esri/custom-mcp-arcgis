import json
import uuid
import datetime
import os
from typing import List

from arcgis.features import FeatureLayer, FeatureLayerCollection
from mcp.server import MCPServer
from arcgis.gis import GIS, SharingLevel
from dotenv import load_dotenv

import httpx

# Constants variables
load_dotenv(dotenv_path='.env')
SERVER_NAME = os.getenv("MCP_SERVER_NAME")
API_KEY = os.getenv("API_KEY")
GEOCODE_FIND_ADDRESS_URL = os.getenv("GEOCODE_FIND_ADDRESS_URL")
# example = r"C:\Users\<Username>\Documents\ArcGIS\Projects\MyProject\MyProject.gdb"
ARCGIS_WORKSPACE = os.getenv("ARCGIS_WORKSPACE")
# example = r"D:\projects\python\custom-mcp-arcgis"
TEMPORARY_DIR = os.getenv("TEMPORARY_DIR")

# Import arcpy modules
print(datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"), "import arcpy modules...")
from arcpy import env, Exists, analysis, management, conversion, ExecuteError, GetMessage, GetMessageCount

# Set environment settings
print(datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"), "set workspace environment...")
env.workspace = ARCGIS_WORKSPACE

# Initialize MCPServer
print(datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"), "initialize MCPServer...")
mcp = MCPServer(SERVER_NAME)

@mcp.tool()
async def get_coordinates(address: str) -> str:
    """Get/find coordinates from address (city, country, street name, etc).

    Args:
        address: string of address (e.g. Capital Building, Jakarta, Indonesia)
    """
    token = API_KEY
    params = {
        "f": "json",
        "token": token,
        "SingleLine": address
    }

    async with httpx.AsyncClient() as client:
        try:
            response = await client.get(GEOCODE_FIND_ADDRESS_URL, params=params)
            response.raise_for_status()
            x = response.json()["candidates"][0]["location"]["x"]
            y = response.json()["candidates"][0]["location"]["y"]
            return f"""\ncoordinate of address is {x}, and {y}\n"""
        except Exception:
            return "not coordinates found"

@mcp.tool(description="long running task")
async def create_webmap(location: str, basemap: str, title: str, description: str, layers: List[str]) -> str:
    """Create a new ArcGIS Web map item by location, type of basemap, title, description, and layers.

    Args:
        location: string of location name (e.g. Jakarta, Bundaran HI, Senayan, etc)
        basemap: string of arcgis basemap name for webmap
        title: title of webmap
        description: description of webmap
        layers: lisf of feature layer url to add to webmap
    """
    # tags: list of tags associated with webmap

    gis = GIS('home')
    webmap = gis.map(location)
    webmap.basemap.basemap = basemap

    for layer in layers:
        if layer is not None:
            flc = FeatureLayerCollection(layer)
            layer_item = gis.content.get(flc.properties.serviceItemId)
            if layer_item is not None:
                webmap.content.add(layer_item)

    # Create folder if it doesn't exist
    folder_name = 'mcp'
    folder = gis.content.folders.get(folder=folder_name)

    if folder is None:
        folder = gis.content.folders.create(
            folder=folder_name,
            exist_ok=True
        )

    tags = []
    mcp_tag = 'mcp'
    if mcp_tag.lower() not in [tag.lower() for tag in tags]:
        tags.append(mcp_tag)
    webmap_properties = {'title': title,
                         'snippet': description,
                         'description': description,
                         'tags': tags}
    webmap_item = webmap.save(webmap_properties, thumbnail='./webmap_thumbnail.png', folder=gis)
    webmap_item.sharing.sharing_level = SharingLevel.EVERYONE
    return f"link to view a new webmap is {gis.url}apps/mapviewer/index.html?webmap={webmap_item.id}"

# Status = Experimental
@mcp.tool(description="Experimental tool")
async def create_dashboard(webmap_url: str, title: str) -> str:
    """Create a new ArcGIS Dashboard item by ArcGIS Web map url.

    Args:
        webmap_url: ArcGIS Web map url
        title: title of ArcGIS Dashboard
    """

    gis = GIS("home")

    webmap_candidate = None
    if "webmap=" in webmap_url:
        webmap_candidate = webmap_url.split("webmap=")[-1]
    elif "id=" in webmap_url:
        webmap_candidate = webmap_url.split("id=")[-1]

    if webmap_candidate and len(webmap_candidate) == 32:
        webmap_item_id = webmap_candidate
    else:
        return f"invalid webmap url: {webmap_url}"

    webmap_item = gis.content.get(webmap_item_id)
    webmap_name = webmap_item.title
    layer_id = None
    for layer in webmap_item.get_data()["operationalLayers"]:
        layer_id = str(layer.get("id"))

    map_widget_id = str(uuid.uuid4())
    legend_widget_id = str(uuid.uuid4())
    pie_chart_widget_id = str(uuid.uuid4())

    legend_chart_title = "Legenda"
    pie_chart_title = "Pie Chart Warna"
    pie_chart_group_by_field = "warna"

    dashboard_text = {"version": "5.0.0", "desktopView": {"layout": {"type": "dockingLayout",
                                                                     "rootElement": {"width": 1, "height": 1,
                                                                                     "type": "stackLayoutElement",
                                                                                     "orientation": "row", "elements": [
                                                                             {"width": 1, "height": 0.75,
                                                                              "type": "groupLayoutElement",
                                                                              "orientation": "col", "elements": [
                                                                                 {"width": 0.18, "height": 1,
                                                                                  "type": "itemLayoutElement",
                                                                                  "id": legend_widget_id},
                                                                                 {"width": 0.82, "height": 1,
                                                                                  "type": "itemLayoutElement",
                                                                                  "id": map_widget_id}]},
                                                                             {"width": 1, "height": 0.25,
                                                                              "type": "stackLayoutElement",
                                                                              "orientation": "col", "elements": [
                                                                                 {"width": 1, "height": 1,
                                                                                  "type": "itemLayoutElement",
                                                                                  "id": pie_chart_widget_id}]}]}},
                                                          "type": "desktop", "widgets": [
            {"id": map_widget_id, "name": webmap_name, "type": "mapWidget", "itemId": webmap_item_id,
             "mapTools": [{"type": "legendTool"}, {"type": "searchTool"}, {"type": "basemapGalleryTool"},
                          {"type": "bookmarksTool"}, {"type": "mapContentsTool"}], "showMeasureTool": True,
             "showNavigation": True, "showPanRotate": False, "showLocate": True, "showCompass": True, "showPopup": True,
             "scalebarStyle": "ruler",
             "selectTool": {"type": "selectTool", "clickToSelect": False, "advanceSketchTools": []}},
            {"id": legend_widget_id, "name": "Map legend", "title": legend_chart_title, "showLastUpdate": False,
             "type": "legendWidget", "mapWidgetId": map_widget_id},
            {"id": pie_chart_widget_id, "name": "Pie chart", "title": pie_chart_title, "showLastUpdate": False,
             "datasets": [{"type": "serviceDataset", "name": "main",
                           "dataSource": {"type": "layerDataSource", "itemId": webmap_item_id, "layerId": layer_id},
                           "groupByFields": [pie_chart_group_by_field], "orderByFields": [], "statisticDefinitions": [
                     {"onStatisticField": "OBJECTID", "statisticType": "count",
                      "outStatisticFieldName": "COUNT_OBJECTID"}], "outFields": ["*"], "returnDistinctValues": False,
                           "allowSourceDownload": False, "allowSummaryDownload": False}], "actionMode": "monoSelection",
             "categoryType": "groupByValues", "type": "pieChartWidget",
             "chartConfig": {"version": "25.0.0", "type": "chart", "orderOptions": {}, "colorMatch": True,
                             "chartRenderer": {"type": "uniqueValue", "field1": pie_chart_group_by_field, "uniqueValueInfos": [
                                 {"label": "hijau",
                                  "symbol": {"type": "esriSFS", "style": "esriSFSSolid", "color": [20, 158, 206, 255],
                                             "outline": {"type": "esriSLS", "style": "esriSLSSolid", "width": 0}},
                                  "value": "hijau"}, {"label": "kuning",
                                                      "symbol": {"type": "esriSFS", "style": "esriSFSSolid",
                                                                 "color": [0, 122, 194, 255],
                                                                 "outline": {"type": "esriSLS", "style": "esriSLSSolid",
                                                                             "width": 0}}, "value": "kuning"},
                                 {"label": "merah",
                                  "symbol": {"type": "esriSFS", "style": "esriSFSSolid", "color": [167, 198, 54, 255],
                                             "outline": {"type": "esriSLS", "style": "esriSLSSolid", "width": 0}},
                                  "value": "merah"}, {"label": "putih",
                                                      "symbol": {"type": "esriSFS", "style": "esriSFSSolid",
                                                                 "color": [158, 85, 156, 255],
                                                                 "outline": {"type": "esriSLS", "style": "esriSLSSolid",
                                                                             "width": 0}}, "value": "putih"},
                                 {"label": "null",
                                  "symbol": {"type": "esriSFS", "style": "esriSFSSolid", "color": [214, 214, 214, 255],
                                             "outline": {"type": "esriSLS", "style": "esriSLSSolid", "width": 0}},
                                  "value": None}, {"label": "blank",
                                                   "symbol": {"type": "esriSFS", "style": "esriSFSSolid",
                                                              "color": [214, 214, 214, 255],
                                                              "outline": {"type": "esriSLS", "style": "esriSLSSolid",
                                                                          "width": 0}}, "value": ""}]}, "series": [
                     {"type": "pieSeries", "id": "main", "name": "main", "x": pie_chart_group_by_field,
                      "dataLabels": {"type": "chartText", "visible": True, "content": {"type": "esriTS", "angle": 0,
                                                                                       "font": {"family": "inherit",
                                                                                                "style": "normal",
                                                                                                "weight": "normal"}}},
                      "dataTooltipVisible": True, "dataTooltipReverseColor": True,
                      "optimizeDataLabelsOverlapping": True, "alignDataLabels": True, "innerRadius": 0,
                      "startAngle": 270, "y": "COUNT_OBJECTID", "ticks": {"type": "pieTick",
                                                                          "lineSymbol": {"type": "esriSLS",
                                                                                         "style": "esriSLSSolid",
                                                                                         "color": [214, 214, 214,
                                                                                                   127.5]}},
                      "fillSymbol": {"type": "esriSFS", "style": "esriSFSSolid", "color": [214, 214, 214, 255],
                                     "outline": {"type": "esriSLS", "style": "esriSLSSolid", "width": 0}},
                      "dataLabelsOffset": 10, "sliceGrouping": {"sliceId": "__other-slice__", "percentageThreshold": 0,
                                                                "fillSymbol": {"type": "esriSFS",
                                                                               "style": "esriSFSSolid",
                                                                               "color": [214, 214, 214, 255],
                                                                               "outline": {"type": "esriSLS",
                                                                                           "style": "esriSLSSolid",
                                                                                           "width": 0}}}}],
                             "legend": {"type": "chartLegend", "visible": False, "body": {"type": "esriTS", "angle": 0,
                                                                                          "font": {"family": "inherit",
                                                                                                   "size": 11,
                                                                                                   "style": "normal",
                                                                                                   "weight": "normal"}},
                                        "position": "bottom", "displayPercentage": False, "displayNumericValue": True,
                                        "labelMaxWidth": 100, "valueLabelMaxWidth": 50}},
             "dataLabelsFormat": "percentage",
             "valueFormat": {"name": "value", "prefix": True, "style": "decimal", "useGrouping": True,
                             "maximumFractionDigits": 1},
             "percentageFormat": {"name": "percentage", "prefix": False, "style": "percent", "useGrouping": True,
                                  "maximumFractionDigits": 2}}], "settings": {"allowElementResizing": False,
                                                                              "allowElementExpansion": False,
                                                                              "allowReset": False}},
                      "mobileView": {"layout": {"type": "dockingLayout"}, "type": "mobile", "widgets": [],
                                     "settings": {"allowElementResizing": False, "allowElementExpansion": False,
                                                  "allowReset": False}}, "elementMappings": {}}
    dashboard_properties = {
        "title": title,
        "type": "Dashboard",
        "tags": ["mcp", "dashboard"],
        "text": json.dumps(dashboard_text)
    }

    dashboard_item = gis.content.add(item_properties=dashboard_properties)
    dashboard_item.sharing.sharing_level = SharingLevel.EVERYONE
    return f"link to view a new dashboard is {gis.url}apps/dashboards/{dashboard_item.id}"

@mcp.tool()
async def query_feature_layer(fs_url: str) -> str:
    """Query from ArcGIS Feature Layer (without layer index).

    Args:
        fs_url: ArcGIS Feature Layer url (without layer index)
    """

    gis = GIS("home")

    try:
        feature_layer_collection = FeatureLayerCollection(fs_url, gis)
        if feature_layer_collection is None:
            return "Invalid ArcGIS Feature Layer url"

        if not feature_layer_collection.layers:
            return "Invalid ArcGIS Feature Layer url"

        result = "Empty result"
        for layer in feature_layer_collection.layers:
            url = fs_url + "/" + str(layer.properties.id)
            feature_layer = FeatureLayer(url)
            result = feature_layer.query(where='1=1', out_fields='*', return_geometry=False)
            break
        return f"{result}"
    except Exception:
        return "Invalid ArcGIS Feature Layer url"

@mcp.tool()
async def buffer(input_feature_name: str) -> dict:
    """Create buffer area around arcgis features data inside an arcgis feature class

    Args:
        input_feature_name: ArcGIS Feature Class Name.
    """
    str_id = uuid.uuid4()
    pid = os.getpid()
    try:
        start_datetime = datetime.datetime.now()

        # Check if feature exists
        print(datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"), f"check if feature exists ${str_id} ${pid}...")
        if not Exists(input_feature_name):
            return {"message": "Feature not found"}

        gdb_name = f"Output_{pid}.gdb"
        gdb_base_dir = TEMPORARY_DIR
        output_gdb_path: str = os.path.join(gdb_base_dir, gdb_name)

        # Check if output GDB exists
        if not Exists(output_gdb_path):
            # Run CreateFileGDB tool
            print(datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                  f"running create file gdb tool ${str_id} ${pid}...")
            management.CreateFileGDB(
                gdb_base_dir,
                gdb_name
            )

        # Run Buffer tool
        output_feature_name: str = "output_Buffer_" + datetime.datetime.now().strftime(
            "%Y%m%d_%H%M%S%f") + "_" + str(uuid.uuid4().hex)
        output_feature_path: str = os.path.join(output_gdb_path, output_feature_name)

        print(datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"), f"running buffer tool ${str_id} ${pid}...")
        analysis.Buffer(
            in_features=input_feature_name,
            out_feature_class=output_feature_path,
            buffer_distance_or_field="2 Kilometers",
            line_side="FULL",
            line_end_type="ROUND",
            dissolve_option="NONE",
            dissolve_field=None,
            method="PLANAR"
        )

        # Run Features to JSON tool
        output_json_path: str = TEMPORARY_DIR
        output_json_name: str = "output_json_" + datetime.datetime.now().strftime("%Y%m%d_%H%M%S%f") + "_" + str(
            uuid.uuid4().hex) + ".geojson"
        output_json: str = os.path.join(output_json_path, output_json_name)

        print(datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"), f"conversion buffer output feature to geojson ${str_id} ${pid}...")
        conversion.FeaturesToJSON(
            in_features=output_feature_path,
            out_json_file=output_json,
            format_json="FORMATTED",
            include_z_values="NO_Z_VALUES",
            include_m_values="NO_M_VALUES",
            geoJSON="GEOJSON",
            outputToWGS84="WGS84",
            use_field_alias="USE_FIELD_NAME"
        )

        # Run Delete tool
        print(datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
              f"delete buffer output feature ${str_id} ${pid}...")
        delete_result = management.Delete(
            in_data=output_feature_path,
            data_type="FeatureClass"
        )
        print(datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
              f"delete status = {delete_result} ${str_id} ${pid}...")

        # Read the json file and load into memory
        with open(output_json, "r", encoding="utf-8") as file:
            json_data = json.load(file)

        # Delete the json file immediately
        os.remove(output_json)

        end_datetime = datetime.datetime.now()
        duration = end_datetime - start_datetime
        print(datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
              f"buffer tool done with duration {duration.total_seconds()} seconds ${str_id} ${pid}...")

        # Return json data
        return json_data
    except ExecuteError:
        message_count = GetMessageCount()
        print(f"Get message count is {message_count} ${str_id} ${pid}...")
        print(GetMessage(0))
        print(GetMessage(1))
        print(GetMessage(2))
        print(GetMessage(3))
        return {"message": GetMessage(2)}

@mcp.tool()
async def select_layer_by_attribute(input_layer: str, where_field: str, where_value: str)-> dict:
    """Query a feature inside the arcgis layer based on an attribute query.

    Args:
        input_layer: The arcgis feature layer name (not URL) to which the selection will be applied based on where_field and where_value.
        where_field: The field name inside the arcgis feature layer as a condition used to select a subset of records.
        where_value: The field value inside the field of the arcgis feature layer as a condition used to select a subset of records.
    """
    str_id = uuid.uuid4()
    pid = os.getpid()
    try:
        start_datetime = datetime.datetime.now()

        # Check if feature exists
        print(datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"), f"check if feature exists ${str_id} ${pid}...")
        if not Exists(input_layer):
            return {"message": "Feature not found"}

        # Run Select Layer By Attribute tool
        selected_rows = management.SelectLayerByAttribute(
            in_layer_or_view=input_layer,
            selection_type="NEW_SELECTION",
            where_clause=f"UPPER({where_field}) LIKE UPPER('%{where_value}%')",
            invert_where_clause=None
        )

        # Run Features to JSON tool
        output_json_path: str = TEMPORARY_DIR
        output_json_name: str = "output_json_" + datetime.datetime.now().strftime("%Y%m%d_%H%M%S%f") + "_" + str(
            uuid.uuid4().hex) + ".json"
        output_json: str = os.path.join(output_json_path, output_json_name)

        print(datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
              f"conversion select layer by location output feature to json ${str_id} ${pid}...")
        conversion.FeaturesToJSON(
            in_features=selected_rows,
            out_json_file=output_json,
            format_json="FORMATTED",
            include_z_values="NO_Z_VALUES",
            include_m_values="NO_M_VALUES",
            geoJSON="NO_GEOJSON",
            outputToWGS84="KEEP_INPUT_SR",
            use_field_alias="USE_FIELD_NAME"
        )

        # Read the json file and load into memory
        with open(output_json, "r", encoding="utf-8") as file:
            json_data = json.load(file)

        # Delete the json file immediately
        os.remove(output_json)

        end_datetime = datetime.datetime.now()
        duration = end_datetime - start_datetime
        print(datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
              f"select layer by attribute tool done with duration {duration.total_seconds()} seconds ${str_id} ${pid}...")

        return {"features": json_data["features"][0]}
    except ExecuteError:
        message_count = GetMessageCount()
        print(f"Get message count is {message_count} ${str_id} ${pid}...")
        print(GetMessage(0))
        print(GetMessage(1))
        print(GetMessage(2))
        print(GetMessage(3))
        return {"message": GetMessage(2)}

@mcp.tool()
async def select_layer_by_location(in_layer: str, select_features: str, where_field: str, where_value: str)-> dict:
    """Query a feature from an ArcGIS layer that is within a distance of a feature in another ArcGIS layer, based on their geometry locations.
    Returns only the selected feature's attributes.

    Args:
        in_layer: The arcgis features that will be evaluated using the select_features parameter values. The selection will be applied to these features.
        select_features: The arcgis feature layer name (not URL) to which the selection will be applied based on where_field and where_value. The features in the in_layer parameter will be selected based on relationship to the features from this layer.
        where_field: The field name inside the arcgis feature layer as a condition used to select a subset of records.
        where_value: The field value inside the field of the arcgis feature layer as a condition used to select a subset of records.
    """
    str_id = uuid.uuid4()
    pid = os.getpid()
    try:
        start_datetime = datetime.datetime.now()

        # Check if features exists
        print(datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"), f"check if features exists ${str_id} ${pid}...")
        if not Exists(in_layer) and not Exists(select_features):
            return {"message": "Feature not found"}

        # Run Select Layer By Attribute tool
        print(datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
              f"running select layer by attribute tool ${str_id} ${pid}...")
        selected_rows = management.SelectLayerByAttribute(
            in_layer_or_view=select_features,
            selection_type="NEW_SELECTION",
            where_clause=f"UPPER({where_field}) LIKE UPPER('%{where_value}%')",
            invert_where_clause=None
        )

        # Run Select Layer By Location tool
        print(datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
              f"running select layer by location tool with overlay type is within ${str_id} ${pid}...")
        within_output = management.SelectLayerByLocation(
            in_layer=in_layer,
            overlap_type="WITHIN_A_DISTANCE",
            select_features=selected_rows,
            search_distance=None,
            selection_type="NEW_SELECTION",
            invert_spatial_relationship="NOT_INVERT"
        )

        # Run Features to JSON tool
        output_json_path: str = TEMPORARY_DIR
        output_json_name: str = "output_json_" + datetime.datetime.now().strftime("%Y%m%d_%H%M%S%f") + "_" + str(
            uuid.uuid4().hex) + ".json"
        output_json: str = os.path.join(output_json_path, output_json_name)

        print(datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
              f"conversion select layer by location output feature to json ${str_id} ${pid}...")
        conversion.FeaturesToJSON(
            in_features=within_output,
            out_json_file=output_json,
            format_json="FORMATTED",
            include_z_values="NO_Z_VALUES",
            include_m_values="NO_M_VALUES",
            geoJSON="NO_GEOJSON",
            outputToWGS84="WGS84",
            use_field_alias="USE_FIELD_NAME"
        )

        # Read the json file and load into memory
        with open(output_json, "r", encoding="utf-8") as file:
            json_data = json.load(file)

        # Delete the json file immediately
        os.remove(output_json)

        end_datetime = datetime.datetime.now()
        duration = end_datetime - start_datetime
        print(datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
              f"select layer by location tool done with duration {duration.total_seconds()} seconds ${str_id} ${pid}...")

        return {"features": { "attributes" : json_data["features"][0]["attributes"] } }
    except ExecuteError:
        message_count = GetMessageCount()
        print(f"Get message count is {message_count} ${str_id} ${pid}...")
        print(GetMessage(0))
        print(GetMessage(1))
        print(GetMessage(2))
        print(GetMessage(3))
        return {"message": GetMessage(2)}

def main():
    # Initialize and run the server
    mcp.run(transport="streamable-http")

if __name__ == "__main__":
    main()