import streamlit as st
import pandas as pd
import os
import plotly.graph_objects as go

# 이 파일(app/APP.py) 기준으로 저장소 루트(HACKATHON/)를 계산해서
# streamlit을 어느 디렉터리에서 실행하든(예: `streamlit run app/APP.py`를
# 저장소 루트가 아닌 다른 위치에서 실행해도) src/, predictions/ 경로를 항상 정확히 찾도록 함.
_APP_DIR = os.path.dirname(os.path.abspath(__file__))
_REPO_ROOT = os.path.dirname(_APP_DIR)

# 1. 페이지 기본 설정
st.set_page_config(page_title="AI-2026 Quant Dashboard", layout="wide")

# 2. 커스텀 CSS (UI 폰트 컬러 버그 완벽 수정)
st.markdown("""
<style>
    .reportview-container { background-color: #f8f9fa; }

    /* 사이드바 배경 및 모든 텍스트를 흰색으로 강제 고정 */
    [data-testid="stSidebar"] { background-color: #1e293b; color: white !important; }
    [data-testid="stSidebar"] * { color: white !important; }

    /* 🔥 단, 셀렉트박스(검색창) 입력란 안의 글자만 까만색으로 예외 처리! */
    /* 최신 Streamlit은 react-aria 기반 콤보박스를 쓰므로 stSelectbox testid로 타겟팅 */
    [data-testid="stSelectbox"] input { color: #0f172a !important; }
    [data-testid="stSelectbox"] input::placeholder { color: #64748b !important; }

    /* 메인 지표 컨테이너 디자인 */
    div[data-testid="metric-container"] { background-color: #ffffff; border: 1px solid #e2e8f0; padding: 20px; border-radius: 12px; box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.05); }

    /* 탭 디자인 */
    .stTabs [data-baseweb="tab-list"] { gap: 20px; }
    .stTabs [data-baseweb="tab"] { height: 50px; white-space: pre-wrap; font-weight: 600; }
</style>
""", unsafe_allow_html=True)

# 3. 데이터 로드 함수
@st.cache_data
def load_data():
    trends_path = os.path.join(_REPO_ROOT, 'src', 'llm_top5_trends.csv')
    mapping_path = os.path.join(_REPO_ROOT, 'src', 'step2_mapped_companies.csv')
    prediction_path = os.path.join(_REPO_ROOT, 'predictions', 'stock_prediction_log.csv')

    # 프로젝트의 다른 CSV들과 동일하게 utf-8-sig(BOM 포함)로 저장되므로 인코딩을 맞춰서 읽는다.
    df_trends = pd.read_csv(trends_path, encoding='utf-8-sig') if os.path.exists(trends_path) else pd.DataFrame()
    df_mapping = pd.read_csv(mapping_path, dtype={'Code': str}, encoding='utf-8-sig') if os.path.exists(mapping_path) else pd.DataFrame()
    df_pred = pd.read_csv(prediction_path, dtype={'code': str}, encoding='utf-8-sig') if os.path.exists(prediction_path) else pd.DataFrame()

    if not df_trends.empty: df_trends.columns = df_trends.columns.str.strip()
    if not df_mapping.empty: df_mapping.columns = df_mapping.columns.str.strip()
    if not df_pred.empty: df_pred.columns = df_pred.columns.str.strip()

    return df_trends, df_mapping, df_pred

df_trends, df_mapping, df_pred = load_data()

if df_pred.empty:
    st.error("데이터가 없습니다. 백엔드 파이프라인을 먼저 실행해주세요.")
    st.stop()

# 4. 좌측 사이드바
with st.sidebar:
    st.markdown("## AI-2026 Navigation")
    st.divider()

    st.markdown("### Market Trends")
    # 5개 분야(반도체/인공지능/바이오/원전/우주항공) 전체가 선택지로 뜬다.
    selected_keyword = st.selectbox("분석할 테마를 선택하세요", df_trends['Keyword'].unique(), label_visibility="collapsed")

    st.markdown("<br>", unsafe_allow_html=True)
    st.markdown("### Top 5 Companies")
    filtered_companies = df_mapping[df_mapping['Keyword'] == selected_keyword]
    selected_company_name = st.radio("종목 선택", filtered_companies['Name'].unique(), label_visibility="collapsed")

