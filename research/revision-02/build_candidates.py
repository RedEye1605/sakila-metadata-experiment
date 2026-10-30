"""Explicit AI-assisted authoring draft. No LLM inference, selection or approval.

Every text is an authored analytical request. The SQL alongside it is first
reference author A; author B receives a separate question-only packet.
"""
from __future__ import annotations

import json
from collections import Counter
from pathlib import Path

from sakila_experiment.artifacts import canonical_json, sha256_bytes
from sakila_experiment.evaluation.structure import profile_sql

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "data/benchmarks/revision-02"

# need, question, canonical SQL, output labels, grain, key facts, family
ITEMS = [
    ("schema_mapping", "Berapa banyak alamat yang kode posnya tidak diisi (NULL)?", "SELECT COUNT(*) FROM address WHERE postal_code IS NULL", ["jumlah_alamat"], "Satu ringkasan seluruh alamat tanpa kode pos", ["local:address.postal_code"], "missing-postal-code"),
    ("schema_mapping", "Pada berapa tanggal kalender berbeda terdapat pembayaran yang diproses? Gunakan komponen tanggal yang tersimpan tanpa konversi zona waktu.", "SELECT COUNT(DISTINCT DATE(payment_date)) FROM payment", ["jumlah_tanggal"], "Satu hitungan tanggal kalender berbeda", ["local:payment.payment_date"], "observed-payment-date-cardinality"),
    ("schema_mapping", "Tampilkan kode rating penonton yang terdapat dalam katalog film, masing-masing satu kali. Abaikan rating NULL. Urutan baris bebas.", "SELECT DISTINCT rating FROM film WHERE rating IS NOT NULL", ["rating"], "Satu baris per kode rating yang ada", ["local:film.rating"], "observed-rating-domain"),
    ("schema_mapping", "Berapa tahun rilis paling awal yang tercatat pada katalog film? Abaikan tahun yang NULL.", "SELECT MIN(release_year) FROM film", ["tahun_terawal"], "Satu minimum tahun rilis non-NULL", ["local:film.release_year"], "catalog-release-boundary"),
    ("schema_mapping", "Berapa banyak ID judul film berbeda yang tercatat dalam inventaris seluruh toko?", "SELECT COUNT(DISTINCT film_id) FROM inventory", ["jumlah_judul"], "Satu hitungan film_id berbeda dalam inventaris", ["local:inventory.film_id"], "stocked-catalog-cardinality"),
    ("schema_mapping", "Tampilkan nama distrik pada rekaman alamat selain string kosong, masing-masing satu kali. Jangan melakukan pemangkasan spasi atau normalisasi teks tambahan. Urutan baris bebas.", "SELECT DISTINCT district FROM address WHERE district <> ''", ["district"], "Satu baris per nama distrik nonempty", ["local:address.district"], "address-district-domain"),
    ("local_semantics", "Berapa rerata lama periode sewa yang dikonfigurasi pada katalog film, dalam hari? Tampilkan empat angka desimal.", "SELECT ROUND(AVG(rental_duration),4) FROM film", ["rerata_hari"], "Satu rerata periode per judul katalog", ["local:film.rental_duration"], "configured-period-mean"),
    ("local_semantics", "Berapa total durasi pemutaran seluruh judul film dalam jam? Abaikan durasi NULL dan tampilkan empat angka desimal.", "SELECT ROUND(SUM(length)/60,4) FROM film", ["total_jam"], "Satu jumlah durasi per judul, dikonversi ke jam", ["local:film.length"], "catalog-runtime-volume"),
    ("local_semantics", "Berapa rerata panjang sinopsis film dalam jumlah karakter? Abaikan sinopsis NULL, hitung string kosong sebagai nol karakter, dan tampilkan empat angka desimal.", "SELECT ROUND(AVG(CHAR_LENGTH(description)),4) FROM film", ["rerata_karakter"], "Satu rerata panjang teks sinopsis non-NULL", ["local:film.description"], "synopsis-character-length"),
    ("local_semantics", "Berapa nominal terbesar untuk satu kejadian pembayaran yang tercatat?", "SELECT MAX(amount) FROM payment", ["nominal_terbesar"], "Satu maksimum nominal kejadian pembayaran", ["local:payment.amount"], "payment-event-maximum"),
    ("local_semantics", "Berapa banyak durasi pemutaran film berbeda yang tercatat dalam satuan menit? Abaikan durasi NULL.", "SELECT COUNT(DISTINCT length) FROM film", ["jumlah_durasi"], "Satu hitungan durasi pemutaran berbeda", ["local:film.length"], "runtime-value-cardinality"),
    ("domain_integration", "Berapa banyak home store berbeda yang dirujuk pada rekaman pelanggan?", "SELECT COUNT(DISTINCT store_id) FROM customer", ["jumlah_home_store"], "Satu hitungan home store pada master pelanggan", ["domain:customer-home"], "customer-home-store-cardinality"),
    ("domain_integration", "Berapa nominal tarif katalog terendah untuk satu periode sewa film?", "SELECT MIN(rental_rate) FROM film", ["tarif_periode_terendah"], "Satu minimum tarif yang berlaku untuk periode katalog", ["domain:rate-period"], "configured-period-rate-minimum"),
    ("domain_integration", "Berapa rerata nominal biaya penggantian film yang ditetapkan pada katalog? Tampilkan empat angka desimal.", "SELECT ROUND(AVG(replacement_cost),4) FROM film", ["rerata_biaya_penggantian"], "Satu rerata nominal konfigurasi penggantian per judul", ["domain:replacement-trigger"], "replacement-charge-configuration"),
    ("domain_integration", "Berapa banyak bahasa asli berbeda yang telah dicatat untuk versi film alih suara? Abaikan referensi bahasa asli yang NULL.", "SELECT COUNT(DISTINCT original_language_id) FROM film", ["jumlah_bahasa_asli"], "Satu hitungan bahasa asli non-NULL", ["domain:original-language-dubbing"], "dubbed-original-language-cardinality"),
    ("schema_mapping", "Untuk setiap ID kategori yang memiliki hubungan ke film, tampilkan ID kategori dan banyaknya judul film yang menjadi anggotanya. Urutan baris bebas.", "SELECT category_id,COUNT(*) FROM film_category GROUP BY category_id", ["category_id", "jumlah_judul"], "Satu baris per kategori dengan keanggotaan", ["local:film_category"], "category-membership-volume"),
    ("schema_mapping", "Untuk setiap distrik yang ada pada alamat, tampilkan nama distrik dan banyaknya rekaman alamat di distrik itu. String distrik kosong tetap merupakan kelompok tersendiri. Urutan baris bebas.", "SELECT district,COUNT(*) FROM address GROUP BY district", ["district", "jumlah_alamat"], "Satu baris per nilai distrik, termasuk string kosong", ["local:address.district"], "district-address-volume"),
    ("schema_mapping", "Untuk setiap negara, tampilkan ID negara, namanya, dan banyaknya kota yang terdaftar di negara itu. Sertakan negara tanpa kota dengan jumlah nol. Urutan baris bebas.", "SELECT c.country_id,c.country,COUNT(ci.city_id) FROM country c LEFT JOIN city ci ON ci.country_id=c.country_id GROUP BY c.country_id", ["country_id", "country", "jumlah_kota"], "Satu baris per negara termasuk yang tanpa kota", ["local:city.country_id"], "country-city-population"),
    ("schema_mapping", "Untuk setiap ID staf yang tercatat memproses penyewaan, tampilkan ID staf dan banyaknya pelanggan berbeda yang pernah dilayaninya pada catatan penyewaan. Urutan baris bebas.", "SELECT staff_id,COUNT(DISTINCT customer_id) FROM rental GROUP BY staff_id", ["staff_id", "jumlah_pelanggan"], "Satu baris per rental staff dengan pelanggan berbeda", ["local:rental.staff_id"], "rental-processor-customer-reach"),
    ("local_semantics", "Untuk setiap kode rating yang memiliki film dengan durasi pemutaran diketahui, tampilkan kode rating dan rerata durasi pemutaran film dalam menit dengan empat angka desimal. Rating NULL tetap menjadi kelompok tersendiri. Urutan baris bebas.", "SELECT rating,ROUND(AVG(length),4) FROM film WHERE length IS NOT NULL GROUP BY rating", ["rating", "rerata_menit"], "Satu baris per rating dengan durasi diketahui", ["local:film.length"], "rating-runtime-mean"),
    ("local_semantics", "Untuk setiap status aktif yang tercatat pada pelanggan, tampilkan nilai status tersebut dan total nominal pembayaran pelanggan dalam kelompoknya. Pelanggan tanpa pembayaran tetap termasuk, dengan kontribusi nol. Urutan baris bebas.", "SELECT c.active,COALESCE(SUM(p.amount),0) FROM customer c LEFT JOIN payment p ON p.customer_id=c.customer_id GROUP BY c.active", ["active", "total_nominal"], "Satu baris per nilai status pelanggan yang ada", ["local:customer.active", "local:payment.amount"], "customer-status-receipt-volume"),
    ("local_semantics", "Untuk setiap toko yang memiliki inventaris, tampilkan ID toko, banyaknya judul film berbeda, dan banyaknya salinan fisik inventaris. Urutan baris bebas.", "SELECT store_id,COUNT(DISTINCT film_id),COUNT(*) FROM inventory GROUP BY store_id", ["store_id", "jumlah_judul", "jumlah_salinan"], "Satu baris per toko dengan inventaris", ["detail:inventory"], "inventory-title-copy-grains"),
    ("local_semantics", "Untuk setiap kombinasi tanggal kalender dan staf pemroses pembayaran yang tercatat, tampilkan tanggal tersebut, ID staf, dan banyaknya kejadian pembayaran. Gunakan tanggal tersimpan tanpa konversi zona waktu; jangan menambah kombinasi yang tidak ada. Urutan baris bebas.", "SELECT DATE(payment_date),staff_id,COUNT(*) FROM payment GROUP BY DATE(payment_date),staff_id", ["tanggal", "staff_id", "jumlah_kejadian"], "Satu baris per observed payment date/staff", ["detail:payment", "detail:payment.payment_date", "local:payment.staff_id"], "processor-date-payment-volume"),
    ("local_semantics", "Untuk setiap salinan inventaris, tampilkan ID salinan dan banyaknya kejadian penyewaannya. Sertakan salinan yang belum pernah disewa dengan jumlah nol. Urutan baris bebas.", "SELECT i.inventory_id,COUNT(r.rental_id) FROM inventory i LEFT JOIN rental r ON r.inventory_id=i.inventory_id GROUP BY i.inventory_id", ["inventory_id", "jumlah_penyewaan"], "Satu baris per salinan termasuk tanpa rental", ["detail:inventory", "detail:rental"], "copy-rental-frequency"),
    ("local_semantics", "Tampilkan nama depan pemeran yang dipakai oleh lebih dari satu ID pemeran, beserta banyaknya ID pemeran yang memakai nama itu. Urutan baris bebas.", "SELECT first_name,COUNT(DISTINCT actor_id) FROM actor GROUP BY first_name HAVING COUNT(DISTINCT actor_id)>1", ["first_name", "jumlah_aktor"], "Satu baris per nama depan dengan beberapa aktor", ["local:actor.first_name", "local:actor.actor_id"], "actor-name-identity-collisions"),
    ("domain_integration", "Untuk setiap home store yang tercatat pada pelanggan, tampilkan ID home store dan banyaknya kota tempat tinggal pelanggan yang berbeda. Kota mengikuti alamat pelanggan pada snapshot. Urutan baris bebas.", "SELECT c.store_id,COUNT(DISTINCT a.city_id) FROM customer c JOIN address a ON a.address_id=c.address_id GROUP BY c.store_id", ["home_store_id", "jumlah_kota"], "Satu baris per customer home store", ["domain:customer-home"], "home-store-customer-geographic-reach"),
    ("domain_integration", "Untuk setiap home store staf, tampilkan ID home store dan total nominal pembayaran yang diproses staf yang memiliki home store tersebut. Sertakan home store staf tanpa pembayaran dengan total nol. Urutan baris bebas.", "SELECT s.store_id,COALESCE(SUM(p.amount),0) FROM staff s LEFT JOIN payment p ON p.staff_id=s.staff_id GROUP BY s.store_id", ["home_store_id", "total_nominal"], "Satu baris per observed staff home store", ["domain:staff-home", "domain:staff-cross-store"], "staff-home-store-receipt-volume"),
    ("domain_integration", "Tampilkan ID film, biaya dasar untuk satu periode sewa katalog, dan lama periode tersebut dalam hari, untuk film dengan biaya dasar lebih dari 2.00. Urutan baris bebas.", "SELECT film_id,rental_rate,rental_duration FROM film WHERE rental_rate>2.00", ["film_id", "tarif_periode", "periode_hari"], "Satu baris per judul dengan biaya periode di atas batas", ["domain:rate-period"], "configured-period-cost-schedule"),
    ("domain_integration", "Untuk setiap bahasa yang terdaftar, tampilkan ID bahasa, nama bahasa, dan banyaknya judul versi alih suara yang mencatat bahasa tersebut sebagai bahasa aslinya. Sertakan bahasa tanpa judul terkait dengan jumlah nol. Urutan baris bebas.", "SELECT l.language_id,l.name,COUNT(f.film_id) FROM language l LEFT JOIN film f ON f.original_language_id=l.language_id GROUP BY l.language_id", ["language_id", "name", "jumlah_judul"], "Satu baris per original language including zero titles", ["domain:original-language-dubbing"], "original-language-dubbed-catalog-coverage"),
    ("domain_integration", "Untuk setiap status aktif pelanggan yang mempunyai riwayat penyewaan, tampilkan status yang tercatat dan banyaknya pelanggan berbeda yang pernah menyewa. Sertakan riwayat pelanggan yang rekamannya telah dinonaktifkan. Urutan baris bebas.", "SELECT c.active,COUNT(DISTINCT r.customer_id) FROM customer c JOIN rental r ON r.customer_id=c.customer_id GROUP BY c.active", ["active", "jumlah_pelanggan"], "Satu baris per recorded customer status among rental participants", ["domain:customer-retention"], "retained-customer-rental-participation"),
    ("schema_mapping", "Tampilkan ID film beserta judulnya untuk film yang memiliki catatan penyewaan mulai 1 Juli 2005 sampai sebelum 1 Agustus 2005. Setiap film ditampilkan satu kali. Urutan baris bebas.", "SELECT DISTINCT f.film_id,f.title FROM film f JOIN inventory i ON i.film_id=f.film_id JOIN rental r ON r.inventory_id=i.inventory_id WHERE r.rental_date>='2005-07-01' AND r.rental_date<'2005-08-01'", ["film_id", "title"], "Satu baris per judul yang dirental dalam interval", ["local:rental.rental_date", "local:rental.inventory_id"], "monthly-rented-catalog-membership"),
    ("schema_mapping", "Tampilkan ID film yang mempunyai setidaknya satu pemeran dengan ID 1 dan setidaknya satu keanggotaan kategori dengan ID 1. Urutan baris bebas.", "SELECT f.film_id FROM film f WHERE EXISTS(SELECT 1 FROM film_actor fa WHERE fa.film_id=f.film_id AND fa.actor_id=1) AND EXISTS(SELECT 1 FROM film_category fc WHERE fc.film_id=f.film_id AND fc.category_id=1)", ["film_id"], "Satu baris per judul yang memenuhi dua keanggotaan", ["local:film_actor", "local:film_category"], "joint-actor-category-membership"),
    ("schema_mapping", "Tampilkan ID kota berbeda yang menjadi alamat pelanggan dengan status aktif bernilai 0 pada snapshot. Urutan baris bebas.", "SELECT DISTINCT city_id FROM address WHERE address_id IN(SELECT address_id FROM customer WHERE active=0)", ["city_id"], "Satu baris per kota yang memiliki pelanggan inactive", ["local:customer.active", "local:customer.address_id"], "inactive-customer-city-coverage"),
    ("schema_mapping", "Tampilkan ID film yang tidak mempunyai pemeran dengan nama depan PENELOPE. Film tanpa pemeran juga disertakan. Urutan baris bebas.", "SELECT film_id FROM film WHERE film_id NOT IN(SELECT film_id FROM film_actor WHERE actor_id IN(SELECT actor_id FROM actor WHERE first_name='PENELOPE'))", ["film_id"], "Satu baris per judul tanpa matching actor", ["local:film_actor", "local:actor.first_name"], "actor-name-catalog-exclusion"),
    ("schema_mapping", "Tampilkan lima ID kategori dengan banyaknya judul film anggota terbanyak. Pertimbangkan hanya kategori yang mempunyai anggota. Urutkan jumlah anggota menurun, lalu ID kategori menaik untuk memutus seri.", "SELECT category_id FROM film_category GROUP BY category_id ORDER BY COUNT(*) DESC,category_id ASC LIMIT 5", ["category_id"], "Maksimal lima kategori dengan deterministic title-count ranking", ["local:film_category"], "catalog-category-top-k"),
    ("local_semantics", "Tampilkan ID pembayaran yang nominalnya melebihi rerata nominal pembayaran yang diproses staf yang sama. Bandingkan terhadap rerata sebelum pembulatan; tidak perlu menampilkan reratanya. Urutan baris bebas.", "SELECT p.payment_id FROM payment p WHERE p.amount>(SELECT AVG(x.amount) FROM payment x WHERE x.staff_id=p.staff_id)", ["payment_id"], "Satu baris per event di atas mean processor-nya", ["local:payment.amount", "local:payment.staff_id"], "processor-relative-payment-outliers"),
    ("local_semantics", "Tampilkan ID penyewaan dengan waktu pengembalian tercatat lebih dari lama periode sewa katalog filmnya setelah waktu penyewaan. Satu hari dihitung 24 jam; gunakan selisih detik yang tersimpan dan abaikan pengembalian NULL. Ini perbandingan waktu, bukan penetapan denda. Urutan baris bebas.", "SELECT r.rental_id FROM rental r JOIN inventory i ON i.inventory_id=r.inventory_id JOIN film f ON f.film_id=i.film_id WHERE r.return_date IS NOT NULL AND TIMESTAMPDIFF(SECOND,r.rental_date,r.return_date)>f.rental_duration*86400", ["rental_id"], "Satu baris per rental dengan elapsed time lebih panjang dari periode", ["local:film.rental_duration", "local:rental.rental_date", "local:rental.return_date"], "recorded-elapsed-configured-period-comparison"),
    ("local_semantics", "Untuk setiap tanggal kalender dan staf pemroses pembayaran yang tercatat, tampilkan tanggal, ID staf, banyaknya kejadian pembayaran, serta total nominalnya. Jangan menambah kombinasi tanpa pembayaran. Urutkan tanggal lalu ID staf menaik.", "SELECT DATE(payment_date),staff_id,COUNT(*),SUM(amount) FROM payment GROUP BY DATE(payment_date),staff_id ORDER BY DATE(payment_date),staff_id", ["tanggal", "staff_id", "jumlah_kejadian", "total_nominal"], "Satu baris per observed payment date/staff dengan dua measures", ["detail:payment", "detail:payment.payment_date", "local:payment.staff_id"], "processor-date-payment-measure-mix"),
    ("local_semantics", "Untuk setiap kombinasi toko inventaris dan rating yang memiliki salinan, tampilkan ID toko, rating, banyaknya salinan, dan total durasi pemutaran semua salinan tersebut dalam menit. Durasi satu judul dihitung sekali untuk setiap salinannya; abaikan durasi NULL dalam penjumlahan; jika semua durasi dalam kelompok NULL, total durasinya NULL. Rating NULL tetap menjadi kelompok tersendiri. Urutkan ID toko menaik lalu kode rating secara leksikografis menaik, dengan rating NULL di awal.", "SELECT i.store_id,f.rating,COUNT(*),SUM(f.length) FROM inventory i JOIN film f ON f.film_id=i.film_id GROUP BY i.store_id,f.rating ORDER BY i.store_id,CAST(f.rating AS CHAR)", ["store_id", "rating", "jumlah_salinan", "total_menit"], "Satu baris per observed inventory-store/rating", ["detail:inventory", "local:film.length"], "store-rating-copy-runtime-volume"),
    ("domain_integration", "Tampilkan ID pelanggan dan banyaknya kejadian penyewaan atas salinan yang toko inventarisnya berbeda dari home store pelanggan, untuk pelanggan dengan sedikitnya dua kejadian demikian. Gunakan asosiasi toko pada snapshot, tanpa merekonstruksi lokasi historis salinan. Urutkan ID pelanggan menaik.", "SELECT c.customer_id,COUNT(*) FROM customer c JOIN rental r ON r.customer_id=c.customer_id JOIN inventory i ON i.inventory_id=r.inventory_id WHERE i.store_id<>c.store_id GROUP BY c.customer_id HAVING COUNT(*)>=2 ORDER BY c.customer_id", ["customer_id", "jumlah_kejadian"], "Satu baris per pelanggan dengan sedikitnya dua cross-store associations", ["domain:customer-home", "domain:customer-cross-store"], "cross-home-store-rental-frequency"),
    ("domain_integration", "Untuk setiap staf yang memproses pembayaran atas penyewaan yang diproses staf lain, tampilkan ID staf pembayaran, home store staf pembayaran, dan banyaknya kejadian pembayaran demikian. Hitung payment events, bukan rental berbeda. Urutkan ID staf pembayaran menaik.", "SELECT s.staff_id,s.store_id,COUNT(*) FROM staff s JOIN payment p ON p.staff_id=s.staff_id JOIN rental r ON r.rental_id=p.rental_id WHERE p.staff_id<>r.staff_id GROUP BY s.staff_id ORDER BY s.staff_id", ["staff_id", "home_store_id", "jumlah_pembayaran"], "Satu baris per payment processor pada role mismatch", ["domain:staff-home", "local:payment.staff_id", "local:rental.staff_id"], "payment-rental-processor-role-mismatch"),
    ("domain_integration", "Pada setiap kelompok rating yang ada, tampilkan ID film, rating, dan konfigurasi biaya penggantian untuk film yang berada pada tiga nilai biaya penggantian tertinggi yang berbeda. Sertakan semua film seri pada nilai biaya tersebut; rating NULL merupakan kelompok tersendiri. Urutkan kode rating secara leksikografis menaik dengan rating NULL di awal, biaya menurun, lalu ID film menaik.", "SELECT f.film_id,f.rating,f.replacement_cost FROM film f WHERE (SELECT COUNT(DISTINCT g.replacement_cost) FROM film g WHERE g.rating<=>f.rating AND g.replacement_cost>f.replacement_cost)<3 ORDER BY CAST(f.rating AS CHAR),f.replacement_cost DESC,f.film_id", ["film_id", "rating", "biaya_penggantian"], "Semua judul pada tiga distinct charge levels per rating", ["domain:replacement-trigger", "domain:configured-not-collected"], "replacement-charge-dense-ranking"),
    ("domain_integration", "Tampilkan kombinasi ID pelanggan, home store pelanggan, dan ID judul film yang pernah disewanya, apabila judul tersebut tidak mempunyai salinan inventaris pada home store pelanggan di snapshot saat ini. Hilangkan kombinasi duplikat. Gunakan asosiasi toko sekarang, tanpa asumsi tentang perpindahan inventaris masa lalu. Urutkan ID pelanggan lalu ID film menaik.", "SELECT DISTINCT c.customer_id,c.store_id,i.film_id FROM customer c JOIN rental r ON r.customer_id=c.customer_id JOIN inventory i ON i.inventory_id=r.inventory_id WHERE NOT EXISTS(SELECT 1 FROM inventory h WHERE h.store_id=c.store_id AND h.film_id=i.film_id) ORDER BY c.customer_id,i.film_id", ["customer_id", "home_store_id", "film_id"], "Satu kombinasi unik customer/home/catalog absence", ["domain:customer-home", "domain:customer-cross-store", "detail:inventory"], "home-store-catalog-gap-among-rentals"),
    ("domain_integration", "Untuk setiap home store staf, tampilkan ID home store, total nominal pembayaran yang diproses staf dengan status aktif bernilai 1, dan total yang diproses staf dengan status aktif bernilai 0. Sertakan home store staf tanpa pembayaran dengan nilai nol. Status mengikuti rekaman snapshot; jangan menganggapnya status saat pembayaran terjadi. Urutkan ID home store menaik.", "SELECT s.store_id,COALESCE(SUM(CASE WHEN s.active=1 THEN p.amount ELSE 0 END),0),COALESCE(SUM(CASE WHEN s.active=0 THEN p.amount ELSE 0 END),0) FROM staff s LEFT JOIN payment p ON p.staff_id=s.staff_id GROUP BY s.store_id ORDER BY s.store_id", ["home_store_id", "total_aktif", "total_tidak_aktif"], "Satu baris per staff home store dengan current recorded status measures", ["domain:staff-home", "domain:staff-retention"], "retained-staff-home-store-payment-history"),
    ("domain_integration", "Tampilkan ID film dengan tarif katalog untuk satu periode sewa tertinggi di antara film yang lama periode sewanya sama. Sertakan semua film seri. Gunakan nominal tarif untuk satu periode tersebut. Urutan baris bebas.", "SELECT f.film_id FROM film f WHERE NOT EXISTS(SELECT 1 FROM film g WHERE g.rental_duration=f.rental_duration AND g.rental_rate>f.rental_rate)", ["film_id"], "Semua judul dengan maximum configured rate per equal period", ["domain:rate-period", "domain:rate-not-receipt"], "equal-period-rate-maxima"),
]

