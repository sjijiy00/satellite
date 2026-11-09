"""Actual pixel arrays are the only source of optional map visualization PNGs."""
import base64
import struct
import zlib

from app.change_analysis import process_change
from test_change_analysis import pair


def rgba(preview):
    data=base64.b64decode(preview['png_base64'])
    assert data[:8]==b'\x89PNG\r\n\x1a\n'
    width,height=struct.unpack('>II',data[16:24])
    offset=8;body=b''
    while offset<len(data):
        length=struct.unpack('>I',data[offset:offset+4])[0]
        kind=data[offset+4:offset+8];payload=data[offset+8:offset+8+length]
        if kind==b'IDAT':body+=payload
        offset+=12+length
    raw=zlib.decompress(body)
    return width,height,raw


def test_real_arrays_only_emit_quality_and_ndvi_visualization(pair):
    payload,_=pair
    result=process_change(payload)
    assert result['status']=='computed'
    layers=result['map_layers']
    assert len(layers['quality'])==2 and layers['analysis']['scene_ids']==['TEST_ONLY_0','TEST_ONLY_1']
    for preview in [*layers['quality'],layers['analysis']]:
        width,height,raw=rgba(preview)
        assert (width,height)==(4,4) and len(raw)==4*(1+4*4)
        assert len(preview['coordinates'])==4 and '실제' in preview['label']
