export async function post<T>(path: string, body: unknown, signal?:AbortSignal): Promise<T> {
  const controller = new AbortController();
  const timer = setTimeout(() => controller.abort(), 120000);
  try {
    const response = await fetch(`/api/${path}`, {method: 'POST', headers: {'Content-Type': 'application/json'}, body: JSON.stringify(body), signal: signal?AbortSignal.any([signal,controller.signal]):controller.signal});
    const data = await response.json().catch(() => null);
    if (!response.ok) {
      if(path==='search' && data?.outcome==='failed' && Array.isArray(data.collection_statuses)) return data as T;
      const details = data?.error?.details?.map((d: {message: string}) => d.message).join(' / ');
      throw new Error([data?.error?.message || (typeof data?.detail==='string'?data.detail:null) || `서버 요청 실패 (${response.status})`, details].filter(Boolean).join(' '));
    }
    return data as T;
  } catch (error) {
    if(signal?.aborted) throw error;
    if (error instanceof Error && error.name === 'AbortError') throw new Error('요청 시간이 초과되었습니다. 검색 범위를 줄여 다시 시도하세요.');
    if (error instanceof TypeError) throw new Error('서버에 연결할 수 없습니다. 백엔드가 실행 중인지 확인하세요.');
    throw error;
  } finally { clearTimeout(timer); }
}
