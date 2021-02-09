FROM python:3.8
RUN apt-get -y update
RUN apt-get -y install libgdal-dev
COPY requirements.txt /
RUN pip install -r requirements.txt
RUN git clone --branch test https://github.com/geospatialncl/udm-rasteriser
#RUN pip install -r udm-rasteriser/requirements.txt
