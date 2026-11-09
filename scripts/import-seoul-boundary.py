"""Import ONLY SGIS 2025 Q2 Seoul from the official downloaded ZIP. No runtime network.

Usage: .venv/Scripts/python scripts/import-seoul-boundary.py path/to/official.zip
Restricted ESRI Polygon (type 5) + DBF reader; fail closed on other formats.
"""
import hashlib
import json
from pathlib import Path
import struct
import sys
import zipfile
from pyproj import CRS, Transformer
from shapely.geometry import Polygon, MultiPolygon, mapping
from shapely.ops import transform

ROOT=Path(__file__).resolve().parents[1]

def dbf(data):
    count=struct.unpack_from('<I',data,4)[0];header,length=struct.unpack_from('<HH',data,8)
    fields=[];pos=32
    while data[pos]!=13:
        fields.append((data[pos:pos+11].split(b'\0')[0].decode('ascii'),data[pos+16]));pos+=32
    rows=[]
    for i in range(count):
        row=data[header+i*length:header+(i+1)*length];p=1;record={}
        if row[0]!=32:raise ValueError('Deleted record')
        for name,size in fields:record[name]=row[p:p+size].decode('utf-8').strip();p+=size
        rows.append(record)
    return rows

def polygon(content):
    if struct.unpack_from('<I',content)[0]!=5:raise ValueError('Only Polygon supported')
    n,points=struct.unpack_from('<II',content,36)
    indexes=list(struct.unpack_from('<'+'I'*n,content,44))+[points]
    xy=[struct.unpack_from('<dd',content,44+4*n+16*i) for i in range(points)]
    rings=[Polygon(xy[indexes[i]:indexes[i+1]]) for i in range(n)]
    # Containment assigns holes independently of shapefile orientation.
    parents=[]
    for i,r in enumerate(rings):
        containers=[j for j,s in enumerate(rings) if j!=i and s.area>r.area and s.contains(r.representative_point())]
        parents.append(min(containers,key=lambda j:rings[j].area) if containers else None)
    def depth(i):return 0 if parents[i] is None else 1+depth(parents[i])
    shapes=[Polygon(r.exterior.coords,[rings[j].exterior.coords for j,p in enumerate(parents) if p==i]) for i,r in enumerate(rings) if depth(i)%2==0]
    g=MultiPolygon(shapes)
    if not g.is_valid:raise ValueError('Invalid official geometry')
    return g

def main(source,code='11'):
    name,stem,area_range,expected_bounds={'11':('서울특별시','seoul',(550e6,660e6),(126,37,128,39)),
        '39':('제주특별자치도','jeju',(1700e6,2100e6),(125,32,128,35))}[code]
    with zipfile.ZipFile(source) as z:
        base=next(n[:-4] for n in z.namelist() if n.endswith('bnd_sido_00_2025_2Q.shp'))
        components={ext:z.read(base+ext) for ext in ('.shp','.dbf','.prj','.cpg')}
    crs=CRS.from_wkt(components['.prj'].decode())
    if crs.to_epsg()!=5179:raise ValueError('Unexpected original CRS')
    rows=dbf(components['.dbf']);data=components['.shp'];offset=100;chosen=None
    for row in rows:
        number,words=struct.unpack_from('>II',data,offset);offset+=8
        content=data[offset:offset+words*2];offset+=words*2
        if row.get('SIDO_CD')==code:chosen=(row,polygon(content))
    if not chosen:raise ValueError('Seoul code 11 absent')
    row,g=chosen
    if row.get('SIDO_NM')!=name or row.get('BASE_DATE')!='20250630' or not area_range[0]<g.area<area_range[1]:raise ValueError('Administrative identity/date/area mismatch')
    project=Transformer.from_crs(crs,4326,always_xy=True)
    wgs=transform(project.transform,g)
    w,s,e,n=wgs.bounds
    if not (expected_bounds[0]<w<e<expected_bounds[2] and expected_bounds[1]<s<n<expected_bounds[3]):raise ValueError('Axis/CRS mismatch')
    geom=mapping(wgs)
    record={'type':'Feature','properties':{'code':code,'name':row['SIDO_NM'],'base_date':row.get('BASE_DATE')},'geometry':geom}
    folder=ROOT/'backend/app/data/boundaries';folder.mkdir(exist_ok=True)
    output=folder/(stem+'-sgis-2025-q2.geojson');output.write_text(json.dumps(record,ensure_ascii=False,separators=(',',':')),encoding='utf-8')
    meta={'id':'sgis-'+stem+'-2025-q2','name':name,'code':code,'code_system':'SGIS SIDO_CD','mois_prefix':'50' if code=='39' else '11',
          'year':'2025-06-30 (2025년 2분기)','source':'국가데이터처 SGIS 행정구역 통계 및 경계',
          'source_url':'https://www.data.go.kr/data/15129688/fileData.do',
          'download_url':'https://www.data.go.kr/cmm/cmm/fileDownload.do?atchFileId=FILE_000000003681593&fileDetailSn=1&dataNm=SGIS',
          'terms':'공공데이터포털 이용허락범위 제한 없음 (2026-11-02 확인), 출처 표시',
          'original_crs':'EPSG:5179','crs':'EPSG:4326','axis_order':'longitude, latitude','always_xy':True,
          'original_component_sha256':{k:hashlib.sha256(v).hexdigest() for k,v in components.items()},
          'source_archive_sha256':hashlib.file_digest(open(source,'rb'),'sha256').hexdigest(),
          'geojson_sha256':hashlib.sha256(output.read_bytes()).hexdigest(),'bbox':list(wgs.bounds),'area_km2':g.area/1e6,
          'note':'SGIS 통계서비스 경계, 2025년 2분기 자료. 법적 측량/최신 경계 확정 아님. 원본 꼭짓점 유지, 간소화 없음.'}
    (folder/(stem+'-sgis-2025-q2.metadata.json')).write_text(json.dumps(meta,ensure_ascii=False,indent=2),encoding='utf-8')
    print(json.dumps({'row':row,'bbox':meta['bbox'],'area_km2':meta['area_km2'],'bytes':output.stat().st_size},ensure_ascii=True))

if __name__=='__main__':main(Path(sys.argv[1]),sys.argv[2] if len(sys.argv)>2 else '11')
