# Lampiran pertanyaan dan reference SQL

Gold hanya untuk evaluator/peneliti, tidak menjadi model input.

## Q102 — simple

Pembayaran tercatat pada berapa tanggal kalender yang berbeda?

```sql
SELECT COUNT(DISTINCT DATE(payment_date)) FROM payment
```

## Q105 — simple

Berapa banyak judul film berbeda dalam persediaan seluruh toko secara keseluruhan?

```sql
SELECT COUNT(DISTINCT film_id) FROM inventory
```

## Q107 — simple

Berapa rata-rata lama satu periode sewa film dalam hari?

```sql
SELECT ROUND(AVG(rental_duration),4) FROM film
```

## Q112 — simple

Ada berapa home store berbeda yang tercatat pada pelanggan?

```sql
SELECT COUNT(DISTINCT store_id) FROM customer
```

## Q114 — simple

Berapa rata-rata biaya penggantian film dalam katalog?

```sql
SELECT ROUND(AVG(replacement_cost),4) FROM film
```

## Q116 — medium

Tampilkan nama setiap kategori film beserta jumlah judul film dalam kategori tersebut.

```sql
SELECT c.name,COUNT(fc.film_id) FROM category c LEFT JOIN film_category fc ON fc.category_id=c.category_id GROUP BY c.category_id
```

## Q117 — medium

Tampilkan nama setiap distrik beserta jumlah alamat yang tercatat di distrik tersebut.

```sql
SELECT district,COUNT(*) FROM address GROUP BY district
```

## Q118 — medium

Tampilkan nama setiap negara beserta jumlah kota yang tercatat di negara tersebut.

```sql
SELECT c.country,COUNT(ci.city_id) FROM country c LEFT JOIN city ci ON ci.country_id=c.country_id GROUP BY c.country_id
```

## Q119 — medium

Tampilkan nomor setiap staf beserta jumlah pelanggan berbeda yang penyewaan filmnya pernah diproses oleh staf tersebut.

```sql
SELECT s.staff_id,COUNT(DISTINCT r.customer_id) FROM staff s LEFT JOIN rental r ON r.staff_id=s.staff_id GROUP BY s.staff_id
```

## Q120 — medium

Berapa rata-rata durasi pemutaran film dalam menit untuk setiap klasifikasi usia penonton? Tampilkan klasifikasi tersebut beserta rata-ratanya.

```sql
SELECT rating,ROUND(AVG(length),4) FROM film GROUP BY rating
```

## Q121 — medium

Tampilkan setiap status keaktifan pelanggan yang tercatat beserta total nilai pembayaran pelanggannya.

```sql
SELECT c.active,SUM(p.amount) FROM customer c LEFT JOIN payment p ON p.customer_id=c.customer_id GROUP BY c.active
```

## Q125 — medium

Sebutkan nama depan yang dimiliki lebih dari satu pemeran, beserta jumlah pemeran untuk masing-masing nama tersebut.

```sql
SELECT first_name,COUNT(DISTINCT actor_id) FROM actor GROUP BY first_name HAVING COUNT(DISTINCT actor_id)>1
```

## Q128 — medium

Tampilkan judul, tarif satu periode sewa, dan lama periode sewa dalam hari untuk semua film dengan tarif satu periode di atas 2.00, urut dari tarif tertinggi.

```sql
SELECT title,rental_rate,rental_duration FROM film WHERE rental_rate>2.00 ORDER BY rental_rate DESC,film_id ASC
```

## Q133 — complex

Sebutkan nama kota tempat tinggal pelanggan yang tercatat tidak aktif, tanpa mengulang nama kota yang sama.

```sql
SELECT DISTINCT ci.city FROM city ci WHERE ci.city_id IN(SELECT a.city_id FROM address a JOIN customer c ON c.address_id=a.address_id WHERE c.active=0)
```

## Q134 — complex

Sebutkan judul semua film yang tidak melibatkan pemeran bernama depan PENELOPE.

```sql
SELECT title FROM film WHERE film_id NOT IN(SELECT film_id FROM film_actor WHERE actor_id IN(SELECT actor_id FROM actor WHERE first_name='PENELOPE'))
```

## Q141 — complex

Untuk satu staf yang paling banyak memproses pembayaran atas penyewaan yang diproses staf lain, tampilkan nomor staf, nomor home store staf, dan jumlah pembayaran tersebut.

```sql
SELECT s.staff_id,s.store_id,COUNT(*) FROM staff s JOIN payment p ON p.staff_id=s.staff_id JOIN rental r ON r.rental_id=p.rental_id WHERE p.staff_id<>r.staff_id GROUP BY s.staff_id ORDER BY COUNT(*) DESC,s.staff_id ASC LIMIT 1
```

## Q143 — complex

Film apa saja yang pernah disewa pelanggan tetapi tidak dimiliki home store pelanggan tersebut? Tampilkan nomor dan judul film, nomor pelanggan, serta nomor home store pelanggan.

```sql
SELECT DISTINCT c.customer_id,c.store_id,f.film_id,f.title FROM customer c JOIN rental r ON r.customer_id=c.customer_id JOIN inventory i ON i.inventory_id=r.inventory_id JOIN film f ON f.film_id=i.film_id WHERE NOT EXISTS(SELECT 1 FROM inventory h WHERE h.store_id=c.store_id AND h.film_id=i.film_id)
```

## Q146 — medium

Sebutkan nomor salinan film yang tersedia untuk disewa menurut ketentuan Sakila.

