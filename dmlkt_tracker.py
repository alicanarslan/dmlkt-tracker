#!/usr/bin/env python3
"""
DMLKT Gayrimenkul Sertifikası - Fiyat Takip & Telegram Bildirim Otomasyonu

TradingView Scanner API üzerinden DMLKT fiyatını periyodik olarak kontrol eder.
Her fiyat değişiminde Telegram bildirimi, gün sonunda özet rapor gönderir.
GitHub Actions üzerinde çalışmak üzere tasarlanmıştır.
"""

import requests
import json
import os
import sys
from datetime import datetime, timezone, timedelta

# ─── Yapılandırma ──────────────────────────────────────
TELEGRAM_BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN", "")
TELEGRAM_CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID", "")
STATE_FILE = os.environ.get("STATE_FILE", "state.json")
TURKEY_TZ = timezone(timedelta(hours=3))

# TradingView Scanner API
TV_SCAN_URL = "https://scanner.tradingview.com/turkey/scan"
TV_PAYLOAD = {
    "symbols": {"tickers": ["BIST:DMLKT"]},
    "columns": [
        "close",        # 0 - Son fiyat
        "change",       # 1 - Değişim %
        "change_abs",   # 2 - Değişim TL
        "high",         # 3 - Gün en yüksek
        "low",          # 4 - Gün en düşük
        "open",         # 5 - Açılış
        "volume",       # 6 - Hacim (lot)
        "name",         # 7 - Kod
        "description",  # 8 - Açıklama
    ],
}

# Borsa saatleri (Türkiye saati)
MARKET_OPEN_HOUR, MARKET_OPEN_MIN = 9, 30
MARKET_CLOSE_HOUR, MARKET_CLOSE_MIN = 18, 10


# ─── Yardımcı Fonksiyonlar ─────────────────────────────
def now_turkey():
    """Türkiye saatini döndürür"""
    return datetime.now(TURKEY_TZ)


def is_market_hours(dt=None):
    """Borsa saatlerinde mi kontrolü"""
    dt = dt or now_turkey()
    t = dt.hour * 60 + dt.minute
    market_open = MARKET_OPEN_HOUR * 60 + MARKET_OPEN_MIN
    market_close = MARKET_CLOSE_HOUR * 60 + MARKET_CLOSE_MIN
    return market_open <= t <= market_close


def format_number(n):
    """Sayıyı Türkçe formatta gösterir"""
    if n is None:
        return "N/A"
    return f"{n:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")


# ─── TradingView API ───────────────────────────────────
def get_dmlkt_price():
    """TradingView Scanner API'dan DMLKT fiyat bilgisi çeker"""
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Origin": "https://www.tradingview.com",
        "Referer": "https://www.tradingview.com/",
    }
    try:
        r = requests.post(TV_SCAN_URL, json=TV_PAYLOAD, headers=headers, timeout=15)
        r.raise_for_status()
        data = r.json()
        if data.get("totalCount", 0) > 0:
            d = data["data"][0]["d"]
            return {
                "price": d[0],
                "change_pct": d[1],
                "change_abs": d[2],
                "high": d[3],
                "low": d[4],
                "open": d[5],
                "volume": int(d[6]) if d[6] else 0,
                "name": d[7],
                "description": d[8],
            }
        print("⚠️ TradingView'den veri gelmedi (totalCount=0)")
    except requests.exceptions.RequestException as e:
        print(f"❌ TradingView API hatası: {e}")
    except (KeyError, IndexError, json.JSONDecodeError) as e:
        print(f"❌ Veri ayrıştırma hatası: {e}")
    return None


# ─── Telegram ──────────────────────────────────────────
def send_telegram(text):
    """Telegram Bot API ile mesaj gönderir"""
    if not TELEGRAM_BOT_TOKEN or not TELEGRAM_CHAT_ID:
        print("⚠️ TELEGRAM_BOT_TOKEN veya TELEGRAM_CHAT_ID tanımlı değil!")
        return False
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    payload = {
        "chat_id": TELEGRAM_CHAT_ID,
        "text": text,
        "parse_mode": "HTML",
        "disable_web_page_preview": True,
    }
    try:
        r = requests.post(url, json=payload, timeout=10)
        result = r.json()
        if result.get("ok"):
            print("📨 Telegram mesajı gönderildi")
            return True
        else:
            print(f"⚠️ Telegram yanıtı: {result}")
            return False
    except Exception as e:
        print(f"❌ Telegram gönderim hatası: {e}")
        return False


