#!/usr/bin/env python3
"""Đọc kết quả một vòng agent (do chay-luot.sh gọi). In dòng đầu `YEU_CAU=<số lượt gọi AI>` rồi phần trả lời cuối.
Gemini CLI với --output-format json có thống kê totalRequests; không đọc được thì dùng số ước tính (đối số 2)."""
import json, sys


def tong(o, khoa="totalRequests"):
    if isinstance(o, dict):
        return sum(v if k == khoa and isinstance(v, (int, float)) else tong(v, khoa) for k, v in o.items())
    if isinstance(o, list):
        return sum(tong(x, khoa) for x in o)
    return 0


def doc(raw, uoc):
    try:
        j = json.loads(raw[raw.index("{"):])
        n = int(tong(j.get("stats", j))) or uoc
        return n, str(j.get("response") or j.get("result") or "")[-3000:]
    except Exception:
        return uoc, raw[-3000:]


if __name__ == "__main__":
    n, chu = doc(open(sys.argv[1], encoding="utf-8", errors="replace").read(), int(sys.argv[2]))
    print("YEU_CAU=%d" % n)
    print(chu)
