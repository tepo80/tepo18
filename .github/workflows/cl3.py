#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import threading
import requests
import urllib.parse
import socket
from typing import List

# ===================== تنظیمات =====================
TEXT_PATH = "normal3.txt"
FIN_PATH = "final3.txt"

LINK_PATH = [
    
    "https://github.com/Aristaproject/AristaSub/raw/refs/heads/main/Arista1.txt",
    "https://github.com/Aristaproject/AristaSub/raw/refs/heads/main/Arista2.txt",
    "https://github.com/Aristaproject/AristaSub/raw/refs/heads/main/Arista3.txt",
    "https://github.com/Aristaproject/AristaSub/raw/refs/heads/main/Arista4.txt",
    "https://github.com/Aristaproject/AristaSub/raw/refs/heads/main/Arista5.txt",
    "https://github.com/Aristaproject/AristaSub/raw/refs/heads/main/Arista6.txt",
    "https://github.com/Aristaproject/AristaSub/raw/refs/heads/main/Arista8.txt",
    "https://github.com/Aristaproject/AristaSub/raw/refs/heads/main/Arista9.txt",
    # ----- Extra sources -----
    "https://zaya.link/Arista_HP_Final",
    "https://raw.githubusercontent.com/yebekhe/vpn-fail/main/sub-link.txt",
    "https://raw.githubusercontent.com/Surfboardv2ray/Proxy-sorter/main/ws_tls/proxies/wstls"
            
]

FILE_HEADER_TEXT = "//profile-title: base64:2YfZhduM2LTZhyDZgdi52KfZhCDwn5iO8J+YjvCfmI4gaGFtZWRwNzE="

# ===================== توابع =====================

def fetch_link(url: str) -> List[str]:
    try:
        r = requests.get(url, timeout=15)
        if r.status_code == 200:
            lines = r.text.splitlines()
            return [l.strip() for l in lines if l.strip()]
    except Exception as e:
        print(f"[⚠️] Cannot fetch {url}: {e}")
    return []

def is_valid_config(line: str) -> bool:
    line = line.strip()
    if not line or len(line) < 5:
        return False
    lower = line.lower()
    if "pin=0" in lower or "pin=red" in lower or "pin=قرمز" in lower:
        return False
    return True

def parse_config_line(line: str):
    try:
        line = urllib.parse.unquote(line.strip())
        for p in ["vmess", "vless", "trojan", "hy2", "hysteria2", "ss", "socks", "wireguard"]:
            if line.startswith(p + "://"):
                return line
    except:
        pass
    return None

def tcp_test(host: str, port: int, timeout=3) -> bool:
    try:
        with socket.create_connection((host, port), timeout=timeout):
            return True
    except:
        return False

def process_configs(lines: List[str], precise_test=False) -> List[str]:
    valid_configs = []
    lock = threading.Lock()

    def worker(line):
        cfg = parse_config_line(line)
        passed = False
        if cfg:
            try:
                import re
                m = re.search(r"@([^:]+):(\d+)", cfg)
                host, port = (m.group(1), int(m.group(2))) if m else ("", 443)
                if precise_test and host:
                    passed = tcp_test(host, port)
                else:
                    passed = True
            except:
                passed = False
        if passed and is_valid_config(line):
            with lock:
                valid_configs.append(line)

    threads = []
    for line in lines:
        t = threading.Thread(target=worker, args=(line,))
        threads.append(t)
        t.start()
    for t in threads:
        t.join()

    # حذف تکراری
    final_list = list(dict.fromkeys(valid_configs))
    return final_list

def save_outputs(lines: List[str]):
    try:
        # ذخیره نرمال
        normal_lines = lines
        with open(TEXT_PATH, "w", encoding="utf-8") as f:
            f.write("\n".join([FILE_HEADER_TEXT] + normal_lines))
        saved_normal = len(normal_lines)

        # ذخیره فینال
        final_lines = process_configs(normal_lines, precise_test=True)
        with open(FIN_PATH, "w", encoding="utf-8") as f:
            f.write("\n".join(final_lines))
        saved_final = len(final_lines)

        # پرینت دقیق و هماهنگ با فایل‌ها
        print(f"[ℹ️] Stage 1: {saved_normal} configs saved to {TEXT_PATH}")
        print(f"[ℹ️] Stage 2: {saved_final} configs saved to {FIN_PATH}")
        print(f"[✅] Update complete.")
        print(f"  -> Normal3 configs (saved): {saved_normal}")
        print(f"  -> Final3 configs (after TCP test, saved): {saved_final}")
        print(f"  -> Total sources processed (final): {saved_final}")

    except Exception as e:
        print(f"[❌] Error saving files: {e}")

def update_subs():
    all_lines = []

    for url in LINK_PATH:
        fetched = fetch_link(url)
        if not fetched:
            print(f"[⚠️] Cannot fetch or empty source: {url}")
        else:
            all_lines.extend(fetched)

    print(f"[*] Total lines fetched from sources: {len(all_lines)}")
    all_lines = process_configs(all_lines)
    save_outputs(all_lines)

# ===================== اجرای اصلی =====================
if __name__ == "__main__":
    print("[*] Starting manual subscription update...")
    update_subs()
    print("[*] Done. Run this script manually whenever needed.")
