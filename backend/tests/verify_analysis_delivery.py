"""TEST ONLY independent inspection of a complete browser-saved processing ZIP.

No network/authentication. Recomputes output consistency and area-weighted
statistics; fixed input-DN/formula accuracy is covered separately by pytest.
"""
import hashlib
import json
from pathlib import Path
import sys
import zipfile
import numpy as np
import rasterio
from rasterio.io import MemoryFile
from pyproj import Transformer
import shapely
from shapely.geometry import box, shape

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from app.analysis_catalog import METHODS


def verify(filename, output):
    path=Path(filename);content=path.read_bytes()
    with zipfile.ZipFile(path) as z:
        assert z.testzip() is None
        m=json.loads(z.read('manifest.json'));query=m['input'];method=query['method_id'];contract=METHODS[method]
        assert m['verified_after_disk_write'] and m['execution_record']['source_mode']=='canonical_server_range'
        assert set(contract['artifacts'])<=set(z.namelist())
        g=m['grid'];arrays={};evidence=[]
        for name,entry in m['files'].items():
            raw=z.read(name);assert len(raw)==entry['bytes'] and hashlib.sha256(raw).hexdigest()==entry['sha256']
            if not name.endswith('.tif'):continue
            with MemoryFile(raw) as memory:
                with memory.open() as ds:
                    spec=contract['artifact_specs'][name]
                    assert ds.crs==rasterio.crs.CRS.from_user_input(g['crs'])
                    assert (ds.width,ds.height)==(g['width'],g['height'])
                    assert np.allclose(list(ds.transform)[:6],g['transform'],atol=1e-8,rtol=0)
                    assert ds.nodata==spec['nodata'] and ds.count==spec['bands'] and all(d==spec['dtype'] for d in ds.dtypes)
                    units=[ds.tags(i).get('unit') for i in range(1,ds.count+1)]
                    assert units==spec.get('units',[spec.get('unit')]*ds.count)
                    values=ds.read();assert np.isfinite(values).all();arrays[name]=values
                    evidence.append({'name':name,'bytes':len(raw),'sha256':entry['sha256'],'crs':ds.crs.to_wkt(),
                        'width':ds.width,'height':ds.height,'bands':ds.count,'nodata':ds.nodata,'units':units,'reopened':True})
        valid=arrays['valid_mask.tif'][0]==1;codes=arrays['exclusion_mask.tif'][0] if method!='thermal_gapfill' else np.where(valid,3,0)
        assert valid.any() and np.isin(arrays['valid_mask.tif'],[0,1]).all() and np.isin(codes,[0,1,2,3]).all()
        assert np.array_equal(codes==3,valid)
        # Independent cell intersections, using the persisted CRS/transform and
        # user-confirmed ROI rather than trusting the server's reported area.
        roi=query['roi'];geometry=shape(roi['geometry']) if roi['mode']=='polygon' else box(*roi['bbox'])
        project=Transformer.from_crs(4326,g['crs'],always_xy=True).transform
        geometry=shapely.transform(geometry.segmentize(.001),project,interleaved=False)
        a,b,c,d,e,f=g['transform'];assert b==d==0 and a>0 and e<0
        xx,yy=np.meshgrid(c+np.arange(g['width'])*a,f+np.arange(g['height'])*e)
        cells=shapely.box(xx,yy+e,xx+a,yy)
        weights=shapely.area(shapely.intersection(cells,geometry))
        area=float(weights[valid].sum());record=m['record'];stats=record.get('statistics',{})
        assert np.isclose(area,record['cloud_fill']['composite_valid_area_m2'] if method in ('thermal_gapfill','thermal_ml') else record.get('analysis_area_m2',record['common_valid_area_m2']),atol=.1,rtol=1e-6)
        assert query['start_date']<=query['end_date']
        assert all(query['start_date']<=s['datetime'][:10]<=query['end_date'] for s in m['sources'])
        assert len({(s['provider_id'],s['collection'],s['id']) for s in query['scenes']})==len(query['scenes'])
        def mean(values,mask=valid,w=weights):return float(np.sum(values[mask]*w[mask])/w[mask].sum())
        def summary(values,expected):
            assert np.isclose(mean(values),expected['mean'],atol=2e-4,rtol=1e-6)
            assert np.isclose(float(values[valid].min()),expected['minimum'],atol=2e-4)
            assert np.isclose(float(values[valid].max()),expected['maximum'],atol=2e-4)
        if method=='thermal_ml':
            from datetime import date
            status=arrays['pixel_status.tif'][0];combined=arrays['estimate_with_observed.tif'];estimated=status==2
            assert np.isin(status,[0,1,2]).all() and np.array_equal(status>0,valid)
            assert np.allclose(combined[0][valid]-combined[1][valid],273.15,atol=.0001)
            for code,name,key in [(1,'target_temperature.tif','target_celsius'),(2,'estimated_only.tif','estimated_celsius')]:
                mask=status==code;v=arrays[name]
                assert np.array_equal(combined[:,mask],v[:,mask]) and np.all(v[:,~mask]==-9999)
                if mask.any():assert np.isclose(mean(v[1],mask),stats[key]['mean'],atol=2e-4)
            assert np.array_equal(arrays['donor_index.tif'][0],np.where(estimated,2,0))
            day=(date.fromisoformat(m['sources'][1]['datetime'][:10])-date(1970,1,1)).days
            assert np.array_equal(arrays['donor_date.tif'][0],np.where(estimated,day,-2147483648))
            assert np.isclose(weights[estimated].sum(),record['cloud_fill']['filled_area_m2'],atol=.1)
            assert int(estimated.sum())==record['ml_validation']['estimated_cells']>0
            assert record['ml_validation']['status']=='passed' and not record['ml_validation']['cloud_truth_accuracy_verified']
        elif method=='thermal_gapfill':
            from datetime import date
            status=arrays['pixel_status.tif'][0];sources=arrays['source_index.tif'][0];days=arrays['source_date.tif'][0]
            assert np.array_equal(sources,status) and np.array_equal(status>0,valid)
            combined=arrays['multi_date_temperature.tif'];assert np.allclose(combined[0][valid]-combined[1][valid],273.15,atol=.0001)
            for code,name,key in [(1,'target_temperature.tif','target_celsius'),(2,'filled_only.tif','other_date_fill_celsius')]:
                mask=status==code;v=arrays[name]
                assert np.array_equal(combined[:,mask],v[:,mask]) and np.all(v[:,~mask]==-9999)
                expected_day=(date.fromisoformat(m['sources'][code-1]['datetime'][:10])-date(1970,1,1)).days
                assert np.all(days[mask]==expected_day)
                if mask.any():assert np.isclose(mean(v[1],mask),stats[key]['mean'],atol=2e-4)
                else:assert stats[key]['mean'] is None
            assert np.isclose(weights[status==2].sum(),record['cloud_fill']['filled_area_m2'],atol=.1)
        elif method=='ndvi_change':
            before,after,difference=arrays['ndvi_change.tif']
            assert np.allclose(difference[valid],(after-before)[valid],atol=2e-6)
            for value,key in [(before,'ndvi_before_mean'),(after,'ndvi_after_mean'),(difference,'ndvi_difference_mean')]:
                assert np.isclose(mean(value),record[key],atol=2e-6)
            assert max(abs(before[valid]).max(),abs(after[valid]).max())<=1.00001
        elif method in ('ndvi','mndwi','mndwi_change','ndbi'):
            values=arrays[method+'.tif']
            if method=='mndwi_change':
                before,after,difference=values
                assert np.allclose(difference[valid],(after-before)[valid],atol=2e-6)
                summary(before,stats['before']);summary(after,stats['after']);summary(difference,stats['difference'])
                expected=np.where(valid,1+(before>query['threshold']).astype('uint8')+2*(after>query['threshold']).astype('uint8'),0)
                assert np.array_equal(arrays['water_change.tif'][0],expected)
            else:
                value=values[0];assert abs(value[valid]).max()<=1.00001;summary(value,stats)
                if method=='mndwi':assert np.array_equal(arrays['water_candidates.tif'][0],np.where(valid,np.where(value>query['threshold'],2,1),0))
        else:
            kelvin,celsius=arrays['temperature.tif'];uncertainty,distance=arrays['temperature_quality.tif']
            assert np.allclose((kelvin-celsius)[valid],273.15,atol=.0001)
            assert kelvin[valid].min()>149 and kelvin[valid].max()<450
            assert (uncertainty[valid]<=query['qa_options']['maximum_uncertainty_k']+1e-5).all()
            assert (distance[valid]>=query['qa_options']['minimum_cloud_distance_km']-1e-5).all()
            summary(kelvin,stats['kelvin']);summary(celsius,stats['celsius'])
            if method=='hotspots':assert np.array_equal(arrays['hotspots.tif'][0],np.where(valid,np.where(celsius>query['threshold'],2,1),0))
            if method=='temperature_comparison':
                means=[]
                for region,expected in zip(query['comparison_regions'],stats['regions']):
                    geom=shape(region['geometry']) if region['mode']=='polygon' else box(*region['bbox'])
                    projected=shapely.transform(geom.segmentize(.001),project,interleaved=False)
                    regional=shapely.area(shapely.intersection(cells,projected.intersection(geometry)))
                    means.append(mean(celsius,valid,regional));assert np.isclose(means[-1],expected['mean_celsius'],atol=2e-4)
                assert np.isclose(means[0]-means[1],stats['mean_difference_celsius_first_minus_second'],atol=4e-4)
        result={'analysis_id':query['analysis_id'],'method':method,'input':query,'zip_bytes':len(content),
            'zip_sha256':hashlib.sha256(content).hexdigest(),'crs_grid_nodata_units_verified':True,
            'numeric_consistency_verified':True,'valid_area_m2_recomputed':area,'files':evidence,
            'scope':'real browser file reopened; output arithmetic/statistics checked; physical ground truth and GUI GIS not verified'}
        result['numeric_outputs_at_common_valid_cells']={name:[{'band':i+1,'minimum':float(band[valid].min()),
            'maximum':float(band[valid].max()),'area_weighted_mean':mean(band),'valid_cells':int(valid.sum())}
            for i,band in enumerate(values)] for name,values in arrays.items() if values.dtype.kind=='f'}
        result['categorical_full_grid_counts']={name:{str(int(value)):int(count) for value,count in zip(*np.unique(values,return_counts=True))}
            for name,values in arrays.items() if values.dtype.kind in ('u','i')}
        Path(output).write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf8')


if __name__=='__main__':verify(sys.argv[1],sys.argv[2])
