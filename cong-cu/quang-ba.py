#!/usr/bin/env python3
"""Công cụ cho việc hằng ngày: viết 1 bài quảng bá trang Facebook. Agent KHÔNG được sửa tệp này.

Bài nằm ở ra/quang-ba/YYYY-MM-DD.md (giờ Việt Nam), đúng khuôn:
  # Tiêu đề 5–90 ký tự
  (dòng trống)
  Nội dung 100–900 ký tự, có link Facebook trong thay-cap/kenh.json, tối đa 5 hashtag.
Chỉ được có link Facebook và link YouTube trong kenh.json. Không câu cấm (dùng danh sách của kiem-bai.py).

Lệnh:  can-lam   in XONG_HOM_NAY nếu hôm nay đã có bài đạt; không thì in CAN_LAM kèm tệp cần ghi, link, góc viết hôm nay
       kiem      kiểm bài hôm nay, in OK hoặc các dòng LỖI (thoát mã 1 nếu lỗi)
"""
import glob, importlib.util, json, os, re, sys
from datetime import datetime, timedelta, timezone

GOC = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BAI = os.path.join(GOC, "ra", "quang-ba")
VN = timezone(timedelta(hours=7))
CHO_TRONG = "ĐIỀN"
CAM_THEM = [r"bảo đảm", r"đảm bảo", r"chắc chắn"]
GOC_VIET = ["đặt một câu hỏi gợi tò mò rồi mời xem", "nhờ bạn chia sẻ cho một người bạn", "xem một video mỗi ngày như một thói quen nhỏ",
            "ngôi thứ nhất, hài hước nhẹ: tôi là AI được giao đúng một việc là rủ bạn ghé trang", "nhắc theo dõi trang để không lỡ video mới",
            "dành cho người bận: chỉ cần vài phút mỗi ngày", "cảm ơn những người đã theo dõi", "mời bình luận chủ đề bạn muốn xem",
            "gợi ý xem lúc nghỉ giải lao", "thư giãn cuối ngày"]


def hom_nay():
    return datetime.now(VN)


def doc_kenh():
    with open(os.path.join(GOC, "thay-cap", "kenh.json"), encoding="utf-8") as f:
        k = json.load(f)
    def sach(v):
        v = str(v or "").strip()
        return "" if CHO_TRONG in v else v
    return {x: sach(k.get(x)) for x in ("facebook_link", "youtube_link", "mo_ta", "facebook_nhung", "youtube_kenh_id")}


def cau_cam():
    s = importlib.util.spec_from_file_location("kiem_bai", os.path.join(GOC, "cong-cu", "kiem-bai.py"))
    m = importlib.util.module_from_spec(s)
    s.loader.exec_module(m)
    return list(m.CAU_CAM) + CAM_THEM


def loi_bai(s, kenh):
    dong = s.strip().splitlines()
    if not dong or not dong[0].startswith("# "):
        return ["dòng đầu phải là '# Tiêu đề'"]
    loi, than = [], "\n".join(dong[1:])
    if not 5 <= len(dong[0][2:].strip()) <= 90:
        loi.append("tiêu đề phải 5–90 ký tự")
    chu = re.sub(r"https?://\S+|#\w+", "", than).strip()
    if not 100 <= len(chu) <= 900:
        loi.append("nội dung (không tính link, hashtag) phải 100–900 ký tự, hiện %d" % len(chu))
    fb = kenh["facebook_link"]
    if fb not in than:
        loi.append("thiếu link Facebook: " + fb)
    cho_phep = {x for x in (fb, kenh["youtube_link"]) if x}
    for l in re.findall(r"https?://[^\s)>\]]+", s):
        if l.rstrip(".,") not in cho_phep:
            loi.append("link lạ: " + l[:50])
    if len(re.findall(r"(?<!\w)#\w+", than)) > 5:
        loi.append("quá 5 hashtag")
    for c in cau_cam():
        m = re.search(c, s, re.I)
        if m:
            loi.append("câu cấm: " + m.group(0))
    return loi


def tep_hom_nay():
    return os.path.join(BAI, hom_nay().date().isoformat() + ".md")


def can_lam():
    kenh = doc_kenh()
    if not kenh["facebook_link"]:
        sys.exit("thay-cap/kenh.json chưa có facebook_link")
    tep = tep_hom_nay()
    if os.path.exists(tep) and not loi_bai(open(tep, encoding="utf-8").read(), kenh):
        print("XONG_HOM_NAY")
        return
    gan = []
    for t in sorted(glob.glob(os.path.join(BAI, "????-??-??.md")), reverse=True):
        if t != tep and len(gan) < 7:
            gan.append(open(t, encoding="utf-8").readline()[2:].strip())
    print("CAN_LAM")
    print("TEP=ra/quang-ba/%s" % os.path.basename(tep))
    print("FACEBOOK=" + kenh["facebook_link"])
    print("YOUTUBE=" + (kenh["youtube_link"] or "(chưa có, không nhắc link YouTube)"))
    print("MO_TA=" + (kenh["mo_ta"] or "(trống: chỉ viết lời mời chung, không đoán chủ đề)"))
    print("GOC_HOM_NAY=" + GOC_VIET[hom_nay().date().toordinal() % len(GOC_VIET)])
    print("TIEU_DE_GAN_DAY=" + (" | ".join(gan) or "(chưa có)"))


def kiem():
    tep = tep_hom_nay()
    if not os.path.exists(tep):
        print("LỖI chưa có " + os.path.relpath(tep, GOC))
        return False
    loi = loi_bai(open(tep, encoding="utf-8").read(), doc_kenh())
    print("\n".join("LỖI " + x for x in loi) if loi else "OK")
    return not loi


if __name__ == "__main__":
    lenh = sys.argv[1] if len(sys.argv) > 1 else ""
    if lenh == "can-lam":
        can_lam()
    elif lenh == "kiem":
        sys.exit(0 if kiem() else 1)
    else:
        sys.exit(__doc__)
