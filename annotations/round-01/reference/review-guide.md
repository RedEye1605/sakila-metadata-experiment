# Paket review ilmiah

Status: **draft, belum disetujui**. Reviewer: peneliti bersama dosen/rekan. Tidak ada persetujuan otomatis dari hasil eksekusi atau EX pilot.

## Cara meninjau

Salin CSV ke directory kerja reviewer; artifact paket ini tidak ditimpa. Isi decision dengan accepted, revise, atau rejected; tulis rationale, reviewer, dan reviewed_at_utc. Keputusan CSV merupakan catatan review, bukan perubahan otomatis pada dataset atau approval gate.

Untuk setiap soal, periksa makna, kolom yang diminta, grain agregasi, JOIN, duplikasi, NULL, urutan, tie-breaking dan kesesuaian rubric. Bedakan keberhasilan eksekusi dari kebenaran semantik. Periksa paraphrase pilot terhadap semua soal utama; kesamaan struktur SQL saja tidak berarti soal identik.

Untuk anotasi, periksa sumber, satuan, nullability, peran relasi dan konteks bisnis. S1/S2 harus mencakup elemen sama; S3 mempertahankan S2. Tolak SQL solusi, petunjuk spesifik soal, atau aturan bisnis tanpa dasar. Jangan mengubah soal agar model mendapat skor lebih tinggi.

Setelah koreksi disepakati, buat dataset/specification versi baru, validasi ulang referensi dan snapshots yang terpengaruh, lalu catat approval untuk hash final. Persetujuan statistik masih menunggu bimbingan.

## Q001 (main, simple)

Berapa jumlah aktor yang tercatat?

```sql
SELECT COUNT(*) FROM actor
```

Kontrak: 1 kolom; ordered=False; approximate columns=().

Cuplikan hasil referensi bertipe (maksimum 3 baris; hasil lengkap tersedia pada reference_result di CSV):

```json
[[["number", "200"]]]
```

## Q002 (main, simple)

Tampilkan ID film, judul, dan durasi dalam menit untuk film yang durasinya lebih dari 120 menit. Urutkan menurut ID film menaik.

```sql
SELECT film_id,title,length FROM film WHERE length>120 ORDER BY film_id
```

Kontrak: 3 kolom; ordered=True; approximate columns=().

Cuplikan hasil referensi bertipe (maksimum 3 baris; hasil lengkap tersedia pada reference_result di CSV):

```json
[[["number", "5"], ["text", "AFRICAN EGG"], ["number", "130"]], [["number", "6"], ["text", "AGENT TRUMAN"], ["number", "169"]], [["number", "11"], ["text", "ALAMO VIDEOTAPE"], ["number", "126"]]]
```

## Q003 (main, simple)

Tampilkan ID pelanggan, nama depan, dan nama belakang pelanggan dengan penanda active bernilai 1. Urutkan menurut ID pelanggan menaik.

```sql
SELECT customer_id,first_name,last_name FROM customer WHERE active=1 ORDER BY customer_id
```

Kontrak: 3 kolom; ordered=True; approximate columns=().

Cuplikan hasil referensi bertipe (maksimum 3 baris; hasil lengkap tersedia pada reference_result di CSV):

```json
[[["number", "1"], ["text", "MARY"], ["text", "SMITH"]], [["number", "2"], ["text", "PATRICIA"], ["text", "JOHNSON"]], [["number", "3"], ["text", "LINDA"], ["text", "WILLIAMS"]]]
```

## Q004 (main, simple)

Berapa jumlah film dengan rating PG-13?

```sql
SELECT COUNT(*) FROM film WHERE rating='PG-13'
```

Kontrak: 1 kolom; ordered=False; approximate columns=().

Cuplikan hasil referensi bertipe (maksimum 3 baris; hasil lengkap tersedia pada reference_result di CSV):

```json
[[["number", "223"]]]
```

## Q005 (main, simple)

Berapa rata-rata tarif sewa yang dikonfigurasi pada film? Bulatkan hasil menjadi dua angka desimal.

```sql
SELECT ROUND(AVG(rental_rate),2) FROM film
```

Kontrak: 1 kolom; ordered=False; approximate columns=().

Cuplikan hasil referensi bertipe (maksimum 3 baris; hasil lengkap tersedia pada reference_result di CSV):

```json
[[["number", "2.98"]]]
```

## Q006 (main, simple)

Berapa total nilai seluruh pembayaran pelanggan yang tercatat?

```sql
SELECT SUM(amount) FROM payment
```

Kontrak: 1 kolom; ordered=False; approximate columns=().

