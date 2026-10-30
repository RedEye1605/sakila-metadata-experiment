"""Authoring recipe for source-grounded revision-02 draft metadata.

This creates authoring inputs, NOT MCP snapshots. It never edits v1 annotations
or grants review approval. Run before the question-selection freeze.
"""
from __future__ import annotations

import json
import hashlib
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "data/benchmarks/revision-02"
BASE = "https://dev.mysql.com/doc/sakila/en/sakila-structure-tables-"

ADDITIONS = {
    "address": "Setiap rekaman menyimpan satu alamat yang dapat dirujuk entitas lain.",
    "address.address2": "Nilai tambahan dapat tidak diisi.",
    "address.district": "Wilayah ini disimpan terpisah dari nama kota dan negara.",
    "address.postal_code": "Kode disimpan sebagai teks; nol di awal merupakan bagian dari kode.",
    "customer": "Setiap baris merepresentasikan satu pelanggan yang terdaftar.",
    "customer.create_date": "Tanggal dan waktu saat pelanggan ditambahkan ke sistem; berbeda dari tanggal transaksi pelanggan.",
    "customer.store_id": "Menunjuk home store tempat pelanggan umumnya berbelanja; pelanggan dapat menyewa dari toko lain.",
    "customer.active": "Menonaktifkan rekaman merupakan alternatif menghapus pelanggan; status yang tercatat tidak menggambarkan status historis setiap transaksi.",
    "film": "Satu rekaman merepresentasikan satu judul dalam katalog.",
    "film.description": "Teks memuat sinopsis atau ringkasan alur cerita.",
    "film.language_id": "Mengacu pada bahasa versi film yang tercatat dalam katalog.",
    "film.original_language_id": "Dipakai ketika versi film dialihsuarakan ke bahasa baru; referensi bahasa asal dapat tidak diisi.",
    "film.rental_rate": "Tarif berlaku untuk periode yang ditentukan pada rental_duration, bukan jumlah pembayaran yang telah diterima.",
    "film.replacement_cost": "Biaya yang ditetapkan bila film tidak dikembalikan atau dikembalikan rusak; nilai konfigurasi bukan bukti pembayaran telah terjadi.",
    "film.rating": "Kode yang tersedia adalah G, PG, PG-13, R, dan NC-17.",
    "film.special_features": "Satu DVD dapat mencantumkan beberapa fitur dari Trailers, Commentaries, Deleted Scenes, dan Behind the Scenes.",
    "film_actor": "Setiap pasangan film dan aktor mencatat keterlibatan aktor pada film tersebut.",
    "film_category": "Setiap pasangan film dan kategori mencatat keanggotaan kategori film.",
    "film_text": "Berisi teks yang digunakan untuk pencarian judul dan sinopsis film.",
    "inventory": "Satu rekaman merepresentasikan satu salinan fisik dari satu judul pada satu toko.",
    "payment": "Satu rekaman merepresentasikan satu kejadian pembayaran oleh pelanggan.",
    "payment.customer_id": "Pelanggan yang saldonya dikenai pembayaran ini.",
    "payment.payment_date": "Memuat tanggal dan waktu pemrosesan kejadian pembayaran.",
    "payment.rental_id": "Referensi rental bersifat opsional; pembayaran dapat terkait biaya belum dilunasi tanpa alokasi langsung ke satu rental. Referensi kosong sendiri tidak menentukan jenis pembayaran.",
    "rental": "Satu rekaman merepresentasikan satu kejadian penyewaan atas satu salinan inventaris.",
    "rental.rental_date": "Memuat tanggal dan waktu awal kejadian penyewaan.",
    "rental.return_date": "Nilai dapat kosong jika waktu pengembalian belum dicatat.",
    "staff": "Setiap baris merepresentasikan satu anggota staf.",
    "staff.username": "Digunakan untuk login staf ke sistem penyewaan.",
    "staff.store_id": "Menunjuk home store penugasan staf; staf dapat bekerja di toko lain.",
    "staff.active": "Rekaman staf yang meninggalkan pekerjaan dipertahankan dengan status tidak aktif; ini status yang tercatat, bukan rekonstruksi masa lalu.",
    "store.manager_staff_id": "Staf yang ditetapkan sebagai manajer untuk rekaman toko ini.",
}

SHORT_OVERRIDES = {
    "film.rental_rate": "Tarif sewa film per periode.",
    "customer.store_id": "ID home store pelanggan.",
    "staff.store_id": "ID home store staf.",
}

