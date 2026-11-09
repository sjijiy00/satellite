"""Finite normalized differences; reuse the existing NDVI numerical policy."""
from .change_analysis import ndvi

FORMULAS={'ndvi':'(NIR-RED)/(NIR+RED)','mndwi':'(GREEN-SWIR1)/(GREEN+SWIR1)',
          'mndwi_change':'(GREEN-SWIR1)/(GREEN+SWIR1); change=after-before','ndbi':'(SWIR1-NIR)/(SWIR1+NIR)'}

def index(method,bands,valid):
    if method=='ndvi':return ndvi(bands['red'],bands['nir'],valid)
    if method in ('mndwi','mndwi_change'):return ndvi(bands['swir16'],bands['green'],valid)
    if method=='ndbi':return ndvi(bands['nir'],bands['swir16'],valid)
    raise ValueError('Unregistered normalized difference')