Cuplikan hasil referensi bertipe (maksimum 3 baris; hasil lengkap tersedia pada reference_result di CSV):

```json
[[["number", "67406.56"]]]
```

## Q007 (main, simple)

Tampilkan ID film, judul, dan nilai penggantian untuk film dengan nilai penggantian lebih dari 20. Urutkan menurut ID film menaik.

```sql
SELECT film_id,title,replacement_cost FROM film WHERE replacement_cost>20 ORDER BY film_id
```

Kontrak: 3 kolom; ordered=True; approximate columns=().

Cuplikan hasil referensi bertipe (maksimum 3 baris; hasil lengkap tersedia pada reference_result di CSV):

```json
[[["number", "1"], ["text", "ACADEMY DINOSAUR"], ["number", "20.99"]], [["number", "4"], ["text", "AFFAIR PREJUDICE"], ["number", "26.99"]], [["number", "5"], ["text", "AFRICAN EGG"], ["number", "22.99"]]]
```

## Q008 (main, simple)

Berapa durasi sewa minimum dan maksimum yang dikonfigurasi pada film? Tampilkan minimum terlebih dahulu, lalu maksimum, dalam satuan hari.

```sql
SELECT MIN(rental_duration),MAX(rental_duration) FROM film
```

Kontrak: 2 kolom; ordered=False; approximate columns=().

Cuplikan hasil referensi bertipe (maksimum 3 baris; hasil lengkap tersedia pada reference_result di CSV):

```json
[[["number", "3"], ["number", "7"]]]
```

## Q009 (main, simple)

Berapa jumlah transaksi penyewaan yang belum memiliki tanggal pengembalian tercatat?

```sql
SELECT COUNT(*) FROM rental WHERE return_date IS NULL
```

Kontrak: 1 kolom; ordered=False; approximate columns=().

Cuplikan hasil referensi bertipe (maksimum 3 baris; hasil lengkap tersedia pada reference_result di CSV):

```json
[[["number", "183"]]]
```

## Q010 (main, simple)

Tampilkan ID penyewaan, tanggal penyewaan, dan tanggal pengembalian untuk pelanggan ber-ID 1. Urutkan menurut tanggal penyewaan menaik, lalu ID penyewaan menaik.

```sql
SELECT rental_id,rental_date,return_date FROM rental WHERE customer_id=1 ORDER BY rental_date,rental_id
```

Kontrak: 3 kolom; ordered=True; approximate columns=().

Cuplikan hasil referensi bertipe (maksimum 3 baris; hasil lengkap tersedia pada reference_result di CSV):

```json
[[["number", "76"], ["datetime", "2005-05-25T11:30:37.000000"], ["datetime", "2005-06-03T12:00:37.000000"]], [["number", "573"], ["datetime", "2005-05-28T10:35:23.000000"], ["datetime", "2005-06-03T06:32:23.000000"]], [["number", "1185"], ["datetime", "2005-06-15T00:54:12.000000"], ["datetime", "2005-06-23T02:42:12.000000"]]]
```

## Q011 (main, medium)

Untuk setiap kategori, tampilkan ID kategori, nama kategori, dan jumlah film di kategori tersebut. Sertakan kategori tanpa film dengan jumlah nol. Urutkan menurut ID kategori menaik.

```sql
SELECT c.category_id,c.name,COUNT(fc.film_id) FROM category c LEFT JOIN film_category fc ON fc.category_id=c.category_id GROUP BY c.category_id,c.name ORDER BY c.category_id
```

Kontrak: 3 kolom; ordered=True; approximate columns=().

Cuplikan hasil referensi bertipe (maksimum 3 baris; hasil lengkap tersedia pada reference_result di CSV):

```json
[[["number", "1"], ["text", "Action"], ["number", "64"]], [["number", "2"], ["text", "Animation"], ["number", "66"]], [["number", "3"], ["text", "Children"], ["number", "60"]]]
```

## Q012 (main, medium)

Untuk setiap pelanggan, tampilkan ID pelanggan, nama depan, nama belakang, dan total nilai pembayaran yang tercatat. Sertakan pelanggan tanpa pembayaran dengan total nol. Urutkan menurut ID pelanggan menaik.

```sql
SELECT c.customer_id,c.first_name,c.last_name,COALESCE(SUM(p.amount),0) FROM customer c LEFT JOIN payment p ON p.customer_id=c.customer_id GROUP BY c.customer_id,c.first_name,c.last_name ORDER BY c.customer_id
```

Kontrak: 4 kolom; ordered=True; approximate columns=().

