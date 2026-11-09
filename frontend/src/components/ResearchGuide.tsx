import type {ProcessingMethod} from '@/lib/types';
import {landsatResearchSources} from '@/lib/researchRecord';
export default function ResearchGuide({method}:{method:ProcessingMethod}){
 return <section aria-label="연구 해석과 방법 기록" className="research-guide">
  <details><summary>연구 해석·방법 기록 안내</summary>
  <details><summary>이 결과로 연구 질문에 어디까지 답할 수 있나요?</summary>
   <p>QA를 통과한 관측 영역의 결과입니다. 결측 지역까지 포함한 전체 지역의 참값이나 변화 원인을 확정하지 않습니다. 유효율과 제외된 위치를 함께 확인하고 다른 촬영일을 골랐다면 그 선택 근거를 연구 방법에 남기세요.</p>
   <p>처리 성공은 연구 타당성 검증과 별개입니다. 연구 목적에 맞는 독립 자료·현장 관측과 대조하고, 기준을 바꾼 결과는 같은 조건의 결과와 구분하세요.</p>
  </details>
  {method.inputs?.thermal_qa&&<>
   <details><summary>2K·1km는 논문에 그대로 써도 되는 기준인가요?</summary>
    <p>앱의 초기 운영값이며 USGS가 모든 연구에 요구하는 통과 기준이 아닙니다. ST_QA의 픽셀 불확실성과 구름 거리로 관측을 거르는 조건입니다. 2K를 지역 평균의 ±2℃ 신뢰구간이나 실제 오차 보장으로 해석하지 마세요.</p>
    <p>연구에서 채택한 값과 이유를 기록하고, 기준 변화에 따라 유효 면적과 통계가 어떻게 달라지는지 별도 실행으로 비교하세요. 이 앱은 온도 기준 민감도나 지역 평균의 신뢰구간을 자동 계산하지 않습니다.</p>
   </details>
   <details><summary>출력 30m·온도 지도는 무엇을 의미하나요?</summary><p>지표면 온도는 기온이 아닙니다. Landsat 8/9 열관측은 100m이며 30m 제품 격자로 제공됩니다. 30m 셀이나 여러 타일을 독립적인 30m 열관측 표본으로 세면 안 됩니다. 처리 타일 수는 촬영 횟수도 아닙니다.</p></details>
   <details><summary>논문 자료 출처와 방법은 어떻게 남기나요?</summary><ul>{landsatResearchSources.map(s=><li key={s.url}><a href={s.url} target="_blank" rel="noreferrer">{s.title}</a></li>)}</ul><p>데이터셋 인용에 사용 장면 ID·UTC 촬영일·AOI·QA·계산 방법을 함께 기록하세요. 처리 후 아래 연구 기록 JSON을 저장하고, 성공했다면 GeoTIFF·manifest ZIP도 보관하세요. 연구 기록은 원본 픽셀이나 완성된 논문 방법 절을 대신하지 않습니다.</p></details>
  </>}
 </details></section>;
}
