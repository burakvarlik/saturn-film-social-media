# Sorun Giderme

## GitHub Actions

### "openai.AuthenticationError: Incorrect API key"
**Sebep:** `OPENAI_API_KEY` secret yanlış veya eklenmemiş.  
**Çözüm:** `Settings → Secrets and variables → Actions` → key'i yeniden ekle. Başında `sk-` olduğundan emin ol.

### "f-string expression part cannot include backslash"
**Sebep:** Python 3.11 öncesi f-string'de backslash kabul etmiyor.  
**Çözüm:** Workflow'da Python 3.12 kullanılıyor; bu hatayı görüyorsan workflow dosyasında `python-version: '3.12'` olduğunu kontrol et.

### "Model 'gpt-image-1' does not exist or you do not have access"
**Sebep:** OpenAI hesabında image generation yetkisi yok veya billing eksik.  
**Çözüm:** platform.openai.com → Billing → Payment method ekle, minimum $5 kredi yatır. Hesabın "Tier 1+" olması gerek.

### "Permission denied" git push hatası
**Sebep:** GitHub Actions'ın commit yetkisi yok.  
**Çözüm:** Repo → `Settings → Actions → General → Workflow permissions` → **Read and write permissions** seç.

---

## Make.com

### Senaryo A "No records found"
**Sebep:** Data store boş veya tarih filtresi yanlış.  
**Çözüm:**
1. Data store'a `posts.py` çalıştırıldı mı kontrol et (Senaryo C'nin History'sinde "200 OK" gör)
2. Data store kayıtlarındaki `tarih` alanı `YYYY-MM-DD` formatında mı (örn. `2026-06-05`)
3. Senaryo A'nın filter expression'ı `tarih = formatDate(now; YYYY-MM-DD)` olmalı

### Webhook 404 dönüyor
**Sebep:** Senaryo C pasif veya URL yanlış.  
**Çözüm:**
1. Make.com'da Senaryo C'yi **aktif** yap
2. GitHub Secrets'taki `MAKE_WEBHOOK_URL` ile Senaryo C'deki webhook URL'i birebir aynı mı

### Free plan 2 aktif scenario sınırı
**Sebep:** Make Free planı en fazla 2 scenario aktif tutar.  
**Çözüm:** Sistem zaten bu kısıtla çalışacak şekilde tasarlandı:
- **Normal günlerde:** A + B aktif, C pasif
- **Ayın 25'inde** (içerik üretildikten sonra): A pasif, C aktif → webhook gelir → C pasif, A aktif

### Instagram "Invalid media URL"
**Sebep:** Posts klasörü public olarak erişilebilir değil.  
**Çözüm:**
1. GitHub repo public olmalı
2. URL format: `https://raw.githubusercontent.com/{kullanici}/saturn-film-social-media/main/posts/{dosya_adi}.png`
3. PNG yüklendikten sonra ~30 saniye CDN cache propagation bekle

---

## Telegram

### "Bot didn't reply"
**Sebep:** Bot ile sohbet başlatılmadı.  
**Çözüm:** Bot'a Telegram'da `/start` yaz. Sonra `getUpdates` URL'inden chat_id al.

### "Webhook tetiklenmiyor" (mesaj attığında Senaryo B çalışmıyor)
**Sebep:** Make Telegram modülünde bot watch'u yanlış kurulu.  
**Çözüm:**
1. Senaryo B'nin ilk modülü `Watch Updates` (Polling) olmalı
2. Senaryo B aktif mi kontrol et
3. Bot token Make Connections'da geçerli mi test et

---

## Tasarım / Render

### Logo PNG'leri yanlış görünüyor
**Sebep:** PNG'ler transparent BG'ye sahip olmalı.  
**Çözüm:** `assets/Saturn_Logo_beyaz.png` ve `Saturn_Logo_siyah.png` — Image Viewer'da aç, BG'nin checkerboard olduğunu doğrula.

### Türkçe karakter (â, ğ, ş, ç) render olmuyor
**Sebep:** Font Türkçe karakterleri desteklemiyor.  
**Çözüm:** `generate_posts.py` DejaVu Sans Condensed kullanıyor (tam Türkçe desteği). Eğer custom font eklediysen `.ttf` dosyasını `assets/fonts/` altına koy ve UTF-8 desteğini kontrol et.