Cuplikan hasil referensi bertipe (maksimum 3 baris; hasil lengkap tersedia pada reference_result di CSV):

```json
[[["number", "1"], ["text", "MARY"], ["text", "SMITH"], ["number", "118.68"]], [["number", "2"], ["text", "PATRICIA"], ["text", "JOHNSON"], ["number", "128.73"]], [["number", "3"], ["text", "LINDA"], ["text", "WILLIAMS"], ["number", "135.74"]]]
```

## Q013 (main, medium)

Untuk setiap kategori yang memiliki film, tampilkan ID kategori, nama kategori, dan rata-rata durasi film dalam menit yang dibulatkan menjadi dua angka desimal. Urutkan menurut ID kategori menaik.

```sql
SELECT c.category_id,c.name,ROUND(AVG(f.length),2) FROM category c JOIN film_category fc ON fc.category_id=c.category_id JOIN film f ON f.film_id=fc.film_id GROUP BY c.category_id,c.name ORDER BY c.category_id
```

Kontrak: 3 kolom; ordered=True; approximate columns=().

Cuplikan hasil referensi bertipe (maksimum 3 baris; hasil lengkap tersedia pada reference_result di CSV):

```json
[[["number", "1"], ["text", "Action"], ["number", "111.61"]], [["number", "2"], ["text", "Animation"], ["number", "111.02"]], [["number", "3"], ["text", "Children"], ["number", "109.8"]]]
```

## Q014 (main, medium)

Tampilkan ID aktor, nama depan, dan nama belakang semua aktor yang tercatat membintangi film ber-ID 1. Urutkan menurut ID aktor menaik.

```sql
SELECT a.actor_id,a.first_name,a.last_name FROM actor a JOIN film_actor fa ON fa.actor_id=a.actor_id WHERE fa.film_id=1 ORDER BY a.actor_id
```

Kontrak: 3 kolom; ordered=True; approximate columns=().

Cuplikan hasil referensi bertipe (maksimum 3 baris; hasil lengkap tersedia pada reference_result di CSV):

```json
[[["number", "1"], ["text", "PENELOPE"], ["text", "GUINESS"]], [["number", "10"], ["text", "CHRISTIAN"], ["text", "GABLE"]], [["number", "20"], ["text", "LUCILLE"], ["text", "TRACY"]]]
```

## Q015 (main, medium)

Untuk setiap staf, tampilkan ID staf, nama depan, nama belakang, dan jumlah pembayaran yang dicatat oleh staf tersebut. Sertakan staf tanpa pembayaran dengan jumlah nol. Urutkan menurut ID staf menaik.

```sql
SELECT s.staff_id,s.first_name,s.last_name,COUNT(p.payment_id) FROM staff s LEFT JOIN payment p ON p.staff_id=s.staff_id GROUP BY s.staff_id,s.first_name,s.last_name ORDER BY s.staff_id
```

Kontrak: 4 kolom; ordered=True; approximate columns=().

Cuplikan hasil referensi bertipe (maksimum 3 baris; hasil lengkap tersedia pada reference_result di CSV):

```json
[[["number", "1"], ["text", "Mike"], ["text", "Hillyer"], ["number", "8054"]], [["number", "2"], ["text", "Jon"], ["text", "Stephens"], ["number", "7990"]]]
```

## Q016 (main, medium)

Untuk setiap toko, tampilkan ID toko dan jumlah salinan film dalam inventaris toko itu. Sertakan toko tanpa inventaris dengan jumlah nol. Urutkan menurut ID toko menaik.

```sql
SELECT s.store_id,COUNT(i.inventory_id) FROM store s LEFT JOIN inventory i ON i.store_id=s.store_id GROUP BY s.store_id ORDER BY s.store_id
```

Kontrak: 2 kolom; ordered=True; approximate columns=().

Cuplikan hasil referensi bertipe (maksimum 3 baris; hasil lengkap tersedia pada reference_result di CSV):

```json
[[["number", "1"], ["number", "2270"]], [["number", "2"], ["number", "2311"]]]
```

## Q017 (main, medium)

Tampilkan ID film, judul, dan nama bahasa yang ditetapkan sebagai bahasa film, bukan bahasa aslinya. Urutkan menurut ID film menaik.

```sql
SELECT f.film_id,f.title,l.name FROM film f JOIN language l ON l.language_id=f.language_id ORDER BY f.film_id
```

Kontrak: 3 kolom; ordered=True; approximate columns=().

Cuplikan hasil referensi bertipe (maksimum 3 baris; hasil lengkap tersedia pada reference_result di CSV):

