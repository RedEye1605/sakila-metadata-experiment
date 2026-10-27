# Draft annotation review

Specification v2. All 16 tables and 90 columns have short and detailed descriptions. S3 adds seven glossary terms. Candidate validation verifies catalog-to-MCP fidelity; human semantic review remains pending.

## actor

S1: Daftar pemeran film.

S2: Menyimpan identitas pemeran film. Keterlibatan pemeran pada film dicatat melalui relasi film_actor.

Source: https://dev.mysql.com/doc/sakila/en/sakila-structure-tables-actor.html

## actor.actor_id

S1: ID unik aktor.

S2: Pengenal unik rekaman aktor. Nilai digunakan untuk mengidentifikasi baris dan berbeda dari atribut deskriptif nama atau label.

Source: https://dev.mysql.com/doc/sakila/en/sakila-structure-tables-actor.html

## actor.first_name

S1: Nama depan aktor.

S2: Bagian nama depan yang disimpan untuk aktor. Nama merupakan atribut identitas tampilan dan terpisah dari pengenal unik rekaman.

Source: https://dev.mysql.com/doc/sakila/en/sakila-structure-tables-actor.html

## actor.last_name

S1: Nama belakang aktor.

S2: Bagian nama belakang yang disimpan untuk aktor. Nama merupakan atribut identitas tampilan dan terpisah dari pengenal unik rekaman.

Source: https://dev.mysql.com/doc/sakila/en/sakila-structure-tables-actor.html

## actor.last_update

S1: Waktu pembaruan rekaman.

S2: Timestamp saat baris dibuat atau terakhir diperbarui. Nilai ini merupakan penanda perubahan rekaman pada tabel yang bersangkutan.

Source: https://dev.mysql.com/doc/sakila/en/sakila-structure-tables-actor.html

## address

S1: Alamat pelanggan, staf, dan toko.

S2: Menyimpan rincian alamat yang dapat dirujuk pelanggan, staf, atau toko. Setiap alamat dihubungkan dengan sebuah kota.

Source: https://dev.mysql.com/doc/sakila/en/sakila-structure-tables-address.html

## address.address

S1: Baris utama alamat.

S2: Baris pertama rincian alamat jalan. Informasi kota, negara, kode pos, dan kontak dicatat pada atribut lain dalam struktur alamat.

Source: https://dev.mysql.com/doc/sakila/en/sakila-structure-tables-address.html

## address.address2

S1: Baris tambahan alamat.

S2: Baris kedua untuk rincian alamat tambahan. Kolom ini melengkapi baris alamat utama ketika informasi tambahan tersedia.

Source: https://dev.mysql.com/doc/sakila/en/sakila-structure-tables-address.html

## address.address_id

S1: ID unik alamat.

S2: Pengenal unik rekaman alamat. Nilai digunakan untuk mengidentifikasi baris dan berbeda dari atribut deskriptif nama atau label.

Source: https://dev.mysql.com/doc/sakila/en/sakila-structure-tables-address.html

## address.city_id

S1: ID kota terkait.

S2: Referensi ke rekaman kota yang terkait dengan alamat. Hubungan tersebut ditetapkan oleh foreign key pada schema terpasang.

Source: https://dev.mysql.com/doc/sakila/en/sakila-structure-tables-address.html

## address.district

S1: Distrik atau wilayah alamat.

S2: Nama distrik atau wilayah administratif yang dicatat pada alamat. Atribut ini terpisah dari nama kota dan negara.

Source: https://dev.mysql.com/doc/sakila/en/sakila-structure-tables-address.html

## address.last_update

S1: Waktu pembaruan rekaman.

S2: Timestamp saat baris dibuat atau terakhir diperbarui. Nilai ini merupakan penanda perubahan rekaman pada tabel yang bersangkutan.

Source: https://dev.mysql.com/doc/sakila/en/sakila-structure-tables-address.html

## address.location

S1: Geometri lokasi alamat.

S2: Data spasial untuk lokasi alamat. Native type pada schema terpasang adalah geometry; kolom ini terpisah dari teks alamat jalan.

Source: https://dev.mysql.com/doc/sakila/en/sakila-structure-tables-address.html

## address.phone

S1: Nomor telepon alamat.

S2: Nomor telepon kontak yang disimpan bersama alamat. Nilai merupakan informasi kontak, bukan besaran transaksi.

Source: https://dev.mysql.com/doc/sakila/en/sakila-structure-tables-address.html

## address.postal_code

S1: Kode pos alamat.

