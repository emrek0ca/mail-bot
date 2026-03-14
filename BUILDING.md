# Mail Bot Packaging

## macOS `.app` build

1. Tk destekli bir Python kullanin.
2. `./scripts/build_macos_app.sh`
3. Cikti:
   - `dist/Mail Bot.app`
   - `dist/MailBot-macOS.zip`

## Notlar

- Uygulama veritabani ve kullanici verileri `~/Library/Application Support/Mail Bot/` altina yazilir.
- Chromium ilk Playwright testinde veya ilk tarama aninda `~/Library/Application Support/Mail Bot/playwright-browsers/` altina otomatik kurulur.
- Ilk acilista Ayarlar sekmesindeki servis testleriyle Gemini, Gmail ve tarayici entegrasyonlarini dogrulayin.
- Paket PyInstaller tarafinda ad-hoc imzalanir. Apple notarization bu akista yoktur; baska bir Mac'te Gatekeeper uyarisi cikarsa sag tik -> Open ile ilk acilis yapilabilir.
