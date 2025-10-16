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

# ===================== توابع =====================
def fetch_txt(url: str) -> List[Dict]:
    """
    تلاش می‌کند محتوا را از url بخواند.
    اگر محتوا JSON معتبر بود، همان لیست JSON را بازمی‌گرداند (اگر لیست باشد).
    در غیر این صورت، هر خط غیرخالی را تبدیل به یک dict ساده می‌کند:
      {"remarks": "<line>", "outbounds": []}
    """
    try:
        with urllib.request.urlopen(url, timeout=15) as resp:
            raw = resp.read()
            if not raw:
                print(f"[⚠️] Empty response from {url}")
                return []
            text_data = raw.decode(errors="replace").strip()

        if not text_data:
            print(f"[⚠️] Empty content at {url}")
            return []

        # اگر محتوا JSON معتبر باشد، سعی کن لودش کنی
        try:
            parsed = json.loads(text_data)
            if isinstance(parsed, list):
                return parsed
            else:
                # اگر JSON بود ولی ساختارش لیست نبود، تلاش می‌کنیم آن را نادیده بگیریم
                # یا اگر آن یک dict است، آن را داخل لیست قرار می‌دهیم.
                if isinstance(parsed, dict):
                    return [parsed]
                print(f"[⚠️] JSON at {url} is not a list; ignoring.")
                return []
        except json.JSONDecodeError:
            # محتوا JSON نیست → فرض کنیم فایل متنی است؛ هر خط را به یک config ساده تبدیل کن
            lines = [line.strip() for line in text_data.splitlines() if line.strip()]
            result = []
            for line in lines:
                # اگر خط خودش JSON باشد (مثلاً هر خط یک JSON object)، سعی به پارس کن
                if (line.startswith("{") and line.endswith("}")) or (line.startswith("[") and line.endswith("]")):
                    try:
                        item = json.loads(line)
                        if isinstance(item, dict):
                            # اطمینان از داشتن فیلدهای پایه
                            if "remarks" not in item:
                                item.setdefault("remarks", item.get("name", "unknown"))
                            if "outbounds" not in item:
                                item.setdefault("outbounds", [])
                            result.append(item)
                            continue
                    except json.JSONDecodeError:
                        pass
                # در حالت عادی، خط را به عنوان remarks ذخیره کن
                result.append({"remarks": line, "outbounds": []})
            return result
    except Exception as e:
        print(f"[⚠️] Cannot fetch {url}: {e}")
        return []

def validate_config(cfg: Dict) -> bool:
    # اعتبارسنجی ساده: باید حداقل remarks داشته باشد
    if not cfg or not isinstance(cfg, dict):
        return False
    if "remarks" not in cfg:
        return False
    # outbounds ممکن است موجود نباشد؛ قبول می‌کنیم چون برخی ورودی‌ها فقط remark هستند
    return True

def tcp_test(address: str, port: int, timeout=3) -> bool:
    try:
        # اگر address یک domain یا ip باشد، create_connection آن را تست می‌کند
        with socket.create_connection((address, int(port)), timeout=timeout):
            return True
    except Exception:
        return False

def process_configs(configs: List[Dict], precise_test=False, max_threads=20) -> List[Dict]:
    """
    فیلتر و تست TCP روی لیست کانفیگ‌ها.
    اگر precise_test=True باشد تلاش می‌شود از داخل outbounds میزبان را استخراج و تست TCP انجام دهد.
    از دویدن روی outbounds خالی جلوگیری می‌کند.
    """
    results = []
    lock = threading.Lock()
    threads = []

    def worker(cfg):
        # اگر outbounds قابل استفاده باشد، سعی کن host/port را استخراج کنی
        try:
            if isinstance(cfg.get("outbounds"), list) and len(cfg.get("outbounds")) > 0:
                # آدرس و پورت را از ساختار مرسوم استخراج کن (خنثی‌سازی exceptions)
                try:
                    # سازگاری با ساختارهایی مثل vless/vmess: outbounds[0]["settings"]["vnext"][0]
                    ob0 = cfg["outbounds"][0]
                    vnext = ob0.get("settings", {}).get("vnext", [])
                    if vnext and isinstance(vnext, list) and len(vnext) > 0:
                        v0 = vnext[0]
                        host = v0.get("address") or v0.get("host")
                        port = v0.get("port", 443)
                    else:
                        # fallback: اگر outbounds[0] شامل address/port مستقیم باشد
                        host = ob0.get("address") or ob0.get("server") or ob0.get("host")
                        port = ob0.get("port", 443)
                except Exception:
                    host = None
                    port = 443

                if precise_test and host:
                    if tcp_test(host, port):
                        with lock:
                            results.append(cfg)
                else:
                    with lock:
                        results.append(cfg)
            else:
                # اگر outbounds خالی است یا وجود ندارد، فقط اضافه‌اش کن (در حالت non-precise)
                if not precise_test:
                    with lock:
                        results.append(cfg)
                # در حالت precise_test و outbounds خالی → نمی‌توان تست TCP انجام داد → رد می‌کنیم
        except Exception:
            # هر خطا را نادیده می‌گیریم تا یک کانفیگ خراب برنامه را متوقف نکند
            return

    # اجرای threaded
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

    # حذف تکراری‌ها بر اساس remarks
    unique = {}
    for cfg in results:
        key = cfg.get("remarks") or str(cfg)
        if key not in unique:
            unique[key] = cfg

    return list(unique.values())

def save_txt_files(normal_list: List[Dict], final_list: List[Dict]):
    os.makedirs(os.path.dirname(os.path.abspath(NORMAL_TXT)) or ".", exist_ok=True)

    with open(NORMAL_TXT, "w", encoding="utf-8") as f:
        json.dump(normal_list, f, ensure_ascii=False, indent=4)
    with open(FINAL_TXT, "w", encoding="utf-8") as f:
        json.dump(final_list, f, ensure_ascii=False, indent=4)

    print(f"[ℹ️] Normal2 configs: {len(normal_list)} saved to {NORMAL_TXT}")
    print(f"[ℹ️] Final2 configs (after TCP test): {len(final_list)} saved to {FINAL_TXT}")
    print(f"[✅] Update complete. {NORMAL_TXT} and {FINAL_TXT} are ready.")

def update_subs():
    all_configs = []
    for url in LINK_PATH:
        data = fetch_txt(url)
        if not data:
            continue
        for cfg in data:
            if validate_config(cfg):
                all_configs.append(cfg)

    print(f"[*] Total configs fetched from sources: {len(all_configs)}")
    normal_list = all_configs
    # اگر precise_test=True باشد، تلاش می‌شود کانکشن‌های واقعی بررسی شوند
    final_list = process_configs(normal_list, precise_test=True)
    save_txt_files(normal_list, final_list)

# ========================== اجرا ==========================
if __name__ == "__main__":
    print("[*] Starting TXT subscription update for cl2...")
    start_time = time.time()
    update_subs()
    print(f"[*] Done. Time elapsed: {time.time() - start_time:.2f}s")
