# Mail Bot 🚀

Mail Bot, Google Maps verilerini kullanarak şirketleri bulan, web sitelerini analiz eden ve yapay zeka (Gemini/OpenAI) desteği ile kişiselleştirilmiş iş başvurusu mailleri hazırlayan profesyonel bir otomasyon aracıdır.

![Mail Bot UI](https://via.placeholder.com/800x450.png?text=Mail+Bot+Arayuz+Onizleme) <!-- Buraya ekran görüntüsü ekleyebilirsiniz -->

## ✨ Özellikler

- **Akıllı Tarama:** Belirlenen sektör ve şehirdeki potansiyel işverenleri otomatik olarak listeler.
- **Yapay Zeka Analizi:** Şirket web sitelerini okur, vizyonlarını anlar ve size özel ikna edici taslaklar hazırlar.
- **Skorlama Sistemi:** Şirketleri "uygunluk skoruna" göre sıralayarak en doğru hedeflere odaklanmanızı sağlar.
- **Toplu İşlemler:** Yüzlerce taslağı tek tıkla onaylayabilir veya atlayabilirsiniz.
- **Kişiselleştirilmiş Mailler:** "Sayın Yetkili" yerine, şirketin projelerine atıfta bulunan profesyonel içerikler üretir.
- **Güvenli Depolama:** API anahtarlarınızı ve şifrelerinizi işletim sisteminizin güvenli kasasında (Keychain/Credential Manager) saklar.

## 🚀 Hızlı Kurulum (Terminal)

Mail Bot'u terminal üzerinden hızlıca kurup çalıştırmak için aşağıdaki komutları kullanabilirsiniz:

### macOS / Linux
```bash
# Depoyu klonlayın
git clone https://github.com/emrek0ca/mail-bot.git
cd mail-bot

# Bağımlılıkları yükleyin
pip install -r requirements.txt

# Tarayıcıyı kurun
playwright install chromium

# Uygulamayı çalıştırın
python main.py
```

### Windows (PowerShell)
```powershell
git clone https://github.com/emrek0ca/mail-bot.git
cd mail-bot
pip install -r requirements.txt
playwright install chromium
python main.py
```

## 🛠️ Derleme (Build)
Kendi `.exe` veya `.app` dosyanızı oluşturmak isterseniz:
```bash
python scripts/build.py
```

## 📋 Gereksinimler
- Python 3.11 veya üzeri
- Google Gemini veya OpenAI API anahtarı
- Gmail Uygulama Şifresi (Standard şifre desteklenmez)

## 🛡️ Lisans ve Yasal Uyarı
Copyright (c) 2026 **Osman Emre Koca**. Tüm Hakları Saklıdır.
Bu projenin kaynak kodu Osman Emre Koca'nın yazılı izni olmaksızın kopyalanamaz, dağıtılamaz veya ticari amaçla kullanılamaz. Detaylar için [LICENSE](LICENSE) dosyasına bakınız.

---
Developed by **Osman Emre Koca**
