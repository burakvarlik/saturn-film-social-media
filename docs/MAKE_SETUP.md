# Make.com Kurulum Kılavuzu — Saturn Film

Bu kılavuz, sıfır Make.com bilgisiyle başlayan birinin **60-90 dakikada** Saturn Film otomasyonunu çalışır hale getirmesi için yazıldı.

> 📌 **Gereksinimler (başlamadan önce):**
> - `@BotFather`'dan oluşturulmuş Telegram bot ve **token** ✅ (sende var)
> - Bot ile sohbet başlatılmış, **chat_id** alınmış (Adım 1.3'te)
> - Saturn Film Instagram hesabının **Business Account** olduğu
> - Instagram'ın bir Facebook Sayfası'na bağlı olduğu
> - OpenAI API key (Senaryo B'deki `degistir` komutu için ayrı bir key olabilir, aynı da olabilir)
> - GitHub repo public olarak açık (image URL erişimi için)

---

## İçindekiler

1. [Adım 1 — Telegram chat_id'yi al](#adım-1)
2. [Adım 2 — Make.com hesap ve bağlantılar](#adım-2)
3. [Adım 3 — Data Store oluştur](#adım-3)
4. [Adım 4 — Senaryo C (Webhook)](#adım-4)
5. [Adım 5 — Senaryo A (Günlük Bildirim)](#adım-5)
6. [Adım 6 — Senaryo B (Komut Router)](#adım-6)
7. [Adım 7 — Test akışı](#adım-7)
8. [Adım 8 — Production'a geçiş](#adım-8)
9. [Aylık operasyon rutini](#aylık-rutin)

---

<a id="adım-1"></a>
## Adım 1 — Telegram chat_id'yi al

1. Telegram'da bot'una git, `/start` yaz (mutlaka, yoksa chat oluşmaz)
2. Bot'a tek bir mesaj yaz: `merhaba` gibi
3. Tarayıcıda şu URL'i aç (`<TOKEN>` yerine kendi bot token'ını koy):
   ```
   https://api.telegram.org/bot<TOKEN>/getUpdates
   ```
4. Açılan JSON içinde şunu bul:
   ```json
   "chat": {
     "id": 123456789,
     ...
   }
   ```
5. Bu **chat_id** değerini (`123456789` gibi bir sayı) bir yere yaz, Adım 5 ve 6'da kullanılacak

> 💡 **chat_id görünmüyor mu?** Bot'a `/start` yazmadın demektir. Geri dön, `/start` yaz, mesaj at, sonra URL'i yeniden aç.

---

<a id="adım-2"></a>
## Adım 2 — Make.com Hesap ve Bağlantılar

### 2.1 Hesap aç

1. https://make.com → "Get started free"
2. Email ile kayıt ol (Saturn Film için kullanılacak email)
3. Onay maili gelir, doğrula
4. Bölge seç: **EU2** (Türkiye için en hızlısı, latency düşük)
5. Onboarding adımlarını atla — direkt dashboard'a geç

### 2.2 Telegram Bot bağlantısı

1. Sol menüden `Connections` → sağ üstte `+ Add a connection`
2. App ara: `Telegram Bot` → seç
3. Connection name: `Saturn Film Telegram Bot`
4. **Token** field'ına BotFather'dan aldığın token'ı yapıştır
5. `Save` → "Connection successful" mesajını gör

### 2.3 Instagram Business bağlantısı

1. `Connections → + Add a connection`
2. App ara: `Instagram for Business` → seç
3. Connection name: `Saturn Film Instagram`
4. `Continue` butonuna bas → Facebook OAuth penceresi açılır
5. **Saturn Film yönetici hesabının** Facebook'una giriş yap
6. Yetki istenen sayfa listesinde **Saturn Film** sayfasını seç
7. **TÜM yetkileri ver** (Instagram Business + Page management)
8. Make'e geri dön, "Connection successful" gör

> ⚠️ **Hata: "No Instagram Business Account found"**
> Instagram hesabın hâlâ Personal modda. Instagram app → Settings → Account Type → "Switch to Professional → Business" yap. Sonra Facebook sayfasıyla bağla (Meta Business Suite).

### 2.4 OpenAI HTTP bağlantısı

`degistir` komutu için Make'ten OpenAI'a HTTP isteği atacağız. Connection değil, doğrudan modül içinde header kullanılır. Şimdilik **API key'i bir yere yaz** — Adım 6.4'te kullanacaksın.

---

<a id="adım-3"></a>
## Adım 3 — Data Store Oluştur

Data Store, Make'in içindeki mini bir veritabanı. Senaryo C buraya yazar, A bunu okur, B günceller.

### 3.1 Yeni Data Store

1. Sol menüden `Data Stores` → sağ üstte `+ Add data store`
2. Name: `Saturn Film İçerik Takvimi`
3. Data structure: `+ Add` → yeni bir structure oluştur (aşağıda)
4. **Data storage size:** `1 MB` (Free plan için yeterli, ~5000 kayıt)

### 3.2 Data Structure (alanlar)

`+ Add` → Specification name: `Saturn Post Schema`. Sonra `+ Add item` ile her alanı tek tek ekle:

| Field name | Type | Required | Default |
|---|---|---|---|
| `tarih` | Text | ✓ | (boş) |
| `gun` | Text | ✗ | (boş) |
| `platform` | Text | ✗ | `instagram` |
| `hizmet` | Text | ✗ | (boş) |
| `layout` | Text | ✗ | (boş) |
| `baslik` | Text | ✗ | (boş) |
| `aciklama` | Text | ✗ | (boş) |
| `caption` | Text | ✗ | (boş) |
| `image_url` | Text | ✗ | (boş) |
| `dosya` | Text | ✗ | (boş) |
| `durum` | Text | ✗ | `pending` |

> 💡 **`caption` çok uzun olabilir.** Make Data Store'da text field 65k karaktere kadar dayanır, sorun olmaz.

3. Tüm alanları ekledikten sonra `Save` → Data Structure hazır
4. Data Store da artık bu structure'ı kullanıyor → `Save`

### 3.3 Primary Key

Data Store'un kendi `key` alanı var (otomatik). **Biz `tarih` alanını primary key olarak kullanacağız** — yani aynı tarihe iki post yazılmasın. Bunu Senaryo C'de "upsert" işlemiyle sağlayacağız (`tarih` ile arar, varsa günceller, yoksa ekler).

---

<a id="adım-4"></a>
## Adım 4 — Senaryo C (Webhook)

**Amaç:** GitHub Actions her ayın 25'inde 6 post üretip Make'e POST atar. Bu webhook her POST'u Data Store'a yazar.

> ⚠️ **Free plan kısıtı:** En fazla 2 senaryo aktif olabilir. C senaryosu sadece **ayın 25'inde manuel aktifleştirilir**, içerik düştükten sonra pasifleştirilir. Normal günlerde aktif olan ikili: A + B.

### 4.1 Senaryo oluştur

1. Sol menüden `Scenarios` → `+ Create a new scenario`
2. Sağ üstte adlandır: **`Saturn — C — Webhook (Yeni İçerik)`**

### 4.2 Modüller

**Modül 1: Webhooks → Custom webhook**

1. `+` ikonu → ara: `Webhooks` → seç → `Custom webhook`
2. Webhook: `+ Add` → name: `Saturn Content Webhook` → `Save`
3. **URL'i kopyala** (örnek: `https://hook.eu2.make.com/abc123xyz...`)
4. **Bu URL'i GitHub Secrets'a `MAKE_WEBHOOK_URL` adıyla ekle** (Repo Settings → Secrets and variables → Actions)

**Modül 2: Data Store → Add/Replace a record**

1. Sağ tarafa `+` → ara: `Data Store` → seç → `Add/Replace a record`
2. Data store: `Saturn Film İçerik Takvimi`
3. Key:
   - **Operator:** `Update existing or create new`
   - **Key:** `{{1.tarih}}` (Mapping: 1. modül → tarih)
4. Record (mapping her alan için, 1. modülden gelen veriler):

| Field | Value |
|---|---|
| tarih | `{{1.tarih}}` |
| gun | `{{1.gun}}` |
| platform | `{{1.platform}}` |
| hizmet | `{{1.hizmet}}` |
| layout | `{{1.layout}}` |
| baslik | `{{1.baslik}}` |
| aciklama | `{{1.aciklama}}` |
| caption | `{{1.caption}}` |
| image_url | `{{1.image_url}}` |
| dosya | `{{1.dosya}}` |
| durum | `{{1.durum}}` |

5. `OK`

**Modül 3: Webhooks → Webhook response**

1. `+` → `Webhooks` → `Webhook response`
2. Status: `200`
3. Body: `{"ok": true, "key": "{{2.key}}"}`
4. `OK`

### 4.3 Senaryo ayarları

1. Sol alttaki ⚙️ → Scenario settings
2. **Auto-commit:** ON
3. **Max number of consecutive errors:** 3
4. Save → Scenario'yu kaydet (Ctrl+S)

### 4.4 Test

1. Sağ üstteki `Run once` butonuna bas → "Waiting for webhook" görüyor
2. Test için curl/Postman ile bir POST at:
   ```bash
   curl -X POST <WEBHOOK_URL> \
     -H "Content-Type: application/json" \
     -d '{
       "tarih": "2026-06-05",
       "gun": "Cuma",
       "platform": "instagram",
       "hizmet": "Film Yapım",
       "layout": "M",
       "baslik": "TEST",
       "aciklama": "Test açıklaması",
       "caption": "Test caption",
       "image_url": "https://example.com/test.png",
       "dosya": "test.png",
       "durum": "pending"
     }'
   ```
3. Make sahnesinde 3 modülün hepsinin yeşil çek işareti almasını gör
4. Data Stores → `Saturn Film İçerik Takvimi` → kaydı görmeli
5. **Test kaydını sil** (Data Stores → seç → trash icon)

### 4.5 Pasifleştir

Sağ üstteki `ON/OFF` toggle'ını **OFF** yap. C senaryosu sadece ayın 25'inde aktif olacak.

---

<a id="adım-5"></a>
## Adım 5 — Senaryo A (Günlük Bildirim)

**Amaç:** Her 15 dakikada Data Store'u kontrol et. Eğer bugünün tarihi varsa ve durum `pending` ise → Telegram'a önizleme gönder.

### 5.1 Senaryo oluştur

`Scenarios → + Create a new scenario` → Name: **`Saturn — A — Günlük Telegram Bildirim`**

### 5.2 Modüller

**Modül 1: Schedule (trigger)**

1. Sol başlangıç dairesi → `Add a trigger` → ara: `Schedule`
2. Run scenario: `At regular intervals`
3. Interval: `15 minutes`
4. Advanced scheduling: `+ Add item`
   - Type: `Days of week`
   - Days: **Wednesday, Friday** (sadece bu iki gün)
   - Time: `18:00`-`18:15` (saat aralığında tetiklensin)
5. `OK`

**Modül 2: Data Store → Search records**

1. `+` → `Data Store` → `Search records`
2. Data store: `Saturn Film İçerik Takvimi`
3. Filter:
   - **Field:** `tarih`
   - **Operator:** `Text operators: Equal to`
   - **Value:** `{{formatDate(now; "YYYY-MM-DD"; "Europe/Istanbul")}}`
4. Filter EKLE:
   - **AND**
   - **Field:** `durum`
   - **Operator:** `Equal to`
   - **Value:** `pending`
5. Maximum number of returned records: `1`
6. `OK`

**Modül 3: Telegram Bot → Send a Photo**

1. `+` → `Telegram Bot` → `Send a Photo`
2. Connection: `Saturn Film Telegram Bot`
3. **Chat ID:** chat_id'ni yapıştır (Adım 1.5'te aldığın sayı)
4. **Photo:** `{{2.image_url}}` (URL — public GitHub raw)
5. **Caption:** (aşağıdaki blok — kopyala/yapıştır)
   ```
   🎬 *SATURN — BUGÜNKÜ POST*
   
   📅 {{2.tarih}} · {{2.gun}}
   🎯 {{2.hizmet}} · Layout {{2.layout}}
   
   *{{2.baslik}}*
   _{{2.aciklama}}_
   
   ━━━━━━━━━━━━━━━━━━
   📝 INSTAGRAM CAPTION:
   
   {{2.caption}}
   ━━━━━━━━━━━━━━━━━━
   
   ✅ Onayla → `onayla`
   🔄 Yeni caption iste → `degistir`
   ✏️ Kendi caption'ın → `onayla [yeni metin]`
   ⏰ Ertele → `ertele`
   ```
6. **Parse mode:** `Markdown`
7. `OK`

**Modül 4: Data Store → Update a record**

1. `+` → `Data Store` → `Update a record`
2. Data store: `Saturn Film İçerik Takvimi`
3. Key: `{{2.key}}`
4. Record:
   - `durum`: `notified` *(bunu Senaryo B'de durum kontrol için kullanacağız)*
5. `OK`

### 5.3 Filter ekle (Modül 2 → 3 arası)

Modül 2 ile 3 arasındaki çizgiye tıkla → Set up a filter:

- Name: `Kayıt var mı`
- Condition:
  - Field: `{{2.total_records}}` (alternatif: `{{length(2.array)}}`)
  - Operator: `Greater than or equal to`
  - Value: `1`

Bu, eğer bugün için pending post yoksa scenario'nun gereksiz çalışmasını engeller.

### 5.4 Aktif et

Sağ üstteki `OFF` toggle'ını **ON** yap.

---

<a id="adım-6"></a>
## Adım 6 — Senaryo B (Komut Router)

**Amaç:** Telegram'a yazdığın komuta göre 4 farklı aksiyon. En karmaşık senaryo.

### 6.1 Senaryo oluştur

`Scenarios → + Create a new scenario` → Name: **`Saturn — B — Telegram Komut Router`**

### 6.2 Modül 1: Telegram Watch Updates

1. Sol dairesi → `Add a trigger` → `Telegram Bot` → `Watch Updates`
2. Connection: `Saturn Film Telegram Bot`
3. **Update types:** `Message` (sadece text mesajları)
4. Limit: `1`
5. `OK`

### 6.3 Modül 2: Router (3 dal)

1. `+` → `Flow Control` → `Router`
2. Dal 1, 2, 3 oluştur (her dalın filter'ı aşağıda)

### 6.4 Dal 1 — "DEGISTIR" → Yeni caption üret

**Filter (Router → Dal 1):**
- Name: `Komut: degistir`
- Condition:
  - `{{lower(1.message.text)}}` `Equal to` `degistir`

**Modül 1.1: Data Store → Search records**
- Filter:
  - `tarih` `Equal to` `{{formatDate(now; "YYYY-MM-DD"; "Europe/Istanbul")}}`
  - AND `durum` `Equal to` `notified`
- Max: 1

**Modül 1.2: HTTP → Make a request** *(OpenAI'dan yeni caption)*
- URL: `https://api.openai.com/v1/chat/completions`
- Method: `POST`
- Headers:
  - `Authorization: Bearer YOUR_OPENAI_KEY` *(API key'ini buraya yapıştır)*
  - `Content-Type: application/json`
- Body type: `Raw`
- Content type: `JSON (application/json)`
- Request content:
  ```json
  {
    "model": "gpt-4o",
    "messages": [
      {
        "role": "system",
        "content": "Sen Saturn Film için Instagram caption üreten kreatif bir yazarsın. Profesyonel, sinematik, vurucu yaz. Mevcut başlık ve açıklamadan yola çıkarak YENİ ve FARKLI bir caption üret. Sondaki iletişim bloğu ve hashtag'leri olduğu gibi koru."
      },
      {
        "role": "user",
        "content": "Hizmet: {{1.1.hizmet}}\nBaşlık: {{1.1.baslik}}\nAçıklama: {{1.1.aciklama}}\n\nMevcut caption:\n{{1.1.caption}}\n\nLütfen yeni bir caption üret. Sondaki iletişim ve hashtag bloğunu aynen koru. Sadece caption'ı dön, başka bir şey ekleme."
      }
    ],
    "temperature": 0.9
  }
  ```
- Parse response: `Yes`

**Modül 1.3: Data Store → Update a record**
- Key: `{{1.1.key}}`
- Record: `caption` → `{{1.2.data.choices[].message.content}}`

**Modül 1.4: Telegram Bot → Send a Photo**
- Chat ID: chat_id
- Photo: `{{1.1.image_url}}`
- Caption:
  ```
  🔄 *YENİ CAPTION ÜRETİLDİ*
  
  📅 {{1.1.tarih}} · {{1.1.gun}}
  
  *{{1.1.baslik}}*
  _{{1.1.aciklama}}_
  
  ━━━━━━━━━━━━━━━━━━
  📝 YENİ CAPTION:
  
  {{1.2.data.choices[].message.content}}
  ━━━━━━━━━━━━━━━━━━
  
  ✅ Onayla → `onayla`
  🔄 Tekrar değiştir → `degistir`
  ```
- Parse mode: `Markdown`

### 6.5 Dal 2 — "ONAYLA + METİN" → Custom caption ile yayınla

**Filter (Router → Dal 2):**
- Name: `Komut: onayla [metin]`
- Condition:
  - `{{1.message.text}}` `Matches pattern` `(?i)^onayla\s+\S+.*`

**Modül 2.1: Data Store → Search records** (Dal 1'deki gibi)

**Modül 2.2: Instagram for Business → Create a Photo Post**
- Connection: `Saturn Film Instagram`
- **Image URL:** `{{2.1.image_url}}`
- **Caption:** `{{replace(1.message.text; "(?i)^onayla\s+"; "")}}` *(komutun başındaki "onayla " kısmını siler)*
- Publish: `Yes`
- `OK`

**Modül 2.3: Telegram Bot → Send a Text Message**
- Chat ID: chat_id
- Text:
  ```
  ✅ *YAYINLANDI*
  
  📅 {{2.1.tarih}}
  🎯 {{2.1.hizmet}}
  
  Instagram'a custom caption ile gönderildi.
  ```
- Parse mode: `Markdown`

**Modül 2.4: Data Store → Update a record**
- Key: `{{2.1.key}}`
- Record: `durum` → `published`

### 6.6 Dal 3 — "ONAYLA" (sade) → Mevcut caption ile yayınla

**Filter (Router → Dal 3):**
- Name: `Komut: onayla`
- Condition:
  - `{{lower(1.message.text)}}` `Equal to` `onayla`

**Modül 3.1: Data Store → Search records** (Dal 1'deki gibi)

**Modül 3.2: Instagram for Business → Create a Photo Post**
- Image URL: `{{3.1.image_url}}`
- Caption: `{{3.1.caption}}` *(mevcut caption — Data Store'dan)*
- Publish: `Yes`

**Modül 3.3: Telegram Bot → Send a Text Message**
- Text:
  ```
  ✅ *YAYINLANDI*
  
  📅 {{3.1.tarih}}
  🎯 {{3.1.hizmet}}
  
  Mevcut caption ile Instagram'a gönderildi.
  ```

**Modül 3.4: Data Store → Update a record**
- `durum` → `published`

### 6.7 Dal 4 — "ERTELE" → O günü atla

**Filter (Router → Dal 4):**
- Name: `Komut: ertele`
- Condition:
  - `{{lower(1.message.text)}}` `Equal to` `ertele`

**Modül 4.1: Data Store → Search records** (yine aynı)

**Modül 4.2: Data Store → Update a record**
- `durum` → `skipped`

**Modül 4.3: Telegram Bot → Send a Text Message**
- Text:
  ```
  ⏰ *ERTELENDİ*
  
  📅 {{4.1.tarih}} · {{4.1.hizmet}}
  Bu post atlandı, yayınlanmayacak.
  ```

### 6.8 Aktif et

Sağ üstteki toggle → **ON**.

---

<a id="adım-7"></a>
## Adım 7 — Test Akışı

Henüz GitHub Actions ile içerik üretmedik. Önce manuel test:

### 7.1 Webhook test (Senaryo C)

1. Senaryo C'yi **aktif** yap (A'yı şimdilik pasif yap, Free plan)
2. Adım 4.4'teki curl'ü tekrar at → Data Store'a kayıt yazılsın
3. **Bu kez tarih'i bugünün tarihi yap** (örnek `"tarih": "2026-05-28"`)
4. `durum`: `pending` olsun
5. Senaryo C'yi tekrar **pasif** yap
6. Senaryo A'yı **aktif** yap

### 7.2 Telegram bildirim test (Senaryo A)

1. Senaryo A'ya gidip `Run once` yap (cron'u beklemeden manuel)
2. Bot'undan Telegram'da önizleme mesajı gelsin
3. Test başarılıysa → Data Store'daki test kaydının `durum`'u `notified` oldu mu kontrol et

### 7.3 Komut test (Senaryo B)

Senaryo B aktif. Telegram'da bot'a şu komutları sırayla yaz, her birinin tepkisini gör:

| Komut | Beklenen davranış |
|---|---|
| `ertele` | "⏰ ERTELENDİ" mesajı, Data Store'da `durum=skipped` |
| (yeni test kaydı oluştur, durum=notified) | |
| `degistir` | Yeni caption gelsin, Data Store'da `caption` güncellenmiş |
| `onayla` | "✅ YAYINLANDI" — gerçekten Instagram'a gider! |

> ⚠️ **`onayla` testinde dikkat:** Gerçek Instagram hesabına post gider. Test için **gizli/sahte bir Instagram hesabı** kullanmak ya da hemen sil. Saturn'un asıl hesabını test edenrı kirletme.

### 7.4 Test verilerini temizle

Test bittikten sonra Data Store'daki test kayıtlarını manuel sil (Data Stores → tüm kayıtlar → checkbox → trash).

---

<a id="adım-8"></a>
## Adım 8 — Production'a Geçiş

### 8.1 İlk içerik üretimi (Haziran 2026 için)

1. Make.com'da senaryolar:
   - **Senaryo A:** OFF
   - **Senaryo B:** ON (her zaman açık kalır)
   - **Senaryo C:** ON (içerik için açık)
2. GitHub'a git → Actions sekmesi → `Generate Monthly Posts` workflow
3. `Run workflow` → inputs:
   - year: `2026`
   - month: `6`
   - month_label: `Haziran 2026`
4. ~5 dakika bekle → 6 post üretilir, webhook ile Make'e düşer
5. Data Store'u kontrol et: 6 kayıt görmelisin (tarihler: 03, 05, 10, 12, 17, 19 Haziran)

### 8.2 Senaryo'ları normal moda al

- Senaryo C: **OFF**
- Senaryo A: **ON**
- Senaryo B: **ON**

### 8.3 İlk yayın

5 Haziran Cuma 18:00'de Telegram'a ilk önizleme düşecek (Senaryo A tetikleyecek). `onayla` yaz → ilk post Instagram'a gider.

---

<a id="aylık-rutin"></a>
## Aylık Operasyon Rutini

Her ayın 25'inde yapılacaklar (yaklaşık 2 dakika):

1. **Ayın 25'i (otomatik):** GitHub Actions cron tetikler → sonraki ayın 6 postu üretilir → webhook'a düşmeye çalışır
2. **Eğer Senaryo C kapalıysa webhook 404 döner.** Bunu önlemek için 25'in sabahı:
   - Senaryo A: **OFF**
   - Senaryo C: **ON**
   - GitHub Actions çalışsın, webhook düşsün
   - Data Store'da 6 yeni kayıt gör
3. **Aynı gün öğleden sonra:**
   - Senaryo C: **OFF**
   - Senaryo A: **ON**
4. Bir sonraki ayın 1'i ile bir sonraki ayın 24'ü arasında normalı: A + B açık, C kapalı

> 💡 **Alternatif: Cron'u 24'üne çek.** GitHub Actions cron'u her ayın 24'üne ayarlarsan, 25 sabahı kontrolü yaparken işi henüz başlatmamış oluyorsun → daha rahat. Bunu workflow YAML'ında ayarlayabilirsin (`cron: '0 6 24 * *'`).

---

## Sorun mu var?

`docs/TROUBLESHOOTING.md` dosyasına bak. En sık karşılaşılanlar:

- **Senaryo A "No records found"** → tarih filter'ı yanlış, formatDate function'ını kontrol et
- **Webhook 404** → C senaryosu kapalı veya URL yanlış
- **Instagram "Invalid media URL"** → repo public mi? raw URL doğru mu?
- **`degistir` çalışmıyor** → HTTP modülde API key yanlış veya quota dolmuş

---

# 🚀 Adım 9 — Gelişmiş Akış (Görsel + Caption Ön Onay)

> **Bu bölüm yukarıdaki temel kuruluma ek özelliklerdir.** Aşağıdaki akışı isteğe bağlı olarak ekleyebilirsin. Eklendiğinde tüm post onay/yayın akışı 2 aşamalı olur: 14:00 ön onay + 18:00 otomatik yayın.

## 9.1 Yeni Akış Genel Bakış

```
14:00 Çar/Cuma → Görsel + Caption tek önizleme + 6 komut + foto upload
                   ✅ "onayla"              → durum=approved
                   🔄 "gorsel degistir"     → AI yeni foto
                   🔄 "metin degistir"      → AI yeni caption
                   ✏️  "metin: [yeni metin]" → kendi caption'ın
                   📸 Telegram'a foto yolla → senin foton + Saturn template
                   ⏰ "ertele" / "elden"    → atla

14:00-17:59      → Kullanıcı istediği kadar düzenler

18:00 Çar/Cuma → durum=approved ise Instagram'a yayınla
                  durum != approved ise "onaylamadın" bildirim
```

## 9.2 Ön Gereksinim — GitHub Personal Access Token (PAT)

Make.com'dan GitHub'a `repository_dispatch` event tetiklemek için Fine-grained PAT gerekli.

### PAT oluştur

1. https://github.com/settings/tokens?type=beta → `Generate new token`
2. Name: `Saturn Film Make.com Dispatcher`
3. Expiration: 1 year (yenileyeceksin)
4. Repository access: `Only select repositories` → `saturn-film-social-media`
5. Repository permissions:
   - **Contents:** Read and write (workflow yeni PNG commit edecek)
   - **Metadata:** Read-only (otomatik)
   - **Actions:** Write (repository_dispatch tetiklemek için)
6. `Generate token` → token'ı kopyala (`github_pat_...` ile başlar)
7. **Make.com'da kullanılacak**, bir yere not al

> ⚠️ **Bu token GitHub'a tam erişim verir!** Make.com'da gizli tut, kimseyle paylaşma.

## 9.3 Data Store Schema Genişletme

Data Store'a 1 yeni durum değeri eklenecek (alan yapısı aynı, sadece `durum` field'ı yeni değerler alır):

| Eski `durum` değerleri | Yeni `durum` değerleri |
|---|---|
| pending, notified, published, skipped | pending, **preview_sent**, **approved**, published, skipped |

Schema değişimi gerekmiyor, sadece kavramsal güncelleme.

## 9.4 Senaryo A'yı Yeniden Tasarla (Genişletilmiş)

**Mevcut Senaryo A'yı sil veya pasifleştir, yenisini bu mantıkla yeniden kur.**

### Schedule trigger
- Run scenario: At regular intervals — **15 minutes**
- Advanced scheduling: TWO time windows:
  - **Wed/Fri 14:00–14:14** (ön onay penceresi)
  - **Wed/Fri 18:00–18:14** (yayın penceresi)

### Data Store search (Modül 2)
Filter: `tarih = formatDate(now; "YYYY-MM-DD"; "Europe/Istanbul")`  
Maximum: 1

### Router (Modül 3) — 3 dal

**Dal 1: Ön onay (14:00 + durum=pending)**
- Filter:
  - `formatDate(now; "HH"; "Europe/Istanbul")` `Equal to` `14`
  - AND `{{2.durum}}` `Equal to` `pending`

Modüller:
1. **Telegram → Send a Photo** (`TELEGRAM_MESSAGES.md` Bölüm 7'deki şablonu kullan)
2. **Data Store → Update a record** → `durum: preview_sent`

**Dal 2: Yayınla (18:00 + durum=approved)**
- Filter:
  - `formatDate(now; "HH"; "Europe/Istanbul")` `Equal to` `18`
  - AND `{{2.durum}}` `Equal to` `approved`

Modüller:
1. **Instagram for Business → Create a Photo Post**
   - Image URL: `{{2.image_url}}`
   - Caption: `{{2.caption}}`
   - Publish: Yes
2. **Telegram → Send a Text Message** → "✅ YAYINLANDI" mesajı (`TELEGRAM_MESSAGES.md` Bölüm 8)
3. **Data Store → Update a record** → `durum: published`

**Dal 3: Onaylanmadı (18:00 + durum != approved)**
- Filter:
  - `formatDate(now; "HH"; "Europe/Istanbul")` `Equal to` `18`
  - AND `{{2.durum}}` `Not equal to` `approved`
  - AND `{{2.durum}}` `Not equal to` `published`
  - AND `{{2.durum}}` `Not equal to` `skipped`

Modüller:
1. **Telegram → Send a Text Message** → "⚠️ ONAYLANMADI, YAYINLANMADI" (`TELEGRAM_MESSAGES.md` Bölüm 9)
2. **Data Store → Update a record** → `durum: skipped`

## 9.5 Senaryo B'yi Yeniden Tasarla (6 Dallı Router)

**Mevcut Senaryo B'yi sil, yenisini bu mantıkla yeniden kur.**

### Trigger
- **Telegram Bot → Watch Updates** (önceki gibi)

### Router — 6 dal

#### Dal 1: Kullanıcı foto gönderdi 📸
**Filter:** `{{length(1.message.photo)}}` `Greater than` `0`

Modüller:
1. **Telegram Bot → Get a File**
   - File ID: `{{1.message.photo[].file_id}}` (en yüksek çözünürlüklü olanı, son eleman)
   - Daha doğrusu: `{{1.message.photo[length(1.message.photo)].file_id}}`
2. **Data Store → Search records** → bugünün postu (önceki gibi)
3. **HTTP → Make a request** (GitHub repository_dispatch)
   - URL: `https://api.github.com/repos/<KULLANICI>/saturn-film-social-media/dispatches`
   - Method: `POST`
   - Headers:
     - `Authorization: Bearer <GITHUB_PAT>` *(Adım 9.2'deki token)*
     - `Accept: application/vnd.github+json`
     - `Content-Type: application/json`
   - Body type: Raw / JSON
   - Request content:
     ```json
     {
       "event_type": "regenerate-photo-user",
       "client_payload": {
         "metadata_path": "posts/{{replace(3.dosya; ".png"; ".json")}}",
         "photo_url": "{{2.file.file_path_url}}"
       }
     }
     ```
4. **Sleep → 90 saniye** *(GitHub Actions'ın render etmesi için bekleme)*
5. **Telegram → Send a Photo** → yeni önizleme (cache busting: image_url'e `?v={{timestamp}}` ekle)
6. **Data Store → Update a record** → `durum: preview_sent` (değişmez ama timestamp güncellenir)

#### Dal 2: `onayla` ✅
**Filter:** `{{lower(1.message.text)}}` `Equal to` `onayla`

Modüller:
1. **Data Store → Search records** → bugünün postu
2. **Data Store → Update a record** → `durum: approved`
3. **Telegram → Send a Text Message** → "✅ POST ONAYLANDI" (`TELEGRAM_MESSAGES.md` Bölüm 10)

#### Dal 3: `gorsel degistir` 🔄
**Filter:** `{{lower(1.message.text)}}` `Equal to` `gorsel degistir`

Modüller:
1. **Data Store → Search records** → bugünün postu
2. **HTTP → Make a request** (GitHub repository_dispatch)
   - URL: `https://api.github.com/repos/<KULLANICI>/saturn-film-social-media/dispatches`
   - Method: POST
   - Headers: (Dal 1 ile aynı)
   - Body:
     ```json
     {
       "event_type": "regenerate-photo-ai",
       "client_payload": {
         "metadata_path": "posts/{{replace(1.dosya; ".png"; ".json")}}"
       }
     }
     ```
3. **Sleep → 90 saniye**
4. **Telegram → Send a Photo** → yeni önizleme (image_url + `?v={{timestamp}}`)

#### Dal 4: `metin degistir` 🔄
**Filter:** `{{lower(1.message.text)}}` `Equal to` `metin degistir`

Modüller:
1. **Data Store → Search records** → bugünün postu
2. **HTTP → Make a request** (GitHub repository_dispatch)
   - Body:
     ```json
     {
       "event_type": "regenerate-caption",
       "client_payload": {
         "metadata_path": "posts/{{replace(1.dosya; ".png"; ".json")}}"
       }
     }
     ```
3. **Sleep → 30 saniye** *(caption üretimi foto'dan hızlı)*
4. **HTTP → Make a request** (yeni JSON'u GitHub raw'dan oku)
   - URL: `https://raw.githubusercontent.com/<KULLANICI>/saturn-film-social-media/main/posts/{{replace(1.dosya; ".png"; ".json")}}`
   - Method: GET
   - Parse response: Yes
5. **Data Store → Update a record** → `caption: {{4.caption}}` *(JSON'dan gelen yeni caption)*
6. **Telegram → Send a Text Message** → "🔄 YENİ CAPTION ÜRETİLDİ" (`TELEGRAM_MESSAGES.md` Bölüm 11)

#### Dal 5: `metin: [yeni metin]` ✏️
**Filter:** `{{lower(substring(1.message.text; 0; 6))}}` `Equal to` `metin:`

Modüller:
1. **Data Store → Search records** → bugünün postu
2. **Data Store → Update a record** → `caption: {{trim(substring(1.message.text; 6; length(1.message.text)))}}`
3. **Telegram → Send a Text Message** → "✏️ CAPTION GÜNCELLENDİ" (`TELEGRAM_MESSAGES.md` Bölüm 12)

#### Dal 6: `ertele` / `elden` ⏰
**Filter:**
- `{{lower(1.message.text)}}` `Equal to` `ertele`
- OR `{{lower(1.message.text)}}` `Equal to` `elden`

Modüller:
1. **Data Store → Search records** → bugünün postu
2. **Data Store → Update a record** → `durum: skipped`
3. **Telegram → Send a Text Message** → "⏰ ATLANDI" (`TELEGRAM_MESSAGES.md` Bölüm 13)

## 9.6 Test Akışı

1. Manuel olarak Senaryo C'yi tetikleyip Data Store'a bir test postu yaz (`durum: pending`, tarih = bugün)
2. Senaryo A'yı `Run once` yap (14:00 saatinden bağımsız, ama filter'ı geçici olarak kapat)
3. Telegram'da önizleme gelmeli
4. Şu komutları sırayla dene:
   - `gorsel degistir` → 90 saniye bekle, yeni görsel gelmeli
   - `metin degistir` → 30 saniye bekle, yeni caption gelmeli
   - `metin: 🎬 Bu test caption'ıdır` → caption hemen güncellenmeli
   - Telegram'a foto gönder → 90 saniye bekle, sen verdiğin fotoyla Saturn template uygulanmış görsel gelmeli
   - `onayla` → "onaylandı" mesajı, durum=approved
5. Senaryo A'yı saat 18 simulasyonu için manuel `Run once`
6. Instagram'a post atılmalı, "yayınlandı" mesajı gelmeli

## 9.7 Geçiş

Yeni akışa geçtiğinde:
- Eski Senaryo A: SİL
- Eski Senaryo B: SİL
- Yeni Senaryo A (Adım 9.4): aktif
- Yeni Senaryo B (Adım 9.5): aktif
- Senaryo C: pasif (yalnız 25'inde aktif)

> 💡 **Free plan: 2 aktif sınırı hâlâ geçerli.** Yeni Senaryo A + Yeni Senaryo B = 2 aktif. C için Adım 6'daki rutini izle.

---

**Tüm adımları bitirdin mi?** ✅ Tebrikler — Saturn Film otomasyonu gelişmiş akışla çalışıyor.
