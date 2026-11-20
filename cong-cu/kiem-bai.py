#!/usr/bin/env python3
"""Kiểm gói bài đăng trong ra/cho-dang/<ngày>/<mã sản phẩm>/ trước khi thầy Thành đăng.

Một gói cần: video.mp4 · bai-dang.md · nguon.txt
Luật máy kiểm: có câu công khai hoa hồng · link Shopee phải CÓ trong thay-cap/link-affiliate.csv ·
nguon.txt ghi nguồn+giấy phép của mọi ảnh/video/nhạc · không có câu cấm (đã dùng thử, 100%, chữa bệnh...).
In danh sách gói đạt/hỏng; thoát mã 1 nếu có gói hỏng.   Chạy: python3 cong-cu/kiem-bai.py [thư-mục-ngày]
"""
import csv, os, re, sys

GOC = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CAU_CAM = [r"mình đã dùng", r"tôi đã dùng", r"dùng thử thấy", r"đã mua và", r"cam kết", r"100\s*%", r"chữa (khỏi|bệnh)",
           r"giảm cân", r"hiệu quả ngay", r"rẻ nhất", r"số 1\b", r"duy nhất", r"hết hàng sau"]
MIEN_SHOPEE = ("s.shopee.vn", "shope.ee", "shopee.vn")


def link_hop_le(thu_muc_goc=GOC):
    tep = os.path.join(thu_muc_goc, "thay-cap", "link-affiliate.csv")
    if not os.path.exists(tep):
        return set()
    with open(tep, encoding="utf-8-sig", newline="") as f:
        return {(d.get("link_affiliate") or "").strip() for d in csv.DictReader(f) if (d.get("link_affiliate") or "").strip()}


def kiem_goi(thu_muc, hop_le):
    loi = []
    for ten in ("video.mp4", "bai-dang.md", "nguon.txt"):
        if not os.path.exists(os.path.join(thu_muc, ten)):
            loi.append("thiếu " + ten)
    bd = os.path.join(thu_muc, "bai-dang.md")
    if os.path.exists(bd):
        s = open(bd, encoding="utf-8").read()
        if not re.search(r"hoa hồng", s, re.I):
            loi.append("thiếu câu công khai hoa hồng")
        links = re.findall(r"https?://[^\s)>\]]+", s)
        shopee = [l for l in links if any(m in l.split("/")[2] for m in MIEN_SHOPEE)]
        if not shopee:
            loi.append("không có link Shopee")
        for l in shopee:
            if l not in hop_le:
                loi.append("link không có trong thay-cap/link-affiliate.csv: " + l[:40])
        for c in CAU_CAM:
            m = re.search(c, s, re.I)
            if m:
                loi.append("câu cấm: " + m.group(0))
    ng = os.path.join(thu_muc, "nguon.txt")
    if os.path.exists(ng) and len(open(ng, encoding="utf-8").read().strip()) < 10:
        loi.append("nguon.txt trống (ghi nguồn + giấy phép của ảnh/video/nhạc, hoặc 'tự tạo bằng script')")
    return loi


def main(argv):
    goc_ngay = argv[1] if len(argv) > 1 else os.path.join(GOC, "ra", "cho-dang")
    hop_le = link_hop_le()
    hong = tong = 0
    for dp, dn, fn in os.walk(goc_ngay):
        if "bai-dang.md" in fn or "video.mp4" in fn or "video.json" in fn:
            tong += 1
            loi = kiem_goi(dp, hop_le)
            print(("HỎNG " if loi else "ĐẠT  ") + os.path.relpath(dp, goc_ngay) + ("  → " + "; ".join(loi) if loi else ""))
            hong += bool(loi)
    print("%d gói, %d hỏng" % (tong, hong))
    return 1 if hong else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