# Prospective amendment: natural user requests; definitions live in metadata.
# Column sequence remains explicit. Other answer contracts stay evaluator-side
# or in common output instructions, never question-specific SQL hints.
NATURAL_REQUESTS = [
    "Berapa banyak alamat yang belum memiliki kode pos?",
    "Pembayaran tercatat pada berapa tanggal kalender yang berbeda?",
    "Kode rating penonton apa saja yang ada di katalog film?",
    "Tahun berapa film paling awal dalam katalog dirilis?",
    "Berapa banyak judul film berbeda yang dimiliki inventaris seluruh toko?",
    "Nama distrik apa saja yang terisi pada alamat?",
    "Berapa rata-rata lama periode sewa film?",
    "Berapa total durasi pemutaran seluruh judul film dalam jam?",
    "Berapa rata-rata panjang sinopsis film dalam karakter?",
    "Berapa nominal terbesar untuk satu pembayaran?",
    "Ada berapa nilai durasi pemutaran film yang berbeda?",
    "Ada berapa home store berbeda pada pelanggan?",
    "Berapa tarif terendah untuk satu periode sewa film?",
    "Berapa rata-rata biaya penggantian film dalam katalog?",
    "Ada berapa bahasa asli berbeda yang tercatat untuk film alih suara?",
    "Berapa banyak judul film anggota masing-masing kategori?",
    "Berapa banyak alamat di masing-masing distrik?",
    "Berapa banyak kota yang dimiliki masing-masing negara?",
    "Berapa banyak pelanggan berbeda yang pernah dilayani setiap staf pemroses penyewaan?",
    "Berapa rata-rata durasi pemutaran film untuk masing-masing rating?",
    "Bagaimana total nominal pembayaran pelanggan menurut status aktifnya?",
    "Berapa banyak judul film berbeda dan salinan fisik di masing-masing toko?",
    "Berapa banyak pembayaran yang diproses masing-masing staf pada setiap tanggal?",
    "Berapa kali masing-masing salinan inventaris pernah disewa?",
    "Nama depan pemeran mana yang dipakai oleh lebih dari satu pemeran?",
    "Seberapa luas jangkauan kota tempat tinggal pelanggan di masing-masing home store?",
    "Berapa total nominal pembayaran yang diproses staf dari masing-masing home store?",
    "Film apa saja yang tarif satu periode sewanya lebih dari 2.00, dan berapa lama periodenya?",
    "Berapa banyak film alih suara yang tercatat untuk masing-masing bahasa asli?",
    "Berapa banyak pelanggan yang pernah menyewa menurut status aktif yang tercatat?",
    "Film apa saja yang mulai disewa selama Juli 2005?",
    "Film mana yang melibatkan pemeran ber-ID 1 dan termasuk kategori ber-ID 1?",
    "Di kota mana saja pelanggan berstatus aktif 0 tinggal?",
    "Film apa saja yang tidak melibatkan pemeran bernama depan PENELOPE?",
    "Apa lima kategori dengan jumlah judul film anggota terbanyak?",
    "Pembayaran mana yang nominalnya melebihi rata-rata pembayaran yang diproses staf yang sama?",
    "Penyewaan mana yang lama peminjamannya melewati periode sewa katalog?",
    "Bagaimana banyaknya pembayaran dan total nominal yang diproses masing-masing staf pada setiap tanggal?",
    "Berapa banyak DVD dan total durasi pemutarannya untuk masing-masing toko dan rating?",
    "Pelanggan mana yang tercatat menyewa di luar home store sedikitnya dua kali?",
    "Staf mana yang memproses pembayaran untuk penyewaan yang diproses staf lain?",
    "Film mana yang biaya penggantiannya berada pada tiga tingkat harga tertinggi di masing-masing rating?",
    "Judul apa saja yang pernah disewa pelanggan tetapi tidak dimiliki inventaris home store pelanggan itu?",
    "Bagaimana total nominal pembayaran menurut home store staf serta status aktif staf yang tercatat?",
    "Film mana yang memiliki tarif satu periode sewa tertinggi untuk lama periode yang sama?",
]

