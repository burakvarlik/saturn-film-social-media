# Saturn Film — Kurulum Kılavuzu

Bu kılavuz, sıfırdan Saturn Film sosyal medya otomasyonunu çalışır hale getirmek için sırayla yapılması gereken her şeyi içerir.

> **Hedef:** İlk paylaşım **5 Haziran 2026 Cuma 18:00**. Kurulum için ~2-3 saat ayır.

---

## 📋 Kurulum Sırası

```
1. GitHub repo aç                       (5 dk)
2. OpenAI API key oluştur                (5 dk)
3. Telegram bot oluştur                  (5 dk)
4. Make.com hesabı + temel setup         (60-90 dk)
5. GitHub PAT (Personal Access Token)    (5 dk)   ← Gelişmiş akış için
6. Make.com Adım 9 (gelişmiş akış)        (45 dk)  ← Opsiyonel ama önerilir
7. İlk manuel test                       (15 dk)
8. Production aç                         (5 dk)
```

---

## Adım 1 — GitHub Repo

1. **GitHub'da yeni public repo aç:**
   - İsim: `saturn-film-social-media`
   - Public (Actions ücretsiz olsun)
   - README, .gitignore ekleme (zaten elimizdekileri yükleyeceğiz)

2. **Bu ZIP'in içeriğini repo'ya yükle:**
   - Önerilen yol: `git clone` ile boş repo'yu çek, ZIP içeriğini içine koy, `git add . && git commit -m "Initial setup" && git push`
   - Alternatif: GitHub web arayüzünden "Add file → Upload files" ile sürükle-bırak

3. **GitHub Secrets ekle:**  
   `Settings → Secrets and variables → Actions → New repository secret`
   
   Eklenecek secret'lar (her birini ayrı ayrı oluştur):
   
   | Secret adı | Değer | Ne zaman alacağız |
   |---|---|---|
   | `OPENAI_API_KEY` | sk-... | Adım 2'de |
   | `MAKE_WEBHOOK_URL` | https://hook.eu2.make.com/... | Adım 4.6'da |

---

## Adım 2 — OpenAI API Key

1. https://platform.openai.com adresine git
2. Sağ üst köşe → `API Keys` → `Create new secret key`
3. İsim: `saturn-film-social-media`
4. Erişim: `All` (veya en azından chat.completions + images.generations)
5. Çıkan key'i kopyala (`sk-proj-...`)
6. **GitHub Secrets'a `OPENAI_API_KEY` adıyla ekle** (yukarıdaki Adım 1.3)
7. **Billing kontrol:** Hesabında en az **$2 kredi** olduğundan emin ol. Aylık ~$0.25 harcanacak; başlangıçta $5 yatırman 18-20 aya yeter.

---

## Adım 3 — Telegram Bot

1. Telegram'da **@BotFather**'ı aç
2. `/newbot` yaz
3. Bot adı: `Saturn Film Bot` (görünen ad)
4. Bot username: `saturnfilm_bot` veya benzeri (kullanılabilir bir şey)
5. BotFather sana **token** verecek (format: `1234567890:ABC-...`) — kaydet
6. Yeni bot'unu Telegram'da bul, `/start` yaz
7. Chat ID'ni almak için:
   - Tarayıcıda aç: `https://api.telegram.org/bot<TOKEN>/getUpdates`
   - `<TOKEN>` yerine kendi tokenin (örn. `1234567890:ABC-...`)
   - Açılan JSON'da `"chat":{"id": 123456789` görürsün, **bu chat_id'yi kaydet**

> 💡 Hem **bot token** hem **chat_id** Make.com setup'ında kullanılacak (bir sonraki adım).

---

## Adım 4 — Make.com

Detaylı kurulum: `docs/MAKE_SETUP.md`

Kısaca:

1. https://make.com → ücretsiz hesap aç (Free plan yeterli)
2. **Connections** kur:
   - Telegram Bot (token ile)
   - Instagram Business (Facebook OAuth — Saturn Film sayfasına bağlı olmalı)
3. **Data Store** oluştur: `Saturn Film İçerik Takvimi` (8 alan)
4. **3 senaryo** oluştur (A, B, C) — modül bağlantıları `MAKE_SETUP.md`'de
5. **Senaryo C'nin webhook URL'ini al** → GitHub Secrets'a `MAKE_WEBHOOK_URL` olarak ekle (Adım 1.3)
6. Senaryo A ve B'yi sürekli aktif yap; C'yi sadece manuel tetiklemeden önce aç

---

## Adım 5 — İlk Manuel Test

Henüz Haziran 25 gelmedi ama Haziran içeriklerini şimdi üretmemiz lazım (kurulum bittiğinde):

1. **Make.com'a gir:**
   - Senaryo A'yı **pasif** yap (Free plan 2 aktif sınırı)
   - Senaryo C'yi **aktif** yap

2. **GitHub'da workflow'u manuel tetikle:**
   - Repo → `Actions` sekmesi → `Generate Monthly Posts` workflow'u
   - Sağ üstte `Run workflow` butonu
   - Inputs:
     - `year`: 2026
     - `month`: 6
     - `month_label`: Haziran 2026
   - `Run workflow` bas

3. **~5 dakika bekle:** workflow logları sayfasından ilerlemeyi görebilirsin
4. **Kontrol et:**
   - GitHub repo'da `posts/` klasörüne 6 PNG düşmüş olmalı
   - Make.com'da Data Store'a 6 kayıt yazılmış olmalı (Senaryo C'nin History'sinden görürsün)

5. **Make.com'a geri dön:**
   - Senaryo C'yi **pasif** yap
   - Senaryo A'yı **aktif** yap

6. **Telegram'da önizleme bekle:** İlk önizleme **5 Haziran Cuma 18:00**'de gelecek

---

## Adım 6 — Production'a Geç

Manuel test başarılıysa:

1. GitHub Actions cron zaten ayın 25'inde otomatik tetiklenir
2. Haziran 25 → Temmuz içerikleri üretilir (sen hiçbir şey yapmazsın)
3. Her ayın 25'inde aynı 2-aşama Make pas/akt değişimi gerekir (~2 dk iş)
4. Günlük: Çar/Cuma 18:00'de Telegram'a düşen önizlemeye `onayla` / `degistir` / `ertele` yaz

---

## ⚠️ Kontrol Listesi

Kuruluma başlamadan önce elinde olması gerekenler:

- [ ] Saturn Film Instagram hesabının **Business Account**'a çevrildiği (Personal değil)
- [ ] Instagram hesabının bir **Facebook Sayfası**'na bağlı olduğu (Meta Business Suite)
- [ ] Saturn Film için **kullanılacak email** (OpenAI, Make, Telegram hesapları için)
- [ ] Bu repo'yu açacağın **GitHub kullanıcı adı**

Bunlar yoksa önce hallet, sonra Adım 1'e geç.

---

## Sorun mu var?

`docs/TROUBLESHOOTING.md` dosyasına bak. En yaygın sorunlar:

- Make.com Senaryo A "no records" diyor → Data store boş veya tarihler yanlış
- GitHub Actions f-string hatası → Python 3.11+ kullanılıyor, eski sözdizimi var
- Instagram yükleme "Invalid media URL" → Repo public değil ya da PNG yolu yanlış
- gpt-image-1 "unsupported model" → API key'in image generation yetkisi yok

---

**Hazır olduğunda Adım 1'den başla.** 🚀
