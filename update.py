
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

BLOCKED = ("hysteria://", "hysteria2://", "tuic://", "ss://", "ssr://")

ALLOWED = (
    "vless://", "vmess://", "trojan://",
    "socks://", "socks5://", "http://",
    "anytls://", "mieru://", "ssh://", "wireguard://"
)

nodes = set()

def extract(text):
    text = text.strip()

    for _ in range(3):
        if "://" in text:
            break
        try:
            compact = re.sub(r"\s+", "", text)
            decoded = base64.b64decode(
                compact + "=" * (-len(compact) % 4),
                altchars=b"-_"
            ).decode("utf-8", errors="ignore").strip()
            if not decoded or "://" not in decoded:
                break
            text = decoded
        except Exception:
            break

    for line in text.splitlines():
        line = line.strip().lstrip("\ufeff")
        lower = line.lower()

        if not line or lower.startswith("#"):
            continue
        if lower.startswith(BLOCKED):
            continue
        if lower.startswith(ALLOWED):
            nodes.add(line)

for url in SOURCES:
    try:
        response = requests.get(url, timeout=25)
        response.raise_for_status()
        extract(response.text)
        print("OK:", url)
    except Exception as error:
        print("ERROR:", url, error)

with open("Text.txt", "w", encoding="utf-8") as file:
    file.write("#profile-title: Text\n")
    file.write("#profile-update-interval: 30\n")
    file.write("\n".join(sorted(nodes)))
    file.write("\n" if nodes else "")

print("Sources:", len(SOURCES))
print("Total unique configs:", len(nodes))
