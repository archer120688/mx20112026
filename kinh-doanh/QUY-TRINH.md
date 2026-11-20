# Quy trình mỗi ngày cho Việc 2 (Shopee)

1. **Chọn sản phẩm (tối đa 5/ngày, xin quota `san-pham`).** Tìm sản phẩm gia dụng (bếp, dọn dẹp, phòng tắm, lưu trữ) có người quan tâm thật: Google Trends, tìm kiếm web, bài công khai nói về đồ gia dụng được hỏi nhiều. Ghi bằng chứng nhu cầu (nguồn, ngày). Chỉ đọc trang công khai từng sản phẩm; không đọc được thì để thầy dán nội dung.
   Ghi `ra/can-tao-link/YYYY-MM-DD.csv`: `ma_san_pham,ten,url_goc,ly_do_hot`. Thầy tạo link affiliate rồi dán vào `thay-cap/link-affiliate.csv`.
2. **Soạn kịch bản (xin quota `video`).** Chỉ khi sản phẩm đã có link trong `thay-cap/link-affiliate.csv`. 20–40 giây, 5–7 cảnh, mỗi cảnh một ý lấy từ trang bán (công dụng, kích thước, chất liệu), mở bằng một câu hỏi người xem hay hỏi. Lưu `ra/cho-dang/NGÀY/<ma>/video.json` (cách viết ở đầu `cong-cu/lam-video.py`).
3. **Dựng video.** `python3 cong-cu/lam-video.py <video.json> <video.mp4>`. Cảnh cuối công khai hoa hồng tự thêm. Ảnh: chỉ ảnh thầy cung cấp hoặc kho miễn phí; ghi `nguon.txt`.
4. **Viết bài đăng (xin quota `bai-dang` cho từng nền tảng).** `bai-dang.md` có 4 mục: YouTube Shorts, Facebook, TikTok, mỗi mục một tiêu đề + mô tả + hashtag riêng, link affiliate đúng như trong `link-affiliate.csv`, câu công khai hoa hồng, không câu cấm.
5. **Kiểm.** `python3 cong-cu/kiem-bai.py`. Gói HỎNG thì sửa ngay. Chỉ gói ĐẠT mới báo thầy đăng.
6. **Báo thầy** trong "Cần thầy": đăng gói nào, và nhắc bật nhãn nội dung có tài trợ/tiếp thị của từng nền tảng khi đăng (YouTube: "có quảng cáo trả phí"; TikTok: "tiết lộ nội dung"; Facebook: ghi rõ trong mô tả).
7. **Đo (sau 3 và 7 ngày).** Thầy cho số từ trang quản lý kênh và báo cáo Shopee (lượt xem, lượt bấm, đơn, hoa hồng). Ghi vào `CO-HOI.md`. Dòng sản phẩm/kiểu video nào có lượt bấm thì làm thêm, không có thì bỏ.
