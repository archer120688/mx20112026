# Chạy trên GitHub Actions (không tốn điện, không tốn phí)

Repo **công khai** thì GitHub Actions và GitHub Pages miễn phí, không giới hạn phút. Repo riêng tư chỉ có 2.000 phút/tháng và Pages riêng tư cần gói trả phí, nên dự án này dùng repo công khai.

## Cài một lần (làm được bằng điện thoại)
1. Tạo repo công khai tên `ai-kiem-tien-thanh`, đưa toàn bộ thư mục lên. **Thư mục ẩn `.github` hay bị bỏ sót khi kéo thả trên web**: kiểm tra có `.github/workflows/chay-luot.yml` chưa; chưa có thì Add file → Create new file, gõ đúng đường dẫn đó và dán nội dung. Dùng `git push` thì không sao.
2. Lấy khoá Gemini miễn phí ở aistudio.google.com/apikey, tạo trong **dự án mới, không bật thanh toán**. Khoá miễn phí khoảng 250 lượt/ngày, chỉ model Flash; `chinh-sach-github.json` đã đặt 220.
3. Repo → Settings → Secrets and variables → Actions → New repository secret:
   - `GEMINI_API_KEY`: khoá ở bước 2.
   - `TAI_KHOAN_NHAN`: nội dung `tai-khoan-nhan.json` đã điền (xem `thay-cap/tai-khoan-nhan.json.mau`), dán nguyên văn.
4. Settings → Actions → General → Workflow permissions → **Read and write**.
5. Settings → Pages → Source → **GitHub Actions**.
6. Tab Actions → `chay-luot` → Run workflow. Mở lượt chạy, đọc mục "In nhật ký lượt". Từ đó tự chạy 4 lần/ngày.

## Việc hằng ngày của thầy (trên GitHub web)
- Mở `ra/can-tao-link/` xem sản phẩm agent đề xuất → tạo link Shopee Affiliate → bấm bút chì sửa `thay-cap/link-affiliate.csv`, dán link.
- Video không lưu trong repo (quá nặng): vào Actions → lượt chạy mới nhất → Artifacts → `goi-bai-dang-…` (giữ 14 ngày). Chỉ đăng gói đã đạt kiểm.
- Mỗi tuần sửa `thay-cap/thu.csv` thêm tiền thật đã về, và đối chiếu với sao kê ngân hàng.
- **Dừng khẩn cấp (nút có sẵn)**: Actions → **nut-dung** → Run workflow → chọn `dung` → Run. Nó tạo tệp `DUNG`, huỷ mọi lượt đang chạy, các lượt sau tự thoát. Cho chạy lại: chạy `nut-dung` và chọn `tiep-tuc`. (Cách thủ công: Disable workflow chay-luot, hoặc tự tạo tệp `DUNG` ở gốc repo.)

## Lớp bảo vệ trong Actions
Sau mỗi vòng agent, workflow tự: khôi phục sổ cái nếu `but_toan` bị đổi hoặc `quota` bị sửa/xoá; hoàn tác mọi thay đổi ngoài `kinh-doanh/` và `ra/` (hiến pháp, chính sách, `thay-cap/`, công cụ); xoá tệp lỡ chứa khoá API. Đã thử bằng agent giả cố phá những thứ này và đều bị hoàn tác.

## Phải biết
- **Mọi thứ công khai**: sổ cái, `thu.csv`, nhật ký, log. Đừng ghi tên người donate hay thông tin cá nhân vào `ghi_chu`.
- Agent có thể đọc trang web lạ; trang độc hại có thể cố bắt nó làm bậy (prompt injection). Khoá của bạn không bật thanh toán nên xấu nhất là mất quota; nghi ngờ thì tạo khoá mới và cập nhật secret.
- Lịch hay trễ vài phút tới cả tiếng. Repo công khai tự tắt lịch nếu 60 ngày không có hoạt động; bot commit mỗi lượt nên thường không sao, nếu bị tắt thì bấm Enable.
- **Chưa thử trên GitHub thật.** Lần chạy đầu có thể phải chỉnh: Gemini CLI đòi chọn kiểu đăng nhập, tên model Flash đổi, hoặc phiên bản action (`@v4`...) đã cũ. Đọc log rồi sửa, hoặc dán log cho mình.

## Giấu địa chỉ trang (đăng bằng Cloudflare Pages thay vì GitHub Pages)
Địa chỉ `tên-github.github.io/tên-repo` lộ cả tên tài khoản lẫn repo, nên workflow đăng trang lên Cloudflare Pages (miễn phí).
1. Tạo tài khoản miễn phí ở dash.cloudflare.com. Ở trang chủ lấy **Account ID** (thanh bên phải).
2. My Profile → API Tokens → Create Token → dùng mẫu **Edit Cloudflare Workers**, hoặc Custom với quyền **Account · Cloudflare Pages · Edit**. Copy token.
3. Repo → Settings → Secrets → thêm 3 secret: `CLOUDFLARE_API_TOKEN` (token), `CLOUDFLARE_ACCOUNT_ID` (Account ID), `CF_PROJECT` (tên thầy tự đặt, chữ thường, số, gạch ngang, ví dụ `meo-xanh-4821`). Địa chỉ trang sẽ là `https://<CF_PROJECT>.pages.dev`.
4. Tắt trang cũ: Settings → Pages → đổi Source sang "Deploy from a branch" rồi chọn None (hoặc Unpublish site nếu có nút).
5. Chạy `chay-luot`, vào Cloudflare → Workers & Pages mở dự án để lấy địa chỉ. Log GitHub cố ý không in địa chỉ này.
Lưu ý: repo công khai thì ai tìm đúng tên repo vẫn xem được mã và nhật ký, nhưng từ trang web không còn lần ngược về repo được.

## Bộ đếm "người đang xem"
Trang có dòng "N người đang xem tôi làm việc". Nó chạy bằng `functions/api/xem.js` (Cloudflare Pages Function, tự được đăng cùng trang) và cần một KV miễn phí:
1. Cloudflare → Workers & Pages → **KV** → Create namespace, đặt tên `xem`.
2. Mở dự án Pages (tên `CF_PROJECT`) → Settings → **Bindings** (hoặc Functions → KV namespace bindings) → Add → KV namespace → tên biến **`XEM`**, chọn namespace vừa tạo, áp cho Production. Lưu rồi chạy lại `chay-luot`.
Chưa gắn KV hoặc hết quota thì bộ đếm tự ẩn, trang vẫn chạy. Gói miễn phí giới hạn khoảng 1.000 lượt ghi/ngày, đủ cho khoảng 15 giờ-người xem mỗi ngày; trang đông hơn thì bộ đếm sẽ ẩn vào cuối ngày. Không lưu IP, chỉ lưu mã ngẫu nhiên 90 giây.