### Foto'da kişi yüzü kötü
**Sebep:** gpt-image-1 yüz detaylarında zayıf.  
**Çözüm:** Prompt'larda "wide shot, person occupies <35% of frame, NO close-ups, NO faces visible" ifadelerini kullan. Caption komutu olarak `degistir` yerine yeni foto üretimi henüz desteklenmiyor — bu özellik gelecekte eklenebilir.

---

**Hâlâ takıldıysan:** GitHub Actions log dosyalarının ekran görüntüsünü al, Make.com History sayfasından scenario execution'ı incele. Çoğu sorun bu iki yerden teşhis edilir.

---

# 🚀 Gelişmiş Akış Sorunları (Adım 9)

## `gorsel degistir` çalışmıyor (Make HTTP 404)
**Sebep:** GitHub Personal Access Token (PAT) hatalı veya yetkisi yetersiz.  
**Çözüm:**
1. PAT'in scope'ları: `Contents: Read/Write` + `Actions: Write`
2. PAT repository access'i `saturn-film-social-media` repo'sunu kapsıyor mu?
3. URL'in doğru formatta: `https://api.github.com/repos/<owner>/<repo>/dispatches`
4. Header `Authorization: Bearer <PAT>` — `token` değil, `Bearer`!

## `gorsel degistir` çalışıyor ama yeni görsel gelmemiş
**Sebep:** GitHub Actions tetiklenmiş ama tamamlanmadan Telegram modülü çalıştı.  
**Çözüm:** Sleep modülünü 90 saniye → 120 saniyeye çıkar. gpt-image-1 bazen 90sn'den uzun sürer.

## Yeni görsel geldi ama eski görsel görünüyor (cache)
**Sebep:** Telegram/Instagram CDN aynı URL'i cache'liyor.  
**Çözüm:** Image URL'ine `?v={{formatDate(now; "X"; "Europe/Istanbul")}}` query ekle. Her seferinde farklı timestamp = cache miss.

## Kullanıcı foto upload → "regenerate workflow failed"
**Sebep:** Telegram CDN URL'i geçici (1 saat geçerli). Workflow çalışırken URL expire olmuş.  
**Çözüm:** Make'te `Telegram → Get a File` modülü ile alınan `file_path_url` zaten geçerli süresince valid. Eğer 90sn beklerken expire ediyorsa Sleep'i kısalt (60sn) veya Make'ten önce GitHub'a indir.

## 18:00'de yayınlanmadı, "onaylanmadı" mesajı da gelmedi
**Sebep:** Senaryo A Dal 3 filter'ı yanlış. `durum != approved` koşulu eklenmemiş veya hatalı.  
**Çözüm:** Dal 3 filter: `durum` `Not equal to` `approved` AND `Not equal to` `published` AND `Not equal to` `skipped`. Tüm `Not equal to` koşullarını tek tek ekle.

## `metin degistir` çalışıyor ama caption değişmemiş
**Sebep:** Make Dal 4'ün son HTTP GET adımı (JSON'u GitHub raw'dan oku) cache'lenmiş eski JSON'u getirmiş.  
**Çözüm:**
1. GitHub raw URL'ine `?t={{timestamp}}` ekle
2. veya `regenerate_post.py` commit yaptıktan sonra Make'in HTTP GET'inden önce 10 saniye daha bekle

## "Layout M için kullanıcı fotosu kullanılamaz" uyarısı
**Sebep:** Layout M typography-only, foto alanı yok.  
**Çözüm:** Bu beklenen davranış. Kullanıcı M layout'undaki posta foto yollarsa, fotoyu yoksay, Saturn template'i yeniden render et. Bunu Telegram'da bildir: "Layout M'de foto kullanılamaz, görsel değişmedi."

## GitHub PAT süresi doldu
**Sebep:** Fine-grained PAT'lerin maksimum 1 yıl ömrü var.  
**Çözüm:** https://github.com/settings/tokens → eski token'ı sil, yenisini oluştur, Make'teki tüm HTTP modüllerinde Authorization header'ını güncelle. (Daha iyi: Make Connections'a "GitHub" connection olarak ekle, böylece tek yerden değiştirirsin.)
