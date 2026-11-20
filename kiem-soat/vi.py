#!/usr/bin/env python3
"""Sổ cái thu nhập + bộ đếm quota miễn phí của agent kiếm tiền (dự án của thầy Thành).

Không có vốn, agent không chi tiền. Thứ khan hiếm ở đây là QUOTA MIỄN PHÍ mỗi ngày (lượt gọi AI, số video, số bài...).
- Sổ cái chỉ-ghi-thêm, mỗi dòng nối băm với dòng trước (sửa lịch sử là kiem-tra báo hỏng).
- Agent chỉ được gọi: trang-thai, bao-cao, xin-quota, kiem-tra.
- Chỉ thầy Thành hoặc script nền gọi: ghi-thu, ghi-quota, tam-dung, tiep-tuc.
Tiền tính bằng VND, số nguyên.
"""
import argparse
import hashlib
import json
import os
import sqlite3
import sys
from datetime import datetime, date

GOC = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DB = os.environ.get("VI_DB", os.path.join(GOC, "du-lieu", "so-cai.db"))
CHINH_SACH = os.environ.get("VI_CHINH_SACH", os.path.join(GOC, "chinh-sach.json"))
FILE_DUNG = os.environ.get("VI_FILE_DUNG", os.path.join(GOC, "DUNG"))
GENESIS = "0" * 64

SCHEMA = """
CREATE TABLE IF NOT EXISTS but_toan (
  id INTEGER PRIMARY KEY,
  thoi_gian TEXT NOT NULL,
  so_tien INTEGER NOT NULL CHECK (so_tien > 0),
  loai_thu TEXT NOT NULL CHECK (loai_thu IN ('donate','shopee')),
  nguon TEXT NOT NULL CHECK (nguon IN ('ngan-hang','shopee','chu')),
  ma_giao_dich TEXT NOT NULL UNIQUE,
  bang_chung TEXT NOT NULL,
  ghi_chu TEXT,
  hash_truoc TEXT NOT NULL,
  hash TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS quota (
  id INTEGER PRIMARY KEY, thoi_gian TEXT NOT NULL, ngay TEXT NOT NULL, nguon TEXT NOT NULL, so INTEGER NOT NULL
);
CREATE TABLE IF NOT EXISTS nhat_ky (
  id INTEGER PRIMARY KEY, thoi_gian TEXT NOT NULL, tac_nhan TEXT NOT NULL, hanh_dong TEXT NOT NULL,
  ket_qua TEXT NOT NULL, chi_tiet TEXT
);
CREATE TABLE IF NOT EXISTS he_thong (khoa TEXT PRIMARY KEY, gia_tri TEXT);
CREATE TRIGGER IF NOT EXISTS khong_sua_but_toan BEFORE UPDATE ON but_toan
  BEGIN SELECT RAISE(ABORT, 'but_toan chi duoc ghi them'); END;
CREATE TRIGGER IF NOT EXISTS khong_xoa_but_toan BEFORE DELETE ON but_toan
  BEGIN SELECT RAISE(ABORT, 'but_toan chi duoc ghi them'); END;
"""


def bay_gio():
    return datetime.now().isoformat(timespec="seconds")


def hom_nay():
    return bay_gio()[:10]


def nap_chinh_sach():
    with open(CHINH_SACH, encoding="utf-8") as f:
        return json.load(f)


def ket_noi(db=None):
    db = db or DB
    if db != ":memory:":
        os.makedirs(os.path.dirname(db), exist_ok=True)
    cn = sqlite3.connect(db, timeout=30, isolation_level=None)
    cn.row_factory = sqlite3.Row
    cn.executescript(SCHEMA)
    cn.execute("INSERT OR IGNORE INTO he_thong VALUES('ngay_bat_dau', ?)", (hom_nay(),))
    return cn