```json
[[["number", "1"], ["text", "ACADEMY DINOSAUR"], ["text", "English"]], [["number", "2"], ["text", "ACE GOLDFINGER"], ["text", "English"]], [["number", "3"], ["text", "ADAPTATION HOLES"], ["text", "English"]]]
```

## Q018 (main, medium)

Untuk setiap negara, tampilkan ID negara, nama negara, dan jumlah kota yang tercatat di negara tersebut. Sertakan negara tanpa kota dengan jumlah nol. Urutkan menurut ID negara menaik.

```sql
SELECT co.country_id,co.country,COUNT(ci.city_id) FROM country co LEFT JOIN city ci ON ci.country_id=co.country_id GROUP BY co.country_id,co.country ORDER BY co.country_id
```

Kontrak: 3 kolom; ordered=True; approximate columns=().

Cuplikan hasil referensi bertipe (maksimum 3 baris; hasil lengkap tersedia pada reference_result di CSV):

```json
[[["number", "1"], ["text", "Afghanistan"], ["number", "1"]], [["number", "2"], ["text", "Algeria"], ["number", "3"]], [["number", "3"], ["text", "American Samoa"], ["number", "1"]]]
```

## Q019 (main, medium)

Tampilkan ID pelanggan, nama depan, nama belakang, dan jumlah transaksi penyewaan untuk pelanggan yang memiliki sedikitnya 30 transaksi penyewaan. Urutkan menurut jumlah penyewaan menurun, lalu ID pelanggan menaik.

```sql
SELECT c.customer_id,c.first_name,c.last_name,COUNT(r.rental_id) AS rental_count FROM customer c JOIN rental r ON r.customer_id=c.customer_id GROUP BY c.customer_id,c.first_name,c.last_name HAVING COUNT(r.rental_id)>=30 ORDER BY rental_count DESC,c.customer_id
```

Kontrak: 4 kolom; ordered=True; approximate columns=().

Cuplikan hasil referensi bertipe (maksimum 3 baris; hasil lengkap tersedia pada reference_result di CSV):

```json
[[["number", "148"], ["text", "ELEANOR"], ["text", "HUNT"], ["number", "46"]], [["number", "526"], ["text", "KARL"], ["text", "SEAL"], ["number", "45"]], [["number", "144"], ["text", "CLARA"], ["text", "SHAW"], ["number", "42"]]]
```

## Q020 (main, medium)

Untuk setiap tanggal kalender pembayaran yang tercatat, tampilkan tanggal, jumlah pembayaran, dan total nilainya. Urutkan menurut tanggal menaik.

```sql
SELECT DATE(payment_date) AS payment_day,COUNT(*),SUM(amount) FROM payment GROUP BY DATE(payment_date) ORDER BY payment_day
```

Kontrak: 3 kolom; ordered=True; approximate columns=().

Cuplikan hasil referensi bertipe (maksimum 3 baris; hasil lengkap tersedia pada reference_result di CSV):

```json
[[["date", "2005-05-24"], ["number", "8"], ["number", "29.92"]], [["date", "2005-05-25"], ["number", "137"], ["number", "573.63"]], [["date", "2005-05-26"], ["number", "174"], ["number", "754.26"]]]
```

## Q021 (main, complex)

Tampilkan ID film, judul, dan durasi dalam menit untuk film yang durasinya melebihi rata-rata durasi seluruh film yang terisi. Urutkan menurut ID film menaik.

```sql
SELECT film_id,title,length FROM film WHERE length>(SELECT AVG(length) FROM film) ORDER BY film_id
```

Kontrak: 3 kolom; ordered=True; approximate columns=().

Cuplikan hasil referensi bertipe (maksimum 3 baris; hasil lengkap tersedia pada reference_result di CSV):

```json
[[["number", "4"], ["text", "AFFAIR PREJUDICE"], ["number", "117"]], [["number", "5"], ["text", "AFRICAN EGG"], ["number", "130"]], [["number", "6"], ["text", "AGENT TRUMAN"], ["number", "169"]]]
```

## Q022 (main, complex)

Tampilkan ID pelanggan, nama depan, nama belakang, dan total pembayarannya untuk pelanggan dengan total pembayaran di atas rata-rata total pembayaran per pelanggan. Dalam perhitungan rata-rata, sertakan seluruh pelanggan dan anggap total pelanggan tanpa pembayaran nol. Urutkan menurut ID pelanggan menaik.

