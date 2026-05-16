# 🏘️ AI Lead Scoring & Automation System

Hệ thống tự động chấm điểm và phân loại khách hàng tiềm năng (Lead Scoring) dành cho ngành Bất Động Sản. Ứng dụng tích hợp AI (Gemini) và Bộ quy tắc nghiệp vụ để tối ưu hóa quy trình chăm sóc khách hàng.

## ✨ Tính năng chính
- **Tự động hóa dữ liệu:** Kết nối trực tiếp với Google Sheets.
- **Chấm điểm thông minh:** 
  - **Quy tắc nhanh:** Chấm điểm dựa trên từ khóa (Biệt thự, Quận 1, Ngân sách > 20 tỷ...).
  - **AI Chuyên sâu:** Sử dụng Gemini 1.5 Flash để phân tích ngữ cảnh nhu cầu.
- **Human-in-the-loop:** Cho phép con người kiểm duyệt và chỉnh sửa kết quả trực tiếp trên Web App.
- **Báo cáo chuyên nghiệp:** Xuất dữ liệu đã xử lý ra file Excel để bàn giao ngay lập tức.

## 🚀 Hướng dẫn cài đặt và sử dụng

### 1. Chuẩn bị
- Cài đặt Python 3.9+
- File `lead_scoring_skill.md` (Chứa bộ quy tắc chấm điểm).

### 2. Cài đặt thư viện
Mở terminal và chạy lệnh:
```bash
pip install -r requirements.txt
```

### 3. Khởi chạy ứng dụng
Chạy lệnh sau để mở giao diện Web App trên trình duyệt:
```bash
streamlit run app_lead_scoring.py
```

### 4. Triển khai lên GitHub & Streamlit Cloud
1. Đưa các file sau lên repository GitHub của bạn:
   - `app_lead_scoring.py`
   - `requirements.txt`
   - `lead_scoring_skill.md`
2. Truy cập [Streamlit Cloud](https://share.streamlit.io/) và kết nối với repo GitHub vừa tạo.
3. Nhấn **Deploy**!

## 📄 Cấu trúc thư mục
```text
├── app_lead_scoring.py    # Mã nguồn chính của ứng dụng
├── requirements.txt       # Danh sách thư viện cần cài đặt
├── lead_scoring_skill.md  # Định nghĩa quy tắc chấm điểm
└── README.md              # Hướng dẫn sử dụng
```

---
*Phát triển bởi Antigravity AI Assistant.*
