import type {MapPreview} from '@/lib/types';
export default function RasterLegend({layer}:{layer:MapPreview}){
 const scale=layer.legend;
 if(!scale)return null;
 const unit=scale.unit==='degC'?'℃':scale.unit==='1'?'(무차원)':scale.unit;
 const n=(v:number)=>v.toLocaleString('ko-KR',{maximumFractionDigits:3});
 return <div className="raster-scale" role="group" aria-label="미리보기 색상 범위">
  <div aria-hidden="true" style={{height:8,background:`linear-gradient(to right, ${scale.low_color}, ${scale.high_color})`}}/>
  <p>{scale.minimum===scale.maximum?`단일 색상 기준값 ${n(scale.minimum)} ${unit}`:`낮음 ${n(scale.minimum)} → 높음 ${n(scale.maximum)} ${unit}`} · 유효 픽셀 {scale.percentiles.join('–')}백분위</p>
  <small>영상마다 색상 범위를 자동 조정합니다. 서로 다른 지도의 같은 색이 같은 값은 아닙니다. 양끝 밖의 값은 끝 색으로 표시하며 원본 수치는 자르지 않습니다. 투명 영역은 유효값 없음입니다.</small>
 </div>;
}