S2: Kode pos yang dicatat untuk alamat. Nilainya disimpan sebagai teks dan berfungsi sebagai kode wilayah pos.

Source: https://dev.mysql.com/doc/sakila/en/sakila-structure-tables-address.html

## category

S1: Daftar kategori film.

S2: Menyimpan kategori untuk pengelompokan film. Hubungan kategori dengan film dicatat pada film_category.

Source: https://dev.mysql.com/doc/sakila/en/sakila-structure-tables-category.html

## category.category_id

S1: ID unik kategori.

S2: Pengenal unik rekaman kategori. Nilai digunakan untuk mengidentifikasi baris dan berbeda dari atribut deskriptif nama atau label.

Source: https://dev.mysql.com/doc/sakila/en/sakila-structure-tables-category.html

## category.last_update

S1: Waktu pembaruan rekaman.

S2: Timestamp saat baris dibuat atau terakhir diperbarui. Nilai ini merupakan penanda perubahan rekaman pada tabel yang bersangkutan.

Source: https://dev.mysql.com/doc/sakila/en/sakila-structure-tables-category.html

## category.name

S1: Nama kategori film.

S2: Label kategori yang digunakan untuk mengelompokkan film. Pengenal kategori tetap menjadi identitas rekaman kategori.

Source: https://dev.mysql.com/doc/sakila/en/sakila-structure-tables-category.html

## city

S1: Daftar kota.

S2: Menyimpan nama kota dan negara tempat kota tersebut dicatat. Kota menjadi bagian dari rincian alamat.

Source: https://dev.mysql.com/doc/sakila/en/sakila-structure-tables-city.html

## city.city

S1: Nama kota.

S2: Nama kota yang dicatat pada struktur alamat. Negara kota tersebut ditentukan oleh referensi negara pada rekaman yang sama.

Source: https://dev.mysql.com/doc/sakila/en/sakila-structure-tables-city.html

## city.city_id

S1: ID unik kota.

S2: Pengenal unik rekaman kota. Nilai digunakan untuk mengidentifikasi baris dan berbeda dari atribut deskriptif nama atau label.

Source: https://dev.mysql.com/doc/sakila/en/sakila-structure-tables-city.html

## city.country_id

S1: ID negara terkait.

S2: Referensi ke rekaman negara yang terkait dengan kota. Hubungan tersebut ditetapkan oleh foreign key pada schema terpasang.

Source: https://dev.mysql.com/doc/sakila/en/sakila-structure-tables-city.html

## city.last_update

S1: Waktu pembaruan rekaman.

S2: Timestamp saat baris dibuat atau terakhir diperbarui. Nilai ini merupakan penanda perubahan rekaman pada tabel yang bersangkutan.

Source: https://dev.mysql.com/doc/sakila/en/sakila-structure-tables-city.html

## country

S1: Daftar negara.

S2: Menyimpan identitas dan nama negara. Negara dirujuk oleh rekaman kota pada struktur alamat.

Source: https://dev.mysql.com/doc/sakila/en/sakila-structure-tables-country.html

## country.country

S1: Nama negara.

S2: Nama negara dalam struktur alamat. Pengenal negara dipakai sebagai referensi oleh rekaman kota.

Source: https://dev.mysql.com/doc/sakila/en/sakila-structure-tables-country.html

## country.country_id

S1: ID unik negara.

S2: Pengenal unik rekaman negara. Nilai digunakan untuk mengidentifikasi baris dan berbeda dari atribut deskriptif nama atau label.

Source: https://dev.mysql.com/doc/sakila/en/sakila-structure-tables-country.html

## country.last_update

S1: Waktu pembaruan rekaman.

S2: Timestamp saat baris dibuat atau terakhir diperbarui. Nilai ini merupakan penanda perubahan rekaman pada tabel yang bersangkutan.

Source: https://dev.mysql.com/doc/sakila/en/sakila-structure-tables-country.html

## customer

S1: Daftar pelanggan penyewaan.

S2: Menyimpan identitas, kontak, status aktif, alamat, dan home store pelanggan. Rekaman pelanggan dirujuk oleh penyewaan serta pembayaran.

Source: https://dev.mysql.com/doc/sakila/en/sakila-structure-tables-customer.html

## customer.active

S1: Penanda pelanggan aktif.

S2: Status aktif pelanggan yang disimpan sebagai penanda Boolean. Status ini merupakan atribut rekaman pelanggan, bukan jumlah transaksi penyewaan.

Source: https://dev.mysql.com/doc/sakila/en/sakila-structure-tables-customer.html

