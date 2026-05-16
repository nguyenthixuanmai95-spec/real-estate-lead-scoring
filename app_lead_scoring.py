import streamlit as st
import pandas as pd
import google.generativeai as genai
import io
import time
import gspread
import json
import os

# --- CONFIGURATION & STYLING ---
st.set_page_config(page_title="AI Lead Scoring System", layout="wide")

# Premium CSS for Glassmorphism & Modern UI
st.markdown("""
    <style>
    .main {
        background: linear-gradient(135deg, #f5f7fa 0%, #c3cfe2 100%);
    }
    .stApp {
        background-color: transparent;
    }
    [data-testid="stSidebar"] {
        background-color: rgba(255, 255, 255, 0.8);
        backdrop-filter: blur(10px);
        border-right: 1px solid rgba(255, 255, 255, 0.2);
    }
    .metric-card {
        background: white;
        padding: 20px;
        border-radius: 15px;
        box-shadow: 0 4px 6px rgba(0,0,0,0.1);
        text-align: center;
        border-top: 5px solid #4A90E2;
    }
    .stButton>button {
        background-color: #4A90E2;
        color: white;
        border-radius: 10px;
        border: none;
        padding: 10px 24px;
        transition: all 0.3s;
    }
    .stButton>button:hover {
        background-color: #357ABD;
        transform: translateY(-2px);
        box-shadow: 0 4px 12px rgba(74, 144, 226, 0.4);
    }
    h1, h2, h3 {
        color: #2C3E50;
        font-family: 'Inter', sans-serif;
    }
    </style>
""", unsafe_allow_html=True)

# --- RULE-BASED SCORING LOGIC (NO API KEY) ---
def rule_based_scoring(df):
    results = []
    
    vip_keywords = [
        "20 tỷ", "tài chính mạnh", "không thành vấn đề", 
        "Biệt thự đơn lập", "Penthouse", "Shophouse", "Quỹ đất công nghiệp", "Sàn văn phòng diện tích lớn",
        "Quận 1", "Ven sông", "Vinhomes Ocean Park", "Phú Mỹ Hưng",
        "Chủ doanh nghiệp", "Nhà đầu tư chuyên nghiệp", "Mua sỉ", "Mua số lượng lớn",
        "Pháp lý chuẩn", "Sổ hồng riêng", "Gặp trực tiếp chủ đầu tư"
    ]
    
    junk_keywords = [
        "Nhầm số", "Không có nhu cầu", "Dữ liệu cũ", "Nhầm ngành",
        "Hỏi giá cho vui", "Chưa có ý định mua", "Thái độ không hợp tác",
        "Bảo hiểm", "Vay vốn", "Mời chào dịch vụ",
        "Thuê bao", "Không bắt máy", "Không phản hồi Zalo"
    ]

    for idx, row in df.iterrows():
        score = 0
        reasons = []
        desc = str(row['nhu_cau_mo_ta']).lower()
        
        # Check VIP
        for kw in vip_keywords:
            if kw.lower() in desc:
                score += 50
                reasons.append(f"Khớp từ khóa VIP: {kw}")
                break # Only add 50 once for VIP status usually, or could be cumulative
        
        # Check Junk
        for kw in junk_keywords:
            if kw.lower() in desc:
                score -= 50
                reasons.append(f"Khớp dấu hiệu Rác: {kw}")
                break
        
        # Check Unrealistic (Simple logic)
        if "quận 1" in desc and ("1 tỷ" in desc or "2 tỷ" in desc):
            score -= 50
            reasons.append("Yêu cầu phi thực tế (Quận 1 giá rẻ)")

        # Classification
        if score >= 50:
            phan_loai = "VIP"
        elif score < 0:
            phan_loai = "Rác"
        else:
            phan_loai = "Tiềm năng"
            
        results.append({
            "diem_tiem_nang": score,
            "phan_loai": phan_loai,
            "ly_do_cham_diem": "; ".join(reasons) if reasons else "Khách hàng tầm trung"
        })
        
    res_df = pd.DataFrame(results)
    return pd.concat([df, res_df], axis=1)

