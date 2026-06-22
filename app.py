import streamlit as st
import pandas as pd
import plotly.express as px
import requests
from datetime import datetime

# --- 페이지 설정 ---
st.set_page_config(page_title="팀 예산 관리 시스템", page_icon="📊", layout="wide")

# --- 구글 시트 연결 (Apps Script Web App URL) ---
# .streamlit/secrets.toml 파일에 설정된 웹 앱 URL을 가져옵니다.
WEB_APP_URL = "https://script.google.com/macros/s/AKfycbzzFcZL5L0qr67eUC2nrKFiuh7ZQpVGGpnZ7I_L_rHhXLPgzjXMF3aKvskKIf3yj5c/exec"

# --- 데이터 로드 함수 ---
@st.cache_data(ttl=5) # 5초 동안 캐시 유지
def load_data():
    try:
        response = requests.get(WEB_APP_URL)
        if response.status_code == 200:
            data = response.json()
            if data and "error" not in data:
                return pd.DataFrame(data)
        return pd.DataFrame(columns=["ID", "연월", "팀원", "항목", "금액"])
    except Exception as e:
        st.error(f"데이터를 불러오는 중 오류가 발생했습니다. Web App URL을 확인해주세요.\n\n오류 내용: {e}")
        return pd.DataFrame(columns=["ID", "연월", "팀원", "항목", "금액"])

# --- 데이터 저장 함수 ---
def save_data(df):
    try:
        # DataFrame을 배열(List) 형태로 변환하여 전송
        data_values = df[["ID", "연월", "팀원", "항목", "금액"]].values.tolist() if not df.empty else []
        payload = {
            "action": "overwrite",
            "data": data_values
        }
        response = requests.post(WEB_APP_URL, json=payload)
        
        if response.status_code == 200:
            st.cache_data.clear() # 캐시 초기화하여 최신 데이터 반영
            return True
        return False
    except Exception as e:
        st.error(f"데이터 저장 중 오류 발생: {e}")
        return False

# 데이터 로드
df = load_data()

# --- 헤더 ---
st.title("📊 팀 예산 관리 시스템")
st.markdown("부장님 보고용 월별 예산 취합 및 대시보드 (Google Sheets 연동)")

# --- 탭 구성 ---
tab1, tab2 = st.tabs(["📝 데이터 입력 및 관리", "📈 전체 대시보드"])

# --- 탭 1: 데이터 입력 ---
with tab1:
    col1, col2 = st.columns([1, 2])
    
    with col1:
        st.subheader("내역 입력")
        with st.form("budget_form", clear_on_submit=True):
            member = st.selectbox("팀원 선택", ["부장님", "팀원1", "팀원2", "팀원3", "팀원4"])
            
            # 기본값을 현재 연월로 설정
            current_date = datetime.now()
            default_month = f"{current_date.year}-{current_date.month:02d}"
            
            # HTML의 input type="month"를 대체하기 위한 문자열 입력 (혹은 selectbox 활용 가능)
            # 여기서는 편의상 YYYY-MM 형식의 문자열 입력을 받습니다.
            month = st.text_input("해당 연월 (YYYY-MM 형식)", value=default_month)
            
            category = st.selectbox("예산 항목", ["수선유지비", "비품", "개량공사"])
            amount = st.number_input("사용 금액 (원)", min_value=0, step=1000)
            
            submit_button = st.form_submit_button("기록 저장하기", use_container_width=True)
            
            if submit_button:
                if not month or amount <= 0:
                    st.warning("연월과 금액을 올바르게 입력해주세요.")
                else:
                    new_id = int(datetime.now().timestamp())
                    new_data = pd.DataFrame([{
                        "ID": new_id, 
                        "연월": month, 
                        "팀원": member, 
                        "항목": category, 
                        "금액": amount
                    }])
                    
                    if df.empty:
                        updated_df = new_data
                    else:
                        updated_df = pd.concat([new_data, df], ignore_index=True)
                    
                    save_data(updated_df)
                    st.success("예산 데이터가 정상적으로 구글 시트에 기록되었습니다.")
                    st.rerun()

    with col2:
        st.subheader("최근 입력 내역 관리")
        st.markdown("표에서 직접 데이터를 수정하거나 선택하여 행을 삭제할 수 있습니다. 변경 후에는 저장됩니다.")
        
        if not df.empty:
            # st.data_editor를 사용하여 시트 데이터 직접 수정 및 삭제 기능 제공
            edited_df = st.data_editor(
                df,
                num_rows="dynamic", # 행 추가/삭제 허용
                use_container_width=True,
                hide_index=True,
                column_config={
                    "ID": st.column_config.NumberColumn(disabled=True), # ID는 수정 불가
                    "금액": st.column_config.NumberColumn(format="%d ₩")
                }
            )
            
            # 데이터가 변경되었는지 확인하고 저장 버튼 표시
            if not df.equals(edited_df):
                if st.button("변경사항 구글 시트에 저장", type="primary"):
                    save_data(edited_df)
                    st.success("수정/삭제된 데이터가 구글 시트에 반영되었습니다.")
                    st.rerun()
        else:
            st.info("등록된 데이터가 없습니다.")

