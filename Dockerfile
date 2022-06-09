FROM python

FROM ubuntu:20.04

WORKDIR ndvi

COPY requirements.txt requirements.txt

RUN apt-get update && apt-get install -y binutils libproj-dev gdal-bin

RUN apt install -y libopenjp2-7 libopenjp2-tools 

RUN apt-get install -y python3-pip

RUN pip install --upgrade pip

RUN pip install -r requirements.txt
 
COPY webapp/ .

EXPOSE 8000

CMD cd ~ && uvicorn main:app
