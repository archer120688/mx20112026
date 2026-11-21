#!/usr/bin/env python3
"""Một lượt làm việc của agent. CODE điều khiển, không dùng agent dòng lệnh (Gemini CLI).

Vì sao đổi: agent dòng lệnh tự gọi hàng chục lần API cho mỗi việc, dễ cháy hết quota miễn phí rồi im lặng, và phải
tự sửa tệp nên hay "nghĩ xong rồi thôi". Ở đây mỗi lượt chỉ 1–3 lần gọi AI. AI trả về JSON; chương trình kiểm đầu ra,
rồi TỰ ghi nhật ký, ý tưởng, sản phẩm, bảng việc. Nếu mọi AI đều hỏng, chương trình ghi thật thà "chưa làm được" và
lý do vào kinh-doanh/TRANG-THAI-LUOT.md. Không bao giờ im lặng.

Thứ tự thử AI: xem cong-cu/nha-cung-cap.json (Gemini trước, rồi các dịch vụ miễn phí khác nếu có khoá).
Chạy: python3 cong-cu/luot-ngay.py        (chay-luot.sh gọi khi AGENT=api)
"""
import glob
import importlib.util
import json
import os
import re
import sys
import time
import unicodedata
import urllib.error
import urllib.request
from datetime import date, datetime, timedelta, timezone
from difflib import SequenceMatcher

CD = os.path.dirname(os.path.abspath(__file__))
GOC = os.environ.get("LUOT_GOC") or os.path.dirname(CD)
sys.path.insert(0, os.path.join(os.path.dirname(CD), "kiem-soat"))
import vi  # noqa: E402


def _nap(ten_tep):
    spec = importlib.util.spec_from_file_location(ten_tep.replace("-", "_"), os.path.join(CD, ten_tep + ".py"))
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


TRANG = _nap("dung-trang")      # bộ lọc riêng tư loc()
KIEM_BAI = _nap("kiem-bai")     # danh sách câu cấm CAU_CAM

VN = timezone(timedelta(hours=7))
KD = os.path.join(GOC, "kinh-doanh")
CONG_KHAI = os.path.join(KD, "nhat-ky-cong-khai")
SAN_PHAM = os.path.join(GOC, "ra", "san-pham")
NGHIEN_CUU = os.path.join(KD, "nghien-cuu")
TEN_KHOA = ["GEMINI_API_KEY", "GROQ_API_KEY", "OPENROUTER_API_KEY", "MISTRAL_API_KEY", "ANTHROPIC_API_KEY",
            "GITHUB_MODELS_TOKEN", "GITHUB_TOKEN"]
MARKER_LOI = "<!-- LOI-AI -->"
GOC_NHIN = ["người bán hàng online nhỏ", "học sinh – sinh viên", "mẹ bỉm sữa", "dân văn phòng",
            "người mê nấu ăn, làm bếp", "người sửa nhà, tự làm đồ (DIY), đồ gia dụng", "người lớn tuổi dùng điện thoại",
            "người đang tìm việc, viết CV", "người mê game, giải trí", "người nuôi thú cưng", "người hay đi đường, tài xế"]

SO_LAN_GOI = 0   # tổng số lần gọi API trong lượt này (ghi vào quota)


# ---------- tiện ích ----------

def bay_gio():
    return datetime.now(VN)


def gio_ngan():
    return bay_gio().strftime("%H:%M %d/%m")


def hom_nay():
    return bay_gio().strftime("%Y-%m-%d")


def che_khoa(s):
    for n in TEN_KHOA:
        v = os.environ.get(n, "")
        if len(v) >= 8:
            s = s.replace(v, "[khóa]")
    return s


def doc_tep(p, mac_dinh=""):
    try:
        with open(p, encoding="utf-8") as f:
            return f.read()
    except OSError:
        return mac_dinh


def ghi_tep(p, s):
    os.makedirs(os.path.dirname(p), exist_ok=True)
    with open(p, "w", encoding="utf-8") as f:
        f.write(s)


def duoi(s, n):
    return s if len(s) <= n else "…" + s[-n:]


def slug(s):
    s = s.replace("đ", "d").replace("Đ", "D")
    s = unicodedata.normalize("NFKD", s).encode("ascii", "ignore").decode()
    s = re.sub(r"[^a-zA-Z0-9]+", "-", s).strip("-").lower()
    return s[:50] or "san-pham"


def sach(s, toi_da=2000):
    """Làm sạch chữ AI viết để đưa lên repo công khai."""
    return TRANG.loc(che_khoa(str(s or ""))).strip()[:toi_da]


