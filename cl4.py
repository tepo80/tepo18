#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Subscriptions JSON aggregator (VIP version)
- Fetches multiple JSON sources from LINK_PATH
- Extracts config strings
- Writes them to normal2.json (no TCP test)
- Performs precise TCP tests and writes reachable ones to final2.json
"""

import json
import threading
import socket
import requests
import urllib.parse
import re
from typing import List, Any

# ===================== تنظیمات =====================
NORMAL_JSON = "normal2.json"
FINAL_JSON = "final2.json"

LINK_PATH = [
    "https://raw.githubusercontent.com/tepo80/tepo18/main/vip.json",
    "https://raw.githubusercontent.com/tepo80/tepo18/main/vip10.json",
    "https://raw.githubusercontent.com/tepo80/tepo18/main/vip20.json",
    "https://raw.githubusercontent.com/tepo80/tepo18/main/vip30.json",
    "https://raw.githubusercontent.com/tepo80/tepo18/main/vip40.json",
    "https://raw.githubusercontent.com/tepo80/tepo18/main/vip50.json",
    "https://raw.githubusercontent.com/tepo80/tepo18/main/vip60.json",
    "https://raw.githubusercontent.com/tepo80/tepo18/main/vip70.json",
    "https://raw.githubusercontent.com/tepo80/tepo18/main/vip80.json",
    "https://raw.githubusercontent.com/tepo80/tepo18/main/vip90.json"
]

# ===================== توابع کمکی =====================

def fetch_url(url: str, timeout: int = 15):
    """دریافت داده از لینک و تلاش برای خواندن JSON یا متن."""
    try:
        r = requests.get(url, timeout=timeout)
        r.raise_for_status()
        try:
            return r.json()
        except Exception:
            return r.text
    except Exception as e:
        print(f"[⚠️] Cannot fetch {url}: {e}")
        return None

def extract_strings_from_json_item(item: Any) -> List[str]:
    """استخراج رشته‌ها از هر نوع ساختار JSON."""
    results = []
    if item is None:
        return results
    if isinstance(item, str):
        s = item.strip()
        if s:
            results.append(s)
        return results
    if isinstance(item, list):
        for v in item:
            results.extend(extract_strings_from_json_item(v))
        return results
    if isinstance(item, dict):
        keys = ["url", "uri", "config", "server", "host", "addr", "address",
                "value", "line", "link", "node", "data"]
        for k in keys:
            if k in item:
                results.extend(extract_strings_from_json_item(item[k]))
        if not results:
            try:
                results.append(json.dumps(item, ensure_ascii=False))
            except:
                pass
        return [r for r in results if r]
    try:
        s = str(item).strip()
        if s:
            results.append(s)
    except:
        pass
    return results

def extract_all_strings(obj: Any) -> List[str]:
    """تبدیل داده ورودی (json/text) به لیست رشته‌های تمیز."""
    results = []
    if obj is None:
        return results
    if isinstance(obj, str):
        for line in obj.splitlines():
            line = line.strip()
            if line:
                results.append(line)
        return results
    results.extend(extract_strings_from_json_item(obj))
    return [r.strip() for r in results if r and isinstance(r, str)]

# ===================== فیلتر و تست =====================

SCHEMES = ["ssh", "vmess", "vless", "trojan", "hy2", "hysteria2", "ss", "socks", "wireguard"]

def is_valid_config(line: str) -> bool:
    if not line or len(line) < 5:
        return False
    l = line.lower()
    if "pin=0" in l or "pin=red" in l or "pin=قرمز" in l:
        return False
    return True

def parse_config_line(line: str) -> str:
    s = line.strip()
    try:
        s = urllib.parse.unquote(s)
    except:
        pass
    for p in SCHEMES:
        if s.lower().startswith(p + "://"):
            return s
    return s

def extract_host_port(s: str):
    """تلاش برای تشخیص host و port از رشته."""
    if not isinstance(s, str):
        return None, None
    m = re.search(r"@([^:\/\s]+):(\d{1,5})", s)
    if m:
        return m.group(1), int(m.group(2))
    m = re.search(r"([a-zA-Z0-9\.\-\_]+):(\d{1,5})", s)
    if m:
        return m.group(1), int(m.group(2))
    return None, None

def tcp_test(host: str, port: int, timeout: int = 3) -> bool:
    try:
        with socket.create_connection((host, port), timeout=timeout):
            return True
    except:
        return False

# ===================== پردازش =====================

def process_entries(entries: List[str], precise_test=False) -> List[str]:
    valid = []
    lock = threading.Lock()

    def worker(line):
        s = parse_config_line(line)
        if not is_valid_config(s):
            return
        passed = True
        if precise_test:
            host, port = extract_host_port(s)
            if host and port:
                passed = tcp_test(host, port)
        if passed:
            with lock:
                valid.append(s)

    threads = []
    for line in entries:
        t = threading.Thread(target=worker, args=(line,))
        t.start()
        threads.append(t)
    for t in threads:
        t.join()

    # حذف تکراری‌ها با حفظ ترتیب
    return list(dict.fromkeys(valid))

def save_json(path: str, data: List[str]):
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

# ===================== اجرای اصلی =====================

def update_subs():
    all_items = []

    for url in LINK_PATH:
        data = fetch_url(url)
        if not data:
            print(f"[⚠️] Empty or unreachable: {url}")
            continue
        lines = extract_all_strings(data)
        if not lines:
            print(f"[⚠️] No strings extracted: {url}")
            continue
        all_items.extend(lines)

    print(f"[*] Total items fetched from all sources: {len(all_items)}")

    # مرحله ۱ - نرمال
    normal_list = process_entries(all_items, precise_test=False)
    save_json(NORMAL_JSON, normal_list)
    print(f"[ℹ️] Stage 1 complete: {len(normal_list)} configs saved to '{NORMAL_JSON}'")

    # مرحله ۲ - فاینال (با تست دقیق)
    final_list = process_entries(normal_list, precise_test=True)
    save_json(FINAL_JSON, final_list)
    print(f"[ℹ️] Stage 2 complete: {len(final_list)} configs saved to '{FINAL_JSON}'")

    print(f"[✅] Update finished.")
    print(f"  -> Normal JSON: '{NORMAL_JSON}' ({len(normal_list)} entries)")
    print(f"  -> Final JSON : '{FINAL_JSON}' ({len(final_list)} entries)")

# ===================== اجرای دستی =====================
if __name__ == "__main__":
    print(f"[*] Starting VIP JSON update → Outputs: '{NORMAL_JSON}', '{FINAL_JSON}'")
    update_subs()
    print(f"[*] Done. Output files: '{NORMAL_JSON}', '{FINAL_JSON}'")