# ─── State Yönetimi ────────────────────────────────────
def load_state():
    """State dosyasını yükler"""
    if os.path.exists(STATE_FILE):
        try:
            with open(STATE_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except (json.JSONDecodeError, IOError) as e:
            print(f"⚠️ State dosyası okunamadı, sıfırlanıyor: {e}")
    return {"last_price": None, "last_check": None, "daily": None}


def save_state(state):
    """State dosyasını kaydeder"""
    with open(STATE_FILE, "w", encoding="utf-8") as f:
        json.dump(state, f, ensure_ascii=False, indent=2)


# ─── Ana İşlevler ──────────────────────────────────────
def check_price():
    """Fiyat kontrol et, değişiklik varsa bildir"""
    state = load_state()
    data = get_dmlkt_price()

    if not data:
        print("❌ Fiyat alınamadı, atlanıyor")
        return

    current_price = data["price"]
    now = now_turkey()
    today = now.strftime("%Y-%m-%d")
    time_str = now.strftime("%H:%M")

    # ── Yeni gün kontrolü & daily reset ──
    if not state.get("daily") or state["daily"].get("date") != today:
        state["daily"] = {
            "date": today,
            "open_price": current_price,
            "high_price": current_price,
            "low_price": current_price,
            "first_price": current_price,
            "changes": [],
            "check_count": 0,
            "summary_sent": False,
        }
        msg = (
            f"🟢 <b>DMLKT Takip Başladı</b>\n\n"
            f"📅 {now.strftime('%d.%m.%Y')} | ⏰ {time_str}\n"
            f"💰 Fiyat: <b>{current_price:.2f} TL</b>\n"
            f"📊 Önceki Gün Değişim: %{data['change_pct']:.2f}\n"
            f"📦 Hacim: {data['volume']:,} lot"
        )
        send_telegram(msg)
        print(f"🟢 Yeni gün başladı: {today} | Fiyat: {current_price:.2f}")

    # ── Daily istatistik güncelle ──
    daily = state["daily"]
    daily["check_count"] = daily.get("check_count", 0) + 1
    if current_price > daily["high_price"]:
        daily["high_price"] = current_price
    if current_price < daily["low_price"]:
        daily["low_price"] = current_price
    daily["close_price"] = current_price

    # ── Fiyat değişimi kontrolü ──
    last_price = state.get("last_price")
    if last_price is not None and current_price != last_price:
        diff = round(current_price - last_price, 4)
        pct = (diff / last_price) * 100

        if diff > 0:
            emoji, direction, arrow = "📈", "YÜKSELDİ", "▲"
        else:
            emoji, direction, arrow = "📉", "DÜŞTÜ", "▼"

        # Gün başından itibaren toplam değişim
        day_open = daily.get("first_price", current_price)
        day_diff = round(current_price - day_open, 4)
        day_pct = (day_diff / day_open * 100) if day_open else 0

        msg = (
            f"{emoji} <b>DMLKT {direction}</b>\n\n"
            f"💰 {last_price:.2f} ➜ <b>{current_price:.2f} TL</b>\n"
            f"{arrow} Fark: <b>{diff:+.2f} TL</b> ({pct:+.2f}%)\n"
            f"⏰ {time_str}\n\n"
            f"📊 <i>Günlük:</i>\n"
            f"   Açılış: {day_open:.2f} | Şu an: {current_price:.2f} ({day_diff:+.2f})\n"
            f"   En Yüksek: {daily['high_price']:.2f} | En Düşük: {daily['low_price']:.2f}"
        )
        send_telegram(msg)

        daily["changes"].append(
            {
                "time": time_str,
                "from": last_price,
                "to": current_price,
                "diff": round(diff, 2),
                "pct": round(pct, 2),
            }
        )
        print(f"{arrow} {time_str} | {last_price:.2f} → {current_price:.2f} ({diff:+.2f})")
    elif last_price is not None:
        print(f"➡️ {time_str} | Fiyat değişmedi: {current_price:.2f} TL")
    else:
        print(f"🆕 {time_str} | İlk fiyat kaydedildi: {current_price:.2f} TL")

    # ── State güncelle ──
    state["last_price"] = current_price
    state["last_check"] = now.isoformat()

    # ── Otomatik gün sonu özet kontrolü ──
    if not daily.get("summary_sent", False) and not is_market_hours(now):
        # Borsa kapandıktan sonra & bugün henüz özet gönderilmemişse
        now_minutes = now.hour * 60 + now.minute
        close_minutes = MARKET_CLOSE_HOUR * 60 + MARKET_CLOSE_MIN
        if now_minutes > close_minutes:
            _send_summary_internal(state)
            daily["summary_sent"] = True

    save_state(state)


def _send_summary_internal(state):
    """Internal: Günlük özet mesajı oluştur ve gönder"""
    daily = state.get("daily")
    if not daily:
        return

    now = now_turkey()
    open_p = daily.get("first_price", daily.get("open_price", 0))
    close_p = daily.get("close_price", open_p)
    high_p = daily["high_price"]
    low_p = daily["low_price"]
    changes = daily.get("changes", [])

    total_diff = round(close_p - open_p, 4)
    total_pct = (total_diff / open_p * 100) if open_p else 0
    spread = round(high_p - low_p, 4)

    ups = sum(1 for c in changes if c["diff"] > 0)
    downs = sum(1 for c in changes if c["diff"] < 0)

    if total_diff > 0:
        emoji, trend = "📈", "YÜKSELİŞ"
    elif total_diff < 0:
        emoji, trend = "📉", "DÜŞÜŞ"
    else:
        emoji, trend = "➡️", "YATAY"

    msg = (
        f"📋 <b>DMLKT GÜN SONU RAPORU</b>\n"
        f"📅 {daily['date']}\n\n"
        f"{'━' * 26}\n"
        f"💰 Açılış:      <b>{open_p:.2f} TL</b>\n"
        f"💰 Kapanış:     <b>{close_p:.2f} TL</b>\n"
        f"📈 En Yüksek:   <b>{high_p:.2f} TL</b>\n"
        f"📉 En Düşük:    <b>{low_p:.2f} TL</b>\n"
        f"📐 Spread:      <b>{spread:.2f} TL</b>\n"
        f"{'━' * 26}\n"
        f"{emoji} Günlük Değişim: <b>{total_diff:+.2f} TL ({total_pct:+.2f}%)</b> → {trend}\n\n"
        f"📈 Yükseliş: <b>{ups}</b> kez\n"
        f"📉 Düşüş: <b>{downs}</b> kez\n"
        f"🔄 Toplam Kontrol: <b>{daily.get('check_count', 0)}</b>\n"
        f"🔀 Toplam Hareket: <b>{len(changes)}</b>\n"
    )

    # Son hareketler listesi
    if changes:
        msg += f"\n{'━' * 26}\n📋 <b>Tüm Hareketler:</b>\n\n"
        display_changes = changes[-20:]  # Son 20 hareket
        for c in display_changes:
            arrow = "▲" if c["diff"] > 0 else "▼"
            msg += f"  ⏰ {c['time']}  {c['from']:.2f} ➜ {c['to']:.2f}  ({c['diff']:+.2f}) {arrow}\n"
        if len(changes) > 20:
            msg += f"\n  <i>... ve {len(changes) - 20} hareket daha</i>\n"

    msg += f"\n🕐 Rapor saati: {now.strftime('%H:%M')}"

    send_telegram(msg)
    print("📋 Günlük özet gönderildi")


def send_summary():
    """Manuel gün sonu özet gönderimi"""
    state = load_state()
    if not state.get("daily"):
        print("ℹ️ Henüz günlük veri yok")
        # Mevcut fiyatı çekip minimal özet gönder
        data = get_dmlkt_price()
        if data:
            msg = (
                f"📋 <b>DMLKT Anlık Durum</b>\n\n"
                f"💰 Fiyat: <b>{data['price']:.2f} TL</b>\n"
                f"📊 Değişim: %{data['change_pct']:.2f}\n"
                f"📈 Yüksek: {data['high']:.2f} | 📉 Düşük: {data['low']:.2f}\n"
                f"📦 Hacim: {data['volume']:,} lot\n"
                f"⏰ {now_turkey().strftime('%H:%M %d.%m.%Y')}"
            )
            send_telegram(msg)
        return

    _send_summary_internal(state)


def test_bot():
    """Bot bağlantı ve fiyat çekme testi"""
    print("🧪 Test başlıyor...\n")

    # 1) TradingView testi
    print("1️⃣ TradingView API testi...")
    data = get_dmlkt_price()
    if data:
        print(f"   ✅ Fiyat: {data['price']:.2f} TL | Değişim: %{data['change_pct']:.2f}")
    else:
        print("   ❌ Fiyat çekilemedi!")
        return

    # 2) Telegram testi
    print("2️⃣ Telegram bot testi...")
    msg = (
        f"🧪 <b>DMLKT Tracker - Test Mesajı</b>\n\n"
        f"✅ Bot bağlantısı başarılı!\n\n"
        f"💰 Anlık Fiyat: <b>{data['price']:.2f} TL</b>\n"
        f"📊 Değişim: %{data['change_pct']:.2f}\n"
        f"📈 Yüksek: {data['high']:.2f} | 📉 Düşük: {data['low']:.2f}\n"
        f"🔓 Açılış: {data['open']:.2f} TL\n"
        f"📦 Hacim: {data['volume']:,} lot\n\n"
        f"⏰ {now_turkey().strftime('%H:%M %d.%m.%Y')}\n"
        f"🤖 GitHub Actions otomasyonu hazır!"
    )
    result = send_telegram(msg)
    if result:
        print("   ✅ Telegram mesajı gönderildi!")
    else:
        print("   ❌ Telegram mesajı gönderilemedi!")

    print("\n✅ Tüm testler tamamlandı")


# ─── Ana Giriş Noktası ─────────────────────────────────
def main():
    if len(sys.argv) < 2:
        mode = "check"
    else:
        mode = sys.argv[1].lower()

    print(f"🔧 Mod: {mode} | Saat: {now_turkey().strftime('%H:%M:%S %d.%m.%Y')}")
    print(f"{'─' * 40}")

    if mode == "check":
        check_price()
    elif mode == "summary":
        send_summary()
    elif mode == "test":
        test_bot()
    else:
        print(f"❌ Bilinmeyen mod: {mode}")
        print("Kullanım: python dmlkt_tracker.py [check|summary|test]")
        sys.exit(1)


if __name__ == "__main__":
    main()