## customer.address_id

S1: ID alamat terkait.

S2: Referensi ke rekaman alamat yang terkait dengan pelanggan. Hubungan tersebut ditetapkan oleh foreign key pada schema terpasang.

Source: https://dev.mysql.com/doc/sakila/en/sakila-structure-tables-customer.html

## customer.create_date

S1: Waktu pencatatan pelanggan.

S2: Waktu pelanggan ditambahkan ke sistem. Kolom ini menandai pencatatan pelanggan dan terpisah dari waktu kejadian transaksi.

Source: https://dev.mysql.com/doc/sakila/en/sakila-structure-tables-customer.html

## customer.customer_id

S1: ID unik pelanggan.

S2: Pengenal unik rekaman pelanggan. Nilai digunakan untuk mengidentifikasi baris dan berbeda dari atribut deskriptif nama atau label.

Source: https://dev.mysql.com/doc/sakila/en/sakila-structure-tables-customer.html

## customer.email

S1: Alamat email pelanggan.

S2: Alamat surat elektronik yang dicatat untuk pelanggan. Atribut ini merupakan informasi kontak pada rekaman tersebut.

Source: https://dev.mysql.com/doc/sakila/en/sakila-structure-tables-customer.html

## customer.first_name

S1: Nama depan pelanggan.

S2: Bagian nama depan yang disimpan untuk pelanggan. Nama merupakan atribut identitas tampilan dan terpisah dari pengenal unik rekaman.

Source: https://dev.mysql.com/doc/sakila/en/sakila-structure-tables-customer.html

## customer.last_name

S1: Nama belakang pelanggan.

S2: Bagian nama belakang yang disimpan untuk pelanggan. Nama merupakan atribut identitas tampilan dan terpisah dari pengenal unik rekaman.

Source: https://dev.mysql.com/doc/sakila/en/sakila-structure-tables-customer.html

## customer.last_update

S1: Waktu pembaruan rekaman.

S2: Timestamp saat baris dibuat atau terakhir diperbarui. Nilai ini merupakan penanda perubahan rekaman pada tabel yang bersangkutan.

Source: https://dev.mysql.com/doc/sakila/en/sakila-structure-tables-customer.html

## customer.store_id

S1: ID home store pelanggan.

S2: Referensi ke toko yang dicatat sebagai home store pelanggan. Ini merupakan asosiasi toko pada rekaman pelanggan.

Source: https://dev.mysql.com/doc/sakila/en/sakila-structure-tables-customer.html

## film

S1: Katalog judul film.

S2: Menyimpan informasi judul dan konfigurasi penyewaan film. Salinan fisik yang berada pada suatu toko dicatat terpisah dalam inventory.

Source: https://dev.mysql.com/doc/sakila/en/sakila-structure-tables-film.html

## film.description

S1: Ringkasan cerita film.

S2: Teks ringkasan isi atau alur cerita film. Informasi ini merupakan atribut isi film dalam katalog.

Source: https://dev.mysql.com/doc/sakila/en/sakila-structure-tables-film.html

## film.film_id

S1: ID unik film.

S2: Pengenal unik rekaman film. Nilai digunakan untuk mengidentifikasi baris dan berbeda dari atribut deskriptif nama atau label.

Source: https://dev.mysql.com/doc/sakila/en/sakila-structure-tables-film.html

## film.language_id

S1: ID bahasa film.

S2: Referensi ke bahasa yang ditetapkan untuk film. Schema juga menyediakan referensi bahasa asli sebagai atribut terpisah.

Source: https://dev.mysql.com/doc/sakila/en/sakila-structure-tables-film.html

## film.last_update

S1: Waktu pembaruan rekaman.

S2: Timestamp saat baris dibuat atau terakhir diperbarui. Nilai ini merupakan penanda perubahan rekaman pada tabel yang bersangkutan.

Source: https://dev.mysql.com/doc/sakila/en/sakila-structure-tables-film.html

## film.length

S1: Durasi film dalam menit.

S2: Lama pemutaran film dengan satuan menit. Atribut ini menggambarkan durasi isi film, bukan periode penyewaan.

Source: https://dev.mysql.com/doc/sakila/en/sakila-structure-tables-film.html

## film.original_language_id

S1: ID bahasa asli film.

S2: Referensi ke bahasa asli film, misalnya ketika film mempunyai versi sulih suara. Referensi ini boleh tidak diisi pada schema.

Source: https://dev.mysql.com/doc/sakila/en/sakila-structure-tables-film.html

## film.rating

