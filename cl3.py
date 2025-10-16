#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Subscriptions JSON aggregator
- Fetches multiple JSON sources (LINK_PATH)
- Extracts config strings from each source when possible
- Writes all extracted configs (deduplicated, original order) to NORMAL_JSON
- Performs precise TCP test on entries that expose host:port and writes the
  reachable subset to FINAL_JSON
- All prints/messages reference NORMAL_JSON and FINAL_JSON exactly
"""

import json
import threading
import socket
import requests
import urllib.parse
import re
from typing import List, Any, Dict

# ===================== تنظیمات =====================
NORMAL_JSON = "normal.json"
FINAL_JSON = "final.json"

LINK_PATH = [
    "https://raw.githubusercontent.com/tepo80/tepo18/main/ssh100.json",
    "https://raw.githubusercontent.com/tepo80/tepo18/main/ssh.json",
    "https://raw.githubusercontent.com/tepo80/tepo18/main/ssh10.json",
    "https://raw.githubusercontent.com/tepo80/tepo18/main/ssh20.json",
    "https://raw.githubusercontent.com/tepo80/tepo18/main/ssh30.json",
    "https://raw.githubusercontent.com/tepo80/tepo18/main/ssh40.json",
    "https://raw.githubusercontent.com/tepo80/tepo18/main/ssh50.json",
    "https://raw.githubusercontent.com/tepo80/tepo18/main/ssh60.json",
    "https://raw.githubusercontent.com/tepo80/tepo18/main/ssh70.json",
    "https://raw.githubusercontent.com/tepo80/tepo18/main/ssh80.json",
    "https://raw.githubusercontent.com/tepo80/tepo18/main/ssh90.json"
]

# ===================== توابع کمکی =====================

def fetch_url(url: str, timeout: int = 15) -> Any:
    """Download URL and try to return parsed JSON or raw text."""
    try:
        r = requests.get(url, timeout=timeout)
        r.raise_for_status()
        # Try JSON first
        try:
            return r.json()
        except Exception:
            # fallback to text
            return r.text
    except Exception as e:
        print(f"[⚠️] Cannot fetch {url}: {e}")
        return None

def extract_strings_from_json_item(item: Any) -> List[str]:
    """
    Given a JSON item (could be string, dict, list), extract a list of candidate strings.
    Strategy:
    - if string -> return [string.strip()]
    - if list -> recurse and collect strings
    - if dict -> attempt to extract likely fields (url, uri, config, server, host, addr, value, line, s)
      otherwise serialize dict (json dumps) as a fallback string
    """
    results: List[str] = []

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
        # common keys that might contain the config string
        keys_to_try = ["url", "uri", "config", "server", "host", "addr", "address",
                       "value", "line", "link", "node", "node_url", "connection", "data"]
        for k in keys_to_try:
            if k in item and isinstance(item[k], (str, list, dict)):
                results.extend(extract_strings_from_json_item(item[k]))
        # also search all values for any string-like candidates
        for v in item.values():
            if isinstance(v, str):
                results.append(v.strip())
            elif isinstance(v, (list, dict)):
                results.extend(extract_strings_from_json_item(v))
        # If still empty, fallback to serializing the dict (so we don't lose data)
        if not results:
            try:
                results.append(json.dumps(item, ensure_ascii=False))
            except Exception:
                pass
        # filter empties and return
        return [r for r in results if r]

    # other types -> stringify
    try:
        s = str(item).strip()
        if s:
            return [s]
    except Exception:
        pass
    return results

def extract_all_strings(obj: Any) -> List[str]:
    """Top-level extractor that returns a flat list of strings from various JSON/text payloads."""
    results: List[str] = []
    if obj is None:
        return results
    if isinstance(obj, str):
        # If text, split lines and include non-empty lines
        for line in obj.splitlines():
            line = line.strip()
            if line:
                results.append(line)
        return results
    # else delegate to item extractor
    results.extend(extract_strings_from_json_item(obj))
    # final cleaning
    cleaned = []
    for s in results:
        if isinstance(s, str):
            ss = s.strip()
            if ss:
                cleaned.append(ss)
    return cleaned

# ============== تشخیص و فیلتر کانفیگ ==============

SCHEMES = ["ssh", "vmess", "vless", "trojan", "hy2", "hysteria2", "ss", "socks", "wireguard"]

def is_valid_config(line: str) -> bool:
    """Basic filtering of obviously-bad configs (same heuristics as before)."""
    if not line:
        return False
    s = line.strip()
    if len(s) < 5:
        return False
    lower = s.lower()
    if "pin=0" in lower or "pin=red" in lower or "pin=قرمز" in lower:
        return False
    return True

def parse_config_line(line: str) -> str:
    """
    If line is a config string starting with a known scheme, return it.
    Otherwise return the original stripped line (we still may keep it).
    """
    s = line.strip()
    # URL-decode
    try:
        s = urllib.parse.unquote(s)
    except Exception:
        pass
    for p in SCHEMES:
        if s.lower().startswith(p + "://"):
            return s
    # Some JSON sources may contain bare host:port or SSH style strings; still return s
    return s

_hostport_re = re.compile(r"(?P<host>(?:[a-zA-Z0-9\-\._]+|\[[0-9a-fA-F:]+\])):(?P<port>\d{1,5})")

def extract_host_port(s: str):
    """
    Try to extract a host and port from a string.
    Returns (host, port) or (None, None).
    """
    if not s or not isinstance(s, str):
        return None, None
    # look for patterns like @host:port or //host:port or host:port
    # first try @host:port
    m = re.search(r"@([^:\/\s]+):(\d{1,5})", s)
    if m:
        return m.group(1), int(m.group(2))
    # then try explicit host:port anywhere
    m = _hostport_re.search(s)
    if m:
        host = m.group("host")
        port = int(m.group("port"))
        return host, port
    return None, None

def tcp_test(host: str, port: int, timeout: int = 3) -> bool:
    """Attempt a TCP connection to host:port."""
    if not host or not port:
        return False
    try:
        # if IPv6 in brackets, strip for create_connection
        host_to_use = host.strip()
        if host_to_use.startswith("[") and host_to_use.endswith("]"):
            host_to_use = host_to_use[1:-1]
        with socket.create_connection((host_to_use, port), timeout=timeout):
            return True
    except Exception:
        return False

# ===================== پردازش و ذخیره =====================

def process_entries(entries: List[str], precise_test: bool = False) -> List[str]:
    """
    Filter entries, optionally TCP-test those with host:port.
    Returns deduplicated list preserving first-seen order.
    """
    results: List[str] = []
    lock = threading.Lock()

    def worker(e: str):
        if not e or not isinstance(e, str):
            return
        s = parse_config_line(e)
        if not is_valid_config(s):
            return
        passed = True
        if precise_test:
            host, port = extract_host_port(s)
            if host:
                passed = tcp_test(host, port, timeout=3)
            else:
                # if no host found, we conservatively keep the entry (you can change this behavior)
                passed = True
        if passed:
            with lock:
                results.append(s)

    threads = []
    for ent in entries:
        t = threading.Thread(target=worker, args=(ent,))
        t.daemon = True
        threads.append(t)
        t.start()
    for t in threads:
        t.join()

    # deduplicate while preserving order
    deduped = list(dict.fromkeys(results))
    return deduped

def save_json(path: str, data: List[str]):
    """Write list of strings as JSON array to path."""
    try:
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
    except Exception as e:
        raise

def update_subs():
    all_candidates: List[str] = []

    for url in LINK_PATH:
        obj = fetch_url(url)
        if obj is None:
            print(f"[⚠️] Cannot fetch or empty source: {url}")
            continue
        strings = extract_all_strings(obj)
        if not strings:
            print(f"[⚠️] No string items extracted from: {url}")
            continue
        all_candidates.extend(strings)

    print(f"[*] Total candidate items extracted from sources: {len(all_candidates)}")

    # Stage 1: save NORMAL_JSON (no precise TCP test)
    normal_list = process_entries(all_candidates, precise_test=False)
    try:
        save_json(NORMAL_JSON, normal_list)
        print(f"[ℹ️] Stage 1: {len(normal_list)} items saved to '{NORMAL_JSON}'")
    except Exception as e:
        print(f"[❌] Failed to write '{NORMAL_JSON}': {e}")
        return

    # Stage 2: produce FINAL_JSON after precise testing (TCP)
    final_list = process_entries(normal_list, precise_test=True)
    try:
        save_json(FINAL_JSON, final_list)
        print(f"[ℹ️] Stage 2: {len(final_list)} items saved to '{FINAL_JSON}'")
    except Exception as e:
        print(f"[❌] Failed to write '{FINAL_JSON}': {e}")
        return

    print(f"[✅] Update complete.")
    print(f"  -> Normal JSON: '{NORMAL_JSON}' ({len(normal_list)} items)")
    print(f"  -> Final JSON : '{FINAL_JSON}' ({len(final_list)} items)")

# ===================== اجرای دستی =====================
if __name__ == "__main__":
    print(f"[*] Starting update process → outputs: '{NORMAL_JSON}', '{FINAL_JSON}'")
    update_subs()
    print(f"[*] Done. Output files: '{NORMAL_JSON}', '{FINAL_JSON}'")