EXTRA_ITEMS = [
    ("domain_integration", "Salinan inventaris mana saja yang tersedia menurut ketentuan Sakila?",
     "SELECT i.inventory_id FROM inventory i LEFT JOIN rental r ON r.inventory_id=i.inventory_id AND r.return_date IS NULL WHERE r.rental_id IS NULL",
     ["inventory_id"], "Satu baris per existing available copy; never-rented included", ["domain:stock-availability"], "stock-available-copy-membership"),
    ("domain_integration", "Pelanggan mana yang lolos rewards bulanan Sakila pada tanggal acuan 1 Agustus 2005, dengan ambang frekuensi 7 dan ambang nominal 20.00?",
     "SELECT customer_id FROM payment WHERE payment_date>='2005-07-01' AND payment_date<'2005-08-01' GROUP BY customer_id HAVING COUNT(*)>7 AND SUM(amount)>20.00",
     ["customer_id"], "Satu baris per eligible customer under frozen reporting clock", ["domain:rewards-period", "domain:rewards-event-grain", "domain:rewards-strict-both", "domain:rewards-no-active-filter"], "monthly-rewards-eligible-membership"),
    ("domain_integration", "Berapa banyak salinan tersedia di toko 1 untuk masing-masing judul katalog menurut ketentuan Sakila?",
     "SELECT f.film_id,COUNT(CASE WHEN i.inventory_id IS NOT NULL AND r.rental_id IS NULL THEN i.inventory_id END) FROM film f LEFT JOIN inventory i ON i.film_id=f.film_id AND i.store_id=1 LEFT JOIN rental r ON r.inventory_id=i.inventory_id AND r.return_date IS NULL GROUP BY f.film_id",
     ["film_id", "jumlah_salinan_tersedia"], "Satu baris per catalog title, availability at store1 including zero holdings", ["domain:stock-availability", "domain:stock-snapshot"], "catalog-stock-availability-coverage"),
    ("domain_integration", "Negara mana yang memiliki penerima rewards bulanan Sakila dan berapa banyak pelanggannya, untuk tanggal acuan 1 Agustus 2005 dengan ambang frekuensi 7 dan ambang nominal 20.00?",
     "SELECT co.country_id,COUNT(*) FROM customer c JOIN address a ON a.address_id=c.address_id JOIN city ci ON ci.city_id=a.city_id JOIN country co ON co.country_id=ci.country_id WHERE c.customer_id IN(SELECT customer_id FROM payment WHERE payment_date>='2005-07-01' AND payment_date<'2005-08-01' GROUP BY customer_id HAVING COUNT(*)>7 AND SUM(amount)>20.00) GROUP BY co.country_id",
     ["country_id", "jumlah_penerima"], "Satu baris per country with eligible customers at current customer addresses", ["domain:rewards-period", "domain:rewards-event-grain", "domain:rewards-strict-both", "domain:rewards-no-active-filter"], "monthly-rewards-country-distribution"),
    ("domain_integration", "Berapa komponen keterlambatan masing-masing pelanggan menurut definisi rutin Sakila dengan tanggal acuan 1 Maret 2006?",
     "SELECT c.customer_id,COALESCE(SUM(GREATEST(COALESCE(DATEDIFF(r.return_date,r.rental_date)-f.rental_duration,0),0)),0) FROM customer c LEFT JOIN rental r ON r.customer_id=c.customer_id AND r.rental_date<='2006-03-01 00:00:00' LEFT JOIN inventory i ON i.inventory_id=r.inventory_id LEFT JOIN film f ON f.film_id=i.film_id GROUP BY c.customer_id",
     ["customer_id", "komponen_keterlambatan"], "Satu baris per customer, returned-rental executable late component only", ["domain:late-calendar-excess", "domain:late-null-return", "domain:late-start-cutoff"], "legacy-returned-late-component-by-customer"),
    ("domain_integration", "Penyewaan mana yang menyumbang komponen keterlambatan positif menurut definisi rutin Sakila dengan tanggal acuan 1 Maret 2006?",
     "SELECT r.rental_id,r.customer_id,DATEDIFF(r.return_date,r.rental_date)-f.rental_duration FROM rental r JOIN inventory i ON i.inventory_id=r.inventory_id JOIN film f ON f.film_id=i.film_id WHERE r.rental_date<='2006-03-01 00:00:00' AND DATEDIFF(r.return_date,r.rental_date)>f.rental_duration",
     ["rental_id", "customer_id", "komponen_keterlambatan"], "Satu baris per rental with strictly positive returned calendar-overage component", ["domain:late-calendar-excess", "domain:late-null-return", "domain:late-start-cutoff"], "legacy-positive-late-component-membership"),
    ("local_semantics", "Bagaimana keragaman kategori dan judul film yang pernah disewa setiap pelanggan yang menjangkau sedikitnya tiga kategori?",
     "SELECT c.customer_id,c.first_name,COUNT(DISTINCT fc.category_id),COUNT(DISTINCT i.film_id) FROM customer c JOIN rental r ON r.customer_id=c.customer_id JOIN inventory i ON i.inventory_id=r.inventory_id JOIN film_category fc ON fc.film_id=i.film_id GROUP BY c.customer_id HAVING COUNT(DISTINCT fc.category_id)>=3",
     ["customer_id", "first_name", "jumlah_kategori", "jumlah_judul"], "Satu baris per customer with at least3distinct rental categories", ["detail:inventory", "detail:rental", "local:film_category"], "customer-rental-catalog-diversity"),
    ("local_semantics", "Bagaimana total nominal dan banyaknya pembayaran bulanan menurut toko inventaris dari penyewaan yang dibayar?",
     "SELECT i.store_id,DATE_FORMAT(p.payment_date,'%Y-%m'),SUM(p.amount),COUNT(*) FROM payment p JOIN rental r ON r.rental_id=p.rental_id JOIN inventory i ON i.inventory_id=r.inventory_id GROUP BY i.store_id,DATE_FORMAT(p.payment_date,'%Y-%m')",
     ["store_id", "bulan", "total_nominal", "jumlah_pembayaran"], "Satu baris per current inventory-store/payment-calendar-month; only linked rentals", ["local:payment.amount", "detail:payment", "local:inventory.store_id"], "inventory-store-monthly-receipt-measures"),
    ("schema_mapping", "Pasangan pemeran dan kategori film apa saja yang terdapat dalam katalog?",
     "SELECT DISTINCT a.actor_id,a.first_name,a.last_name,c.category_id,c.name FROM actor a JOIN film_actor fa ON fa.actor_id=a.actor_id JOIN film_category fc ON fc.film_id=fa.film_id JOIN category c ON c.category_id=fc.category_id",
     ["actor_id", "first_name", "last_name", "category_id", "category_name"], "Satu baris per distinct actor/category pair", ["local:film_actor", "local:film_category"], "actor-category-catalog-reach"),
    ("local_semantics", "Berapa banyak film yang durasi pemutarannya lebih dari dua jam?",
     "SELECT COUNT(*) FROM film WHERE length>120", ["jumlah_film"], "Satu hitungan judul dengan durasi melebihi dua jam",
     ["local:film.length"], "catalog-runtime-threshold"),
    ("local_semantics", "Berapa banyak pelanggan yang tercatat tidak aktif?",
     "SELECT COUNT(*) FROM customer WHERE active=0", ["jumlah_pelanggan"], "Satu hitungan current inactive customer records",
     ["local:customer.active"], "recorded-inactive-customer-population"),
    ("local_semantics", "Pelanggan mana saja yang terdaftar di home store 1?",
     "SELECT customer_id FROM customer WHERE store_id=1", ["customer_id"], "Satu baris per customer whose home store is1",
     ["detail:customer.store_id"], "home-store-customer-membership"),
    ("local_semantics", "Berapa banyak film yang periode sewanya lebih dari lima hari?",
     "SELECT COUNT(*) FROM film WHERE rental_duration>5", ["jumlah_film"], "Satu hitungan configured catalog periods exceeding five days",
     ["local:film.rental_duration"], "configured-period-threshold"),
    ("local_semantics", "Berapa banyak pembayaran yang nominalnya melebihi 10.00?",
     "SELECT COUNT(*) FROM payment WHERE amount>10.00", ["jumlah_pembayaran"], "Satu hitungan recorded payment events above a supplied threshold",
     ["local:payment.amount"], "payment-event-amount-threshold"),
    ("schema_mapping", "Film mana saja yang memiliki rating PG-13?",
     "SELECT film_id FROM film WHERE rating='PG-13'", ["film_id"], "Satu baris per catalog title with the requested rating",
     ["local:film.rating"], "catalog-rating-membership"),
]

