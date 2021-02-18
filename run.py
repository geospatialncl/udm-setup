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


def get_environment_variables():
    """
    Pull the environment variables into a dict and return
    """
    conf = {}
    conf['api_url'] = os.getenv('API_URL')
    conf['username'] = os.getenv('USERNAME')
    conf['password'] = os.getenv('PASSWORD')
    return conf


def generate_fishnet(data_dir='/outputs', output_file='fishnet_100m.tif', bbox=[419000, 173500, 572500, 318500], lads=None):
    """
    Generate a fishnet (grid) over within the given bounding box and export as a raster (.tif).

    bbox    : bounding box for fishnet. Default is for Cambridge Oxford Arc.
    """

    if lads is not None:
        # if a lad, or of lads is passed generate a fishnet for the area covered by these
        fishnet_geojson = FishNet(outfile='fishnet', outformat='GeoJSON', lad=lads).create()
    else:
        # if no lads passed, generate fishnet based on a bounding box
        fishnet_geojson = FishNet(outfile='fishnet', outformat='GeoJSON', bbox=bbox).create()

    # copy fishnet file to docker shared directory
    if os.path.isfile('/udm-rasteriser/data/fishnet'):
        copyfile('/udm-rasteriser/data/fishnet', '/outputs/fishnet')
    else:
        print('Error! Fishnet file was not created.')
        exit(2)

    return fishnet_geojson


def rasterise(geojson_data, fishnet=None, area_scale='lad', area_codes=['E08000021']):
    """
    Rasterise a set of data
    """

    if fishnet is None:
        Rasteriser(
            geojson_data,  # Extracted GeoJSON data
            area_codes=['E08000021'],  # Boundary specified either by area codes OR
            scale=area_scale,  # Scale to look at (oa|lad|gor)
            output_filename='output_raster.tif',  # Output filename
            output_format='GeoTIFF',  # Raster output file format (GeoTIFF|ASCII)
            resolution=100.0,  # Fishnet sampling resolution in metres
            area_threshold=50.0,  # Minimum data area within a cell to trigger raster inclusion
            invert=True,  # True if output raster gets a '0' for areas > threshold
            nodata=1
        ).create()
    else:
        Rasteriser(
            geojson_data,  # Extracted GeoJSON data
            fishnet=fishnet,    # Fishnet grid GeoJSON
            output_filename='output_raster.tif',  # Output filename
            output_format='GeoTIFF',  # Raster output file format (GeoTIFF|ASCII)
            resolution=100.0,  # Fishnet sampling resolution in metres
            area_threshold=50.0,  # Minimum data area within a cell to trigger raster inclusion
            invert=True,  # True if output raster gets a '0' for areas > threshold
            nodata=1
        ).create()

    return


def process_response(response, layer_name, data_dir):
    """"""

    if response.status_code != 200:
        print('ERROR! A response code (%s) indicating no data was returned has been received from the API.' % response.status_code)
        exit(2)

    # if api call a success
    if response.status_code == 200:
        data = json.loads(response.text)

        # open file to save data to
        with open(os.path.join(data_dir, '%s.geojson' % layer_name), 'w') as data_file:
            json.dump(data, data_file)  # write the data from API to the file
            print('Written data for to GeoJSON file.')

    return data


def run(data_dir='/outputs', layers={'buildings': {'year': 2011}, }, area_codes=['E00042673',], area_scale='oa', fishnet=None):
    """
    Inputs:
    - LAD: a local authority district code
    - Layer(s): List of layers to generate raster(s) for
    - raster settings: Dict of settings for generating raster

    """
    # get environmental variables
    conf = get_environment_variables()

    # loop through the passed layers, download data and rasterise
    for layer_name in layers.keys():
        if layer_name == 'topographic':
            name = layer_name
            layers[layer_name]
            request_string = '%s/data/mastermap/areas?export_format=geojson&scale=%s&area_codes=%s&classification_codes=all' % (conf['api_url'], area_scale, area_codes)

            response = requests.get(request_string, auth=(conf['username'], conf['password']))

        elif layer_name == 'buildings':
            name = layer_name
            layer = layers[layer_name]
            request_string = '%s/data/mastermap/buildings?export_format=geojson&scale=%s&area_codes=%s&building_year=%s' % (conf['api_url'], area_scale, area_codes[0], layer['year'])

            response = requests.get(request_string, auth=(conf['username'], conf['password']))

        # process response
        data = process_response(response=response, layer_name=layer_name, data_dir=data_dir)

        # run rasterise process
        rasterise(data, area_codes='E08000021', area_scale='lad')

        # copy output from rasteriser output dir to outputs dir
        copyfile('/udm-rasteriser/data/output_raster.tif', '/outputs/output_raster.tif')

    return


generate_fishnet(lads=['E08000021'])
#run()
