#!/bin/sh
# Launcher dự phòng POSIX cho hook agile (scripts/agile_guard.py): không cần Python để chạy chính nó. KHÔNG còn được `hooks/hooks.json` dùng
# (hook mới gọi Python trực tiếp); giữ cho máy/host chỉ có `sh`.
# Đọc sự kiện ở stdin một lần vào biến, rồi gọi thẳng guard bằng `python3`, `python`, `py -3` theo thứ tự (không dò phiên bản bằng tiến trình
# riêng, để mỗi lệnh chỉ tốn một lần khởi động Python; guard tự xử khi Python quá cũ). Guard trả 0 hoặc 2 thì trả nguyên mã (kèm
# stdout/stderr của guard).
# GIỚI HẠN CÓ CHỦ Ý (SPR-32 B3): guard vắng, Python không có, hoặc mọi ứng viên trả mã khác (lỗi cú pháp, import hỏng, traceback) thì launcher
# KHÔNG tự phán đoán công tắc agile (trạng thái nằm trong file JSON ngoài dự án, `sh` thuần không đọc được): nó in cảnh báo rõ ở stderr rằng
# rào KHÔNG hoạt động lần này và thoát 0. Nghĩa là: không có Python dùng được thì không có rào máy; luật chữ vẫn áp. Không dò file dấu cũ.
# Guard luôn là agile_guard.py cạnh chính launcher (không có biến môi trường đổi đường). Chỉ dùng lệnh dựng sẵn của sh khi dò, nên vẫn chạy
# được khi PATH rỗng.

here=${0%/*}
[ "$here" = "$0" ] && here=.
here=$(cd "$here" 2>/dev/null && pwd) || here=.
guard=$here/agile_guard.py

reason="agile: CẢNH BÁO — không chạy được Python để kiểm lệnh, rào máy agile KHÔNG hoạt động lần này (không chặn gì)"

if [ -f "$guard" ]; then
  event=
  while IFS= read -r line || [ -n "$line" ]; do
    event="$event$line
"
  done
  for candidate in "python3" "python" "py -3"; do
    found=$(command -v "${candidate%% *}" 2>/dev/null) || continue
    case $found in
      *[Ww]indows[Aa]pps*) continue ;; # stub của Microsoft Store (không phải Python thật, mỗi lần gọi tốn ~0,2 s)
    esac
    # shellcheck disable=SC2086 -- `py -3` cần tách từ
    printf '%s' "$event" | $candidate "$guard" "$@"
    code=$?
    if [ "$code" = 0 ] || [ "$code" = 2 ]; then
      exit "$code"
    fi
    # 126/127: không chạy được lệnh; mã khác (traceback, lỗi cú pháp, Python quá cũ, stub của Store): thử ứng viên kế
    [ "$code" = 126 ] || [ "$code" = 127 ] || reason="agile: CẢNH BÁO — guard lỗi, rào máy agile KHÔNG hoạt động lần này (không chặn gì)"
  done
fi

echo "$reason" >&2
exit 0
