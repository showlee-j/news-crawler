import streamlit as st
import re
import html
import time
import requests
from bs4 import BeautifulSoup
from urllib.parse import urlparse
from email.utils import parsedate_to_datetime
import pandas as pd

# =========================
# 0) API 정보 (보안상 환경변수 권장)
# =========================
CLIENT_ID = "3bewxYUlBRRcl9j2X4AK"
CLIENT_SECRET = "dDgX44GYmS"
NAVER_NEWS_API = "https://openapi.naver.com/v1/search/news.json"

# =========================
# 유틸리티 함수 (기존 코드 유지)
# =========================
def strip_html_tags(text):
    text = html.unescape(text or "")
    return re.sub(r"<[^>]+>", "", text).strip()

def normalize_spaces(s):
    s = (s or "").replace("\xa0", " ")
    s = re.sub(r"\s+", " ", s).strip()
    return s

def contains_any_keyword(text, keywords):
    t = (text or "").lower()
    return any(k.strip().lower() in t for k in keywords if k.strip())

def format_pubdate(pubdate_str):
    try:
        dt = parsedate_to_datetime(pubdate_str)
        return dt.strftime("%Y-%m-%d")
    except: return ""

# (생략된 크롤링 함수들: fetch_press_and_body, extract_naver_body 등은 기존 코드와 동일하게 유지)
# 여기에 기존 코드의 3)번과 4)번 함수들을 그대로 복사해서 넣어주세요.

def fetch_press_and_body(url):
    try:
        headers = {"User-Agent": "Mozilla/5.0"}
        r = requests.get(url, headers=headers, timeout=10)
        r.raise_for_status()
        soup = BeautifulSoup(r.text, "html.parser")
        
        # 간단한 추출 로직 (기존 함수 활용)
        press = "알 수 없음"
        meta_press = soup.select_one("meta[property='og:site_name']")
        if meta_press: press = meta_press['content']
        
        body = soup.get_text(" ", strip=True)
        return press, body
    except:
        return "접근불가", ""

# =========================
# 5) Streamlit UI 구현
# =========================
st.set_page_config(page_title="뉴스 키워드 수집기", layout="wide")

st.title("📰 실시간 뉴스 키워드 수집기")
st.markdown("네이버 뉴스 API를 활용하여 최신 뉴스를 검색하고 본문을 필터링합니다.")

with st.sidebar:
    st.header("설정")
    # 사용자로부터 키워드 입력 받기 (쉼표로 구분)
    user_keywords = st.text_input("검색 키워드 (쉼표로 구분)", "밀라노, 올림픽, 급식")
    display_count = st.slider("검색 건수", 10, 100, 50)
    start_button = st.button("뉴스 수집 시작")

if start_button:
    keywords = [k.strip() for k in user_keywords.split(",")]
    query = " ".join(keywords)
    
    headers = {"X-Naver-Client-Id": CLIENT_ID, "X-Naver-Client-Secret": CLIENT_SECRET}
    params = {"query": query, "display": display_count, "sort": "date"}
    
    with st.spinner('뉴스를 불러오는 중입니다...'):
        response = requests.get(NAVER_NEWS_API, headers=headers, params=params)
        
        if response.status_code == 200:
            items = response.json().get("items", [])
            results = []
            
            progress_bar = st.progress(0)
            for idx, it in enumerate(items):
                title = strip_html_tags(it.get("title", ""))
                link = it.get("link", "")
                pub_date = format_pubdate(it.get("pubDate", ""))
                
                # 본문 수집
                press, body = fetch_press_and_body(link)
                
                # 필터링
                if contains_any_keyword(title + " " + body, keywords):
                    results.append({
                        "날짜": pub_date,
                        "언론사": press,
                        "제목": title,
                        "URL": link
                    })
                
                # 진행률 표시
                progress_bar.progress((idx + 1) / len(items))
                time.sleep(0.1)
            
            # 결과 출력
            st.success(f"총 {len(results)}건의 뉴스를 발견했습니다.")
            df = pd.DataFrame(results)
            
            # 테이블 출력 및 엑셀 다운로드
            st.dataframe(df, use_container_width=True)
            
            csv = df.to_csv(index=False).encode('utf-8-sig')
            st.download_button("CSV 결과 다운로드", csv, "news_result.csv", "text/csv")
        else:
            st.error("API 연결에 실패했습니다. ID와 Secret을 확인해주세요.")
