import urllib.request
import json
import pandas as pd
import re
from google import genai

# 1. API 키 세팅
naver_client_id = "GTUC2M3UrjfrFu6TLZwD"
naver_client_secret = "QIiUftG0ku"

GEMINI_API_KEY = "AIzaSyBqq261TDz6hgwu13YDRCVf_qYk-THz1e4"

# 🔥 최신 SDK 클라이언트 생성 방식
client = genai.Client(api_key=GEMINI_API_KEY)

def get_financial_news(display=100):
    query = "특징주 | 주가 | 관련주 | 수혜주"
    encText = urllib.parse.quote(query)
    url = f"https://openapi.naver.com/v1/search/news?query={encText}&display={display}&sort=date"
    
    request = urllib.request.Request(url)
    request.add_header("X-Naver-Client-Id", naver_client_id)
    request.add_header("X-Naver-Client-Secret", naver_client_secret)
    
    try:
        response = urllib.request.urlopen(request)
        if response.getcode() == 200:
            return json.loads(response.read().decode('utf-8'))['items']
    except Exception as e:
        print(f"네이버 API 에러: {e}")
    return []

def extract_trends_with_llm(news_items):
    headlines = [re.sub(r'<[^>]*>', '', item['title']) for item in news_items]
    headlines_text = "\n".join(headlines)
    
    prompt = f"""
    다음은 주식 시장 최신 뉴스 헤드라인 100개입니다.
    가장 핫한 '산업군, 테마, 기술 트렌드' 키워드 TOP 5를 추출해주세요.
    (주의: '지정', '상승' 같은 공시/주식 일반 용어 제외. 오직 산업/테마 명사만 5개 콤마로 구분해서 출력)
    
    [헤드라인]
    {headlines_text}
    """
    try:
        # 🔥 최신 SDK 호출 문법 + 최신 2.5 flash 모델 적용
        response = client.models.generate_content(
            model='gemini-2.5-flash',
            contents=prompt
        )
        result_text = response.text.strip()
        return [kw.strip() for kw in result_text.split(',')]
    except Exception as e:
        print(f"Gemini API 에러: {e}")
        return []

# 3. 메인 실행부
if __name__ == "__main__":
    print("🚀 실시간 뉴스 기반 LLM 트렌드 분석 시작...")
    
    news_data = get_financial_news(display=100)
    
    if news_data:
        print(f"✅ {len(news_data)}개의 금융 기사 수집 완료. LLM이 진짜 산업 테마를 솎아내는 중...")
        top_5_trends = extract_trends_with_llm(news_data)
        
        print("\n🔥 [LLM이 도출한 현재 주식 시장 산업 트렌드 TOP 5] 🔥")
        for i, keyword in enumerate(top_5_trends, 1):
            print(f"{i}위: {keyword}")
            
        trend_df = pd.DataFrame({'Keyword': top_5_trends})
        trend_df.to_csv('llm_top5_trends.csv', index=False, encoding='utf-8-sig')