# --- 탭 2: 대시보드 ---
with tab2:
    if df.empty:
        st.info("대시보드를 구성할 데이터가 없습니다. 먼저 데이터를 입력해주세요.")
    else:
        # 데이터 타입 정리
        df['금액'] = pd.to_numeric(df['금액'], errors='coerce').fillna(0)
        
        # 상단 KPI 지표
        total_amount = df['금액'].sum()
        record_count = len(df)
        
        if not df.empty:
            top_category_series = df.groupby('항목')['금액'].sum()
            if not top_category_series.empty:
                top_category = top_category_series.idxmax()
                top_category_amount = top_category_series.max()
                top_category_text = f"{top_category} ({top_category_amount:,.0f}원)"
            else:
                top_category_text = "-"
        else:
            top_category_text = "-"

        col1, col2, col3 = st.columns(3)
        col1.metric("전체 누적 사용액", f"{total_amount:,.0f}원")
        col2.metric("최대 사용 항목", top_category_text)
        col3.metric("총 데이터 건수", f"{record_count}건")
        
        st.divider()

        # 차트 영역
        col_chart1, col_chart2 = st.columns(2)
        
        with col_chart1:
            st.subheader("🏠 항목별 예산 분포")
            cat_sum = df.groupby('항목')['금액'].sum().reset_index()
            fig_pie = px.pie(cat_sum, values='금액', names='항목', hole=0.4, 
                             color_discrete_sequence=px.colors.qualitative.Pastel)
            st.plotly_chart(fig_pie, use_container_width=True)
            
        with col_chart2:
            st.subheader("👥 팀원별 누적 사용액")
            mem_sum = df.groupby('팀원')['금액'].sum().reset_index()
            fig_bar = px.bar(mem_sum, x='팀원', y='금액', text_auto='.2s',
                             color_discrete_sequence=['#60a5fa'])
            fig_bar.update_traces(textfont_size=12, textangle=0, textposition="outside", cliponaxis=False)
            fig_bar.update_layout(xaxis_title="", yaxis_title="금액 (원)")
            st.plotly_chart(fig_bar, use_container_width=True)

        st.divider()

        # 요약 테이블 (피벗 테이블)
        st.subheader("📅 월별/항목별 요약 테이블 (취합본)")
        pivot_df = pd.pivot_table(df, values='금액', index='연월', columns='항목', aggfunc='sum', fill_value=0)
        
        # 합계 열 추가
        pivot_df['합계'] = pivot_df.sum(axis=1)
        
        # 최신 월이 위로 오도록 정렬
        pivot_df = pivot_df.sort_index(ascending=False)
        
        # 인덱스 리셋하여 '연월'을 일반 열로 변환
        pivot_df = pivot_df.reset_index()
        
        st.dataframe(
            pivot_df,
            use_container_width=True,
            hide_index=True,
            column_config={
                "합계": st.column_config.NumberColumn(format="%d ₩", width="medium"),
                # 존재하는 항목 열들에 대해서만 포맷 적용 (동적 처리)
                **{col: st.column_config.NumberColumn(format="%d") for col in pivot_df.columns if col not in ['연월', '합계']}
            }
        )
