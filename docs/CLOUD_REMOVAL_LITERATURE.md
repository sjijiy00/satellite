# 위성영상 구름 제거·결측 복원의 정확도와 한계: 원저 조사

확인일: 2026-10-29. 이 문서는 Satellite Insight AI의 향후 의사결정을 위한 선별 문헌 조사다. 모든 연구를 포괄한 체계적 문헌고찰은 아니다. 논문·학회 공식 원문을 우선했다.

## 서로 다른 세 문제

1. **구름·그림자 탐지:** 실제 광학 관측에서 가려진 픽셀을 식별하고 제외한다. 탐지 F1/정밀도는 구름 아래 지면 반사도 복원 정확도가 아니다.
2. **실제 관측 합성:** 허용 기간 내 다른 날의 구름 없는 원관측 픽셀을 선택한다. 값은 실제이지만 목표 날짜의 관측값은 아니다. 취득일·원본 장면·남은 결측을 보존해야 한다.
3. **가려진 시점의 광학값 추정:** 시계열·SAR·생성모델로 보이지 않는 픽셀을 예측한다. 사진처럼 자연스러운 결과와 분석량의 정량 정확성은 다르다. 두꺼운 불투명 구름 아래 **동일 시점의 광학 참값**은 직접 관측하기 어렵기 때문에 대부분 인공 가림 또는 다른 날짜 참조로 평가한다. 이는 아래 벤치마크 설계에서 도출한 해석이다.

## 원저·학회 발표

