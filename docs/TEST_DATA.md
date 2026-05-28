# Test Verileri

Make.com senaryolarını test etmek için hazır payload örnekleri.

---

## 1. Senaryo C Webhook Testi

GitHub Actions'tan gelecek POST'u simüle eder. `<WEBHOOK_URL>` yerine kendi Make webhook URL'ini koy.

### Tek post payload

```bash
curl -X POST <WEBHOOK_URL> \
  -H "Content-Type: application/json" \
  -d '{
    "tarih": "2026-06-05",
    "gun": "Cuma",
    "platform": "instagram",
    "hizmet": "Film Yapım",
    "layout": "M",
    "baslik": "HİKÂYENİZİ YENİ BİR YÖRÜNGEYE",
    "aciklama": "— uzun metraj, kısa film, belgesel",
    "caption": "🎬 Her hikâye bir yörünge çizer.\n\nSaturn Film & Entertainment olarak senaryodan post-prodüksiyona uzanan yolculukta, hikâyenizi taşıyacak güvenli ellerdeyiz.\n\nUzun metraj, kısa film ve belgesel projeleriniz için profesyonel ekibimizle yanınızdayız.\n\n📞 İletişim:\n🌐 www.saturnfilm.net\n📩 info@saturnfilm.net\n\n#SaturnFilm #FilmYapımı #Sinema #FilmProdüksiyon #TürkSineması",
    "image_url": "https://raw.githubusercontent.com/<KULLANICI>/saturn-film-social-media/main/posts/2026-06-05-film-yapim-M.png",
    "dosya": "2026-06-05-film-yapim-M.png",
    "durum": "pending"
  }'
```

### Bugünün tarihi ile test (Senaryo A'yı tetiklemek için)

```bash
# YYYY-MM-DD formatında bugünün tarihi
TODAY=$(date +%Y-%m-%d)

curl -X POST <WEBHOOK_URL> \
  -H "Content-Type: application/json" \
  -d "{
    \"tarih\": \"$TODAY\",
    \"gun\": \"$(date +%A)\",
    \"platform\": \"instagram\",
    \"hizmet\": \"Film Yapım\",
    \"layout\": \"A\",
    \"baslik\": \"TEST BAŞLIĞI\",
    \"aciklama\": \"Test açıklaması italik\",
    \"caption\": \"Test caption metni.\\n\\n#SaturnFilm #Test\",
    \"image_url\": \"https://via.placeholder.com/1080x1080/0A0E1A/C9A961?text=SATURN+TEST\",
    \"dosya\": \"test-bugun.png\",
    \"durum\": \"pending\"
  }"
```

Bu payload'u attıktan sonra:
1. Data Store'da bugünün tarihiyle kayıt var mı kontrol et
2. Senaryo A'yı `Run once` ile manuel tetikle
3. Telegram'a bildirim gelmeli

---

## 2. Manuel Data Store Kaydı (Make UI'dan)

Eğer curl yerine elle test yapmak istersen, Make.com'da:

`Data Stores → Saturn Film İçerik Takvimi → + Add a record`

Aşağıdaki değerleri tek tek gir:

| Alan | Test Değeri |
|---|---|
| **key** (otomatik) | (boş bırak, Make üretir) |
| tarih | bugünün tarihi (YYYY-MM-DD) |
| gun | bugünün günü (Pazartesi/Salı/...) |
| platform | `instagram` |
| hizmet | `Film Yapım` |
| layout | `A` |
| baslik | `TEST POSTU` |
| aciklama | `Bu bir test postudur` |
| caption | `🎬 Test caption.\n\n#SaturnFilm` |
| image_url | `https://via.placeholder.com/1080x1080` |
| dosya | `test.png` |
| durum | `pending` |

---

## 3. Senaryo B Komut Testleri

Telegram'da bot'una sırayla şu mesajları yaz:

### 3.1 `ertele` → en güvenli test

```
ertele
```

**Beklenen:** "⏰ ERTELENDİ" mesajı, Data Store'da `durum=skipped`.

### 3.2 `degistir` → AI çağrı testi (~$0.01 maliyet)

Önce başka bir test kaydı oluştur (`durum=notified` olmalı), sonra:

```
degistir
```

**Beklenen:** ~10 saniye sonra yeni caption ile foto + caption mesajı.  
**Kontrol:** Data Store'da `caption` alanı güncellenmiş mi?

### 3.3 `onayla` → ⚠️ Gerçek Instagram yayını

> ⚠️ **DİKKAT:** Bu komut **gerçek Instagram hesabınıza** post atar! Test için ya geçici test hesabı kullan, ya da Instagram'dan hemen sil.

Önce yeni test kaydı (`durum=notified`):

```
onayla
```

**Beklenen:** "✅ YAYINLANDI", Saturn Film Instagram'da post.

Test sonrası: Instagram'a git, postu manuel sil (eğer test hesabı kullanmıyorsan).

### 3.4 `onayla TEST CAPTION DEĞIŞTI` → custom caption testi

```
onayla 🎬 BU BİR TEST CAPTIONIDIR. Otomasyon çalışıyor!
```

**Beklenen:** Instagram'a girilen text ile post atılır.

### 3.5 Tanınmayan komut testi (eğer default dal eklediysen)

```
selam
```

**Beklenen:** "❓ KOMUT ANLAŞILMADI" mesajı.

---

## 4. Test Sonrası Temizlik

Tüm test bittikten sonra:

1. **Data Store:** Tüm test kayıtlarını sil  
   `Data Stores → Saturn Film İçerik Takvimi → Browse records → checkbox seç → Delete`

2. **Instagram:** Test postlarını manuel sil

3. **Senaryo History:** Make.com'da `Scenarios → [scenario] → History` sekmesinden test execution'larını arşivle veya silebilirsin (opsiyonel)

---

## 5. Production'a Geçmeden Önce Final Kontrol

| Kontrol | OK? |
|---|---|
| Telegram bot'a `/start` yazıldı, chat_id doğru | ☐ |
| Senaryo A test edildi, Telegram'a önizleme geldi | ☐ |
| Senaryo B - Dal 1 (`degistir`) test edildi, GPT cevabı geldi | ☐ |
| Senaryo B - Dal 2 (`onayla [metin]`) test edildi, Instagram'a custom caption gitti | ☐ |
| Senaryo B - Dal 3 (`onayla`) test edildi, Instagram'a mevcut caption gitti | ☐ |
| Senaryo B - Dal 4 (`ertele`) test edildi, durum güncellendi | ☐ |
| Senaryo C webhook test edildi, Data Store'a kayıt yazıldı | ☐ |
| Tüm test kayıtları silindi | ☐ |
| Tüm test Instagram postları silindi | ☐ |
| Senaryo A: ON, Senaryo B: ON, Senaryo C: OFF | ☐ |

Hepsi ✓ olduğunda → Production hazır.
