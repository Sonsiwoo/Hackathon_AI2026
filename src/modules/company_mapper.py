"""
[2단계용 모듈] 트렌드 키워드 → 실제 상장 종목 매핑

흐름: 1단계에서 뽑은 트렌드 키워드(예: '반도체')를 Gemini에게 주고
      "이 테마의 대장주 5개"를 물어본 뒤, 실제 KRX(한국거래소) 상장 종목 목록과
      대조해서 정확한 종목코드(Code)/시장구분(Market)을 찾아 붙여준다.
      LLM이 종목명을 조금 다르게 말하거나 오타를 낼 수 있으므로,
      정확히 일치하는 이름이 없으면 '포함' 관계로도 한 번 더 찾아본다 (fallback).
"""

import FinanceDataReader as fdr

from modules import gemini_client


def request_llm_company_candidates(keywords):
    """
    키워드(테마) 리스트를 Gemini에게 보내 테마별 대표 종목(대장주) 5개씩을 요청한다.

    Args:
        keywords: 트렌드 키워드 문자열 리스트 (예: ['반도체', '인공지능', ...])

    Returns:
        "키워드,종목명" 형태의 텍스트 줄(line) 리스트. 아직 종목코드는 없는 원본 응답이며,
        실제 코드/시장구분 매핑은 map_companies_to_krx()에서 처리한다.
        LLM 호출이 실패하면 빈 리스트를 반환한다.
    """
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
        response = gemini_client.get_client().models.generate_content(
            model='gemini-flash-latest',
            contents=prompt
        )
        # 줄바꿈 단위로 쪼개서 반환 (한 줄 = "키워드,종목명")
        return response.text.strip().split('\n')
    except Exception as e:
        print(f"Gemini API 에러: {e}")
        return []


def load_krx_listing():
    """
    한국거래소(KRX)에 상장된 전체 종목 목록을 가져온다.
    종목명 → 종목코드/시장구분을 조회하기 위한 '정답지' 역할.

    Returns:
        Code(종목코드), Name(종목명), Market(시장구분) 등을 포함한 DataFrame
    """
    return fdr.StockListing('KRX')


def resolve_company_code(df_krx, comp_name):
    """
    LLM이 알려준 종목명(comp_name)을 KRX 상장 목록에서 찾아 종목코드/시장구분을 붙인다.

    1차: 이름이 정확히 일치하는 종목을 찾는다.
    2차(fallback): 정확히 일치하는 게 없으면, 이름에 comp_name이 '포함'된 종목을 찾는다.
                    (예: LLM이 "삼성생명보험"이라고 답했는데 실제 상장명은 "삼성생명"인 경우 등을 구제)

    Args:
        df_krx: load_krx_listing()이 반환한 전체 상장 종목 DataFrame
        comp_name: LLM이 알려준 종목명 문자열

    Returns:
        {'Code': 종목코드, 'Name': 실제 상장명, 'Market': 시장구분} 딕셔너리.
        둘 다 못 찾으면 None (호출부에서 해당 종목을 결과에서 제외하고 경고 출력).
    """
    matched_row = df_krx[df_krx['Name'] == comp_name]
    if not matched_row.empty:
        return {
            'Code': matched_row.iloc[0]['Code'],
            'Name': comp_name,
            'Market': matched_row.iloc[0]['Market'],
        }

    # 정확매칭 실패 시, 이름에 comp_name이 포함된 종목을 대소문자 구분 없이 탐색
    fallback_row = df_krx[df_krx['Name'].str.contains(comp_name, case=False, na=False)]
    if not fallback_row.empty:
        return {
            'Code': fallback_row.iloc[0]['Code'],
            'Name': fallback_row.iloc[0]['Name'],
            'Market': fallback_row.iloc[0]['Market'],
        }

    return None


def map_companies_to_krx(llm_lines, df_krx):
    """
    request_llm_company_candidates()의 원본 응답 줄들을 파싱해서
    실제 KRX 종목코드/시장구분이 붙은 최종 리스트로 변환한다.

    Args:
        llm_lines: "키워드,종목명" 형태의 텍스트 줄 리스트
        df_krx: load_krx_listing()이 반환한 전체 상장 종목 DataFrame

    Returns:
        {'Keyword', 'Code', 'Name', 'Market'} 딕셔너리들의 리스트.
        형식이 이상한 줄이나 매칭 실패한 종목은 조용히 건너뛴다 (전체 파이프라인이 죽지 않도록).
    """
    final_data = []

    for line in llm_lines:
        line = line.strip()
        # 빈 줄이거나 "키워드,종목명" 형식이 아니면(콤마 없음) 건너뜀
        if not line or ',' not in line:
            continue

        try:
            kw, comp_name = line.split(',', 1)
            kw = kw.strip()
            comp_name = comp_name.strip()

            resolved = resolve_company_code(df_krx, comp_name)
            if resolved:
                final_data.append({
                    'Keyword': kw,
                    'Code': resolved['Code'],
                    'Name': resolved['Name'],
                    'Market': resolved['Market'],
                })
            else:
                print(f"⚠️ '{comp_name}'은(는) 상장 종목에서 찾을 수 없어 제외됩니다.")
        except Exception:
            # 예상 못한 파싱 오류가 나도 그 줄만 건너뛰고 나머지는 계속 처리
            continue

    return final_data
