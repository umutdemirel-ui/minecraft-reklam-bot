# Minecraft Auto Advertiser

**Minecraft Java Edition · Windows 10/11 · Python 3.12+**

İzinli sunucularda çalışan, Türkçe, koyu antrasit / ateş kırmızısı arayüzlü sohbet mesajı zamanlayıcısı. Sunucu kurallarını aşmaz; CAPTCHA, anti-cheat veya başka bir korumayı atlatmaya yönelik özellik içermez.

> **Önemli sınır:** Uygulama bir sunucuya bağlanmaz, sunucu kurallarını okuyamaz ve mesajın sunucu tarafından kabul edildiğini doğrulayamaz. Geçmişteki **“Gönderildi\***”, “Enter tuşu tespit edilen bir giriş hatası olmadan gönderildi” anlamına gelir. Sohbet ekranının görüntüsü de doğrulanmaz. Varsayılan **T** sohbet düzeni ve gönderim sırasında açık menü bulunmaması kullanıcı tarafından onaylanmalıdır.

## İndir / çalıştır

Windows doğrulama hattı başarılı olduğunda GitHub → **Actions** → **Windows tests and desktop build** → ilgili çalıştırma → **Artifacts** bölümünde `MinecraftAutoAdvertiser-Windows` bulunur:

- `MinecraftAutoAdvertiser-Setup-1.0.0.exe`: kullanıcı hesabına kurulan sürüm.
- `MinecraftAutoAdvertiser-Portable-1.0.0.zip`: tamamını bir klasöre çıkarıp içindeki EXE'yi çalıştırın. ZIP içindeki `portable.txt` dosyasını silmeyin.

Python, CMD veya ek bir Python paketi kurmanız gerekmez. İndirilen dosyaları yalnızca güvendiğiniz deponun kendi Actions çıktısından alın. Bu proje kod imzalama sertifikası içermez; Windows SmartScreen uyarısı verebilir. İmzasız bir dosyayı doğrulamadan çalıştırmayın.

**Gerçek bir Minecraft sunucusunda kabul testi, otomatik testlerin yerine geçmez.** İlk kullanımda izinli bir test sunucusunda, görünür bir test mesajıyla doğrulayın. Windows derleme ve arayüz açılış testinin güncel sonucu deponun Actions sayfasındadır; burada gerçek oyun istemcisiyle test edildiği iddia edilmez.

## İlk kullanım

1. Uygulamayı ve Minecraft Java Edition'ı açın; izinli sunucunuza girin.
2. **Ayarlar** ekranında sunucunun otomasyona açıkça izin verdiğini ve varsayılan **T** sohbet düzenini kullandığınızı onaylayın. Sunucunun karakter sınırını girin.
3. **Mesaj yönetimi → Yeni mesaj** ile başlık, tek satır içerik ve saniye cinsinden aralık ekleyin. Birden çok mesaj ekleyebilirsiniz; pasif mesajlar atlanır.
4. **Zamanlayıcı** ekranında genel aralığı, ek bekleme ve başlangıç gecikmesini ayarlayın. Sunucunun minimum aralığını doğru girin; varsayılanlar 180 saniyedir.
5. Minecraft'ta sohbeti manuel olarak açıp kapatın; envanter, sandık, menü veya başka bir ekran açık kalmasın.
6. Dashboard'da gerekirse doğru Java penceresini seçin, **Başlat**'a basın ve başlangıç gecikmesi içinde Minecraft'ı öne getirin.
7. **F8** her ekrandan acil durdurur. **Duraklat** sayacı korur; **Durdur** oturumu kapatır. Odak geri geldiğinde otomasyon kendiliğinden devam etmez.

Uygulama açık değilken, Minecraft kapalıyken veya uygulama yalnızca Windows başlangıcında açıldığında mesaj göndermez. Her oturum açık bir Başlat/Sürdür eylemi gerektirir.

## Güvenlik davranışları

- Hedef süreç yalnızca `java.exe` veya `javaw.exe` olabilir. Başlık eşleşmesi tek başına yeterli değildir.
- `Minecraft`, `Minecraft* 1.x.x`, sürüm/snapshot ekleri ve oyun durum ekleri tanınır. Launcher, tarayıcı ve Bedrock hedeflenmez.
- Birden fazla aday varsa otomatik seçim yapılmaz. Dashboard'daki listeden hedef seçilmelidir.
- HWND, PID ve süreç başlangıç zamanı birlikte doğrulanır. Pencere kapanması, yeniden başlatma veya HWND yeniden kullanımı eski hedefi geçersiz kılar.
- Pencere simge durumundaysa, görünmüyorsa veya yanıt vermiyorsa gönderim duraklar.
- Pencere otomatik öne getirilmez. Her tuş işleminden ve her mesaj karakterinden önce canlı odak kontrolü yapılır.
- Windows girdisi ile odak kontrolü atomik değildir: kontrolden hemen sonra işletim sistemi odağını değiştirirse mutlak garanti verilemez. Bu nedenle oyunu siz ön planda tutun ve F8'i kullanın.
- Türkçe karakterler pano değiştirilmeden Unicode `SendInput` ile yazılır. T, Ctrl+A, Backspace ve Enter işlemlerinde PyAutoGUI kullanılır.
- `/` ile başlayan komutlar, çok satırlı içerik ve kontrol karakterleri engellenir.
- Bir girişim için en fazla bir Enter denemesi vardır. Otomatik retry yoktur. Hata, iptal veya belirsiz sonuç güvenli duraklatır.
- Enter öncesinde iptal edilen mesajın **taslağı oyunda kalabilir**. Kendiniz kontrol edin; uygulama iptalden sonra istenmeyen ek tuşlar göndermez.
- Bekleme süresi veritabanında ilk tuştan önce saklanır. Durdur/başlat, geçmiş temizleme veya yeniden açma bu bekleme kaydını sıfırlamaz.

