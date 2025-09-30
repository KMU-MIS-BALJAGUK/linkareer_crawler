# 국민대학교 경영정보학부 창업(개발)소모임 1기 알파프로젝트 "공모자들"



*LinkareerCrawler* 클래스는 링커리어(https://linkareer.com)의 공모전 게시물을 자동으로 수집하고 상세 정보를 추출하기 위한 Selenium 기반 크롤러입니다.

https://linkareer.com/list/contest?filterType=CATEGORY&orderBy_direction=DESC&orderBy_field=CREATED_AT&page=1

<img width="960" height="504" alt="image" src="https://github.com/user-attachments/assets/d6014a00-f014-477d-89ac-29f84662c8e1" />


<img width="960" height="504" alt="image" src="https://github.com/user-attachments/assets/ec2c512b-5d9c-4f27-8567-f61170f45025" />



## 주요 기능

* 최신순으로 정렬된 링커리어 공모전 목록에서 활동(`activity`)의 상세 페이지 URL 수집
* 상세 페이지 방문 후 다음 정보 수집

  * 활동 제목 (`activity_title`)
  * 공식 홈페이지 URL (`activity_url`)
  * 카테고리 리스트 (`activity_category`)
  * 접수 시작일 (`start_date`)
  * 접수 마감일 (`end_date`)
  * 대표 이미지 URL (`activity_img`)
    
* headless 모드 지원 및 Docker 친화적 옵션 적용
* `webdriver_manager`로 ChromeDriver 자동 설치
* 예외 처리 및 로깅 기반 안정성 향상

---

## 요구 사항

* Python 3.10+ (또는 `from __future__ import annotations`를 사용하는 버전 이상)
* 주요 패키지

  * selenium
  * webdriver-manager

예시 설치:

```bash
python -m pip install -r requirements.txt
```

requirements.txt 예시:

```
selenium>=4.8
webdriver-manager>=3.8
```

---

## 사용법

### 코드 구조

* `LinkareerCrawler` 클래스스

  * `fetch_activity_urls(page: int)`

    * 지정된 페이지 번호에서 모든 활동 URL을 수집하여 리스트로 반환합니다.
  * `fetch_activity_details(detail_url: str)`

    * 활동 상세 페이지를 방문하여 세부 정보를 딕셔너리로 반환합니다.
  * `start()` / `stop()`

    * WebDriver 인스턴스의 시작/종료를 담당합니다.

### Testcode

`if __name__ == "__main__"` 블록에 간단한 테스트 실행이 포함되어 있습니다. 기본적으로 `headless=False`로 실행하여 브라우저 동작을 눈으로 확인할 수 있습니다.

```bash
python linkareer_crawler.py
```

스크립트는 1페이지에서 URL을 수집하고, 발견된 URL 중 처음 두 개에 대해 세부 정보를 출력합니다.

---

## 환경 설정 & 옵션

* `LinkareerCrawler(headless: bool = True, wait_time: int = DEFAULT_WAIT, viewport: tuple = (1200, 900), throttle: float = 1.0)`

  * `headless`: 브라우저 UI 없이 실행하려면 `True` (기본값). 디버깅 시 `False` 권장.
  * `wait_time`: `WebDriverWait`에서 요소를 기다리는 최대 초 수.
  * `viewport`: 브라우저 창 크기(너비, 높이).
  * `throttle`: 페이지 요청 사이에 넣을 인위적 지연(초).

* Docker 환경에서 안정적으로 실행하기 위해 다음 옵션을 추가합니다:

  * `--no-sandbox`
  * `--disable-dev-shm-usage`
  * 이미지 로딩 비활성화(`prefs`로 설정)

---

## 선택자(CSS/XPath) 관련 노트

* 코드에서는 다음과 같은 CSS 선택자를 사용합니다.

  * 리스트 페이지: `div.list-body a[href^='/activity/']`
  * 상세 페이지 헤더: `header[class^='ActivityInformationHeader__'] h1`
  * 홈페이지 링크: `dl[class^='HomepageField__'] a`
  * 카테고리: `ul[class^='CategoryChipList__'] p`
  * 시작일/마감일(형제 노드): `.start-at + span`, `.end-at + span`
  * 대표 이미지: `img.card-image` (fallback: `div.poster > img`)


---

## 출력 포맷

`fetch_activity_details`는 다음과 같은 딕셔너리를 반환합니다:

```json
{
  "activity_title": null | "제목",
  "activity_url": null | "https://...",
  "activity_category": [],
  "start_date": null | "YYYY.MM.DD",
  "end_date": null | "YYYY.MM.DD",
  "activity_img": null | "https://...",
  "detail_url": "요청한 상세 페이지 URL"
}
```

