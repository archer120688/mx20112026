#!/bin/bash
# Chạy NGAY SAU mỗi vòng agent trong GitHub Actions: hoàn tác mọi thứ agent đụng vào ngoài vùng được phép
# (agent chỉ được ghi trong kinh-doanh/ và ra/), rồi xoá tệp nào lỡ chứa khoá API.
cd "$(dirname "$0")/.." || exit 1
BAO_VE=(HIEN-PHAP.md chinh-sach.json chinh-sach-github.json chay-luot.sh khoa-tep.sh README.md .gitignore cau-hinh.env.mau
        kiem-soat cong-cu functions thay-cap github .github da-khai-tu kinh-doanh/kiem-bang-viec.py)
for p in "${BAO_VE[@]}"; do
  [[ -e "$p" ]] || continue
  git checkout -q -- "$p" 2>/dev/null
  [[ -d "$p" ]] && git clean -fdq -- "$p"
done
if [[ ${#GEMINI_API_KEY} -ge 8 ]]; then
  grep -rlaF --exclude-dir=.git --exclude-dir=nhat-ky -- "$GEMINI_API_KEY" . 2>/dev/null | while read -r f; do
    echo "KHOÁ LỘ trong $f — đã xoá tệp"; rm -f -- "$f"
  done
fi
echo "bao-ve-tep: đã hoàn tác thay đổi ngoài vùng được phép"
