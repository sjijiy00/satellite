import json,zipfile
from uuid import uuid4
import numpy as np
import pytest
import rasterio
from app.thermal_ml import estimate
from app.processing_failure import ProcessingBlocked
from app import artifact_store
from app.processing_worker import execute
from test_product_engines import sample,private_store


def arrays():
 y,x=np.indices((96,96));donor=300+5*np.sin(x/8)+3*np.cos(y/7)
 target=donor+3+2*x/95+y/95
 valid=np.ones(donor.shape,bool);cloud=valid.copy();cloud[:]=False;cloud[36:60,36:60]=True
 return target,donor,valid&~cloud,valid,cloud,valid


def test_buffered_validation_preserves_observed_and_does_not_read_cloud_truth():
 a=list(arrays());values,status,e=estimate(*a)
 assert e['status']=='passed' and e['model']['rmse_k']<.1 and (status==2).any()
 assert np.array_equal(values[status==1],a[0][status==1])
 a[0]=a[0].copy();a[0][a[4]]=1000000
 again,newstatus,ee=estimate(*a)
 assert np.array_equal(newstatus,status) and np.array_equal(values,again,equal_nan=True)
 assert e['model_sha256']==ee['model_sha256'] and len(e['folds'])==4


@pytest.mark.parametrize('fault',['no_cloud','no_donor','few_pairs','poor_fit','copy_already_exact','outside_support'])
def test_quality_gates_do_not_publish_fake_accuracy(fault):
 a=list(arrays())
 if fault=='no_cloud':a[4][:]=False
 if fault=='no_donor':a[3]=a[3]&~a[4]
 if fault=='few_pairs':a[2][:]=False;a[2][0:10,0:10]=True
 if fault=='poor_fit':a[0]=np.random.default_rng(42).uniform(280,340,a[0].shape)
 if fault=='copy_already_exact':a[0]=a[1].copy()
 if fault=='outside_support':a[1][a[4]]=500
 with pytest.raises(ProcessingBlocked) as e:estimate(*a)
 assert e.value.failure['ml_validation']['status']=='blocked'
 assert e.value.failure['ml_validation']['cloud_truth_accuracy_verified'] is False


def fixture_payload(tmp_path):
 q,p,raw,g=sample(tmp_path,'thermal_ml','pc_landsat',bbox=[126.7,36.4,126.73,36.43])
 y,x=np.indices((g['height'],g['width']));donor=45000+900*np.sin(x/8)+600*np.cos(y/7)
 target=donor+1200+500*x/g['width']+250*y/g['height']
 for scene,a in zip(p['scenes'],[target,donor]):
  with rasterio.open(scene['assets']['lwir11']['path'],'r+') as ds:ds.write(a.astype('uint16'),1)
 with rasterio.open(p['scenes'][0]['assets']['qa_pixel']['path'],'r+') as ds:
  a=ds.read(1);a[30:50,30:50]=8;ds.write(a,1)
 return q,p


def test_real_tiff_qa_worker_artifacts_and_ml_record(tmp_path):
 q,p=fixture_payload(tmp_path);result=execute(p,uuid4().hex)
 assert result['result']['ml_validation']['status']=='passed'
 assert result['result']['cloud_fill']['mode']=='ml_estimate'
 artifact=result['artifact'];path=artifact_store.verified_download(artifact['filename'][11:-4],artifact)
 with zipfile.ZipFile(path) as z:
  m=json.loads(z.read('manifest.json'));assert m['model']['status']=='passed'
  steps={s['id']:s['status'] for s in m['execution_record']['steps']}
  assert steps['estimate']=='completed' and steps['composite']=='skipped'
  def read(name):
   with rasterio.io.MemoryFile(z.read(name)) as f:
    with f.open() as d:return d.read()
  status=read('pixel_status.tif')[0];values=read('estimate_with_observed.tif');original=read('target_temperature.tif');estimated=read('estimated_only.tif')
  assert (status==2).any() and np.array_equal(values[:,status==1],original[:,status==1])
  assert np.all(estimated[:,status!=2]==-9999) and np.all(original[:,status==2]==-9999)
  assert np.all(read('donor_index.tif')[0][status==2]==2) and np.all(read('donor_index.tif')[0][status!=2]==0)
  assert np.all(read('donor_date.tif')[0][status!=2]==-2147483648)
  assert not any(n in z.namelist() for n in ['multi_date_temperature.tif','source_date.tif'])


def test_ml_request_requires_two_scenes_and_bounded_aoi(tmp_path):
 from app.processing_models import ProcessingRequest
 from app.processing_raster import processing_grid
 from app.pixel_policy import QualityError
 q,p=fixture_payload(tmp_path)
 q['scenes']=q['scenes'][:1]
 with pytest.raises(ValueError):ProcessingRequest.model_validate(q)
 p['bbox']=[126.7,36.4,126.8,36.5];p['roi']['bbox']=p['bbox']
 with pytest.raises(QualityError):processing_grid(p)
