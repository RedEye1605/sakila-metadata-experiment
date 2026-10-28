"""Generate BAB IV/V only from complete, audited real experiment artifacts."""
from __future__ import annotations

import hashlib
import json
import shutil
from collections import Counter, defaultdict
from pathlib import Path

from sakila_experiment.analysis.report import audit_run
from sakila_experiment.contracts import load_gold, load_questions

TITLE = "Analisis Pengaruh Metadata terhadap Execution Accuracy pada Sistem Text-to-SQL Berbasis Large Language Model (Studi Kasus: Basis Data Sakila)"


def table(headers, rows):
    cell = lambda v: str(v).replace("|", "\\|").replace("\n", "<br>")
    return "\n".join(["| " + " | ".join(map(cell, headers)) + " |", "|" + "---|" * len(headers),
                      *["| " + " | ".join(map(cell, row)) + " |" for row in rows]])


def num(value, digits=2):
    return "tidak tersedia" if value is None else f"{value:.{digits}f}"


def build_thesis(root: Path, run: Path, output: Path):
    manifest, records = audit_run(run / "benchmark")
    report = json.loads((run / "analysis/report.json").read_bytes())
    auxiliary = json.loads((run / "auxiliary/report.json").read_bytes())
    if (manifest["mode"] != "main" or len(records) != 600 or not report["integrity_verified"]
            or report.get("experiment_id") != manifest["experiment_id"]
            or auxiliary["status"] != "auxiliary_replay_complete"):
        raise ValueError("Complete audited600 trial primary and8case auxiliary results are required for BAB V")
    output.mkdir(parents=True, exist_ok=True)
    paths = {key: root / value for key, value in manifest["instrument_paths"].items()}
    questions, gold = load_questions(paths["questions"]), load_gold(paths["gold"])
    baseline = json.loads((root / "runs/database/baseline.json").read_bytes())
    backend = manifest["backend_evidence"]
    settings, plan = manifest["inference_config"], manifest["experiment_config"]
    schemas = baseline["technical_schema"]["tables"]
    row_counts = {r["table"]: r["row_count"] for r in baseline["table_content"]}
    review = manifest["review_attestation"]
    source = manifest["source_version"]
    snapshot_rows = [[s, manifest["snapshots"]["snapshot_sha256"][s]] for s in ("S0", "S1", "S2", "S3")]
    software = [["Python", manifest["python_version"]], ["MySQL", manifest["mysql_version"]],
                ["Model", backend["model_repository"]], ["Model revision", backend["model_repository_revision"]],
                ["Quantization", backend["quantization_runtime"]], ["Backend", backend["build_info"]],
                ["Context", settings["context_tokens"]], ["GPU layers", backend["gpu_layers"]],
                *[[name, version] for name, version in manifest["package_versions"].items()]]
    design = [["S0", "Technical schema: tabel, kolom, tipe, PK/FK dan relasi"],
              ["S1", "S0 ditambah deskripsi singkat"], ["S2", "Schema/coverage sama, detail lokal ditambahkan bila bersumber"],
              ["S3", "S2 dipertahankan, ditambah tiga definisi domain bersumber"]]
    chapter4 = f"""# BAB IV — PERANCANGAN DAN IMPLEMENTASI

Judul penelitian: **{TITLE}**.

## 4.1 Kedudukan sistem dalam penelitian

Pipeline berfungsi sebagai instrumen eksperimen kuantitatif untuk menguji pengaruh paket anotasi metadata terhadap Execution Accuracy (EX). Penelitian menggunakan satu model lokal yang tetap dan satu database Sakila resmi. Pengembangan aplikasi, perbandingan banyak model, fine-tuning dan evaluasi pengalaman pengguna bukan sasaran penelitian. Delapan tahap metodologi tetap meliputi studi literatur, penyusunan anotasi metadata, penyusunan dataset pengujian, perancangan pipeline, implementasi pipeline, pengujian, analisis hasil, serta kesimpulan dan saran. Instalasi database dan pemeriksaan model merupakan prasyarat teknis.

Unit berpasangan adalah pertanyaan. Tiga puluh pertanyaan yang sama diuji pada empat kondisi dengan lima request independen pada setiap pasangan. Jumlah trial utama ialah30×4×5=600, dengan150 trial per kondisi dan200 trial per kelompok kompleksitas. Lima pengulangan memperlihatkan kestabilan keluaran; pengulangan tidak mengubah jumlah pertanyaan independen menjadi600.

## 4.2 Arsitektur dan pemisahan akses

```mermaid
flowchart LR
  DB[MySQL Sakila] --> DH[DataHub ingestion dan annotations]
  DH --> MCP[MCP server dan Python client]
  MCP --> SNAP[Frozen snapshots S0 S1 S2 S3]
  SNAP --> CTRL[Python controller]
  Q[Pertanyaan Indonesia] --> CTRL
  CTRL --> LLM[Local llama-server]
  LLM --> SAFE[Parser dan SQL safety]
  SAFE --> RO[MySQL read-only]
  RO --> EX[Result comparator]
  GOLD[Gold SQL terpisah] --> EX
  EX --> LOG[Ledger dan paired analysis]
```

Fase persiapan metadata menggunakan DataHub sebagai katalog dan MCP sebagai jalur pengambilan metadata. Python memvalidasi schema, deskripsi, konteks bisnis serta provenance, kemudian membangun snapshot deterministic dengan hash SHA-256. MCP tidak dipanggil dinamis berdasarkan pertanyaan pada fase inference. LLM menerima instruksi umum, satu snapshot dan satu pertanyaan; model tidak diberi koneksi database, tools MCP/DataHub, gold SQL, hasil eksekusi gold, hasil eksperimen lama atau history request sebelumnya. Eksekusi dan evaluasi dimiliki Python.

## 4.3 Lingkungan implementasi

{table(['Komponen','Versi/nilai aktual'], software)}

GPU yang dicatat saat verifikasi backend: `{backend.get('resource_observations', {}).get('gpu', 'lihat verification.json')}`. Observasi memori host tercantum dalam verification artifact; jangan menggantinya dengan spesifikasi laptop perkiraan. Metadata/catalog dan inference dijalankan bergantian agar tidak bersaing pada RAM. Model file SHA-256: `{manifest['model_version_or_hash']}`. Source commit yang dipakai smoke dan benchmark: `{source['git_commit']}`. Source tree hash: `{source['source_tree_sha256']}`. Versi image DataHub dan bukti ingestion/MCP disimpan melalui hash runtime/provenance pada manifest; image yang sedang populer bukan pengganti versi yang benar-benar dipakai.

## 4.4 Objek database dan kontrol isi

Sakila terpasang mempunyai {len(schemas)} base tables,{sum(len(t['columns']) for t in schemas)} kolom,{sum(len(t['foreign_keys']) for t in schemas)} foreign keys dan{sum(row_counts.values())} baris. Database utama memakai character set `{baseline['server']['character_set']}`, collation `{baseline['server']['collation']}` dan timezone UTC. Schema SHA-256 `{manifest['database_schema_sha256']}`; data SHA-256 `{manifest['database_data_sha256']}`. Fingerprint diperiksa sebelum dan sesudah run. Data utama tidak diubah antarkondisi. Delapan variasi evaluasi berada pada clone dengan container, port dan credentials terpisah.

{table(['Tabel','Baris','Kolom','PK'], [[t['name'],row_counts[t['name']],len(t['columns']),', '.join(t['primary_key'])] for t in schemas])}

## 4.5 Variabel perlakuan dan anotasi

{table(['Kondisi','Metadata'], design)}

Semua kondisi mempertahankan technical schema, urutan serialisasi, seluruh16 tabel/90 kolom dan PK/FK yang sama. S1/S2 mencakup106 table/column targets;74 deskripsi trivial dipertahankan sama untuk menghindari tambahan kalimat tanpa fakta. Detail tambahan pada S2 karena itu tidak dianggap merata pada seluruh elemen. S3 mempertahankan deskripsi S2 dan menambah definisi ketersediaan salinan, rewards bulanan serta komponen keterlambatan dari routine resmi Sakila. Ketersediaan adalah kondisi snapshot, bukan rekonstruksi historis. Rewards memakai kejadian pembayaran, bulan kalender lengkap sebelumnya, dua ambang strict, dan tidak menambah syarat status aktif. Komponen keterlambatan mengikuti perilaku executable routine, bukan saldo lengkap atau kebijakan penagihan universal.

{table(['Kondisi','Snapshot SHA-256'], snapshot_rows)}

Business rules tidak memuat gold SQL, langkah join, jawaban baris atau ambang spesifik benchmark. Semua annotation source dan paired MCP export receipts dipertahankan. Kontrol identik di antara kondisi meliputi database/data, schema coverage, prompt template, bahasa, pertanyaan, model/decoder, evaluator, privileges dan timeouts. Panjang input tidak dipaksakan sama karena panjang merupakan bagian perubahan paket metadata; actual tokens dicatat.

## 4.6 Penyusunan dataset dan validasi makna

Dataset memuat10 simple,10 medium dan10 complex. Struktur canonical reference mengikuti adapter MySQL terhadap routine hardness Spider yang commit-nya dikunci:10 easy,10 medium,5 hard dan5 extra. Label menggambarkan canonical SQL, bukan minimum kompleksitas semua SQL ekuivalen dan bukan jaminan kesulitan model. Pemisahan struktur dari kebutuhan informasi terinspirasi Spider/BIRD; taxonomy lokal10 schema mapping,14 local semantics dan6 domain integration tidak disebut label resmi BIRD.

Pertanyaan menggunakan kebutuhan bisnis dalam bahasa Indonesia, tanpa footer nama kolom teknis, clause SQL atau recipe penyelesaian. Objek, metrik, filter, tanggal dan jumlah peringkat tetap disampaikan agar tugas dapat dinilai secara jelas. Definisi domain berada di metadata. Tiga soal meminta ordering/ranking, dua di antaranya top-k. Sisa ties mengikuti konvensi identifier numerik unik ascending yang sama pada seluruh kondisi; top-k tepat k atau seluruh eligible rows jika kurang dari k. Posisi kolom dan aliases tidak dipaksakan.

Reference A/B ditulis terpisah, interpretasi question-only dikunci sebelum complete-input review, kemudian seluruh30 pasangan diperiksa pada baseline dan8 variations. Seluruh56 critical mutants mempunyai observed witnesses. Reference agreement dan finite witnesses merupakan bukti engineering, bukan proof semantik universal. Review substansi dinyatakan selesai oleh peneliti melalui pernyataan yang direkam pada `{review['recorded_at_utc']}`; ini waktu pencatatan, bukan tanggal review yang diketahui. **Nama reviewer: [diisi peneliti]. Tanggal dan rincian pelaksanaan review: [diisi peneliti].** Tidak ada klaim dua reviewer manusia atau signed review yang belum didokumentasikan.

## 4.7 Prompt dan local inference

Instruksi dan construction logic identik untuk S0–S3. Question IDs, complexity, schema-reference hints dan kontrak private tidak diteruskan ke model. Semua120 kombinasi question/snapshot diperiksa dengan tokenizer serta chat template backend aktual, dengan reserve keluaran{settings['max_output_tokens']}tokens dan safety margin{settings['safety_margin_tokens']}tokens. Input tidak dipotong diam-diam.

Temperature={settings['temperature']},top-p={settings['top_p']},top-k={settings['top_k']}; min-p=0,repeat penalty=1,cache prompt=false,stream=false,n=1. Backend memakai satu slot, tanpa context shifting atau conversation history. Seed inference diturunkan deterministic dari base seed{plan['inference_seed_base']},question ID dan repetition; seed yang sama dipakai pada kondisi berbeda untuk question/repetition yang sama. Independent requests tidak menjamin SQL berbeda pada setiap pengulangan.

## 4.8 SQL safety dan EX

Generated SQL dianggap untrusted. Dedicated SELECT-only account, single-statement AST validation, function restrictions, timeout query{manifest['database_config']['query_timeout_ms']}ms, connection timeout dan batas hasil diberlakukan. Administrator hanya dipakai pada setup clone yang topology-nya diverifikasi, tidak untuk prediksi model. Raw response, mechanically extracted SQL, rejected SQL dan error tetap dicatat. Tidak ada semantic repair, execution-feedback loop atau kesempatan kedua untuk model-generated failure.

Evaluator `{manifest['comparator_version']}` mencari satu bijeksi kolom global. `(nama,pendapatan)` dapat setara dengan `(pendapatan,nama)` jika hubungan nilai seluruh baris tetap sama. Alias diabaikan. Multiset whole rows mempertahankan duplikasi, NULL tidak disamakan dengan string/zero, numeric exact tidak dibulatkan sembarang, dan tolerance hanya berlaku pada kolom yang ditetapkan. Kontrak date/numeric memakai koordinat gold sesudah mapping. Requested row ordering tetap diperiksa. Empty outputs memerlukan jumlah kolom sama tetapi tidak membuktikan identitas semantik kolom kosong. Search-budget exhaustion merupakan evaluator/infrastructure incident dengan EX belum ditetapkan, bukan model nol.

EX trial bernilai1bila SQL berhasil dan hasil ekuivalen sesuai kontrak; invalid/unauthorized SQL atau hasil salah bernilai0. Infrastructure failures dicatat terpisah. Hasil sama pada satu database tidak membuktikan ekuivalensi universal; exact SQL string matching bukan metrik utama.

## 4.9 Controller, logging dan pelaksanaan

Trial ID deterministic memakai question/scenario/repetition. Urutan randomized dalam repetition blocks dengan seed{plan['order_seed']}. Ledger SQLite append-only menyimpan dispatch, durable response, incident dan terminal outcome. Restart menggunakan respons tersimpan untuk evaluasi, tidak meregenerasi model errors atau completed trials. Dispatch ambigu memerlukan rekonsiliasi operator tercatat dan tidak diklaim exactly-once inference.

Smoke terpisah terdiri3 pertanyaan P×4 snapshot=12 requests. Smoke memeriksa transport, sampler, source identity, database access dan evaluator; tidak ada threshold EX untuk memilih model atau menyeleksi soal. Setelah smoke lengkap, source/model/backend/prompt/snapshot/policy serta sampler evidence harus sama sebelum main freeze. Benchmark600 trial dijalankan sekali per assignment. Sesudah hasil lengkap, semua SQL tersimpan, termasuk primary failures, dieksekusi pada8 auxiliary cases tanpa generation baru. Hasil auxiliary tidak mengganti EX primer.

## 4.10 Rencana analisis dan reproduksibilitas

EX kondisi=jumlah benar/150×100%. Perhitungan tambahan memakai question dan complexity; skor per question/scenario ialah successes/5. Analisis menggunakan30 question blocks. Omnibus memakai100.000 within-question permutations; enam pairwise contrasts memakai exact sign-flip dan koreksi Holm. Effect size dinyatakan sebagai percentage points. Bootstrap10.000 whole-question samples distratifikasi menurut complexity untuk pointwise95%interval. Analysis seed={plan['analysis_seed']}. Exchangeability/swap invariance adalah asumsi statistik; randomisasi urutan request tidak otomatis membuktikannya. Nonsignificance tidak membuktikan equivalence.

Manifest mencatat Git/source hashes, Python/packages, MySQL/data hashes, model/image/template, snapshots, questions/gold, prompt hashes, settings dan seeds. Logging mencakup latency inference/SQL terpisah, input/output tokens dari backend, validation/execution status, result/gold hashes dan EX. Keseluruhan evidence dipertahankan; output laporan tidak mengarang token atau skor yang hilang. Sumber metode: [Spider](https://aclanthology.org/D18-1425/),[BIRD](https://arxiv.org/html/2305.03111v3),dan [semantic test-suite evaluation](https://aclanthology.org/2020.emnlp-main.29/). Penelitian ini tetap studi satu database dan tidak mengklaim cakupan benchmark cross-domain tersebut.
"""
    desc = report["descriptive"]
    scores = {r["scenario_id"]: r for r in desc["by_scenario"]}
    if (set(scores) != {"S0", "S1", "S2", "S3"}
            or any(r["trials"] != 150 or r["correct"] != sum(t["execution_accuracy"] for t in records if t["scenario_id"] == s)
                   for s, r in scores.items())):
        raise ValueError("Analysis table differs from the audited primary outcomes")
    stats = report["paired_analysis"]
    best = max(r["execution_accuracy_percent"] for r in scores.values())
    leaders = ", ".join(s for s, r in scores.items() if r["execution_accuracy_percent"] == best)
    primary_table = table(["Kondisi", "Benar", "Trial", "EX (%)", "Selisih terhadap S0 (pp)"],
        [[s, scores[s]["correct"], 150, num(scores[s]["execution_accuracy_percent"]),
          num(scores[s]["execution_accuracy_percent"] - scores["S0"]["execution_accuracy_percent"])] for s in scores])
    consistency = []
    for s in scores:
        pairs = [r for r in desc["by_question"] if r["scenario_id"] == s]
        consistency.append([s, sum(r["correct"] == 5 for r in pairs), sum(r["correct"] == 0 for r in pairs),
                            sum(0 < r["correct"] < 5 for r in pairs)])
    aux_rows = [json.loads(line) for line in (run / "auxiliary/outcomes.jsonl").read_bytes().splitlines() if line.strip()]
    aux_plan = json.loads((run / "auxiliary/plan.json").read_bytes())
    expected_cases = set(aux_plan["case_ids"])
    cells = Counter((r["trial_id"], r["fixture_id"]) for r in aux_rows)
    if (aux_plan["source_run_manifest_sha256"] != hashlib.sha256((run / "benchmark/manifest.json").read_bytes()).hexdigest()
            or len(expected_cases) != 8 or len(aux_rows) != 4800
            or set(cells) != {(r["trial_id"], case) for r in records for case in expected_cases}
            or set(cells.values()) != {1} or any(type(r["execution_accuracy"]) is not int or r["execution_accuracy"] not in (0, 1) for r in aux_rows)):
        raise ValueError("Complete matching4800auxiliary outcomes are required before reporting robustness")
    aux_by_trial = defaultdict(list)
    for row in aux_rows:
        aux_by_trial[row["trial_id"]].append(row["execution_accuracy"])
    robustness = []
    for s in scores:
        selected = [r for r in records if r["scenario_id"] == s]
        nine_pass = sum(r["execution_accuracy"] == 1 and all(aux_by_trial[r["trial_id"]]) for r in selected)
        primary_only = sum(r["execution_accuracy"] == 1 and not all(aux_by_trial[r["trial_id"]]) for r in selected)
        robustness.append([s, 150, nine_pass, num(nine_pass / 150 * 100), primary_only])
    errors = Counter((r["scenario_id"], str(r.get("error_type")), str(r.get("execution_error_code")))
                     for r in records if r["execution_status"] != "success")
    incidents = report["infrastructure_accounting"]
    timestamps = sorted(r["timestamp"] for r in records)
    p = stats["omnibus"]["p_value"]
    interpretation = ("Hasil omnibus melewati ambang0,05 dalam model pengujian yang ditetapkan; penentuan pasangan tetap mengikuti enam kontras berkoreksi Holm."
                      if p < .05 else "Hasil omnibus tidak melewati ambang0,05. Ini bukan bukti bahwa seluruh kondisi ekuivalen; effect size dan interval tetap perlu dibaca.")
    chapter5 = f"""# BAB V — HASIL DAN PEMBAHASAN

## 5.1 Kelengkapan dan integritas eksperimen

Bab ini disusun dari hasil aktual `{manifest['experiment_id']}`,bukan simulasi atau hasil versi terdahulu. Seluruh600 assigned trials mempunyai terminal EX biner,150per kondisi, 200per complexity,30 pertanyaan dan 5 repetitions. Audit ledger/export, assignments, prompt/result hashes, request settings, model/source/snapshot identity serta fingerprint database berhasil. Primary database tidak berubah. Waktu outcome pertama `{timestamps[0]}` dan terakhir `{timestamps[-1]}` memakai timestamp UTC.

Terdapat{incidents['request_attempts_started']} dispatch attempts dan{incidents['infrastructure_incidents']} infrastructure incidents pada benchmark. Incident tidak otomatis masuk EX nol. Jenis incident: `{json.dumps(incidents['incident_types'],ensure_ascii=False)}`. Dua belas smoke requests berada terpisah dan tidak masuk denominator600. Review completion dilaporkan oleh peneliti; nama/tanggal reviewer masih perlu dilengkapi sesuai BAB IV. Tidak mengklaim dokumen review independen yang belum tersedia.

## 5.2 Execution Accuracy menurut kondisi metadata

{primary_table}

Nilai EX tertinggi dalam benchmark tetap ini diperoleh {leaders}, sebesar{num(best)}%. Ini peringkat deskriptif dan tidak otomatis merupakan perbedaan signifikan. Penambahan anotasi dapat membantu, tidak mengubah hasil, atau mengganggu pilihan SQL. Kesimpulan tidak mensyaratkan S3 menjadi yang terbaik.

## 5.3 Hasil menurut kompleksitas

{table(['Kondisi','Kompleksitas','Benar','Trial','EX (%)'], [[r['scenario_id'],r['complexity'],r['correct'],r['trials'],num(r['execution_accuracy_percent'])] for r in desc['by_complexity']])}

Setiap condition/complexity cell memuat10 pertanyaan×5 repetitions=50 trial. Label complexity merupakan profil canonical reference. Perbandingan ini deskriptif; pertanyaan kompleks tidak identik dengan kebutuhan domain, dan domain tasks tidak tersebar merata pada semua complexity levels.

## 5.4 Perbandingan berpasangan dan ukuran efek

Omnibus paired permutation menghasilkan p={p:.6g},dengan analysis seed{stats['seed']}. {interpretation}

{table(['Kontras','Selisih EX (pp)','p exact','p Holm','95% pointwise CI (pp)'], [[r['contrast'],num(r['difference_pp']),f"{r['p_value']:.6g}",f"{r['p_value_holm']:.6g}",f"[{num(r['confidence_interval_95_pp'][0])}; {num(r['confidence_interval_95_pp'][1])}]"] for r in stats['contrasts']])}

Enam kontras sudah ditetapkan sebelum main outcomes. Semua30 question blocks, termasuk tied/zero-difference blocks, dipertahankan. Tidak memilih uji berdasarkan p yang lebih kecil. Interval bersifat pointwise, bukan simultaneous confidence set dan bukan inversi exact tests. Bootstrap menunjukkan sensitivitas terhadap komposisi fixed benchmark di bawah resampling model; tidak menjadikan30 soal purposive sebagai sampel acak seluruh kebutuhan bisnis.

## 5.5 Konsistensi lima pengulangan

{table(['Kondisi','Pertanyaan5/5benar','Pertanyaan0/5benar','Pertanyaan campuran'], consistency)}

Setiap baris merangkum30 pertanyaan. Konsistensi outcome berbeda dari identitas teks SQL: query berbeda dapat menghasilkan EX yang sama. Lima requests dapat menghasilkan SQL identik meskipun temperature positif. Kestabilan tidak diperlakukan sebagai tambahan jumlah pertanyaan independen.

## 5.6 Kebutuhan informasi dan aturan domain

{table(['Kondisi','Profil','Pertanyaan','Trial','EX (%)'], [[r['scenario_id'],r['profile'],r['questions'],r['trials'],num(r['execution_accuracy_percent'])] for r in report.get('cohort_descriptive',{}).get('primary_need',[])])}

Profil terdiri10 schema mapping,14 local semantics dan6 domain integration. Enam domain tasks berasal dari tiga keluarga aturan Sakila, bukan enam kebijakan independen. Profil berkaitan dengan complexity dan selection constraints; tidak digunakan untuk menambahkan significance tests baru. Efek paket metadata menggabungkan ketersediaan informasi, panjang, framing dan salience. Tidak mengklaim efek murni jumlah token atau kemampuan model-family tertentu.

## 5.7 Latency dan token

{table(['Kondisi','Rerata inference (ms)','Median inference (ms)','Rerata SQL (ms)','Rerata input tokens','Rerata output tokens'], [[s,num(r['inference_latency_ms']['mean']),num(r['inference_latency_ms']['median']),num(r['sql_execution_latency_ms']['mean']),num(r['input_tokens']['mean']),num(r['output_tokens']['mean'])] for s,r in scores.items()])}

Inference latency dan SQL execution latency diukur terpisah. Ukuran ini mendukung pembahasan dan bukan target optimisasi utama. Missing values, bila ada, tercatat sebagai unavailable pada measurements.csv dan tidak diganti angka buatan. Peningkatan biaya token tidak dengan sendirinya membuktikan penyebab perbedaan EX. Load/thermal/system state pada satu mesin juga membatasi tafsir latency.

## 5.8 Kegagalan keluaran dan eksekusi SQL

{table(['Kondisi','Error type','MySQL code','Jumlah'], [[*key,count] for key,count in sorted(errors.items())])}

Query yang berhasil dieksekusi tetapi hasilnya berbeda tetap salah; syntax/execution success bukan correctness. Jumlah success-but-wrong:{sum(r['execution_status']=='success' and r['execution_accuracy']==0 for r in records)}trial. Validasi SQL menolak statement yang tidak diizinkan; kegagalan model adalah outcome terminal dan tidak direpair. Pengelompokan kode error bersifat deskriptif. Penjelasan mekanisme berdasarkan contoh SQL adalah analisis kualitatif pascahasil dan tidak dipakai mengganti soal/metadata/model. Ledger menyimpan raw output dan extracted SQL agar contoh dapat diperiksa ulang.

## 5.9 Pemeriksaan pada delapan variasi data

Semua600 SQL tersimpan diuji pada8 cases,termasuk SQL yang gagal di primary. Tidak ada generation atau semantic repair baru. Tabel berikut menghitung kelulusan pada primary **dan** seluruh8 auxiliary cases, bukan mengganti primary EX dengan metrik lain.

{table(['Kondisi','Trial','Lulus seluruh9cases','Persentase','Primary benar tetapi gagal auxiliary'], robustness)}

Wrong variants yang dideklarasikan sebelum generation membantu memastikan cases dapat membedakan unit/grain, role, NULL/zero, kalender, numeric boundary, ranking dan tie-breaking. Finite cases tetap tidak membuktikan ekuivalensi universal. Query dengan hasil kosong atau nilai yang kebetulan sama pada satu instance tetap berpotensi memperoleh primary EX1; hasil auxiliary memberi bukti pembeda tambahan.

## 5.10 Pembahasan dan batas generalisasi

Temuan utama harus dibaca sebagai pengaruh empat paket anotasi terhadap satu local model terkuantisasi, satu database Sakila beku dan30 pertanyaan terkurasi berbahasa Indonesia. Penelitian tidak mengisolasi efek bahasa, model size, quantization atau panjang token secara tersendiri. S1/S2 memiliki coverage yang sama dan sebagian descriptions identik; detail tambahan tidak tersebar merata pada seluruh elements. Efek rata-rata dapat menyembunyikan perbedaan antarpertanyaan.

Hasil eksplorasi/diagnostik versi lama tetap menjadi sejarah engineering; prompt, soal dan comparator berubah pada revision03. Selisih skor versi lama-versi baru tidak dapat diperlakukan sebagai efek metadata saja. Studi ini bukan preregistration retrospektif. Analisis main memakai rencana yang dikunci sebelum600 outcomes; seluruh kondisi, contrasts dan non-significant findings tetap dilaporkan.

Statistical nonsignificance bukan bukti tidak ada efek; significance juga tidak menjamin manfaat praktis atau generalisasi workload. Identitas/tanggal reviewer perlu ditambahkan peneliti, tanpa mengubah tanggal pencatatan atau mengklaim signed-review evidence yang belum ada. Koreksi stimulus sesudah hasil membutuhkan versi/generation baru; gold-only correction setelah adjudication harus dilaporkan sebagai turunan dan tidak menimpa original evidence.

## 5.11 Jejak audit dan bahan penulisan

Sumber tabel: `analysis/report.json`,CSV pendamping,benchmark manifest/ledger dan `auxiliary/outcomes.jsonl`. Question/gold/prompt/snapshot hashes berada dalam manifest. Lampiran pertanyaan dan gold disertakan terpisah untuk peneliti; gold tidak pernah masuk model prompt. Semua angka pada bab ini berasal dari artifacts lengkap yang lolos integrity audit. Reviewer tidak boleh mengganti angka dengan ilustrasi atau menyebut hasil model lain sebagai hasil run ini.
"""
    for name, text in (("BAB_IV.md", chapter4), ("BAB_V.md", chapter5)):
        path = output / name
        if path.exists():
            raise FileExistsError("Choose a new thesis output directory; preserve authored manuscripts")
        path.write_text(text.rstrip() + "\n")
    qlines = ["# Lampiran pertanyaan dan reference SQL", "", "Gold hanya untuk evaluator/peneliti, tidak menjadi model input.", ""]
    for q in questions:
        qlines += [f"## {q.question_id} — {q.complexity}", "", q.question, "", "```sql", gold[q.question_id].sql, "```", ""]
    (output / "LAMPIRAN_QUESTIONS_GOLD.md").write_text("\n".join(qlines).rstrip() + "\n")
    appendix = ["# Lampiran technical schema aktual", ""]
    for t in schemas:
        appendix += [f"## {t['name']}", "", "```json", json.dumps(t, ensure_ascii=False, indent=2), "```", ""]
    (output / "LAMPIRAN_SCHEMA.md").write_text("\n".join(appendix).rstrip() + "\n")
    figure_dir = output / "figures"
    figure_dir.mkdir(exist_ok=True)
    figure_links = []
    for pth in sorted((run / "analysis").glob("*")):
        if pth.suffix in {".png", ".pdf"}:
            shutil.copyfile(pth, figure_dir / pth.name)
            figure_links.append(f"- [{pth.name}](figures/{pth.name})")
    (output / "FIGURES.md").write_text("# Gambar hasil aktual\n\n" + "\n".join(figure_links) + "\n")
    files = {str(p.relative_to(output)): hashlib.sha256(p.read_bytes()).hexdigest() for p in output.rglob("*") if p.is_file()}
    (output / "source-and-output-hashes.json").write_text(json.dumps({"experiment_id":manifest['experiment_id'],
        "source_commit":source['git_commit'], "files":files, "reviewer_identity_status":"pending_user_entry",
        "main_manifest_sha256":hashlib.sha256((run/'benchmark/manifest.json').read_bytes()).hexdigest()},sort_keys=True,indent=2)+"\n")
    return {"bab_iv":str(output/"BAB_IV.md"),"bab_v":str(output/"BAB_V.md"),"main_trials":600}
