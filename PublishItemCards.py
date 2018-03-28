import time
from arcgis.gis import GIS

import os, re, json, traceback, sys, copy, urllib
import urllib.request as urlopen
import urllib.request as request
import requests
from datetime import datetime

online_username = ""
online_password = ""
online_connection = "http://<your org>.maps.arcgis.com"
gis_online_connection = GIS(online_connection, online_username, online_password)

# location for the Koop Connection
service_url = "https://sdgseries.herokuapp.com/sdgs/series/"
# location for the metadata API
metadata_url = "https://sdg-metadata.herokuapp.com"

# Load the Layer info JSON into an object
#layer_info = json.load(open("layerinfo.json"))

def set_field_alias(field_name):
    if field_name == "geoAreaName_x":
        return "Geographic Area Name"
    elif field_name == "seriesDescription":
        return "Series Description"
    elif field_name == "ISO3CD":
        return "ISO3 Code"
    elif field_name == "freq":
        return "Frequency"
    elif field_name == "last_5_years_mean":
        return "Mean of the Last 5 Years"
    else:
        return field_name.capitalize()

def analyze_csv(item_id):
    try:
        sharing_url = gis_online_connection.content._gis._url + "/sharing/rest/content/features/analyze"
        analyze_params = {'f': 'json', 'token': gis_online_connection._con._token,
                          'sourceLocale': 'en-us',
                          'filetype': 'csv', 'itemid': item_id}
        r = requests.post(sharing_url, data=analyze_params)
        json_data = json.loads(r.content.decode("UTF-8"))
        for field in json_data["publishParameters"]["layerInfo"]["fields"]:
            field["alias"] = set_field_alias(field["name"])

            # Indicator is coming in as a date Field make the correct
            if field["name"] == "indicator":
                field["type"] = "esriFieldTypeString"
                field["sqlType"] = "sqlTypeNVarchar"
        json_data["publishParameters"]["layerInfo"]["displayField"] = "geoAreaName_x"
        return json_data["publishParameters"]
    except:
        print("Unexpected error:", sys.exc_info()[0])
        raise


def publish_csv(series_code, item_properties, thumbnail,property_update_only=False):
    # Do we need to publish the hosted feature service for this layer
    try:
        data_dir = r"/Users/trav5516/Box Sync/Projects/UNSD - HUB Pilot/Technical/Data/Dataset-nofolders"
        file = os.path.join(data_dir, series_code + ".csv")
        if os.path.isfile(file):
            csv_item_properties = copy.deepcopy(item_properties)
            csv_item_properties["title"] = series_code + "_MST"
            csv_item_properties["type"] = "CSV"
            csv_item_properties["url"] = ""

            # Does this CSV already exist
            query_string = "title:'{}' AND owner:{}".format(csv_item_properties["title"], online_username)
            search_results = gis_online_connection.content.search(query_string)

            csv_item = None
            print('Publishing CSV File....')
            if search_results:
                for search_result in search_results:
                    if search_result["title"] == csv_item_properties["title"]:
                        if property_update_only:
                            search_result.update(item_properties=csv_item_properties, thumbnail=thumbnail)
                        else:
                            search_result.update(item_properties=csv_item_properties, thumbnail=thumbnail,
                                                 data=file)
                        csv_item = search_result
                        break

            if csv_item is None:
                csv_item = gis_online_connection.content.add(item_properties=csv_item_properties, thumbnail=thumbnail,
                                                             data=file)



            # find the published service
            query_string = "title:'{}' AND owner:{}".format(item_properties["title"], online_username)
            search_results = gis_online_connection.content.search(query_string)

            if search_results:
                for search_result in search_results:
                    if search_result["title"] == item_properties["title"]:
                        search_result.update(item_properties=item_properties, thumbnail=thumbnail)
                        search_result.move("Open Data")
                        return search_result

            # publish the layer if it was not found
            print('Analyze Feature Service....')
            publish_parameters = analyze_csv(csv_item["id"])
            publish_parameters["name"] = csv_item_properties["title"]
            print('Publishing Feature Service....')
            csv_lyr = csv_item.publish(publish_parameters=publish_parameters,overwrite=True)
            csv_lyr.update(item_properties=item_properties, thumbnail=thumbnail)
            if csv_item["ownerFolder"] is None:
                print('Moving CSV to Open Data Folder')
                csv_item.move("Open Data")

            if csv_lyr["ownerFolder"] is None:
                print('Moving Feature Service to Open Data Folder')
                csv_lyr.move("Open Data")
            return csv_lyr
        else:
            return None
    except:
        print("Unexpected error:", sys.exc_info()[0])
        raise