def moc_mua_sam(hn):
    def den_thu_sau(y):  # Black Friday: ngày sau thứ Năm thứ tư của tháng 11
        d = date(y, 11, 1)
        return d + timedelta((3 - d.weekday()) % 7) + timedelta(weeks=3, days=1)
    tet = {2026: date(2027, 2, 6), 2027: date(2027, 2, 6), 2028: date(2028, 1, 26), 2029: date(2029, 2, 13),
           2030: date(2030, 2, 3)}
    ds = []
    for y in (hn.year, hn.year + 1):
        ds += [("20/10 Phụ nữ VN", date(y, 10, 20)), ("20/11 Nhà giáo VN", date(y, 11, 20)),
               ("11.11", date(y, 11, 11)), ("Black Friday", den_thu_sau(y)), ("12.12", date(y, 12, 12)),
               ("Giáng sinh", date(y, 12, 25)), ("Tết Dương lịch", date(y, 1, 1)),
               ("Valentine", date(y, 2, 14)), ("8/3", date(y, 3, 8))]
    ds += [("Tết Nguyên đán", d) for d in set(tet.values())]
    return [(t, d) for t, d in sorted(ds, key=lambda x: x[1]) if 0 <= (d - hn).days <= 100]


# ---------- gọi AI ----------

class HetCach(Exception):
    pass


def post_json(url, headers, body, timeout=150):
    req = urllib.request.Request(url, data=json.dumps(body).encode("utf-8"), method="POST",
                                 headers={"content-type": "application/json", **headers})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return r.status, json.loads(r.read().decode("utf-8", "replace"))
    except urllib.error.HTTPError as e:
        try:
            nd = e.read().decode("utf-8", "replace")
        except Exception:
            nd = ""
        return e.code, {"_loi": che_khoa(nd)[:300]}
    except Exception as e:  # mạng, hết giờ, JSON hỏng
        return 0, {"_loi": che_khoa(str(e))[:200]}


def goi_gemini(nc, model, he, nguoi, json_mode, tim_kiem):
    cfg = {"temperature": 1.0, "maxOutputTokens": 16384}
    if json_mode:
        cfg["responseMimeType"] = "application/json"
    body = {"systemInstruction": {"parts": [{"text": he}]},
            "contents": [{"role": "user", "parts": [{"text": nguoi}]}], "generationConfig": cfg}
    if tim_kiem:
        body["tools"] = [{"google_search": {}}]
    st, j = post_json("https://generativelanguage.googleapis.com/v1beta/models/%s:generateContent" % model,
                      {"x-goog-api-key": os.environ.get(nc["khoa_env"], "")}, body)
    if st != 200:
        return st, None, [], j.get("_loi", "")
    c = (j.get("candidates") or [{}])[0]
    text = "".join(p.get("text", "") for p in (c.get("content") or {}).get("parts", []) if not p.get("thought"))
    nguon = []
    for g in (c.get("groundingMetadata") or {}).get("groundingChunks", []):
        w = g.get("web") or {}
        if w.get("uri"):
            nguon.append({"tieu_de": w.get("title", ""), "url": w["uri"]})
    return 200, text.strip(), nguon, ""


def goi_openai(nc, model, he, nguoi, json_mode):
    body = {"model": model, "temperature": 0.9, "max_tokens": 6000,
            "messages": [{"role": "system", "content": he}, {"role": "user", "content": nguoi}]}
    if json_mode:
        body["response_format"] = {"type": "json_object"}
    hdr = {"authorization": "Bearer " + os.environ.get(nc["khoa_env"], "")}
    st, j = post_json(nc["url"], hdr, body)
    if st == 400 and json_mode:  # một số dịch vụ miễn phí không hỗ trợ response_format
        body.pop("response_format")
        st, j = post_json(nc["url"], hdr, body)
    if st != 200:
        return st, None, [], j.get("_loi", "")
    try:
        return 200, (j["choices"][0]["message"]["content"] or "").strip(), [], ""
    except (KeyError, IndexError, TypeError):
        return 200, "", [], "phản hồi lạ"


def goi_anthropic(nc, model, he, nguoi):
    body = {"model": model, "max_tokens": 6000, "system": he, "messages": [{"role": "user", "content": nguoi}]}
    st, j = post_json("https://api.anthropic.com/v1/messages",
                      {"x-api-key": os.environ.get(nc["khoa_env"], ""), "anthropic-version": "2023-06-01"}, body)
    if st != 200:
        return st, None, [], j.get("_loi", "")
    return 200, "".join(b.get("text", "") for b in j.get("content", []) if b.get("type") == "text").strip(), [], ""


def nap_nha_cung_cap():
    with open(os.path.join(CD, "nha-cung-cap.json"), encoding="utf-8") as f:
        return json.load(f)


