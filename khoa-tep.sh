#!/bin/bash
# Thầy Thành chạy MỘT LẦN sau khi cài: khoá các tệp luật để agent không sửa được.
#   bash khoa-tep.sh        khoá        bash khoa-tep.sh mo     mở khoá (khi thầy muốn sửa luật)
# macOS dùng chflags uchg; Linux dùng chattr +i (cần sudo).
cd "$(dirname "$0")" || exit 1
FILES=(HIEN-PHAP.md chinh-sach.json chay-luot.sh khoa-tep.sh kiem-soat/vi.py kiem-soat/nhap-thu.py
       cong-cu/kiem-bai.py cong-cu/doc-ket-qua.py cong-cu/lam-video.py cong-cu/dung-trang.py
       cong-cu/bao-ve-so.py chinh-sach-github.json github/bao-ve-tep.sh)
if [[ "$(uname)" == Darwin ]]; then
  [[ "$1" == mo ]] && CMD=(chflags nouchg) || CMD=(chflags uchg)
else
  [[ "$1" == mo ]] && CMD=(sudo chattr -i) || CMD=(sudo chattr +i)
fi
for f in "${FILES[@]}"; do "${CMD[@]}" "$f" && echo "${CMD[*]} $f"; done
