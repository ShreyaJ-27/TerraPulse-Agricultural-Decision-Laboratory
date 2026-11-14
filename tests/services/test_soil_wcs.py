from io import BytesIO

import httpx
import pytest
from PIL import Image, TiffImagePlugin

from app.contracts import DataStatus
from app.services.soil.adapter import SoilGridsAdapter
from app.services.soil.exceptions import SoilResponseMalformedError
from app.services.soil.wcs import SoilGridsWcsClient, sample_geotiff


def raster(value=300, *, crs=4326):
    # Signed Int16 raster with a distinguishable upper-left pixel.
    import struct

    tile = Image.frombytes("I", (2, 2), struct.pack("<4h", 999, value, 999, 999), "raw", "I;16S")
    tags = TiffImagePlugin.ImageFileDirectory_v2()
    for code, values in {33550: (0.01, 0.01, 0.), 33922: (0., 0., 0., 75., 16., 0.)}.items():
        tags.tagtype[code] = 12
        tags[code] = values
    tags.tagtype[34735] = 3
    tags[34735] = (1, 1, 0, 2, 1025, 0, 1, 1, 2048, 0, 1, crs)
    tags[42113] = "-32768"
    # Pillow writes I mode as Int32. Patch the baseline TIFF sample size and
    # strip byte count, then replace the strip with the equivalent Int16 data.
    out = BytesIO()
    tile.save(out, format="TIFF", tiffinfo=tags)
    data = bytearray(out.getvalue())
    offset = struct.unpack_from("<I", data, 4)[0]
    count = struct.unpack_from("<H", data, offset)[0]
    for index in range(count):
        entry = offset + 2 + 12 * index
        tag, _, _, field = struct.unpack_from("<HHII", data, entry)
        if tag == 258:
            struct.pack_into("<H", data, entry + 8, 16)
        elif tag == 273:
            strip = field
        elif tag == 279:
            struct.pack_into("<I", data, entry + 8, 8)
    data[strip:strip + 8] = struct.pack("<4h", 999, value, 999, 999)
    return bytes(data)


def test_geotiff_samples_containing_pixel_and_rejects_invalid_georeferencing():
    assert sample_geotiff(raster(0), 15.995, 75.015) == 0
    assert sample_geotiff(raster(-32768), 15.995, 75.015) is None
    for content, lat, lon in [
        (raster(crs=3857), 15.995, 75.015),
        (raster(), 16.02, 75.015),
        (b"<ServiceException/>", 15.995, 75.015),
    ]:
        with pytest.raises(SoilResponseMalformedError):
            sample_geotiff(content, lat, lon)


@pytest.mark.parametrize("failure", [None, "nodata", "zero", "http", "xml", "timeout"])
@pytest.mark.asyncio
async def test_wcs_profile_provenance_and_missing_coverage(failure):
    def respond(request):
        coverage = request.url.params["COVERAGEID"]
        assert request.url.params["REQUEST"] == "GetCoverage"
        assert len(request.url.params.get_list("SUBSET")) == 2
        if coverage == "wv0033_5-15cm_mean":
            if failure == "http":
                return httpx.Response(503)
            if failure == "xml":
                return httpx.Response(200, content=b"<ServiceException/>")
            if failure == "timeout":
                raise httpx.ReadTimeout("upstream timeout")
            value = {"nodata": -32768, "zero": 0}.get(failure, 330)
        else:
            value = 300 if coverage.startswith("wv0033") else 120
        return httpx.Response(200, content=raster(value))

    async with httpx.AsyncClient(transport=httpx.MockTransport(respond)) as http:
        adapter = SoilGridsAdapter(SoilGridsWcsClient(http_client=http))
        result = await adapter.fetch_soil(15.995, 75.015, 20, ["wv0033", "wv1500"])

    assert result.data_source_ids == ["isric:soilgrids:wcs"]
    assert result.provenance[0].source_id == "isric:soilgrids:wcs"
    assert result.soil_properties.wilting_point.value == 0.12
    if failure is None:
        assert result.availability.status == DataStatus.AVAILABLE
        assert result.soil_properties.field_capacity.value == 0.315
        assert "wv0033_5-15cm_mean" in result.provenance[0].reference
    else:
        assert result.availability.status == DataStatus.MISSING
        assert result.soil_properties.field_capacity.value is None
        assert result.raw_metadata["coverages"]["wv0033_5-15cm_mean"] != "sampled"
