# AI Kiếm Tiền

Một con AI được giao **0đ vốn, không hạn chót**, và một nhiệm vụ: **tự kiếm ra tiền thật, hợp pháp.**

Nó tự nghĩ ý tưởng, tự thử, tự đo kết quả, hỏng thì bỏ và thử cách khác. Mỗi ngày nó viết nhật ký công khai: hôm nay làm gì, hỏng gì, học được gì. Chạy tự động trên GitHub Actions, trang web hiện robot "đang làm / đang nghĩ / đang ngủ" cùng số tiền thật đã về.

## Luật chơi

- Vốn 0đ. Agent không chi đồng nào.
- Tự do sáng tạo ý tưởng và dùng mọi công cụ (kể cả bản dùng thử), miễn hợp pháp và an toàn.
- Tiền chỉ được tính khi người thật xác nhận từ sao kê (sổ cái nối băm, sửa lịch sử là bị phát hiện).
- 14 ngày liên tiếp không có đồng nào thì bắt buộc rà soát và đổi cách.
- Không spam, không lừa đảo, không bịa số liệu.

## Các cách nó đang thử

1. **Xin ủng hộ trên trang công khai** bằng nhật ký thật (có chút kịch tính cho vui).
2. **Dự đoán kết quả xổ số ngày mai**

## Chạy thử

```bash
python3 kiem-soat/test_vi.py && python3 cong-cu/test_cong_cu.py
cp thay-cap/tai-khoan-nhan.json.mau thay-cap/tai-khoan-nhan.json   # điền tài khoản nhận tiền
bash chay-luot.sh                                                  # một lượt (cần Gemini CLI + ffmpeg)
```

Chạy trên GitHub (miễn phí, repo công khai): xem `github/HUONG-DAN.md`. Dừng khẩn cấp: tạo tệp `DUNG`.

## Thư mục

`HIEN-PHAP.md` luật cho agent · `chinh-sach.json` quota · `kiem-soat/` sổ cái + quota · `cong-cu/` dựng trang, video, kiểm bài · `kinh-doanh/` chỗ làm việc của agent · `thay-cap/` phần của người vận hành · `ra/` đầu ra.

Không có gì bảo đảm nó ra tiền. Đây là một thí nghiệm công khai.
