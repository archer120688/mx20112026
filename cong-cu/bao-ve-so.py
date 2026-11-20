#!/usr/bin/env python3
"""Bảo vệ sổ cái khi agent chạy trong GitHub Actions (nơi agent có thể sửa mọi tệp trong thư mục làm việc).

  chup        chép sổ cái sang nơi an toàn (chạy TRƯỚC mỗi vòng agent)
  doi-chieu   so sổ cái hiện tại với bản chụp (chạy SAU mỗi vòng agent):
              but_toan phải y nguyên · quota chỉ được thêm, không sửa/xoá · he_thong y nguyên · không chứa khoá API
              · tệp không hỏng. Sai bất kỳ điều nào thì khôi phục bản chụp (mất ghi chép của vòng đó, chấp nhận được).
"""
import os, shutil, sqlite3, sys

GOC = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(GOC, "kiem-soat"))
import vi

AN_TOAN = os.environ.get("VI_DB_AN_TOAN", "/tmp/aiauto-so-cai.an-toan.db")


def doc(db, bang, sap_xep):
    cn = sqlite3.connect(db)
    try:
        return cn.execute("SELECT * FROM %s ORDER BY %s" % (bang, sap_xep)).fetchall()
    finally:
        cn.close()


def chup(db, an_toan):
    if os.path.exists(db):
        shutil.copyfile(db, an_toan)
        return "ĐÃ CHỤP"
    return "CHƯA CÓ SỔ (lượt đầu)"


def doi_chieu(db, an_toan, khoa=""):
    if not os.path.exists(an_toan):
        return "BỎ QUA (không có bản chụp)"
    ly_do = []
    if not os.path.exists(db):
        ly_do.append("sổ cái bị xoá")
    else:
        try:
            if doc(db, "but_toan", "id") != doc(an_toan, "but_toan", "id"):
                ly_do.append("but_toan bị đổi")
            moi = {r[0]: r for r in doc(db, "quota", "id")}
            if any(moi.get(r[0]) != r for r in doc(an_toan, "quota", "id")):
                ly_do.append("quota bị sửa/xoá")
            if doc(db, "he_thong", "khoa") != doc(an_toan, "he_thong", "khoa"):
                ly_do.append("he_thong bị đổi")
        except sqlite3.DatabaseError as e:
            ly_do.append("sổ hỏng: %s" % e)
        if len(khoa) >= 8 and khoa.encode() in open(db, "rb").read():
            ly_do.append("khoá API lọt vào sổ")
    if ly_do:
        shutil.copyfile(an_toan, db)
        return "KHÔI PHỤC: " + "; ".join(ly_do)
    return "OK"


if __name__ == "__main__":
    if len(sys.argv) != 2 or sys.argv[1] not in ("chup", "doi-chieu"):
        sys.exit(__doc__)
    if sys.argv[1] == "chup":
        print("bao-ve-so chup:", chup(vi.DB, AN_TOAN))
    else:
        print("bao-ve-so doi-chieu:", doi_chieu(vi.DB, AN_TOAN, os.environ.get("GEMINI_API_KEY", "")))
