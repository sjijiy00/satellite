"""Validated geocoder point + explicit user radius; no guessed extent."""
import math
from pyproj import Geod

def radius_bbox(center,radius):
    x,y=center
    if not all(math.isfinite(v) for v in (x,y,radius)) or not (124<=x<=132 and 33<=y<=39 and 0<radius<=100000):raise ValueError('radius/point range')
    geod=Geod(ellps='WGS84')
    points=[geod.fwd(x,y,i/10,radius)[:2] for i in range(3600)]
    # Dense geodesic perimeter plus one-metre guard, outward rounding. Korea only.
    dx=1/(111000*math.cos(math.radians(y)));dy=1/110000
    raw=[min(p[0] for p in points)-dx,min(p[1] for p in points)-dy,max(p[0] for p in points)+dx,max(p[1] for p in points)+dy]
    return [math.floor(v*1e7)/1e7 if i<2 else math.ceil(v*1e7)/1e7 for i,v in enumerate(raw)]
