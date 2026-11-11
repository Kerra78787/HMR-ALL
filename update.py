
def is_valid_config(uri):
    from urllib.parse import urlsplit, unquote
    import uuid
    import json

    try:
        scheme = uri.split("://", 1)[0].lower()
        payload = uri.split("://", 1)[1]

        if not payload or "..." in payload or "×" in payload:
            return False

        if scheme == "vmess":
            padded = payload + "=" * (-len(payload) % 4)
            decoded = base64.b64decode(
                padded, altchars=b"-_", validate=True
            )
            data = json.loads(decoded.decode("utf-8"))

            uuid.UUID(str(data.get("id", "")))
            port = int(data.get("port", 0))
            host = str(data.get("add", "")).strip()

            return bool(host) and 1 <= port <= 65535

        parsed = urlsplit(uri)
        if not parsed.hostname or not parsed.port:
            return False

        if not 1 <= parsed.port <= 65535:
            return False

        user = unquote(parsed.username or "")
        if not user:
            return False

        if scheme == "vless":
            uuid.UUID(user)

        elif scheme == "trojan":
            if len(user) < 4:
                return False

        else:
            return False

        return True

    except (ValueError, TypeError, UnicodeError, json.JSONDecodeError):
        return False


def extract_configs(content):
    text = content.decode("utf-8-sig", errors="replace")
    found = []
    seen = set()

    def collect(value):
        for match in URI_PATTERN.findall(value):
            uri = match.rstrip(".,;)]}")

            if uri not in seen and is_valid_config(uri):
                seen.add(uri)
                found.append(uri)

    collect(text)

    candidates = [text]
    candidates.extend(text.splitlines())

    for candidate in candidates:
        compact = "".join(candidate.split())

        if len(compact) < 16:
            continue

        try:
            padded = compact + "=" * (-len(compact) % 4)
            decoded = base64.b64decode(
                padded, altchars=b"-_", validate=True
            )
            collect(decoded.decode("utf-8-sig", errors="ignore"))
        except (ValueError, UnicodeError):
            continue

    return found
eir previous files were preserved."
        )

    print("All 12 sources synchronized successfully!")


if __name__ == "__main__":
    main()
