import streamlit as st
import pandas as pd
import google.generativeai as genai
import io
import time
import gspread
import json
import os
from google.oauth2 import service_account

# --- CONFIGURATION & STYLING ---
st.set_page_config(
    page_title="MindX AI Lead Scoring - Premium Dashboard",
    page_icon="💎",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS for Premium Look
st.markdown("""
    <style>
    /* Main Background */
    .stApp {
        background: linear-gradient(135deg, #0f172a 0%, #1e293b 100%);
        color: #f8fafc;
    }
    
    /* Sidebar Styling */
    [data-testid="stSidebar"] {
        background-color: rgba(15, 23, 42, 0.95);
        border-right: 1px solid rgba(255, 255, 255, 0.1);
    }
    
    /* Glassmorphism Cards */
    .metric-card {
        background: rgba(255, 255, 255, 0.05);
        backdrop-filter: blur(10px);
        padding: 25px;
        border-radius: 20px;
        border: 1px solid rgba(255, 255, 255, 0.1);
        text-align: center;
        transition: transform 0.3s ease;
    }
    .metric-card:hover {
        transform: translateY(-5px);
        background: rgba(255, 255, 255, 0.08);
        border-color: rgba(245, 158, 11, 0.5);
    }
    
    /* Typography */
    h1, h2, h3 {
        font-family: 'Inter', sans-serif;
        font-weight: 700;
        letter-spacing: -0.025em;
    }
    
    /* Buttons */
    .stButton>button {
        border-radius: 12px;
        font-weight: 600;
        padding: 0.6rem 1.5rem;
        transition: all 0.2s ease;
        border: none;
    }
    
    /* Tables */
    .stDataFrame {
        border-radius: 15px;
        overflow: hidden;
    }
    
    /* Custom Banner Container */
    .banner-container {
        width: 100%;
        border-radius: 20px;
        overflow: hidden;
        margin-bottom: 2rem;
        box-shadow: 0 10px 30px rgba(0,0,0,0.5);
    }
    
    /* Metric Values */
    .metric-value {
        font-size: 2.5rem;
        font-weight: 800;
        margin: 10px 0;
    }
    .metric-label {
        color: #94a3b8;
        font-size: 0.9rem;
        text-transform: uppercase;
        letter-spacing: 0.1em;
    }
    </style>
""", unsafe_allow_html=True)

# --- UTILITY FUNCTIONS ---

def load_data_securely(url):
    """
    Kết nối an toàn tới Google Sheets (Private) qua Service Account.
    Hỗ trợ cả Streamlit Secrets và file credentials.json cục bộ.
    """
    try:
        scope = ['https://www.googleapis.com/auth/spreadsheets', 'https://www.googleapis.com/auth/drive']
        creds_info = None
        
        # 1. Kiểm tra trong Streamlit Secrets (Ưu tiên cho Cloud)
        if "gcp_service_account" in st.secrets:
            raw_creds = st.secrets["gcp_service_account"]
            creds_info = json.loads(raw_creds) if isinstance(raw_creds, str) else dict(raw_creds)
        # 2. Kiểm tra file credentials.json (Dùng cho local development)
        elif os.path.exists("credentials.json"):
            with open("credentials.json", "r", encoding="utf-8") as f:
                creds_info = json.load(f)
        
        if creds_info:
            info_dict = dict(creds_info)
            # Chuẩn hóa private_key (quan trọng cho PEM format)
            if 'private_key' in info_dict:
                pk = str(info_dict['private_key']).replace('\\n', '\n')
                # Đảm bảo định dạng PEM chuẩn
                pk = pk.strip()
                if "-----BEGIN PRIVATE KEY-----" not in pk:
                    pk = "-----BEGIN PRIVATE KEY-----\n" + pk
                if "-----END PRIVATE KEY-----" not in pk:
                    pk = pk + "\n-----END PRIVATE KEY-----"
                info_dict['private_key'] = pk
            
            creds = service_account.Credentials.from_service_account_info(info_dict, scopes=scope)
            client = gspread.authorize(creds)
            
            # Trích xuất Sheet ID từ URL
            try:
                sheet_id = url.split("/d/")[1].split("/")[0]
                sheet = client.open_by_key(sheet_id).get_worksheet(0)
                return pd.DataFrame(sheet.get_all_records())
            except Exception as e:
                st.sidebar.error(f"❌ Lỗi truy cập Sheet ID: {e}")
                return None
        else:
            st.sidebar.warning("⚠️ Không tìm thấy cấu hình Service Account.")
            return None
            
    except Exception as e:
        st.sidebar.error(f"❌ Lỗi xác thực Service Account: {e}")
        return None

def rule_based_scoring(df):
    results = []
    # Các quy tắc dựa trên file lead_scoring_skill.md
    vip_keywords = ["20 tỷ", "tài chính mạnh", "không thành vấn đề", "biệt thự", "penthouse", "shophouse", "vinhomes", "phú mỹ hưng", "chủ doanh nghiệp", "mua sỉ"]
    junk_keywords = ["nhầm số", "không có nhu cầu", "dữ liệu cũ", "hỏi giá cho vui", "bảo hiểm", "vay vốn", "thuê bao"]

    for idx, row in df.iterrows():
        score = 0
        reasons = []
        desc = str(row['nhu_cau_mo_ta']).lower()
        
        # Logic VIP
        for kw in vip_keywords:
            if kw in desc:
                score += 50
                reasons.append(f"VIP Keyword: {kw}")
                break
        
        # Logic Junk
        for kw in junk_keywords:
            if kw in desc:
                score -= 50
                reasons.append(f"Junk Sign: {kw}")
                break
        
        # Phân loại
        phan_loai = "VIP" if score >= 50 else ("Rác" if score < 0 else "Tiềm năng")
        
        results.append({
            "diem_tiem_nang": score,
            "phan_loai": phan_loai,
            "ly_do_cham_diem": "; ".join(reasons) if reasons else "Khách hàng tiêu chuẩn"
        })
        
    return pd.concat([df, pd.DataFrame(results)], axis=1)

def get_ai_score(api_key, leads_df, skill_content):
    if not api_key:
        st.error("Vui lòng nhập Gemini API Key!")
        return None
    
    genai.configure(api_key=api_key)
    model = genai.GenerativeModel('gemini-1.5-flash')
    
    results = []
    progress_bar = st.progress(0)
    status_text = st.empty()
    
    for idx, row in leads_df.iterrows():
        status_text.text(f"🤖 AI đang phân tích Lead {idx+1}/{len(leads_df)}...")
        prompt = f"Dựa trên quy tắc:\n{skill_content}\n\nPhân tích Lead:\n{row['ten_khach']} - {row['nhu_cau_mo_ta']}\n\nTrả về JSON: diem_tiem_nang (int), phan_loai (VIP/Tiềm năng/Rác), ly_do_cham_diem (string). Chỉ JSON."
        
        try:
            response = model.generate_content(prompt)
            res_text = response.text.replace("```json", "").replace("```", "").strip()
            results.append(json.loads(res_text))
        except:
            results.append({"diem_tiem_nang": 0, "phan_loai": "Lỗi", "ly_do_cham_diem": "Lỗi AI"})
        
        progress_bar.progress((idx + 1) / len(leads_df))
    
    progress_bar.empty()
    status_text.empty()
    return pd.concat([leads_df, pd.DataFrame(results)], axis=1)

# --- MAIN APPLICATION ---

def main():
    # Banner & Header
    # Lấy đường dẫn banner đã generate (giả sử file này tồn tại trong folder)
    banner_path = next((f for f in os.listdir(".") if "lead_scoring_banner" in f), None)
    if banner_path:
        st.image(banner_path, use_container_width=True)
    else:
        st.markdown('<div style="height: 150px; background: linear-gradient(90deg, #1e293b, #4f46e5); border-radius: 20px; display: flex; align-items: center; justify-content: center;"><h1 style="color: white; margin: 0;">💎 AI LEAD SCORING SYSTEM</h1></div>', unsafe_allow_html=True)

    st.markdown("<br>", unsafe_allow_html=True)

    # Sidebar
    with st.sidebar:
        st.title("⚙️ Cấu hình Hệ thống")
        gsheet_url = st.text_input("🔗 Link Google Sheet (Private)", "https://docs.google.com/spreadsheets/d/1StcpiSKHKYevnM2Jjqt_3KH90vld-ykSiMaRwteju6w/edit#gid=0")
        
        with st.expander("🔑 AI Settings"):
            api_key = st.text_input("Gemini API Key", type="password")
            
        st.divider()
        st.markdown("### 🛡️ Trạng thái bảo mật")
        if "gcp_service_account" in st.secrets or os.path.exists("credentials.json"):
            st.success("✅ Đã kết nối Service Account")
        else:
            st.warning("⚠️ Chế độ Công khai (Kém bảo mật)")
            st.info("Để dùng Sheet Riêng tư: \n1. Tạo Service Account trên Google Cloud\n2. Share Sheet với mail service account\n3. Thêm JSON vào Secrets.")

        if st.button("🔄 Làm mới dữ liệu", use_container_width=True):
            st.session_state.clear()
            st.rerun()

    # Data Loading
    if 'raw_data' not in st.session_state:
        with st.spinner("Đang tải dữ liệu từ Google Sheets..."):
            df = load_data_securely(gsheet_url)
            if df is not None:
                st.session_state['raw_data'] = df
            else:
                st.stop()

    df = st.session_state['raw_data']

    # --- DASHBOARD SECTION ---
    st.markdown("## 📊 Lead Insights Dashboard")
    
    # Calculate Metrics
    total_leads = len(df)
    scored_df = st.session_state.get('scored_data', None)
    
    c1, c2, c3, c4 = st.columns(4)
    
    with c1:
        st.markdown(f"""<div class="metric-card"><div class="metric-label">Tổng Lead</div><div class="metric-value" style="color: #60a5fa;">{total_leads}</div></div>""", unsafe_allow_html=True)
    
    if scored_df is not None:
        vip_count = len(scored_df[scored_df['phan_loai'] == 'VIP'])
        pot_count = len(scored_df[scored_df['phan_loai'] == 'Tiềm năng'])
        junk_count = len(scored_df[scored_df['phan_loai'] == 'Rác'])
        
        with c2:
            st.markdown(f"""<div class="metric-card"><div class="metric-label">Khách VIP</div><div class="metric-value" style="color: #fbbf24;">{vip_count}</div></div>""", unsafe_allow_html=True)
        with c3:
            st.markdown(f"""<div class="metric-card"><div class="metric-label">Tiềm năng</div><div class="metric-value" style="color: #34d399;">{pot_count}</div></div>""", unsafe_allow_html=True)
        with c4:
            st.markdown(f"""<div class="metric-card"><div class="metric-label">Khách Rác</div><div class="metric-value" style="color: #f87171;">{junk_count}</div></div>""", unsafe_allow_html=True)
    else:
        with c2: st.markdown(f"""<div class="metric-card"><div class="metric-label">Khách VIP</div><div class="metric-value">--</div></div>""", unsafe_allow_html=True)
        with c3: st.markdown(f"""<div class="metric-card"><div class="metric-label">Tiềm năng</div><div class="metric-value">--</div></div>""", unsafe_allow_html=True)
        with c4: st.markdown(f"""<div class="metric-card"><div class="metric-label">Khách Rác</div><div class="metric-value">--</div></div>""", unsafe_allow_html=True)

    st.markdown("<br>", unsafe_allow_html=True)

    # --- TABS FOR WORKFLOW ---
    tab1, tab2, tab3 = st.tabs(["📥 Dữ liệu thô", "⚡ Xử lý thông minh", "📋 Báo cáo & Xuất file"])

    with tab1:
        st.markdown("### 📄 Danh sách khách hàng mới cập nhật")
        st.dataframe(df, use_container_width=True)

    with tab2:
        st.markdown("### 🧠 Lựa chọn phương thức phân tích")
        col_btn1, col_btn2 = st.columns(2)
        
        with col_btn1:
            st.info("Phù hợp cho dữ liệu lớn, cần kết quả tức thì dựa trên từ khóa cố định.")
            if st.button("🔥 CHẤM ĐIỂM QUY TẮC (FAST)", use_container_width=True):
                st.session_state['scored_data'] = rule_based_scoring(df)
                st.rerun()
                
        with col_btn2:
            st.info("Sử dụng AI Gemini 1.5 để hiểu sâu ngữ cảnh và nhu cầu thực tế.")
            if st.button("🤖 CHẤM ĐIỂM AI (ADVANCED)", use_container_width=True):
                if api_key:
                    with open("lead_scoring_skill.md", "r", encoding="utf-8") as f:
                        skill = f.read()
                    st.session_state['scored_data'] = get_ai_score(api_key, df, skill)
                    st.rerun()
                else:
                    st.error("Vui lòng nhập API Key ở Sidebar!")

    with tab3:
        if scored_df is not None:
            st.markdown("### 🏆 Kết quả phân loại & Audit")
            
            # Interactive Editor
            edited_df = st.data_editor(
                scored_df,
                use_container_width=True,
                column_config={
                    "diem_tiem_nang": st.column_config.NumberColumn("Điểm", format="%d"),
                    "phan_loai": st.column_config.SelectboxColumn("Loại", options=["VIP", "Tiềm năng", "Rác"]),
                    "ly_do_cham_diem": st.column_config.TextColumn("Lý do chi tiết", width="large")
                }
            )
            st.session_state['scored_data'] = edited_df

            st.divider()
            
            # Export Logic
            col_exp1, col_exp2 = st.columns([2, 1])
            with col_exp1:
                # Simple Bar Chart for distribution
                dist = edited_df['phan_loai'].value_counts()
                st.bar_chart(dist)
            
            with col_exp2:
                st.markdown("#### 📥 Xuất báo cáo chuyên nghiệp")
                output = io.BytesIO()
                with pd.ExcelWriter(output, engine='openpyxl') as writer:
                    edited_df.to_excel(writer, index=False, sheet_name='LeadScoringReport')
                
                st.download_button(
                    label="📥 Tải File Excel (.xlsx)",
                    data=output.getvalue(),
                    file_name="Lead_Scoring_Premium_Report.xlsx",
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                    use_container_width=True
                )
                st.success("Dữ liệu đã sẵn sàng để bàn giao cho Sales!")
        else:
            st.info("Chưa có dữ liệu đã chấm điểm. Vui lòng thực hiện ở tab 'Xử lý thông minh'.")

if __name__ == "__main__":
    main()