```sql
WITH totals AS (SELECT c.customer_id,c.first_name,c.last_name,COALESCE(SUM(p.amount),0) AS total_paid FROM customer c LEFT JOIN payment p ON p.customer_id=c.customer_id GROUP BY c.customer_id,c.first_name,c.last_name) SELECT customer_id,first_name,last_name,total_paid FROM totals WHERE total_paid>(SELECT AVG(total_paid) FROM totals) ORDER BY customer_id
```

Kontrak: 4 kolom; ordered=True; approximate columns=().

Cuplikan hasil referensi bertipe (maksimum 3 baris; hasil lengkap tersedia pada reference_result di CSV):

```json
[[["number", "1"], ["text", "MARY"], ["text", "SMITH"], ["number", "118.68"]], [["number", "2"], ["text", "PATRICIA"], ["text", "JOHNSON"], ["number", "128.73"]], [["number", "3"], ["text", "LINDA"], ["text", "WILLIAMS"], ["number", "135.74"]]]
```

## Q023 (main, complex)

Tampilkan sepuluh kategori dengan jumlah transaksi penyewaan terbanyak atas salinan filmnya. Tampilkan ID kategori, nama kategori, dan jumlah transaksi penyewaan. Urutkan jumlah menurun; jika sama, ID kategori menaik.

```sql
SELECT c.category_id,c.name,COUNT(r.rental_id) AS rental_count FROM category c JOIN film_category fc ON fc.category_id=c.category_id JOIN inventory i ON i.film_id=fc.film_id JOIN rental r ON r.inventory_id=i.inventory_id GROUP BY c.category_id,c.name ORDER BY rental_count DESC,c.category_id LIMIT 10
```

Kontrak: 3 kolom; ordered=True; approximate columns=().

Cuplikan hasil referensi bertipe (maksimum 3 baris; hasil lengkap tersedia pada reference_result di CSV):

```json
[[["number", "15"], ["text", "Sports"], ["number", "1179"]], [["number", "2"], ["text", "Animation"], ["number", "1166"]], [["number", "1"], ["text", "Action"], ["number", "1112"]]]
```

## Q024 (main, complex)

Tampilkan sepuluh film dengan total pembayaran tercatat terbesar yang terhubung ke transaksi penyewaan film tersebut. Tampilkan ID film, judul, dan total pembayaran. Abaikan pembayaran tanpa transaksi penyewaan terkait. Urutkan total menurun; jika sama, ID film menaik.

```sql
SELECT f.film_id,f.title,SUM(p.amount) AS total_paid FROM payment p JOIN rental r ON r.rental_id=p.rental_id JOIN inventory i ON i.inventory_id=r.inventory_id JOIN film f ON f.film_id=i.film_id GROUP BY f.film_id,f.title ORDER BY total_paid DESC,f.film_id LIMIT 10
```

Kontrak: 3 kolom; ordered=True; approximate columns=().

Cuplikan hasil referensi bertipe (maksimum 3 baris; hasil lengkap tersedia pada reference_result di CSV):

```json
[[["number", "879"], ["text", "TELEGRAPH VOYAGE"], ["number", "231.73"]], [["number", "973"], ["text", "WIFE TURN"], ["number", "223.69"]], [["number", "1000"], ["text", "ZORRO ARK"], ["number", "214.69"]]]
```

## Q025 (main, complex)

Untuk setiap negara yang memiliki transaksi penyewaan oleh pelanggan beralamat di negara itu, tampilkan ID negara, nama negara, dan jumlah transaksi penyewaan pelanggannya. Urutkan jumlah menurun; jika sama, ID negara menaik.

```sql
SELECT co.country_id,co.country,COUNT(r.rental_id) AS rental_count FROM country co JOIN city ci ON ci.country_id=co.country_id JOIN address a ON a.city_id=ci.city_id JOIN customer c ON c.address_id=a.address_id JOIN rental r ON r.customer_id=c.customer_id GROUP BY co.country_id,co.country ORDER BY rental_count DESC,co.country_id
```

Kontrak: 3 kolom; ordered=True; approximate columns=().

Cuplikan hasil referensi bertipe (maksimum 3 baris; hasil lengkap tersedia pada reference_result di CSV):

```json
[[["number", "44"], ["text", "India"], ["number", "1572"]], [["number", "23"], ["text", "China"], ["number", "1426"]], [["number", "103"], ["text", "United States"], ["number", "968"]]]
```

## Q026 (main, complex)

Tampilkan ID film dan judul film yang tidak mempunyai salinan inventaris di toko ber-ID 1. Urutkan menurut ID film menaik.

```sql
SELECT f.film_id,f.title FROM film f WHERE NOT EXISTS (SELECT 1 FROM inventory i WHERE i.film_id=f.film_id AND i.store_id=1) ORDER BY f.film_id
```

