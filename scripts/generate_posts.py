#!/usr/bin/env python3
"""
Saturn Film & Entertainment — Aylık Post Üretici
=================================================
GitHub Actions her ayın 25'inde çalıştırır. Şu işleri yapar:

1. OpenAI GPT-4o'dan 6 post için içerik üretir (caption, başlık, alt başlık)
2. gpt-image-1'den sinematik fotoğraflar üretir (4 foto — Layout A ve B)
3. Saturn dark sinematik template'ini 3 layout (A, M, B) ile bastırır
4. posts/ klasörüne PNG + JSON metadata yazar
5. Make.com webhook'una her post için POST atar

Kullanım:
    python generate_posts.py --year 2026 --month 6
    python generate_posts.py --year 2026 --month 6 --dry-run    # webhook atma
"""

import os
import sys
import json
import base64
import calendar
import argparse
import re
import math
import random
import logging
from pathlib import Path
from datetime import date, datetime, timezone
from io import BytesIO
from typing import Optional

import requests
from PIL import Image, ImageDraw, ImageFont, ImageEnhance, ImageOps
from openai import OpenAI

# ────────────────────────────────────────────────────────────────────
# LOGGING
# ────────────────────────────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)-7s | %(message)s",
    datefmt="%H:%M:%S",
)
log = logging.getLogger("saturn")


# ────────────────────────────────────────────────────────────────────
# YOLLAR
# ────────────────────────────────────────────────────────────────────
SCRIPT_DIR = Path(__file__).parent
REPO_ROOT = SCRIPT_DIR.parent
ASSETS = REPO_ROOT / "assets"
POSTS = REPO_ROOT / "posts"
POSTS.mkdir(exist_ok=True)


# ────────────────────────────────────────────────────────────────────
# RENKLER (Saturn brand)
# ────────────────────────────────────────────────────────────────────
BG_DEEP = (10, 14, 26)        # #0A0E1A — derin lacivert/siyah
BG_DARKER = (3, 5, 12)        # foto vinyet için
GOLD = (201, 169, 97)         # #C9A961 — Saturn ring rengi
CYAN = (31, 182, 230)         # #1FB6E6 — Saturn A harfi rengi
WHITE = (255, 255, 255)
MUTED = (140, 150, 170)


# ────────────────────────────────────────────────────────────────────
# FONTLAR (DejaVu — Ubuntu/GitHub Actions runner'da hazır)
# ────────────────────────────────────────────────────────────────────
F_BOLD_COND = "/usr/share/fonts/truetype/dejavu/DejaVuSansCondensed-Bold.ttf"
F_REG = "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"
F_OBLIQUE = "/usr/share/fonts/truetype/dejavu/DejaVuSansCondensed-Oblique.ttf"


def font(path: str, size: int) -> ImageFont.FreeTypeFont:
    return ImageFont.truetype(path, size)


def fit_font_to_width(draw, text: str, font_path: str, max_size: int, min_size: int, max_width: int) -> ImageFont.FreeTypeFont:
    """Text'i max_width'e sığdıracak en büyük font size'ı döndür."""
    for size in range(max_size, min_size - 1, -2):
        f = ImageFont.truetype(font_path, size)
        bbox = draw.textbbox((0, 0), text, font=f)
        if (bbox[2] - bbox[0]) <= max_width:
            return f
    return ImageFont.truetype(font_path, min_size)


def wrap_text_to_width(draw, text: str, font: ImageFont.FreeTypeFont, max_width: int) -> list:
    """Text'i kelime kelime sarmalayıp her satırı max_width'e sığdır."""
    if not text:
        return []
    lines = []
    for paragraph in text.split("\n"):
        words = paragraph.split()
        cur = ""
        for w in words:
            test = (cur + " " + w).strip() if cur else w
            bbox = draw.textbbox((0, 0), test, font=font)
            if (bbox[2] - bbox[0]) <= max_width:
                cur = test
            else:
                if cur:
                    lines.append(cur)
                cur = w
        if cur:
            lines.append(cur)
    return lines




# ────────────────────────────────────────────────────────────────────
# HİZMETLER (4 ana hizmet)
# ────────────────────────────────────────────────────────────────────
HIZMETLER = {
    "film_yapim": {
        "ad": "Film Yapım",
        "tag": "FİLM YAPIM",
        "hashtag": "#FilmYapımı #Sinema #FilmProdüksiyon #TürkSineması",
        "ozellik": (
            "Senaryo geliştirme, prodüksiyon, çekim, kurgu ve post-prodüksiyon dahil "
            "uçtan uca film yapım hizmeti. Uzun metraj, kısa film ve belgesel projeleri."
        ),
        "photo_subject": (
            "professional film set with cinematic lighting, vintage camera equipment, "
            "director's chair, soft rim light, atmospheric haze, blue-grey color palette"
        ),
    },
    "ai_reklam": {
        "ad": "Yapay Zeka Reklam Filmleri",
        "tag": "AI REKLAM FİLMLERİ",
        "hashtag": "#YapayZeka #AIReklam #AIVideo #ReklamFilmi #GenerativeAI",
        "ozellik": (
            "Yapay zeka destekli yeni nesil reklam filmleri. Hızlı, ekonomik ve "
            "yaratıcı çözümler. Kavram geliştirmeden final teslime kadar AI iş akışı."
        ),
        "photo_subject": (
            "futuristic creative studio, glowing monitors with abstract digital "
            "graphics, neon blue accent light, holographic interfaces, atmospheric "
            "dark workspace, cinematic mood"
        ),
    },
    "dizi_yapim": {
        "ad": "Dizi Yapımı",
        "tag": "DİZİ YAPIMI",
        "hashtag": "#DiziYapımı #TürkDizisi #DiziProdüksiyon #TVProdüksiyon",
        "ozellik": (
            "Konseptten yayına televizyon ve dijital platform dizi yapımı. "
            "Senaryo, kadrolama, set yönetimi, çekim ve post-prodüksiyon."
        ),
        "photo_subject": (
            "TV drama set with warm tungsten lighting, vintage furniture, "
            "atmospheric haze, period drama mood, soft golden hour light through "
            "windows, cinematic depth"
        ),
    },
    "muzik_klibi": {
        "ad": "Müzik Klibi",
        "tag": "MÜZİK KLİBİ",
        "hashtag": "#MüzikKlibi #MusicVideo #TürkMüziği #VideoKlip",
        "ozellik": (
            "Sanatçı vizyonunu görsel hikâyeye dönüştüren müzik klibi yapımı. "
            "Konsept tasarımı, sahne kurgusu, sinematografi ve renk grade."
        ),
        "photo_subject": (
            "music video shoot atmosphere, dramatic colored lighting (deep blue "
            "and gold), smoke and haze, modern stylized set, low key cinematic "
            "mood, performance art aesthetic"
        ),
    },
}