def getMetadata(value):
    try:
        url = metadata_url + "/goals?ids=" + value
        print(url)
        req = request.Request(url)
        response = urlopen.urlopen(req)
        response_bytes = response.read()
        json_data = json.loads(response_bytes.decode("UTF-8"))
        if int(value) < 10:
            key = "0" + str(value)
        else:
            key = str(value)

        if "icon_url_sq" not in json_data["data"][0]:
            json_data["data"][0]["icon_url_sq"] = "https://raw.githubusercontent.com/UNStats-SDGs/sdg-metadata-api/master/icons/SDG" + key + ".png"
        return json_data["data"][0]
    except:
        return "https://raw.githubusercontent.com/UNStats-SDGs/sdgs-data/master/images/en/TGG_Icon_Color_" + value + ".png"


def get_series_tags(series_code):
    try:
        url = metadata_url + "/series?code=" + series_code
        print(url)
        req = request.Request(url)
        response = urlopen.urlopen(req)
        response_bytes = response.read()
        json_data = json.loads(response_bytes.decode("UTF-8"))
        if "tags" not in json_data["data"][0]:
            return []
        return json_data["data"][0]["tags"]
    except:
        return []


def addItemtoOnline(item_properties, thumbnail):
    # Check if there is a group here
    query_string = "title:'{}' AND owner:{}".format(item_properties["title"], online_username)
    search_results = gis_online_connection.content.search(query_string)
    if not search_results:
        return gis_online_connection.content.add(item_properties=item_properties, thumbnail=thumbnail)
    else:
        for search_result in search_results:
            if search_result["title"] == item_properties["title"]:
                search_result.update(item_properties=item_properties, thumbnail=thumbnail)
                return search_result
    return None


def createGroup(group_info):
    try:
        # Add the Service Definition to the Enterprise site
        item_properties = dict({
            "title": group_info["title"],
            "snippet": group_info["snippet"],
            "description": group_info["description"],
            "tags": ", ".join([group_info["title"], "Open Data", "Hub"]),
            "thumbnail": group_info["thumbnail"],
            "isOpenData": True,
            "access": "public",
            "isInvitationOnly": True,
            "protected": True
        })

        # Check if there is a group here
        query_string = "title:'{}' AND owner:{}".format(group_info["title"], online_username)
        search_results = gis_online_connection.groups.search(query_string)
        if not search_results:
            return gis_online_connection.groups.create_from_dict(item_properties)
        else:
            for search_result in search_results:
                if search_result["title"] == group_info["title"]:
                    group_found = True
                    search_result.update(title=group_info["title"], tags=group_info["tags"],
                                         description=group_info["description"],
                                         snippet=group_info["snippet"], access="Public",
                                         thumbnail=group_info["thumbnail"])
                    return search_result
            # The correct group was not found in the search results add it now
            return gis_online_connection.groups.create_from_dict(item_properties)
    except:
        traceback.print_exc()