BUSINESS = [
    ("inventory-availability", "Ketersediaan salinan inventaris Sakila",
     "Salinan inventaris tersedia apabila belum pernah disewa atau semua catatan penyewaannya sudah mempunyai waktu pengembalian. Adanya satu catatan penyewaan tanpa waktu pengembalian membuat salinan itu tidak tersedia. Ini keadaan menurut catatan snapshot; tidak merekonstruksi ketersediaan pada tanggal historis. Judul yang tidak memiliki inventaris berbeda dari salinan yang sedang tidak tersedia.",
     ["inventory", "rental.return_date"], ["https://dev.mysql.com/doc/sakila/en/sakila-structure-functions-inventory_in_stock.html", "inventory", "rental"]),
    ("monthly-rewards", "Kelayakan rewards bulanan Sakila",
     "Kelayakan rewards dinilai untuk satu bulan kalender penuh sebelum tanggal acuan laporan. Frekuensi yang dinilai adalah banyaknya kejadian pembayaran, termasuk pembayaran yang tidak terkait langsung dengan rental, dan ukuran nominalnya adalah total nilai pembayaran. Kedua ukuran masing-masing harus lebih besar daripada ambang yang diberikan; sama dengan ambang belum memenuhi syarat. Status aktif pelanggan bukan syarat tambahan pada definisi ini. Kelayakan tidak berarti pemeringkatan pelanggan. Tanggal acuan eksplisit membekukan tanggal sistem laporan untuk eksperimen; routine asli menggunakan tanggal sistem.",
     ["customer", "payment"], ["https://dev.mysql.com/doc/sakila/en/sakila-structure-procedures-rewards_report.html", "payment"]),
    ("returned-rental-late-component", "Komponen keterlambatan menurut rutin Sakila",
     "Komponen keterlambatan yang dihitung rutin Sakila memberi satu unit nominal untuk setiap kelebihan hari kalender pengembalian atas periode sewa katalog. Selisih hari memakai tanggal kalender yang tersimpan, bukan pembulatan durasi jam. Kontribusi tidak negatif; penyewaan tanpa waktu pengembalian menyumbang nol pada komponen ini. Awal penyewaan yang tepat pada tanggal dan waktu acuan ikut dihitung; tanggal acuan tanpa jam berarti pukul 00:00:00. Batas ini tidak memotong waktu pengembalian. Komponen pelanggan adalah total kontribusi rental yang masuk cakupan; pelanggan tanpa rental yang masuk cakupan mendapat komponen nol. Komponen ini bukan saldo lengkap, bukan nominal yang sudah dibayar, dan tidak memuat biaya penggantian film. Ini definisi komponen executable rutin sampel, bukan kebijakan penagihan umum.",
     ["rental", "film.rental_duration"], ["https://dev.mysql.com/doc/sakila/en/sakila-structure-functions-get_customer_balance.html", "film", "rental"]),
]

DOMAIN_ATOMS = {
    "inventory-availability": [
        ("stock-availability", "Satu salinan tersedia jika tidak memiliki penyewaan yang waktu pengembaliannya belum diisi; salinan tanpa riwayat penyewaan juga tersedia.", ["https://dev.mysql.com/doc/sakila/en/sakila-structure-functions-inventory_in_stock.html"], "documented_routine_rule", []),
        ("stock-snapshot", "Ketersediaan tersebut adalah state catatan snapshot, bukan rekonstruksi histori.", ["https://dev.mysql.com/doc/sakila/en/sakila-structure-functions-inventory_in_stock.html"], "routine_scope_boundary", []),
    ],
    "monthly-rewards": [
        ("rewards-period", "Periode rewards adalah bulan kalender penuh sebelum tanggal sistem laporan.", ["https://dev.mysql.com/doc/sakila/en/sakila-structure-procedures-rewards_report.html"], "documented_routine_rule", []),
        ("rewards-event-grain", "Frekuensi rewards dihitung dari kejadian pembayaran, bukan jumlah rental.", ["https://dev.mysql.com/doc/sakila/en/sakila-structure-procedures-rewards_report.html"], "executable_routine_rule", []),
        ("rewards-strict-both", "Jumlah pembayaran dan total nominal keduanya harus melampaui ambang masing-masing; equality belum eligible.", ["https://dev.mysql.com/doc/sakila/en/sakila-structure-procedures-rewards_report.html"], "executable_routine_rule", []),
        ("rewards-no-active-filter", "Status aktif pelanggan bukan kriteria tambahan rewards pada routine ini.", ["https://dev.mysql.com/doc/sakila/en/sakila-structure-procedures-rewards_report.html"], "executable_routine_rule", []),
    ],
    "returned-rental-late-component": [
        ("late-empty-zero", "Komponen pelanggan menjumlah kontribusi rental tercakup dan bernilai nol jika tidak ada rental tercakup.", ["https://dev.mysql.com/doc/sakila/en/sakila-structure-functions-get_customer_balance.html"], "executable_routine_component", []),
        ("late-calendar-excess", "Komponen keterlambatan adalah satu unit nominal per kelebihan hari kalender pengembalian terhadap periode katalog, minimum nol.", ["https://dev.mysql.com/doc/sakila/en/sakila-structure-functions-get_customer_balance.html"], "executable_routine_component", []),
        ("late-null-return", "Penyewaan dengan pengembalian belum tercatat menyumbang nol pada komponen executable ini.", ["https://dev.mysql.com/doc/sakila/en/sakila-structure-functions-get_customer_balance.html"], "executable_routine_component", []),
        ("late-start-cutoff", "Awal penyewaan harus tidak melewati waktu acuan, inklusif; tanggal tanpa jam diinterpretasikan 00:00:00. Cutoff tidak membatasi waktu pengembalian.", ["https://dev.mysql.com/doc/sakila/en/sakila-structure-functions-get_customer_balance.html"], "executable_routine_scope_boundary", []),
    ],
}

