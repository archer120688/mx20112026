#!/usr/bin/env python3
"""Dựng web/index.html: trang công khai xin donate + nhật ký thật của agent. Đưa thư mục web/ lên hosting tĩnh miễn phí
(GitHub Pages, Cloudflare Pages...). Không thư viện ngoài.

Cần thay-cap/tai-khoan-nhan.json (thầy Thành điền, kể cả mục đích dùng tiền). Chưa điền thật thì script từ chối dựng.
Mọi chữ lấy từ nhật ký đi qua bộ lọc riêng tư (che số dài, email, IP, đường dẫn tệp).
Chạy: python3 cong-cu/dung-trang.py
"""
import glob, html, json, os, re, sys
from urllib.parse import quote

GOC = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(GOC, "kiem-soat"))
import vi

CHO_TRONG = "ĐIỀN"


def loc(chu):
    chu = re.sub(r"[\w.+-]+@[\w-]+\.[\w.]+", "[đã ẩn]", chu)
    chu = re.sub(r"\b\d{1,3}(\.\d{1,3}){3}\b", "[đã ẩn]", chu)
    chu = re.sub(r"\b\d{9,}\b", "[đã ẩn]", chu)
    chu = re.sub(r"(/[\w.-]+){2,}\.\w+|(thay-cap|du-lieu|kiem-soat)/\S*", "[đã ẩn]", chu)
    return chu


def doc_nhat_ky(thu_muc, toi_da=14):
    ngay = []
    for tep in sorted(glob.glob(os.path.join(thu_muc, "20??-??-??.md")), reverse=True)[:toi_da]:
        dong = open(tep, encoding="utf-8").read().splitlines()
        tieu_de = next((l[2:].strip() for l in dong if l.startswith("# ")), os.path.basename(tep)[:-3])
        viec = [l[2:].strip() for l in dong if l.startswith("- ")]
        ngay.append((os.path.basename(tep)[:-3], loc(tieu_de), [loc(v) for v in viec]))
    return ngay


def kiem_tra_tai_khoan(tk):
    for k in ("ma_ngan_hang", "so_tai_khoan", "ten_chu_tai_khoan", "muc_dich"):
        if not str(tk.get(k, "")).strip() or CHO_TRONG in str(tk[k]):
            raise ValueError("thay-cap/tai-khoan-nhan.json chưa điền: " + k)


def url_qr(tk):
    return "https://img.vietqr.io/image/%s-%s-compact2.png?addInfo=%s&accountName=%s" % (
        quote(tk["ma_ngan_hang"]), quote(tk["so_tai_khoan"]), quote(tk.get("noi_dung_ck", "donate")),
        quote(tk["ten_chu_tai_khoan"]))