## Zamanlama nasıl hesaplanır?

```text
etkin aralık = max(genel aralık,
                   sunucunun minimum aralığı,
                   o mesajın aralığı)
               + mesajlar arası ek bekleme
```

Örnek: genel 120 sn, sunucu alt sınırı 180 sn, mesaj aralığı 300 sn, ek bekleme 10 sn → **310 sn**.

Mesajın aralığı, **o mesajdan sonraki bekleme** anlamına gelir; aynı mesajın bağımsız bir tekrar sayacı değildir. Aktif mesajlar kayıt sırasıyla ilerler. Döngü kapalıysa liste bir kez tamamlanır. Mesaj eklemek, silmek, düzenlemek veya etkinliğini değiştirmek oturumu duraklatır; sürdürüldüğünde güncel liste baştan ilerler. Önceki gönderimin bekleme süresi korunur.

Başlangıç gecikmesi varsayılan 10 saniyedir. Önceki gönderimden kalan bekleme daha uzunsa o uygulanır. Çalışma sınırı etkin oturum süresini ölçer; duraklatılan süre bu sınıra eklenmez. `0` sınırsızdır. Süre denetimi gönderimler arasında yapılır; uzun süren bir işletim sistemi çağrısını zorla kesmez.

Tüm alt sınırlar yapılandırmada en az 30 saniyedir. Bu teknik alt sınır sunucu izni değildir: sunucunuz daha uzun süre istiyorsa onun kuralını girin. Uygulama sunucu kuralını otomatik keşfettiğini iddia etmez.

## Veriler, yedek ve taşınabilir kullanım

Normal kurulum:

```text
%LOCALAPPDATA%\MinecraftAutoAdvertiser\
├── advertiser.db
├── instance.lock
└── logs\application.log
```

Taşınabilir sürüm:

```text
MinecraftAutoAdvertiser.exe
portable.txt
data\advertiser.db
data\logs\application.log
```

`portable.txt` varsa veriler EXE yanındaki `data` klasöründe tutulur. Yazılabilir bir klasöre çıkarın; Program Files içine çıkarmayın. Taşınabilir ve kurulu sürümlerin verileri ayrıdır. Aynı veri klasörü için tek uygulama örneği kilidi kullanılır. Farklı veri klasörleriyle iki kopyayı aynı anda çalıştırmayın.

Ayarlar SQLite'tadır. Depodaki `config/settings.json` yalnızca ilk açılış varsayılanlarıdır; çalışan kullanıcının ayar dosyası değildir.

**Ayarlar → Veritabanını yedekle** SQLite backup API ile tutarlı bir kopya alır, bütünlüğünü kontrol eder ve seçilen dosyaya atomik olarak yerleştirir. Geçmişi temizlemek mesajları veya ayarları silmez.

Geri yükleme: uygulamayı tamamen kapatın, mevcut `advertiser.db` dosyasını başka bir yere yedekleyin, seçtiğiniz yedeği `advertiser.db` adıyla veri klasörüne koyun. Eski `-wal` ve `-shm` dosyalarını kapatılmış eski veritabanından yeni veritabanına taşımayın; kapatma sonrası bunlar normalde birleşmiş olur. Sonra uygulamayı açın. Geçmişte `pending/sending` kalan kayıtlar açılışta **Belirsiz** olur ve yeniden gönderilmez.

Windows başlangıcına ekleme tercihi `HKCU\...\Run` altındadır. Yalnızca siz kaydederseniz değiştirilir. Kaldırmadan önce Ayarlar'da kapatın. Kurulumu kaldırmak kullanıcı verilerini otomatik silmez.

## Kaynaktan geliştirme

Python **3.12 veya üzeri** ve etkileşimli Windows masaüstü gerekir. Arayüz yönetimi Linux'ta geliştirilebilir ancak gerçek pencere/klavye otomasyonu yalnızca Windows'tadır.

```powershell
py -3.12 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements-dev.txt
.\.venv\Scripts\python.exe main.py
```

Testler gerçek klavye girdisi üretmez:

```powershell
.\.venv\Scripts\python.exe -m pytest -q
.\.venv\Scripts\python.exe scripts\smoke_ui.py --screenshots dist\screenshots
```

