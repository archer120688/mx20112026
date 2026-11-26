#!/usr/bin/env python3
"""Công cụ cho việc hằng ngày: đọc kết quả xổ số, dự đoán TẤT CẢ các giải của TẤT CẢ các đài ngày mai, chấm điểm.
Agent KHÔNG được sửa tệp này.

Dữ liệu (mỗi ngày một tệp, chỉ trong ra/xo-so/):
  ket-qua/YYYY-MM-DD.json  KẾT QUẢ THẬT đọc từ trang xổ số (agent ghi, có thể bổ sung đài dần trong ngày):
     {"ngay":"2026-11-26","nguon":"https://...","dai":[{"ten":"TP.HCM","mien":"Nam","giai":{"G8":["12"],"G7":["123"],...,"DB":["123456"]}}]}
  du-doan/YYYY-MM-DD.json  dự đoán cho ngày đó, do lệnh tao-du-doan sinh (agent không tự gõ số).

Số giải: Nam/Trung: G8(1×2 số) G7(1×3) G6(3×4) G5(1×4) G4(7×5) G3(2×5) G2(1×5) G1(1×5) DB(1×6)
         Bắc:       DB(1×5) G1(1×5) G2(2×5) G3(6×5) G4(4×4) G5(6×4) G6(3×3) G7(4×2)

Lệnh:  can-lam                         việc còn thiếu (giờ Việt Nam)
       kiem                            kiểm định dạng
       tao-du-doan NGÀY "Đài:Miền"...  sinh dự đoán từ dữ liệu các kỳ trước (miền: Nam|Trung|Bac). Không ghi đè.
       cham                            chấm điểm → ra/xo-so/bang.json
"""
import glob, json, os, random, re, subprocess, sys, unicodedata
from datetime import date, datetime, timedelta, timezone

GOC = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
XS = os.path.join(GOC, "ra", "xo-so")
VN = timezone(timedelta(hours=7))
NT = [("G8", 1, 2), ("G7", 1, 3), ("G6", 3, 4), ("G5", 1, 4), ("G4", 7, 5), ("G3", 2, 5), ("G2", 1, 5), ("G1", 1, 5), ("DB", 1, 6)]
BAC = [("DB", 1, 5), ("G1", 1, 5), ("G2", 2, 5), ("G3", 6, 5), ("G4", 4, 4), ("G5", 6, 4), ("G6", 3, 3), ("G7", 4, 2)]
SPEC = {"Nam": NT, "Trung": NT, "Bac": BAC}
HAN_NOP = 15          # dự đoán phải được commit trước 15:00 ngày quay
GIO_XEM = {"Nam": (16, 45), "Trung": (17, 45), "Bac": (18, 45)}   # từ giờ này mới có kết quả đủ của miền đó
GIO_DU_DOAN = 19      # từ 19:00 mới dự đoán ngày mai (đã có kết quả cả 3 miền)
DECAY = 0.97          # kỳ càng gần càng nặng ký


def hom_nay():
    return datetime.now(VN)


def chuan(ten):
    s = unicodedata.normalize("NFD", ten.lower().replace("đ", "d"))
    s = "".join(c for c in s if unicodedata.category(c) != "Mn")
    s = re.sub(r"^(tp|thanh pho|dai|xs|xo so)\s*", "", s)
    s = re.sub(r"[^a-z0-9]", "", s)
    return {"hochiminh": "hcm", "saigon": "hcm"}.get(s, s)


def mien_chuan(m):
    c = chuan(str(m))
    return {"nam": "Nam", "trung": "Trung", "bac": "Bac"}.get(c.replace("mien", ""))


def doc(tep):
    with open(tep, encoding="utf-8") as f:
        return json.load(f)


def cac_tep(loai):
    return sorted(glob.glob(os.path.join(XS, loai, "????-??-??.json")))


def ngay_tu_tep(tep):
    return os.path.basename(tep)[:10]


def kiem_dai(x, ten_tep, loi):
    m = mien_chuan(x.get("mien", ""))
    if not str(x.get("ten", "")).strip() or not m:
        loi.append("%s: đài thiếu ten hoặc mien sai (%s)" % (ten_tep, x.get("ten"))); return
    g = x.get("giai", {})
    for k, n, dai in SPEC[m]:
        ds = g.get(k)
        if not isinstance(ds, list) or len(ds) != n or not all(re.fullmatch(r"\d{%d}" % dai, str(v)) for v in ds):
            loi.append("%s: %s giải %s phải có %d số, mỗi số %d chữ số" % (ten_tep, x["ten"], k, n, dai))


