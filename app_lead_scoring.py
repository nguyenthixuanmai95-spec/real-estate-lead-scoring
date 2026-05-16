import streamlit as st
import pandas as pd
import google.generativeai as genai
import io
import time

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
    st.title("🚀 AI Lead Scoring & Automation System")
    st.subheader("Hệ thống chấm điểm khách hàng tiềm năng - Bất Động Sản")

    # --- Sidebar ---
    with st.sidebar:
        st.header("⚙️ Cấu hình")
        api_key = st.text_input("Gemini API Key", type="password", help="Lấy tại https://aistudio.google.com/app/apikey")
        gsheet_url = st.text_input("Google Sheet URL", "https://docs.google.com/spreadsheets/d/1StcpiSKHKYevnM2Jjqt_3KH90vld-ykSiMaRwteju6w/edit?gid=0#gid=0")
        
        if st.button("🔄 Tải dữ liệu"):
            try:
                # Convert share link to export link
                csv_url = gsheet_url.replace("/edit?gid=", "/export?format=csv&gid=").split("#")[0]
                if "/edit" in csv_url and "/export" not in csv_url:
                    csv_url = gsheet_url.replace("/edit", "/export?format=csv")
                
                df = pd.read_csv(csv_url)
                st.session_state['raw_data'] = df
                st.success("Tải dữ liệu thành công!")
            except Exception as e:
                st.error(f"Không thể tải dữ liệu: {e}")

    # --- Application Content ---
    if 'raw_data' in st.session_state:
        df = st.session_state['raw_data']
        
        col1, col2, col3 = st.columns(3)
        col1.markdown(f'<div class="metric-card"><h3>Tổng Lead</h3><h2>{len(df)}</h2></div>', unsafe_allow_html=True)
        
        st.write("### 📋 Dữ liệu thô từ Google Sheets")
        st.dataframe(df, use_container_width=True)

        if st.button("🧠 Chạy AI Chấm Điểm"):
            with open("lead_scoring_skill.md", "r", encoding="utf-8") as f:
                skill_content = f.read()
            
            scored_df = get_ai_score(api_key, df, skill_content)
            if scored_df is not None:
                st.session_state['scored_data'] = scored_df
                st.success("Đã chấm điểm xong!")

    if 'scored_data' in st.session_state:
        st.divider()
        st.write("### 🏆 Kết quả Chấm Điểm (AI + Human Review)")
        
        # Human-in-the-loop: Editable data editor
        edited_df = st.data_editor(
            st.session_state['scored_data'],
            use_container_width=True,
            num_rows="dynamic",
            column_config={
                "diem_tiem_nang": st.column_config.NumberColumn("Điểm", format="%d"),
                "phan_loai": st.column_config.SelectboxColumn("Phân loại", options=["VIP", "Tiềm năng", "Rác"]),
            }
        )
        st.session_state['scored_data'] = edited_df

        # --- Statistics & Export ---
        st.divider()
        c1, c2 = st.columns([2, 1])
        
        with c1:
            st.write("#### Phân bổ chất lượng Lead")
            summary = edited_df['phan_loai'].value_counts()
            st.bar_chart(summary)
            
        with c2:
            st.write("#### 📤 Xuất dữ liệu")
            
            # Export to Excel
            output = io.BytesIO()
            with pd.ExcelWriter(output, engine='openpyxl') as writer:
                edited_df.to_excel(writer, index=False, sheet_name='Lead_Scoring_Results')
            processed_data = output.getvalue()
            
            st.download_button(
                label="📥 Tải file Excel (.xlsx)",
                data=processed_data,
                file_name="lead_scoring_results.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            )

    else:
        st.info("Vui lòng tải dữ liệu và chạy AI để bắt đầu.")

if __name__ == "__main__":
    main()