# --- AI SCORING LOGIC ---
def get_ai_score(api_key, leads_df, skill_content):
    if not api_key:
        st.error("Vui lòng nhập Gemini API Key trong Sidebar!")
        return None
    
    genai.configure(api_key=api_key)
    model = genai.GenerativeModel('gemini-1.5-flash')
    
    results = []
    progress_bar = st.progress(0)
    status_text = st.empty()
    
    for idx, row in leads_df.iterrows():
        status_text.text(f"Đang xử lý Lead {idx+1}/{len(leads_df)}: {row['ten_khach']}")
        
        prompt = f"""
        Dựa trên bộ quy tắc chấm điểm sau đây:
        {skill_content}
        
        Hãy phân tích nội dung nhu cầu của khách hàng sau:
        Tên: {row['ten_khach']}
        Mô tả nhu cầu: {row['nhu_cau_mo_ta']}
        
        Trả về kết quả dưới dạng JSON duy nhất với các trường:
        - "diem_tiem_nang": (số nguyên)
        - "phan_loai": (VIP, Tiềm năng, Rác)
        - "ly_do_cham_diem": (chuỗi giải thích ngắn gọn)
        
        Lưu ý: Chỉ trả về JSON, không kèm văn bản khác.
        """
        
        try:
            response = model.generate_content(prompt)
            # Simple cleaning of response text if needed
            res_text = response.text.replace("```json", "").replace("```", "").strip()
            import json
            res_json = json.loads(res_text)
            results.append(res_json)
        except Exception as e:
            results.append({
                "diem_tiem_nang": 0,
                "phan_loai": "Lỗi",
                "ly_do_cham_diem": f"Lỗi xử lý: {str(e)}"
            })
        
        progress_bar.progress((idx + 1) / len(leads_df))
        time.sleep(0.5) # Avoid rate limits
        
    progress_bar.empty()
    status_text.empty()
    
    res_df = pd.DataFrame(results)
    return pd.concat([leads_df, res_df], axis=1)

