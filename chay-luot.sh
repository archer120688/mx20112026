#!/bin/bash
# Một lượt chạy của agent (cron/launchd gọi, hoặc chạy tay: bash chay-luot.sh).
# Dừng khẩn cấp: touch DUNG
export PATH=/opt/homebrew/bin:/usr/local/bin:/usr/bin:/bin:$PATH
cd "$(dirname "$0")" || exit 1
[[ -f ./cau-hinh.env ]] && source ./cau-hinh.env
AGENT=${AGENT:-api}                 # api (mặc định: code điều khiển, cong-cu/luot-ngay.py) | gemini (agent CLI cũ) | lenh (lệnh tuỳ chọn trong LENH_AGENT, đọc lời nhắc từ stdin)
HAN=${HAN:-5400}                    # tối đa 90 phút mỗi lượt
VONG_TOI_DA=${VONG_TOI_DA:-3}
UOC=$(python3 -c 'import json,os;print(json.load(open(os.environ.get("VI_CHINH_SACH","chinh-sach.json")))["uoc_tinh_moi_vong"])')
NK=nhat-ky/luot-$(date +%F).log
mkdir -p nhat-ky du-lieu
log() { echo "$(date '+%F %T') $*" >> "$NK"; }

[[ -e DUNG ]] && { log "có tệp DUNG — không chạy."; exit 0; }
trang_thai() { python3 kiem-soat/vi.py trang-thai | python3 -c 'import json,sys;print(json.load(sys.stdin)["trang_thai"])'; }
TT=$(trang_thai)
case "$TT" in KILL_SWITCH|PAUSED_BY_OWNER|HALTED) log "$TT — không chạy."; exit 0;; esac

KHOA=${KHOA_LUOT:-/tmp/aiauto-thanh-luot.khoa}
if ! mkdir "$KHOA" 2>/dev/null; then
  if [[ -n $(find "$KHOA" -maxdepth 0 -mmin +$(( HAN * 2 / 60 )) 2>/dev/null) ]]; then   # khoá treo quá 2×HAN
    rmdir "$KHOA"; mkdir "$KHOA" || exit 0
  else
    log "lượt trước chưa xong, bỏ lượt này."; exit 0
  fi
fi
trap 'rmdir "$KHOA" 2>/dev/null' EXIT

python3 kiem-soat/nhap-thu.py >> "$NK" 2>&1                       # tiền thầy ghi trong thay-cap/thu.csv → sổ cái
if ! python3 kiem-soat/vi.py kiem-tra >> "$NK" 2>&1; then          # sổ cái bị sửa → tự dừng
  log "SỔ CÁI HỎNG — tạo DUNG."; touch DUNG; exit 1
fi

goi_agent() {
  case "$AGENT" in
    gemini) gemini -y -p "$1" --output-format json ;;
    lenh)   printf '%s' "$1" | bash -c "$LENH_AGENT" ;;
    *)      echo "AGENT không hợp lệ: $AGENT" >&2; return 1 ;;
  esac
}

if [[ "$AGENT" == "api" ]]; then
  # Cách mới: 1–3 lần gọi API, AI trả JSON, chương trình tự ghi nhật ký/ý tưởng/sản phẩm (xem cong-cu/luot-ngay.py)
  [[ -n "${HOOK_TRUOC_AGENT:-}" ]] && bash -c "$HOOK_TRUOC_AGENT" >> "$NK" 2>&1
  timeout "${HAN_API:-1500}" python3 cong-cu/luot-ngay.py >> "$NK" 2>&1 || log "luot-ngay.py thoát lỗi hoặc quá giờ."
  [[ -n "${HOOK_SAU_AGENT:-}" ]] && bash -c "$HOOK_SAU_AGENT" >> "$NK" 2>&1
  python3 kinh-doanh/kiem-bang-viec.py >> "$NK" 2>&1 || true
  python3 cong-cu/dung-trang.py >> "$NK" 2>&1 || true
  log "hết lượt (api)."
  exit 0
fi

BAT_DAU=$(date +%s)
for VONG in $(seq 1 "$VONG_TOI_DA"); do
  LOI_NHAC="$(cat HIEN-PHAP.md)

---
Bắt đầu lượt làm việc (vòng $VONG/$VONG_TOI_DA). Bây giờ là $(date '+%F %H:%M'). Trạng thái: $TT.
Làm đúng phần \"Mỗi lượt\" ở trên. Kết thúc bằng 3–5 dòng tóm tắt tiếng Việt: đã làm gì, bằng chứng, việc lượt sau."
  OUT=$(mktemp)
  [[ -n "${HOOK_TRUOC_AGENT:-}" ]] && bash -c "$HOOK_TRUOC_AGENT" >> "$NK" 2>&1   # dùng cho GitHub Actions
  goi_agent "$LOI_NHAC" > "$OUT" 2>&1 &
  CPID=$!
  CON_LAI=$(( HAN - ($(date +%s) - BAT_DAU) )); (( CON_LAI < 60 )) && CON_LAI=60
  ( sleep "$CON_LAI"; kill -TERM "$CPID" 2>/dev/null; sleep 20; kill -KILL "$CPID" 2>/dev/null; pkill -KILL -P "$CPID" 2>/dev/null ) >/dev/null 2>&1 &
  WPID=$!
  wait "$CPID" 2>/dev/null
  pkill -P "$WPID" 2>/dev/null; kill "$WPID" 2>/dev/null   # gỡ cả đồng hồ hẹn giờ lẫn tiến trình sleep con

  [[ -n "${HOOK_SAU_AGENT:-}" ]] && bash -c "$HOOK_SAU_AGENT" >> "$NK" 2>&1
  KQ=$(python3 cong-cu/doc-ket-qua.py "$OUT" "$UOC")
  N=$(echo "$KQ" | sed -n '1s/^YEU_CAU=//p')
  python3 kiem-soat/vi.py ghi-quota --nguon gemini --so "${N:-$UOC}" >/dev/null
  { echo "--- vòng $VONG: ${N:-$UOC} lượt gọi AI ---"; echo "$KQ" | tail -n +2; } >> "$NK"
  rm -f "$OUT"

  python3 kinh-doanh/kiem-bang-viec.py >> "$NK" 2>&1 || true       # nhắc giữ bảng việc thật
  python3 cong-cu/kiem-bai.py >> "$NK" 2>&1 || true                # kiểm gói bài đăng
  python3 cong-cu/dung-trang.py >> "$NK" 2>&1 || true              # dựng lại trang công khai (chỉ khi thầy đã điền tài khoản)

  [[ -e DUNG ]] && break
  TT=$(trang_thai)
  [[ "$TT" == ACTIVE || "$TT" == THRIFT_MODE ]] || break
  (( $(date +%s) - BAT_DAU >= HAN - 600 )) && break
done
log "hết lượt (trạng thái cuối $TT)."
