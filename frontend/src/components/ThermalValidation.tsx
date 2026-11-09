import {asObject} from '@/lib/researchRecord';
export default function ThermalValidation({value}:{value:unknown}){
 const v=asObject(value);if(!Object.keys(v).length)return null;
 const n=(x:unknown)=>typeof x==='number'&&Number.isFinite(x)?x.toFixed(3):'미검증';
 const rows=[['ML',v.model],['참조일 그대로 복사',v.copy],['평균 대신 중앙값 차이 보정 복사',v.bias_corrected_copy]] as const;
 return <section aria-label="ML 공간 검증 결과"><h4>ML 검증 · {v.status==='passed'?'통과':'보류'}</h4>
 <p>공간 보류 RMSE <strong>{n(asObject(v.model).rmse_k)} K</strong> · 구름 아래 참값 정확도는 미검증</p>
 <details className="collection-help"><summary>검증 방법·기준선 비교</summary>
 <p>맑은 관측을 공간 4구역으로 나누고 120m 완충 구간을 두어 검증했습니다. 구름 아래 실제 정확도를 측정한 값은 아닙니다.</p>
 <p>공간 간격 학습·검증 표본: {typeof v.sampled_pairs==='number'?v.sampled_pairs:'미확인'}개. 30m 출력 셀을 독립적인 30m 열관측으로 간주하지 않습니다.</p>
 <table><thead><tr><th>방법</th><th>RMSE (K)</th><th>MAE (K)</th><th>절대오차 95백분위 (K)</th></tr></thead><tbody>{rows.map(([name,row])=>{const m=asObject(row);return <tr key={name}><th>{name}</th><td>{n(m.rmse_k)}</td><td>{n(m.mae_k)}</td><td>{n(m.p95_k)}</td></tr>;})}</tbody></table>
 <p>통과 기준: 전체와 각 구역 RMSE ≤2K·MAE ≤1.5K·95백분위 ≤4K, 전체 RMSE가 단순 복사보다 10%, 편향 보정 복사보다 5% 이상 개선. 앱의 운영 기준이며 보편적 정확도 보장은 아닙니다.</p>
 <details><summary>구역별 검증·모델 기록</summary><pre>{JSON.stringify(v,null,2)}</pre></details></details></section>;
}