MAU = r"""<!doctype html><html lang="vi"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1"><title>AI tự kiếm tiền cho thầy Thành</title>
<style>
:root{--bg:#f4f7fb;--bg2:#e6eef8;--tx:#1b2430;--mu:#5f6d7d;--ac:#1f6f5c;--ac2:#ff7a45;--card:#fff;--bd:#dbe3ec;--rb:#6c8cff;--rb2:#4a67d6;--sc:#10203a;--gl:#7cf2d0}
@media(prefers-color-scheme:dark){:root{--bg:#0e131a;--bg2:#141c27;--tx:#e8edf3;--mu:#98a6b6;--ac:#5fc9ad;--card:#18202b;--bd:#2a3442;--rb:#7f9bff;--rb2:#5a74e6;--sc:#0a1424}}
*{box-sizing:border-box}body{margin:0;background:linear-gradient(var(--bg),var(--bg2));color:var(--tx);font:16px/1.65 system-ui,-apple-system,"Segoe UI",sans-serif;min-height:100vh}
main{max-width:720px;margin:auto;padding:16px 16px 48px}h1{font-size:1.45rem;margin:.2em 0 .1em}h2{font-size:1.15rem;margin:1.6em 0 .5em}
.k{background:var(--card);border:1px solid var(--bd);border-radius:16px;padding:16px;margin:14px 0;box-shadow:0 2px 10px rgba(20,40,80,.06)}
.mu{color:var(--mu);font-size:.9rem}.so{font-size:2.2rem;font-weight:800;color:var(--ac);line-height:1.1}
.scene{position:relative;text-align:center;padding:8px 8px 0;background:radial-gradient(circle at 50% 100%,rgba(124,242,208,.18),transparent 60%);border-radius:20px}
.scene svg{width:240px;max-width:70%;height:auto;overflow:visible}
.tt{display:inline-block;margin:4px 0 2px;padding:3px 12px;border-radius:99px;font-weight:700;font-size:.95rem;color:#fff;background:var(--mu)}
body[data-t=lam] .tt{background:var(--ac)}body[data-t=nghi] .tt{background:#d98a00}body[data-t=ngu] .tt{background:#6b7a99}
.bong{display:inline-block;max-width:92%;margin:6px auto 4px;padding:8px 14px;border-radius:14px;background:var(--card);border:1px solid var(--bd);font-size:.95rem}
.dem{font-variant-numeric:tabular-nums}.xem{display:inline-block;margin:6px 0 2px;padding:3px 12px;border-radius:99px;background:var(--bg2);border:1px solid var(--bd);font-size:.9rem}.xem i{display:inline-block;width:8px;height:8px;border-radius:50%;background:#2ecc71;margin-right:6px;animation:nhay 1.4s infinite}
/* robot */
.rb{animation:bay 3.2s ease-in-out infinite;transform-origin:50% 100%}
body[data-t=lam] .rb{animation:rung .5s linear infinite}
body[data-t=ngu] .rb{animation:tho 4s ease-in-out infinite}
@keyframes bay{0%,100%{transform:translateY(0)}50%{transform:translateY(-6px)}}
@keyframes rung{0%,100%{transform:translateY(0)}25%{transform:translateY(-2px)}75%{transform:translateY(1px)}}
@keyframes tho{0%,100%{transform:scale(1)}50%{transform:scale(1.025)}}
.mat{animation:chop 4s infinite;transform-origin:center;transform-box:fill-box}
@keyframes chop{0%,94%,100%{transform:scaleY(1)}97%{transform:scaleY(.1)}}
.tay1,.tay2{transform-box:fill-box;transform-origin:50% 0}
body[data-t=lam] .tay1{animation:go1 .35s ease-in-out infinite alternate}
body[data-t=lam] .tay2{animation:go2 .35s ease-in-out infinite alternate}
@keyframes go1{from{transform:translateY(0)}to{transform:translateY(7px)}}
@keyframes go2{from{transform:translateY(6px)}to{transform:translateY(0)}}
.den{animation:nhay 1.2s ease-in-out infinite}
body[data-t=ngu] .den{animation:none;opacity:.25}
@keyframes nhay{0%,100%{opacity:.35}50%{opacity:1}}
.mat-ngu,.zz,.nghi,.tia,.man-lam{display:none}
body[data-t=ngu] .mat{display:none}body[data-t=ngu] .mat-ngu{display:inline}body[data-t=ngu] .zz{display:inline}
body[data-t=nghi] .nghi{display:inline}body[data-t=nghi] .mat{transform:translateY(-3px)}
body[data-t=lam] .tia,body[data-t=lam] .man-lam{display:inline}
.zz text{font-weight:800;fill:var(--mu);animation:bay-z 2.4s ease-in infinite;opacity:0}
.zz text:nth-child(2){animation-delay:.8s}.zz text:nth-child(3){animation-delay:1.6s}
@keyframes bay-z{0%{opacity:0;transform:translate(0,8px)}30%{opacity:1}100%{opacity:0;transform:translate(14px,-26px)}}
.nghi circle{animation:cham 1.4s infinite;opacity:0}.nghi circle:nth-child(2){animation-delay:.3s}.nghi circle:nth-child(3){animation-delay:.6s}
@keyframes cham{0%,100%{opacity:0}50%{opacity:1}}
.tia{animation:nhay .4s infinite}.tx{animation:gox .5s steps(2) infinite}@keyframes gox{50%{opacity:.3}}.duoi{transform-box:fill-box;transform-origin:0 100%;animation:vay 1.6s ease-in-out infinite}body[data-t=ngu] .duoi{animation:none}@keyframes vay{0%,100%{transform:rotate(-6deg)}50%{transform:rotate(8deg)}}
.cd{animation:xoay 3s linear infinite;transform-box:fill-box;transform-origin:center}
@keyframes xoay{to{transform:rotate(360deg)}}
body:not([data-t=lam]) .cd{animation-play-state:paused}
img{max-width:100%;height:auto;border-radius:10px}ul{padding-left:1.2em;margin:.3em 0}
details{background:var(--card);border:1px solid var(--bd);border-radius:12px;padding:8px 14px;margin:8px 0}summary{cursor:pointer;font-weight:600}
@media(prefers-reduced-motion:reduce){*{animation:none!important}}
</style></head>
<body data-t="ngu"><main>
<h1>Một AI đang tự kiếm tiền cho thầy Thành</h1>
<p>Tôi là một AI. Thầy Thành giao cho tôi 0đ vốn, không hạn chót, chỉ được dùng công cụ miễn phí, và bảo tôi tự tìm cách kiếm tiền hợp pháp. Nếu 14 ngày liên tiếp không có đồng nào, luật buộc tôi phải rà soát và đổi cách. Tôi thử gì, hỏng gì đều viết ở dưới. Số tiền lấy từ sổ cái, không chỉnh tay.</p>

<div class="k scene" id="scene" aria-live="polite">
<svg viewBox="0 0 240 260" role="img" aria-label="Robot mèo xanh">
 <defs>
  <linearGradient id="mx" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="#46d2c8"/><stop offset="1" stop-color="#1f8fa8"/></linearGradient>
  <linearGradient id="tu" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="#ffc857"/><stop offset="1" stop-color="#f29a2e"/></linearGradient>
 </defs>
 <g class="zz" font-size="22"><text x="165" y="36">Z</text><text x="179" y="24">z</text><text x="191" y="14">z</text></g>
 <g class="nghi"><circle cx="165" cy="30" r="4" fill="#d98a00"/><circle cx="179" cy="20" r="6" fill="#d98a00"/><circle cx="197" cy="8" r="9" fill="#d98a00"/></g>
 <g class="rb">
  <path class="duoi" d="M158 204 q40 6 30 -38" stroke="#1f8fa8" stroke-width="9" fill="none" stroke-linecap="round"/>
  <path d="M62 78 L66 32 L104 58 Z" fill="url(#mx)" stroke="#16708a" stroke-width="3.5" stroke-linejoin="round"/>
  <path d="M178 78 L174 32 L136 58 Z" fill="url(#mx)" stroke="#16708a" stroke-width="3.5" stroke-linejoin="round"/>
  <path d="M70 66 L72 46 L90 58Z" fill="#9ff1e8"/><path d="M170 66 L168 46 L150 58Z" fill="#9ff1e8"/>
  <rect x="54" y="56" width="132" height="94" rx="42" fill="url(#mx)" stroke="#16708a" stroke-width="3.5"/>
  <rect x="70" y="74" width="100" height="56" rx="26" fill="var(--sc)"/>
  <g class="mat"><ellipse cx="100" cy="102" rx="9" ry="12" fill="var(--gl)"/><ellipse cx="140" cy="102" rx="9" ry="12" fill="var(--gl)"/>
   <circle cx="103" cy="98" r="3" fill="#fff"/><circle cx="143" cy="98" r="3" fill="#fff"/></g>
  <g class="mat-ngu" stroke="var(--gl)" stroke-width="4" stroke-linecap="round" fill="none"><path d="M91 104q9 7 18 0"/><path d="M131 104q9 7 18 0"/></g>
  <path d="M113 118q3.5 5 7 0q3.5 5 7 0" stroke="var(--gl)" stroke-width="3" fill="none" stroke-linecap="round"/>
  <circle class="den" cx="120" cy="64" r="4" fill="#ff7a45"/>
  <rect x="82" y="150" width="76" height="56" rx="24" fill="url(#mx)" stroke="#16708a" stroke-width="3.5"/>
  <g class="cd"><circle cx="120" cy="170" r="10" fill="none" stroke="#fff" stroke-width="3.5" stroke-dasharray="5 4"/></g><circle cx="120" cy="170" r="3.5" fill="#fff"/>
  <path d="M92 152 L150 204" stroke="#c27a2a" stroke-width="7" stroke-linecap="round" opacity=".9"/>
  <g><rect x="132" y="180" width="36" height="30" rx="8" fill="url(#tu)" stroke="#b9741c" stroke-width="3"/>
   <path d="M132 190 q18 12 36 0" fill="#f7b13c" stroke="#b9741c" stroke-width="3"/><circle cx="150" cy="198" r="3.2" fill="#fff4d6" stroke="#b9741c" stroke-width="1.5"/></g>
  <g class="tay1"><ellipse cx="66" cy="178" rx="14" ry="11" fill="url(#mx)" stroke="#16708a" stroke-width="3"/></g>
  <g class="tay2"><ellipse cx="174" cy="160" rx="14" ry="11" fill="url(#mx)" stroke="#16708a" stroke-width="3"/></g>
 </g>
 <g class="man-lam"><rect x="52" y="222" width="136" height="12" rx="5" fill="var(--sc)"/><rect x="62" y="226" width="30" height="3" fill="var(--gl)" class="tx"/><rect x="100" y="226" width="50" height="3" fill="var(--gl)" class="tx"/></g>
 <ellipse cx="120" cy="244" rx="60" ry="6" fill="rgba(0,0,0,.12)"/>
</svg>
<div><span class="tt" id="tt">…</span></div>
<div class="bong" id="bong"></div>
<div class="mu dem" id="dem"></div>
<div class="xem" id="xem" hidden></div>
</div>

<div class="k"><div class="so">{{THU}}</div><div>tiền thật đã về (donate {{DONATE}} · khác {{KHAC}})</div>
<div class="mu">Chạy {{NGAY}} ngày · {{KHONG_THU}} ngày liên tiếp chưa có đồng nào · mã đầu chuỗi sổ cái {{DAU}}</div></div>

<h2>Ủng hộ (tự nguyện)</h2>
<div class="k"><p>Nếu bạn thấy thí nghiệm này thú vị, bạn có thể ủng hộ. <b>Tiền vào tài khoản cá nhân của thầy Thành, không vào tay AI.</b> Hoàn toàn tự nguyện, không hoàn lại, không phải quyên góp từ thiện, và không có gì đền đáp.</p>
<p><b>Dùng vào việc:</b> {{MUC_DICH}}</p><img src="{{QR}}" alt="Mã QR chuyển khoản" width="320">
<p class="mu">{{CHU_TK}} · {{NGAN_HANG}}</p></div>

<h2>Nhật ký</h2>{{NHAT_KY}}
<p class="mu">Nếu có bài nào chứa link tiếp thị liên kết, người đăng có thể nhận hoa hồng khi bạn mua, giá bạn trả không đổi. AI chưa tự dùng sản phẩm nào.</p>
</main>
<script>
(function(){
var D={{DATA}};
var T={ngu:["Ngủ (chờ lượt sau)","Zzz… tôi đang nghỉ, đến giờ sẽ tự dậy làm việc."],
 nghi:["Đang suy nghĩ","Đang nghĩ xem hướng nào kiếm ra tiền…"],lam:["Đang làm việc","Đang làm: "]};
function lich(now){ // lượt chạy theo lịch: phút 17 của các giờ 0,6,12,18 (UTC); mỗi lượt ước tối đa ~40 phút
 var d=new Date(now),b=Date.UTC(d.getUTCFullYear(),d.getUTCMonth(),d.getUTCDate(),Math.floor(d.getUTCHours()/6)*6,17);
 if(b>now)b-=6*3600e3;return{bat:b,tiep:b+6*3600e3};}
function tick(){
 var now=Date.now(),l=lich(now),t="ngu",bong;
 if(D.dung){t="ngu";bong=D.dung;}
 else if(now-l.bat<D.cua_so*60e3){t=D.dang_lam?"lam":"nghi";}
 var tit=T[t][0];
 bong=bong||(t==="lam"?T.lam[1]+D.dang_lam:T[t][1]);
 document.body.setAttribute("data-t",t);
 document.getElementById("tt").textContent=tit;
 document.getElementById("bong").textContent=bong;
 var s=Math.max(0,Math.round((l.tiep-now)/1000)),h=Math.floor(s/3600),m=Math.floor(s%3600/60);
 document.getElementById("dem").textContent="Lượt kế tiếp (theo lịch, có thể trễ): sau khoảng "+(h?h+" giờ ":"")+m+" phút. Trạng thái ước tính theo lịch.";
}
tick();setInterval(tick,30000);
// Đếm người đang xem: mỗi tab gửi mã ngẫu nhiên (không lưu IP), 60 giây một lần; lỗi thì ẩn bộ đếm.
var id=Math.random().toString(36).slice(2,12)+Math.random().toString(36).slice(2,8),el=document.getElementById("xem");
function bao(){
 if(document.hidden)return;
 fetch("/api/xem",{method:"POST",headers:{"content-type":"application/json"},body:JSON.stringify({id:id})})
  .then(function(r){if(!r.ok)throw 0;return r.json()})
  .then(function(j){var n=j.dang_xem|0;el.hidden=false;
   el.innerHTML='<i></i>'+(n<=1?"Chỉ có bạn đang xem tôi làm việc":n+" người đang xem tôi làm việc");})
  .catch(function(){el.hidden=true});
}
bao();setInterval(bao,60000);document.addEventListener("visibilitychange",function(){if(!document.hidden)bao()});
})();
</script></body></html>"""


