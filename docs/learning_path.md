# Tám buổi, mỗi buổi khoảng60–90phút

1. Bảng/dòng/khóa: phân biệt trận nguồn với đội–trận.
2. SELECT, WHERE, LIKE, ORDER BY, LIMIT: tìm trận theo đội/ngày.
3. JOIN hai lần cùng bảng teams: nhãn sân nhà và sân khách.
4. UNION ALL, CASE, GROUP BY: biến hai đội thành hai góc nhìn, tính điểm.
5. LEFT JOIN, NULL: giữ đội chưa thi đấu tại mốc; thống kê thiếu.
6. CTE, ROW_NUMBER, LAG: phong độ theo ngày, không suy vòng đấu.
7. Transaction và ràng buộc: thử rollback trong SQLite tạm; nguồn thật chỉ đọc.
8. pandas, đối chiếu, bốn biểu đồ, ba nhận xét và Git.

Mỗi notebook: câu hỏi → dự đoán → SQL → giải thích → tự làm → kiểm tra.

## Bài Git để bạn tự làm

Issue: “Lọc lịch sử đội theo số bàn thắng tối thiểu”. Tiêu chí: nhận số nguyên không âm;0giữ tất cả; lọc theo gf của đội được chọn, không phải tổng bàn haiđội; trường hợp0kết quả hiển thị rõ; không thay dữ liệu. Viết kiểm thử0/2/sai đầu vào; sửa CLI/hàm; chạy unittest; `git diff`; `git add epl_lab/cli.py tests/`; `git commit -m "Add minimum goals filter to team history"`; `git push`. Đóng Issue khi đạt tiêu chí.