S1: Klasifikasi rating penonton film.

S2: Rating penonton yang ditetapkan pada film. Nilai yang diperbolehkan ditentukan oleh tipe enum dalam schema.

Source: https://dev.mysql.com/doc/sakila/en/sakila-structure-tables-film.html

## film.release_year

S1: Tahun rilis film.

S2: Tahun ketika film dirilis. Nilai ini berbeda konsep dari timestamp perubahan rekaman katalog.

Source: https://dev.mysql.com/doc/sakila/en/sakila-structure-tables-film.html

## film.rental_duration

S1: Periode sewa film dalam hari.

S2: Lama periode penyewaan yang dikonfigurasi pada film, dengan satuan hari. Nilai ini merupakan pengaturan pada katalog film.

Source: https://dev.mysql.com/doc/sakila/en/sakila-structure-tables-film.html

## film.rental_rate

S1: Tarif sewa film per periode.

S2: Biaya sewa film untuk periode yang ditentukan oleh konfigurasi durasi sewa film. Nilai ini disimpan pada katalog film.

Source: https://dev.mysql.com/doc/sakila/en/sakila-structure-tables-film.html

## film.replacement_cost

S1: Nilai penggantian film.

S2: Nilai yang dibebankan untuk penggantian ketika film tidak kembali atau kembali dalam keadaan rusak. Atribut ini tersimpan pada katalog film.

Source: https://dev.mysql.com/doc/sakila/en/sakila-structure-tables-film.html

## film.special_features

S1: Fitur tambahan DVD film.

S2: Fitur tambahan yang disediakan pada DVD film. Lebih dari satu fitur dapat dicatat karena atribut ini memakai tipe set.

Source: https://dev.mysql.com/doc/sakila/en/sakila-structure-tables-film.html

## film.title

S1: Judul film.

S2: Judul yang digunakan untuk menamai film dalam katalog. Identitas rekaman film ditentukan oleh pengenal film yang terpisah.

Source: https://dev.mysql.com/doc/sakila/en/sakila-structure-tables-film.html

## film_actor

S1: Hubungan film dengan pemerannya.

S2: Satu baris merepresentasikan hubungan seorang pemeran dengan sebuah film. Pengenal pemeran dan film membentuk identitas gabungan hubungan tersebut.

Source: https://dev.mysql.com/doc/sakila/en/sakila-structure-tables-film_actor.html

## film_actor.actor_id

S1: ID aktor terkait.

S2: Referensi ke rekaman aktor yang terkait dengan hubungan pemeran film. Hubungan tersebut ditetapkan oleh foreign key pada schema terpasang.

Source: https://dev.mysql.com/doc/sakila/en/sakila-structure-tables-film_actor.html

## film_actor.film_id

S1: ID film terkait.

S2: Referensi ke rekaman film yang terkait dengan hubungan pemeran film. Hubungan tersebut ditetapkan oleh foreign key pada schema terpasang.

Source: https://dev.mysql.com/doc/sakila/en/sakila-structure-tables-film_actor.html

## film_actor.last_update

S1: Waktu pembaruan rekaman.

S2: Timestamp saat baris dibuat atau terakhir diperbarui. Nilai ini merupakan penanda perubahan rekaman pada tabel yang bersangkutan.

Source: https://dev.mysql.com/doc/sakila/en/sakila-structure-tables-film_actor.html

## film_category

S1: Hubungan film dengan kategori.

S2: Mencatat pengaitan sebuah film dengan kategori. Pengenal film dan kategori membentuk identitas gabungan pada tabel hubungan ini.

Source: https://dev.mysql.com/doc/sakila/en/sakila-structure-tables-film_category.html

## film_category.category_id

S1: ID kategori terkait.

S2: Referensi ke rekaman kategori yang terkait dengan hubungan kategori film. Hubungan tersebut ditetapkan oleh foreign key pada schema terpasang.

Source: https://dev.mysql.com/doc/sakila/en/sakila-structure-tables-film_category.html

## film_category.film_id

S1: ID film terkait.

S2: Referensi ke rekaman film yang terkait dengan hubungan kategori film. Hubungan tersebut ditetapkan oleh foreign key pada schema terpasang.

Source: https://dev.mysql.com/doc/sakila/en/sakila-structure-tables-film_category.html

## film_category.last_update

S1: Waktu pembaruan rekaman.

S2: Timestamp saat baris dibuat atau terakhir diperbarui. Nilai ini merupakan penanda perubahan rekaman pada tabel yang bersangkutan.

