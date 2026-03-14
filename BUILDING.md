# Mail Bot - Derleme ve Kurulum Kılavuzu

Mail Bot artık Windows, macOS ve Linux sistemlerini tam olarak desteklemektedir.

## 🛠️ Derleme (Build) Adımları

Tüm platformlarda tek bir komutla derleme yapabilirsiniz:

1.  Gerekli Python sürümünün (3.11+) kurulu olduğundan emin olun.
2.  Bağımlılıkları yükleyin: `pip install -r requirements.txt`
3.  Derleme aracını çalıştırın:
    ```bash
    python scripts/build.py
    ```

### Çıktılar (dist/ klasörü)
- **Windows:** `Mail Bot.exe` (klasör içinde)
- **macOS:** `Mail Bot.app` ve `MailBot-macOS.zip`
- **Linux:** `Mail Bot` binary dosyası

## 📂 Veri ve Ayar Konumları

Uygulama, ayarları ve veritabanını işletim sisteminizin standart uygulama veri klasörlerine kaydeder:
- **Windows:** `%LOCALAPPDATA%\Mail Bot\`
- **macOS:** `~/Library/Application Support/Mail Bot/`
- **Linux:** `~/.local/share/mail-bot/`

Log dosyaları da (`app.log`) bu klasörlerin içinde yer alır.

## ⚠️ Önemli Notlar

- **Playwright:** İlk çalıştırmada tarayıcı otomatik kurulacaktır. Eğer Linux kullanıyorsanız, sistem bağımlılıkları için `sudo npx playwright install-deps` komutu gerekebilir.
- **Tkinter:** Linux'ta `sudo apt-get install python3-tk` gerekebilir.
- **Gmail:** Google Hesabınızda "Uygulama Şifresi" oluşturduğunuzdan emin olun. Standart şifre ile gönderim yapılamaz.
- **Güvenlik:** API anahtarlarınız işletim sisteminin güvenli kasasında (Keychain/Credential Manager) saklanır.

## 🚀 Başlangıç
Uygulama açıldıktan sonra **Yardım** sekmesine giderek detaylı kullanım kılavuzunu inceleyebilirsiniz.