```sql
SELECT i.inventory_id FROM inventory i LEFT JOIN rental r ON r.inventory_id=i.inventory_id AND r.return_date IS NULL WHERE r.rental_id IS NULL
```

## Q147 — medium

Sebutkan nomor pelanggan yang memenuhi syarat rewards bulanan Sakila pada tanggal acuan 1 Agustus 2005, dengan ambang frekuensi 7 dan ambang nilai pembayaran 20.00.

```sql
SELECT customer_id FROM payment WHERE payment_date>='2005-07-01' AND payment_date<'2005-08-01' GROUP BY customer_id HAVING COUNT(*)>7 AND SUM(amount)>20.00
```

## Q148 — complex

Tampilkan judul setiap film dalam katalog beserta jumlah salinan yang tersedia di toko 1 menurut ketentuan Sakila.

```sql
SELECT f.title,COUNT(CASE WHEN i.inventory_id IS NOT NULL AND r.rental_id IS NULL THEN i.inventory_id END) FROM film f LEFT JOIN inventory i ON i.film_id=f.film_id AND i.store_id=1 LEFT JOIN rental r ON r.inventory_id=i.inventory_id AND r.return_date IS NULL GROUP BY f.film_id
```

## Q149 — complex

Tampilkan nama negara yang memiliki penerima rewards bulanan Sakila beserta jumlah penerima di setiap negara, untuk tanggal acuan 1 Agustus 2005 dengan ambang frekuensi 7 dan ambang nilai pembayaran 20.00.

```sql
SELECT co.country,COUNT(*) FROM customer c JOIN address a ON a.address_id=c.address_id JOIN city ci ON ci.city_id=a.city_id JOIN country co ON co.country_id=ci.country_id WHERE c.customer_id IN(SELECT customer_id FROM payment WHERE payment_date>='2005-07-01' AND payment_date<'2005-08-01' GROUP BY customer_id HAVING COUNT(*)>7 AND SUM(amount)>20.00) GROUP BY co.country_id
```

## Q150 — complex

Untuk setiap pelanggan, tampilkan nomor pelanggan beserta nilai komponen keterlambatan menurut rutin Sakila pada tanggal acuan 1 Maret 2006.

```sql
SELECT c.customer_id,COALESCE(SUM(GREATEST(COALESCE(DATEDIFF(r.return_date,r.rental_date)-CAST(f.rental_duration AS SIGNED),0),0)),0) FROM customer c LEFT JOIN rental r ON r.customer_id=c.customer_id AND r.rental_date<='2006-03-01 00:00:00' LEFT JOIN inventory i ON i.inventory_id=r.inventory_id LEFT JOIN film f ON f.film_id=i.film_id GROUP BY c.customer_id
```

## Q151 — complex

Sebutkan nomor penyewaan yang memberikan komponen keterlambatan positif menurut rutin Sakila pada tanggal acuan 1 Maret 2006, beserta nomor pelanggan dan nilai komponen tersebut.

```sql
SELECT r.rental_id,r.customer_id,DATEDIFF(r.return_date,r.rental_date)-f.rental_duration FROM rental r JOIN inventory i ON i.inventory_id=r.inventory_id JOIN film f ON f.film_id=i.film_id WHERE r.rental_date<='2006-03-01 00:00:00' AND DATEDIFF(r.return_date,r.rental_date)>f.rental_duration
```

## Q152 — complex

Tampilkan nomor dan nama depan sepuluh pelanggan dengan ragam kategori film sewaan terbanyak di antara pelanggan yang pernah menyewa film dari sedikitnya tiga kategori berbeda, beserta jumlah kategori dan jumlah judul film berbeda yang pernah disewa. Dahulukan jumlah kategori terbanyak, lalu jumlah judul terbanyak.

```sql
SELECT c.customer_id,c.first_name,COUNT(DISTINCT fc.category_id),COUNT(DISTINCT i.film_id) FROM customer c JOIN rental r ON r.customer_id=c.customer_id JOIN inventory i ON i.inventory_id=r.inventory_id LEFT JOIN film_category fc ON fc.film_id=i.film_id GROUP BY c.customer_id HAVING COUNT(DISTINCT fc.category_id)>=3 ORDER BY COUNT(DISTINCT fc.category_id) DESC,COUNT(DISTINCT i.film_id) DESC,c.customer_id ASC LIMIT 10
```

## Q154 — complex

Tampilkan nomor, nama depan, dan nama belakang pemeran beserta nomor dan nama setiap kategori film yang pernah dibintanginya.

```sql
SELECT DISTINCT a.actor_id,a.first_name,a.last_name,c.category_id,c.name FROM actor a JOIN film_actor fa ON fa.actor_id=a.actor_id JOIN film_category fc ON fc.film_id=fa.film_id JOIN category c ON c.category_id=fc.category_id
```

## Q155 — simple

Berapa banyak film yang durasi pemutarannya lebih dari dua jam?

```sql
SELECT COUNT(*) FROM film WHERE length>120
```

## Q156 — simple

Berapa banyak pelanggan yang tercatat tidak aktif?

```sql
SELECT COUNT(*) FROM customer WHERE active=0
```

## Q157 — simple

Sebutkan nomor semua pelanggan dengan home store 1.

```sql
SELECT customer_id FROM customer WHERE store_id=1
```

## Q159 — simple

Berapa banyak pembayaran yang nilainya melebihi 10.00?

```sql
SELECT COUNT(*) FROM payment WHERE amount>10.00
```

## Q160 — simple

Sebutkan judul semua film dengan klasifikasi usia PG-13.

```sql
SELECT title FROM film WHERE rating='PG-13'
```