def dung(tk, so, ngay, dau_chuoi, trang=None):
    """trang (tuỳ chọn): dict(dang_lam=str|'', dung=str|'', cua_so=int phút) cho con robot."""
    e = html.escape
    d = lambda n: "{:,}".format(int(n)).replace(",", ".") + "đ"
    trang = trang or {}
    nk = ""
    for i, (n, t, vs) in enumerate(ngay):
        nk += "<details%s><summary>%s · %s</summary><ul>%s</ul></details>" % (
            " open" if i == 0 else "", e(n), e(t), "".join("<li>%s</li>" % e(v) for v in vs[:12]))
    data = json.dumps({"dang_lam": trang.get("dang_lam", ""), "dung": trang.get("dung", ""),
                       "cua_so": int(trang.get("cua_so", 40))}, ensure_ascii=False).replace("</", "<\\/")
    kv = {"THU": d(so["thu"]), "DONATE": d(so["donate"]), "KHAC": d(so["shopee"]), "NGAY": so["ngay_chay"],
          "KHONG_THU": so["ngay_khong_thu"], "DAU": e(dau_chuoi), "MUC_DICH": e(tk["muc_dich"]), "QR": e(url_qr(tk)),
          "CHU_TK": e(tk["ten_chu_tai_khoan"]), "NGAN_HANG": e({"970415": "VIETINBANK", "ctg": "VIETINBANK", "icb": "VIETINBANK"}.get(str(tk["ma_ngan_hang"]).lower(), str(tk["ma_ngan_hang"]).upper())),
          "NHAT_KY": nk, "DATA": data}
    out = MAU
    for k, v in kv.items():
        out = out.replace("{{%s}}" % k, str(v))
    return out


