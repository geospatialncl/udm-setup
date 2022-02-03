# udm-setup
[![build](https://github.com/geospatialncl/udm-setup/workflows/build/badge.svg)](https://github.com/geospatialncl/udm-setup/actions)

Setup data for UDM model on DAFNI. Collects data from previous steps in the modelling flowline (clip outputs, population data), and reads user inputs to generate a final folder of data inputs and parameters which the OpenUDM model can then use. 

## Description
Generates the input tables required for UDM:
* attractors.csv
* constraints.csv
* parameters.csv

For the attractors and constraints tables the list of inputs are cross-checked with the the datasets found in the data directory, where a dataset file is then linked to the parameter with it's passed value(s) in the csv file generated.

### attractors
Contains a list layers considered to be attractors to development. The file has 3 fields:
* layer_name (string: the name of the file)
* reverse_polarity_flag (integer (0 or 1): if reverse the polarity (1) so layer considers being further away better)
* layer_weight (float: how important the layer is compared to others. All layers should sum to 1)

A row in the table may look like: roads_proximity_100m_clip.asc,0,0

### constraints
Contains a list of layers considered to be constraints to where development can happen. The file has 3 fields:
* layer_name (string: the name of the file)
* current_development_flag (integer: (0 or 1): 1 to denote the layer is the current development (only one layer should be set as 1))
* layer_threshold (float: the threshold % (value) at which to no longer permit the cell to be developed for the layer)

A row in the table may look like: developed_coverage_100m_clip.asc,1,0.3

### parameters
Contains the parameter values for 4 parameters for the UDM model:
* density_from_raster (integer: set to zero to derive density from current development and initial population - set to one to provide a density raster (density.asc))
* people_per_dwelling (float: conversion factor from people_per_cell to people_per_cell)
* coverage_threshold (float: percentage coverage threshold for combined constraint layers - cells above threshold are constrained)
* minimum_plot_size (integer: minimum number of contiguous cells withing a zones which constitute a development plot)

## Methods
### Passing data files
Data files should for the attractors and constraints should be placed in the '/data' directory as the code will search here for the files when matching passed parameters.

### Passing parameter values
All parameters should be passed as environmental variables (--env) to te docker container.

#### attractors
A semi-colan seperated list of attractor layers including a polarity value and a weight value.
* name: 'attractors'
* e.g: 'road:0.3:1;'

#### constraints
A semi-colan seperated list of constraint layers 
name: constraints

#### current development
A colan seperated list of a file name and a threshold value for % coverage denoting the pint it's considered already occupied/developed.
name: current_development

#### density from raster
Parameter (integer) to identify is new development density is taken from the input data (0) or from an input density raster
name: density_from_raster

#### people per dwelling
Float value for converting between people per cell and people per dwelling
name: people_per_dwelling

#### coverage threshold
Float value for the threshold value at which a cell is considered occupied/full and can't be developed when all constraints have been merged
name: coverage_threshold

#### minimum plot size
Integer value for the number of cells which must be clustered together to consider for development
name: minimum_plot_size

