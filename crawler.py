from __future__ import annotations
import time
import json
import logging
from typing import List, Dict, Optional
from urllib.parse import urljoin
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from selenium.common.exceptions import (
    TimeoutException, NoSuchElementException, WebDriverException
)
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager


logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
# "LinkareerCrawler" 로거 생성
logger = logging.getLogger("LinkareerCrawler")

DEFAULT_WAIT = 12


class LinkareerCrawler:
    """
    링커리어(https://linkareer.com) 크롤링 클래스.
    """
    # 최신순으로 정렬된 공모전 목록 페이지 URL의 기본 형태
    Newest_Url="https://linkareer.com/list/contest?filterType=CATEGORY&orderBy_direction=DESC&orderBy_field=CREATED_AT&page="
    
    BASE_URL = "https://linkareer.com"
    
    LIST_PATH = "/list/contest"

    def __init__(self,
                 headless: bool = True,
                 wait_time: int = DEFAULT_WAIT,
                 viewport: tuple = (1200, 900),
                 throttle: float = 1.0):
        """
        Args:
            headless (bool): True일 경우 브라우저 창을 띄우지 않고 백그라운드에서 실행
            wait_time (int): 웹 요소가 나타날 때까지 기다리는 최대 시간(초)
            viewport (tuple): 브라우저 창 크기를 (너비, 높이) 튜플로 설정
            throttle (float): 각 HTTP 요청 사이에 추가하는 대기 시간(초)
        """
        self.headless = headless
        self.wait_time = wait_time
        self.viewport = viewport
        self.throttle = throttle
        self.driver = None

    def _make_driver(self):
        """Selenium WebDriver 인스턴스를 생성하고 설정을 최적화"""
        opts = Options()
        # headless 모드 설정: True일 경우 UI 없이 백그라운드에서 실행
        if self.headless:
            opts.add_argument("--headless=new")
        
        # Docker 또는 Linux 환경에서 권한 문제 및 메모리 부족 문제 방지를 위한 옵션
        opts.add_argument("--no-sandbox")
        opts.add_argument("--disable-dev-shm-usage")
        opts.add_argument(f"--window-size={self.viewport[0]},{self.viewport[1]}")

        # 이미지 로딩 비활성화: 크롤링 속도 향상 및 리소스 사용량 감소
        prefs = {"profile.managed_default_content_settings.images": 2}
        opts.add_experimental_option("prefs", prefs)

        # ChromeDriverManager를 통해 시스템에 맞는 드라이버를 자동으로 설치
        # Service 객체를 명시적으로 사용하여 executable_path와 options를 분리하여 전달
        service=Service(executable_path=ChromeDriverManager().install())
        driver = webdriver.Chrome(service=service, options=opts)
        return driver

    def start(self):
        """웹 드라이버 시작"""
        if self.driver is None:
            logger.info("Starting WebDriver")
            self.driver = self._make_driver()

    def stop(self):
        """웹 드라이버를 안전하게 종료하고 리소스를 해제"""
        if self.driver:
            try:
                self.driver.quit()
            except Exception:
                pass
            self.driver = None
            logger.info("WebDriver stopped.")

    def fetch_activity_urls(self, page: int = 1) -> List[str]:
        """
        URL 수집
        특정 page 번호의 공모전 상세 페이지 URL 목록을 크롤링

        Args:
            page (int): 가져올 페이지 번호.

        Returns:
            List[str]: 해당 페이지에 있는 모든 공모전 상세 페이지의 절대 URL 리스트.
        """
        self.start()
        driver = self.driver
        list_url = f"{self.Newest_Url}{page}"

        logger.info("Opening list page: %s", list_url)
        driver.get(list_url)

        # 동적으로 렌더링되는 목록의 첫 번째 항목이 나타날 때까지 대기
        # 페이지가 비어있거나 로드에 실패 시 TimeoutException 발생
        wait = WebDriverWait(driver, self.wait_time)
        try:
            wait.until(EC.presence_of_element_located(
                (By.CSS_SELECTOR, "div.list-body a[href^='/activity/']")
            ))
        except TimeoutException:
            logger.warning("Warning method(fetch_activity_urls) Timeout waiting for list page to render on page %d. No activities found or page is empty.", page)
            return []

        # list-body 내에서 '/activity/'로 시작하는 모든 링크(<a> 태그)
        anchors = driver.find_elements(By.CSS_SELECTOR, "div.list-body a[href^='/activity/']")
        logger.info("Found %d anchors on page %d", len(anchors), page)

        # 중복된 URL 수집을 방지하기 위해 set을 사용
        seen_urls = set()
        urls = []
        for el in anchors:
            try:
                href = el.get_attribute("href")
                if not href:
                    continue
                
                # 상대 경로(e.g., '/activity/12345')를 절대 경로(e.g., 'https://...')로 변환
                href = urljoin(self.BASE_URL, href)
                if href not in seen_urls:
                    seen_urls.add(href)
                    urls.append(href)
            except Exception as e:
                logger.debug("Error parsing anchor element: %s", e)
                continue
        
        logger.info("Found %d unique activity URLs on page %d", len(urls), page)
        return urls

    def fetch_activity_details(self, detail_url: str) -> Optional[Dict]:

        """
        상세 정보 추출
        activity 상세 페이지를 방문하여 세부 정보를 추출

        Args:
            detail_url (str): 정보를 추출할 상세 페이지의 절대 URL.

        Returns:
            Optional[Dict]: 추출된 정보가 담긴 딕셔너리. 실패 시 None을 반환.
        """
        self.start()
        driver = self.driver
        logger.info("Visiting detail page: %s", detail_url)
        
        try:
            driver.get(detail_url)
        except WebDriverException as e:
            logger.error("WebDriverException visiting %s: %s", detail_url, e)
            return None

        
        wait = WebDriverWait(driver, self.wait_time)
        try:
            wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, "header[class^='ActivityInformationHeader__']")))
        except TimeoutException:
            logger.warning("Timeout waiting for detail page to render: %s", detail_url)
            return None

        time.sleep(self.throttle)

        # 결과를 저장할 딕셔너리를 기본값으로 초기화
        result = {
            "activity_title": None,
            "activity_url": None,
            "activity_category": [],
            "start_date": None,
            "end_date": None,
            "activity_img": None,
            "detail_url": detail_url
        }

        # --- 각 필드 스크래핑 시작 ---

        # 제목 (activity_title): 헤더(<header>) 안의 <h1> 태그에서 텍스트 추출
        try:
            #ActivityInformationHeader__로 시작하는 class의 h1
            title_element = driver.find_element(By.CSS_SELECTOR, "header[class^='ActivityInformationHeader__'] h1")
            result["activity_title"] = title_element.text.strip()
        except NoSuchElementException:
            logger.debug("Title not found on %s", detail_url)

        # 홈페이지 URL (activity_url): 'HomepageField' 클래스로 시작하는 <dl> 내부의 <a> 태그에서 href 속성 추출
        try:
            home_anchor = driver.find_element(By.CSS_SELECTOR, "dl[class^='HomepageField__'] a")
            result["activity_url"] = home_anchor.get_attribute("href")
        except NoSuchElementException:
            logger.debug("Homepage/activity_url not found on %s", detail_url)

        # 카테고리 (activity_category): 카테고리 칩 목록 내부의 모든 <p> 태그 텍스트를 가져와 '/' 기준으로 분리하고, 하나의 리스트로 만듭니다.
        try:
            category_elements = driver.find_elements(By.CSS_SELECTOR, "ul[class^='CategoryChipList__'] p")
            categories = []
            for p_element in category_elements:
                categories.extend(p_element.text.strip().split('/'))
            # 빈 문자열 제거 후 리스트로
            result["activity_category"] = [cat.strip() for cat in categories if cat.strip()]
        except NoSuchElementException:
            logger.debug("Category not found on %s", detail_url)

        # 접수 시작일 (start_date): 'start-at' 클래스를 가진 <span> 태그의 텍스트를 추출
        try:
            result["start_date"] = driver.find_element(By.CSS_SELECTOR, ".start-at + span").text.strip()
        except NoSuchElementException:
            logger.debug("Start date not found on %s", detail_url)

        # 접수 마감일 (end_date): 'end-at' 클래스를 가진 <span> 태그의 텍스트를 추출
        try:
            result["end_date"] = driver.find_element(By.CSS_SELECTOR, ".end-at + span").text.strip()
        except NoSuchElementException:
            logger.debug("End date not found on %s", detail_url)

        # 대표 이미지 (activity_img): 'card-image' 클래스 <img> 태그의 src 속성을 추출
        try:
            result["activity_img"] = driver.find_element(By.CSS_SELECTOR, "img.card-image").get_attribute("src")
        except NoSuchElementException:
            logger.debug("img.card-image not found, trying fallback selector.")
            try:
                poster_img = driver.find_element(By.CSS_SELECTOR, "div.poster > img")
                result["activity_img"] = poster_img.get_attribute("src")
            except NoSuchElementException:
                logger.debug("Activity image not found on %s", detail_url)
                
        return result

