import os
import io
import zipfile
from tools.ndvi_calc import (pull_sat_images,
                             clip_tif,
                             get_array,
                             get_tif,
                             get_png)
from fastapi import HTTPException
import numpy as np


def delete_files(*args):
    for file in args:
        os.remove(file)


def make_sat_request(geojson, sentinel_request):
    try:
        geojson = geojson.decode()
    except AttributeError:
        pass
    sat_response = pull_sat_images(geojson,
                                   sentinel_request.username,
                                   sentinel_request.password,
                                   sentinel_request.cloud_cover,
                                   sentinel_request.days_offset)

    if sat_response:
        sat_b04_path, sat_b08_path = sat_response
        return sat_b04_path, sat_b08_path
    else:
        raise HTTPException(500)


def clip_get_path(geojson, sentinel_request, token):
    sat_b04_path, sat_b08_path = make_sat_request(geojson, sentinel_request)
    clip_response = clip_tif(sat_b04_path, sat_b08_path, geojson, token)

    if clip_response:
        b04_path, b08_path = clip_response
        delete_files(sat_b04_path, sat_b08_path)
        return b04_path, b08_path
    else:
        raise HTTPException(500)


def prepare_zip(b04_path, b08_path):
    if os.path.exists(b04_path) and os.path.exists(b08_path):
        zip_bytes = io.BytesIO()

        with zipfile.ZipFile(zip_bytes, 'w') as zip_fh:
            for file in b04_path, b08_path:
                with open(file, 'rb') as fh:
                    data = fh.read()
                    zip_fh.writestr(fh.name, data)
                delete_files(file)
        return zip_bytes
    else:
        raise HTTPException(500)


def prepare_array(geojson, sentinel_request, token):
    b04_path, b08_path = clip_get_path(geojson, sentinel_request, token)
    array_meta = get_array(b04_path, b08_path)
    if array_meta is not False:
        return array_meta
    else:
        raise HTTPException(500)


def calculate_ndvi_values(geojson, sentinel_request, token):
    array, meta = prepare_array(geojson, sentinel_request, token)
    return {
        "max": np.nanmax(array),
        "mean": np.nanmean(array),
        "median": np.nanmedian(array),
        "min": np.nanmin(array)
    }


def get_picture(geojson, sentiel_request, token, tif):
    array, meta = prepare_array(geojson, sentiel_request, token)
    path = get_tif(array, meta, token) if tif else get_png(array, token)
    if path:
        return path
    else:
        raise HTTPException(500)
