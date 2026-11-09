'use client';
import {createContext,useContext} from 'react';
import {sceneKey,type Scene,type CloudJob,type EstimateJob} from './types';
export type Acquisition={status:'receiving'|'received'|'failed';bytes?:number;at:number};
export type Acquisitions=Record<string,Record<string,Acquisition>>;
export type SavedJob={kind:'cloud'|'estimate';context:string;job:CloudJob|EstimateJob};
export interface WorkSession {
 analysis:{id:string|null;label:string|null;confirmed:boolean;metadataReady:boolean;engine:string|null};
 stage:'quality'|'preprocess'|'analysis';setStage:(stage:WorkSession['stage'])=>void;
 settings:Record<string,unknown>;setSettings:(values:Record<string,unknown>)=>void;
 requestOriginal:()=>void;
 canSearchPcLandsat:boolean;searchPcLandsat:()=>void;
 context:string;bands:Record<string,string[]>;acquisitions:Acquisitions;linksSaved:Record<string,number>;jobs:SavedJob[];
 setBands:(id:string,keys:string[])=>void;
 recordAsset:(scene:Scene,key:string,value:Acquisition)=>void;recordLinks:(scene:Scene)=>void;
 recordJob:(kind:'cloud'|'estimate',job:CloudJob|EstimateJob,context?:string)=>void;
 canProcess:(scenes:Scene[],required?:string[])=>boolean;
}
export const WorkContext=createContext<WorkSession|null>(null);
export const useWorkSession=()=>useContext(WorkContext);
export function selectedBands(scene:Scene,bands:WorkSession['bands']){return bands[sceneKey(scene)]??scene.purpose_plan?.default_keys??[];}
export function acquired(scenes:Scene[],bands:WorkSession['bands'],assets:Acquisitions,required?:string[]){
 return scenes.length>0&&scenes.every(scene=>{
  const keys=selectedBands(scene,bands),needed=required??scene.purpose_plan?.analysis_keys??[];
  return keys.length>0&&needed.every(key=>keys.includes(key))&&keys.every(key=>
   scene.download_assets?.some(a=>a.key===key)&&assets[sceneKey(scene)]?.[key]?.status==='received');
 });
}
