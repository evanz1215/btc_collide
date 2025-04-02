import os
import time
import json
import random
import threading
import argparse
from bitcoin import *
import requests

# 全局統計
checked = 0
found = 0
lock = threading.Lock()

# 載入 config.json
with open("config.json", "r") as f:
    config = json.load(f)

api_endpoints = config.get("apis", [])


def generate_private_key():
    return random_key()


def check_balance_multi_rpc(address):
    for api in api_endpoints:
        url = api.replace("{address}", address)
        try:
            res = requests.get(url, timeout=10)
            if res.status_code != 200:
                continue
            data = res.json()

            # 根據 API 來源解析
            if "chainstats" in data:
                balance = data["chainstats"]["funded_txo_sum"] - data["chainstats"]["spent_txo_sum"]
                return balance / 1e8
            elif "final_balance" in data:
                return data["final_balance"] / 1e8
            elif "tx_count" in data and "address" in data:
                return float(data.get("balance", 0)) / 1e8
            else:
                continue
        except:
            continue
    return 0.0


def save_key_info(private_key, public_key, address, balance):
    date_str = time.strftime("%Y-%m")
    folder = f"found_keys/{date_str}"
    os.makedirs(folder, exist_ok=True)
    filename = f"{folder}/btc_found.txt"
    with open(filename, "a") as f:
        f.write(f"Private Key: {private_key}\n")
        f.write(f"Public Key: {public_key}\n")
        f.write(f"Address: {address}\n")
        f.write(f"Balance: {balance:.8f} BTC\n")
        f.write("=" * 40 + "\n")


def worker():
    global checked, found
    while True:
        private_key = generate_private_key()
        public_key = privtopub(private_key)
        address = pubtoaddr(public_key)

        balance = check_balance_multi_rpc(address)

        short_key = f"{private_key[:4]}...{private_key[-4:]}"  # 私鑰遮蔽顯示

        with lock:
            checked += 1
            print(
                f"[CHECK] #{checked} | Key: {short_key} | Addr: {address[:6]}... | Balance: {balance:.8f}"
            )

            if balance > 0:
                found += 1
                save_key_info(private_key, public_key, address, balance)
                print(f"[FOUND] {address} -> {balance:.8f} BTC")

            if checked % 100 == 0:
                print(f"[INFO] Total Checked: {checked}, Found: {found}")


def start_threads(thread_count=4):
    print(f"Starting {thread_count} threads...")
    for _ in range(thread_count):
        t = threading.Thread(target=worker, daemon=True)
        t.start()

    while True:
        time.sleep(10)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--thread", type=int, default=4, help="Number of threads to start")
    args = parser.parse_args()

    start_threads(thread_count=args.thread)