def goi_ai(he, nguoi, json_mode=True, tim_kiem=False, kiem=None, lan=None):
    """Thử lần lượt từng nhà cung cấp và model có khoá. Trả (chữ, meta). Hết cách thì ném HetCach.
    kiem(chữ) -> chuỗi lỗi hoặc '' : đầu ra sai thì thử model khác. lan: list ghi lại mọi lần thử (nha, model, mã, lỗi)."""
    global SO_LAN_GOI
    lan = lan if lan is not None else []
    cfg = nap_nha_cung_cap()
    for ten in cfg["thu_tu"]:
        nc = cfg.get(ten)
        if not nc or not os.environ.get(nc["khoa_env"], ""):
            continue
        if tim_kiem and not nc.get("tim_kiem"):
            continue
        ds = [m.strip() for m in os.environ.get(nc.get("models_env", "_"), "").split(",") if m.strip()] or nc["models"]
        for model in ds:
            for thu in (1, 2):
                SO_LAN_GOI += 1
                if nc["loai"] == "gemini":
                    st, text, nguon, loi = goi_gemini(nc, model, he, nguoi, json_mode, tim_kiem)
                elif nc["loai"] == "anthropic":
                    st, text, nguon, loi = goi_anthropic(nc, model, he, nguoi)
                else:
                    st, text, nguon, loi = goi_openai(nc, model, he, nguoi, json_mode)
                if st == 200 and text:
                    sai = kiem(text) if kiem else ""
                    if not sai:
                        lan.append((ten, model, 200, "OK"))
                        return text, {"nha": ten, "model": model, "nguon": nguon}
                    lan.append((ten, model, 200, "đầu ra sai: " + sai[:100]))
                    break
                lan.append((ten, model, st, loi or "trống"))
                if st in (500, 502, 503, 504) and thu == 1:
                    time.sleep(8)
                    continue
                break
    raise HetCach(lan)


def chan_doan(lan):
    if not lan:
        return "Chưa có khoá AI nào được đặt (GEMINI_API_KEY...). Vào repo → Settings → Secrets để thêm."
    ma = [x[2] for x in lan]
    if all(m in (400, 401, 403) for m in ma):
        return "Khoá AI có vẻ sai hoặc bị khoá/chưa bật (mã %s). Tạo khoá mới ở aistudio.google.com/apikey." % sorted(set(ma))
    if any(m == 429 for m in ma):
        return "Hết lượt miễn phí hôm nay (mã 429). Thêm khoá dự phòng (GROQ_API_KEY hoặc OPENROUTER_API_KEY) hoặc chờ sang ngày."
    if any(m == 200 for m in ma):
        return "AI trả lời nhưng sai khuôn mẫu; xem chi tiết các lần thử."
    return "Dịch vụ AI lỗi hoặc mạng lỗi; lượt sau tự thử lại."


# ---------- đọc/kiểm đầu ra ----------

def tach_json(text):
    t = re.sub(r"^```(?:json)?\s*|\s*```$", "", text.strip())
    i, j = t.find("{"), t.rfind("}")
    if i < 0 or j <= i:
        return None
    try:
        d = json.loads(t[i:j + 1])
    except ValueError:
        return None
    return d if isinstance(d, dict) else None


def ds_chu(x):
    return [str(i).strip() for i in x if str(i).strip()] if isinstance(x, list) else []


def loi_ket_qua(d, moi):
    if not isinstance(d, dict):
        return "không phải JSON"
    sp = d.get("san_pham") if isinstance(d.get("san_pham"), dict) else {}
    tn = d.get("thi_nghiem_hom_nay") if isinstance(d.get("thi_nghiem_hom_nay"), dict) else {}
    yt = [y for y in d.get("y_tuong", []) if isinstance(y, dict) and str(y.get("ten", "")).strip()] \
        if isinstance(d.get("y_tuong"), list) else []
    loi = []
    if len(ds_chu(d.get("nhat_ky_cong_khai"))) < (3 if moi else 1):
        loi.append("thiếu nhật ký công khai")
    if len(str(sp.get("noi_dung_md", ""))) < 300:
        loi.append("san_pham.noi_dung_md quá ngắn")
    if not str(sp.get("tieu_de", "")).strip():
        loi.append("thiếu san_pham.tieu_de")
    if moi:
        if not str(d.get("tieu_de_ngay", "")).strip():
            loi.append("thiếu tieu_de_ngay")
        if len(yt) < 2:
            loi.append("cần ít nhất 2 ý tưởng")
        if not str(tn.get("ten", "")).strip():
            loi.append("thiếu thi_nghiem_hom_nay")
    return "; ".join(loi)


SO_TIEN = re.compile(r"\d[\d.,]*\s*(?:đ|đồng|vnd|vnđ|k|nghìn|ngàn|triệu|tr)\b", re.I)


def loc_nhat_ky_cong_khai(ds):
    """Bỏ dòng có số tiền (tiền thật chỉ lấy từ sổ cái) hoặc câu cấm (đã dùng thử, cam kết, 100%...)."""
    out = []
    for b in ds:
        b = sach(b, 400)
        if not b or SO_TIEN.search(b) or any(re.search(c, b, re.I) for c in KIEM_BAI.CAU_CAM):
            continue
        out.append(b)
    return out