# Ay → 2 hizmet rotasyonu (Haziran=tek=Film+AI, Temmuz=çift=Dizi+Müzik)
def aylik_rotasyon(month: int) -> list[str]:
    # Haziran: AI Reklam + Müzik Klibi (kullanıcı tercihi)
    # Diğer çift aylar (Ağustos, Ekim, Aralık): Film + AI Reklam
    # Tek aylar (Temmuz, Eylül, Kasım): Dizi + Müzik Klibi
    if month == 6:
        return ["ai_reklam", "muzik_klibi"]
    elif month % 2 == 0:
        return ["film_yapim", "ai_reklam"]
    else:
        return ["dizi_yapim", "muzik_klibi"]


# Layout havuzu — 5 foto'lu + 1 foto'suz (M).
# Her ay bu havuzdan, aya göre kayan, çeşitli bir 3'lü kombinasyon seçilir.
# Böylece feed her ay farklı görünür ama marka kimliği (renk/logo/font) sabit kalır.
LAYOUT_HAVUZU = ["A", "B", "F", "T", "C"]   # foto gerektiren layout'lar (M ayrı)


def aylik_layout_secimi(month: int) -> list[str]:
    """Her hizmet için 3 layout döner. Aya göre kayar, böylece aylar arası çeşitlilik olur.

    Kural: her 3'lüde 1 adet foto'suz M layout + 2 adet foto'lu layout bulunur.
    Foto'lu layout'lar havuzdan (A,B,F,T,C) aya göre kayan pencereyle seçilir.
    Dönen değer 6 elemanlı: [H1-x, H1-y, H1-z, H2-x, H2-y, H2-z].
    """
    # Aya göre havuzda kayan başlangıç noktası
    offset = (month - 1) % len(LAYOUT_HAVUZU)
    # Bu ayın 2 foto'lu layout'u (kayan pencere)
    foto1 = LAYOUT_HAVUZU[offset]
    foto2 = LAYOUT_HAVUZU[(offset + 2) % len(LAYOUT_HAVUZU)]
    # Her hizmet: [foto1, M, foto2]  (M ortada, foto'lular kenarda)
    tek_hizmet = [foto1, "M", foto2]
    return tek_hizmet * 2   # iki hizmet için tekrarla


AY_ADI_TR = {
    1: "Ocak", 2: "Şubat", 3: "Mart", 4: "Nisan", 5: "Mayıs", 6: "Haziran",
    7: "Temmuz", 8: "Ağustos", 9: "Eylül", 10: "Ekim", 11: "Kasım", 12: "Aralık",
}
GUN_ADI_TR = {0: "Pazartesi", 1: "Salı", 2: "Çarşamba", 3: "Perşembe",
              4: "Cuma", 5: "Cumartesi", 6: "Pazar"}


# ────────────────────────────────────────────────────────────────────
# BRAND BRIEF (OpenAI prompt'larında kullanılır)
# ────────────────────────────────────────────────────────────────────
BRAND_BRIEF = """
Saturn Film & Entertainment — uçtan uca film, dizi, reklam ve müzik klibi
prodüksiyon şirketi. Resmi site: www.saturnfilm.net

MARKA SESİ:
- Profesyonel ve kurumsal, ama soğuk değil
- Vizyon sahibi: "yörünge", "hikâye", "sinematik" gibi kelimeler doğal
- Saturn'un logo metaforu (gezegen halkası) marka diline yansır
- Türkçe akıcı, yabancı kelime gerekirse İngilizce
- Aşırı emoji yok, ama 1-2 stratejik emoji caption'ı canlandırır

VURGUYU SEVDIĞIMIZ KAVRAMLAR:
- Hikâyenin gücü
- Sinematik bakış
- Vizyon ve teknoloji birlikteliği
- Türk sineması ve televizyonuna katkı
- Yeni nesil prodüksiyon yaklaşımı

KAÇINILACAK:
- Klişe ifadeler ("sektörün lideri", "kalitemiz", "müşteri memnuniyeti")
- Aşırı satışçı dil
- Genel geçer pazarlama jargon
- Belirsiz/içi boş sözler ("en iyi", "her zaman")
"""


# ────────────────────────────────────────────────────────────────────
# YARDIMCILAR — Türkçe karakter, markdown temizliği
# ────────────────────────────────────────────────────────────────────
def slugify_tr(text: str) -> str:
    """Türkçe karakter destekli ASCII slug."""
    tr_map = str.maketrans({
        "ç": "c", "Ç": "C", "ğ": "g", "Ğ": "G", "ı": "i", "İ": "I",
        "ö": "o", "Ö": "O", "ş": "s", "Ş": "S", "ü": "u", "Ü": "U",
        "â": "a", "Â": "A", "î": "i", "Î": "I", "û": "u", "Û": "U",
    })
    text = text.translate(tr_map).lower()
    text = re.sub(r"[^a-z0-9]+", "-", text)
    return text.strip("-")


def clean_markdown(text: str) -> str:
    """GPT'nin bazen eklediği markdown markerlarını temizle."""
    if not text:
        return ""
    text = re.sub(r"\*\*(.*?)\*\*", r"\1", text)
    text = re.sub(r"__(.*?)__", r"\1", text)
    text = re.sub(r"\*(.*?)\*", r"\1", text)
    text = re.sub(r"_(.*?)_", r"\1", text)
    return text.strip()


# ────────────────────────────────────────────────────────────────────
# TARİH HESAPLAMA — Çar/Cuma takvimi
# ────────────────────────────────────────────────────────────────────
def compute_post_dates(year: int, month: int, n: int = 6, start_date: date | None = None) -> list[date]:
    """Yayın tarihlerini hesaplar.
    
    Eğer start_date verilirse: o tarih ilk post + sonrası Çar/Cuma takvimi.
    Verilmezse: ayın ilk n adet Çar/Cuma'sı.
    
    Wed=2, Fri=4 (calendar.WEDNESDAY=2, calendar.FRIDAY=4).
    """
    dates: list[date] = []
    
    if start_date is not None:
        # İlk post = start_date (haftanın hangi günü olursa olsun)
        dates.append(start_date)
        # Sonraki tarihler: start_date'den ileri Çar/Cuma'lar
        from datetime import timedelta
        d = start_date + timedelta(days=1)
        while len(dates) < n:
            if d.weekday() in (calendar.WEDNESDAY, calendar.FRIDAY):
                dates.append(d)
            d += timedelta(days=1)
            # Güvenlik valfı: 60 gün sonrasını arama
            if (d - start_date).days > 60:
                break
        if len(dates) < n:
            log.warning(f"start_date={start_date}: sadece {len(dates)}/{n} tarih bulundu")
        return dates
    
    # Klasik mantık: ayın ilk n Çar/Cuma'sı
    days_in_month = calendar.monthrange(year, month)[1]
    for day in range(1, days_in_month + 1):
        d = date(year, month, day)
        if d.weekday() in (calendar.WEDNESDAY, calendar.FRIDAY):
            dates.append(d)
        if len(dates) >= n:
            break
    if len(dates) < n:
        log.warning(f"{year}-{month:02d}: sadece {len(dates)} Çar/Cuma var, {n} istendi")
    return dates


# ────────────────────────────────────────────────────────────────────
# OPENAI — İÇERIK ÜRETİMİ
# ────────────────────────────────────────────────────────────────────
def get_openai_client() -> OpenAI:
    api_key = os.environ.get("OPENAI_API_KEY")
    if not api_key:
        raise RuntimeError("OPENAI_API_KEY environment variable yok")
    return OpenAI(api_key=api_key)


