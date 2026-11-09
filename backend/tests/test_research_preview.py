"""TEST ONLY: displayed percentile ranges match the actual raster colors."""
import numpy as np
import pytest
from app import product_processing

def test_preview_scale_excludes_masked_outliers_and_preserves_values(monkeypatch):
    captured={}
    def preview(rgba,g,label,ids):
        captured['rgba']=rgba
        return {'label':label,'scene_ids':ids}
    monkeypatch.setattr(product_processing,'map_preview',preview)
    values=np.array([[10.,20.,30.],[40.,50.,9999.]])
    mask=np.array([[True,True,True],[True,True,False]])
    before=values.copy()
    result=product_processing.display(values,mask,{},[{'id':'TEST_ONLY'}],'TEST ONLY','degC')
    assert result['legend']['minimum']==pytest.approx(10.8)
    assert result['legend']['maximum']==pytest.approx(49.2)
    assert result['legend']['unit']=='degC'
    assert captured['rgba'][0,0,:3].tolist()==[0,190,200]
    assert captured['rgba'][1,1,:3].tolist()==[230,40,0]
    assert captured['rgba'][1,2,3]==0
    assert np.array_equal(values,before)

def test_constant_and_absent_data_do_not_invent_color_ranges(monkeypatch):
    monkeypatch.setattr(product_processing,'map_preview',lambda *a:{})
    constant=product_processing.display(np.ones((2,2)),np.ones((2,2),dtype=bool),{},[],'TEST ONLY')
    assert constant['legend']['minimum']==constant['legend']['maximum']==1
    assert constant['legend']['low_color']==constant['legend']['high_color']
    absent=product_processing.display(np.ones((2,2)),np.zeros((2,2),dtype=bool),{},[],'TEST ONLY')
    assert absent['legend'] is None