if __name__ == "__main__":
    
    # 테스트 시에는 브라우저 동작을 직접 보기 위해 headless=False로
    crawler = LinkareerCrawler(headless=False)

    try:
        # 1. 1페이지에서 모든 공모전 URL fetch
        print("\n--- 1. Fetching URLs from page 1 ---")
        activity_urls = crawler.fetch_activity_urls(page=1)
        
        
        if not activity_urls:
            print("No activity URLs found on page 1. Exiting.")
            
        else:
            # 테스트를 위해 최대 2개의 URL에 대해서만 상세 정보 fetch

            print(f"Found {len(activity_urls)} URLs. 처음 두개의 url에 대해서만 세부 정보 조회")

            for url in activity_urls[:2]:
                print(f"\n--- 2. Fetching details for: {url} ---")
                details = crawler.fetch_activity_details(url)

                if details:

                    # 한글이 깨지지 않도록 ensure_ascii=False를 사용
                    print(json.dumps(details, indent=4, ensure_ascii=False))
                else:
                    print(f"Failed to fetch details for {url}")

    except Exception as e:
        # 테스트 실행 중 발생할 수 있는 모든 예외를 처리
        print(f"\nAn error occurred during the test run: {e}")

    finally:
        print("\n--- 3. Stopping crawler ---")
        crawler.stop() 