def generate_content(
    client: OpenAI,
    year: int,
    month: int,
    hizmet_anahtarlari: list[str],
    layouts: list[str],
) -> list[dict]:
    """6 post için içerik üretir (2 hizmet × 3 layout = 6).

    Layout'lar `layouts` parametresinden gelir (aylik_layout_secimi ile belirlenir).
    Returns: list of 6 dict; layout sırası `layouts` ile birebir eşleşir.
    """
    ay_adi = AY_ADI_TR[month]
    h1 = HIZMETLER[hizmet_anahtarlari[0]]
    h2 = HIZMETLER[hizmet_anahtarlari[1]]

    # Post planı: hangi hizmet + hangi layout sırası (layouts param'dan)
    # layouts 6 elemanlı: ilk 3'ü h1, son 3'ü h2 için
    plan_satirlari = []
    for i, lay in enumerate(layouts):
        hiz = hizmet_anahtarlari[0] if i < 3 else hizmet_anahtarlari[1]
        hiz_ad = HIZMETLER[hiz]["ad"]
        plan_satirlari.append(f"  Post {i+1}: hizmet_anahtari={hiz} ({hiz_ad}), layout={lay}")
    post_plan_str = "\n".join(plan_satirlari)
    
    prompt = f"""Saturn Film & Entertainment için {ay_adi} {year} ayı sosyal medya içeriklerini üreteceksin.

{BRAND_BRIEF}

BU AYIN HİZMETLERİ:
1) {h1['ad']}: {h1['ozellik']}
2) {h2['ad']}: {h2['ozellik']}

ÇIKTILAR: 6 post (2 hizmet × 3 farklı layout). Layout'lar aşağıda her post için TANIMLI;
verilen layout'a UYGUN alanları doldur (diğerlerini null bırak).

LAYOUT A / F / T / C (foto + başlık; hepsi aynı içerik alanlarını kullanır):
- headline: 2-3 satır CAPS başlık (toplam 4-8 kelime). Vurucu, sinematik, sloganvari.
- subtitle: 1 satır italic alt başlık (6-12 kelime). Açıklayıcı.

LAYOUT M (sadece typography, foto YOK, manifesto/slogan):
- slogan: 3 satır CAPS dev slogan (toplam 5-8 kelime). Saturn yörünge metaforu olabilir.
- subslogan: 1 satır italic (5-10 kelime). Hizmetin kapsamını belirten.

LAYOUT B (foto + CTA/iletişim paneli):
- cta_headline: 2 satır CAPS başlık (4-7 kelime). Eyleme çağıran.
- cta_body: 2-3 satır body (15-25 kelime). Saturn'un ne sunduğunu özetleyen.

CAPTION (Instagram açıklaması) - HER POST İÇİN AYRI:
- Etkili 1-cümle açılış (emoji ile başlayabilir: 🎬 ✨ 🎥 vb.)
- 2-3 cümle gövde (hizmetin değerini anlatan, Saturn'a özgü)
- 1 cümle çağrı/vurgu
- Sabit iletişim bloğu:
  📞 İletişim:
  🌐 www.saturnfilm.net
  📩 info@saturnfilm.net
- Hashtag satırı (sondaki bu hashtag'leri olduğu gibi koy: {h1['hashtag']} ya da {h2['hashtag']} — hangi hizmetse onunki + #SaturnFilm #SaturnFilmEntertainment)

KESIN KURALLAR:
- Caption max 1200 karakter (Instagram limiti)
- headline/slogan/cta_headline tamamen BÜYÜK HARF
- Türkçe karakter (ç, ğ, ı, ö, ş, ü, â) sorunsuz kullan
- markdown YOK (asterisk, underscore vs)
- Aynı söz ve metaforu farklı postlarda tekrar etme; her post ayrı bir açı bulsun

ÜRETİLECEK 6 POST (bu sıra ve layout'lara TAM uy):
{post_plan_str}

JSON formatında dön. Her post için TÜM alanları ver (kullanılmayanı null bırak):
{{
  "posts": [
    {{
      "hizmet_anahtari": "...",
      "layout": "...",
      "headline": null, "subtitle": null,
      "slogan": null, "subslogan": null,
      "cta_headline": null, "cta_body": null,
      "caption": "..."
    }}
    // ... toplam 6 post, yukarıdaki plana göre
  ]
}}
"""
    
    log.info(f"OpenAI: {ay_adi} {year} için içerik üretiliyor ({h1['ad']} + {h2['ad']})...")
    
    response = client.chat.completions.create(
        model="gpt-4o",
        messages=[
            {"role": "system", "content": "Sen Saturn Film için içerik üreten kıdemli bir kreatif strateji uzmanısın. Profesyonel, sinematik ve özgün dilde yazarsın."},
            {"role": "user", "content": prompt},
        ],
        response_format={"type": "json_object"},
        temperature=0.85,
    )
    
    data = json.loads(response.choices[0].message.content)
    posts = data.get("posts", [])
    
    if len(posts) != 6:
        log.error(f"GPT 6 post yerine {len(posts)} post döndü, durduruluyor")
        log.debug(f"Response: {posts}")
        raise RuntimeError(f"Beklenen 6 post, gelen {len(posts)}")
    
    # Markdown temizliği
    for p in posts:
        for k in ("headline", "subtitle", "slogan", "subslogan", "cta_headline", "cta_body", "caption"):
            if p.get(k):
                p[k] = clean_markdown(p[k])
    
    log.info(f"OpenAI içerik üretimi tamam. Token kullanımı: {response.usage.total_tokens}")
    return posts


def generate_photo(client: OpenAI, hizmet_anahtari: str, layout: str) -> Image.Image:
    """Sinematik foto üret. Layout A = portrait (1024x1536), Layout B = landscape (1536x1024)."""
    hizmet = HIZMETLER[hizmet_anahtari]
    
    # Layout'a göre en uygun foto oranı
    if layout == "A":
        size = "1024x1536"          # dikey (sağ şerit)
    elif layout in ("B", "T"):
        size = "1536x1024"          # yatay (üst şerit)
    elif layout in ("F", "C"):
        size = "1024x1024"          # kare (tam ekran / çerçeve)
    else:
        raise ValueError(f"Layout {layout} için foto üretilmez (M foto-suz)")
    
    prompt = (
        f"CRITICAL: wide shot, atmospheric, NO people facing camera, NO close-up faces. "
        f"Cinematic photograph, dark moody atmosphere, professional film production aesthetic. "
        f"Subject: {hizmet['photo_subject']}. "
        f"Color palette: deep blue and black background with subtle gold accent highlights. "
        f"Style: editorial cinematography, magazine-quality, soft rim lighting, atmospheric haze. "
        f"No text, no logos, no watermarks. Photographic realism, not illustration."
    )
    
    log.info(f"gpt-image-1: {hizmet['ad']} ({layout}) — {size}")
    
    response = client.images.generate(
        model="gpt-image-1",
        prompt=prompt,
        size=size,
        quality="medium",
        n=1,
    )
    
    b64 = response.data[0].b64_json
    img_bytes = base64.b64decode(b64)
    return Image.open(BytesIO(img_bytes)).convert("RGB")


