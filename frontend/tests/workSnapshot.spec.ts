import {test,expect} from './runtime';
import {safeMetadata} from '../src/lib/workSnapshot';
test('TEST ONLY 작업 메타데이터는 비밀·서명 URL·실행 확인·바이너리를 보관하지 않음',()=>{
 const result=safeMetadata({password:'TEST_ONLY_PASSWORD',refresh_token:'TEST_ONLY_REFRESH',authorization:'Bearer TEST_ONLY',cookie:'TEST_ONLY_COOKIE',
  item:{id:'TEST_ONLY_SCENE',href:'https://example.test/data.tif?unknown-signature=TEST_ONLY_SIGNATURE',source_url:'https://example.test/public'},
  plan_id:'TEST_ONLY_PLAN',confirmation_digest:'TEST_ONLY_CONFIRM',artifact_base64:'TEST_ONLY_BYTES',png_base64:'TEST_ONLY_PIXELS',
  download_url:'/api/media/downloads/TEST_ONLY_RECEIPT',notes:'error https://example.test/a?other=TEST_ONLY_QUERY',job_id:'a'.repeat(32)});
 const text=JSON.stringify(result);
 for(const forbidden of ['TEST_ONLY_PASSWORD','TEST_ONLY_REFRESH','TEST_ONLY_COOKIE','TEST_ONLY_SIGNATURE','TEST_ONLY_CONFIRM','TEST_ONLY_BYTES','TEST_ONLY_PIXELS','TEST_ONLY_RECEIPT','TEST_ONLY_QUERY'])expect(text).not.toContain(forbidden);
 expect(text).toContain('TEST_ONLY_SCENE');expect(text).toContain('https://example.test/public');expect(text).toContain('a'.repeat(32));
});
test('TEST ONLY 브라우저 보관 상한·유효하지 않은 숫자·프로토타입 키 제한',()=>{
 const result=safeMetadata(JSON.parse('{"__proto__":{"injected":true},"constructor":"TEST_ONLY","numbers":[1,null],"long":"'+ 'x'.repeat(9000)+'"}')) as Record<string,unknown>;
 expect(Object.hasOwn(result,'__proto__')).toBe(false);expect(Object.hasOwn(result,'constructor')).toBe(false);expect(result.long).toBe('');
 expect(safeMetadata(Infinity)).toBeNull();expect((safeMetadata(Array(500).fill(1)) as unknown[]).length).toBe(200);
});
test('TEST ONLY 행정경계 링은 일반 배열 상한으로 잘라 잘못 복원하지 않음',()=>{
 const ring=Array.from({length:350},(_,i)=>[126+Math.cos(i/349*2*Math.PI)*.1,36+Math.sin(i/349*2*Math.PI)*.1]);ring.push(ring[0]);
 const result=safeMetadata({geometry:{type:'Polygon',coordinates:[ring]}}) as {geometry:{coordinates:number[][][]}};
 expect(result.geometry.coordinates[0]).toHaveLength(351);expect(result.geometry.coordinates[0].at(-1)).toEqual(ring[0]);
});
