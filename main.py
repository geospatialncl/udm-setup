import pandas as pd
from os import getenv, walk, mkdir, remove, listdir
from os.path import join, isdir, isfile
import logging
from pathlib import Path
from shutil import copyfile

data_path = '/data'
input_dir = 'input'
output_dir = 'outputs'
outputs_data_dir = 'data'


def check_dir_exists(path):
    """
    Check output directory exists and create if not
    """
    if isdir(path) is False:
        mkdir(path)
    else:
        files = [f for f in listdir(path) if isfile(join(path, f))]
        for file in files:
            remove(join(path, file))
    return


# check output dir exists
check_dir_exists(join(data_path, output_dir))

logger = logging.getLogger('transformer')
logger.setLevel(logging.INFO)
fh = logging.FileHandler(Path(join(data_path, output_dir)) / 'udm-setup.log')
formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
fh.setFormatter(formatter)
logger.addHandler(fh)

logger.info('Log file established!')

# check output dir exists
check_dir_exists(join(data_path, output_dir, outputs_data_dir))


def find_files():
    """
    Search all directories for any input files
    """

    suitable_extension_types = ['asc', 'tiff', 'geotiff', 'gpkg', 'csv']

    input_files = []

    for root, dirs, files in walk('/data'):
        print(root, files)
        for file in files:

            # check if extension acceptable
            extension = file.split('.')[-1]
            if extension in suitable_extension_types:
                # file is good and what we are looking for
                input_files.append(join(root, file))

    print(input_files)
    return input_files


def copy_file(source, dest):
    print('COPYING FILE: %s' % source)
    copyfile(source, dest)
    logger.info('Copied file into output directory: %s' %dest)
    return


def generate_attractors(files):
    """
    Generate the input csv file for the attractors required by UDM
    """
    # for each attractor as a row in the csv file
    ## name = attactors.csv
    ## format
    ### name (file_name.asc); reverse_polarity_flag (0 or 1, default is 1); weight (numeric, float, default=1)
    #files = ['major_roads_gb_clip.asc', 'developmentareas_gb_clip.asc']
    # print(files)

    #data = {'name': [], 'reverse_polarity_flag': [], 'weight': []}
    data = {'layer_name': [], 'reverse_polarity_flag': [], 'layer_weight': []}

    # input_str = 'roads:0.3:1;development:0.5:0;' # should be replaced with user inputs
    # input_str = input_str.split(';')

    attractors = getenv('attractors')
    if attractors == '' or attractors == 'None':  # if no extent passed
        attractors = None
    else:
        attractors = attractors.split(';')
    print(attractors)
    logger.info('Attractors input: %s' %attractors)

    # loop through the passed attractors
    for layer in attractors:
        if len(layer) == 0 or layer is None: break
        layer = layer.split(':')

        # print('Layer:',layer)
        layer_name = layer[0]
        layer_weight = layer[1]
        layer_polarity = layer[2]
        # print(layer_name)

        # search list of files of file with layer name in
        for file in files:

            if layer_name.lower() in file.lower():
                layer_path = file
                data['layer_name'].append(layer_path)
                data['reverse_polarity_flag'].append(layer_polarity)
                data['layer_weight'].append(layer_weight)

                # copy the file into the outputs dir
                copy_file(layer_path, join(data_path, output_dir, layer_path.split('/')[-1]))

    logger.info('Processed attractors')

    df = pd.DataFrame(data)
    print(df.head())
    df.to_csv(join(data_path, output_dir, 'attractors.csv'), index=False)
    logger.info('Written attractor csv')


def generate_constraints(files):
    """
    """
    # for each constraint as row in the table
    ## name = constraints.csv
    ## format
    ### name (file_name.asc); current_development_flag (0 or 1, default is 0, 1 being the current dev layer); threshold (percentage value, default=??25?)

    # data from the previous steps???
    #files = ['greenbelt_clip.asc', 'sssi_gb_clip.asc', 'currentdevelopment_clip.asc']

    #data = {'name': [], 'current_development_flag': [], 'threshold': []}
    data = {'layer_name': [], 'current_development_flag': [], 'layer_threshold': []}

    # should be replaced with user inputs
    constraints = getenv('constraints')
    if constraints == '' or constraints == 'None':  # if no extent passed
        constraints = None
    else:
        constraints = constraints.split(';')
    print(constraints)
    logger.info('Constraints input: %s' %constraints)

    constraint_currentdevelopment = getenv('current_development')

    if constraint_currentdevelopment == '' or constraint_currentdevelopment == 'None':  # if no extent passed
        constraint_currentdevelopment = None
    print('current-development', constraint_currentdevelopment)

    # input_str = 'greenbelt:0:25;sssi:0:30;development:1:50' # example input expected

    # loop through the constraint layers
    for layer in constraints:
        print('layer=',layer)
        if len(layer) == 0 or layer is None: break
        layer = layer.split(':')

        layer_name = layer[0]
        layer_threshold = layer[1]

        # search list of files of file with layer name in
        for file in files:

            if layer_name.lower() in file.lower():
                layer_path = file
                data['layer_name'].append(layer_path) # this is the path and the name of the file
                data['layer_threshold'].append(layer_threshold)
                data['current_development_flag'].append(0)

                # copy the file into the outputs dir
                copy_file(layer_path, join(data_path, output_dir, layer_path.split('/')[-1]))

    logger.info('Completed constraints')

    # add current dev layer to dataframe
    layer = constraint_currentdevelopment.split(':')

    layer_name = layer[0]
    layer_threshold = layer[1]

    # search list of files of file with layer name in
    for file in files:

        if layer_name.lower() in file.lower():
            layer_path = file
            data['layer_name'].append(layer_path)
            data['layer_threshold'].append(layer_threshold)
            data['current_development_flag'].append(1)

            # copy the file into the outputs dir
            copy_file(layer_path, join(data_path, output_dir,  layer_path.split('/')[-1]))

    logger.info('Completed development constraint')

    df = pd.DataFrame(data)
    print(df.head())
    df.to_csv(join(data_path, output_dir, 'constraints.csv'), index=False)
    logger.info('Written constraint csv')

# find any potential input files
available_files = find_files()
logger.info('Available files found: %s' %available_files)

generate_constraints(available_files)
logger.info('Constraints CSV generated')

generate_attractors(available_files)
logger.info('Attractors CSV generated')

# move other files # zone id and population
copy_file(source='/data/inputs/zone_identity_100m.asc', dest='/data/outputs/zone_identity_100m.asc')
#copy_file(source='/data/inputs/zone_identity.asc', dest='/data/outputs/data/zone_identity.asc')
copy_file(source='/data/inputs/population.csv', dest='/data/outputs/population.csv')
