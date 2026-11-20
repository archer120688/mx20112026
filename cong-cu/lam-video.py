#!/usr/bin/env python3
"""Dựng video dọc 1080x1920 từ một tệp kịch bản JSON, chỉ dùng ffmpeg (miễn phí). Không cần CapCut.

Kịch bản (video.json):
{ "canh": [ {"chu": "Chảo chống dính 24cm", "anh": "đường/dẫn/anh.jpg (tuỳ chọn)", "giay": 4},
            {"chu": "Ưu điểm: nhẹ, rửa dễ", "giay": 4} ],
  "mau": ["1f6f5c", "7a3e9d"] }                       (màu nền khi cảnh không có ảnh; tuỳ chọn)
Cảnh cuối (câu công khai hoa hồng + "link ở mô tả") do script tự thêm, không bỏ được.
Giọng đọc (tuỳ chọn): đặt PIPER_MODEL=/đường/dẫn/vi_VN-....onnx và cài piper (mã nguồn mở, chạy offline).
Chạy: python3 cong-cu/lam-video.py video.json video.mp4        (thêm --thu để chỉ in lệnh, không chạy)
"""
import json, os, shutil, subprocess, sys, tempfile, textwrap

W, H = 1080, 1920
CAU_CONG_KHAI = "Có link tiếp thị Shopee: mình có thể nhận hoa hồng khi bạn mua, giá bạn trả không đổi."
CANH_CUOI = ["Link sản phẩm ở phần mô tả", CAU_CONG_KHAI]
FONT_UNG_VIEN = [
    os.environ.get("FONT", ""),
    "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
    "/usr/share/fonts/truetype/noto/NotoSans-Bold.ttf",
    "/System/Library/Fonts/Supplemental/Arial Bold.ttf",
    "/Library/Fonts/Arial Unicode.ttf",
    "C:/Windows/Fonts/arialbd.ttf",
]


def tim_font():
    for f in FONT_UNG_VIEN:
        if f and os.path.exists(f):
            return f
    sys.exit("Không thấy font có tiếng Việt. Đặt biến FONT=/đường/dẫn/font.ttf")


def thoi_luong(tep):
    out = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", tep],
                         capture_output=True, text=True).stdout.strip()
    return float(out) if out else 0.0


def doc_giong(chu, ra):
    """Trả đường dẫn wav nếu có piper + PIPER_MODEL, ngược lại None."""
    mo = os.environ.get("PIPER_MODEL")
    if not mo or not shutil.which("piper"):
        return None
    subprocess.run(["piper", "--model", mo, "--output_file", ra], input=chu, text=True, capture_output=True)
    return ra if os.path.exists(ra) else None


def lenh_canh(i, canh, mau, font, tam, thu):
    chu = canh["chu"]
    giay = float(canh.get("giay", 4))
    wav = None if thu else doc_giong(chu, os.path.join(tam, "c%d.wav" % i))
    if wav:
        giay = max(giay, thoi_luong(wav) + 0.5)
    tep_chu = os.path.join(tam, "c%d.txt" % i)
    open(tep_chu, "w", encoding="utf-8").write("\n".join(textwrap.wrap(chu, 24)))
    vf = ("scale=%d:%d:force_original_aspect_ratio=increase,crop=%d:%d,"
          "drawtext=fontfile='%s':textfile='%s':fontcolor=white:fontsize=64:line_spacing=14:"
          "x=(w-text_w)/2:y=(h-text_h)/2:box=1:boxcolor=black@0.55:boxborderw=28") % (W, H, W, H, font, tep_chu)
    anh = canh.get("anh")
    if anh and os.path.exists(anh):
        vao = ["-loop", "1", "-i", anh]
    else:
        vao = ["-f", "lavfi", "-i", "color=c=0x%s:s=%dx%d:r=30" % (mau[i % len(mau)], W, H)]
    am = ["-i", wav] if wav else ["-f", "lavfi", "-i", "anullsrc=r=44100:cl=stereo"]
    ra = os.path.join(tam, "c%d.mp4" % i)
    cmd = ["ffmpeg", "-y", "-loglevel", "error"] + vao + am + [
        "-map", "0:v", "-map", "1:a", "-vf", vf + ",format=yuv420p", "-r", "30", "-t", "%.2f" % giay,
        "-c:v", "libx264", "-preset", "veryfast", "-c:a", "aac", "-ar", "44100", "-ac", "2"] + (["-af", "apad"] if wav else []) + [ra]
    return cmd, ra


def dung(kich_ban, dau_ra, thu=False):
    canh = list(kich_ban["canh"]) + [{"chu": c, "giay": 3.5} for c in CANH_CUOI]
    mau = kich_ban.get("mau") or ["1f6f5c", "7a3e9d", "b5532b"]
    font = tim_font()
    tam = tempfile.mkdtemp(prefix="lamvideo_")
    clips = []
    for i, c in enumerate(canh):
        cmd, ra = lenh_canh(i, c, mau, font, tam, thu)
        if thu:
            print(" ".join(cmd))
        else:
            r = subprocess.run(cmd, capture_output=True, text=True)
            if r.returncode:
                sys.exit("ffmpeg lỗi ở cảnh %d: %s" % (i, r.stderr[-400:]))
        clips.append(ra)
    if thu:
        return
    ds = os.path.join(tam, "ds.txt")
    open(ds, "w").write("".join("file '%s'\n" % c for c in clips))
    r = subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-f", "concat", "-safe", "0", "-i", ds,
                        "-c", "copy", "-movflags", "+faststart", dau_ra], capture_output=True, text=True)
    if r.returncode:
        sys.exit("ghép lỗi: " + r.stderr[-400:])
    shutil.rmtree(tam, ignore_errors=True)
    print("xong %s (%.1f giây)" % (dau_ra, thoi_luong(dau_ra)))


if __name__ == "__main__":
    a = [x for x in sys.argv[1:] if x != "--thu"]
    if len(a) != 2:
        sys.exit(__doc__)
    dung(json.load(open(a[0], encoding="utf-8")), a[1], thu="--thu" in sys.argv)