def ghi_nhat_ky(cn, tac_nhan, hanh_dong, ket_qua, chi_tiet=None):
    cn.execute("INSERT INTO nhat_ky(thoi_gian,tac_nhan,hanh_dong,ket_qua,chi_tiet) VALUES(?,?,?,?,?)",
               (bay_gio(), tac_nhan, hanh_dong, ket_qua,
                json.dumps(chi_tiet, ensure_ascii=False) if chi_tiet is not None else None))


# ---------- Sổ thu ----------

def _bam(truoc, tg, so_tien, loai_thu, nguon, ma, bang_chung, ghi_chu):
    s = "|".join([truoc, tg, str(so_tien), loai_thu, nguon, ma, bang_chung, ghi_chu or ""])
    return hashlib.sha256(s.encode("utf-8")).hexdigest()


def ghi_thu(cn, so_tien, ma_giao_dich, bang_chung, loai_thu, nguon="chu", ghi_chu=None):
    """Ghi tiền đã về thật. Trả (ket_qua, ly_do). Trùng mã giao dịch thì bỏ qua."""
    if not isinstance(so_tien, int) or so_tien <= 0 or not ma_giao_dich or not bang_chung:
        return "TU_CHOI", "thiếu hoặc sai số tiền/mã giao dịch/bằng chứng"
    if loai_thu not in ("donate", "shopee") or nguon not in ("ngan-hang", "shopee", "chu"):
        return "TU_CHOI", "loại thu hoặc nguồn không hợp lệ"
    cn.execute("BEGIN IMMEDIATE")
    try:
        if cn.execute("SELECT 1 FROM but_toan WHERE ma_giao_dich=?", (ma_giao_dich,)).fetchone():
            cn.execute("COMMIT")
            return "TRUNG", "giao dịch đã ghi rồi"
        r = cn.execute("SELECT hash FROM but_toan ORDER BY id DESC LIMIT 1").fetchone()
        truoc = r[0] if r else GENESIS
        tg = bay_gio()
        h = _bam(truoc, tg, so_tien, loai_thu, nguon, ma_giao_dich, bang_chung, ghi_chu)
        cn.execute("INSERT INTO but_toan(thoi_gian,so_tien,loai_thu,nguon,ma_giao_dich,bang_chung,ghi_chu,hash_truoc,hash) "
                   "VALUES(?,?,?,?,?,?,?,?,?)", (tg, so_tien, loai_thu, nguon, ma_giao_dich, bang_chung, ghi_chu, truoc, h))
        ghi_nhat_ky(cn, nguon, "ghi-thu", "DA_GHI", dict(so_tien=so_tien, loai_thu=loai_thu))
        cn.execute("COMMIT")
    except Exception:
        cn.execute("ROLLBACK")
        raise
    return "DA_GHI", "đã ghi thu %d" % so_tien


def kiem_tra(cn):
    """Duyệt chuỗi băm. Trả (ok, so_dong, hash_dau_chuoi_hoac_id_hong)."""
    truoc, n = GENESIS, 0
    for r in cn.execute("SELECT * FROM but_toan ORDER BY id"):
        if r["hash_truoc"] != truoc or r["hash"] != _bam(
                truoc, r["thoi_gian"], r["so_tien"], r["loai_thu"], r["nguon"], r["ma_giao_dich"], r["bang_chung"], r["ghi_chu"]):
            return False, n, "hỏng tại dòng id=%d" % r["id"]
        truoc, n = r["hash"], n + 1
    return True, n, truoc[:12]


# ---------- Quota ----------

def da_dung_hom_nay(cn, nguon, ngay=None):
    return cn.execute("SELECT COALESCE(SUM(so),0) FROM quota WHERE ngay=? AND nguon=?",
                      (ngay or hom_nay(), nguon)).fetchone()[0]


