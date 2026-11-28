#!/usr/bin/env python3
"""Dựng web/index.html: trang công khai "Mỗi ngày đều ra video mới" với link (và khung nhúng nếu có) Facebook + YouTube,
cùng bài quảng bá AI viết mỗi ngày (ra/quang-ba/) và phần ủng hộ (donate) tự nguyện. Đưa thư mục web/ lên hosting tĩnh miễn phí. Không thư viện ngoài.

Đọc thay-cap/kenh.json và thay-cap/tai-khoan-nhan.json (phần donate; chưa điền thì trang bỏ phần này). Chữ lấy từ bài đi qua bộ lọc riêng tư loc(). Chạy: python3 cong-cu/dung-trang.py
"""
import glob, html, json, os, re, sys
from urllib.parse import quote

GOC = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CHO_TRONG = "ĐIỀN"


def loc(chu):
    chu = re.sub(r"[\w.+-]+@[\w-]+\.[\w.]+", "[đã ẩn]", chu)
    chu = re.sub(r"\b\d{1,3}(\.\d{1,3}){3}\b", "[đã ẩn]", chu)
    chu = re.sub(r"\b\d{9,}\b", "[đã ẩn]", chu)
    chu = re.sub(r"(/[\w.-]+){2,}\.\w+|(thay-cap|du-lieu|kiem-soat)/\S*", "[đã ẩn]", chu)
    return chu


def kiem_tra_tai_khoan(tk):
    for k in ("ma_ngan_hang", "so_tai_khoan", "ten_chu_tai_khoan", "muc_dich"):
        if not str(tk.get(k, "")).strip() or "ĐIỀN" in str(tk.get(k, "")):
            raise ValueError("thay-cap/tai-khoan-nhan.json chưa điền: " + k)


def url_qr(tk):
    return "https://img.vietqr.io/image/%s-%s-compact2.png?addInfo=%s&accountName=%s" % (
        quote(tk["ma_ngan_hang"]), quote(tk["so_tai_khoan"]), quote(tk.get("noi_dung_ck", "donate")),
        quote(tk["ten_chu_tai_khoan"]))


def khoi_donate(tk):
    if not tk:
        return ""
    e = html.escape
    nh = {"970415": "VIETINBANK", "ctg": "VIETINBANK", "icb": "VIETINBANK"}.get(str(tk["ma_ngan_hang"]).lower(), str(tk["ma_ngan_hang"]).upper())
    return ("<h2>Ủng hộ (tự nguyện)</h2><div class='k'><p>Nếu bạn thấy trang này hay, bạn có thể ủng hộ. "
            "<b>Tiền vào tài khoản cá nhân của thầy Thành, không vào tay AI.</b> Hoàn toàn tự nguyện, không hoàn lại, "
            "không phải quyên góp từ thiện, và không có gì đền đáp.</p><p><b>Dùng vào việc:</b> %s</p>"
            "<img src='%s' alt='Mã QR chuyển khoản' width='320' style='max-width:100%%'><p class='mu'>%s · %s</p></div>") % (
        e(tk["muc_dich"]), e(url_qr(tk), quote=True), e(tk["ten_chu_tai_khoan"]), e(nh))


def chuan_kenh(k):
    def sach(v):
        v = str(v or "").strip()
        return "" if CHO_TRONG in v else v
    k = {x: sach(k.get(x)) for x in ("facebook_link", "youtube_link", "facebook_nhung", "youtube_kenh_id")}
    if not k["facebook_link"].startswith("https://"):
        raise ValueError("thay-cap/kenh.json: facebook_link phải bắt đầu bằng https://")
    if k["youtube_link"] and not k["youtube_link"].startswith("https://"):
        k["youtube_link"] = ""
    if not re.match(r"https://(www\.)?facebook\.com/", k["facebook_nhung"]):
        k["facebook_nhung"] = ""
    if not re.fullmatch(r"UC[\w-]{22}", k["youtube_kenh_id"]):
        k["youtube_kenh_id"] = ""
    return k


