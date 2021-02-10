"""
Setup input data for UDM

- Pull data from NISMOD-DB API
- Rasterise data for input into UDM

Issues
- NISMOD-DB API username and password method
- Write all data to a single directory or other output method?
"""

import requests, json, os, sys
sys.path.insert(0, "/udm-rasteriser")
from classes import Config, FishNet, Rasteriser
from geopandas import GeoDataFrame
from shutil import copyfile

api_url = os.getenv('API_URL')
username = os.getenv('USERNAME')
password = os.getenv('PASSWORD')


def generate_fishnet(data_dir='/outputs', output_file='fishnet_100m.tif'):
    """
    Generate a fishnet (grid) over within the given bounding box and export as a raster (.tif).
    """
    fishnet_geojson = FishNet(outfile='fishnet', outformat='GeoJSON', bbox=[419000, 173500, 572500, 318500]).create()

    return


def rasterise(geojson_data, area_scale='lad', area_codes=['E08000021']):
    """
    Rasterise a set of data
    """

    return Rasteriser(
        geojson_data,  # Extracted GeoJSON data
        area_codes=area_codes,  # Boundary specified either by area codes OR
        scale=area_scale,  # Scale to look at (oa|lad|gor)
        output_filename='output_raster.tif',  # Output filename
        output_format='GeoTIFF',  # Raster output file format (GeoTIFF|ASCII)
        resolution=100.0,  # Fishnet sampling resolution in metres
        area_threshold=50.0,  # Minimum data area within a cell to trigger raster inclusion
        invert=True,  # True if output raster gets a '0' for areas > threshold
        nodata=1
    ).create()


def run(data_dir='/outputs'):
    """
    Inputs:
    - LAD: a local authority district code
    - Layer(s): List of layers to generate raster(s) for
    - raster settings: Dict of settings for generating raster

    """
    area = 'E00042673' #'E08000021'

    request_string = '%s/data/mastermap/areas?export_format=geojson&scale=oa&area_codes=%s&classification_codes=all' %(api_url, area)

    response = requests.get(request_string, auth=(username, password))

    if response.status_code != 200:
        print('ERROR! A response code (%s) indicating no data was returned has been received from the API.' % response.status_code)
        exit(2)

    if response.status_code == 200:
        data = json.loads(response.text)

        # open file to save data to
        with open(os.path.join(data_dir, 'mastermap_%s.geojson' %area), 'w') as data_file:
            json.dump(data, data_file)  # write the data from API to the file
            print('Written data for ' + area + ' to GeoJSON file.')

    print(rasterise(data))
    return

run()

# copy output from rasteriser to output dir
copyfile('/udm-rasteriser/data/output_raster.tif', '/outputs/output_raster.tif')