# ---------- ngữ cảnh + lời nhắc ----------

def y_tuong_da_co():
    out = []
    for l in doc_tep(os.path.join(KD, "CO-HOI.md")).splitlines():
        if l.startswith("|") and not re.match(r"^\|\s*(-|#)", l):
            o = [x.strip() for x in l.strip("|").split("|")]
            if len(o) > 1 and o[1]:
                out.append(o[1].split(":")[0].strip())
    return out


def che_do():
    tep = os.path.join(CONG_KHAI, hom_nay() + ".md")
    if not os.path.exists(tep) or MARKER_LOI in doc_tep(tep):
        return "ngay-moi"
    return "lam-viec"


def nhat_ky_gan_day():
    out = []
    for tep in sorted(glob.glob(os.path.join(CONG_KHAI, "20??-??-??.md")), reverse=True)[:3]:
        out.append("[%s]\n%s" % (os.path.basename(tep)[:-3], duoi(doc_tep(tep), 900)))
    return "\n".join(out) or "(chưa có)"


def san_pham_gan_day():
    return ", ".join(os.path.basename(p) for p in sorted(glob.glob(os.path.join(SAN_PHAM, "*.md")))[-6:]) or "(chưa có)"


def prompt_nghien_cuu(hn, goc):
    moc = ", ".join("%s (%s)" % (t, d.strftime("%d/%m")) for t, d in moc_mua_sam(hn)) or "không có"
    return ("Hôm nay là %s. Bạn đang giúp một dự án kiếm tiền hợp pháp bằng 0đ ở Việt Nam. Hãy tìm trên web và liệt kê "
            "6–8 gạch đầu dòng NGẮN về thứ người Việt đang quan tâm, hỏi nhiều, hoặc sắp cần mua trong 1–3 tuần tới "
            "(sản phẩm gia dụng đang hot trên Shopee, câu hỏi hay gặp, nhu cầu theo mốc: %s). Ưu tiên góc nhìn: %s. "
            "Mỗi gạch ghi rõ nguồn tin (tên trang). Chỉ ghi điều tìm thấy thật, không bịa." % (hn.strftime("%d/%m/%Y"), moc, goc))


KHUON = """Trả về DUY NHẤT một đối tượng JSON hợp lệ (không giải thích, không dấu ```), đúng các khoá sau:
{
 "tieu_de_ngay": "một câu ngắn nói điều chính của hôm nay",
 "nhat_ky_cong_khai": ["câu ngôi thứ nhất, ngắn, thật thà, hài hước nhẹ; KHÔNG ghi số tiền", "..."],
 "nhat_ky_noi_bo": ["1-3 dòng: đã làm gì · bằng chứng · việc lượt sau"],
 "y_tuong": [{"ten": "tên ngắn", "mo_ta": "1-2 câu", "ai_tra_tien": "ai trả và vì sao", "vi_sao_co_nhu_cau": "bằng chứng từ mục NGHIÊN CỨU, hoặc ghi 'giả thuyết, chưa kiểm'", "tien_du_kien_thang": "ước lượng thật thà, có thể là '0 - vài trăm nghìn'", "buoc_dau_tien": "việc làm được ngay hôm nay", "can_thay_lam": "việc thầy phải làm (≤10 phút) hoặc 'không'", "diem": 1}],
 "thi_nghiem_hom_nay": {"ten": "", "viec_cu_the": "", "do_bang_so_nao": "số nào tăng thì coi là có tín hiệu"},
 "san_pham": {"tieu_de": "", "noi_dung_md": "THỨ DÙNG ĐƯỢC NGAY của thí nghiệm hôm nay, dạng markdown, tối thiểu 400 chữ (bài đăng hoàn chỉnh, nội dung trang, mẫu biểu, kịch bản, danh sách bước cho thầy...)"},
 "viec_moi": ["Câu dễ hiểu (≤15 chữ, không tên tệp) » chi tiết"],
 "viec_xong": [{"so": 1, "bang_chung": "việc số mấy trong bảng CHỜ đã xong và bằng chứng"}],
 "can_thay": ["việc cần thầy Thành làm, gom ngắn gọn; rỗng nếu không có"],
 "ra_soat_md": "chỉ điền khi báo cáo ghi PHẢI RÀ SOÁT: đã thử gì, khâu nghẽn, bỏ gì, 2 thí nghiệm mới"
}"""


