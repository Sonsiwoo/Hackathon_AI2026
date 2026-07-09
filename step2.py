import requests
from bs4 import BeautifulSoup
import pandas as pd
import FinanceDataReader as fdr
import io 

def get_top_5_by_keyword(keyword):
    print(f"🔍 '{keyword}' 관련 핫한 테마를 검색 중입니다...")
    
    url = "https://finance.naver.com/sise/theme.naver"
    headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}
    
    try:
        res = requests.get(url, headers=headers)
        soup = BeautifulSoup(res.text, 'html.parser')
        theme_links = soup.select('.col_type1 a')
    except Exception as e:
        print(f"네이버 테마 페이지 로드 실패: {e}")
        return None

    target_url = None
    theme_name = ""
    for link in theme_links:
        if keyword in link.text:
            target_url = "https://finance.naver.com" + link['href']
            theme_name = link.text.strip()
            print(f"🎯 매칭된 테마를 찾았습니다: [{theme_name}]")
            break
            
    if not target_url:
        print(f"❌ 네이버 금융 테마에서 '{keyword}'를 포함한 항목을 찾지 못했습니다.")
        stock_names = []
    else:
        theme_res = requests.get(target_url, headers=headers)
        tables = pd.read_html(io.StringIO(theme_res.text), encoding='euc-kr')
        
        theme_df = tables[2] 
        theme_df = theme_df.dropna(subset=['종목명'])
        stock_names = theme_df['종목명'].tolist()

    print("📊 KRX 전체 종목 데이터를 조회하는 중...")
    df_krx = fdr.StockListing('KRX')
    
    if stock_names:
        filtered_df = df_krx[df_krx['Name'].isin(stock_names)].copy()
    else:
        filtered_df = df_krx[df_krx['Name'].str.contains(keyword, na=False)].copy()
        
    if filtered_df.empty:
        print(f"⚠️ '{keyword}' 결과가 없습니다. 스킵합니다.")
        return None
        
    top_5 = filtered_df.head(5)
    
    # 🔥 에러 해결 부분: 'Symbol' 대신 'Code'로 바로 가져오기!
    result = top_5[['Code', 'Name', 'Market']].copy()
    result.reset_index(drop=True, inplace=True)
    result.index = result.index + 1 
    
    return result

if __name__ == "__main__":
    print("🚀 [Step 2] LLM 트렌드 키워드 기반 관련주 매핑 시작...")
    
    try:
        df_trends = pd.read_csv('llm_top5_trends.csv')
        keywords = df_trends['Keyword'].tolist()
    except FileNotFoundError:
        print("❌ 에러: 'llm_top5_trends.csv' 파일이 없습니다. 1단계를 먼저 실행해주세요.")
        exit()

    all_mapped_companies = []

    for kw in keywords:
        top5_companies_df = get_top_5_by_keyword(kw)
        
        if top5_companies_df is not None and not top5_companies_df.empty:
            top5_companies_df.insert(0, 'Keyword', kw) 
            all_mapped_companies.append(top5_companies_df)
            
            print(f"\n🏆 '{kw}' 분야 상위 5개 기업")
            print(top5_companies_df.to_string(index=False))
            print("-" * 50)

    if all_mapped_companies:
        final_result_df = pd.concat(all_mapped_companies, ignore_index=True)
        final_result_df.to_csv('step2_mapped_companies.csv', index=False, encoding='utf-8-sig')
        print(f"\n✅ 매핑 완료! 총 {len(final_result_df)}개 기업의 데이터가 'step2_mapped_companies.csv'로 저장되었습니다.")
    else:
        print("⚠️ 매핑된 기업이 없어서 CSV 파일을 생성하지 못했습니다.")