Source: https://dev.mysql.com/doc/sakila/en/sakila-structure-tables-film_category.html

## film_text

S1: Teks film untuk pencarian.

S2: Menyimpan salinan pengenal, judul, dan ringkasan film untuk pencarian teks. Tabel ini bukan pencatatan salinan inventaris film.

Source: https://dev.mysql.com/doc/sakila/en/sakila-structure-tables-film_text.html

## film_text.description

S1: Ringkasan pada teks pencarian film.

S2: Salinan ringkasan isi film yang disediakan untuk pencarian teks. Isi ini merupakan teks film, bukan catatan penyewaan.

Source: https://dev.mysql.com/doc/sakila/en/sakila-structure-tables-film_text.html

## film_text.film_id

S1: ID film pada teks pencarian.

S2: Pengenal film yang direpresentasikan pada tabel teks pencarian. Schema terpasang tidak menetapkan foreign key untuk kolom ini.

Source: https://dev.mysql.com/doc/sakila/en/sakila-structure-tables-film_text.html

## film_text.title

S1: Judul pada teks pencarian film.

S2: Salinan judul film pada tabel untuk pencarian teks. Atribut ini tidak mengidentifikasi salinan fisik inventaris.

Source: https://dev.mysql.com/doc/sakila/en/sakila-structure-tables-film_text.html

## inventory

S1: Salinan film pada toko.

S2: Satu baris merepresentasikan satu salinan film di satu toko. Salinan tersebut dapat dirujuk oleh rekaman transaksi penyewaan.

Source: https://dev.mysql.com/doc/sakila/en/sakila-structure-tables-inventory.html

## inventory.film_id

S1: ID film terkait.

S2: Referensi ke rekaman film yang terkait dengan salinan inventaris. Hubungan tersebut ditetapkan oleh foreign key pada schema terpasang.

Source: https://dev.mysql.com/doc/sakila/en/sakila-structure-tables-inventory.html

## inventory.inventory_id

S1: ID unik salinan inventaris.

S2: Pengenal unik satu salinan film dalam inventaris. Identitas salinan berbeda dari identitas judul film yang direpresentasikan.

Source: https://dev.mysql.com/doc/sakila/en/sakila-structure-tables-inventory.html

## inventory.last_update

S1: Waktu pembaruan rekaman.

S2: Timestamp saat baris dibuat atau terakhir diperbarui. Nilai ini merupakan penanda perubahan rekaman pada tabel yang bersangkutan.

Source: https://dev.mysql.com/doc/sakila/en/sakila-structure-tables-inventory.html

## inventory.store_id

S1: ID toko salinan inventaris.

S2: Referensi ke toko tempat salinan inventaris dicatat. Asosiasi toko melekat pada salinan film dalam inventaris.

Source: https://dev.mysql.com/doc/sakila/en/sakila-structure-tables-inventory.html

## language

S1: Daftar bahasa film.

S2: Menyimpan identitas dan label bahasa. Film mempunyai referensi bahasa film dan referensi bahasa asli yang terpisah.

Source: https://dev.mysql.com/doc/sakila/en/sakila-structure-tables-language.html

## language.language_id

S1: ID unik bahasa.

S2: Pengenal unik rekaman bahasa. Nilai digunakan untuk mengidentifikasi baris dan berbeda dari atribut deskriptif nama atau label.

Source: https://dev.mysql.com/doc/sakila/en/sakila-structure-tables-language.html

## language.last_update

S1: Waktu pembaruan rekaman.

S2: Timestamp saat baris dibuat atau terakhir diperbarui. Nilai ini merupakan penanda perubahan rekaman pada tabel yang bersangkutan.

Source: https://dev.mysql.com/doc/sakila/en/sakila-structure-tables-language.html

## language.name

S1: Nama bahasa.

S2: Label bahasa yang dapat dirujuk oleh film. Identitas bahasa disimpan pada pengenal bahasa yang terpisah.

Source: https://dev.mysql.com/doc/sakila/en/sakila-structure-tables-language.html

## payment

S1: Catatan pembayaran pelanggan.

S2: Satu baris mencatat pembayaran pelanggan yang diproses staf. Referensi penyewaan terkait tersedia ketika pembayaran dihubungkan dengan suatu penyewaan.

Source: https://dev.mysql.com/doc/sakila/en/sakila-structure-tables-payment.html

## payment.amount

S1: Nilai pembayaran pelanggan.

S2: Nilai uang yang tercatat untuk satu pembayaran pelanggan. Pembayaran diproses sebagai rekaman tersendiri pada tabel pembayaran.