def dung_prompt(cn, cs, moi, nghien_cuu, hn):
    goc = GOC_NHIN[hn.toordinal() % len(GOC_NHIN)]
    moc = ", ".join("%s (%s)" % (t, d.strftime("%d/%m")) for t, d in moc_mua_sam(hn)) or "không có"
    ke_hoach = re.sub(r"<!--.*?-->", "", doc_tep(os.path.join(KD, "KE-HOACH.md")), flags=re.S)
    p = ["Hôm nay là %s %s (giờ Việt Nam). Chế độ: %s." % (
        ["Thứ hai", "Thứ ba", "Thứ tư", "Thứ năm", "Thứ sáu", "Thứ bảy", "Chủ nhật"][hn.weekday()],
        hn.strftime("%d/%m/%Y"), "NGÀY MỚI" if moi else "LÀM VIỆC TIẾP TRONG NGÀY"),
        "Góc nhìn gợi ý hôm nay (để ý tưởng khỏi lặp, được bỏ nếu có hướng tốt hơn): " + goc,
        "Mốc mua sắm sắp tới: " + moc,
        "Ý TƯỞNG ĐÃ CÓ (không lặp lại): " + ("; ".join(y_tuong_da_co()[-40:]) or "(chưa có)"),
        "SẢN PHẨM GẦN ĐÂY: " + san_pham_gan_day(),
        "BÁO CÁO:\n" + vi.bao_cao(cn, cs),
        "KẾ HOẠCH:\n" + duoi(ke_hoach, 2500),
        "BẢNG VIỆC:\n" + duoi(doc_tep(os.path.join(KD, "BANG-VIEC.md")), 3500),
        "NHẬT KÝ NỘI BỘ (cuối):\n" + duoi(doc_tep(os.path.join(KD, "NHAT-KY.md")), 1800),
        "NHẬT KÝ CÔNG KHAI GẦN ĐÂY:\n" + nhat_ky_gan_day()]
    if moi:
        p.append("NGHIÊN CỨU HÔM NAY (kết quả tìm web thật, có thể rỗng):\n" + (duoi(nghien_cuu, 4000) or "(không tìm được; mọi nhu cầu ghi là giả thuyết)"))
        p.append("NHIỆM VỤ HÔM NAY:\n"
                 "1) Nghĩ ra ĐÚNG 3 ý tưởng kiếm tiền MỚI, khác loại nhau, không trùng danh sách đã có. Mỗi ý tưởng: làm được với 0đ và công cụ miễn phí; "
                 "AI viết/làm phần lớn, thầy chỉ làm ≤10 phút (đăng bài, bấm nút, dán link); nói rõ AI trả tiền và vì sao; có bước đầu tiên làm ngay. "
                 "Hai việc thầy giao (xin donate qua trang công khai, tiếp thị Shopee) chỉ là điểm xuất phát: video KHÔNG bắt buộc, bài chữ/trang/công cụ/mẫu biểu đều được, "
                 "và bạn được nghĩ ra hướng thứ ba, thứ tư nếu hợp pháp.\n"
                 "2) Chọn 1 ý tưởng đáng thử nhất làm THÍ NGHIỆM HÔM NAY và LÀM NGAY phần AI làm được, ghi vào san_pham: viết chính thứ đó, không viết kế hoạch chung chung.\n"
                 "3) Nhật ký công khai 3–6 câu ngôi thứ nhất: hôm nay nghĩ gì, chọn gì vì sao, chưa biết gì. Thật thà, không bịa, không nêu số tiền.\n"
                 "4) Sinh 2–3 việc mới cho bảng việc; nếu một việc trong CHỜ đã được san_pham làm xong thì ghi vào viec_xong.\n"
                 "5) can_thay: gom việc cần thầy (đăng bài nào, dán link nào, kênh nào) thành vài dòng.")
    else:
        p.append("NHIỆM VỤ LƯỢT NÀY:\n"
                 "Hôm nay đã có nhật ký. Chọn việc gần tiền nhất (thí nghiệm hôm nay hoặc việc đầu bảng CHỜ) và LÀM TIẾP: san_pham là bản mới/phần tiếp theo, không lặp sản phẩm trước. "
                 "nhat_ky_cong_khai chỉ 1–2 câu về phần làm thêm. y_tuong có thể rỗng. tieu_de_ngay, thi_nghiem_hom_nay có thể để trống.")
    if "PHẢI RÀ SOÁT" in vi.bao_cao(cn, cs):
        p.append("BÁO CÁO GHI PHẢI RÀ SOÁT: điền ra_soat_md.")
    p.append(KHUON)
    return "\n\n".join(p)


# ---------- ghi kết quả ----------

def bang_cell(s, n=220):
    return re.sub(r"\s+", " ", sach(s, n)).replace("|", "/")


