// TEST ONLY AI/Kakao transports. Boundary bbox comes from reviewed official metadata.
import {readFileSync} from 'node:fs';
import {resolve} from 'node:path';
import type {Page} from './runtime';
import type {ConditionProposals} from '../src/lib/types';
export const usage={requests:1,succeeded:1,failed:0,cancelled:0,cache_hits:0,input_tokens:100,output_tokens:100,unknown_usage_calls:0,last_status:'succeeded'};
export const seoulMeta=JSON.parse(readFileSync(resolve(__dirname,'../../backend/app/data/boundaries/seoul-sgis-2025-q2.metadata.json'),'utf8'));
export const jejuMeta=JSON.parse(readFileSync(resolve(__dirname,'../../backend/app/data/boundaries/jeju-sgis-2025-q2.metadata.json'),'utf8'));
export function region(jeju=false){
 const m=jeju?jejuMeta:seoulMeta,b=m.bbox;
 return {status:'resolved',id:jeju?'TEST_ONLY_JEJU':'TEST_ONLY_SEOUL',name:m.name,official_name:m.name,parent:'대한민국',admin_level:'시·도',center:jeju?[126.53,33.49]:[126.978,37.5665],role:'camera_only',source:'TEST ONLY Kakao 응답',checked_at:'2026-11-02T00:00:00Z',
  boundary:{...m,status:'proposed',message:'TEST ONLY 경계 transport; bbox는 공식 자료 메타데이터',geometry:{type:'Polygon',coordinates:[[[b[0],b[1]],[b[2],b[1]],[b[2],b[3]],[b[0],b[3]],[b[0],b[1]]]]},pixel_area_exceeded:true,polygon_clipping:false}};
}
export function interpretation(place='제주도',start='2025-08-15',end='2025-08-30'):{condition_proposals:ConditionProposals}{
 const explicit=(value:string|number|null,evidence:string|null)=>({value,evidence,basis:value===null?'unspecified' as const:'explicit' as const});
 return {condition_proposals:{status:'success',messages:[],event_reference_required:false,scope:'TEST ONLY AI response',engine:{mode:'ai',status:'succeeded',provider:'openai',model:'TEST_ONLY_MODEL',usage},
  fields:{purpose_type:explicit('thermal','지표면 온도'),analysis_target:explicit('지표면 온도','지표면 온도'),temporal_mode:explicit(null,null),observation_need:explicit(null,null),resolution_m:explicit(null,null),target_size_m:explicit(null,null),max_cloud_cover:explicit(null,null),reference_date:explicit(null,null)},
  extraction:{purpose_type:'thermal',analysis_target:'지표면 온도',temporal_mode:'unspecified',places:[{text:place,ambiguous:false,basis:'explicit',kind:'administrative',spatial_scope:'boundary',radius_m:null}]},period:{status:'resolved',start,end,timezone:'UTC'},region:{status:'lookup_required',mentioned_text:place}}};
}
export async function configs(page:Page){
 await page.route('**/api/request/config',r=>r.fulfill({json:{ready:true,provider:'openai',model:'TEST_ONLY_MODEL',message:'TEST ONLY 설정',usage,limits:{timeout_seconds:12,requests_per_minute:6,requests_per_process:100}}}));
 await page.route('**/api/places/config',r=>r.fulfill({json:{ready:true,provider:'kakao',missing_settings:[],message:'TEST ONLY 준비됨'}}));
}
export async function input(page:Page,text='2025년 8/15~8/30까지 제주도의 지표면 온도를 알고 싶어'){
 // Wait for the client configuration effect before interacting with server-rendered
 // inputs. A dev-server cold compilation can otherwise precede React hydration.
 await page.waitForFunction(()=>document.querySelector('[data-testid="automatic-conditions"]')?.getAttribute('data-config-ready')==='true');
 const switcher=page.getByRole('button',{name:'자연어 입력으로 전환',exact:true});if(await switcher.isVisible())await switcher.click();
 await page.getByLabel('분석 목적',{exact:true}).fill(text);await page.getByLabel('분석 목적',{exact:true}).blur();
}
export const map=(page:Page)=>page.getByRole('region',{name:'관심 지역 지도',exact:true});
export async function chooseLocation(page:Page,name='제주특별자치도'){
 const {expect}=await import('@playwright/test');await page.getByRole('button',{name,exact:true}).click();await expect(page.getByLabel('분석 장소',{exact:true})).toHaveValue(name);
}
export async function coordinates(page:Page,b:number[]){
 for(const [i,label] of ['서쪽 경도','남쪽 위도','동쪽 경도','북쪽 위도'].entries())await page.getByLabel(label,{exact:true}).fill(String(b[i]));
 await page.getByRole('button',{name:'좌표 적용',exact:true}).click();
}