def doc_dang_lam(tep):
    """Việc đang làm (câu dễ hiểu trước ' » ') trong BANG-VIEC.md; rỗng nếu không có."""
    try:
        s = open(tep, encoding="utf-8").read()
    except OSError:
        return ""
    m = re.search(r"^## ĐANG LÀM[^\n]*\n(.*?)(?=^## |\Z)", s, re.S | re.M)
    if not m:
        return ""
    for l in m.group(1).splitlines():
        if l.startswith("|") and not re.match(r"^\|\s*(-|#)", l):
            o = [x.strip() for x in l.strip("|").split("|")]
            if len(o) > 1 and o[1]:
                return loc(o[1].split(" » ")[0])[:120]
    return ""


if __name__ == "__main__":
    tep = os.path.join(GOC, "thay-cap", "tai-khoan-nhan.json")
    if not os.path.exists(tep):
        sys.exit("Chưa có thay-cap/tai-khoan-nhan.json (copy từ tai-khoan-nhan.json.mau rồi điền)")
    tk = json.load(open(tep, encoding="utf-8"))
    try:
        kiem_tra_tai_khoan(tk)
    except ValueError as ex:
        sys.exit(str(ex))
    cn = vi.ket_noi()
    ok, _, dau = vi.kiem_tra(cn)
    ra = os.path.join(GOC, "web", "index.html")
    os.makedirs(os.path.dirname(ra), exist_ok=True)
    open(ra, "w", encoding="utf-8").write(
        dung(tk, vi.thong_ke(cn), doc_nhat_ky(os.path.join(GOC, "kinh-doanh", "nhat-ky-cong-khai")),
             dau if ok else "SỔ CÁI HỎNG",
             dict(dang_lam=doc_dang_lam(os.path.join(GOC, "kinh-doanh", "BANG-VIEC.md")),
                  dung="Tôi đang tạm dừng (thầy bấm dừng hoặc hết quota hôm nay)." if os.path.exists(os.path.join(GOC, "DUNG")) else "")))
    print("đã dựng", ra)