# 5. 메인 화면
st.title(f"{selected_company_name} AI 분석 리포트")
st.markdown("N-HiTS 딥러닝 모델과 실시간 DART 공시 기반의 퀀트 예측 결과를 제공합니다.")

if selected_company_name:
    company_data = df_pred[df_pred['name'] == selected_company_name].copy()

    if not company_data.empty:
        # 날짜 포맷 정리
        company_data['run_datetime'] = company_data['run_datetime'].astype(str)

        latest_pred = company_data.iloc[-1]
        current_price = latest_pred['current_close']
        predicted_price = latest_pred['predicted_close']
        target_date = latest_pred['target_date']

        price_diff = latest_pred['change']
        direction = latest_pred['direction']
        model_name = latest_pred['model']

        diff_percent = (price_diff / current_price) * 100

        # 핵심 지표
        col1, col2, col3, col4 = st.columns(4)
        col1.metric("현재 주가", f"{int(current_price):,} 원")
        col2.metric("N-HiTS 목표가", f"{int(predicted_price):,} 원", f"{price_diff:,.0f} 원 ({diff_percent:.2f}%)")
        col3.metric("예측 타겟 날짜", f"{target_date}")
        col4.metric("AI 예측 모델", f"{model_name}", f"예상 방향: {direction}")

        st.markdown("<br>", unsafe_allow_html=True)

        tab1, tab2, tab3 = st.tabs(["AI 주가 예측 차트", "실시간 공시 브리핑 (LLM)", "모델 & 데이터 정보"])

        with tab1:
            fig = go.Figure()

            # 1. 실제 주가 흐름
            fig.add_trace(go.Scatter(
                x=company_data['run_datetime'],
                y=company_data['current_close'],
                mode='lines+markers',
                line=dict(color='#1e293b', width=3),
                marker=dict(size=8, color='#1e293b'),
                name="실제 주가 흐름"
            ))

            # 2. 미래 예측 궤적
            x_pred = [company_data['run_datetime'].iloc[-1], target_date]
            y_pred = [current_price, predicted_price]

            fig.add_trace(go.Scatter(
                x=x_pred,
                y=y_pred,
                mode='lines+markers',
                line=dict(color='#ef4444' if price_diff > 0 else '#3b82f6', width=4, dash='dot'),
                marker=dict(size=12, color=['#1e293b', '#ef4444' if price_diff > 0 else '#3b82f6']),
                name="N-HiTS 목표가"
            ))

            fig.update_layout(
                title=f"<b>{selected_company_name} 주가 추세 및 모델 예측 비교</b>",
                xaxis_title="시간 (Timeline)",
                yaxis_title="가격 (KRW)",
                plot_bgcolor='rgba(0,0,0,0)',
                yaxis=dict(gridcolor='#e2e8f0'),
                legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
                height=450,
                margin=dict(l=20, r=20, t=40, b=20)
            )
            st.plotly_chart(fig, use_container_width=True)

        with tab2:
            st.markdown("#### DART & 뉴스 기반 AI 요약")
            st.info("실시간 시장 분석 브리핑이 곧 연동됩니다.")
            st.markdown(f"> **[{selected_keyword}]** 섹터 대장주인 **{selected_company_name}**의 최근 수주 공시 및 실적 발표를 분석 중입니다...")

        with tab3:
            st.markdown("#### N-HiTS 예측 원본 데이터 로그")
            st.dataframe(company_data, use_container_width=True)
    else:
        # 아직 이 종목에 대한 예측 기록이 없는 경우(예: step3를 아직 안 돌린 신규 매핑 종목)
        st.warning(f"'{selected_company_name}'에 대한 예측 데이터가 아직 없습니다. step3_predict_stock_price.py를 실행해주세요.")