def kiem():
    loi = []
    for tep in cac_tep("ket-qua"):
        try:
            d = doc(tep); n = ngay_tu_tep(tep)
            if d.get("ngay") != n: loi.append("%s: ngay khác tên tệp" % tep)
            if date.fromisoformat(n) > hom_nay().date(): loi.append("%s: kết quả của ngày chưa tới" % tep)
            if not str(d.get("nguon", "")).startswith("http"): loi.append("%s: thiếu nguon (đường dẫn trang đã đọc)" % tep)
            if not d.get("dai"): loi.append("%s: không có đài nào" % tep)
            for x in d.get("dai", []): kiem_dai(x, tep, loi)
        except Exception as e:
            loi.append("%s: %s" % (tep, e))
    for tep in cac_tep("du-doan"):
        try:
            d = doc(tep)
            if d.get("ngay") != ngay_tu_tep(tep): loi.append("%s: ngay khác tên tệp" % tep)
            if not d.get("du_doan"): loi.append("%s: không có dự đoán" % tep)
            for x in d.get("du_doan", []): kiem_dai(x, tep, loi)
        except Exception as e:
            loi.append("%s: %s" % (tep, e))
    for l in loi: print("LỖI:", l)
    return not loi


def can_lam():
    b = hom_nay(); h = b.date()
    thieu = []
    hqua = (h - timedelta(days=1)).isoformat()
    if os.path.exists(os.path.join(XS, "du-doan", hqua + ".json")) and not os.path.exists(os.path.join(XS, "ket-qua", hqua + ".json")):
        thieu.append({"viec": "doc_ket_qua", "ngay": hqua, "mien": ["Nam", "Trung", "Bac"]})
    tep = os.path.join(XS, "ket-qua", h.isoformat() + ".json")
    co = {}
    if os.path.exists(tep):
        for x in doc(tep).get("dai", []): co.setdefault(mien_chuan(x.get("mien", "")), []).append(x["ten"])
    can = [m for m, (gio, ph) in GIO_XEM.items() if (b.hour, b.minute) >= (gio, ph) and m not in co]
    if can:
        thieu.append({"viec": "doc_ket_qua", "ngay": h.isoformat(), "mien": can, "da_co": co})
    mai = (h + timedelta(days=1)).isoformat()
    if b.hour >= GIO_DU_DOAN and not os.path.exists(os.path.join(XS, "du-doan", mai + ".json")) and not can:
        thieu.append({"viec": "du_doan", "ngay": mai, "ghi_chu": "xem lịch mở thưởng ngày mai trên trang xổ số, liệt kê TẤT CẢ đài rồi chạy tao-du-doan"})
    print(json.dumps({"bay_gio": b.strftime("%F %H:%M"), "con_thieu": thieu or "XONG_HOM_NAY"}, ensure_ascii=False))


def lich_su(truoc):
    ds = []
    for t in cac_tep("ket-qua"):
        n = ngay_tu_tep(t)
        if n < truoc:
            ds.append((n, doc(t)))
    return ds


def sinh_dai(ngay, ten, mien, ls):
    """Số cho từng giải: mỗi chữ số chọn theo tần suất các kỳ trước (kỳ gần nặng hơn, cùng đài nặng gấp đôi), có làm mượt."""
    mt = datetime.fromisoformat(ngay)
    giai = {}
    for k, n, dai in SPEC[mien]:
        dem = [[1.0] * 10 for _ in range(dai)]
        for ng, d in ls:
            tuoi = (mt - datetime.fromisoformat(ng)).days
            for x in d["dai"]:
                if mien_chuan(x.get("mien", "")) != mien: continue
                w = DECAY ** tuoi * (2.0 if chuan(x["ten"]) == chuan(ten) else 1.0)
                for so in x["giai"].get(k, []):
                    for i, c in enumerate(str(so)): dem[i][int(c)] += w
        rng = random.Random("%s|%s|%s" % (ngay, chuan(ten), k))
        ra = []
        for _ in range(n):
            for _thu in range(30):
                so = "".join(str(rng.choices(range(10), weights=dem[i])[0]) for i in range(dai))
                if so not in ra: break
            ra.append(so)
        giai[k] = ra
    return {"ten": ten, "mien": mien, "giai": giai}


