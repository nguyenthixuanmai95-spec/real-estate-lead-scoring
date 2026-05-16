# Skill: Lead Scoring Automation for Real Estate

## 1. Mục tiêu (Objective)
Tự động hóa việc phân tích và chấm điểm tiềm năng của khách hàng (Lead Scoring) dựa trên mô tả nhu cầu thực tế, giúp đội ngũ kinh doanh ưu tiên chăm sóc các khách hàng VIP và loại bỏ các dữ liệu rác.

## 2. Nguồn dữ liệu đầu vào (Input Sources)
- **Google Sheets Link**: [Dữ liệu khách hàng](https://docs.google.com/spreadsheets/d/1StcpiSKHKYevnM2Jjqt_3KH90vld-ykSiMaRwteju6w/edit?gid=0#gid=0)
- **Cấu trúc bảng tính**:
  - `id`: Mã định danh khách hàng.
  - `ten_khach`: Tên khách hàng.
  - `sdt`: Số điện thoại.
  - `nhu_cau_mo_ta`: Nội dung quan trọng nhất để AI phân tích và chấm điểm.

## 3. Quy tắc chấm điểm (Scoring Logic)

### A. Nhóm Siêu Tiềm Năng (Cộng 50 điểm)
Cộng ngay 50 điểm nếu trong `nhu_cau_mo_ta` xuất hiện các yếu tố sau:
- **Ngân sách lớn**: Đề cập số tiền từ **20 tỷ trở lên** hoặc từ khóa: *"tài chính mạnh"*, *"không thành vấn đề"*.
- **Loại hình cao cấp**: *"Biệt thự đơn lập"*, *"Penthouse"*, *"Shophouse mặt đường lớn"*, *"Quỹ đất công nghiệp"*, *"Sàn văn phòng diện tích lớn"*.
- **Vị trí đắc địa**: *"Quận 1"*, *"Ven sông"*, *"Vinhomes Ocean Park"*, *"Phú Mỹ Hưng"*.
- **Đối tượng khách hàng**: *"Chủ doanh nghiệp"*, *"Nhà đầu tư chuyên nghiệp"*, *"Mua sỉ"*, *"Mua số lượng lớn"*.
- **Tính cấp thiết & Minh bạch**: *"Pháp lý chuẩn 100%"*, *"Sổ hồng riêng"*, *"Muốn gặp trực tiếp chủ đầu tư để đàm phán"*.

### B. Nhóm Rác / Không tiềm năng (Trừ 50 điểm)
Trừ ngay 50 điểm nếu phát hiện các dấu hiệu:
- **Yêu cầu phi thực tế**: Giá thấp vô lý (Ví dụ: Nhà Quận 1 giá 1-2 tỷ, nhà trung tâm có sân vườn giá vài trăm triệu).
- **Không có nhu cầu**: *"Nhầm số"*, *"Không có nhu cầu"*, *"Dữ liệu cũ"*, *"Nhầm ngành"*.
- **Thiếu thiện chí**: *"Hỏi giá cho vui"*, *"Chưa có ý định mua"*, *"Thái độ không hợp tác"*.
- **Spam/Quảng cáo**: Chứa nội dung về *"Bảo hiểm"*, *"Vay vốn"*, *"Mời chào dịch vụ khác"*.
- **Lỗi liên lạc**: *"Thuê bao"*, *"Gọi nhiều lần không bắt máy"*, *"Không phản hồi Zalo"*.

### C. Nhóm Tiềm Năng Trung Bình (Giữ nguyên hoặc Cộng ít: 0 - 10 điểm)
- Khách hàng tìm mua chung cư, nhà phố tầm trung (3-10 tỷ).
- Khách hàng cần vay ngân hàng, đang cân nhắc chính sách.
- Khách hàng có nhu cầu thực nhưng cần tư vấn thêm về pháp lý hoặc vị trí.

## 4. Hướng dẫn thực hiện cho AI (AI Instructions)
1. **Phân tích ngữ cảnh**: Đọc kỹ trường `nhu_cau_mo_ta`. Không chỉ tìm từ khóa mà phải hiểu ngữ cảnh (Ví dụ: "Tôi không muốn mua chung cư" -> Không được tính điểm chung cư).
2. **Tính toán điểm số**: Tổng hợp điểm cộng và điểm trừ để ra số điểm cuối cùng cho mỗi Lead.
3. **Phân loại**:
   - **Score >= 50**: Khách hàng VIP (Hot Lead).
   - **0 <= Score < 50**: Khách hàng tiềm năng (Warm Lead).
   - **Score < 0**: Khách hàng rác (Cold/Junk Lead).
4. **Trích xuất thông tin**: Ngoài điểm số, AI cần tóm tắt lý do chấm điểm (Ví dụ: "Cộng 50đ vì tìm mua Penthouse Quận 1").

## 5. Kết quả mong muốn (Expected Output)
Dữ liệu sau khi xử lý nên được trình bày dưới dạng bảng hoặc file Excel gồm các cột:
`id` | `ten_khach` | `nhu_cau_mo_ta` | `diem_tiem_nang` | `phan_loai` | `ly_do_cham_diem`