def them_viec(s, ds, gio, nguon):
    m = re.search(r"^## CHỜ[^\n]*\n(.*?)(?=^## |\Z)", s, re.S | re.M)
    if not m:
        return s
    body = m.group(1).rstrip("\n")
    so_cho = len([l for l in body.splitlines() if re.match(r"^\|\s*\d+\s*\|", l)])
    nid = max([int(x) for x in re.findall(r"^\|\s*(\d+)\s*\|", s, re.M)] or [0]) + 1
    han = (bay_gio() + timedelta(days=3)).strftime("%d/%m")
    moi = []
    for v in ds:
        if so_cho + len(moi) >= 12:
            break
        v = bang_cell(v, 300)
        if not v:
            continue
        if " » " not in v:
            v = v[:60] + " » " + v
        moi.append("| %d | %s | Ý tưởng | số việc làm xong | %s | %s | %s |" % (nid + len(moi), v, gio, han, nguon))
    if not moi:
        return s
    return s[:m.start(1)] + body + "\n" + "\n".join(moi) + "\n\n" + s[m.end(1):]


def chuyen_xong(s, so, bang_chung, gio):
    """Chuyển việc số `so` từ CHỜ sang XONG (mới nhất ở trên) kèm bằng chứng."""
    a, b = s.find("## CHỜ"), s.find("## ĐANG LÀM")
    if a < 0 or b < a:
        return s
    cho = s[a:b]
    m = re.search(r"^\|\s*%d\s*\|[^\n]*\n" % so, cho, re.M)
    if not m:
        return s
    viec = [x.strip() for x in m.group(0).strip().strip("|").split("|")][1]
    s = s[:a] + cho[:m.start()] + cho[m.end():] + s[b:]
    x = re.search(r"^## XONG[^\n]*\n\|[^\n]*\n\|[^\n]*\n", s, re.M)
    if not x:
        return s
    hang = "| %d | %s | %s | %s | làm trong lượt tự động |\n" % (so, viec, gio, bang_cell(bang_chung, 200))
    return s[:x.end()] + hang + s[x.end():]


def thay_khoi(s, ten, noi_dung):
    bd, kt = "<!-- AUTO:%s:BAT-DAU -->" % ten, "<!-- AUTO:%s:KET-THUC -->" % ten
    khoi = "%s\n%s\n%s" % (bd, noi_dung.strip(), kt)
    if bd in s and kt in s:
        return re.sub(re.escape(bd) + r".*?" + re.escape(kt), lambda _: khoi, s, flags=re.S)
    return s.rstrip("\n") + "\n\n" + khoi + "\n"


