# Damiki Scraper

TackleWarehouse에서 Damiki 낚시 용품 이미지를 자동으로 수집하는 Selenium 기반 스크래퍼입니다.

## 기능

- Damiki 카테고리 페이지에서 모든 제품 자동 수집
- 각 제품의 모든 색상 이미지 다운로드
- 고해상도 이미지 자동 요청 (800px)
- 중복 URL 자동 제거
- 쿠키 배너 자동 처리

## 요구사항

- Python 3.8+
- Chrome 브라우저

## 설치

```bash
# 가상환경 생성 및 활성화
python -m venv venv
source venv/bin/activate  # macOS/Linux
# venv\Scripts\activate  # Windows

# 패키지 설치
pip install -r requirements.txt
```

## 사용법

```bash
# 가상환경 활성화
source venv/bin/activate

# 스크래퍼 실행
python scraper.py
```

## 출력 구조

```
damiki_images/
├── DHYD/
│   ├── DHYD-color_1.jpg
│   ├── DHYD-color_2.jpg
│   └── ...
├── DARM/
│   ├── DARM-color_1.jpg
│   └── ...
└── ...
```

## 수집 통계 (2025.11 기준)

- 총 22개 제품
- 총 153개 이미지
- 평균 7개 색상/제품

## 주요 파일

| 파일 | 설명 |
|------|------|
| `scraper.py` | 메인 스크래퍼 코드 |
| `requirements.txt` | Python 패키지 의존성 |
| `damiki_images/` | 다운로드된 이미지 저장 폴더 |

## 설정 옵션

`scraper.py`에서 수정 가능:

```python
# Headless 모드 (브라우저 창 숨김)
options.add_argument('--headless')  # 주석 해제하여 활성화

# 카테고리 URL 변경
category_url = "https://www.tacklewarehouse.com/catpage-DAM.html"
```

## 문제 해결

### ChromeDriver 오류
webdriver-manager가 자동으로 ChromeDriver를 설치합니다. Chrome 브라우저가 최신 버전인지 확인하세요.

### 이미지가 다운로드되지 않는 경우
- 네트워크 연결 확인
- Chrome 브라우저 업데이트
- `--headless` 옵션이 비활성화되어 있는지 확인 (일부 사이트는 headless 차단)

## 라이선스

개인 사용 목적으로만 사용하세요. TackleWarehouse의 이용약관을 준수하세요.
