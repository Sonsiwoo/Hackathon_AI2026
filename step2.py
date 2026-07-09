import pandas as pd
import FinanceDataReader as fdr
from google import genai

# 🔥 1단계에서 썼던 Gemini API 키를 여기에 똑같이 넣어줘!
GEMINI_API_KEY = "AIzaSyBqq261TDz6hgwu13YDRCVf_qYk-THz1e4"
client = genai.Client(api_key=GEMINI_API_KEY)

def get_llm_mapped_companies(keywords):
    print("🤖 LLM이 시장 상황을 분석하여 키워드별 대장주를 5개씩 엄선하는 중...")
    
    prompt = f"""
    당신은 한국 주식 시장 전문가입니다.
    다음 5개의 테마(키워드)에 대해, 한국 주식 시장(KOSPI, KOSDAQ)에 상장된 가장 대표적인 관련주(대장주)를 각 키워드당 정확히 5개씩 선정해주세요.
    
    키워드 리스트: {', '.join(keywords)}
    
    [출력 규칙]
    1. 반드시 "키워드,종목명" 형태의 CSV 포맷으로만 출력하세요.
    2. 종목명은 한국거래소(KRX) 공식 명칭을 사용하세요. (예: 퀄컴 안됨, 삼성전자 가능)
    3. 부연 설명이나 코드 블록(```) 등 불필요한 텍스트는 절대 작성하지 마세요.
    
    [출력 예시]
    {keywords[0]},삼성전자
    {keywords[0]},SK하이닉스
    """
    
    try:
        response = client.models.generate_content(
            model='gemini-2.5-flash',
            contents=prompt
        )
        # LLM이 준 텍스트를 줄바꿈 단위로 쪼개서 리스트로 반환
        return response.text.strip().split('\n')
    except Exception as e:
        print(f"Gemini API 에러: {e}")
        return []

if __name__ == "__main__":
    print("🚀 [Step 2] LLM 기반 종목 정밀 매핑 시작...")
    
    try:
        df_trends = pd.read_csv('llm_top5_trends.csv')
        keywords = df_trends['Keyword'].tolist()
    except FileNotFoundError:
        print("❌ 에러: 'llm_top5_trends.csv' 파일이 없습니다. 1단계를 먼저 실행해주세요.")
        exit()

    # 1. LLM에게 종목 리스트 텍스트로 받아오기
    llm_result_lines = get_llm_mapped_companies(keywords)
    
    # 2. KRX 전체 종목 데이터 불러오기 (종목코드 추출용)
    print("📊 KRX 상장 종목 데이터와 교차 검증 중...")
    df_krx = fdr.StockListing('KRX')
    
    final_data = []

    # 3. LLM 결과물을 파싱해서 종목코드 정확히 찾기
    for line in llm_result_lines:
        line = line.strip()
        if not line or ',' not in line:
            continue
            
        try:
            kw, comp_name = line.split(',', 1)
            kw = kw.strip()
            comp_name = comp_name.strip()
            
            # KRX 데이터에서 종목명으로 검색 (정확히 일치)
            matched_row = df_krx[df_krx['Name'] == comp_name]
            
            if not matched_row.empty:
                code = matched_row.iloc[0]['Code']
                market = matched_row.iloc[0]['Market']
                final_data.append({'Keyword': kw, 'Code': code, 'Name': comp_name, 'Market': market})
            else:
                # 정확한 이름이 없으면 융통성 있게 포함된 이름 찾기 (예: 삼성생명보험 -> 삼성생명)
                fallback_row = df_krx[df_krx['Name'].str.contains(comp_name, case=False, na=False)]
                if not fallback_row.empty:
                    code = fallback_row.iloc[0]['Code']
                    name = fallback_row.iloc[0]['Name']
                    market = fallback_row.iloc[0]['Market']
                    final_data.append({'Keyword': kw, 'Code': code, 'Name': name, 'Market': market})
                else:
                    print(f"⚠️ '{comp_name}'은(는) 상장 종목에서 찾을 수 없어 제외됩니다.")
        except Exception:
            continue

    # 4. 결과 출력 및 저장
    if final_data:
        final_result_df = pd.DataFrame(final_data)
        print("\n🏆 [최종 매핑된 기업 리스트]")
        print(final_result_df.to_string(index=False))
        
        final_result_df.to_csv('step2_mapped_companies.csv', index=False, encoding='utf-8-sig')
        print(f"\n✅ 매핑 완료! 총 {len(final_result_df)}개 기업이 완벽하게 정리되어 'step2_mapped_companies.csv'로 저장되었습니다.")
    else:
        print("⚠️ 매핑에 실패했습니다.")