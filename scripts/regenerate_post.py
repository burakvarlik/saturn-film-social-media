#!/usr/bin/env python3
"""
Saturn Film — Tek Post Regenerate
==================================
Tek bir postun görselini veya caption'ını yeniden üretir.
GitHub Actions repository_dispatch event'i ile tetiklenir.

Modlar:
  --mode ai-photo               : gpt-image-1'den yeni foto + Saturn template
  --mode user-photo --photo-url : harici URL'den foto + Saturn template
  --mode caption                : OpenAI'dan yeni caption (görsel değişmez)

Kullanım:
  python regenerate_post.py --metadata-path posts/2026-06-05-film-yapim-M.json --mode ai-photo
  python regenerate_post.py --metadata-path ... --mode user-photo --photo-url https://...
  python regenerate_post.py --metadata-path ... --mode caption
"""

import os
import sys
import json
import base64
import argparse
import logging
from pathlib import Path
from io import BytesIO
from datetime import datetime, timezone

import requests
from PIL import Image

# generate_posts.py'den paylaşılan modülleri import et
SCRIPT_DIR = Path(__file__).parent
sys.path.insert(0, str(SCRIPT_DIR))

from generate_posts import (  # noqa: E402
    HIZMETLER,
    POSTS,
    render_layout_A,
    render_layout_M,
    render_layout_B,
    clean_markdown,
    get_openai_client,
)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)-7s | %(message)s",
    datefmt="%H:%M:%S",
)
log = logging.getLogger("saturn-regen")


# ────────────────────────────────────────────────────────────────────
# MODLAR
# ────────────────────────────────────────────────────────────────────
def regenerate_ai_photo(metadata: dict, openai_client) -> Image.Image:
    """AI'dan yeni foto üret + Saturn template uygula."""
    layout = metadata["layout"]
    hizmet_anahtari = metadata["hizmet_anahtari"]
    hizmet = HIZMETLER[hizmet_anahtari]
    service_no = metadata["service_no"]

    # Layout M'de foto yok, sadece template render
    if layout == "M":
        log.info("Layout M — foto yok, template yeniden render")
        post_data = {
            "hizmet_anahtari": hizmet_anahtari,
            "layout": "M",
            "slogan": metadata.get("slogan"),
            "subslogan": metadata.get("subslogan"),
        }
        return render_layout_M(post_data, service_no)

    # Layout A veya B için yeni foto
    size = "1024x1536" if layout == "A" else "1536x1024"
    prompt = (
        f"CRITICAL: wide shot, atmospheric, NO people facing camera, NO close-up faces. "
        f"Cinematic photograph, dark moody atmosphere, professional film production aesthetic. "
        f"Subject: {hizmet['photo_subject']}. "
        f"Color palette: deep blue and black background with subtle gold accent highlights. "
        f"Style: editorial cinematography, magazine-quality, soft rim lighting, atmospheric haze. "
        f"No text, no logos, no watermarks. Photographic realism, not illustration. "
        f"Different composition than previous attempts."
    )

    log.info(f"OpenAI gpt-image-1 → {hizmet['ad']} ({layout}, {size})")
    response = openai_client.images.generate(
        model="gpt-image-1",
        prompt=prompt,
        size=size,
        quality="medium",
        n=1,
    )

    b64 = response.data[0].b64_json
    photo = Image.open(BytesIO(base64.b64decode(b64))).convert("RGB")
    log.info(f"Foto alındı: {photo.size}")

    # Layout render
    post_data = {
        "hizmet_anahtari": hizmet_anahtari,
        "layout": layout,
        "headline": metadata.get("headline"),
        "subtitle": metadata.get("subtitle"),
        "cta_headline": metadata.get("cta_headline"),
        "cta_body": metadata.get("cta_body"),
    }
    if layout == "A":
        return render_layout_A(post_data, photo, service_no)
    else:
        return render_layout_B(post_data, photo, service_no)


def regenerate_user_photo(metadata: dict, photo_url: str) -> Image.Image:
    """Harici URL'den foto indir + Saturn template uygula."""
    layout = metadata["layout"]
    hizmet_anahtari = metadata["hizmet_anahtari"]
    service_no = metadata["service_no"]

    if layout == "M":
        log.warning("Layout M için kullanıcı fotosu kullanılamaz (foto alanı yok). "
                    "Template yeniden render ediliyor.")
        post_data = {
            "hizmet_anahtari": hizmet_anahtari,
            "layout": "M",
            "slogan": metadata.get("slogan"),
            "subslogan": metadata.get("subslogan"),
        }
        return render_layout_M(post_data, service_no)

    log.info(f"Foto indiriliyor: {photo_url[:80]}...")
    r = requests.get(photo_url, timeout=30)
    r.raise_for_status()
    photo = Image.open(BytesIO(r.content)).convert("RGB")
    log.info(f"Kullanıcı fotosu alındı: {photo.size}")

    post_data = {
        "hizmet_anahtari": hizmet_anahtari,
        "layout": layout,
        "headline": metadata.get("headline"),
        "subtitle": metadata.get("subtitle"),
        "cta_headline": metadata.get("cta_headline"),
        "cta_body": metadata.get("cta_body"),
    }
    if layout == "A":
        return render_layout_A(post_data, photo, service_no)
    else:
        return render_layout_B(post_data, photo, service_no)