FACT_REPLACEMENTS = {
    "domain:customer-home": "detail:customer.store_id", "domain:customer-cross-store": "detail:customer.store_id",
    "domain:staff-home": "detail:staff.store_id", "domain:staff-cross-store": "detail:staff.store_id",
    "domain:rate-period": "detail:film.rental_rate", "domain:replacement-trigger": "detail:film.replacement_cost",
    "domain:original-language-dubbing": "detail:film.original_language_id", "domain:customer-retention": "detail:customer.active",
    "domain:staff-retention": "detail:staff.active", "domain:configured-not-collected": "detail:film.replacement_cost",
    "domain:rate-not-receipt": "detail:film.rental_rate",
}


def main():
    if len(ITEMS) != 45 or len(NATURAL_REQUESTS) != 45 or len(EXTRA_ITEMS) != 15:
        raise ValueError("Expected45archived-family drafts and15prospective additions")
    inventory = json.loads((OUT / "facts.json").read_bytes())
    facts = {entry["fact_id"]: entry for entry in inventory["facts"]}
    questions, gold, contracts, profiles = [], [], [], []
    natural = []
    for item, question in zip(ITEMS, NATURAL_REQUESTS, strict=True):
        need, _, sql, columns, grain, required, family = item
        if need == "domain_integration":
            need = "local_semantics"  # Helpful mapping was not a rule dependency.
        required = list(dict.fromkeys(FACT_REPLACEMENTS.get(fact, fact) for fact in required))
        natural.append((need, question, sql, columns, grain, required, family))
    for i, (need, question, sql, columns, grain, required, family) in enumerate(natural + EXTRA_ITEMS, 101):
        qid = f"Q{i:03}"
        question += " Keluaran (berurutan): " + ", ".join(columns) + "."
        if qid == "Q120":
            sql = "SELECT rating,ROUND(AVG(length),4) FROM film GROUP BY rating"
        elif qid == "Q116":
            sql = "SELECT c.category_id,COUNT(fc.film_id) FROM category c LEFT JOIN film_category fc ON fc.category_id=c.category_id GROUP BY c.category_id"
        elif qid == "Q119":
            sql = "SELECT s.staff_id,COUNT(DISTINCT r.customer_id) FROM staff s LEFT JOIN rental r ON r.staff_id=s.staff_id GROUP BY s.staff_id"
        elif qid == "Q121":
            sql = "SELECT c.active,SUM(p.amount) FROM customer c LEFT JOIN payment p ON p.customer_id=c.customer_id GROUP BY c.active"
        elif qid == "Q127":
            sql = "SELECT st.store_id,SUM(p.amount) FROM store st LEFT JOIN staff s ON s.store_id=st.store_id LEFT JOIN payment p ON p.staff_id=s.staff_id GROUP BY st.store_id"
        elif qid == "Q122":
            sql = "SELECT st.store_id,COUNT(DISTINCT i.film_id),COUNT(i.inventory_id) FROM store st LEFT JOIN inventory i ON i.store_id=st.store_id GROUP BY st.store_id"
        elif qid == "Q144":
            sql = "SELECT st.store_id,SUM(CASE WHEN s.active=1 THEN p.amount END),SUM(CASE WHEN s.active=0 THEN p.amount END) FROM store st LEFT JOIN staff s ON s.store_id=st.store_id LEFT JOIN payment p ON p.staff_id=s.staff_id GROUP BY st.store_id"
        elif qid == "Q150":
            required = [*required, "domain:late-empty-zero"]
            # rental_duration is UNSIGNED in installed Sakila. GREATEST alone
            # does not protect an underflow evaluated before clipping.
            sql = sql.replace("-f.rental_duration", "-CAST(f.rental_duration AS SIGNED)")
        elif qid == "Q152":
            # The requested title count includes rented uncategorized titles;
            # category membership determines the eligibility threshold only.
            sql = sql.replace("JOIN film_category fc", "LEFT JOIN film_category fc")
        ordered = False
        # Do not require unseen ordering from a canonical reference. Ranking
        # membership ambiguity is separately screened before selection.
        from sqlglot import exp, parse_one
        parsed = parse_one(sql, read="mysql")
        if parsed.args.get("order") and not parsed.args.get("limit"):
            parsed.set("order", None)
            sql = parsed.sql(dialect="mysql")
        profile = profile_sql(sql)
        questions.append({"question_id": qid, "question": question, "complexity": profile.complexity,
                          "schema_references": sorted({table.name for table in parsed.find_all(exp.Table)})})
        approximate = {"Q107": [0], "Q108": [0], "Q109": [0], "Q114": [0], "Q120": [1]}.get(qid, [])
        date_columns = [0] if qid in {"Q123", "Q138"} else []
        gold.append({"question_id": qid, "sql": sql, "column_count": len(columns), "ordered": ordered,
                     "approximate_columns": approximate, "date_columns": date_columns,
                     "review_status": "draft", "semantic_notes": "First reference author A; independent reference and semantic review pending. Canonical structure chosen before new model outputs. Numeric/date contracts are prospective, not fitted to predictions."})
        availability = {}
        for fact_id in required:
            first = int(facts[fact_id]["first_annotation_scenario"][1:])
            availability[fact_id] = {f"S{arm}": "explicit" if arm >= first else "absent" if fact_id.startswith("domain:") else "derivable" for arm in range(4)}
        contracts.append({"question_id": qid, "analytic_purpose": "Memeriksa kebutuhan laporan Sakila: " + family,
                          "primary_need": need, "semantic_family": family, "capabilities": [need, profile.complexity],
                          "grain": grain, "population": "Seluruh rekaman snapshot yang memenuhi syarat tertulis dalam pertanyaan; tidak ada default active filter atau periode tersembunyi.",
                          "measure": question, "role_attribution": "Ikuti role yang disebut dalam pertanyaan; gunakan hubungan master pada snapshot, bukan rekonstruksi historis.",
                          "units": "Mengikuti satuan eksplisit dalam pertanyaan dan makna field sumber.",
                          "time_scope": "Seluruh catatan snapshot kecuali interval yang ditulis eksplisit; timezone session UTC tanpa konversi tersirat.",
                          "zero_and_null_policy": "Common output conventions tetap di S0–S3: groups NULL dipertahankan, missing numeric diabaikan, all-missing SUM tetap NULL; setiap entitas yang diminta dipertahankan dengan zero count. Sourced domain definition eksplisit dapat menetapkan total nol.",
                          "duplicate_policy": "Baris dan kejadian dihitung dengan multiplicity, kecuali pertanyaan menyebut berbeda, tanpa duplikasi, atau satu kali.",
                          "ordering_and_ties": "Sequence mengikuti urutan dan pemutus seri eksplisit." if ordered else "Multiset whole rows; urutan bebas; seluruh ties yang diminta disertakan.",
                          "output_columns": columns, "numeric_policy": "Common instruction: tampilkan rerata/rasio empat desimal; threshold sebelum pembulatan. Count dan monetary sums exact. Tolerance1e-9/1e-12 hanya declared average/ratio columns; DATE/string ISO hanya declared calendar-date columns.",
                          "required_fact_ids": required, "fact_availability": availability,
                          "source_urls": sorted({url for fact_id in required for url in facts[fact_id]["sources"]}),
                          "plausible_wrong_variants": ["Pilih measure atau role berbeda dari yang diminta, atau hilangkan syarat utama; specific mutation and witness must be authored before eligibility."],
                          "construction_status": "draft", "human_review_status": "pending"})
        profiles.append({"question_id": qid, "primary_need": need, **profile.document()})
    OUT.mkdir(parents=True, exist_ok=True)
    for name, rows in [("candidates.questions.jsonl", questions), ("candidates.gold-a.jsonl", gold), ("candidates.contracts.jsonl", contracts)]:
        (OUT / name).write_bytes(b"".join(canonical_json(row) for row in rows))
    (OUT / "candidate-profiles.json").write_bytes(canonical_json({"status": "authoring_draft_only", "profiles": profiles,
                   "availability_warning": "Initial author exposure labels only, not independently assessed necessity or entailment. No candidate is eligible until review, alternative reference, explicit mutations, witness and overlap checks complete."}))
    packet = ROOT / "runs/revision-02/review-packets/questions-only-04"
    packet.mkdir(parents=True, exist_ok=True)
    (packet / "questions.jsonl").write_bytes(b"".join(canonical_json({"question_id": q["question_id"], "question": q["question"]}) for q in questions))
    print(json.dumps({"status": "candidate_draft", "questions": len(questions),
                      "levels": dict(Counter(q["complexity"] for q in questions)),
                      "cells": {str(k):v for k,v in Counter((q["complexity"],c["primary_need"]) for q,c in zip(questions,contracts)).items()},
                      "generation_requests": 0, "main_experiment_allowed": False}))


if __name__ == "__main__":
    main()
