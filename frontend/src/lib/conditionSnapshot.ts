import type {ConditionProposals} from './types';
export type ConditionPhase='idle'|'loading'|'ready'|'failed'|'interrupted';
export interface ConditionSnapshot {version:1;sentence:string;phase:ConditionPhase;proposal:ConditionProposals|null;error:string;manual:boolean;ack:string}
export function readConditionSnapshot(value:unknown,sentence:string):ConditionSnapshot|null{
 if(!value||typeof value!=='object')return null;
 const v=value as ConditionSnapshot;
 if(v.version!==1||v.sentence!==sentence.trim()||!['idle','loading','ready','failed','interrupted'].includes(v.phase)||typeof v.manual!=='boolean'||typeof v.error!=='string'||typeof v.ack!=='string'||!('proposal' in v))return null;
 const p=v.proposal;
 if(p&&(!['success','partial','failed'].includes(p.status)||p.engine?.mode!=='ai'||!p.period||!p.region||!Array.isArray(p.messages)||!p.messages.every(m=>typeof m==='string')||p.fields!=null&&(typeof p.fields!=='object'||Object.values(p.fields).some(f=>!f||!['explicit','inferred','unspecified'].includes(f.basis)))||p.region.candidates!=null&&!Array.isArray(p.region.candidates)||p.extraction?.places!=null&&!Array.isArray(p.extraction.places)))return null;
 return v;
}