def processSDGInfomation(goal_code=None,indicator_code=None, series_code=None,property_update_only=False):
    try:
        #  Get the JSON Values from the SDG API
        url = "https://unstats.un.org/SDGAPI/v1/sdg/Goal/List?includechildren=true"
        req = request.Request(url)
        response = urlopen.urlopen(req)
        response_bytes = response.read()
        json_data = json.loads(response_bytes.decode("UTF-8"))

        for goal in json_data:
            # Determine if we are processing this query Only process a specific series code
            if goal_code is not None and int(goal["code"]) not in goal_code:
                continue

            # Get the Thumbnail from the SDG API
            goal_metadata = getMetadata(goal["code"])
            print(goal_metadata)
            if "icon_url_sq" in goal_metadata:
                thumbnail = goal_metadata["icon_url_sq"]
            else:
                thumbnail = "http://undesa.maps.arcgis.com/sharing/rest/content/items/aaa0678dba0a466e8efef6b9f11775fe/data"

            # Create a Group for the Goal
            group_goal_properties = dict()
            group_goal_properties["title"] = "SDG " + goal["code"]
            group_goal_properties["snippet"] = goal["title"]
            group_goal_properties["description"] = goal["description"]
            group_goal_properties["tags"] = [group_goal_properties["title"]]
            #if "keywords" in goal_metadata:
            #    if "tags" in goal_metadata["keywords"]:
            #        group_goal_properties["tags"] += goal_metadata["keywords"]["tags"]
            #    if "descriptions" in goal_metadata["keywords"]:
            #        group_goal_properties["tags"] += goal_metadata["keywords"]["descriptions"]
            #    if "groups" in goal_metadata["keywords"]:
            #        group_goal_properties["tags"] += goal_metadata["keywords"]["groups"]
            group_goal_properties["thumbnail"] = thumbnail
            group_id = createGroup(group_goal_properties)

            for target in goal["targets"]:
                group_target_properties = dict()
                group_target_properties["tags"] = ["Target " + target["code"]]
                group_id.update(tags=group_id["tags"] + group_target_properties["tags"])

                # Iterate through each of the targets
                # Allow processing a single indicator
                for indicator in target["indicators"]:
                    if indicator_code and not indicator["code"] == indicator_code:
                        continue

                    process_indicator = dict()
                    process_indicator["name"] = "Indicator " + indicator["code"]  # eg. Indicator 1.1.1
                    process_indicator["tags"] = [process_indicator["name"]]
                    # Append the keyword tags from the metadata as well
                    group_id.update(tags=group_id["tags"] + process_indicator["tags"])

                    process_indicator["snippet"] = indicator["code"] + ": " + indicator["description"]
                    process_indicator["description"] = "<p><b>Indicator " + indicator["code"] + ": </b>" + indicator["description"] + "</p>" + \
                                                       "</p><p><b>Target " + target["code"] + ": </b>" + target["description"] + "</p>" + \
                                                       "<p>" + goal["description"] + "</p>"

                    process_indicator["credits"] = "UNSD"
                    process_indicator["thumbnail"] = thumbnail

                    for series in indicator["series"]:
                        # Determine if we are processing this query Only process a specific series code
                        if indicator_code and not (series["code"] == series_code or series_code is None):
                            continue

                        # indicator_code = None
                        item_properties = dict()
                        item_properties["title"] = process_indicator["name"] + " (" + series["code"] + "): " + series["description"]
                        if not series["description"]:
                            series["description"] = series["code"]
                        snippet = series["code"] + ": " + series["description"]
                        item_properties["snippet"] = (snippet[:250] + "..") if len(snippet) > 250 else snippet
                        item_properties["description"] = "<p><b>Series " + series["code"] + ": </b>" + \
                                                         series["description"] + "</p>" + \
                                                         process_indicator["description"]
                        final_tags = group_goal_properties["tags"] + \
                                        group_target_properties["tags"] + \
                                        process_indicator["tags"]
                        final_tags.extend(get_series_tags(series["code"]))
                        #final_tags = set(final_tags)
                        #final_tags = list(final_tags)
                        item_properties["tags"] = final_tags

                        # Add this item to ArcGIS Online
                        print("Processing series code:", indicator["code"], series["code"])
                        try:
                            online_item = publish_csv(series["code"], item_properties=item_properties,
                                                      thumbnail=thumbnail,property_update_only=property_update_only)

                            if online_item is not None:
                                # Share this content with the goals group
                                online_item.share(everyone=True, org=True, groups=group_id["id"],
                                                  allow_members_to_edit=False)
                                # Update the Group Information with Data from the Indicator and targets
                                group_id.update(tags=group_id["tags"] + [series["code"]])
                        except:
                            print("Failed to process series code:", indicator["code"], series["code"], item_properties)

        return
    except:
        traceback.print_exc()


if __name__ == "__main__":se
    start_time = str(datetime.now())
    processSDGInfomation()
    end_time = str(datetime.now())
    print(start_time, end_time)
    print("Completed")