def ghi_ket_qua(d, moi, meta, nghien_cuu, nguon, cn, cs):
    """Ghi mọi thứ AI trả về vào đúng chỗ. Trả list đường dẫn đã ghi (để báo cáo)."""
    ngay, gio = hom_nay(), gio_ngan()
    ra = []
    # 1. nhật ký công khai
    bullets = loc_nhat_ky_cong_khai(ds_chu(d.get("nhat_ky_cong_khai")))
    tep = os.path.join(CONG_KHAI, ngay + ".md")
    if not bullets and moi:   # bộ lọc loại hết thì vẫn phải có nhật ký thật thà
        bullets = [sach("Hôm nay tôi thử: %s." % ((d.get("thi_nghiem_hom_nay") or {}).get("ten") or "một hướng mới"), 200)]
    if bullets:
        if moi:
            tieu = sach(d.get("tieu_de_ngay") or "Hôm nay tôi làm việc", 120)
            ghi_tep(tep, "# %s\n\n%s\n" % (tieu, "\n".join("- " + b for b in bullets[:6])))
        else:
            cu = doc_tep(tep).rstrip("\n")
            if len([l for l in cu.splitlines() if l.startswith("- ")]) < 10:
                ghi_tep(tep, cu + "\n" + "\n".join("- " + b for b in bullets[:2]) + "\n")
        ra.append(os.path.relpath(tep, GOC))
    # 2. nhật ký nội bộ
    nb = [sach(x, 300) for x in ds_chu(d.get("nhat_ky_noi_bo"))[:3]] or ["(AI không ghi dòng nội bộ)"]
    nk = os.path.join(KD, "NHAT-KY.md")
    ghi_tep(nk, doc_tep(nk, "# Nhật ký làm việc\n").rstrip("\n") + "\n" + "\n".join(
        "%s · %s · %s/%s · %s" % (gio, "ngày mới" if moi else "làm tiếp", meta["nha"], meta["model"], x) for x in nb) + "\n")
    # 3. nghiên cứu (bằng chứng thật: chữ do AI tóm tắt + danh sách nguồn tìm được)
    ten_nc = ""
    if nghien_cuu:
        tep_nc = os.path.join(NGHIEN_CUU, ngay + ".md")
        ghi_tep(tep_nc, "# Nghiên cứu %s\n\n%s\n\n## Nguồn tìm được\n%s\n" % (
            ngay, sach(nghien_cuu, 6000), "\n".join("- %s %s" % (sach(n["tieu_de"], 80), n["url"]) for n in nguon[:12]) or "- (không có danh sách nguồn)"))
        ten_nc = "kinh-doanh/nghien-cuu/%s.md" % ngay
        ra.append(ten_nc)
    # 4. ý tưởng -> CO-HOI.md (bỏ trùng tên)
    co_hoi = os.path.join(KD, "CO-HOI.md")
    s = doc_tep(co_hoi)
    da_co = [x.lower() for x in y_tuong_da_co()]
    rows = len([l for l in s.splitlines() if re.match(r"^\|\s*\d+\s*\|", l)])
    them = []
    for y in (d.get("y_tuong") or [])[:4]:
        if not isinstance(y, dict) or not str(y.get("ten", "")).strip():
            continue
        ten = bang_cell(y["ten"], 80)
        if any(SequenceMatcher(None, ten.lower(), x).ratio() > 0.8 for x in da_co):
            continue
        da_co.append(ten.lower())
        ly_do = bang_cell(y.get("vi_sao_co_nhu_cau"), 160)
        if ten_nc and "giả thuyết" not in ly_do.lower():
            bc = "Có tìm web (xem %s). %s" % (ten_nc, ly_do)
        else:
            bc = "GIẢ THUYẾT, chưa kiểm: " + re.sub(r"^giả thuyết,? ?(chưa kiểm)?:? ?", "", ly_do, flags=re.I)
        them.append("| %d | %s: %s | %s | %s | %s | 0đ | %s | %s |" % (
            rows + len(them) + 1, ten, bang_cell(y.get("mo_ta"), 200), bc, bang_cell(y.get("tien_du_kien_thang"), 60),
            bang_cell(y.get("buoc_dau_tien"), 140), bang_cell(y.get("can_thay_lam"), 100) or "không",
            "ĐỀ XUẤT %s (điểm %s/10)" % (ngay, bang_cell(y.get("diem"), 4))))
    if them and "| # |" in s:
        ghi_tep(co_hoi, s.rstrip("\n") + "\n" + "\n".join(them) + "\n")
        ra.append("kinh-doanh/CO-HOI.md (+%d ý tưởng)" % len(them))
    # 5. sản phẩm
    sp = d.get("san_pham") or {}
    tep_sp = os.path.join(SAN_PHAM, "%s-%s.md" % (ngay, slug(str(sp.get("tieu_de", "")))))
    n = 2
    while os.path.exists(tep_sp):
        tep_sp = os.path.join(SAN_PHAM, "%s-%s-%d.md" % (ngay, slug(str(sp.get("tieu_de", ""))), n))
        n += 1
    ghi_tep(tep_sp, "# %s\n\n> Bản nháp do AI viết (%s/%s, %s). Thầy đọc lại trước khi đăng. AI chưa dùng thử sản phẩm nào; "
                    "nếu có link tiếp thị phải ghi rõ có thể nhận hoa hồng.\n\n%s\n" % (
                        sach(sp.get("tieu_de"), 120), meta["nha"], meta["model"], gio, sach(sp.get("noi_dung_md"), 12000)))
    ra.append(os.path.relpath(tep_sp, GOC))
    # 6. bảng việc
    bv = os.path.join(KD, "BANG-VIEC.md")
    s = doc_tep(bv)
    if s:
        for x in (d.get("viec_xong") or [])[:2]:
            try:
                s = chuyen_xong(s, int(x["so"]), x.get("bang_chung", "") or os.path.relpath(tep_sp, GOC), gio)
            except (KeyError, TypeError, ValueError):
                pass
        s = them_viec(s, ds_chu(d.get("viec_moi"))[:3], gio, "lượt tự động " + ngay)
        ghi_tep(bv, s)
    # 7. mục Cần thầy + hướng đang đi (khối tự động trong KE-HOACH.md)
    kh = os.path.join(KD, "KE-HOACH.md")
    s = doc_tep(kh)
    ct = ds_chu(d.get("can_thay"))[:6]
    s = thay_khoi(s, "CAN-THAY", "\n".join("- (%s) %s" % (gio, sach(x, 300)) for x in ct) or "- (chưa có việc mới cần thầy)")
    tn = d.get("thi_nghiem_hom_nay") or {}
    if moi and str(tn.get("ten", "")).strip():
        s = thay_khoi(s, "HUONG", "- (%s) Thí nghiệm: %s. Việc cụ thể: %s. Đo bằng: %s" % (
            ngay, sach(tn.get("ten"), 120), sach(tn.get("viec_cu_the"), 200), sach(tn.get("do_bang_so_nao"), 120)))
    ghi_tep(kh, s)
    # 8. rà soát
    if str(d.get("ra_soat_md", "")).strip():
        ghi_tep(os.path.join(KD, "RA-SOAT.md"), "# Rà soát %s\n\n%s\n" % (ngay, sach(d["ra_soat_md"], 6000)))
        ra.append("kinh-doanh/RA-SOAT.md")
    return ra