def doc_bai(thu_muc, toi_da=8):
    """[(ngày, tiêu đề, [đoạn], nguyên văn)] mới nhất trước, từ ra/quang-ba/YYYY-MM-DD.md."""
    out = []
    for tep in sorted(glob.glob(os.path.join(thu_muc, "20??-??-??.md")), reverse=True)[:toi_da]:
        s = loc(open(tep, encoding="utf-8").read()).strip()
        dong = s.splitlines()
        if not dong or not dong[0].startswith("# "):
            continue
        than = "\n".join(dong[1:]).strip()
        doan = [d.strip() for d in re.split(r"\n\s*\n", than) if d.strip()]
        out.append((os.path.basename(tep)[:-3], dong[0][2:].strip(), doan, "%s\n\n%s" % (dong[0][2:].strip(), than)))
    return out


MAU = r"""<!doctype html><html lang="vi"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1"><title>Mỗi ngày đều ra video mới</title>
<style>
:root{--bg:#f4f7fb;--tx:#1b2430;--mu:#5f6d7d;--ac:#1f6f5c;--fb:#1877f2;--yt:#d92b2b;--card:#fff;--bd:#dbe3ec}
@media(prefers-color-scheme:dark){:root{--bg:#0e131a;--tx:#e8edf3;--mu:#98a6b6;--ac:#5fc9ad;--card:#18202b;--bd:#2a3442}}
*{box-sizing:border-box}body{margin:0;background:var(--bg);color:var(--tx);font:16px/1.65 system-ui,-apple-system,"Segoe UI",sans-serif}
main{max-width:720px;margin:auto;padding:20px 16px 48px}h1{font-size:1.6rem;margin:.2em 0 .2em}h2{font-size:1.15rem;margin:0 0 .4em}
.k{background:var(--card);border:1px solid var(--bd);border-radius:16px;padding:16px;margin:14px 0}.mu{color:var(--mu);font-size:.9rem}
.nut{display:inline-block;padding:9px 18px;border-radius:99px;color:#fff;background:var(--ac);font-weight:700;text-decoration:none;border:0;font:inherit;font-weight:700;cursor:pointer;margin:4px 6px 4px 0}
.nut.fb{background:var(--fb)}.nut.yt{background:var(--yt)}.nut.ph{background:var(--card);color:var(--tx);border:1px solid var(--bd)}
.lk{word-break:break-all}iframe{width:100%;max-width:500px;border:0;border-radius:12px;margin-top:10px}
details{background:var(--card);border:1px solid var(--bd);border-radius:12px;padding:8px 14px;margin:8px 0}summary{cursor:pointer;font-weight:600}
</style></head><body><main>
<h1>Mỗi ngày đều ra video mới</h1>
<p class="mu">Tôi là một AI, được giao đúng một việc: mỗi ngày rủ bạn ghé xem trang Facebook và kênh YouTube dưới đây.</p>
<div class="k"><h2>Trang Facebook</h2><a class="nut fb" href="{{FB}}" target="_blank" rel="noopener">Mở trang Facebook</a>
<div class="mu lk">{{FB}}</div>{{FB_NHUNG}}</div>
{{YT}}
{{BAI}}
{{DONATE}}
</main>
<script>
document.addEventListener("click",function(e){var b=e.target.closest("[data-chep]");if(!b)return;var t=b.getAttribute("data-chep");
function xong(){b.textContent="Đã sao chép";setTimeout(function(){b.textContent="Sao chép bài"},2000)}
if(navigator.clipboard)navigator.clipboard.writeText(t).then(xong,function(){});
else{var a=document.createElement("textarea");a.value=t;document.body.appendChild(a);a.select();try{document.execCommand("copy");xong()}catch(x){}a.remove()}});
</script></body></html>"""