Kontrak: 2 kolom; ordered=True; approximate columns=().

Cuplikan hasil referensi bertipe (maksimum 3 baris; hasil lengkap tersedia pada reference_result di CSV):

```json
[[["number", "2"], ["text", "ACE GOLDFINGER"]], [["number", "3"], ["text", "ADAPTATION HOLES"]], [["number", "5"], ["text", "AFRICAN EGG"]]]
```

## Q027 (main, complex)

Untuk setiap kategori, tampilkan semua film dengan durasi terpanjang di kategori itu, termasuk semua film yang seri. Tampilkan ID kategori, nama kategori, ID film, judul, dan durasi dalam menit. Urutkan menurut ID kategori lalu ID film menaik.

```sql
SELECT c.category_id,c.name,f.film_id,f.title,f.length FROM category c JOIN film_category fc ON fc.category_id=c.category_id JOIN film f ON f.film_id=fc.film_id WHERE f.length=(SELECT MAX(f2.length) FROM film_category fc2 JOIN film f2 ON f2.film_id=fc2.film_id WHERE fc2.category_id=c.category_id) ORDER BY c.category_id,f.film_id
```

Kontrak: 5 kolom; ordered=True; approximate columns=().

Cuplikan hasil referensi bertipe (maksimum 3 baris; hasil lengkap tersedia pada reference_result di CSV):

```json
[[["number", "1"], ["text", "Action"], ["number", "212"], ["text", "DARN FORRESTER"], ["number", "185"]], [["number", "1"], ["text", "Action"], ["number", "991"], ["text", "WORST BANGER"], ["number", "185"]], [["number", "2"], ["text", "Animation"], ["number", "349"], ["text", "GANGS PRIDE"], ["number", "185"]]]
```

## Q028 (main, complex)

Untuk setiap toko tempat pelanggan terdaftar, tampilkan tiga pelanggan dengan total pembayaran tercatat terbesar. Total pelanggan tanpa pembayaran dianggap nol. Jika total sama, dahulukan ID pelanggan lebih kecil. Tampilkan ID toko, ID pelanggan, nama depan, nama belakang, total pembayaran, dan posisi 1 sampai 3. Urutkan menurut ID toko lalu posisi menaik.

```sql
WITH totals AS (SELECT c.store_id,c.customer_id,c.first_name,c.last_name,COALESCE(SUM(p.amount),0) AS total_paid FROM customer c LEFT JOIN payment p ON p.customer_id=c.customer_id GROUP BY c.store_id,c.customer_id,c.first_name,c.last_name), ranked AS (SELECT totals.*,ROW_NUMBER() OVER (PARTITION BY store_id ORDER BY total_paid DESC,customer_id) AS position_in_store FROM totals) SELECT store_id,customer_id,first_name,last_name,total_paid,position_in_store FROM ranked WHERE position_in_store<=3 ORDER BY store_id,position_in_store
```

Kontrak: 6 kolom; ordered=True; approximate columns=().

Cuplikan hasil referensi bertipe (maksimum 3 baris; hasil lengkap tersedia pada reference_result di CSV):

```json
[[["number", "1"], ["number", "148"], ["text", "ELEANOR"], ["text", "HUNT"], ["number", "216.54"], ["number", "1"]], [["number", "1"], ["number", "144"], ["text", "CLARA"], ["text", "SHAW"], ["number", "195.58"], ["number", "2"]], [["number", "1"], ["number", "459"], ["text", "TOMMY"], ["text", "COLLAZO"], ["number", "186.62"], ["number", "3"]]]
```

## Q029 (main, complex)

Untuk setiap toko, pertimbangkan hanya film yang mempunyai salinan inventaris di toko itu. Tampilkan film dengan jumlah transaksi penyewaan di atas rata-rata jumlah penyewaan per film di toko tersebut; film berinventaris tanpa penyewaan dihitung nol. Tampilkan ID toko, ID film, jumlah penyewaan, dan rata-rata tersebut. Urutkan menurut ID toko lalu ID film menaik.

```sql
WITH counts AS (SELECT i.store_id,i.film_id,COUNT(r.rental_id) AS rental_count FROM inventory i LEFT JOIN rental r ON r.inventory_id=i.inventory_id GROUP BY i.store_id,i.film_id), stats AS (SELECT counts.*,AVG(rental_count) OVER (PARTITION BY store_id) AS store_average FROM counts) SELECT store_id,film_id,rental_count,store_average FROM stats WHERE rental_count>store_average ORDER BY store_id,film_id
```

