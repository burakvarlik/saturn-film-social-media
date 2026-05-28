#!/usr/bin/env python3
"""GitHub Actions regenerate bitince Make'e 'görsel hazır' bildirimi gönderir."""
import json
import sys
import urllib.request

WEBHOOK_URL = "https://hook.eu2.make.com/8ix47k9buhd6vt5av9t9nen8l28iov0z"


def main():
    metadata_path = sys.argv[1]
    mode = sys.argv[2]

    png = json.load(open(metadata_path))["dosya"]
    image_url = (
        "https://raw.githubusercontent.com/burakvarlik/"
        f"saturn-film-social-media/main/posts/{png}"
    )

    if mode == "user-photo":
        caption = (
            "📸 FOTONUZ KULLANILDI\n\n"
            "Saturn template uygulandı.\n\n"
            "✅ onayla → yayınla\n"
            "📸 Başka foto gönder\n"
            "🔄 gorsel degistir → AI fotoya dön"
        )
    else:
        caption = (
            "🔄 YENİ GÖRSEL HAZIR\n\n"
            "✅ onayla → yayınla\n"
            "🔄 gorsel degistir → tekrar dene\n"
            "📸 Foto gönder → senin fotonu kullan"
        )

    payload = json.dumps({"image_url": image_url, "caption": caption}).encode()
    req = urllib.request.Request(
        WEBHOOK_URL,
        data=payload,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    resp = urllib.request.urlopen(req, timeout=30)
    print("Make yanıtı:", resp.status, resp.read().decode()[:200])


if __name__ == "__main__":
    main()
