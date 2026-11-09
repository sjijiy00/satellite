"""Reviewed next routes. Discovery hints are NEVER claims of scene availability."""
ROUTES=[
 {'purposes':['vegetation','flood','urban','thermal'],'provider':'USGS M2M / EarthExplorer','products':'Landsat 8/9 Collection 2 Level-2','authentication':'USGS account + M2M permission + Application Token','url':'https://www.usgs.gov/media/files/m2m-application-token-documentation','conditions':'Landsat public domain; account quota. AWS requester-pays is separate and remains disabled.'},
 {'purposes':['flood'],'provider':'Copernicus Data Space','products':'Sentinel-1 GRD','authentication':'CDSE account + OData access/refresh token; official 2FA when required','url':'https://documentation.dataspace.copernicus.eu/APIs/Token.html','conditions':'Sentinel legal notice/attribution and account quota; metadata search is not SAR preprocessing.'},
 {'purposes':['flood'],'provider':'NASA Earthdata / ASF','products':'Sentinel-1 SAR products','authentication':'Earthdata Login + ASF authorization as required','url':'https://docs.asf.alaska.edu/','conditions':'ASF route not connected in app. Product format/processing/EULA must be reviewed.'},
 {'purposes':['vegetation','thermal'],'provider':'NASA Earthdata / LP DAAC','products':'VIIRS surface reflectance / thermal products, product-specific','authentication':'Earthdata Login/User Token compatible with the DAAC; application authorization','url':'https://www.earthdata.nasa.gov/data/earthdata-login','conditions':'Only VNP09GA.002 is currently connected through CMR; other products not connected. Review product and redistribution terms.'},
 {'purposes':['thermal','flood'],'provider':'EUMETSAT Data Store','products':'Meteosat / polar products; per-product coverage','authentication':'EUMETSAT account + Data Store consumer key/secret for access token','url':'https://user.eumetsat.int/resources/user-guides/eumetsat-data-access-client-eumdac-guide','conditions':'Not connected. Geostationary field-of-view must match AOI; catalogue entries do not prove Korea coverage or access rights.'},
 {'purposes':['vegetation','flood','urban'],'provider':'Planet','products':'PlanetScope / SkySat according to contract','authentication':'Contract/account + API key','url':'https://docs.planet.com/develop/authentication/','conditions':'Commercial/contract and redistribution limits; app not connected, no paid requests.'},
]


def for_purpose(purpose):
    return [{**row,'checked_on':'2026-11-02','scene_confirmed':False,'scope':'Additional product/provider route, not searched for this AOI/period'} for row in ROUTES if purpose in row['purposes']]
