# udm-setup
[![build](https://github.com/geospatialncl/udm-setup/build/badge.svg)](https://github.com/OpenCLIM/udm-dafni/actions) 

Setup data for UDM model. Currenly only method 2 below is operational, with others to be enabled with further updates.

## Usage
Three usage patterns:  
(1) Generate a grid for rasterising data with (only)  
(2) Rasterise vector datasets (input) using a grid  
(3) Download and rasterise data from NISMOD-DB API

### Methods
#### (1) Generate a grid
To generate a grid only using a list of LADs or GOR's  
`<example code here>`

#### (2) Rasterise vector datasets (input) using a grid
Pass a set of files with vector data in (in a format which can be loaded by the python geopandas library). Optionally, can also pass a fishnet/grid file to rasterise with, or one can be generated using 1 of 3 methods and output.
Grid generation:  
  (1) Provide a grid  
        `<example code here>`  
  (2) Provide a list of LAD's or GOR's    
        `<example code here>`  
  (3) Grid based on the input dataset (this could result in a different grid for each dataset)  
        `<example code here>`

#### (3) Download and rasterise data from NISMOD-DB API
Use NISMOD-DB API to download data and rasterise.  
`<example code needed>`

### Expected environmental variables
API_URL=  
USERNAME=  
PASSWORD=  