def regenerate_caption(metadata: dict, openai_client) -> str:
    """AI'dan yeni caption üret. Görsel değişmez."""
    hizmet_anahtari = metadata["hizmet_anahtari"]
    hizmet = HIZMETLER[hizmet_anahtari]

    prompt = f"""Saturn Film için bu postun YENİ ve FARKLI bir caption'ını yaz.

Hizmet: {hizmet['ad']}
Layout: {metadata['layout']}
Başlık: {metadata.get('headline') or metadata.get('slogan') or metadata.get('cta_headline', '')}
Açıklama: {metadata.get('subtitle') or metadata.get('subslogan') or metadata.get('cta_body', '')}

Önceki caption (BUNDAN FARKLI yaz):
{metadata.get('caption', '')}

Kurallar:
- Profesyonel, sinematik, Saturn marka sesinde
- 1 vurucu açılış cümlesi (emoji ile başlayabilir)
- 2-3 cümle gövde
- 1 çağrı/vurgu
- Sondaki iletişim bloğu aynen şu olsun:

📞 İletişim:
🌐 www.saturnfilm.net
📩 info@saturnfilm.net

- Hashtag satırı sonda: {hizmet['hashtag']} #SaturnFilm

Sadece yeni caption'ı dön, başka bir şey yazma."""

    log.info(f"OpenAI GPT-4o → yeni caption: {hizmet['ad']}")
    response = openai_client.chat.completions.create(
        model="gpt-4o",
        messages=[
            {"role": "system",
             "content": "Sen Saturn Film için kıdemli kreatif yazarsın. Profesyonel sinematik dilde yazarsın."},
            {"role": "user", "content": prompt},
        ],
        temperature=0.95,  # daha çeşitli sonuç için
    )

    new_caption = clean_markdown(response.choices[0].message.content)
    log.info(f"Yeni caption üretildi ({len(new_caption)} karakter)")
    return new_caption


# ────────────────────────────────────────────────────────────────────
# MAIN
# ────────────────────────────────────────────────────────────────────
def main():
    parser = argparse.ArgumentParser(description="Saturn Film tek post regenerate")
    parser.add_argument("--metadata-path", required=True,
                        help="posts/*.json metadata dosyası yolu")
    parser.add_argument("--mode", required=True,
                        choices=["ai-photo", "user-photo", "caption"],
                        help="Regenerate modu")
    parser.add_argument("--photo-url",
                        help="user-photo modu için harici foto URL'i")
    args = parser.parse_args()

    # Metadata oku
    metadata_path = Path(args.metadata_path)
    if not metadata_path.exists():
        log.error(f"Metadata dosyası bulunamadı: {metadata_path}")
        sys.exit(1)

    with open(metadata_path, encoding="utf-8") as f:
        metadata = json.load(f)

    log.info(f"═══ Regenerate ═══")
    log.info(f"Dosya: {metadata['dosya']}")
    log.info(f"Hizmet: {metadata['hizmet']} · Layout {metadata['layout']}")
    log.info(f"Mod: {args.mode}")

    # Mod-spesifik aksiyon
    if args.mode == "ai-photo":
        client = get_openai_client()
        new_img = regenerate_ai_photo(metadata, client)
        png_path = POSTS / metadata["dosya"]
        new_img.save(png_path, "PNG", optimize=True)
        log.info(f"✅ PNG güncellendi: {png_path.name}")
        metadata["last_regenerate"] = datetime.now(timezone.utc).isoformat()
        metadata["regenerate_mode"] = "ai-photo"

    elif args.mode == "user-photo":
        if not args.photo_url:
            log.error("--photo-url gerekli (user-photo modunda)")
            sys.exit(1)
        new_img = regenerate_user_photo(metadata, args.photo_url)
        png_path = POSTS / metadata["dosya"]
        new_img.save(png_path, "PNG", optimize=True)
        log.info(f"✅ PNG güncellendi (kullanıcı foto): {png_path.name}")
        metadata["last_regenerate"] = datetime.now(timezone.utc).isoformat()
        metadata["regenerate_mode"] = "user-photo"

    elif args.mode == "caption":
        client = get_openai_client()
        new_caption = regenerate_caption(metadata, client)
        metadata["caption"] = new_caption
        metadata["last_regenerate"] = datetime.now(timezone.utc).isoformat()
        metadata["regenerate_mode"] = "caption"
        log.info(f"✅ Caption güncellendi: {metadata_path.name}")

    # Metadata JSON'u yaz
    with open(metadata_path, "w", encoding="utf-8") as f:
        json.dump(metadata, f, ensure_ascii=False, indent=2)
    log.info(f"✅ Metadata yazıldı: {metadata_path.name}")


if __name__ == "__main__":
    main()
