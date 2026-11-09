/** Official discovery portals. These links do not imply that this app searched them. */
export const COPERNICUS_BROWSER = {
  name: 'Copernicus Browser',
  url: 'https://dataspace.copernicus.eu/browser/',
  access: '포털 계정이 필요할 수 있습니다. 포털에서 자료와 접근 조건을 다시 확인하세요.',
};

export const EARTH_EXPLORER = {
  name: 'USGS EarthExplorer',
  url: 'https://earthexplorer.usgs.gov/',
  access: 'USGS 계정이 필요합니다. 포털에서 자료와 접근 조건을 다시 확인하세요.',
};

export function portalForCollection(collection: string) {
  if (collection === 'sentinel-2-l2a' || collection === 'sentinel-1-grd') return COPERNICUS_BROWSER;
  if (['viirs-vnp09ga-002','hls-l30-002','hls-s30-002'].includes(collection)) return {name:'NASA Earthdata Search',url:'https://search.earthdata.nasa.gov/',access:'원본 파일은 서버 Earthdata 인증과 대상 제품 이용 조건 확인이 필요합니다.'};
  if (collection === 'landsat-c2-l2') return EARTH_EXPLORER;
  return null;
}

export function portalForProfile(id: string) {
  if (id === 's1_csar') return COPERNICUS_BROWSER;
  return null;
}
