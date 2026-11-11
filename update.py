
import requests
from pathlib import Path

SOURCES = {
    "1-MustafaBaqer-vless.txt":
        "https://raw.githubusercontent.com/MustafaBaqer/VestraNet-Nodes/main/protocols/vless.txt",

    "2-aviamastersgh-verified_configs.txt":
        "https://raw.githubusercontent.com/aviamastersgh/vpn-free-russia/main/verified_configs.txt",

    "3-R3ZARAHIMI-conf-week.txt":
        "https://raw.githubusercontent.com/R3ZARAHIMI/tg-v2ray-configs-every2h/main/conf-week.txt",

    "4-ALIILAPRO-server.txt":
        "https://raw.githubusercontent.com/ALIILAPRO/v2rayNG-Config/main/server.txt",

    "5-ermaozi-v2ray.txt":
        "https://raw.githubusercontent.com/ermaozi/get_subscribe/main/subscribe/v2ray.txt",

    "6-svinakraft-maker-podpiska.txt":
        "https://raw.githubusercontent.com/svinakraft-maker/FlareFeed/main/public/podpiska.txt",

    "7-alireza786786-vless_servers.txt":
        "https://raw.githubusercontent.com/alireza786786/Free-V2ray-Configs/main/servers/vless_servers.txt",

    "8-openproxylist-rawlist.txt":
        "https://openproxylist.com/v2ray/rawlist/text",

    "9-cbusifabcap-Z.txt":
        "https://raw.githubusercontent.com/cbusifabcap/daily_free_vpn/main/Z.txt",

    "10-0xRadikal-vless.txt":
        "https://raw.githubusercontent.com/0xRadikal/Free-v2ray-Configs/main/protocols/vless.txt",

    "11-histeenn-sub.txt":
        "https://raw.githubusercontent.com/histeenn/VLESS-PO-GRIBI/main/deploy/sub.txt",

    "12-igareck-Reality.txt":
        "https://raw.githubusercontent.com/igareck/vpn-configs-for-russia/main/Vless-Reality-White-Lists-Rus-Mobile.txt",

    "13-mrdevmohamed-All_Configs_Sub.txt":
        "https://raw.githubusercontent.com/mrdevmohamed/v2ray-configs/main/All_Configs_Sub.txt",
}

folder = Path("Sources")
folder.mkdir(parents=True, exist_ok=True)

session = requests.Session()
session.headers.update({"User-Agent": "HMR-ALL-Updater/1.0"})

success = 0

for filename, url in SOURCES.items():
    try:
        response = session.get(url, timeout=40)
        response.raise_for_status()

        (folder / filename).write_bytes(response.content)

        success += 1
        print("OK:", filename)

    except Exception as error:
        print("ERROR:", filename, error)

print("Sources:", len(SOURCES))
print("Updated:", success)
