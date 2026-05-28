# Telegram Mesaj Şablonları

Make.com'da Telegram modüllerinin `Text` veya `Caption` alanlarına aynen kopyala-yapıştır. Tüm şablonlar **Markdown** parse mode için yazıldı.

> 💡 **Değiştirmek istersen:** Bu dosyada düzenle, sonra Make'te ilgili modülün caption field'ını güncelle.

---

## 1. Senaryo A — Günlük Post Önizlemesi

**Modül:** `Telegram Bot → Send a Photo`  
**Parse mode:** `Markdown`  
**Photo:** `{{2.image_url}}`  
**Caption:**

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

---

## 2. Senaryo B / Dal 1 — Yeni Caption Üretildi (`degistir` sonrası)

**Modül:** `Telegram Bot → Send a Photo` (Dal 1, Modül 1.4)  
**Parse mode:** `Markdown`  
**Photo:** `{{1.1.image_url}}`  
**Caption:**

```
🔄 *YENİ CAPTION ÜRETİLDİ*

📅 {{1.1.tarih}} · {{1.1.gun}}
🎯 {{1.1.hizmet}}

*{{1.1.baslik}}*
_{{1.1.aciklama}}_

━━━━━━━━━━━━━━━━━━
📝 YENİ CAPTION:

{{1.2.data.choices[].message.content}}
━━━━━━━━━━━━━━━━━━

✅ Onayla → `onayla`
🔄 Tekrar değiştir → `degistir`
✏️ Kendi caption'ın → `onayla [yeni metin]`
```

---

## 3. Senaryo B / Dal 2 — Custom Caption ile Yayınlandı (`onayla [metin]`)

**Modül:** `Telegram Bot → Send a Text Message` (Dal 2, Modül 2.3)  
**Parse mode:** `Markdown`  
**Text:**

```
✅ *YAYINLANDI*

📅 {{2.1.tarih}} · {{2.1.gun}}
🎯 {{2.1.hizmet}} · Layout {{2.1.layout}}

Instagram'a *custom caption* ile gönderildi.

🌐 saturnfilm.net
```

---

## 4. Senaryo B / Dal 3 — Mevcut Caption ile Yayınlandı (`onayla`)

**Modül:** `Telegram Bot → Send a Text Message` (Dal 3, Modül 3.3)  
**Parse mode:** `Markdown`  
**Text:**

```
✅ *YAYINLANDI*

📅 {{3.1.tarih}} · {{3.1.gun}}
🎯 {{3.1.hizmet}} · Layout {{3.1.layout}}

Mevcut caption ile Instagram'a gönderildi.

🌐 saturnfilm.net
```

---

## 5. Senaryo B / Dal 4 — Ertelendi (`ertele`)

**Modül:** `Telegram Bot → Send a Text Message` (Dal 4, Modül 4.3)  
**Parse mode:** `Markdown`  
**Text:**

```
⏰ *ERTELENDİ*

📅 {{4.1.tarih}} · {{4.1.gun}}
🎯 {{4.1.hizmet}} · Layout {{4.1.layout}}

Bu post atlandı, Instagram'a gönderilmeyecek.
```

---

## 6. (Opsiyonel) Senaryo B — Hata Mesajı

Eğer kullanıcı tanınmayan bir komut yazarsa hatırlatma mesajı. Bu, Router'ın **default** dalı olarak eklenir (filter yok).

**Modül:** `Telegram Bot → Send a Text Message`  
**Text:**

```
❓ *KOMUT ANLAŞILMADI*

Geçerli komutlar:
✅ `onayla` — mevcut caption ile yayınla
✏️ `onayla [yeni metin]` — kendi caption'ınla
🔄 `degistir` — AI'dan yeni caption iste
⏰ `ertele` — bu postu atla
```

---

## Markdown Notları (Make'te dikkat)

Telegram Markdown'da bazı karakterler **özel anlama** sahip: `_*[]()~\`>#+-=|{}.!`

- `*kalın*` → **kalın**
- `_italik_` → *italik*
- `` `kod` `` → `kod`