def trang_thai_song(cn, cs):
    if os.path.exists(FILE_DUNG):
        return "KILL_SWITCH"
    r = cn.execute("SELECT gia_tri FROM he_thong WHERE khoa='tam_dung'").fetchone()
    if r and r[0] == "1":
        return "PAUSED_BY_OWNER"
    han = cs["han_muc_ngay"]["gemini"]
    ty_le = da_dung_hom_nay(cn, "gemini") / han if han > 0 else 1
    if ty_le >= cs["nguong"]["dung"]:
        return "HALTED"  # hết quota AI hôm nay; sang ngày mới tự chạy lại
    if ty_le >= cs["nguong"]["tiet_kiem"]:
        return "THRIFT_MODE"
    return "ACTIVE"


def ghi_quota(cn, nguon, so):
    if so <= 0:
        return "TU_CHOI", "số phải dương"
    cn.execute("INSERT INTO quota(thoi_gian,ngay,nguon,so) VALUES(?,?,?,?)", (bay_gio(), hom_nay(), nguon, so))
    return "DA_GHI", "đã ghi %s +%d" % (nguon, so)


def xin_quota(cn, cs, nguon, so):
    """Agent xin làm thêm `so` đơn vị `nguon` (video, bai-dang, san-pham). DUYET thì tự ghi luôn."""
    cn.execute("BEGIN IMMEDIATE")
    try:
        tt = trang_thai_song(cn, cs)
        han = cs["han_muc_ngay"].get(nguon)
        if nguon == "gemini" or han is None:
            kq = ("TU_CHOI", "nguồn quota không hợp lệ: " + nguon)
        elif so <= 0:
            kq = ("TU_CHOI", "số phải dương")
        elif tt in ("KILL_SWITCH", "PAUSED_BY_OWNER", "HALTED"):
            kq = ("TU_CHOI", "hệ thống đang " + tt)
        elif tt == "THRIFT_MODE" and nguon == "san-pham":
            kq = ("TU_CHOI", "THRIFT_MODE: không tìm sản phẩm mới, chỉ làm nốt việc đang dở")
        elif da_dung_hom_nay(cn, nguon) + so > han:
            kq = ("TU_CHOI", "hết hạn mức hôm nay của %s (%d)" % (nguon, han))
        else:
            cn.execute("INSERT INTO quota(thoi_gian,ngay,nguon,so) VALUES(?,?,?,?)", (bay_gio(), hom_nay(), nguon, so))
            kq = ("DUYET", "còn %d hôm nay" % (han - da_dung_hom_nay(cn, nguon)))
        ghi_nhat_ky(cn, "agent", "xin-quota", kq[0], dict(nguon=nguon, so=so, ly_do=kq[1]))
        cn.execute("COMMIT")
    except Exception:
        cn.execute("ROLLBACK")
        raise
    return kq


# ---------- Báo cáo ----------

def thong_ke(cn):
    thu = cn.execute("SELECT COALESCE(SUM(so_tien),0) FROM but_toan").fetchone()[0]
    donate = cn.execute("SELECT COALESCE(SUM(so_tien),0) FROM but_toan WHERE loai_thu='donate'").fetchone()[0]
    shopee = cn.execute("SELECT COALESCE(SUM(so_tien),0) FROM but_toan WHERE loai_thu='shopee'").fetchone()[0]
    bd = cn.execute("SELECT gia_tri FROM he_thong WHERE khoa='ngay_bat_dau'").fetchone()[0]
    ngay_chay = (date.fromisoformat(hom_nay()) - date.fromisoformat(bd)).days + 1
    r = cn.execute("SELECT MAX(substr(thoi_gian,1,10)) FROM but_toan").fetchone()[0]
    ngay_khong_thu = (date.fromisoformat(hom_nay()) - date.fromisoformat(r or bd)).days
    return dict(thu=thu, donate=donate, shopee=shopee, ngay_chay=ngay_chay, ngay_khong_thu=ngay_khong_thu)