# ────────────────────────────────────────────────────────────────────
# FOTO İŞLEME — cover-fit + sinematik treatment
# ────────────────────────────────────────────────────────────────────
def fit_photo_to_area(photo: Image.Image, target_w: int, target_h: int) -> Image.Image:
    """Cover-fit: foto target alanı tam kaplar, fazlası ortadan kırpılır."""
    src_w, src_h = photo.size
    src_ratio = src_w / src_h
    target_ratio = target_w / target_h
    
    if src_ratio > target_ratio:
        new_h = target_h
        new_w = int(target_h * src_ratio)
    else:
        new_w = target_w
        new_h = int(target_w / src_ratio)
    
    photo = photo.resize((new_w, new_h), Image.LANCZOS)
    left = (new_w - target_w) // 2
    top = (new_h - target_h) // 2
    return photo.crop((left, top, left + target_w, top + target_h))


def apply_cinematic_treatment(photo: Image.Image, seed: int = 42) -> Image.Image:
    """Foto'ya Saturn sinematik atmosfer ekle: oto-parlaklik + vignette + blue tone + grain.

    Karanlik fotolar (orijinali koyu olanlar) otomatik telafi edilir, boylece
    vignette uygulandiktan sonra da gorunur kalirlar.
    """
    w, h = photo.size

    # --- Adaptif isik telafisi (gamma tabanli, highlight korumali) ---
    # Sabit parlaklik carpani highlight'lari patlatiyordu (cene/el parlamasi).
    # Bunun yerine gamma ile SADECE golgeleri acariz, parlak tonlari korur ve
    # 0.85 ustunu yumusak sikistirip parlamayi (clipping) onleriz.
    photo = ImageOps.autocontrast(photo, cutoff=0.5)
    gray = photo.convert("L")
    mean_lum = sum(gray.getdata()) / (w * h)
    if mean_lum < 120:
        # mean=20 -> gamma~0.57 (cok acar), mean=120 -> gamma~1.0 (dokunmaz)
        gamma = max(0.5, min(1.0, mean_lum / 120.0 * 0.5 + 0.5))
        lut = []
        for i in range(256):
            v = (i / 255.0) ** gamma          # gamma<1 golgeleri acar
            if v > 0.85:                       # highlight sikistirma (parlama onler)
                v = 0.85 + (v - 0.85) * 0.5
            lut.append(int(max(0, min(255, v * 255))))
        photo = photo.point(lut * 3)           # RGB uc kanala uygula

    # --- Vignette (yumusatildi: 200 -> 110) ---
    vignette = Image.new("L", (w, h), 0)
    vd = ImageDraw.Draw(vignette)
    max_r = int(math.hypot(w, h) / 2)
    for r in range(max_r, 0, -8):
        t = r / max_r
        alpha = int(110 * t)
        vd.ellipse((w//2 - r, h//2 - r, w//2 + r, h//2 + r), fill=255 - alpha)
    black = Image.new("RGB", (w, h), (0, 0, 0))
    # DUZELTME: composite(image1, image2, mask) -> mask=255 ise image1 secilir.
    # Maske merkezi beyaz (foto gorunur), kenarlar koyu (vignette).
    photo = Image.composite(photo, black, vignette)

    # --- Hafif mavi tone shift (0.08 -> 0.05, daha az soguk) ---
    overlay = Image.new("RGB", (w, h), (15, 25, 45))
    photo = Image.blend(photo, overlay, 0.05)

    # --- Grain ---
    grain = Image.new("L", (w, h), 0)
    gp = grain.load()
    rng = random.Random(seed)
    for _ in range(w * h // 12):
        x, y = rng.randint(0, w-1), rng.randint(0, h-1)
        gp[x, y] = rng.randint(0, 60)
    grain_rgb = Image.merge("RGB", (grain, grain, grain))
    photo = Image.blend(photo, grain_rgb, 0.05)

    return photo


def overlay_gold_sweep(photo: Image.Image, y_ratio: float = 0.6) -> Image.Image:
    """Foto'nun belirli yüksekliğinde diyagonal altın çizgi."""
    img = photo.copy()
    overlay = Image.new("RGBA", img.size, (0, 0, 0, 0))
    od = ImageDraw.Draw(overlay)
    w, h = img.size
    sweep_y = int(h * y_ratio)
    od.polygon([
        (-50, sweep_y + 80),
        (w + 50, sweep_y - 40),
        (w + 50, sweep_y - 37),
        (-50, sweep_y + 83),
    ], fill=(*GOLD, 120))
    return Image.alpha_composite(img.convert("RGBA"), overlay).convert("RGB")


# ────────────────────────────────────────────────────────────────────
# DRAW YARDIMCILARI
# ────────────────────────────────────────────────────────────────────
def paste_logo(canvas: Image.Image, target_w: int, x: int, y: int) -> None:
    """Saturn beyaz logosunu canvas'a yerleştir."""
    logo = Image.open(ASSETS / "Saturn_Logo_beyaz.png").convert("RGBA")
    ratio = target_w / logo.width
    logo = logo.resize((target_w, int(logo.height * ratio)), Image.LANCZOS)
    canvas.paste(logo, (x, y), logo)


def L_mark(draw: ImageDraw.ImageDraw, x: int, y: int, dx: int, dy: int,
           cs: int = 28, cw: int = 3, color=WHITE) -> None:
    """Sinematik köşe markeri (L şeklinde)."""
    x1, x2 = sorted([x, x + dx * cs]); y1, y2 = sorted([y, y + dy * cw])
    draw.rectangle((x1, y1, x2, y2), fill=color)
    x1, x2 = sorted([x, x + dx * cw]); y1, y2 = sorted([y, y + dy * cs])
    draw.rectangle((x1, y1, x2, y2), fill=color)


def four_corners(draw: ImageDraw.ImageDraw, w: int, h: int,
                 inset: int = 35, cs: int = 28, cw: int = 3, color=WHITE) -> None:
    L_mark(draw, inset, inset, 1, 1, cs, cw, color)
    L_mark(draw, w - inset, inset, -1, 1, cs, cw, color)
    L_mark(draw, inset, h - inset, 1, -1, cs, cw, color)
    L_mark(draw, w - inset, h - inset, -1, -1, cs, cw, color)


def draw_cyan_dot(draw: ImageDraw.ImageDraw, cx: int, cy: int, r: int = 6) -> None:
    """Saturn ring metaforu — cyan parlak nokta."""
    for rr in range(r, 0, -1):
        draw.ellipse((cx - rr, cy - rr, cx + rr, cy + rr), fill=CYAN)


def draw_gold_sweep_line(draw: ImageDraw.ImageDraw, x1: int, y1: int,
                         x2: int, y2: int, width: int = 2) -> None:
    draw.line([(x1, y1), (x2, y2)], fill=GOLD, width=width)


# ────────────────────────────────────────────────────────────────────
# LAYOUT RENDER FONKSİYONLARI
# ────────────────────────────────────────────────────────────────────
POST_SIZE = 1080


def render_layout_A(post_data: dict, photo: Image.Image, service_no: int) -> Image.Image:
    """Layout A — sol text alanı + sağ portrait foto."""
    hizmet_anahtari = post_data["hizmet_anahtari"]
    hizmet = HIZMETLER[hizmet_anahtari]
    
    img = Image.new("RGB", (POST_SIZE, POST_SIZE), BG_DEEP)
    draw = ImageDraw.Draw(img)
    
    PHOTO_X = int(POST_SIZE * 0.42)
    PHOTO_W = POST_SIZE - PHOTO_X
    
    # Foto hazırla: cover-fit + cinematic + gold sweep
    photo_fitted = fit_photo_to_area(photo, PHOTO_W, POST_SIZE)
    photo_fitted = apply_cinematic_treatment(photo_fitted, seed=hash(hizmet_anahtari) & 0xFFFF)
    photo_fitted = overlay_gold_sweep(photo_fitted, y_ratio=0.55)
    img.paste(photo_fitted, (PHOTO_X, 0))
    
    # Sınır altın
    draw.line([(PHOTO_X - 1, 0), (PHOTO_X - 1, POST_SIZE)], fill=GOLD, width=2)
    
    # Logo
    paste_logo(img, target_w=280, x=60, y=60)
    
    # Hizmet sayacı sağ üst
    f_num = font(F_BOLD_COND, 18)
    num_text = f"0{service_no} / 04"
    bbox = draw.textbbox((0, 0), num_text, font=f_num)
    draw.text((POST_SIZE - 60 - (bbox[2] - bbox[0]), 70), num_text, fill=GOLD, font=f_num)
    
    # Hizmet tag
    f_tag = font(F_BOLD_COND, 20)
    draw.text((60, 380), "— HİZMET", fill=CYAN, font=f_tag)
    f_tag2 = font(F_BOLD_COND, 26)
    draw.text((60, 412), hizmet["tag"], fill=WHITE, font=f_tag2)
    
    # Headline — ADAPTIVE font + wrap (text alanı: PHOTO_X - 60 margin - 20 buffer)
    MAX_W_A = PHOTO_X - 80
    raw_h_lines = (post_data.get("headline") or "").upper().split("\n")
    longest_h = max(raw_h_lines, key=len) if raw_h_lines else ""
    f_h = fit_font_to_width(draw, longest_h, F_BOLD_COND, max_size=56, min_size=34, max_width=MAX_W_A)
    line_h_h = int(f_h.size * 1.18)
    
    y = 490
    for line in raw_h_lines:
        bbox = draw.textbbox((0, 0), line, font=f_h)
        if (bbox[2] - bbox[0]) > MAX_W_A:
            for w_line in wrap_text_to_width(draw, line, f_h, MAX_W_A):
                draw.text((60, y), w_line, fill=WHITE, font=f_h)
                y += line_h_h
        else:
            draw.text((60, y), line, fill=WHITE, font=f_h)
            y += line_h_h
    
    # Gold sweep
    draw_gold_sweep_line(draw, 60, y + 25, 380, y + 25, width=3)
    
    # Subtitle (italic) — word wrap
    f_sub = font(F_OBLIQUE, 22)
    sub_y = y + 55
    for line in (post_data.get("subtitle") or "").split("\n"):
        for w_line in wrap_text_to_width(draw, line, f_sub, MAX_W_A):
            draw.text((60, sub_y), w_line, fill=MUTED, font=f_sub)
            sub_y += 30
    
    # Alt URL
    f_url = font(F_BOLD_COND, 18)
    draw.text((60, POST_SIZE - 60), "www.saturnfilm.net", fill=GOLD, font=f_url)
    
    return img


def render_layout_M(post_data: dict, service_no: int) -> Image.Image:
    """Layout M — sadece typography (foto yok). Manifesto/slogan."""
    img = Image.new("RGB", (POST_SIZE, POST_SIZE), BG_DEEP)
    draw = ImageDraw.Draw(img)
    
    # Subtle radial glow
    cx, cy = POST_SIZE // 2, POST_SIZE // 2
    for r in range(POST_SIZE, 0, -10):
        t = r / POST_SIZE
        glow = int(8 * (1 - t))
        color = (
            min(255, BG_DEEP[0] + glow),
            min(255, BG_DEEP[1] + glow + 2),
            min(255, BG_DEEP[2] + glow + 8),
        )
        draw.ellipse((cx - r, cy - r, cx + r, cy + r), fill=color)
    
    # Asimetrik gold sweep'ler
    draw_gold_sweep_line(draw, 0, 280, POST_SIZE - 200, 250, width=2)
    draw_gold_sweep_line(draw, 200, POST_SIZE - 250, POST_SIZE, POST_SIZE - 280, width=2)
    
    # Logo
    paste_logo(img, target_w=280, x=60, y=60)
    
    # Sayaç
    f_num = font(F_BOLD_COND, 18)
    num_text = f"0{service_no} / 04"
    bbox = draw.textbbox((0, 0), num_text, font=f_num)
    draw.text((POST_SIZE - 60 - (bbox[2] - bbox[0]), 70), num_text, fill=GOLD, font=f_num)
    
    # Slogan (büyük, ortalanmış) — ADAPTIVE FONT SIZE
    MAX_W_M = POST_SIZE - 120  # 60px margin her iki yandan
    raw_lines = (post_data.get("slogan") or "").upper().split("\n")
    
    # Her satır için en uzun olana göre tek bir font size belirle
    longest = max(raw_lines, key=len) if raw_lines else ""
    f_sl = fit_font_to_width(draw, longest, F_BOLD_COND, max_size=72, min_size=42, max_width=MAX_W_M)
    
    # Line height fontun ~%117'si
    line_h = int(f_sl.size * 1.17)
    
    # Uzun tek satır varsa otomatik wrap dene (font 42'de hala taşıyorsa)
    final_lines = []
    for line in raw_lines:
        bbox = draw.textbbox((0, 0), line, font=f_sl)
        if (bbox[2] - bbox[0]) > MAX_W_M:
            # Wrap yap
            wrapped = wrap_text_to_width(draw, line, f_sl, MAX_W_M)
            final_lines.extend(wrapped)
        else:
            final_lines.append(line)
    
    total_h = len(final_lines) * line_h
    sy = (POST_SIZE - total_h) // 2 - 40
    for line in final_lines:
        bbox = draw.textbbox((0, 0), line, font=f_sl)
        tw = bbox[2] - bbox[0]
        draw.text(((POST_SIZE - tw) // 2, sy), line, fill=WHITE, font=f_sl)
        sy += line_h
    # sy artık son satırın ALTINDA — dot ve subslogan buradan devam eder
    
    # Cyan dot (Saturn ring metaforu)
    dot_y = sy + 18
    draw_cyan_dot(draw, cx, dot_y, r=6)
    
    # Subslogan (italic)
    f_ss = font(F_OBLIQUE, 24)
    subslogan = post_data.get("subslogan", "")
    bbox = draw.textbbox((0, 0), subslogan, font=f_ss)
    tw = bbox[2] - bbox[0]
    draw.text(((POST_SIZE - tw) // 2, dot_y + 30), subslogan, fill=MUTED, font=f_ss)
    
    # Alt URL ortalanmış
    f_url = font(F_BOLD_COND, 18)
    url = "www.saturnfilm.net"
    bbox = draw.textbbox((0, 0), url, font=f_url)
    tw = bbox[2] - bbox[0]
    draw.text(((POST_SIZE - tw) // 2, POST_SIZE - 60), url, fill=GOLD, font=f_url)
    
    return img


def render_layout_B(post_data: dict, photo: Image.Image, service_no: int) -> Image.Image:
    """Layout B — üst landscape foto + alt CTA paneli."""
    hizmet_anahtari = post_data["hizmet_anahtari"]
    hizmet = HIZMETLER[hizmet_anahtari]
    
    img = Image.new("RGB", (POST_SIZE, POST_SIZE), BG_DEEP)
    draw = ImageDraw.Draw(img)
    
    PHOTO_H = int(POST_SIZE * 0.55)
    
    photo_fitted = fit_photo_to_area(photo, POST_SIZE, PHOTO_H)
    photo_fitted = apply_cinematic_treatment(photo_fitted, seed=(hash(hizmet_anahtari) + 1) & 0xFFFF)
    photo_fitted = overlay_gold_sweep(photo_fitted, y_ratio=0.6)
    img.paste(photo_fitted, (0, 0))
    
    # Foto-text sınırı
    draw.line([(0, PHOTO_H), (POST_SIZE, PHOTO_H)], fill=GOLD, width=2)
    
    # Logo
    paste_logo(img, target_w=280, x=60, y=60)
    
    # Sayaç
    f_num = font(F_BOLD_COND, 18)
    num_text = f"0{service_no} / 04"
    bbox = draw.textbbox((0, 0), num_text, font=f_num)
    draw.text((POST_SIZE - 60 - (bbox[2] - bbox[0]), 70), num_text, fill=GOLD, font=f_num)
    
    # CTA alanı (alt yarı)
    cta_y = PHOTO_H + 50
    
    f_tag = font(F_BOLD_COND, 20)
    draw.text((60, cta_y), "— PROJENİZ İÇİN", fill=CYAN, font=f_tag)
    
    # CTA başlık — ADAPTIVE: uzun başlık için font düşür + wrap
    MAX_W_B = POST_SIZE - 120  # 60px margin her iki yandan
    raw_headline_lines = (post_data.get("cta_headline") or "").upper().split("\n")
    longest_h = max(raw_headline_lines, key=len) if raw_headline_lines else ""
    f_h = fit_font_to_width(draw, longest_h, F_BOLD_COND, max_size=44, min_size=30, max_width=MAX_W_B)
    line_h_h = int(f_h.size * 1.18)
    
    y = cta_y + 36
    for line in raw_headline_lines:
        bbox = draw.textbbox((0, 0), line, font=f_h)
        if (bbox[2] - bbox[0]) > MAX_W_B:
            for w_line in wrap_text_to_width(draw, line, f_h, MAX_W_B):
                draw.text((60, y), w_line, fill=WHITE, font=f_h)
                y += line_h_h
        else:
            draw.text((60, y), line, fill=WHITE, font=f_h)
            y += line_h_h
    
    # CTA body — WORD WRAP
    f_b = font(F_REG, 20)
    y += 12
    for line in (post_data.get("cta_body") or "").split("\n"):
        for w_line in wrap_text_to_width(draw, line, f_b, MAX_W_B):
            draw.text((60, y), w_line, fill=MUTED, font=f_b)
            y += 28
    
    # Alt URL + CTA ok
    f_url = font(F_BOLD_COND, 18)
    draw.text((60, POST_SIZE - 60), "www.saturnfilm.net", fill=GOLD, font=f_url)
    
    f_arr = font(F_BOLD_COND, 22)
    arrow = "→ İLETİŞİM"
    bbox = draw.textbbox((0, 0), arrow, font=f_arr)
    draw.text((POST_SIZE - 60 - (bbox[2] - bbox[0]), POST_SIZE - 62), arrow, fill=WHITE, font=f_arr)
    
    return img


def render_layout_F(post_data: dict, photo: Image.Image, service_no: int) -> Image.Image:
    """Layout F — full-bleed: foto tum kareyi kaplar, alt gradient uzerine baslik."""
    hizmet_anahtari = post_data["hizmet_anahtari"]
    hizmet = HIZMETLER[hizmet_anahtari]

    img = Image.new("RGB", (POST_SIZE, POST_SIZE), BG_DEEP)
    photo_fitted = fit_photo_to_area(photo, POST_SIZE, POST_SIZE)
    photo_fitted = apply_cinematic_treatment(photo_fitted, seed=(hash(hizmet_anahtari) + 2) & 0xFFFF)
    img.paste(photo_fitted, (0, 0))

    # Alttan koyu gradient (metin okunurlugu icin)
    grad = Image.new("L", (1, POST_SIZE), 0)
    for y in range(POST_SIZE):
        t = y / POST_SIZE
        a = 0 if t < 0.45 else int(235 * ((t - 0.45) / 0.55) ** 1.3)
        grad.putpixel((0, y), a)
    grad = grad.resize((POST_SIZE, POST_SIZE))
    dark = Image.new("RGB", (POST_SIZE, POST_SIZE), BG_DEEP)
    img = Image.composite(dark, img, grad)

    draw = ImageDraw.Draw(img)
    paste_logo(img, target_w=260, x=60, y=60)

    f_num = font(F_BOLD_COND, 18)
    num_text = f"0{service_no} / 04"
    bbox = draw.textbbox((0, 0), num_text, font=f_num)
    draw.text((POST_SIZE - 60 - (bbox[2] - bbox[0]), 70), num_text, fill=GOLD, font=f_num)

    # Alt blok: tag + baslik
    f_tag = font(F_BOLD_COND, 22)
    draw.text((60, POST_SIZE - 300), "— " + hizmet["tag"], fill=CYAN, font=f_tag)
    f_h = font(F_BOLD_COND, 62)
    y = POST_SIZE - 262
    for line in (post_data.get("headline") or "").split("\n"):
        draw.text((60, y), line.upper(), fill=WHITE, font=f_h)
        y += 66
    draw.line([(62, y + 10), (300, y + 10)], fill=GOLD, width=3)
    f_sub = font(F_OBLIQUE, 26)
    draw.text((60, y + 26), post_data.get("subtitle") or "", fill=MUTED, font=f_sub)
    f_url = font(F_BOLD_COND, 18)
    draw.text((60, POST_SIZE - 50), "www.saturnfilm.net", fill=GOLD, font=f_url)
    four_corners(draw, POST_SIZE, POST_SIZE, inset=32, cs=24, cw=3, color=WHITE)
    return img


def render_layout_T(post_data: dict, photo: Image.Image, service_no: int) -> Image.Image:
    """Layout T — top-strip: ust yatay foto seridi + alt lacivert zeminde ortali metin."""
    hizmet_anahtari = post_data["hizmet_anahtari"]
    hizmet = HIZMETLER[hizmet_anahtari]

    img = Image.new("RGB", (POST_SIZE, POST_SIZE), BG_DEEP)
    draw = ImageDraw.Draw(img)

    PHOTO_H = int(POST_SIZE * 0.52)
    photo_fitted = fit_photo_to_area(photo, POST_SIZE, PHOTO_H)
    photo_fitted = apply_cinematic_treatment(photo_fitted, seed=(hash(hizmet_anahtari) + 3) & 0xFFFF)
    photo_fitted = overlay_gold_sweep(photo_fitted, y_ratio=0.8)
    img.paste(photo_fitted, (0, 0))
    draw.line([(0, PHOTO_H), (POST_SIZE, PHOTO_H)], fill=GOLD, width=3)

    paste_logo(img, target_w=240, x=55, y=55)
    f_num = font(F_BOLD_COND, 18)
    num_text = f"0{service_no} / 04"
    bbox = draw.textbbox((0, 0), num_text, font=f_num)
    draw.text((POST_SIZE - 58 - (bbox[2] - bbox[0]), 62), num_text, fill=WHITE, font=f_num)

    cy = PHOTO_H + 55
    f_tag = font(F_BOLD_COND, 22)
    tag = "— " + hizmet["tag"]
    bbox = draw.textbbox((0, 0), tag, font=f_tag)
    draw.text(((POST_SIZE - (bbox[2] - bbox[0])) // 2, cy), tag, fill=CYAN, font=f_tag)
    f_h = font(F_BOLD_COND, 58)
    y = cy + 44
    for line in (post_data.get("headline") or "").split("\n"):
        bbox = draw.textbbox((0, 0), line.upper(), font=f_h)
        draw.text(((POST_SIZE - (bbox[2] - bbox[0])) // 2, y), line.upper(), fill=WHITE, font=f_h)
        y += 62
    draw_cyan_dot(draw, POST_SIZE // 2, y + 22, r=5)
    draw.line([(POST_SIZE // 2 - 120, y + 22), (POST_SIZE // 2 - 20, y + 22)], fill=GOLD, width=2)
    draw.line([(POST_SIZE // 2 + 20, y + 22), (POST_SIZE // 2 + 120, y + 22)], fill=GOLD, width=2)
    f_sub = font(F_OBLIQUE, 25)
    sub = post_data.get("subtitle") or ""
    bbox = draw.textbbox((0, 0), sub, font=f_sub)
    draw.text(((POST_SIZE - (bbox[2] - bbox[0])) // 2, y + 42), sub, fill=MUTED, font=f_sub)
    f_url = font(F_BOLD_COND, 18)
    bbox = draw.textbbox((0, 0), "www.saturnfilm.net", font=f_url)
    draw.text(((POST_SIZE - (bbox[2] - bbox[0])) // 2, POST_SIZE - 58), "www.saturnfilm.net", fill=GOLD, font=f_url)
    return img


def render_layout_C(post_data: dict, photo: Image.Image, service_no: int) -> Image.Image:
    """Layout C — center-frame: ortada altin cerceveli foto + ust/alt ortali metin."""
    hizmet_anahtari = post_data["hizmet_anahtari"]
    hizmet = HIZMETLER[hizmet_anahtari]

    img = Image.new("RGB", (POST_SIZE, POST_SIZE), BG_DEEP)
    draw = ImageDraw.Draw(img)

    logo_w = 240
    paste_logo(img, target_w=logo_w, x=(POST_SIZE - logo_w) // 2, y=55)

    f_tag = font(F_BOLD_COND, 22)
    tag = "— " + hizmet["tag"]
    bbox = draw.textbbox((0, 0), tag, font=f_tag)
    draw.text(((POST_SIZE - (bbox[2] - bbox[0])) // 2, 150), tag, fill=CYAN, font=f_tag)

    FRAME = 560
    fx = (POST_SIZE - FRAME) // 2
    fy = 200
    photo_fitted = fit_photo_to_area(photo, FRAME, FRAME)
    photo_fitted = apply_cinematic_treatment(photo_fitted, seed=(hash(hizmet_anahtari) + 4) & 0xFFFF)
    img.paste(photo_fitted, (fx, fy))
    draw.rectangle((fx - 3, fy - 3, fx + FRAME + 2, fy + FRAME + 2), outline=GOLD, width=3)
    four_corners(draw, POST_SIZE, POST_SIZE, inset=34, cs=26, cw=3, color=WHITE)

    f_h = font(F_BOLD_COND, 52)
    y = fy + FRAME + 40
    for line in (post_data.get("headline") or "").split("\n"):
        bbox = draw.textbbox((0, 0), line.upper(), font=f_h)
        draw.text(((POST_SIZE - (bbox[2] - bbox[0])) // 2, y), line.upper(), fill=WHITE, font=f_h)
        y += 56
    f_sub = font(F_OBLIQUE, 24)
    sub = post_data.get("subtitle") or ""
    bbox = draw.textbbox((0, 0), sub, font=f_sub)
    draw.text(((POST_SIZE - (bbox[2] - bbox[0])) // 2, y + 6), sub, fill=MUTED, font=f_sub)
    f_url = font(F_BOLD_COND, 18)
    bbox = draw.textbbox((0, 0), "www.saturnfilm.net", font=f_url)
    draw.text(((POST_SIZE - (bbox[2] - bbox[0])) // 2, POST_SIZE - 52), "www.saturnfilm.net", fill=GOLD, font=f_url)
    return img


# ────────────────────────────────────────────────────────────────────
# WEBHOOK (Make.com)
# ────────────────────────────────────────────────────────────────────
def send_to_make(payload: dict, webhook_url: str) -> bool:
    """Make.com data store webhook'una post bilgisini gönder."""
    try:
        r = requests.post(webhook_url, json=payload, timeout=20)
        if r.status_code == 200:
            log.info(f"  → Webhook OK ({payload['tarih']})")
            return True
        else:
            log.error(f"  → Webhook hata {r.status_code}: {r.text[:200]}")
            return False
    except requests.RequestException as e:
        log.error(f"  → Webhook bağlantı hatası: {e}")
        return False


# ────────────────────────────────────────────────────────────────────
# MAIN — Orchestrator
# ────────────────────────────────────────────────────────────────────
def main():
    parser = argparse.ArgumentParser(description="Saturn Film aylık post üretici")
    parser.add_argument("--year", type=int, required=True, help="Yıl (örn: 2026)")
    parser.add_argument("--month", type=int, required=True, help="Ay (1-12)")
    parser.add_argument("--month-label", type=str, default=None,
                        help="Ay etiketi (örn: 'Haziran 2026'). Boşsa otomatik üretilir.")
    parser.add_argument("--dry-run", action="store_true",
                        help="Webhook atma, sadece render et")
    parser.add_argument("--skip-photo", action="store_true",
                        help="Foto üretmeyi atla (placeholder kullan) — sadece test için")
    parser.add_argument("--start-date", type=str, default=None,
                        help="Başlangıç tarihi (YYYY-MM-DD). Verilirse o tarihten itibaren Çar/Cuma. Verilmezse ayın ilk Çar/Cuma'lardan başlar.")
    args = parser.parse_args()
    
    # start_date parse
    start_date_obj = None
    if args.start_date:
        try:
            from datetime import datetime as _dt
            start_date_obj = _dt.strptime(args.start_date, "%Y-%m-%d").date()
            log.info(f"Başlangıç tarihi: {start_date_obj.strftime('%d %b %Y (%a)')}")
        except ValueError:
            log.error(f"--start-date geçersiz format: {args.start_date} (YYYY-MM-DD olmalı)")
            sys.exit(1)
    
    year, month = args.year, args.month
    month_label = args.month_label or f"{AY_ADI_TR[month]} {year}"
    
    log.info(f"═══════ Saturn Film içerik üretimi: {month_label} ═══════")
    
    # 1) Tarihler
    dates = compute_post_dates(year, month, n=6, start_date=start_date_obj)
    if len(dates) < 6:
        log.error(f"Yeterli Çar/Cuma yok ({len(dates)}/6). Durduruluyor.")
        sys.exit(1)
    log.info(f"Yayın tarihleri: {', '.join(d.strftime('%d %b') for d in dates)}")
    
    # 2) Bu ayın hizmetleri + layout kombinasyonu
    hizmet_anahtarlari = aylik_rotasyon(month)
    layouts = aylik_layout_secimi(month)   # 6 elemanlı; aya göre çeşitlenir
    log.info(f"Bu ayın hizmetleri: {HIZMETLER[hizmet_anahtarlari[0]]['ad']} + {HIZMETLER[hizmet_anahtarlari[1]]['ad']}")
    log.info(f"Bu ayın layout'ları: {layouts[:3]} (her hizmet için)")
    
    # 3) GitHub repo URL'i (image_url için)
    gh_repo = os.environ.get("GITHUB_REPOSITORY", "<KULLANICI>/saturn-film-social-media")
    gh_branch = os.environ.get("GITHUB_REF_NAME", "main")
    base_url = f"https://raw.githubusercontent.com/{gh_repo}/{gh_branch}/posts"
    
    # 4) OpenAI içerik üretimi
    client = get_openai_client()
    posts = generate_content(client, year, month, hizmet_anahtarlari, layouts)
    
    # 5) Her post için foto üret + render + kaydet
    webhook_url = os.environ.get("MAKE_WEBHOOK_URL")
    if not webhook_url and not args.dry_run:
        log.warning("MAKE_WEBHOOK_URL env yok — webhook atılmayacak (dry-run gibi)")
    
    summary = []
    
    for idx, post in enumerate(posts):
        post_date = dates[idx]
        # Layout ve hizmet KODDAN gelir (GPT'ye güvenmeyiz — tutarlılık için)
        layout = layouts[idx]
        hizmet_anahtari = hizmet_anahtarlari[0] if idx < 3 else hizmet_anahtarlari[1]
        hizmet = HIZMETLER[hizmet_anahtari]
        post["layout"] = layout              # metadata tutarlılığı
        post["hizmet_anahtari"] = hizmet_anahtari
        
        # Her hizmetin sıra numarası (1-4) — global liste
        service_no_map = {"film_yapim": 1, "ai_reklam": 2, "dizi_yapim": 3, "muzik_klibi": 4}
        service_no = service_no_map[hizmet_anahtari]
        
        log.info(f"[{idx+1}/6] {post_date.strftime('%d %b %a')} · {hizmet['ad']} · Layout {layout}")
        
        # Foto üret (M hariç tüm layout'lar foto gerektirir)
        photo = None
        if layout != "M":
            if args.skip_photo:
                # Test placeholder — layout'a göre oran
                if layout == "A":
                    size = (1024, 1536)   # dikey
                elif layout in ("B", "T"):
                    size = (1536, 1024)   # yatay
                else:                     # F, C → kare
                    size = (1024, 1024)
                photo = Image.new("RGB", size, (40, 50, 80))
                log.info("  · Foto: placeholder (skip-photo)")
            else:
                photo = generate_photo(client, hizmet_anahtari, layout)
                log.info(f"  · Foto: {photo.size}")
        
        # Render — 6 layout
        render_map = {
            "A": lambda: render_layout_A(post, photo, service_no),
            "M": lambda: render_layout_M(post, service_no),
            "B": lambda: render_layout_B(post, photo, service_no),
            "F": lambda: render_layout_F(post, photo, service_no),
            "T": lambda: render_layout_T(post, photo, service_no),
            "C": lambda: render_layout_C(post, photo, service_no),
        }
        if layout in render_map:
            img = render_map[layout]()
        else:
            log.error(f"Bilinmeyen layout: {layout}")
            continue
        
        # Kaydet
        slug = slugify_tr(hizmet["ad"])
        filename = f"{post_date.isoformat()}-{slug}-{layout}.png"
        png_path = POSTS / filename
        img.save(png_path, "PNG", optimize=True)
        log.info(f"  · PNG: posts/{filename}")
        
        # Metadata JSON (debug + arşiv için)
        metadata = {
            "tarih": post_date.isoformat(),
            "gun": GUN_ADI_TR[post_date.weekday()],
            "saat": "18:00",
            "ay_label": month_label,
            "hizmet_anahtari": hizmet_anahtari,
            "hizmet": hizmet["ad"],
            "layout": layout,
            "service_no": service_no,
            "headline": post.get("headline"),
            "subtitle": post.get("subtitle"),
            "slogan": post.get("slogan"),
            "subslogan": post.get("subslogan"),
            "cta_headline": post.get("cta_headline"),
            "cta_body": post.get("cta_body"),
            "caption": post.get("caption"),
            "dosya": filename,
            "image_url": f"{base_url}/{filename}",
            "olusturma_tarihi": datetime.now(timezone.utc).isoformat(),
            "durum": "pending",
        }
        json_path = POSTS / f"{post_date.isoformat()}-{slug}-{layout}.json"
        with open(json_path, "w", encoding="utf-8") as f:
            json.dump(metadata, f, ensure_ascii=False, indent=2)
        
        # Webhook payload (Make data store'a)
        webhook_payload = {
            "tarih": metadata["tarih"],
            "gun": metadata["gun"],
            "platform": "instagram",
            "hizmet": metadata["hizmet"],
            "layout": layout,
            "baslik": post.get("headline") or post.get("slogan") or post.get("cta_headline", ""),
            "aciklama": post.get("subtitle") or post.get("subslogan") or post.get("cta_body", ""),
            "caption": post.get("caption", ""),
            "image_url": metadata["image_url"],
            "dosya": filename,
            "durum": "pending",
        }
        
        if webhook_url and not args.dry_run:
            send_to_make(webhook_payload, webhook_url)
        
        summary.append({
            "date": post_date.isoformat(),
            "hizmet": hizmet["ad"],
            "layout": layout,
            "file": filename,
        })
    
    # Özet
    log.info("═══════ ÖZET ═══════")
    for s in summary:
        log.info(f"  · {s['date']} · {s['hizmet']:32s} · Layout {s['layout']} · {s['file']}")
    log.info(f"Toplam {len(summary)} post üretildi.")
    log.info("Bitti. ✅")


if __name__ == "__main__":
    main()