Eğer caption içeriği kullanıcı tarafından üretiliyorsa (örn. GPT'den gelen serbest metin), bu karakterler escape edilmesi gerekir. Şu an Saturn caption'larında özel karakter kullanmıyoruz, sorun yok. Eğer ileride sorun çıkarsa, Make modülünde:

```
{{replace(replace(replace(2.caption; "_"; "\\_"); "*"; "\\*"); "`"; "\\`")}}
```

şeklinde escape edilebilir.

---

## Önizleme Görseli

Telegram'da mesaj şöyle görünecek (örnek):

```
[Foto: 1080x1080 PNG]

🎬 SATURN — BUGÜNKÜ POST

📅 2026-06-05 · Cuma
🎯 Film Yapım · Layout M

HİKÂYENİZİ YENİ BİR YÖRÜNGEYE
— uzun metraj, kısa film, belgesel

━━━━━━━━━━━━━━━━━━
📝 INSTAGRAM CAPTION:

🎬 Her hikâye bir yörünge çizer...
[devamı tam caption]
━━━━━━━━━━━━━━━━━━

✅ Onayla → onayla
🔄 Yeni caption iste → degistir
✏️ Kendi caption'ın → onayla [yeni metin]
⏰ Ertele → ertele
```

---

# 🚀 Gelişmiş Akış Şablonları (Adım 9 için)

Bu bölüm, MAKE_SETUP.md Adım 9'daki gelişmiş akışta kullanılır.

## 7. Görsel + Caption Ön Önizleme (14:00) — Senaryo A Dal 1

**Modül:** `Telegram Bot → Send a Photo`  
**Parse mode:** `Markdown`  
**Photo:** `{{2.image_url}}`  
**Caption:**

```
🎬 *SATURN — 4 SAAT KALA ÖN ONAY*

📅 {{2.tarih}} · {{2.gun}} 18:00
🎯 {{2.hizmet}} · Layout {{2.layout}}

*{{2.baslik}}*
_{{2.aciklama}}_

━━━━━━━━━━━━━━━━━━
📝 CAPTION:

{{2.caption}}
━━━━━━━━━━━━━━━━━━

🟢 *KOMUTLAR:*

✅ `onayla` → 18:00'de yayınla
🔄 `gorsel degistir` → AI yeni foto üret
🔄 `metin degistir` → AI yeni caption yaz
✏️ `metin: [yeni metin]` → kendi caption'ın
📸 *Foto gönder* → senin foton kullanılır
⏰ `ertele` → bu postu atla

_4 saat içinde onaylamazsan post yayınlanmaz._
```

## 8. Yayınlandı (18:00) — Senaryo A Dal 2

**Modül:** `Telegram Bot → Send a Text Message`  
**Parse mode:** `Markdown`  
**Text:**

```
✅ *YAYINLANDI*

📅 {{2.tarih}} · {{2.gun}}
🎯 {{2.hizmet}} · Layout {{2.layout}}

*{{2.baslik}}*

Instagram'a başarıyla gönderildi.

🌐 saturnfilm.net
```

## 9. Onaylanmadı (18:00) — Senaryo A Dal 3

**Modül:** `Telegram Bot → Send a Text Message`  
**Parse mode:** `Markdown`  
**Text:**

```
⚠️ *POST YAYINLANMADI*

📅 {{2.tarih}} · {{2.gun}}
🎯 {{2.hizmet}}

14:00'te gönderilen ön onayı geçen 4 saat içinde onaylamadın.

Bu post atlandı. Bir sonraki yayın günü yeni post gelecek.
```

## 10. Onaylandı Bildirim — Senaryo B Dal 2

**Modül:** `Telegram Bot → Send a Text Message`  
**Parse mode:** `Markdown`  
**Text:**

```
✅ *POST ONAYLANDI*

📅 {{1.tarih}} · {{1.gun}}
🎯 {{1.hizmet}}

Bu post 18:00'de otomatik olarak Instagram'a yayınlanacak.

_Hâlâ değişiklik yapmak istersen 18:00'e kadar düzenleme komutlarını kullanabilirsin:_
🔄 `gorsel degistir` · `metin degistir`
✏️ `metin: [yeni metin]`
⏰ `ertele` (artık iptal et)
```

## 11. Yeni Caption Üretildi — Senaryo B Dal 4

**Modül:** `Telegram Bot → Send a Text Message`  
**Parse mode:** `Markdown`  
**Text:**

```
🔄 *YENİ CAPTION ÜRETİLDİ*

📅 {{1.tarih}} · {{1.gun}}
🎯 {{1.hizmet}}

━━━━━━━━━━━━━━━━━━
{{4.caption}}
━━━━━━━━━━━━━━━━━━

✅ `onayla` → bu caption ile devam et
🔄 `metin degistir` → tekrar dene
✏️ `metin: [yeni metin]` → kendi caption'ın
```

## 12. Caption Manuel Güncellendi — Senaryo B Dal 5

**Modül:** `Telegram Bot → Send a Text Message`  
**Parse mode:** `Markdown`  
**Text:**

```
✏️ *CAPTION GÜNCELLENDİ*

📅 {{1.tarih}} · {{1.gun}}

Yeni caption Data Store'a kaydedildi.

✅ `onayla` → bu caption ile yayınla
🔄 `metin degistir` → AI'dan yeniden iste
```

## 13. Ertelendi — Senaryo B Dal 6

**Modül:** `Telegram Bot → Send a Text Message`  
**Parse mode:** `Markdown`  
**Text:**

```
⏰ *POST ATLANDI*

📅 {{1.tarih}} · {{1.gun}}
🎯 {{1.hizmet}} · Layout {{1.layout}}

Bu post Instagram'a yayınlanmayacak.
```

## 14. Görsel Yenilendi — Senaryo B Dal 3 (foto önizlemesi)

**Modül:** `Telegram Bot → Send a Photo`  
**Parse mode:** `Markdown`  
**Photo:** `{{1.image_url}}?v={{timestamp}}` *(cache busting için)*  
**Caption:**

```
🔄 *YENİ GÖRSEL HAZIR*

📅 {{1.tarih}} · {{1.gun}}
🎯 {{1.hizmet}} · Layout {{1.layout}}

━━━━━━━━━━━━━━━━━━
📝 MEVCUT CAPTION:

{{1.caption}}
━━━━━━━━━━━━━━━━━━

✅ `onayla` → bu görselle yayınla
🔄 `gorsel degistir` → tekrar dene
📸 *Foto gönder* → senin fotonu kullan
```

## 15. Kullanıcı Fotosu İşlendi — Senaryo B Dal 1 (foto önizlemesi)

**Modül:** `Telegram Bot → Send a Photo`  
**Parse mode:** `Markdown`  
**Photo:** `{{1.image_url}}?v={{timestamp}}`  
**Caption:**

```
📸 *FOTONUZ KULLANILDI*

Fotonuza Saturn template uygulandı.

📅 {{1.tarih}} · {{1.gun}}
🎯 {{1.hizmet}} · Layout {{1.layout}}

━━━━━━━━━━━━━━━━━━
📝 MEVCUT CAPTION:

{{1.caption}}
━━━━━━━━━━━━━━━━━━

✅ `onayla` → bu görselle yayınla
📸 *Başka foto gönder* → yine değiştir
🔄 `gorsel degistir` → AI fotoyla geri dön
```

---

## ⚠️ Cache Busting Notu

`gorsel degistir`, foto upload veya benzeri durumlarda PNG dosyası **aynı isimle** GitHub'a commit edilir. Telegram ve Instagram CDN'leri eski versiyonu cache'leyebilir. Bunu engellemek için image URL'lerine `?v={{timestamp}}` query string'i eklenir:

```
{{1.image_url}}?v={{formatDate(now; "X"; "Europe/Istanbul")}}
```

`formatDate(now; "X")` Unix timestamp döner; her seferinde farklı, cache miss oluşturur.
