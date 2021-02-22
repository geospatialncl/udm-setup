"""
Setup input data for UDM

- Pull data from NISMOD-DB API
- Rasterise data for input into UDM

Issues
- NISMOD-DB API username and password method
- Write all data to a single directory or other output method?
"""

import requests, json, os, sys, geojson
sys.path.insert(0, "/udm-rasteriser")
from classes import Config, FishNet, Rasteriser
from geopandas import GeoDataFrame
import geopandas
from shutil import copyfile
from io import BytesIO


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
        copyfile('/udm-rasteriser/data/fishnet', '/outputs/fishnet.geojson')
    else:
        print('Error! Fishnet file was not created.')
        exit(2)

    return fishnet_geojson


def rasterise(geojson_data, fishnet=None, area_scale='lad', area_codes=['E08000021'], output_filename='output_raster.tif'):
    """
    Rasterise a set of data
    """
    if '.' not in output_filename:
        output_filename = output_filename+'.tif'

    if fishnet is None:
        Rasteriser(
            geojson_data,  # Extracted GeoJSON data
            area_codes=area_codes,  # Boundary specified either by area codes OR
            scale=area_scale,  # Scale to look at (oa|lad|gor)
            output_filename=output_filename,  # Output filename
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
            output_filename=output_filename,  # Output filename
            output_format='GeoTIFF',  # Raster output file format (GeoTIFF|ASCII)
            resolution=100.0,  # Fishnet sampling resolution in metres
            area_threshold=50.0,  # Minimum data area within a cell to trigger raster inclusion
            invert=True,  # True if output raster gets a '0' for areas > threshold
            nodata=1
        ).create()

    return


def process_response(response, layer_name, data_dir):
    """
    Returns GeoJSON for the data returned if any returned. Returns error/warning otherwise.

    """

    if response.status_code != 200:
        print('ERROR! A response code (%s) indicating no data was returned has been received from the API.' % response.status_code)
        exit(2)

    # if api call a success
    if response.status_code == 200:
        # read data from API response
        gdf = geopandas.read_file(BytesIO(response.content))

        # write the data from API to the file
        gdf.to_file(os.path.join(data_dir, '%s.geojson' % layer_name), driver='GeoJSON')

        print('Written data for to GeoJSON file.')

    return gdf.to_json()


def run(data_dir='/outputs', files=[], layers={}, area_codes=['E00042673',], area_scale='oa', fishnet=None):
    """
    Inputs:
    - LAD: a local authority district code
    - Layer(s): List of layers to generate raster(s) for
    - raster settings: Dict of settings for generating raster

    - fishnet: file path to fishnet
    - files: a list of files to load in and rasterise
    """
    # get environmental variables
    conf = get_environment_variables()

    # if no fishnet passed
    # by generating fishnet now it ensures all raster layers generated use the same fishnet
    fishnet_filepath = None
    if fishnet is None:
        # temp method until below is sorted
        fishnet_filepath = generate_fishnet(lads=['E08000021',])

        #if area_scale == 'oa':
        #    print('This method is not supported yet')
        #    # need to fetch the lads the OA's fall in
        #    exit(2)
        #else:
        #    fishnet_filepath = generate_fishnet(lads=area_codes)

    # read in fishnet now so can be used in rasterise process do now so only done once if multiple layers
    # read fishnet in with geopandas (seems more stable than with json or geojson libraries)
    fnet = geopandas.read_file(fishnet_filepath)

    # if a list of files is passed, allow these to be rasterised using a fishnet, either passed or generated
    if len(files) != 0:
        for file in files:
            gdf = geopandas.read_file(fishnet_filepath)

            # name the output after the input file - get the name of the input file
            output_filename = file.split('/')[-1]

            # run rasterise process
            rasterise(data=gdf.to_json(), fishnet=fnet.to_json(), output_filename=output_filename)

    # loop through the passed layers, download data and rasterise
    for layer_name in layers.keys():
        if layer_name == 'topographic' or layer_name == 'current-dev':
            layer = layers[layer_name]
            request_string = '%s/data/mastermap/areas?export_format=geojson&scale=%s&area_codes=%s&classification_codes=all' % (conf['api_url'], area_scale, ''.join(area_codes))

            response = requests.get(request_string, auth=(conf['username'], conf['password']))

        elif layer_name == 'buildings':

            layer = layers[layer_name]
            request_string = '%s/data/mastermap/buildings?export_format=geojson&scale=%s&area_codes=%s&building_year=%s' % (conf['api_url'], area_scale, area_codes[0], layer['year'])

            response = requests.get(request_string, auth=(conf['username'], conf['password']))

        elif layer_name == 'water-bodies':
            layer = layers[layer_name]
            request_string = '%s/data/mastermap/areas?export_format=geojson&geom_foramt=geojson&scale=%s&area_codes=%s&classification_codes=all&year=2017&theme=Water&flatten_lists=True' % (conf['api_url'], area_scale, ''.join(area_codes))

            response = requests.get(request_string, auth=(conf['username'], conf['password']))

        # process response
        data = process_response(response=response, layer_name=layer_name, data_dir=data_dir)

        # convert data to a geopandas dataframe
        gdf = geopandas.read_file(data)

        # if any post querying process required
        if layer_name == 'water-bodies':
            # filter data
            #print(gdf.columns)
            #print(gdf['theme'].head())

            # convert to json for rasterising
            data = gdf.to_json()

        elif layer_name == 'current-dev':
            # filter data
            # developed land
            gdf_result = gdf.loc[gdf['theme'] == 'Land']
            gdf_result = gdf_result.loc[gdf_result['make'] == 'Multiple']
            # buildings
            gdf_blds = gdf.loc[gdf['descriptive_group'] == 'Buildings']
            gdf_blds = gdf_blds.loc[gdf_blds['make'] == 'Manmade']
            # rail
            gdf_rail = gdf.loc[gdf['descriptive_group'] == 'Rail']
            gdf_rail = gdf_rail.loc[gdf_rail['make'] == 'Manmade']
            # roads
            gdf_roads = gdf.loc[gdf['descriptive_group'] == 'Roads']
            gdf_roads = gdf_roads.loc[gdf_roads['make'] == 'Manmade'] & gdf_roads.loc[gdf_roads['make'] == 'Unknown']
            # roadside
            gdf_roadside = gdf.loc[gdf['descriptive_group'] == 'Roadside']
            gdf_roadside = gdf_roadside.loc[gdf_roadside['make'] == 'Natural']

            #gdf_result.append(gdf_blds).append(gdf_rail).append(gdf_roads).append(gdf_roadside)

            # convert to json for rasterising
            data = gdf_result.to_json()

        # run rasterise process
        if fishnet_filepath is not None:
            rasterise(data, fishnet=fnet.to_json(), output_filename=layer_name)
        else:
            print('Warning: This method is going to be removed.')
            rasterise(data, area_codes='E08000021', area_scale='lad', output_filename=layer_name)

        # copy output from rasteriser output dir to outputs dir
        copyfile('/udm-rasteriser/data/%s.tif' % layer_name, '/outputs/%s.tif' % layer_name)

    return


#generate_fishnet(lads=['E08000021'])
#generate_fishnet()
run(layers={'water-bodies':{}}, area_codes='E08000021', area_scale='lad')
#run(layers={'current-dev':{}})
