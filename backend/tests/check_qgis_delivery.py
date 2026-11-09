"""Optional installed QGIS isolated/headless provider+render verification.
Run with QGIS's own python-qgis.bat, not the project's Python environment.
Does not open/change the operator's current QGIS project or profile.
"""
import json
import math
import os
from pathlib import Path
import sys
import zipfile
os.environ['QT_QPA_PLATFORM']='offscreen'
from qgis.core import QgsApplication,QgsRasterLayer,QgsMapSettings,QgsMapRendererSequentialJob,Qgis
from qgis.PyQt.QtCore import QSize

root=Path(sys.argv[1]);out=root/'qgis';out.mkdir(exist_ok=True)
app=QgsApplication([],False,str(out/'isolated-profile'));app.initQgis()
rows=[]
try:
    for archive in (root/'e2e-live-artifacts').rglob('*.zip'):
        with zipfile.ZipFile(archive) as z:
            manifest=json.loads(z.read('manifest.json'));analysis=manifest['input']['analysis_id']
            folder=out/(analysis+'-'+archive.stem);folder.mkdir(exist_ok=True)
            for name in z.namelist():
                if not name.endswith('.tif'):continue
                assert '/' not in name and '\\' not in name
                file=folder/name;file.write_bytes(z.read(name))
                layer=QgsRasterLayer(str(file),name,'gdal');assert layer.isValid() and layer.crs().isValid()
                provider=layer.dataProvider()
                for band in range(1,layer.bandCount()+1):
                    block=provider.block(band,layer.extent(),layer.width(),layer.height())
                    assert block.isValid()
                    assert provider.sourceHasNoDataValue(band)
                    assert math.isfinite(provider.sourceNoDataValue(band))
                row={'analysis_id':analysis,'file':name,'qgis_valid':True,'width':layer.width(),'height':layer.height(),
                     'bands':layer.bandCount(),'crs_wkt':layer.crs().toWkt(),'qgis_version':Qgis.QGIS_VERSION,'scope':'isolated headless QGIS provider; desktop GUI not used'}
                if name not in ('valid_mask.tif','exclusion_mask.tif','temperature_quality.tif'):
                    settings=QgsMapSettings();settings.setLayers([layer]);settings.setDestinationCrs(layer.crs());settings.setExtent(layer.extent());settings.setOutputSize(QSize(512,512))
                    job=QgsMapRendererSequentialJob(settings);job.start();job.waitForFinished()
                    image=job.renderedImage();assert not image.isNull();assert image.save(str(folder/(name+'.png')))
                    row['qgis_rendered']=True
                    del job,settings,image
                rows.append(row);del layer,provider,block
    assert rows, 'No real browser ZIPs found'
    (out/'result.json').write_text(json.dumps(rows,ensure_ascii=False,indent=2),encoding='utf8')
    print(json.dumps({'files':len(rows),'analyses':len(set(r['analysis_id'] for r in rows)),'qgis_version':Qgis.QGIS_VERSION,'mode':'isolated headless provider/read/render; desktop GUI not executed'}))
finally:
    app.exitQgis()
