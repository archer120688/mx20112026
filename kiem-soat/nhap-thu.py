#!/usr/bin/env python3
"""Nhập tiền thật từ thay-cap/thu.csv vào sổ cái. Chạy đầu mỗi lượt (chay-luot.sh) hoặc chạy tay.

Chỉ thầy Thành điền tệp này, lấy từ sao kê ngân hàng (donate) và báo cáo hoa hồng Shopee Affiliate (shopee).
Cột: ma_giao_dich,ngay,so_tien,loai_thu,nguon,ghi_chu   (loai_thu: donate|shopee · nguon: ngan-hang|shopee|chu)
Trùng ma_giao_dich thì sổ cái tự bỏ qua. Agent không được sửa tệp này.
"""
import csv, os, re, sys
GOC = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import vi


def so(chu):
    s = re.sub(r"[^\d]", "", str(chu))
    return int(s) if s else 0


def nhap(tep, cn):
    moi = tong = 0
    with open(tep, encoding="utf-8-sig", newline="") as f:
        for d in csv.DictReader(f):
            if not (d.get("ma_giao_dich") or "").strip():
                continue
            tong += 1
            nguon = (d.get("nguon") or "chu").strip() or "chu"
            ghi = (d.get("ghi_chu") or "").strip()
            bc = "thầy Thành ghi %s%s" % ((d.get("ngay") or "").strip(), (": " + ghi) if ghi else "")
            kq, _ = vi.ghi_thu(cn, so(d.get("so_tien")), d["ma_giao_dich"].strip(), bc,
                               (d.get("loai_thu") or "").strip(), nguon, ghi or None)
            if kq == "DA_GHI":
                moi += 1
            elif kq == "TU_CHOI":
                print("bỏ qua dòng lỗi:", d.get("ma_giao_dich"))
    return tong, moi


if __name__ == "__main__":
    tep = os.path.join(GOC, "thay-cap", "thu.csv")
    if not os.path.exists(tep):
        print("chưa có thay-cap/thu.csv")
        sys.exit(0)
    tong, moi = nhap(tep, vi.ket_noi())
    print("nhập thu: %d dòng trong tệp, %d khoản mới vào sổ" % (tong, moi))