def ghi_trang_thai(ket_qua, moi, meta, lan, ra, ghi_chu=""):
    dong = ["# Trạng thái lượt gần nhất (máy tự ghi, thầy mở tệp này để biết AI có đang làm việc không)", "",
            "- Lúc: %s (giờ Việt Nam)" % gio_ngan(),
            "- Chế độ: %s" % ("ngày mới" if moi else "làm tiếp trong ngày"),
            "- Kết quả: **%s**" % ket_qua]
    if meta:
        dong.append("- AI đã dùng: %s / %s" % (meta["nha"], meta["model"]))
    dong.append("- Số lần gọi API trong lượt: %d" % SO_LAN_GOI)
    if ghi_chu:
        dong.append("- Ghi chú: %s" % ghi_chu)
    if ra:
        dong += ["- Đã ghi:"] + ["  - " + x for x in ra]
    if lan:
        dong += ["- Các lần thử:"] + ["  - %s / %s: %s %s" % (a, b, c, sach(e, 100)) for a, b, c, e in lan[-12:]]
    ghi_tep(os.path.join(KD, "TRANG-THAI-LUOT.md"), "\n".join(dong) + "\n")


def xu_ly_that_bai(moi, lan):
    ngay, gio = hom_nay(), gio_ngan()
    hint = chan_doan(lan)
    if moi:
        ghi_tep(os.path.join(CONG_KHAI, ngay + ".md"),
                "# Hôm nay tôi chưa làm được gì\n%s\n- Tôi muốn nghĩ ý tưởng mới nhưng các dịch vụ AI miễn phí không trả lời được lúc này.\n"
                "- Tôi không bịa ý tưởng cho đủ chỉ tiêu. Lượt sau tôi sẽ thử lại, và đã báo thầy Thành.\n" % MARKER_LOI)
    nk = os.path.join(KD, "NHAT-KY.md")
    ghi_tep(nk, doc_tep(nk, "# Nhật ký làm việc\n").rstrip("\n") + "\n%s · LỖI AI · %s\n" % (gio, hint))
    kh = os.path.join(KD, "KE-HOACH.md")
    ghi_tep(kh, thay_khoi(doc_tep(kh), "CAN-THAY", "- (%s) **AI chưa chạy được**: %s" % (gio, hint)))


# ---------- chính ----------

def main():
    if os.path.exists(os.path.join(GOC, "DUNG")):
        print("có tệp DUNG — không làm.")
        return 0
    cn, cs = vi.ket_noi(), vi.nap_chinh_sach()
    tt = vi.trang_thai_song(cn, cs)
    if tt in ("KILL_SWITCH", "PAUSED_BY_OWNER", "HALTED"):
        print("trạng thái %s — không làm." % tt)
        return 0
    hn = bay_gio().date()
    moi = che_do() == "ngay-moi"
    he = doc_tep(os.path.join(GOC, "HIEN-PHAP.md"))
    lan, nghien_cuu, nguon = [], "", []
    try:
        if moi and tt == "ACTIVE":
            try:
                text, m = goi_ai(he, prompt_nghien_cuu(hn, GOC_NHIN[hn.toordinal() % len(GOC_NHIN)]),
                                 json_mode=False, tim_kiem=True, lan=lan)
                nghien_cuu, nguon = text, m["nguon"]
            except HetCach:
                print("không tìm web được; ý tưởng hôm nay sẽ ghi là giả thuyết.")
        prompt = dung_prompt(cn, cs, moi, nghien_cuu, hn)
        text, meta = goi_ai(he, prompt, json_mode=True,
                            kiem=lambda t: "không đọc được JSON" if tach_json(t) is None else loi_ket_qua(tach_json(t), moi),
                            lan=lan)
        ra = ghi_ket_qua(tach_json(text), moi, meta, nghien_cuu, nguon, cn, cs)
        ghi_trang_thai("THÀNH CÔNG", moi, meta, lan, ra)
        print("OK %s/%s, %d lần gọi, đã ghi: %s" % (meta["nha"], meta["model"], SO_LAN_GOI, "; ".join(ra)))
        rc = 0
    except HetCach as e:
        lan = e.args[0] if e.args else lan
        xu_ly_that_bai(moi, lan)
        ghi_trang_thai("THẤT BẠI", moi, None, lan, [], chan_doan(lan))
        print("THẤT BẠI: %s" % chan_doan(lan))
        rc = 0
    finally:
        if SO_LAN_GOI:
            vi.ghi_quota(cn, "gemini", SO_LAN_GOI)   # khoá "gemini" trong chính sách nay đếm MỌI lượt gọi AI
    return rc


if __name__ == "__main__":
    sys.exit(main())
