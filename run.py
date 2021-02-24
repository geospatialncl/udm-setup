"""
Setup input data for UDM

- Pull data from NISMOD-DB API
- Rasterise data for input into UDM

Issues
- NISMOD-DB API username and password method
- Write all data to a single directory or other output method?
"""

import requests, json, os, sys, glob
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

    if conf['api_url'] is None:
        # need to load in file
        print('ERROR! Could not find the required environmental variables')
        exit(1)

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
        exit(1)

    return fishnet_geojson


def rasterise(data, fishnet=None, area_scale='lad', area_codes=['E08000021'], output_filename='output_raster.tif', fishnet_uid='FID'):
    """
    Rasterise a set of data
    """
    if '.' not in output_filename:
        output_filename = output_filename+'.tif'
    print(output_filename)
    if fishnet is None:
        Rasteriser(
            data,  # Extracted GeoJSON data
            area_codes=area_codes,  # Boundary specified either by area codes OR
            scale=area_scale,  # Scale to look at (oa|lad|gor)
            output_filename=output_filename,  # Output filename
            output_format='GeoTIFF',  # Raster output file format (GeoTIFF|ASCII)
            resolution=100.0,  # Fishnet sampling resolution in metres
            area_threshold=50.0,  # Minimum data area within a cell to trigger raster inclusion
            invert=True,  # True if output raster gets a '0' for areas > threshold
            nodata=1,
            fishnet_uid=fishnet_uid
        ).create()
    else:
        print('rasterising using existing fishnet')
        Rasteriser(
            data,  # Extracted GeoJSON data
            fishnet=fishnet,    # Fishnet grid GeoJSON
            output_filename=output_filename,  # Output filename
            output_format='GeoTIFF',  # Raster output file format (GeoTIFF|ASCII)
            resolution=100.0,  # Fishnet sampling resolution in metres
            area_threshold=50.0,  # Minimum data area within a cell to trigger raster inclusion
            invert=True,  # True if output raster gets a '0' for areas > threshold
            nodata=1,
            fishnet_uid=fishnet_uid
        ).create()

    return


def check_fishnet_valid(gdf, uid):
    """
    This checks if there is a 'FID' field in the fishnet. The rasteriser code requires this.

    Returns updated fishnet if a lowercase 'fid' is found.

    Future update should allow user to pass a fid equivalent field name.

    """
    if 'FID' not in gdf.columns:
        # check if fid attribute is lower case
        if 'fid' in gdf.columns:
            gdf = gdf.rename(columns={'fid': 'FID'})
        else:
            print('ERROR! A FID attribute is required within the fishnet dataset.')
            exit(1)
    return gdf


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


def move_output(file_name, output_dir):
    """
    Move the file from the rasterise output dir to the model output dir
    """

    # copy output from rasteriser output dir to outputs dir
    if os.path.exists('/udm-rasteriser/data/%s.tif' % file_name):
        copyfile('/udm-rasteriser/data/%s.tif' % file_name, os.path.join(output_dir, '%s.tif' % 'output_raster'))
    else:
        print('ERROR! Output raster has not been generated or found at the expected location.')
    return


def run_processing(output_dir='/data/outputs', files=[], layers={}, area_codes=['E00042673',], area_scale='oa', fishnet=None, fishnet_uid='FID'):
    """
    Inputs:
    - LAD: a local authority district code
    - Layer(s): List of layers to generate raster(s) for
    - raster settings: Dict of settings for generating raster

    - fishnet: file path to fishnet
    - files: a list of files to load in and rasterise
    """

    # if no fishnet passed
    # by generating fishnet now it ensures all raster layers generated use the same fishnet
    if fishnet is None:

        # temp method until below is sorted
        fishnet_filepath = generate_fishnet(data_dir=output_dir, lads=area_codes)

        #if area_scale == 'oa':
        #    print('This method is not supported yet')
        #    # need to fetch the lads the OA's fall in
        #    exit(1)
        #else:
        #    fishnet_filepath = generate_fishnet(lads=area_codes)
    else:
        # set the fishnet file path
        fishnet_filepath = fishnet

    # read in fishnet now so can be used in rasterise process do now so only done once if multiple layers
    # read fishnet in with geopandas (seems more stable than with json or geojson libraries)
    fnet = geopandas.read_file(fishnet_filepath, encoding='utf-8')

    # check the fishnet is valid
    fnet = check_fishnet_valid(fnet, fishnet_uid)

    # if a list of files is passed, allow these to be rasterised using a fishnet, either passed or generated
    if len(files) != 0:

        for file in files:
            print('Rasterising file %s' % file)
            data_gdf = geopandas.read_file(file, encoding='utf-8')
            # name the output after the input file - get the name of the input file
            output_filename = file.split('/')[-1]
            output_filename = output_filename.split('.')[0]

            # run rasterise process
            rasterise(data=data_gdf.to_json(), fishnet=fnet.to_json(), output_filename=output_filename)

            move_output(output_filename, output_dir)

    # load in env variables if needed
    if len(layers.keys()) != 0:
        # get environmental variables
        conf = get_environment_variables()

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

        move_output(layer_name, output_dir)

    return


def run():
    """
    Entry point.
    Parse passed arguments.

    Should include:
    - fishnet (optional)
        - a single file path
        - e.g. /inputs/fishnet.geojson
    - rasterise_files (optional - required for now)
        - a list of files, each with a complete filepath
        - e.g. '/inputs/file1.geojson,/inputs/file2.geojson'
    - lads (optional)
        - a list of lads to generate the fishnet from
        - e.g. 'E08000021,E08000020'
    """
    data_path = os.getenv('DATA_PATH', '/data')

    input_dir = os.path.join(data_path, 'inputs')
    output_dir = os.path.join(data_path, 'outputs')

    # declare as None, future updates will use these to check for valid set of inputs
    fishnet_file = None
    files_to_rasterise = None
    lads = None
    bbox = None

    # check set dirs exist
    if not os.path.exists(input_dir):
        print(os.listdir('/'))
        print(os.listdir('/data'))
        print('ERROR! Input directory could not be found! Details. Searched for %s' % input_dir)
        exit(1)
    if not os.path.exists(output_dir):
        os.mkdir(output_dir)

    # get the fishnet file
    fishnet_file = glob.glob(os.path.join(input_dir, 'fishnet', '*.gpkg')) + glob.glob(os.path.join(input_dir, 'fishnet', '*.geojson'))
    if len(fishnet_file) == 0:
        print('ERROR! No fishnet file found in dir (%s).' % os.path.join(input_dir, 'fishnet'))
        exit(1)
    elif len(fishnet_file) > 1:
        print('ERROR! More than one fishnet file found (%s). Only one is required.' % fishnet_file)
        exit(1)
    else:
        fishnet_file = fishnet_file[0]

    # get the list of files to rasterise
    vector_file_list = glob.glob(os.path.join(input_dir, 'vectorfiles', '*.*'))
    print(fishnet_file)
    print(vector_file_list)
    run_processing(files=vector_file_list, fishnet=fishnet_file, area_codes=lads, output_dir=output_dir)
    return


if __name__ == '__main__':
    run()

#generate_fishnet(lads=['E08000021'])
#generate_fishnet()
#run_processing(layers={'water-bodies':{}}, area_codes='E08000021', area_scale='lad')
#run_processing(layers={'current-dev':{}})