Kontrak: 4 kolom; ordered=True; approximate columns=().

Cuplikan hasil referensi bertipe (maksimum 3 baris; hasil lengkap tersedia pada reference_result di CSV):

```json
[[["number", "1"], ["number", "1"], ["number", "12"], ["number", "10.4387"]], [["number", "1"], ["number", "4"], ["number", "13"], ["number", "10.4387"]], [["number", "1"], ["number", "6"], ["number", "11"], ["number", "10.4387"]]]
```

## Q030 (main, complex)

Untuk setiap bulan pembayaran yang tercatat, tampilkan bulan dalam format YYYY-MM, total nilai pembayaran, dan selisih total terhadap bulan tercatat sebelumnya. Selisih untuk bulan pertama harus NULL. Urutkan menurut bulan menaik.

```sql
WITH monthly AS (SELECT DATE_FORMAT(payment_date,'%Y-%m') AS payment_month,SUM(amount) AS total_paid FROM payment GROUP BY DATE_FORMAT(payment_date,'%Y-%m')) SELECT payment_month,total_paid,total_paid-LAG(total_paid) OVER (ORDER BY payment_month) AS change_from_previous FROM monthly ORDER BY payment_month
```

Kontrak: 3 kolom; ordered=True; approximate columns=().

Cuplikan hasil referensi bertipe (maksimum 3 baris; hasil lengkap tersedia pada reference_result di CSV):

```json
[[["text", "2005-05"], ["number", "4823.44"], ["null"]], [["text", "2005-06"], ["number", "9629.89"], ["number", "4806.45"]], [["text", "2005-07"], ["number", "28368.91"], ["number", "18739.02"]]]
```

## P001 (pilot, simple)

Berapa jumlah bahasa yang tercatat dalam tabel bahasa?

```sql
SELECT COUNT(*) FROM language
```

Kontrak: 1 kolom; ordered=False; approximate columns=().

Cuplikan hasil referensi bertipe (maksimum 3 baris; hasil lengkap tersedia pada reference_result di CSV):

```json
[[["number", "6"]]]
```

## P002 (pilot, simple)

Tampilkan ID film dan judul film dengan tarif sewa yang dikonfigurasi sebesar 0,99. Urutkan menurut ID film menaik.

```sql
SELECT film_id,title FROM film WHERE rental_rate=0.99 ORDER BY film_id
```

Kontrak: 2 kolom; ordered=True; approximate columns=().

Cuplikan hasil referensi bertipe (maksimum 3 baris; hasil lengkap tersedia pada reference_result di CSV):

```json
[[["number", "1"], ["text", "ACADEMY DINOSAUR"]], [["number", "11"], ["text", "ALAMO VIDEOTAPE"]], [["number", "12"], ["text", "ALASKA PHANTOM"]]]
```

## P003 (pilot, simple)

Berapa nilai pembayaran individual terbesar yang tercatat?

```sql
SELECT MAX(amount) FROM payment
```

Kontrak: 1 kolom; ordered=False; approximate columns=().

Cuplikan hasil referensi bertipe (maksimum 3 baris; hasil lengkap tersedia pada reference_result di CSV):

```json
[[["number", "11.99"]]]
```

## P004 (pilot, medium)

Tampilkan ID pelanggan, nama depan, dan alamat jalan untuk lima pelanggan dengan ID terkecil. Urutkan menurut ID pelanggan menaik.

```sql
SELECT c.customer_id,c.first_name,a.address FROM customer c JOIN address a ON a.address_id=c.address_id ORDER BY c.customer_id LIMIT 5
```

Kontrak: 3 kolom; ordered=True; approximate columns=().

Cuplikan hasil referensi bertipe (maksimum 3 baris; hasil lengkap tersedia pada reference_result di CSV):

```json
[[["number", "1"], ["text", "MARY"], ["text", "1913 Hanoi Way"]], [["number", "2"], ["text", "PATRICIA"], ["text", "1121 Loja Avenue"]], [["number", "3"], ["text", "LINDA"], ["text", "692 Joliet Street"]]]
```

## P005 (pilot, medium)

Untuk setiap aktor, tampilkan ID aktor dan jumlah film yang dibintanginya. Sertakan aktor tanpa film dengan jumlah nol. Urutkan menurut ID aktor menaik.

```sql
SELECT a.actor_id,COUNT(fa.film_id) FROM actor a LEFT JOIN film_actor fa ON fa.actor_id=a.actor_id GROUP BY a.actor_id ORDER BY a.actor_id
```

Kontrak: 2 kolom; ordered=True; approximate columns=().

