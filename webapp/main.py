import os
import secrets
import aioredis
import mimetypes
from fastapi import (FastAPI,
                     UploadFile,
                     File,
                     HTTPException,
                     responses)
from pydantic import BaseModel

from shortcuts import (clip_get_path,
                       calculate_ndvi_values,
                       prepare_zip,
                       get_picture)

app = FastAPI()
r = aioredis.Redis()

token_length = os.getenv('TOKEN_BYTES_LENGTH', 8)
geojson_hours_alive = os.getenv('GEOJSON_HOURS_ALIVE', 24)


class SentinelRequest(BaseModel):
    username: str
    password: str
    days_offset: int = 14
    cloud_cover: int = 15


async def check_geojson(geojson_id):
    geojson = await r.get(f'{geojson_id}_geojson')
    if geojson:
        return geojson

    else:
        raise HTTPException(404, detail='Not found, already deleted or '
                                        'invalid token')


async def get_image(geojson_id, sentiel_request, tif):
    geojson = await check_geojson(geojson_id)
    path = get_picture(geojson, sentiel_request, geojson_id, tif)
    return responses.FileResponse(path, media_type=mimetypes.guess_type(
        path)[0], content_disposition_type='attachment', filename=path)


@app.post("/load_geojson/")
async def load_geojson(file: UploadFile = File()):
    token = secrets.token_urlsafe(int(token_length))
    rset = await r.set(f'{token}_geojson', file.file.read())

    if rset:
        await r.expire(f'{token}_geojson', int(geojson_hours_alive) * 60 * 60)
        return {"token": token,
                "message": f'Created! File be alive for {geojson_hours_alive}'
                           f' hours'}

    else:
        return HTTPException(500)


@app.delete('/delete_geojson/{geojson_id}')
async def delete_geojson(geojson_id):
    rdel = await r.delete(f'{geojson_id}_geojson')
    if rdel:
        raise HTTPException(204, detail='Deleted')
    else:
        raise HTTPException(404, detail='Not found, already deleted or '
                                        'invalid token')


@app.post('/pull_images/{geojson_id}')
async def pull_images(geojson_id, sentinel_request: SentinelRequest):
    geojson = await check_geojson(geojson_id)
    b04_path, b08_path = clip_get_path(geojson,
                                       sentinel_request,
                                       geojson_id)
    zip_bytes = prepare_zip(b04_path, b08_path)

    return responses.StreamingResponse(iter([zip_bytes.getvalue()]),
                                       media_type="application/"
                                                  "x-zip-compressed",
                                       headers={
                                           "Content-Disposition":
                                               f"attachment;filename="
                                               f"{geojson_id}.zip"})


@app.post('/calc_ndvi/{geojson_id}')
async def calculate_ndvi(geojson_id, sentinel_request: SentinelRequest):
    geojson = await check_geojson(geojson_id)
    data = calculate_ndvi_values(geojson, sentinel_request, geojson_id)
    return data


@app.post('/tif_ndvi/{geojson_id}')
async def ndvi_image_tif(geojson_id, sentiel_request: SentinelRequest):
    return await get_image(geojson_id, sentiel_request, True)


@app.post('/png_ndvi/{geojson_id}')
async def ndvi_image_png(geojson_id, sentiel_request: SentinelRequest):
    return await get_image(geojson_id, sentiel_request, False)
