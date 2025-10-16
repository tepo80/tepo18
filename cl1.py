#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import json
import threading
import time
import socket
import urllib.request
from typing import List, Dict

# ===================== تنظیمات =====================
NORMAL_TXT = "normal2.txt"
FINAL_TXT = "final2.txt"

LINK_PATH = [
    "https://raw.githubusercontent.com/tepo80/tepo18/main/ss.txt",
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

# ===================== توابع =====================
def fetch_txt(url: str) -> List[Dict]:
    try:
        with urllib.request.urlopen(url, timeout=15) as resp:
            data = json.loads(resp.read().decode())  # فرض بر این است که محتوا JSON داخل TXT است
        return data if isinstance(data, list) else []
    except Exception as e:
        print(f"[⚠️] Cannot fetch {url}: {e}")
        return []

def validate_config(cfg: Dict) -> bool:
    return bool(cfg and "remarks" in cfg and "outbounds" in cfg)

def tcp_test(address: str, port: int, timeout=3) -> bool:
    try:
        with socket.create_connection((address, port), timeout=timeout):
            return True
    except:
        return False

def process_configs(configs: List[Dict], precise_test=False, max_threads=20) -> List[Dict]:
    results = []
    lock = threading.Lock()
    threads = []

    def worker(cfg):
        if "outbounds" in cfg:
            try:
                vnext = cfg["outbounds"][0]["settings"]["vnext"][0]
                host = vnext.get("address")
                port = vnext.get("port", 443)
                if precise_test and host:
                    if tcp_test(host, port):
                        with lock:
                            results.append(cfg)
                else:
                    with lock:
                        results.append(cfg)
            except:
                pass

    for cfg in configs:
        t = threading.Thread(target=worker, args=(cfg,))
        threads.append(t)
        t.start()
        if len(threads) >= max_threads:
            for th in threads:
                th.join()
            threads = []

    for t in threads:
        t.join()

    unique = {}
    for cfg in results:
        key = cfg.get("remarks")
        if key not in unique:
            unique[key] = cfg

    return list(unique.values())

def save_txt_files(normal_list: List[Dict], final_list: List[Dict]):
    os.makedirs(os.path.dirname(os.path.abspath(NORMAL_TXT)), exist_ok=True)

    with open(NORMAL_TXT, "w", encoding="utf-8") as f:
        json.dump(normal_list, f, ensure_ascii=False, indent=4)
    with open(FINAL_TXT, "w", encoding="utf-8") as f:
        json.dump(final_list, f, ensure_ascii=False, indent=4)

    print(f"[ℹ️] Normal2 configs: {len(normal_list)} saved to {NORMAL_TXT}")
    print(f"[ℹ️] Final2 configs (after TCP test): {len(final_list)} saved to {FINAL_TXT}")
    print(f"[✅] Update complete. Normal2.txt and Final2.txt are ready.")

def update_subs():
    all_configs = []
    for url in LINK_PATH:
        data = fetch_txt(url)
        for cfg in data:
            if validate_config(cfg):
                all_configs.append(cfg)

    print(f"[*] Total configs fetched from sources: {len(all_configs)}")
    normal_list = all_configs
    final_list = process_configs(normal_list, precise_test=True)
    save_txt_files(normal_list, final_list)

# ========================== اجرا ==========================
if __name__ == "__main__":
    print("[*] Starting TXT subscription update for cl2...")
    start_time = time.time()
    update_subs()
    print(f"[*] Done. Time elapsed: {time.time() - start_time:.2f}s")