## Windows EXE ve kurulum dosyası üretme

Windows'ta, depo kökünde:

```powershell
.\.venv\Scripts\python.exe -m pip install -r requirements-dev.txt
.\.venv\Scripts\python.exe scripts\build_windows.py
```

Bu komut testleri çalıştırır, PyInstaller ile pencere modunda tek EXE üretir ve taşınabilir ZIP oluşturur. Tek adımlı doğrudan PyInstaller komutu:

```powershell
.\.venv\Scripts\python.exe -m PyInstaller --clean --noconfirm MinecraftAutoAdvertiser.spec
```

Inno Setup 6 kuruluysa kurulum EXE'sini de üretmek için:

```powershell
.\.venv\Scripts\python.exe scripts\build_windows.py --installer
```

Çıktılar `dist/` altındadır. `build/`, `.venv/`, `dist/` ve çalışma zamanı verileri Git'e eklenmez. Linux üzerinde PyInstaller çalıştırmak Windows EXE üretmez; `.github/workflows/windows.yml` gerçek `windows-latest`, Python 3.12 üzerinde test, arayüz açılışı, paketleme, taşınabilir EXE açılışı ve kurulum/açılış doğrulaması yapar.

## Mimari

```text
main.py                         açılış, log, tek örnek, kurtarma
config/settings.json            ilk çalıştırma varsayılanları
core/
  config.py                     doğrulanan ayarlar ve veri yolları
  minecraft_detector.py         PyGetWindow + canlı Win32 kimlik/odak kontrolü
  window_monitor.py             1 Hz iptal edilebilir pencere izleme
  message_engine.py             tek denemelik gönderim ve sonuç kaydı
  keyboard_adapter.py           PyAutoGUI + Unicode SendInput
  scheduler.py                  monotonic sayaç, sıralı kuyruk, tek işçi
  safety_manager.py             izin ön koşulları ve F8 mandalı
  hotkeys.py                    F8 global kısayol kaydı
  single_instance.py            aynı veri klasörü için örnek kilidi
  startup.py                    açık tercihle HKCU başlangıç kaydı
database/
  models.py                     mesaj ve girişim modelleri
  database.py                   WAL SQLite, ayarlar, geçmiş, yedek
ui/
  app.py                        composition root, Tk iş parçacığı sınırı
  dashboard.py                  canlı durum ve oturum kontrolleri
  messages.py                   mesaj ekleme/düzenleme/etkinlik
  scheduler_view.py             dakika/saniye ve oturum ayarları
  history.py                    sayfalı geçmiş ve temizleme
  settings.py                   izin, tespit, tema, başlangıç, yedek
assets/icon.ico                 özgün uygulama simgesi
tests/                          sahte saat/Backend/Keyboard ile güvenlik testleri
scripts/                        simge, arayüz smoke ve Windows derleme
installer/                      Inno Setup ve EXE sürüm bilgisi
```

Arayüz ana thread'de çalışır. Zamanlayıcı ayrı bir işçi, pencere izleme ayrı bir işçi kullanır; arayüze yalnızca kuyruklar üzerinden bildirim gelir. SQLite işlemleri kendi bağlantılarını açar. Kapatmada iptal sinyali verilir, işçiler beklenir ve kısayol kaldırılır. SQLite kilitlenmesi gibi uzun işletim sistemi çağrıları kapanışı birkaç saniye geciktirebilir.

## Sorun giderme

| Belirti | Yapılacaklar |
|---|---|
| Minecraft bulunamadı | Java oyununu açın; launcher yerine oyun penceresini açın. Gerekirse Ayarlar'da tam başlık girin. |
| Birden fazla aday | Dashboard'da doğru PID/pencereyi seçin. |
| Aktif pencere değil | Minecraft'ı öne getirin; ardından Sürdür'e basın. |
| F8 kaydedilemedi | Başka kısayol yazılımı çakışmasını kontrol edin; Ayarlar'dan yeniden kaydedin. F8 hazır değilse otomasyon başlamaz. |
| Sohbet açılmıyor / yanlış yazılıyor | Hemen F8. T düzenini, açık menüleri ve pencere odağını kontrol edin. Bu arayüz görüntüden doğrulanmaz. |
| Yanıt vermiyor | Oyunun düzelmesini bekleyin. Otomasyon kendiliğinden devam etmez. |
| Belirsiz gönderim | Sunucu sohbetini kontrol edin. Kayıt otomatik tekrarlanmaz. |
| Veritabanı hatası | Yazma izinlerini, disk alanını ve veri klasörünü kontrol edin. Loglar veri klasöründedir. |
| Başka kopya açık | Çalışan kopyayı kapatın; aynı anda ikinci zamanlayıcı çalıştırmayın. |
| Akıllı ekran uyarısı | Dosyanın kaynağını ve Actions derlemesini doğrulayın; imzasız yazılıma otomatik güvenmeyin. |

Minecraft/Mojang/Microsoft ile bağlantılı veya onların tarafından onaylanmış bir ürün değildir. Başka oyuncuların deneyimini ve sunucu kurallarını gözetin.
