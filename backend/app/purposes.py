from .models import Purpose

KEYWORDS = {
    Purpose.vegetation: ('식생', '녹지', '산림', '농작물', '작황', 'ndvi', 'vegetation'),
    Purpose.flood: ('침수', '홍수', '장마', '집중호우', '수역', 'flood', 'water'),
    Purpose.urban: ('도시', '토지피복', '토지 피복', '개발', 'urban', 'land cover'),
    Purpose.thermal: ('열환경', '열섬', '온도', '열적외선', 'thermal', 'temperature'),
}
LABELS = {'vegetation': '식생 분석', 'flood': '침수·수역 분석', 'urban': '도시·토지피복 변화', 'thermal': '열환경 분석'}


def classify(text: str, explicit: Purpose | None):
    """Require an explicit choice if no rule or multiple purpose rules match."""
    if explicit:
        return explicit, ['사용자 직접 선택']
    matches = {p: [word for word in words if word in text.lower()] for p, words in KEYWORDS.items()}
    found = [(p, words) for p, words in matches.items() if words]
    return found[0] if len(found) == 1 else (None, [])
