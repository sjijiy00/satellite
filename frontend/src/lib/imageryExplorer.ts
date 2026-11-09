import {sceneKey,type Scene} from './types';

/** Pure view model for already searched STAC Items; it never issues a new query. */
export function sceneDay(scene:Scene):string|null {
  const value=scene.datetime;
  if(!value||!Number.isFinite(Date.parse(value)))return null;
  return new Date(value).toISOString().slice(0,10);
}

export function withinPeriod(scene:Scene,start:string,end:string):boolean {
  const day=sceneDay(scene);
  return day!==null&&day>=start&&day<=end;
}

export interface DayGroup {day:string;count:number;keys:string[];cloudKnown:number;cloudUnknown:number}

export function groupScenesByDay(items:Scene[],start:string,end:string):{days:DayGroup[];included:Scene[];outside:number;unknownDate:number}{
  const groups=new Map<string,DayGroup>(),included:Scene[]=[];
  let outside=0,unknownDate=0;
  for(const scene of items){
    const day=sceneDay(scene);
    if(day===null){unknownDate++;continue;}
    if(day<start||day>end){outside++;continue;}
    included.push(scene);
    const group=groups.get(day)||{day,count:0,keys:[],cloudKnown:0,cloudUnknown:0};
    group.count++;group.keys.push(sceneKey(scene));
    if(scene.scene_cloud_cover===null)group.cloudUnknown++;else group.cloudKnown++;
    groups.set(day,group);
  }
  return {days:[...groups.values()].sort((a,b)=>a.day.localeCompare(b.day)),included,outside,unknownDate};
}

export function firstOnDay(items:Scene[],day:string,current:string|null):string|null {
  const candidates=items.filter(scene=>sceneDay(scene)===day);
  return candidates.find(scene=>sceneKey(scene)===current)?current:candidates[0]?sceneKey(candidates[0]):null;
}