def tao_du_doan(ngay, dais):
    if date.fromisoformat(ngay) <= hom_nay().date():
        sys.exit("chỉ được dự đoán cho ngày sau hôm nay")
    tep = os.path.join(XS, "du-doan", ngay + ".json")
    if os.path.exists(tep):
        sys.exit("đã có dự đoán cho %s, không ghi đè" % ngay)
    ls = lich_su(ngay)
    out = []
    for s in dais:
        ten, _, m = s.rpartition(":")
        mien = mien_chuan(m)
        if not ten.strip() or not mien: sys.exit('sai đài "%s" (dạng "Cần Thơ:Nam")' % s)
        out.append(sinh_dai(ngay, ten.strip(), mien, ls))
    if not out: sys.exit("cần ít nhất một đài")
    os.makedirs(os.path.dirname(tep), exist_ok=True)
    with open(tep, "w", encoding="utf-8") as f:
        json.dump({"ngay": ngay, "so_ky_du_lieu": len(ls), "du_doan": out}, f, ensure_ascii=False, indent=1)
    print("đã tạo %s: %d đài, dựa trên %d ngày dữ liệu" % (tep, len(out), len(ls)))


def gio_commit_dau(tep):
    try:
        r = subprocess.run(["git", "-C", GOC, "log", "--diff-filter=A", "--format=%cI", "--", os.path.relpath(tep, GOC)],
                           capture_output=True, text=True, timeout=30)
        dong = [x for x in r.stdout.split() if x]
        return datetime.fromisoformat(dong[-1]) if dong else None
    except Exception:
        return None


def cham():
    if not kiem():
        sys.exit("dữ liệu sai, không chấm")
    kq = {ngay_tu_tep(t): doc(t) for t in cac_tep("ket-qua")}
    dong, muon, khong_khop = [], [], []
    tong = {}
    for tep in cac_tep("du-doan"):
        n = ngay_tu_tep(tep)
        if n not in kq: continue
        t = gio_commit_dau(tep)
        if t and t > datetime.fromisoformat(n + "T%02d:00:00+07:00" % HAN_NOP):
            muon.append(n); continue
        theo = {chuan(x["ten"]): x for x in kq[n]["dai"]}
        for p in doc(tep)["du_doan"]:
            x = theo.get(chuan(p["ten"]))
            if not x:
                khong_khop.append(n + " " + p["ten"]); continue
            so_trung, tong_so = [], 0
            for k, nn, _ in SPEC[mien_chuan(p["mien"])]:
                thuc = set(x["giai"].get(k, []))
                for so in p["giai"].get(k, []):
                    tong_so += 1
                    v = tong.setdefault(k, {"so_lan": 0, "trung": 0}); v["so_lan"] += 1
                    if so in thuc:
                        v["trung"] += 1; so_trung.append({"giai": k, "so": so})
            dong.append({"ngay": n, "dai": p["ten"], "mien": mien_chuan(p["mien"]), "tong": tong_so, "trung": len(so_trung), "so_trung": so_trung})
    dong.sort(key=lambda r: (r["ngay"], r["dai"]), reverse=True)
    out = {"cap_nhat": hom_nay().isoformat(timespec="minutes"), "so_ky_du_lieu": len(kq), "tong": tong,
           "tong_chung": {"so_lan": sum(v["so_lan"] for v in tong.values()), "trung": sum(v["trung"] for v in tong.values())},
           "dong": dong[:150], "nop_muon": muon, "khong_khop_dai": khong_khop[:50]}
    os.makedirs(XS, exist_ok=True)
    with open(os.path.join(XS, "bang.json"), "w", encoding="utf-8") as f:
        json.dump(out, f, ensure_ascii=False, indent=1)
    print("đã chấm %d dòng đài-ngày, nộp muộn %d ngày" % (len(dong), len(muon)))


if __name__ == "__main__":
    lenh = sys.argv[1] if len(sys.argv) > 1 else ""
    if lenh == "can-lam": can_lam()
    elif lenh == "kiem": sys.exit(0 if kiem() else 1)
    elif lenh == "tao-du-doan" and len(sys.argv) >= 4: tao_du_doan(sys.argv[2], sys.argv[3:])
    elif lenh == "cham": cham()
    else: sys.exit(__doc__)