Cuplikan hasil referensi bertipe (maksimum 3 baris; hasil lengkap tersedia pada reference_result di CSV):

```json
[[["number", "1"], ["number", "19"]], [["number", "2"], ["number", "25"]], [["number", "3"], ["number", "22"]]]
```

## P006 (pilot, medium)

Untuk setiap film, tampilkan ID film, judul, dan jumlah salinan inventarisnya pada seluruh toko. Sertakan film tanpa salinan dengan jumlah nol. Urutkan menurut ID film menaik.

```sql
SELECT f.film_id,f.title,COUNT(i.inventory_id) FROM film f LEFT JOIN inventory i ON i.film_id=f.film_id GROUP BY f.film_id,f.title ORDER BY f.film_id
```

Kontrak: 3 kolom; ordered=True; approximate columns=().

Cuplikan hasil referensi bertipe (maksimum 3 baris; hasil lengkap tersedia pada reference_result di CSV):

```json
[[["number", "1"], ["text", "ACADEMY DINOSAUR"], ["number", "8"]], [["number", "2"], ["text", "ACE GOLDFINGER"], ["number", "3"]], [["number", "3"], ["text", "ADAPTATION HOLES"], ["number", "4"]]]
```

## P007 (pilot, complex)

Tampilkan ID pelanggan, nama depan, dan nama belakang pelanggan yang pernah memiliki pembayaran individual lebih dari 10. Urutkan menurut ID pelanggan menaik.

```sql
SELECT c.customer_id,c.first_name,c.last_name FROM customer c WHERE EXISTS (SELECT 1 FROM payment p WHERE p.customer_id=c.customer_id AND p.amount>10) ORDER BY c.customer_id
```

Kontrak: 3 kolom; ordered=True; approximate columns=().

Cuplikan hasil referensi bertipe (maksimum 3 baris; hasil lengkap tersedia pada reference_result di CSV):

```json
[[["number", "2"], ["text", "PATRICIA"], ["text", "JOHNSON"]], [["number", "3"], ["text", "LINDA"], ["text", "WILLIAMS"]], [["number", "12"], ["text", "NANCY"], ["text", "THOMAS"]]]
```

## P008 (pilot, complex)

Tampilkan ID kota, nama kota, dan jumlah pelanggannya untuk kota dengan jumlah pelanggan di atas rata-rata jumlah pelanggan per kota. Sertakan semua kota dan jumlah nol dalam perhitungan rata-rata. Urutkan menurut ID kota menaik.

```sql
WITH city_counts AS (SELECT ci.city_id,ci.city,COUNT(c.customer_id) AS customer_count FROM city ci LEFT JOIN address a ON a.city_id=ci.city_id LEFT JOIN customer c ON c.address_id=a.address_id GROUP BY ci.city_id,ci.city) SELECT city_id,city,customer_count FROM city_counts WHERE customer_count>(SELECT AVG(customer_count) FROM city_counts) ORDER BY city_id
```

Kontrak: 3 kolom; ordered=True; approximate columns=().

Cuplikan hasil referensi bertipe (maksimum 3 baris; hasil lengkap tersedia pada reference_result di CSV):

```json
[[["number", "1"], ["text", "A Coruña (La Coruña)"], ["number", "1"]], [["number", "2"], ["text", "Abha"], ["number", "1"]], [["number", "3"], ["text", "Abu Dhabi"], ["number", "1"]]]
```

## P009 (pilot, complex)

Tampilkan lima bahasa film dengan jumlah transaksi penyewaan salinan film terbanyak. Sertakan bahasa tanpa penyewaan dengan jumlah nol. Tampilkan ID bahasa, nama bahasa, dan jumlah penyewaan. Urutkan jumlah menurun; jika sama, ID bahasa menaik.

```sql
SELECT l.language_id,l.name,COUNT(r.rental_id) AS rental_count FROM language l LEFT JOIN film f ON f.language_id=l.language_id LEFT JOIN inventory i ON i.film_id=f.film_id LEFT JOIN rental r ON r.inventory_id=i.inventory_id GROUP BY l.language_id,l.name ORDER BY rental_count DESC,l.language_id LIMIT 5
```

Kontrak: 3 kolom; ordered=True; approximate columns=().

Cuplikan hasil referensi bertipe (maksimum 3 baris; hasil lengkap tersedia pada reference_result di CSV):

```json
[[["number", "1"], ["text", "English"], ["number", "16044"]], [["number", "2"], ["text", "Italian"], ["number", "0"]], [["number", "3"], ["text", "Japanese"], ["number", "0"]]]
```
