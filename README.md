# Saturn Film & Entertainment — Sosyal Medya Otomasyonu

Saturn Film & Entertainment için aylık Instagram içerik üretim ve yayın otomasyonu.

GitHub Actions her ayın 25'inde tetiklenir, OpenAI ile içerik + fotoğraf üretir, Saturn dark sinematik template'ini uygular, Make.com'a webhook gönderir. Make sıralanan postları Telegram'a önizleme olarak düşürür; tek komutla Instagram'a yayınlar.

## Sistem mimarisi

```
┌─────────────────────────────────────────────────────────────────────┐
│      GITHUB ACTIONS                                                  │
│                                                                      │
│  generate-monthly-posts.yml (her ayın 25'i, 06:00 UTC)               │
│    └── 6 post (PNG + JSON) üret → posts/ → Make webhook              │
│                                                                      │
│  regenerate-post.yml (Make'ten repository_dispatch ile)              │
│    ├── regenerate-photo-ai    → AI yeni foto + Saturn template       │
│    ├── regenerate-photo-user  → kullanıcı fotosu + Saturn template   │
│    └── regenerate-caption     → AI yeni caption                      │
└─────────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────────┐
│      MAKE.COM                                                        │
│                                                                      │
│  Senaryo C — Webhook (yalnız 25'inde aktif)                          │
│    └── GitHub'tan post → Data Store'a yaz                            │
│                                                                      │
│  Senaryo A — Schedule (her 15dk kontrol)                             │
│    ├── Çar/Cuma 14:00 + pending  → görsel+caption önizleme           │
│    ├── Çar/Cuma 18:00 + approved → Instagram'a yayınla               │
│    └── Çar/Cuma 18:00 + !approved → "onaylanmadı" bildirim           │
│                                                                      │
│  Senaryo B — Telegram Watch (6 dallı router)                         │
│    ├── 📸 Foto gönderildi       → repo_dispatch user-photo           │
│    ├── ✅ "onayla"              → durum=approved                      │
│    ├── 🔄 "gorsel degistir"     → repo_dispatch ai-photo              │
│    ├── 🔄 "metin degistir"      → repo_dispatch caption               │
│    ├── ✏️  "metin: [yeni metin]" → durum/caption güncelle             │
│    └── ⏰ "ertele" / "elden"    → durum=skipped                       │
└─────────────────────────────────────────────────────────────────────┘
                              │
                              ▼
                       INSTAGRAM YAYIN
```

## Onay akışı (yayın günü)

```
14:00 Çar/Cuma → Görsel + Caption tek önizleme + 6 komut
                 (4 saatlik düzenleme penceresi başlar)
                 
14:00–17:59    → Kullanıcı istediği kadar düzenler:
                 - Görseli değiştirir (AI veya kendi foton)
                 - Caption'ı değiştirir (AI veya kendi metnin)
                 - Ertelerse post atlanır
                 - Onaylarsa 18:00'de yayına hazır

18:00 Çar/Cuma → durum=approved ise Instagram'a otomatik yayın
                 durum != approved ise "onaylanmadı" bildirimi
```

## Hizmet rotasyonu

Aylık 2 hizmet × 3 post (Layout A, M, B) = **6 post/ay**.

| Ay | Hizmet 1 | Hizmet 2 |
|---|---|---|
| Haziran 2026 | Film Yapım | Yapay Zeka Reklam Filmleri |
| Temmuz 2026 | Dizi Yapımı | Müzik Klibi |
| Ağustos 2026 | Film Yapım | Yapay Zeka Reklam Filmleri |
| Eylül 2026 | Dizi Yapımı | Müzik Klibi |

İki ayda 4 hizmet tamamlanır, sonra döngü yeniden başlar.

## Yayın takvimi

Çarşamba + Cuma · 18:00 Türkiye saati.

Her hizmet için **B → M → A** sırasında 3 ardışık post. Bu sıralama Instagram feed grid'inde "A (sol) | M (orta) | B (sağ)" görünümünü oluşturur.

## Tasarım dili

Dark sinematik (BG `#0A0E1A`), Saturn logo renkleri aksent:
- **Gold** `#C9A961` — sweep çizgiler, URL, hizmet sayacı
- **Cyan** `#1FB6E6` — tag'ler, vurgu noktaları
- **White** — ana tipografi
- Modern sans-serif condensed bold tipografi, CAPS başlıklar
- 1080×1080 Instagram square

## Aylık maliyet

| Servis | Maliyet |
|---|---|
| OpenAI GPT-4o (içerik) | ~$0.04 |
| OpenAI gpt-image-1 (4 foto × $0.04) | ~$0.16 |
| Caption regenerate (her `degistir`) | +$0.01 |
| GitHub Actions | Ücretsiz (public repo) |
| Make.com | Ücretsiz (Free plan) |
| **TOPLAM** | **~$0.20–0.25/ay** |

> Layout M postlarında foto yok (typography-only), 6 post için sadece 4 foto üretilir.

## Repo yapısı

```
saturn-film-social-media/
├── README.md                                ← Bu dosya
├── SETUP.md                                 ← Adım adım kurulum kılavuzu
├── .gitignore
├── .github/
│   └── workflows/
│       └── generate-monthly-posts.yml       ← GitHub Actions (cron)
├── scripts/
│   ├── generate_posts.py                    ← Ana üretim scripti
│   └── requirements.txt                     ← Python bağımlılıkları
├── assets/
│   ├── Saturn_Logo_beyaz.png                ← Beyaz logo (transparent BG)
│   └── Saturn_Logo_siyah.png                ← Siyah logo (transparent BG)
├── posts/                                   ← Otomatik dolacak (üretilen PNG + JSON)
└── docs/
    ├── MAKE_SETUP.md                        ← Make.com kurulum kılavuzu
    └── TROUBLESHOOTING.md                   ← Sorun giderme
```

## Hızlı başlangıç

İlk kurulum için `SETUP.md` dosyasını takip edin. Sırasıyla:

1. Bu repo'yu GitHub'da public olarak aç
2. OpenAI API key oluştur, GitHub Secrets'a ekle
3. Telegram bot oluştur (`@BotFather`)
4. Make.com'da 3 senaryo, 1 data store, bağlantıları kur (`docs/MAKE_SETUP.md`)
5. İlk test: `workflow_dispatch` ile manuel tetikle
6. Telegram'da önizleme geldiğinde kontrol et
7. Cron aktif, sistem otomatik akar

---

**İletişim:** info@saturnfilm.net · [saturnfilm.net](https://www.saturnfilm.net)
