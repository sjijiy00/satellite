'use client';
import {sceneKey} from '@/lib/types';
import {useEffect, useRef, useState} from 'react';
import * as maplibregl from 'maplibre-gl';
import type {GeoJSONSource, Map as MapType} from 'maplibre-gl';
import type {FeatureCollection} from 'geojson';
import type {Bbox, Scene, MapPreview, CameraLocation, BoundaryProposal} from '@/lib/types';
import {sceneDay} from '@/lib/imageryExplorer';
import RasterLegend from './RasterLegend';

export function rectangle(b: Bbox): FeatureCollection {
  return {type: 'FeatureCollection', features: [{type: 'Feature', properties: {}, geometry: {type: 'Polygon', coordinates: [[[b[0],b[1]],[b[2],b[1]],[b[2],b[3]],[b[0],b[3]],[b[0],b[1]]]]}}]};
}
const empty: FeatureCollection = {type:'FeatureCollection',features:[]};

export default function MapPanel({boundaryProposal=null,confirmedBoundary=null,camera,onManualCamera,aoiConfirmed,onConfirmAoi,bbox, onBbox, scenes, selected, onSelect, activeDay, showFootprints, pair=['',''], qualityOverlay, analysisOverlay, observedEstimateOverlay, estimatedOverlay, moveAoiToken}: {boundaryProposal?:BoundaryProposal|null;confirmedBoundary?:BoundaryProposal|null;camera:CameraLocation|null;onManualCamera:()=>void;aoiConfirmed:boolean;onConfirmAoi:()=>void;bbox: Bbox | null; onBbox: (b: Bbox) => void; scenes: Scene[]; selected: string | null; onSelect: (id: string) => void; activeDay:string|null; showFootprints:boolean; pair:[string,string];qualityOverlay:MapPreview|null;analysisOverlay:MapPreview|null;observedEstimateOverlay:MapPreview|null;estimatedOverlay:MapPreview|null;moveAoiToken:number}) {
  const container = useRef<HTMLDivElement>(null), map = useRef<MapType | null>(null);
  const selecting = useRef(false), anchor = useRef<[number,number] | null>(null);
  const corners=useRef<maplibregl.Marker[]>([]);
  const handlers = useRef({onBbox, onSelect,onManualCamera}); handlers.current = {onBbox,onSelect,onManualCamera};
  const [cameraCenter,setCameraCenter]=useState<number[]|null>(null);
  const [drawing,setDrawing] = useState(false), [ready,setReady] = useState(false), [error,setError] = useState('');
  const bboxKey=JSON.stringify(bbox);
  useEffect(() => {
    if (!container.current) return;
    setReady(false);
    let m: MapType;
    try {
      maplibregl.setWorkerUrl('/maplibre/maplibre-gl-worker.mjs');
      m = new maplibregl.Map({container:container.current, center:[126.9,36.5], zoom:6.6, renderWorldCopies:false,
        style:{version:8, sources:{osm:{type:'raster',tiles:['https://tile.openstreetmap.org/{z}/{x}/{y}.png'],tileSize:256,attribution:'© <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a>'}},layers:[{id:'base',type:'raster',source:'osm',paint:{'raster-saturation':-0.65,'raster-opacity':0.8}}]}});
    } catch (cause) { console.error('Map initialization failed',cause); setError('지도를 초기화하지 못했습니다. WebGL을 지원하는 브라우저를 사용하거나 좌표로 영역을 입력하세요.'); return; }
    map.current=m;
    m.addControl(new maplibregl.NavigationControl(),'top-right');
    m.on('movestart',event=>{if(event.originalEvent)handlers.current.onManualCamera();});
    m.on('moveend',()=>{const c=m.getCenter();setCameraCenter([Number(c.lng.toFixed(6)),Number(c.lat.toFixed(6))]);});
    m.on('error', () => setError('일부 지도 타일을 불러오지 못했습니다. 네트워크를 확인하세요. 좌표 입력과 검색은 계속 사용할 수 있습니다.'));
    m.on('load', () => {
      for (const name of ['footprints','aoi','draft','boundary-proposal','boundary-confirmed']) m.addSource(name,{type:'geojson',data:empty});
      for(const name of ['boundary-proposal','boundary-confirmed']){
        m.addLayer({id:name+'-fill',type:'fill',source:name,paint:{'fill-color':name==='boundary-proposal'?'#d97706':'#2563eb','fill-opacity':0.05}});
        m.addLayer({id:name+'-line',type:'line',source:name,paint:{'line-color':name==='boundary-proposal'?'#d97706':'#2563eb','line-width':3,'line-dasharray':name==='boundary-proposal'?[4,3]:[1,0]}});
      }
      m.addLayer({id:'footprints-fill',type:'fill',source:'footprints',paint:{'fill-color':['case',['==',['get','selected'],true],'#f59e0b','#0284c7'],'fill-opacity':['case',['==',['get','selected'],true],0.18,0.025]}});
      m.addLayer({id:'footprints-line',type:'line',source:'footprints',paint:{'line-color':['case',['==',['get','selected'],true],'#d97706',['==',['get','pair'],1],'#7c3aed',['==',['get','pair'],2],'#db2777','#0284c7'],'line-opacity':['case',['==',['get','active'],true],0.95,0.28],'line-width':['case',['==',['get','selected'],true],4,['>', ['get','pair'],0],3,1]}});
      for (const name of ['aoi','draft']) {
        m.addLayer({id:`${name}-fill`,type:'fill',source:name,paint:{'fill-color':'#0d9488','fill-opacity':0.12}});
        m.addLayer({id:`${name}-line`,type:'line',source:name,paint:{'line-color':'#0f766e','line-width':2,'line-dasharray':name==='draft'?[2,2]:[1,0]}});
      }
      setReady(true);
    });
    m.on('click', (event) => {
      if (!selecting.current) {
        const feature = m.getLayer('footprints-fill') && m.queryRenderedFeatures(event.point,{layers:['footprints-fill']})[0];
        if (feature?.properties?.id) handlers.current.onSelect(feature.properties.id);
        return;
      }
      const point: [number,number]=[event.lngLat.lng,event.lngLat.lat];
      if (!anchor.current) { anchor.current=point; return; }
      const a=anchor.current;
      const bounds: Bbox=[Math.min(a[0],point[0]),Math.min(a[1],point[1]),Math.max(a[0],point[0]),Math.max(a[1],point[1])];
      if (bounds[0]===bounds[2] || bounds[1]===bounds[3]) return;
      handlers.current.onBbox(bounds.map(v=>Number(v.toFixed(6))) as Bbox);
      anchor.current=null; selecting.current=false; setDrawing(false); m.getCanvas().style.cursor='';
      (m.getSource('draft') as GeoJSONSource)?.setData(empty);
    });
    m.on('mousemove', event=>{
      if (!selecting.current || !anchor.current) return;
      const a=anchor.current;
      (m.getSource('draft') as GeoJSONSource)?.setData(rectangle([Math.min(a[0],event.lngLat.lng),Math.min(a[1],event.lngLat.lat),Math.max(a[0],event.lngLat.lng),Math.max(a[1],event.lngLat.lat)]));
    });
    const resize=new ResizeObserver(()=>m.resize());resize.observe(container.current);
    return ()=>{resize.disconnect();for(const marker of corners.current)marker.remove();corners.current=[];m.remove(); map.current=null;};
  },[]);
  useEffect(()=>{if(ready && map.current){(map.current.getSource('aoi') as GeoJSONSource | undefined)?.setData(bbox?rectangle(bbox):empty);if(bbox)map.current.fitBounds([[bbox[0],bbox[1]],[bbox[2],bbox[3]]],{padding:70,maxZoom:13});}},[bboxKey,ready]);
  useEffect(()=>{if(ready&&map.current?.getLayer('aoi-line'))map.current.setPaintProperty('aoi-line','line-dasharray',aoiConfirmed?[1,0]:[2,2]);},[ready,aoiConfirmed]);
  useEffect(()=>{
    for(const marker of corners.current)marker.remove();corners.current=[];
    if(!ready||!map.current||!bbox||drawing)return;
    const points:[[number,number],[number,number],[number,number],[number,number]]=[[bbox[0],bbox[1]],[bbox[2],bbox[1]],[bbox[2],bbox[3]],[bbox[0],bbox[3]]];
    for(let i=0;i<4;i++){
      const element=document.createElement('button');element.type='button';element.className='aoi-corner';element.setAttribute('aria-label','AOI 꼭짓점 '+(i+1)+' 드래그');
      const marker=new maplibregl.Marker({element,draggable:true}).setLngLat(points[i]).addTo(map.current);
      marker.on('dragstart',()=>handlers.current.onManualCamera());
      marker.on('dragend',()=>{const moved=marker.getLngLat(),opposite=points[(i+2)%4];const b:Bbox=[Math.min(moved.lng,opposite[0]),Math.min(moved.lat,opposite[1]),Math.max(moved.lng,opposite[0]),Math.max(moved.lat,opposite[1])];if(b.every(Number.isFinite)&&b[0]<b[2]&&b[1]<b[3]&&b[2]-b[0]<=5&&b[3]-b[1]<=5)handlers.current.onBbox(b.map(v=>Number(v.toFixed(7))) as Bbox);});
      corners.current.push(marker);
    }
    return()=>{for(const marker of corners.current)marker.remove();corners.current=[];};
  },[bboxKey,ready,drawing]);
  useEffect(()=>{if(!ready||!map.current)return;for(const [name,b] of [['boundary-proposal',boundaryProposal?.id===confirmedBoundary?.id?null:boundaryProposal],['boundary-confirmed',confirmedBoundary]] as const)(map.current.getSource(name) as GeoJSONSource|undefined)?.setData(b?.geometry?{type:'FeatureCollection',features:[{type:'Feature',properties:{name:b.name},geometry:b.geometry}]}:empty);},[boundaryProposal,confirmedBoundary,ready]);
  useEffect(()=>{if(ready&&map.current&&camera&&!selecting.current){const b=camera.view_bbox;if(b)map.current.fitBounds([[b[0],b[1]],[b[2],b[3]]],{padding:60,maxZoom:11,duration:500});else if(camera.center)map.current.flyTo({center:camera.center,zoom:9,duration:500});}},[camera,ready]);
  useEffect(()=>{if(moveAoiToken && bbox && ready && map.current)map.current.fitBounds([[bbox[0],bbox[1]],[bbox[2],bbox[3]]],{padding:70,maxZoom:13});},[moveAoiToken,bbox,ready]);
  useEffect(()=>{
    if (!ready || !map.current) return;
    const features= showFootprints?scenes.filter(s=>s.geometry).map(s=>({type:'Feature' as const, properties:{id:sceneKey(s),selected:sceneKey(s)===selected,active:activeDay===null||sceneDay(s)===activeDay,pair:sceneKey(s)===pair[0]?1:sceneKey(s)===pair[1]?2:0},geometry:s.geometry!})):[];
    (map.current.getSource('footprints') as GeoJSONSource | undefined)?.setData({type:'FeatureCollection',features});
  },[scenes,selected,ready,activeDay,showFootprints,pair]);
  useEffect(()=>{
    if(!ready||!map.current)return;
    const m=map.current;
    for(const [name,overlay] of [['quality',qualityOverlay],['analysis',analysisOverlay],['observed-estimate',observedEstimateOverlay],['estimated',estimatedOverlay]] as const){
      const id=`${name}-actual-raster`;
      if(m.getLayer(id))m.removeLayer(id);
      if(m.getSource(id))m.removeSource(id);
      if(overlay){
        m.addSource(id,{type:'image',url:`data:image/png;base64,${overlay.png_base64}`,coordinates:overlay.coordinates});
        m.addLayer({id,type:'raster',source:id,paint:{'raster-opacity':0.72}},'footprints-fill');
      }
    }
  },[ready,qualityOverlay,analysisOverlay,observedEstimateOverlay,estimatedOverlay]);
  function toggleDrawing() {
    handlers.current.onManualCamera();map.current?.stop();
    selecting.current=!drawing; anchor.current=null; setDrawing(!drawing);
    if(map.current) { map.current.getCanvas().style.cursor=!drawing?'crosshair':''; (map.current.getSource('draft') as GeoJSONSource)?.setData(empty); }
  }
  return <section className="map-panel" aria-label="관심 지역 지도" data-aoi-bbox={JSON.stringify(bbox)} data-camera-place={camera?.id||""} data-camera-center={JSON.stringify(cameraCenter)} data-aoi-confirmed={String(aoiConfirmed)} data-aoi-feature-count={bbox?1:0} data-boundary-proposal={boundaryProposal?.id||''} data-boundary-confirmed={confirmedBoundary?.id||''}>
    <div ref={container} className="map-canvas" data-testid="map" />
    <div className="map-tools"><button type="button" onClick={toggleDrawing} disabled={!ready}>{drawing?'선택 취소':'▧ 영역 선택'}</button><button type="button" disabled={!bbox || !ready} onClick={()=>bbox && map.current?.fitBounds([[bbox[0],bbox[1]],[bbox[2],bbox[3]]],{padding:70})}>선택 영역으로 이동</button>{bbox&&!aoiConfirmed&&<button type="button" onClick={onConfirmAoi}>분석 AOI 확정</button>}</div>
    <div className="map-caption">{drawing?'지도의 대각선 두 꼭짓점을 차례로 클릭하세요.':'분석할 영역을 지도에서 선택하거나 좌표로 지정하세요. 지도 이동만으로 AOI는 바뀌지 않습니다.'}</div>
    <span className="map-state" data-testid="map-selected-scene">{selected||'미선택'}</span>
    {(boundaryProposal||confirmedBoundary)&&<div className="boundary-map-note">주황 점선: 미확정 경계 제안 · 파란 실선: 적용한 경계 참고 · 녹색 사각형: 실제 bbox 검색 범위. 폴리곤 클리핑 미지원.</div>}
    <div className="map-legend"><span className="aoi-dot"/> 관심 지역 <span className="scene-dot"/> 촬영 범위 <span className="selected-dot"/> 선택 영상 <span data-testid="footprint-count">{showFootprints?scenes.filter(s=>s.geometry).length:0}개 범위</span>{pair[0]&&pair[1]&&<span>보라·분홍: 비교 영상 1·2</span>}{qualityOverlay&&<span>초록·주황: 실제 유효·제외 마스크</span>}{analysisOverlay&&<span>{analysisOverlay.label}</span>}{observedEstimateOverlay&&<span>실측 픽셀 거짓색 미리보기</span>}{estimatedOverlay&&<span>ML 추정 픽셀 거짓색 미리보기 · 관측 아님</span>}</div>
    {analysisOverlay?.legend&&<div className="analysis-map-scale"><RasterLegend layer={analysisOverlay}/></div>}
    {error && <p role="status" className="map-error">{error}</p>}
  </section>;
}