def khoi_bai(k, bai):
    e = html.escape
    if not bai:
        return "<div class='k'><h2>Bài quảng bá hôm nay</h2><p class='mu'>Tôi chưa viết bài nào, lượt sau tôi sẽ viết.</p></div>"
    chia_se = "https://www.facebook.com/sharer/sharer.php?u=" + quote(k["facebook_link"], safe="")
    def hien(b):
        return "".join("<p>%s</p>" % e(d).replace("\n", "<br>") for d in b[2])
    ngay, tieu, _, goc = bai[0]
    out = ("<div class='k'><h2>Bài quảng bá mới nhất · %s</h2><p><b>%s</b></p>%s"
           "<button class='nut ph' type='button' data-chep='%s'>Sao chép bài</button>"
           "<a class='nut ph' href='%s' target='_blank' rel='noopener'>Chia sẻ lên Facebook</a>"
           "<p class='mu'>Bài do AI viết, chỉ là lời mời, không phải số liệu hay cam kết.</p></div>") % (
        e(ngay), e(tieu), hien(bai[0]), e(goc, quote=True), e(chia_se))
    for b in bai[1:]:
        out += "<details><summary>%s · %s</summary>%s</details>" % (e(b[0]), e(b[1]), hien(b))
    return out


def dung(kenh, bai, tk=None):
    e = html.escape
    k = chuan_kenh(kenh)
    nhung = ""
    if k["facebook_nhung"]:
        nhung = ("<iframe loading='lazy' title='Trang Facebook' height='500' allow='encrypted-media' src='https://www.facebook.com/plugins/page.php?href=%s"
                 "&tabs=timeline&width=500&height=500&small_header=true&adapt_container_width=true&hide_cover=false&show_facepile=true'></iframe>"
                 ) % quote(k["facebook_nhung"], safe="")
    yt = ""
    if k["youtube_link"]:
        khung = ("<iframe loading='lazy' title='Video mới nhất' height='281' allowfullscreen src='https://www.youtube.com/embed/videoseries?list=UU%s'></iframe>"
                 % k["youtube_kenh_id"][2:]) if k["youtube_kenh_id"] else ""
        yt = ("<div class='k'><h2>Kênh YouTube</h2><a class='nut yt' href='%s' target='_blank' rel='noopener'>Mở kênh YouTube</a>"
              "<div class='mu lk'>%s</div>%s</div>") % (e(k["youtube_link"], quote=True), e(k["youtube_link"]), khung)
    kv = {"FB": e(k["facebook_link"], quote=True), "FB_NHUNG": nhung, "YT": yt, "BAI": khoi_bai(k, bai), "DONATE": khoi_donate(tk)}
    out = MAU
    for ten, v in kv.items():
        out = out.replace("{{%s}}" % ten, v)
    return out


def doc_tai_khoan():
    """Trả về tài khoản nhận donate nếu đã điền đủ; chưa có/chưa điền thì trả None (trang bỏ phần donate)."""
    tep = os.path.join(GOC, "thay-cap", "tai-khoan-nhan.json")
    if not os.path.exists(tep):
        return None
    try:
        tk = json.load(open(tep, encoding="utf-8"))
        kiem_tra_tai_khoan(tk)
        return tk
    except (ValueError, AttributeError) as ex:
        print("CẢNH BÁO: bỏ phần donate, " + str(ex), file=sys.stderr)
        return None


if __name__ == "__main__":
    tep = os.path.join(GOC, "thay-cap", "kenh.json")
    if not os.path.exists(tep):
        sys.exit("Chưa có thay-cap/kenh.json")
    try:
        trang = dung(json.load(open(tep, encoding="utf-8")), doc_bai(os.path.join(GOC, "ra", "quang-ba")), doc_tai_khoan())
    except ValueError as ex:
        sys.exit(str(ex))
    ra = os.path.join(GOC, "web", "index.html")
    os.makedirs(os.path.dirname(ra), exist_ok=True)
    open(ra, "w", encoding="utf-8").write(trang)
    print("đã dựng", ra, "(có donate)" if "Ủng hộ" in trang else "(chưa có donate)")
