"""
Setup input data for UDM

- Pull data from NISMOD-DB API
- Rasterise data for input into UDM

Issues
- NISMOD-DB API username and password method
- Write all data to a single directory or other output method?
"""

import requests, json
import os

api_url = os.getenv('API_URL')
username = os.getenv('USERNAME')
password = os.getenv('PASSWORD')


def run():
    """
    Inputs:
    - LAD: a local authority district code
    - Layer(s): List of layers to generate raster(s) for
    - raster settings: Dict of settings for generating raster

    """
    area = 'E08000021'

    request_string = '%s/data/mastermap/areas?export_format=geojson&scale=lad&area_codes=%s&classification_codes=all' %(api_url, area)

    response = requests.get(request_string, auth=(username, password))

    if response.status_code != 200:
        print('ERROR! A response code (%s) indicating no data was returned has been received from the API.' % response.status_code)
        exit(2)

    if response.status_code == 200:
        data = json.loads(response.text)

        # open file to save data to
        with open(os.path.join('data', 'mastermap_%s.geojson' %area), 'w') as data_file:
            json.dump(data, data_file)  # write the data from API to the file
            print('Written data for ' + area + ' to GeoJSON file.')
    return