Source: https://dev.mysql.com/doc/sakila/en/sakila-structure-tables-payment.html

## payment.customer_id

S1: ID pelanggan pemilik pembayaran.

S2: Referensi ke pelanggan yang saldonya dikaitkan dengan pembayaran. Kolom ini mengidentifikasi pelanggan pada rekaman pembayaran.

Source: https://dev.mysql.com/doc/sakila/en/sakila-structure-tables-payment.html

## payment.last_update

S1: Waktu pembaruan rekaman.

S2: Timestamp saat baris dibuat atau terakhir diperbarui. Nilai ini merupakan penanda perubahan rekaman pada tabel yang bersangkutan.

Source: https://dev.mysql.com/doc/sakila/en/sakila-structure-tables-payment.html

## payment.payment_date

S1: Waktu pembayaran diproses.

S2: Tanggal dan waktu ketika pembayaran diproses. Ini merupakan waktu kejadian pembayaran pada rekaman tersebut.

Source: https://dev.mysql.com/doc/sakila/en/sakila-structure-tables-payment.html

## payment.payment_id

S1: ID unik pembayaran.

S2: Pengenal unik rekaman pembayaran. Nilai digunakan untuk mengidentifikasi baris dan berbeda dari atribut deskriptif nama atau label.

Source: https://dev.mysql.com/doc/sakila/en/sakila-structure-tables-payment.html

## payment.rental_id

S1: ID penyewaan terkait pembayaran.

S2: Referensi ke penyewaan yang berkaitan dengan pembayaran ketika hubungan tersebut dicatat. Schema memperbolehkan referensi ini kosong.

Source: https://dev.mysql.com/doc/sakila/en/sakila-structure-tables-payment.html

## payment.staff_id

S1: ID staf pemroses pembayaran.

S2: Referensi ke anggota staf yang memproses pembayaran. Atribut ini merekam peran staf pada kejadian pembayaran.

Source: https://dev.mysql.com/doc/sakila/en/sakila-structure-tables-payment.html

## rental

S1: Catatan transaksi penyewaan.

S2: Satu baris mencatat penyewaan sebuah salinan inventaris oleh pelanggan. Rekaman memuat waktu penyewaan, pengembalian, dan staf pemroses.

Source: https://dev.mysql.com/doc/sakila/en/sakila-structure-tables-rental.html

## rental.customer_id

S1: ID pelanggan terkait.

S2: Referensi ke rekaman pelanggan yang terkait dengan penyewaan. Hubungan tersebut ditetapkan oleh foreign key pada schema terpasang.

Source: https://dev.mysql.com/doc/sakila/en/sakila-structure-tables-rental.html

## rental.inventory_id

S1: ID salinan yang disewa.

S2: Referensi ke satu salinan inventaris yang terlibat dalam transaksi penyewaan. Salinan mempunyai identitas film dan toko pada rekaman inventaris.

Source: https://dev.mysql.com/doc/sakila/en/sakila-structure-tables-rental.html

## rental.last_update

S1: Waktu pembaruan rekaman.

S2: Timestamp saat baris dibuat atau terakhir diperbarui. Nilai ini merupakan penanda perubahan rekaman pada tabel yang bersangkutan.

Source: https://dev.mysql.com/doc/sakila/en/sakila-structure-tables-rental.html

## rental.rental_date

S1: Waktu transaksi penyewaan.

S2: Tanggal dan waktu ketika salinan inventaris disewakan. Atribut ini menandai awal kejadian penyewaan yang dicatat.

Source: https://dev.mysql.com/doc/sakila/en/sakila-structure-tables-rental.html

## rental.rental_id

S1: ID unik penyewaan.

S2: Pengenal unik rekaman penyewaan. Nilai digunakan untuk mengidentifikasi baris dan berbeda dari atribut deskriptif nama atau label.

Source: https://dev.mysql.com/doc/sakila/en/sakila-structure-tables-rental.html

## rental.return_date

S1: Waktu pengembalian tercatat.

S2: Tanggal dan waktu pengembalian salinan inventaris yang disewa. Nilai kosong menandakan belum ada waktu pengembalian yang dicatat.

Source: https://dev.mysql.com/doc/sakila/en/sakila-structure-tables-rental.html

## rental.staff_id

S1: ID staf pemroses penyewaan.

S2: Referensi ke anggota staf yang memproses penyewaan. Ini adalah peran staf pada transaksi penyewaan yang dicatat.

Source: https://dev.mysql.com/doc/sakila/en/sakila-structure-tables-rental.html

