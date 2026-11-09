"""Post-execution evidence only; never a proposed preprocessing checklist."""
from datetime import datetime, timezone


def completed_record(manifest, files):
    """Called only after every written raster has been reopened and checked."""
    request = manifest.get('input', {})
    method = request.get('method_id')
    report = manifest.get('record', {})
    inputs = [{k: scene.get(k) for k in ('provider_id', 'collection', 'id', 'asset_keys')}
              for scene in request.get('scenes', [])]
    def row(identifier, label, detail, status='completed'):
        return {'id': identifier, 'label': label, 'status': status, 'detail': detail}
    rows = [row('source', '서버 원본 범위 읽기',
                'canonical Item의 실제 Asset 헤더·픽셀을 읽었습니다. 브라우저 TIFF·미리보기는 처리 입력이 아닙니다.'),
            row('grid', 'AOI·공통 격자', '실제 출력 격자는 grid에 기록됩니다. bbox는 행정경계 클리핑과 다릅니다.'),
            row('qa', '품질·NoData 마스킹', '실제 유효/제외 마스크를 생성했습니다. 제외는 가려진 지표의 복원이 아닙니다.')]
    radiometry = [r for s in report.get('scenes', []) for r in s.get('radiometry', [])]
    if radiometry and all(r.get('status') in ('confirmed_metadata','confirmed_documented_metadata') for r in radiometry):
        rows.append(row('calibration', '제품 scale/offset 적용',
                        '제품별 검증된 보정값을 한 번 적용했습니다. 값·근거는 record.scenes.radiometry에 있습니다.'))
    else:
        rows.append(row('calibration', '제품 보정 기록',
                        '이 엔진의 상세 보정 근거는 기존 engine_record/처리 기록을 확인하세요. 독립 대기 보정을 실행했다는 뜻이 아닙니다.', 'not_recorded'))
    rows.append(row('resampling', '격자 정렬·재표본화', str(manifest.get('resampling', {}))))
    rows.append(row('compute', '실제 계산', method or '카탈로그 방법'))
    rows.append(row('composite', '다른 날짜의 실제 관측 선택',
                    '입력 날짜·출처는 source_date/engine_record를 확인하세요.' if method in ('observed_composite','thermal_gapfill') else '이번 작업은 관측 합성을 실행하지 않았습니다.',
                    'completed' if method in ('observed_composite','thermal_gapfill') else 'skipped'))
    rows.append(row('estimate', 'ML 추정 · 원관측 아님',
                    '추정/관측/미해결 마스크와 보류 검증은 engine_record에 보존됩니다. 구름 아래 참값의 검증이 아닙니다.' if method in ('local_ridge','thermal_ml') else '이번 작업은 ML 추정을 실행하지 않았습니다.',
                    'completed' if method in ('local_ridge','thermal_ml') else 'skipped'))
    rows.append(row('files', '파일 저장·재열기 검증',
                    '실제 저장 파일의 CRS·transform·NoData·크기·밴드·해시를 검사했습니다. GIS GUI 검증이나 브라우저 저장 완료와 별개입니다.'))
    for row_input,scene in zip(inputs,report.get('scenes',[])):row_input['datetime']=scene.get('datetime')
    return {'version': 'execution-record-1', 'recorded_at': datetime.now(timezone.utc).isoformat(),
            'source_mode': 'canonical_server_range', 'inputs': inputs,
            'outputs': list(files), 'grid': manifest.get('grid'), 'steps': rows}
