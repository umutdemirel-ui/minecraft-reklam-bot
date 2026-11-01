# Doğrulama ve sınırlar

## Otomatik kapsam

- Mesaj CRUD, Türkçe metin, uzunluk/komut engeli, sıralama.
- Ayar doğrulama, ilk açılışta otomasyonun kapalı olması.
- SQLite WAL, eşzamanlı girişimler, yedek bütünlüğü, geçmiş temizliğinde cooldown korunması.
- Java süreç filtresi, canlı başlık, HWND/PID/başlangıç zamanı, odağa geçmeme.
- Eksik/çoklu/kapanmış/simge/yanıtsız pencere durumları.
- Etkin aralık hesabı, döngü, sıra sıfırlama, duraklatılan sayacın korunması.
- Gerçek işçi thread'i ile sahte saat ve sahte gönderim motoru.
- Önce jurnal, sonra girdi; Enter belirsizliğinde retry olmaması.
- F8 iptali ve eski işçinin yeni oturumu değiştirememesi.
- Unicode UTF-16 surrogate pair ve Win32 INPUT boyutu (Windows işinde).
- Beş arayüz sayfasının gerçek CustomTkinter ile kurulması; otomasyon başlatılmaz.
- PyInstaller tek EXE, taşınabilir ZIP, Inno Setup kurulumu ve paketlenmiş uygulama açılışı.

## Otomatik olmayan kabul testi

Gerçek Windows masaüstü ve izinli test sunucusunda aşağıdakiler bir insan tarafından doğrulanmalıdır:

- [ ] Java oyun penceresi doğru bulunuyor, launcher bulunmuyor.
- [ ] İki Java örneğinde seçim yapılmadan gönderilmiyor.
- [ ] T ile sohbet manuel açılıyor; Türkçe ve emoji metni doğru giriliyor.
- [ ] İzin/onay kutuları kapalıyken Başlat engelleniyor.
- [ ] Başlat sonrası kullanıcı oyunu öne getiriyor, ilk mesaj bir kez gönderiliyor.
- [ ] Genel/kişisel/sunucu aralıklarından en büyüğü + ek bekleme uygulanıyor.
- [ ] Başka pencereye geçiş, simge durumuna alma ve oyunu kapatma duraklatıyor.
- [ ] Odak geri geldiğinde kendiliğinden mesaj gitmiyor.
- [ ] F8 başka uygulamadayken de durduruyor.
- [ ] Hata sonrası aynı mesaj otomatik tekrarlanmıyor.
- [ ] Geçmiş, yeniden açılış, yedek/geri yükleme ve cooldown doğru.
- [ ] Kurulum ve taşınabilir veri yolları doğru.
- [ ] Yüksek DPI ve küçük ekranda kontroller erişilebilir.

`smoke-test` bir arayüz açılış testidir; oyun/sunucu kabul testi değildir. CI ekran görüntüleri izole örnek veriyle üretilir, gerçek gönderim kanıtı olarak sunulmaz.

## Bilinen teknik sınırlar

Win32 foreground kontrolü ile SendInput atomik bir işlem değildir. Uygulama her karakterden önce kontrol eder ancak işletim sisteminin bu kontrol ile girdi arasında odak değiştirmesi teorik olarak engellenemez. Sohbet UI durumu veya sunucu ACK okunmaz. Enter çağrısınınkısmen uygulanıp hata döndürmesi belirsiz olarak kaydedilir. Bu sınırlar gizlenmez ve otomatik tekrar deneme ile kapatılmaz.