## staff

S1: Daftar staf penyewaan.

S2: Menyimpan identitas, kontak, akun, status aktif, dan home store staf. Staf dapat dirujuk oleh pembayaran, penyewaan, serta penetapan manajer toko.

Source: https://dev.mysql.com/doc/sakila/en/sakila-structure-tables-staff.html

## staff.active

S1: Penanda staf aktif.

S2: Status aktif anggota staf dalam sistem. Penanda ini merupakan atribut staf dan terpisah dari keberadaan transaksi historisnya.

Source: https://dev.mysql.com/doc/sakila/en/sakila-structure-tables-staff.html

## staff.address_id

S1: ID alamat terkait.

S2: Referensi ke rekaman alamat yang terkait dengan staf. Hubungan tersebut ditetapkan oleh foreign key pada schema terpasang.

Source: https://dev.mysql.com/doc/sakila/en/sakila-structure-tables-staff.html

## staff.email

S1: Alamat email staf.

S2: Alamat surat elektronik yang dicatat untuk staf. Atribut ini merupakan informasi kontak pada rekaman tersebut.

Source: https://dev.mysql.com/doc/sakila/en/sakila-structure-tables-staff.html

## staff.first_name

S1: Nama depan staf.

S2: Bagian nama depan yang disimpan untuk staf. Nama merupakan atribut identitas tampilan dan terpisah dari pengenal unik rekaman.

Source: https://dev.mysql.com/doc/sakila/en/sakila-structure-tables-staff.html

## staff.last_name

S1: Nama belakang staf.

S2: Bagian nama belakang yang disimpan untuk staf. Nama merupakan atribut identitas tampilan dan terpisah dari pengenal unik rekaman.

Source: https://dev.mysql.com/doc/sakila/en/sakila-structure-tables-staff.html

## staff.last_update

S1: Waktu pembaruan rekaman.

S2: Timestamp saat baris dibuat atau terakhir diperbarui. Nilai ini merupakan penanda perubahan rekaman pada tabel yang bersangkutan.

Source: https://dev.mysql.com/doc/sakila/en/sakila-structure-tables-staff.html

## staff.password

S1: Nilai autentikasi akun staf.

S2: Representasi kata sandi yang disimpan untuk akses akun staf. Algoritme pembentukan nilainya tidak ditetapkan oleh tipe kolom.

Source: https://dev.mysql.com/doc/sakila/en/sakila-structure-tables-staff.html

## staff.picture

S1: Data foto staf.

S2: Konten biner foto anggota staf. Kolom foto boleh tidak diisi ketika tidak ada gambar yang disimpan.

Source: https://dev.mysql.com/doc/sakila/en/sakila-structure-tables-staff.html

## staff.staff_id

S1: ID unik staf.

S2: Pengenal unik rekaman staf. Nilai digunakan untuk mengidentifikasi baris dan berbeda dari atribut deskriptif nama atau label.

Source: https://dev.mysql.com/doc/sakila/en/sakila-structure-tables-staff.html

## staff.store_id

S1: ID home store staf.

S2: Referensi ke toko yang dicatat sebagai home store atau penempatan umum staf. Kolom ini merupakan asosiasi pada rekaman staf.

Source: https://dev.mysql.com/doc/sakila/en/sakila-structure-tables-staff.html

## staff.username

S1: Nama akun login staf.

S2: Nama akun yang digunakan staf untuk mengakses sistem penyewaan. Nama akun terpisah dari nama depan dan nama belakang staf.

Source: https://dev.mysql.com/doc/sakila/en/sakila-structure-tables-staff.html

## store

S1: Daftar toko penyewaan.

S2: Menyimpan identitas toko, alamat, dan staf yang menjadi manajernya. Toko mempunyai hubungan dengan salinan inventaris dan home store pelanggan maupun staf.

Source: https://dev.mysql.com/doc/sakila/en/sakila-structure-tables-store.html

## store.address_id

S1: ID alamat terkait.

S2: Referensi ke rekaman alamat yang terkait dengan toko. Hubungan tersebut ditetapkan oleh foreign key pada schema terpasang.

Source: https://dev.mysql.com/doc/sakila/en/sakila-structure-tables-store.html

## store.last_update

S1: Waktu pembaruan rekaman.

S2: Timestamp saat baris dibuat atau terakhir diperbarui. Nilai ini merupakan penanda perubahan rekaman pada tabel yang bersangkutan.

Source: https://dev.mysql.com/doc/sakila/en/sakila-structure-tables-store.html