def source_url(name):
    return name if name.startswith("https://") else BASE + name + ".html"


def main():
    old = json.loads((ROOT / "data/annotations/specification.json").read_bytes())
    annotations, facts = [], []
    for original in old["annotations"]:
        item = dict(original)
        identity = item["element_id"]
        item["short"] = SHORT_OVERRIDES.get(identity, item["short"])
        addition = ADDITIONS.get(identity, "")
        item["detailed"] = item["short"] + (" " + addition if addition else "")
        annotations.append(item)
        facts.append({"fact_id": "local:" + identity, "statement": item["short"], "owner": identity,
                      "first_annotation_scenario": "S1", "kind": "local_description",
                      "sources": [item["source_url"]], "human_review_status": "pending"})
        if addition:
            facts.append({"fact_id": "detail:" + identity, "statement": addition, "owner": identity,
                          "first_annotation_scenario": "S2", "kind": "local_detail_or_technical_restatement",
                          "sources": [item["source_url"]], "human_review_status": "pending"})
    terms = []
    for term_id, name, definition, targets, tables in BUSINESS:
        sources = [source_url(table) for table in tables]
        terms.append({"term_id": term_id, "name": name, "definition": definition, "applies_to": targets,
                      "sources": sources, "urn": "urn:li:glossaryTerm:sakila.revision02." + term_id,
                      "executable_source": {"path": "downloads/sakila/sakila-schema.sql", "sha256": hashlib.sha256((ROOT / "downloads/sakila/sakila-schema.sql").read_bytes()).hexdigest(),
                                            "authority": "Executable official Sakila1.5 body; prose/comments alone may be incomplete. Fixed reporting date is an explicit experimental adapter."}})
        for atom_id, statement, atom_tables, kind, dependencies in DOMAIN_ATOMS[term_id]:
            facts.append({"fact_id": "domain:" + atom_id, "statement": statement, "owner": "business_context:" + term_id,
                          "first_annotation_scenario": "S3", "kind": kind,
                          "sources": [source_url(table) for table in atom_tables],
                          "derived_from": dependencies, "human_review_status": "pending"})
    OUT.mkdir(parents=True, exist_ok=True)
    spec = {"specification_version": "revision-02-draft-03", "status": "draft", "language": "id",
            "database_schema_sha256": old["database_schema_sha256"],
            "policy": "Source-grounded local descriptions and cross-entity contexts; no gold, SQL recipes, IDs, answer thresholds or implicit reporting policies. Trivial fields may have equal short/detailed text. Semantic review pending.",
            "annotations": annotations, "business_terms": terms}
    inventory = {"inventory_version": 2, "status": "draft", "exposure_scope": "annotation_prose_only_not_complete_model_input", "facts": facts,
                 "limits": "Authoring draft. Technical entailment and proposition-level redundancy need independent review. First annotation occurrence is not complete-input availability or necessity. Record count is not a count of strictly atomic or novel facts. Routine sources must be checked against the exact cached executable body, not comments alone."}
    for name, value in [("annotations.json", spec), ("facts.json", inventory)]:
        (OUT / name).write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n")
    print(json.dumps({"status": "authoring_draft_only", "annotations": len(annotations), "facts": len(facts),
                      "business_cards": len(terms), "unchanged_short_detailed": sum(a["short"] == a["detailed"] for a in annotations),
                      "mcp_snapshots_created": False, "human_review_complete": False}))


if __name__ == "__main__":
    main()
