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
NORMAL_JSON = "normal6.json"
FINAL_JSON = "final6.json"

LINKS_JSON = [
    "https://raw.githubusercontent.com/tepo18/sab-vip10/main/freg.json",
    "https://raw.githubusercontent.com/tepo18/sab-vip10/main/tepo60.json",
    "https://raw.githubusercontent.com/tepo18/sab-vip10/main/tepo70.json",
    "https://raw.githubusercontent.com/tepo18/sab-vip10/main/tepo80.json",
    "https://raw.githubusercontent.com/tepo18/sab-vip10/main/tepo90.json",
    "https://raw.githubusercontent.com/tepo18/sab-vip10/main/freg10.json",
    "https://raw.githubusercontent.com/tepo18/sab-vip10/main/freg20.json",
    "https://raw.githubusercontent.com/tepo18/sab-vip10/main/tepo40.json",
    "https://raw.githubusercontent.com/tepo18/sab-vip10/main/tepo50.json",
    "https://raw.githubusercontent.com/tepo18/sab-vip10/main/tepo10.json",
    "https://raw.githubusercontent.com/tepo18/sab-vip10/main/tepo20.json",
    "https://raw.githubusercontent.com/tepo18/sab-vip10/main/tepo30.json",
]

# ===================== توابع =====================
def fetch_json(url: str) -> List[Dict]:
    try:
        with urllib.request.urlopen(url, timeout=15) as resp:
            data = json.loads(resp.read().decode())
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

def save_json_files(normal_list: List[Dict], final_list: List[Dict]):
    os.makedirs(os.path.dirname(os.path.abspath(NORMAL_JSON)), exist_ok=True)

    with open(NORMAL_JSON, "w", encoding="utf-8") as f:
        json.dump(normal_list, f, ensure_ascii=False, indent=4)
    with open(FINAL_JSON, "w", encoding="utf-8") as f:
        json.dump(final_list, f, ensure_ascii=False, indent=4)

    print(f"[ℹ️] Normal6 configs: {len(normal_list)} saved to {NORMAL_JSON}")
    print(f"[ℹ️] Final6 configs (after TCP test): {len(final_list)} saved to {FINAL_JSON}")
    print(f"[✅] Update complete. Normal6.json and Final6.json are ready.")

def update_subs():
    all_configs = []
    for url in LINKS_JSON:
        data = fetch_json(url)
        for cfg in data:
            if validate_config(cfg):
                all_configs.append(cfg)

    print(f"[*] Total configs fetched from sources: {len(all_configs)}")
    normal_list = all_configs
    final_list = process_configs(normal_list, precise_test=True)
    save_json_files(normal_list, final_list)

# ========================== اجرا ==========================
if __name__ == "__main__":
    print("[*] Starting JSON subscription update for cl6...")
    start_time = time.time()
    update_subs()
    print(f"[*] Done. Time elapsed: {time.time() - start_time:.2f}s")
