#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Update subscriptions script
- Uses LINK_PATH provided by user
- Writes normal list to NORMAL_TXT (normal2.txt)
- Writes final (tested) list to FINAL_TXT (final2.txt)
"""

import threading
import socket
import urllib.parse
import requests
from typing import List

# ===================== تنظیمات (برابر با درخواست شما) =====================
NORMAL_TXT = "normal2.txt"
FINAL_TXT = "final2.txt"

LINK_PATH = [
    "https://raw.githubusercontent.com/tepo80/tepo18/main/trojan.txt",
    "https://raw.githubusercontent.com/tepo80/tepo18/main/trojan10.txt",
    "https://raw.githubusercontent.com/tepo80/tepo18/main/trojan20.txt",
    "https://raw.githubusercontent.com/tepo80/tepo18/main/trojan30.txt",
    "https://raw.githubusercontent.com/tepo80/tepo18/main/trojan40.txt",
    "https://raw.githubusercontent.com/tepo80/tepo18/main/trojan50.txt",
    "https://raw.githubusercontent.com/tepo80/tepo18/main/trojan60.txt",
    "https://raw.githubusercontent.com/tepo80/tepo18/main/trojan70.txt",
    "https://raw.githubusercontent.com/tepo80/tepo18/main/trojan80.txt",
    "https://raw.githubusercontent.com/tepo80/tepo18/main/trojan90.txt",
    "https://raw.githubusercontent.com/tepo80/tepo18/main/vless.txt",
    "https://raw.githubusercontent.com/tepo80/tepo18/main/vless10.txt",
    "https://raw.githubusercontent.com/tepo80/tepo18/main/vless20.txt",
    "https://raw.githubusercontent.com/tepo80/tepo18/main/vless30.txt",
    "https://raw.githubusercontent.com/tepo80/tepo18/main/vless40.txt",
    "https://raw.githubusercontent.com/tepo80/tepo18/main/vless50.txt",
    "https://raw.githubusercontent.com/tepo80/tepo18/main/vless60.txt",
    "https://raw.githubusercontent.com/tepo80/tepo18/main/vless70.txt",
    "https://raw.githubusercontent.com/tepo80/tepo18/main/vless80.txt",
    "https://raw.githubusercontent.com/tepo80/tepo18/main/vless90.txt",
    "https://raw.githubusercontent.com/tepo80/tepo18/main/ss.txt",
    "https://raw.githubusercontent.com/tepo80/tepo18/main/ss10.txt",
    "https://raw.githubusercontent.com/tepo80/tepo18/main/ss20.txt",
    "https://raw.githubusercontent.com/tepo80/tepo18/main/ss30.txt",
    "https://raw.githubusercontent.com/tepo80/tepo18/main/ss40.txt",
    "https://raw.githubusercontent.com/tepo80/tepo18/main/ss50.txt",
    "https://raw.githubusercontent.com/tepo80/tepo18/main/ss60.txt",
    "https://raw.githubusercontent.com/tepo80/tepo18/main/ss70.txt",
    "https://raw.githubusercontent.com/tepo80/tepo18/main/ss80.txt",
    "https://raw.githubusercontent.com/tepo80/tepo18/main/ss90.txt"
]

# header used in normal file (kept from original)
FILE_HEADER_TEXT = "//profile-title: base64:2YfZhduM2LTZhyDZgdi52KfZhCDwn5iO8J+YjvCfmI4gaGFtZWRwNzE="

# ===================== توابع =====================

def fetch_link(url: str) -> List[str]:
    """Download a source file and return non-empty stripped lines."""
    try:
        r = requests.get(url, timeout=15)
        if r.status_code == 200:
            lines = r.text.splitlines()
            return [l.strip() for l in lines if l.strip()]
        else:
            print(f"[⚠️] Failed {url} -> status {r.status_code}")
    except Exception as e:
        print(f"[⚠️] Cannot fetch {url}: {e}")
    return []

def is_valid_config(line: str) -> bool:
    """Basic filtering of obviously-bad configs."""
    line = line.strip()
    if not line or len(line) < 5:
        return False
    lower = line.lower()
    # حذف کانفیگ‌هایی که حاوی شناسنامه‌ی ناخواسته هستند
    if "pin=0" in lower or "pin=red" in lower or "pin=قرمز" in lower:
        return False
    return True

def parse_config_line(line: str):
    """Return the config line if it starts with a known scheme, else None."""
    try:
        line = urllib.parse.unquote(line.strip())
        schemes = ["vmess", "vless", "trojan", "hy2", "hysteria2", "ss", "socks", "wireguard", "ssh"]
        for p in schemes:
            if line.startswith(p + "://"):
                return line
    except Exception:
        pass
    return None

def tcp_test(host: str, port: int, timeout=3) -> bool:
    """Try to open a TCP connection to host:port (returns True if success)."""
    try:
        with socket.create_connection((host, port), timeout=timeout):
            return True
    except Exception:
        return False

def process_configs(lines: List[str], precise_test: bool = False) -> List[str]:
    """
    Filter & (optionally) TCP-test configs in parallel threads.
    Returns deduplicated list preserving first-seen order.
    """
    valid_configs: List[str] = []
    lock = threading.Lock()

    def worker(line: str):
        cfg = parse_config_line(line)
        passed = False
        if cfg:
            try:
                import re
                # تلاش برای یافتن host:port مانند ...@host:port
                m = re.search(r"@([^:\/\s]+):(\d+)", cfg)
                if m:
                    host, port = m.group(1), int(m.group(2))
                else:
                    # اگر هُست پیدا نشد، از پورت پیش‌فرض 443 استفاده می‌کنیم
                    host, port = "", 443

                if precise_test and host:
                    passed = tcp_test(host, port)
                else:
                    passed = True
            except Exception:
                passed = False

        if passed and is_valid_config(line):
            with lock:
                valid_configs.append(line)

    threads = []
    for line in lines:
        t = threading.Thread(target=worker, args=(line,))
        t.daemon = True
        threads.append(t)
        t.start()

    for t in threads:
        t.join()

    # حذف تکراری و حفظ ترتیب
    final_list = list(dict.fromkeys(valid_configs))
    return final_list

def save_outputs(lines: List[str]):
    """
    Save normal list (NORMAL_TXT) with header and then produce FINAL_TXT
    after precise testing.
    """
    try:
        # پاک کردن یا ساخت فایل‌ها
        with open(NORMAL_TXT, "w", encoding="utf-8") as f:
            f.write("")
        with open(FINAL_TXT, "w", encoding="utf-8") as f:
            f.write("")

        # مرحله نرمال (بدون تست TCP دقیق)
        normal_lines = lines
        with open(NORMAL_TXT, "w", encoding="utf-8") as f:
            f.write("\n".join([FILE_HEADER_TEXT] + normal_lines))
        print(f"[ℹ️] Stage 1: {len(normal_lines)} configs saved to {NORMAL_TXT}")

        # مرحله فینال با تست دقیق TCP
        final_lines = process_configs(normal_lines, precise_test=True)
        with open(FINAL_TXT, "w", encoding="utf-8") as f:
            f.write("\n".join(final_lines))
        print(f"[ℹ️] Stage 2: {len(final_lines)} configs saved to {FINAL_TXT}")

        print(f"[✅] Update complete. Total source lines processed: {len(lines)}")
        print(f"  -> Normal configs: {len(normal_lines)}")
        print(f"  -> Final configs: {len(final_lines)}")

    except Exception as e:
        print(f"[❌] Error saving files: {e}")

def update_subs():
    """Fetch all LINK_PATH sources, process and save outputs."""
    all_lines: List[str] = []

    for url in LINK_PATH:
        fetched = fetch_link(url)
        if not fetched:
            print(f"[⚠️] Cannot fetch or empty source: {url}")
        else:
            all_lines.extend(fetched)

    print(f"[*] Total lines fetched from sources: {len(all_lines)}")
    all_lines = process_configs(all_lines, precise_test=False)
    save_outputs(all_lines)

# ===================== اجرای دستی =====================
if __name__ == "__main__":
    print("[*] Starting subscription update...")
    update_subs()
    print("[*] Done.")