## store.manager_staff_id

S1: ID staf manajer toko.

S2: Referensi ke anggota staf yang ditetapkan sebagai manajer toko. Ini merupakan peran khusus staf pada rekaman toko.

Source: https://dev.mysql.com/doc/sakila/en/sakila-structure-tables-store.html

## store.store_id

S1: ID unik toko.

S2: Pengenal unik rekaman toko. Nilai digunakan untuk mengidentifikasi baris dan berbeda dari atribut deskriptif nama atau label.

Source: https://dev.mysql.com/doc/sakila/en/sakila-structure-tables-store.html

## Business term: Judul, salinan, dan transaksi

Film merepresentasikan judul katalog. Inventaris merepresentasikan salinan film pada toko. Penyewaan merepresentasikan transaksi atas salinan; satu judul dapat memiliki beberapa salinan dan satu salinan dapat terkait dengan beberapa transaksi penyewaan.

Applies to: film, inventory, rental

Sources: https://dev.mysql.com/doc/sakila/en/sakila-structure-tables-film.html, https://dev.mysql.com/doc/sakila/en/sakila-structure-tables-inventory.html, https://dev.mysql.com/doc/sakila/en/sakila-structure-tables-rental.html

## Business term: Tarif sewa dan pembayaran tercatat

Tarif sewa adalah biaya yang dikonfigurasi pada film untuk periode sewanya. Nilai pembayaran adalah uang yang dicatat pada kejadian pembayaran pelanggan. Kedua atribut tersebut mewakili konsep yang berbeda dan tidak saling menggantikan.

Applies to: film.rental_rate, payment.amount

Sources: https://dev.mysql.com/doc/sakila/en/sakila-structure-tables-film.html, https://dev.mysql.com/doc/sakila/en/sakila-structure-tables-payment.html

## Business term: Periode sewa dan waktu kejadian

Durasi sewa pada katalog film menggunakan satuan hari. Durasi pemutaran film menggunakan menit. Waktu penyewaan dan pengembalian adalah penanda kejadian transaksi yang dicatat secara terpisah.

Applies to: film.rental_duration, film.length, rental.rental_date, rental.return_date

Sources: https://dev.mysql.com/doc/sakila/en/sakila-structure-tables-film.html, https://dev.mysql.com/doc/sakila/en/sakila-structure-tables-rental.html

## Business term: Home store pelanggan dan staf

Toko pada rekaman pelanggan maupun staf merupakan home store. Pelanggan dan staf tidak dibatasi hanya bertransaksi atau bekerja pada home store itu. Salinan inventaris mempunyai asosiasi toko tersendiri.

Applies to: customer.store_id, staff.store_id, inventory.store_id

Sources: https://dev.mysql.com/doc/sakila/en/sakila-structure-tables-customer.html, https://dev.mysql.com/doc/sakila/en/sakila-structure-tables-staff.html, https://dev.mysql.com/doc/sakila/en/sakila-structure-tables-inventory.html

## Business term: Pengembalian yang belum tercatat

Nilai kosong pada waktu pengembalian berarti tidak ada waktu pengembalian yang dicatat untuk transaksi tersebut. Interpretasinya mengikuti isi dataset yang dibekukan dan bukan keadaan operasional toko pada tanggal saat eksperimen dijalankan.

Applies to: rental.return_date

Sources: https://dev.mysql.com/doc/sakila/en/sakila-structure-tables-rental.html

## Business term: Status aktif dan riwayat transaksi

Penanda aktif menjelaskan status rekaman pelanggan atau staf. Penanda tersebut tidak menyatakan jumlah transaksi atau ada tidaknya penyewaan yang belum dikembalikan. Riwayat transaksi mempunyai rekaman dan referensi identitasnya sendiri.

Applies to: customer.active, staff.active, rental

Sources: https://dev.mysql.com/doc/sakila/en/sakila-structure-tables-customer.html, https://dev.mysql.com/doc/sakila/en/sakila-structure-tables-staff.html, https://dev.mysql.com/doc/sakila/en/sakila-structure-tables-rental.html

## Business term: Hubungan pembayaran dengan penyewaan

Schema pembayaran menyediakan referensi penyewaan yang boleh kosong. Pembayaran tetap merupakan rekaman pembayaran tersendiri ketika referensi penyewaan tidak diisi. Ketiadaan referensi tersebut bukan penanda nilai pembayaran nol.

Applies to: payment, payment.rental_id

Sources: https://dev.mysql.com/doc/sakila/en/sakila-structure-tables-payment.html