| 분야 | 자료 | 실험과 한계의 핵심 |
|---|---|---|
| 구름 마스크 | Skakun 외, [CEOS CMIX, *Remote Sensing of Environment* 2022](https://elib.dlr.de/187708/), DOI `10.1016/j.rse.2022.112990` | Landsat 8/Sentinel-2 구름 탐지 알고리즘 10개를 비교. 두꺼운 구름은 상대적으로 일치하지만 얇고 반투명한 구름은 불확실성이 크며 **참조 라벨 데이터셋에 따라 성능이 달랐다**. 복원 성능 연구가 아니다. |
| 마스크 데이터 | Aybar 외, [CloudSEN12, *Scientific Data* 2022](https://www.nature.com/articles/s41597-022-01878-2), DOI `10.1038/s41597-022-01878-2`; [CloudSEN12+ 2024](https://pmc.ncbi.nlm.nih.gov/articles/PMC11399688/) | 두꺼운/얇은 구름·그림자 라벨을 제공한다. 구름 밑 동일 시점의 맑은 지면 영상은 제공하지 않는다. |
| SAR와 다중 시점 데이터 | Ebel 외, [SEN12MS-CR-TS, *IEEE TGRS* 2022](https://elib.dlr.de/192764/), DOI `10.1109/TGRS.2022.3146246` | Sentinel-1 SAR/2 광학의 여러 시점을 이용한 복원 벤치마크. 정보가 늘지만 센서·날짜 사이 시차와 공간 정합이 홍수·산불 등 빠른 사건의 해석을 제한한다. |
| 추정 불확실성 | Ebel 외, [UnCRtainTS, CVPR Workshops 2023](https://arxiv.org/abs/2304.05464), DOI `10.1109/CVPRW59228.2023.00202` | 광학 시계열 복원과 픽셀별 불확실성 추정을 함께 제안. 불확실성 지도가 참값을 제공하는 것은 아니며, 다른 자료로 옮겼을 때 성능을 따로 검증해야 한다. |
| 시계열 복원 | Stucker 외, [U-TILISE, *IEEE TGRS* 2023](https://arxiv.org/abs/2305.13277), DOI `10.1109/TGRS.2023.3333391` | 자체 시계열 자료에서 개선을 보고했지만, 아래 AllClear의 별도 자료에서는 단순 최저구름 기준선보다 약한 사례가 있다. |
| 대규모 독립 벤치마크 | Zhou 외, [AllClear, NeurIPS Datasets & Benchmarks 2024](https://proceedings.neurips.cc/paper_files/paper/2024/file/60095e1d7ebb292dbba93c4d8f7b2463-Paper-Datasets_and_Benchmarks_Track.pdf), DOI `10.52202/079017-1696` | 약 435만 장, 23,742개 ROI. 사전학습 U-TILISE·DiffCR 등 일부가 단순 기준선보다 낮았다. 맑은 입력 무시, 색 스펙트럼 오류, 적설 일반화 실패 사례. 토지피복 분할 Jaccard는 맑은 참조 .698, 기존 UnCRtainTS .479, 최저구름 .514, AllClear 재학습 .604. 이는 해당 데이터/모델의 하류 지표이지 보편적 정확도 %가 아니다. 북미를 학습에서 제외한 실험의 PSNR은 전역 34.872 dB 대 북미 31.561 dB였다. 저자들은 구름 라벨의 자동생성 및 대기보정되지 않은 L1C도 한계로 적었다. |
| 확산 기반 생성 | Zou 외, [DiffCR, *IEEE TGRS* 2024](https://ieeexplore.ieee.org/document/10436560/), DOI `10.1109/TGRS.2024.3365806`; Liu 외, [EMRDM, CVPR 2025](https://openaccess.thecvf.com/content/CVPR2025/html/Liu_Effective_Cloud_Removal_for_Remote_Sensing_Images_by_an_Improved_CVPR_2025_paper.html) | 확산모델은 시각적으로 그럴듯한 복원을 만들 수 있지만, AllClear의 독립 평가에서는 사전학습 DiffCR이 단순 기준선보다 낮았다. EMRDM 저자도 기존 생성모델이 흐린 영상의 이미 관측된 정보를 무시하는 문제를 지적했다. |
| 확산모델 학회 발표 | Guo 외, [Cloud Meets Diffusion, IGARSS 2025 공식 세션](https://2025.ieeeigarss.org/view_session.php?SessionID=1134), DOI `10.1109/IGARSS55030.2025.11242781` | 자연 구름의 다양한 모양과 시계열 정보 의존을 다룬 연구. 발표/논문의 개선 수치는 해당 실험 조건에서만 해석해야 한다. |
| SAR 조건부 생성 | Cao 외, [GLCdiffcr, *International Journal of Applied Earth Observation and Geoinformation* 2026](https://www.sciencedirect.com/science/article/pii/S1569843225006600), DOI `10.1016/j.jag.2025.105013` | SAR 안내 확산모델에 전역/국소·조건 일관성 제약을 추가한다. 생성 영상의 내부 일관성을 높이는 시도이며 실제 불투명 구름 아래 동일 시점의 광학 참값을 제공하는 것은 아니다. |
| 인공 결측률 증가 | Grich 외, [*Scientific Reports* 2026](https://www.nature.com/articles/s41598-026-39488-2), DOI `10.1038/s41598-026-39488-2` | 맑은 영상에 인공 가림을 만든 **연속 시간 결측** 실험에서 한 딥러닝 방법의 상대 RMSE가 가림 10→50%일 때 5.96→18.62%로 상승했다. 실제 자연 구름의 동일 시점 복원 성능으로 직접 환산할 수 없다. |
| 원관측 보존 | [TCM-CR, *Remote Sensing* 2026](https://www.mdpi.com/2072-4292/18/15/2443), DOI `10.3390/rs18152443` | 맑은 원관측 픽셀까지 모델이 다시 그려 손실을 만들 수 있고, 영상 평균 PSNR/SSIM이 그 오류를 숨길 수 있다고 지적. 구름 영역과 맑은 영역의 오차를 분리해 보고해야 한다. |
| 홍수 대응 | Li 외, [*ISPRS JPRS* 2024](https://doi.org/10.1016/j.isprsjprs.2024.07.022), DOI `10.1016/j.isprsjprs.2024.07.022` | 흐린 HLS 시계열로 홍수 **분류 지도**를 추정. 논문의 분류 F1은 광학 밴드의 동일 날짜 반사도 복원 정확도가 아니다. 시간에 민감한 사건에 날짜 혼합을 숨기면 안 된다. |
| 다른 해상도 사례 | Liang 외, [전지구 MODIS 500 m 결측 채움, *Earth System Science Data* 2024](https://essd.copernicus.org/articles/16/177/2024/), DOI `10.5194/essd-16-177-2024` | 긴 몬순 구름 공백, 태양/관측각 차이, 대기보정·정합 문제가 여전히 중요하다. 저자 보고 RMSE .0496은 **MODIS 500 m** 제품 평가이며 Sentinel-2 10 m로 전이할 수 없다. |
| 국내 학회 발표 | [ISRS 2026 P-71·P-73 공식 프로그램](https://www.rssj.or.jp/isrs2026/program_final.html) | P-71은 다른 날짜 참조로 인한 시간 불일치와 인공 구름 학습을 다룬다. P-73(인하대·K-water)은 SAR→광학 재구성 영역에 **상당한 오류가 남아** 보정이 필요하다고 명시한다. 학회 초록 수준이며 일반 성능 수치를 제공하지 않는다. |
| 최신 검증 시도 | [CGD-Net, *International Journal of Remote Sensing* 2026](https://www.tandfonline.com/doi/full/10.1080/01431161.2026.2717440), DOI `10.1080/01431161.2026.2717440` | SAR·시계열 기반 모델에서 마스크 교란, 정합 오차, 시차, 극단 구름, 지역 전이를 시험. 보고된 점수는 해당 벤치마크의 모델 점수이며 독립 지역·실제 사건의 운영 정확도 보증이 아니다. |

## 해석할 때 주의할 수치

- **PSNR(dB), SSIM, SAM, RMSE/MAE**는 반사도/영상 유사도와 관계되는 서로 다른 척도다. SSIM 0.9는 “정확도 90%”가 아니다.
- **구름 마스크 F1**이 높아도 가려진 지면 복원 오차는 별개다. **분류 F1**은 홍수/토지피복 분류 결과이며 원래 광학 픽셀의 참값을 보장하지 않는다.
- AllClear의 참조 영상도 일부 구름을 허용하며 평가에서는 참조의 맑은 픽셀을 사용한다. 입력과 참조 날짜 차이가 있으면 실제 변화가 복원 오차로 섞인다.
- 고구름·연속 장마·그림자·눈·농작물 생육·홍수/산불·경계·지역/센서 전이에서 별도 홀드아웃 검증이 필요하다. 명시적 불확실성·결측과 실제 원관측 보존 여부를 확인해야 한다.

## Satellite Insight AI에 적용할 결론

현재 A3의 실제 SCL/NoData 진단과 허용 기간 안의 **실제 관측 선택 합성**을 우선한다. 날짜·Item·남은 결측을 유지하고, 합성을 사건 당일 관측이나 AI 복원으로 부르지 않는다. 향후 ML 추정을 실험한다면 추정 픽셀을 원관측과 별도 레이어/GeoTIFF로 구분하고, 구름 마스크 오차·관측 날짜 차이·지역 홀드아웃·구름 비율별 반사도 오차와 NDVI/홍수 등 목적별 하류 성능을 각각 검증한다. 벤치마크 결과 하나로 “구름 제거 완료”를 선언하지 않는다.