# --- MAIN APP ---
def main():
    st.markdown('<h1 style="color: #1E3A8A;">🏘️ Hệ thống AI Lead Scoring & Automation</h1>', unsafe_allow_html=True)
    st.markdown('<p style="font-size: 1.2rem; color: #4B5563;">Giải pháp tự động phân loại khách hàng tiềm năng cho ngành Bất Động Sản</p>', unsafe_allow_html=True)

    # --- Sidebar ---
    with st.sidebar:
        st.image("https://img.icons8.com/fluency/96/artificial-intelligence.png", width=80)
        st.header("⚙️ Cấu hình Hệ thống")
        
        gsheet_url = st.text_input("🔗 Google Sheet URL", "https://docs.google.com/spreadsheets/d/1StcpiSKHKYevnM2Jjqt_3KH90vld-ykSiMaRwteju6w/edit?gid=0#gid=0")
        
        with st.expander("🛠️ Cài đặt nâng cao (AI Gemini)"):
            api_key = st.text_input("Gemini API Key", type="password", help="Chỉ điền nếu muốn dùng AI phân tích sâu hơn")
            
        st.divider()
        st.info("💡 **Mẹo:** Hệ thống mặc định sử dụng bộ quy tắc nghiệp vụ (Rule-based) để chấm điểm ngay lập tức mà không cần API Key.")

    # --- Data Loading Logic ---
    def load_data_from_gsheet(url):
        # 1. Thử dùng Service Account (gspread + google-auth)
        try:
            from google.oauth2 import service_account
            
            scope = ['https://www.googleapis.com/auth/spreadsheets', 'https://www.googleapis.com/auth/drive']
            creds_info = None
            
            # Ưu tiên lấy từ Secrets (cho Cloud)
            if "gcp_service_account" in st.secrets:
                creds_info = json.loads(st.secrets["gcp_service_account"])
            # Fallback lấy từ file local
            elif os.path.exists("credentials.json"):
                with open("credentials.json", "r") as f:
                    creds_info = json.load(f)
            
            if creds_info:
                # Fix lỗi định dạng private_key phổ biến
                if 'private_key' in creds_info:
                    creds_info['private_key'] = creds_info['private_key'].replace('\\n', '\n')
                
                creds = service_account.Credentials.from_service_account_info(creds_info, scopes=scope)
                client = gspread.authorize(creds)
                
                # Trích xuất ID từ URL
                sheet_id = url.split("/d/")[1].split("/")[0]
                sheet = client.open_by_key(sheet_id).sheet1
                data = sheet.get_all_records()
                return pd.DataFrame(data)
        except Exception as e:
            st.sidebar.warning(f"⚠️ Xác thực Service Account thất bại: {e}")

        # 2. Fallback: Thử dùng URL công khai (CSV export)
        try:
            csv_url = url.replace("/edit?gid=", "/export?format=csv&gid=").split("#")[0]
            if "/edit" in csv_url and "/export" not in csv_url:
                csv_url = url.replace("/edit", "/export?format=csv")
            return pd.read_csv(csv_url)
        except Exception as e:
            st.error(f"❌ Lỗi kết nối Google Sheets: {e}")
            st.info("💡 **Hướng dẫn:**\n1. Hãy đảm bảo đã Share quyền **Viewer** cho email robot: `id-lead-scoring-robot-302@plenary-charge-496514-e0.iam.gserviceaccount.com` \n2. Hoặc hãy chỉnh chế độ của Google Sheet sang: **'Bất kỳ ai có đường liên kết đều có thể xem'** (Anyone with link can view).")
            return None

    # Control loading via session state and buttons
    if gsheet_url:
        if 'raw_data' not in st.session_state or st.sidebar.button("🔄 Tải lại dữ liệu"):
            with st.spinner("Đang tải dữ liệu từ Google Sheets..."):
                df = load_data_from_gsheet(gsheet_url)
                if df is not None:
                    st.session_state['raw_data'] = df
                    st.session_state.pop('scored_data', None) # Clear old scores on reload
                    st.rerun()

    # --- Application Content ---
    if 'raw_data' in st.session_state:
        df = st.session_state['raw_data']
        
        # Dashboard Overview
        c1, c2, c3 = st.columns(3)
        with c1:
            st.markdown(f'<div class="metric-card"><h3>Tổng số Lead</h3><h2 style="color: #2563EB;">{len(df)}</h2></div>', unsafe_allow_html=True)
        
        st.write("### 📋 Danh sách khách hàng mới")
        st.dataframe(df, use_container_width=True, height=300)

        # Action Buttons
        col_btn1, col_btn2 = st.columns(2)
        
        with col_btn1:
            if st.button("⚡ Chấm Điểm Nhanh (Quy Tắc)", use_container_width=True):
                scored_df = rule_based_scoring(df)
                st.session_state['scored_data'] = scored_df
                st.success("✅ Đã hoàn thành chấm điểm quy tắc!")

        with col_btn2:
            if st.button("🧠 Chấm Điểm Chuyên Sâu (AI)", use_container_width=True):
                if not api_key:
                    st.warning("⚠️ Vui lòng nhập Gemini API Key trong phần 'Cài đặt nâng cao' để dùng tính năng này.")
                else:
                    with open("lead_scoring_skill.md", "r", encoding="utf-8") as f:
                        skill_content = f.read()
                    scored_df = get_ai_score(api_key, df, skill_content)
                    if scored_df is not None:
                        st.session_state['scored_data'] = scored_df
                        st.success("✅ Đã hoàn thành chấm điểm bằng AI!")

    # --- Results & Review ---
    if 'scored_data' in st.session_state:
        st.divider()
        st.write("### 🏆 Kết quả Phân Loại & Chấm Điểm")
        st.caption("Bạn có thể chỉnh sửa trực tiếp vào bảng bên dưới để điều chỉnh kết quả nếu cần (Human-in-the-loop).")
        
        # Highlighted Data Editor
        edited_df = st.data_editor(
            st.session_state['scored_data'],
            use_container_width=True,
            num_rows="dynamic",
            column_config={
                "diem_tiem_nang": st.column_config.NumberColumn("Điểm", format="%d", help="Điểm tiềm năng (0-100)"),
                "phan_loai": st.column_config.SelectboxColumn("Phân loại", options=["VIP", "Tiềm năng", "Rác"]),
                "ly_do_cham_diem": st.column_config.TextColumn("Lý do/Ghi chú", width="large")
            }
        )
        st.session_state['scored_data'] = edited_df

        # --- Statistics & Export ---
        st.write("#### 📊 Thống kê & Báo cáo")
        c_stat, c_export = st.columns([2, 1])
        
        with c_stat:
            summary = edited_df['phan_loai'].value_counts()
            st.bar_chart(summary)
            
        with c_export:
            st.write("#### 📤 Xuất dữ liệu Bàn giao")
            
            # Export to Excel
            output = io.BytesIO()
            with pd.ExcelWriter(output, engine='openpyxl') as writer:
                edited_df.to_excel(writer, index=False, sheet_name='Bao_cao_Lead_Scoring')
            processed_data = output.getvalue()
            
            st.download_button(
                label="📥 Tải file Excel Bàn Giao (.xlsx)",
                data=processed_data,
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            )

    else:
        st.info("Vui lòng tải dữ liệu và chạy AI để bắt đầu.")

if __name__ == "__main__":
    main()
