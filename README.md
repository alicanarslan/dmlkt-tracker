# DMLKT Fiyat Takip Otomasyonu 📊

DMLKT (Damla Kent Gayrimenkul Sertifikası) fiyatını **TradingView API** üzerinden takip edip, her değişimde **Telegram** bildirimi gönderen GitHub Actions otomasyonu.

## 🚀 Özellikler

- ✅ **Her fiyat değişiminde** anlık Telegram bildirimi
- 📋 **Gün sonu otomatik özet raporu** (açılış/kapanış/en yüksek/en düşük)
- ⏰ **5 dakikalık periyotlarla** otomatik kontrol (borsa saatleri: 09:30-18:10)
- 🆓 **Ücretsiz** - TradingView Scanner API (API key gerektirmez)
- 🔄 **GitHub Actions** üzerinde tam otomatik çalışma
- 💾 Çalışmalar arası durum koruması (cache ile)

## 📦 Kurulum

### 1. GitHub Repository Oluştur

Bu klasörü bir GitHub reposuna push edin:

```bash
cd "stok takip"
git init
git add .
git commit -m "DMLKT tracker ilk kurulum"
git branch -M main
git remote add origin https://github.com/KULLANICI_ADINIZ/dmlkt-tracker.git
git push -u origin main
```

### 2. GitHub Secrets Ekle

Repository **Settings** → **Secrets and variables** → **Actions** → **New repository secret**:

| Secret Adı | Değer |
|---|---|
| `TELEGRAM_BOT_TOKEN` | Telegram bot token'ınız |
| `TELEGRAM_CHAT_ID` | Telegram chat ID'niz |

### 3. GitHub Actions'ı Etkinleştir

Repository'nin **Actions** sekmesine gidin ve workflow'u etkinleştirin.

## 🧪 Manuel Test

Actions sekmesinden **DMLKT Fiyat Takip** → **Run workflow** → Mode: **test** seçin.

## 📱 Bildirim Örnekleri

### Fiyat Değişimi
```
📈 DMLKT YÜKSELDİ

💰 6.27 ➜ 6.28 TL
▲ Fark: +0.01 TL (+0.16%)
⏰ 14:35

📊 Günlük:
   Açılış: 6.25 | Şu an: 6.28 (+0.03)
   En Yüksek: 6.30 | En Düşük: 6.24
```

### Gün Sonu Raporu
```
📋 DMLKT GÜN SONU RAPORU
📅 2026-04-15

━━━━━━━━━━━━━━━━━━━━━━━━━━
💰 Açılış:      6.25 TL
💰 Kapanış:     6.28 TL
📈 En Yüksek:   6.30 TL
📉 En Düşük:    6.24 TL
━━━━━━━━━━━━━━━━━━━━━━━━━━
📈 Günlük: +0.03 TL (+0.48%) → YÜKSELİŞ

📈 Yükseliş: 5 kez
📉 Düşüş: 3 kez
🔄 Toplam Kontrol: 108
🔀 Toplam Hareket: 8
```

## ⚙️ Modlar

| Mod | Açıklama |
|---|---|
| `check` | Fiyat kontrol et, değişiklik varsa bildir |
| `summary` | Günlük özet raporu gönder |
| `test` | Bot bağlantı ve API testi |

## 📝 Notlar

- TradingView verileri **~15 dakika gecikmeli**dir
- GitHub Actions ücretsiz hesaplarda aylık **2000 dakika** limiti vardır
- Bu otomasyon yaklaşık **~1200 dk/ay** kullanır (limitin altında)
- Sadece **hafta içi** borsa saatlerinde çalışır
