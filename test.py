import copy
# used to prompt for user input
# when using this script internally, you may remove this and simply hard code in your username and password
import getpass
import json
import os
import re
import sys
import time
import traceback
import urllib
import urllib.request as request
import urllib.request as urlopen
from datetime import datetime
import requests
# this helps us do some debugging within the Python Notebook
# another optional component
from IPython.display import display
from arcgis.gis import GIS
from arcgis.features import FeatureLayer

try:
    online_username = 'tbutcher_undesa' #input('Username: ')
    online_password = 'july1974' #getpass.getpass('Password: ')
    online_connection = "https://www.arcgis.com"
    gis_online_connection = GIS(online_connection, online_username, online_password)
    gis_online_connection

    test_item = gis_online_connection.content.get('c1242c4e44734047b7291486a27e282e')
    test_item

    #get the min/max for this items
    stat_features = test_item.layers[0].query(where='1=1', out_fields=["latest_min_value","latest_max_value"],
        out_statistics=[{"statisticType": "max","onStatisticField": "latest_value", "outStatisticFieldName": "latest_max_value"},
                        {"statisticType": "min","onStatisticField": "latest_value", "outStatisticFieldName": "latest_min_value"}])
    stat_features

    #get the first feature for the stats
    max_value = stat_features.features[0].attributes["latest_max_value"]
    min_value = stat_features.features[0].attributes["latest_min_value"]
    print("Max Value is: " + max_value +" and Min Value is: " + min_value)

    test_feature_layer = test_item.layers[0]
    test_feature_layer.properties
    renderer_definition = {"type":"classBreaksDef","classificationField":"latest_value","classificationMethod":"esriClassifyNaturalBreaks","breakCount":5}
    test_feature_layer.generate_renderer(renderer_definition, where=None)
except:
    print("Unexpected error:", sys.exc_info()[0])