def bao_cao(cn, cs):
    tt = trang_thai_song(cn, cs)
    s = thong_ke(cn)
    d = lambda n: "{:,}".format(int(n)).replace(",", ".") + "đ"
    q = ["%s %d/%d" % (k, da_dung_hom_nay(cn, k), v) for k, v in cs["han_muc_ngay"].items()]
    ok, n, dau = kiem_tra(cn)
    dong = [
        "Trạng thái: " + tt,
        "Quota miễn phí hôm nay: " + " · ".join(q),
        "Tiền thật đã về: %s (donate %s · Shopee %s) · %d khoản" % (d(s["thu"]), d(s["donate"]), d(s["shopee"]), n),
        "Chạy được %d ngày · %d ngày liên tiếp chưa có đồng nào" % (s["ngay_chay"], s["ngay_khong_thu"]),
        "Sổ cái: " + ("toàn vẹn, mã đầu chuỗi " + dau if ok else "HỎNG — " + dau),
    ]
    if s["ngay_khong_thu"] >= cs["ngay_khong_thu_phai_ra_soat"]:
        dong.append("PHẢI RÀ SOÁT: quá %d ngày không thu — viết kinh-doanh/RA-SOAT.md trước khi làm việc khác."
                    % cs["ngay_khong_thu_phai_ra_soat"])
    return "\n".join(dong)


def main(argv=None):
    p = argparse.ArgumentParser(prog="vi.py")
    sub = p.add_subparsers(dest="lenh", required=True)
    sub.add_parser("trang-thai")
    sub.add_parser("bao-cao")
    sub.add_parser("kiem-tra")
    a = sub.add_parser("xin-quota")
    a.add_argument("--nguon", required=True)
    a.add_argument("--so", type=int, default=1)
    # --- Chỉ dành cho thầy / script nền ---
    a = sub.add_parser("ghi-quota")
    a.add_argument("--nguon", required=True)
    a.add_argument("--so", type=int, required=True)
    a = sub.add_parser("ghi-thu")
    a.add_argument("--so-tien", type=int, required=True)
    a.add_argument("--ma-giao-dich", required=True)
    a.add_argument("--bang-chung", required=True)
    a.add_argument("--loai-thu", choices=["donate", "shopee"], required=True)
    a.add_argument("--nguon", choices=["ngan-hang", "shopee", "chu"], default="chu")
    a.add_argument("--ghi-chu")
    sub.add_parser("tam-dung")
    sub.add_parser("tiep-tuc")
    k = p.parse_args(argv)

    cs = nap_chinh_sach()
    cn = ket_noi()
    L = k.lenh
    if L == "trang-thai":
        print(json.dumps(dict(trang_thai=trang_thai_song(cn, cs), **thong_ke(cn)), ensure_ascii=False))
    elif L == "bao-cao":
        print(bao_cao(cn, cs))
    elif L == "kiem-tra":
        ok, n, dau = kiem_tra(cn)
        print(("OK %d dòng, mã đầu chuỗi %s" % (n, dau)) if ok else "HỎNG: " + dau)
        return 0 if ok else 2
    elif L == "xin-quota":
        kq, ly_do = xin_quota(cn, cs, k.nguon, k.so)
        print(json.dumps(dict(ket_qua=kq, ly_do=ly_do), ensure_ascii=False))
        return 0 if kq == "DUYET" else 2
    elif L == "ghi-quota":
        print(ghi_quota(cn, k.nguon, k.so)[1])
    elif L == "ghi-thu":
        kq, ly_do = ghi_thu(cn, k.so_tien, k.ma_giao_dich, k.bang_chung, k.loai_thu, k.nguon, k.ghi_chu)
        print(ly_do)
        return 0 if kq in ("DA_GHI", "TRUNG") else 2
    elif L == "tam-dung":
        cn.execute("INSERT OR REPLACE INTO he_thong VALUES('tam_dung','1')")
        ghi_nhat_ky(cn, "chu", "tam-dung", "OK")
        print("đã tạm dừng")
    elif L == "tiep-tuc":
        cn.execute("INSERT OR REPLACE INTO he_thong VALUES('tam_dung','0')")
        ghi_nhat_ky(cn, "chu", "tiep-tuc", "OK")
        print("đã cho chạy tiếp")
    return 0


if __name__ == "__main__":
    sys.exit(main())
