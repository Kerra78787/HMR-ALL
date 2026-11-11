import requests
import re
import base64

SOURCES = [
    "https://raw.githubusercontent.com/MustafaBaqer/VestraNet-Nodes/main/protocols/vless.txt",
    "https://raw.githubusercontent.com/R3ZARAHIMI/tg-v2ray-configs-every2h/main/Original-Configs.txt",
    "https://raw.githubusercontent.com/ALIILAPRO/v2rayNG-Config/main/server.txt",
    "https://raw.githubusercontent.com/ALIILAPRO/v2rayNG-Config/main/sub.txt",
    "https://raw.githubusercontent.com/ermaozi/get_subscribe/main/subscribe/v2ray.txt",
    "https://raw.githubusercontent.com/svinakraft-maker/FlareFeed/main/public/podpiska.txt",
    "https://raw.githubusercontent.com/alireza786786/Free-V2ray-Configs/main/servers/vless_servers.txt",
    "https://raw.githubusercontent.com/roosterkid/openproxylist/main/V2RAY.txt",
    "https://raw.githubusercontent.com/cbusifabcap/daily_free_vpn/main/Z.txt",
    "https://raw.githubusercontent.com/0xRadikal/Free-v2ray-Configs/main/protocols/vless.txt",
    "https://raw.githubusercontent.com/histeenn/VLESS-PO-GRIBI/main/deploy/sub.txt",
    "https://raw.githubusercontent.com/morpheusadam/v2ray-config/main/subs/bundles/vless.txt",
]

ALLOWED = ("vless://", "vmess://", "trojan://", "ss://", "ssr://",
           "hysteria://", "hysteria2://", "socks://", "socks5://", "http://")

nodes = set()

def extract(text):
    text = text.strip()
    if not text:
        return

    for _ in range(2):
        try:
            decoded = base64.b64decode(
                text + "=" * (-len(text) % 4)
            ).decode("utf-8", errors="ignore")
            if "://" in decoded:
                text = decoded
            else:
                break
        except Exception:
            break

    for line in text.splitlines():
        line = line.strip()
        if line.startswith(ALLOWED):
            nodes.add(line)

for url in SOURCES:
    try:
        response = requests.get(url, timeout=20)
        response.raise_for_status()
        extract(response.text)
        print("OK:", url)
    except Exception as error:
        print("ERROR:", url, error)

with open("Text.txt", "w", encoding="utf-8") as file:
    file.write("#profile-title: Text\n")
    file.write("#profile-update-interval: 30\n")
    file.write("\n".join(sorted(nodes)))

print("Total unique nodes:", len(nodes))
