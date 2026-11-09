"""USGS L2SP ST, not brightness temperature or a second atmospheric correction."""
import numpy as np

def pixel_quality(qa,radsat):
    # Exclude fill, dilated cloud, high cirrus/cloud/shadow, snow. Water is not
    # excluded. Also reject medium/high confidence cloud/shadow/snow/cirrus and
    # any saturation/terrain-occlusion flag, conservatively for both OLI/TIRS.
    return ((qa&63)==0)&(radsat==0)&(((qa>>8)&3)<2)&(((qa>>10)&3)<2)&(((qa>>12)&3)<2)&(((qa>>14)&3)<2)

def kelvin_celsius(dn):
    # Called on raw integer DN exactly once, before continuous resampling.
    k=dn.astype('float64')*.00341802+149.
    return k,k-273.15

def thermal_valid(uncertainty_k,cloud_distance_km,options):
    return np.isfinite(uncertainty_k)&np.isfinite(cloud_distance_km)&(uncertainty_k>=0)&(uncertainty_k<=options['maximum_uncertainty_k'])&(cloud_distance_km>=options['minimum_cloud_distance_km'])
