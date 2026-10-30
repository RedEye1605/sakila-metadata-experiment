"""Write an implementation-only packet from the actual frozen run; no EX claims."""
from __future__ import annotations

import json
from pathlib import Path

from sakila_experiment.artifacts import canonical_json, publish_artifact, sha256_bytes
from sakila_experiment.contracts import load_gold, load_questions

ROOT = Path(__file__).resolve().parents[2]
RUN = ROOT / "runs/qwen35-9b/main-01"


def main():
    manifest_bytes = (RUN / "benchmark/manifest.json").read_bytes()
    manifest = json.loads(manifest_bytes)
    freeze = json.loads((RUN / "benchmark/freeze.json").read_bytes())
    if freeze["manifest_sha256"] != sha256_bytes(manifest_bytes) or freeze["generation_requests"] != 0:
        raise ValueError("Writing packet requires the actual zero-generation main freeze")
    out = RUN / "writing"
    paths = {name: ROOT / value for name, value in manifest["instrument_paths"].items()}
    questions, gold = load_questions(paths["questions"]), load_gold(paths["gold"])
    backend, settings = manifest["backend_evidence"], manifest["inference_config"]
    amendment = manifest["execution_amendment"]
    budgets = manifest["complete_main_prompt_budgets"]
    snapshots = ROOT / "runs/revision-02/metadata/preparation-03/snapshots"
    metadata = ["# Lampiran metadata dan common prompt aktual", "",
                "JSON ditata ulang untuk dibaca. Hash merujuk payload frozen yang benar-benar diberikan kepada model.", ""]
    for scenario in ("S0", "S1", "S2", "S3"):
        folder = snapshots / scenario
        snap = json.loads((folder / "manifest.json").read_bytes())
        payload = json.loads((folder / snap["payload_file"]).read_bytes())
        metadata += [f"## {scenario}", "", f"SHA-256: `{snap['snapshot_sha256']}`", "", "```json",
                     json.dumps(payload, ensure_ascii=False, indent=2), "```", ""]
    metadata += ["## Common prompt", "", "```text", paths["prompt_template"].read_text(), "```", ""]
    publish_artifact(out / "LAMPIRAN_METADATA_PROMPT.md", "\n".join(metadata).encode())
    dataset = ["# Lampiran30pertanyaan dan reference SQL", "",
               "Gold hanya milik evaluator/peneliti dan tidak diberikan kepada LLM. Review completion dinyatakan oleh peneliti; nama dan tanggal reviewer diisi peneliti.", ""]
    for question in questions:
        profile = manifest["question_attributes"][question.question_id]
        dataset += [f"## {question.question_id} — {question.complexity}", "", question.question, "",
                    f"Canonical Spider level: `{profile['spider_level']}`; information need: `{profile['primary_need']}`.", "",
                    "```sql", gold[question.question_id].sql, "```", ""]
    publish_artifact(out / "LAMPIRAN_QUESTIONS_GOLD.md", "\n".join(dataset).encode())
    baseline = json.loads((ROOT / "runs/database/baseline.json").read_bytes())
    publish_artifact(out / "LAMPIRAN_SCHEMA.json", canonical_json(baseline["technical_schema"]))
    text = f"""# BAB IV — Bahan perancangan dan implementasi Qwen3.5-9B

Judul tetap: **Analisis Pengaruh Metadata terhadap Execution Accuracy pada Sistem Text-to-SQL Berbasis Large Language Model (Studi Kasus: Basis Data Sakila)**.

Dokumen ini berisi implementasi dan preflight aktual run `{manifest['experiment_id']}`. Hasil600trial belum dinyatakan selesai di dokumen ini. BABV harus diambil dari `../analysis/report.md` dan `../thesis/BAB_V.md` setelah pipeline lengkap; jangan mengisi angka perkiraan atau memakai hasil model lama sebagai hasil run baru.

## 4.1 Kedudukan instrumen dan metodologi

Pipeline adalah instrumen eksperimen kuantitatif analitis. Delapan tahap penelitian tetap studi literatur, penyusunan anotasi metadata, penyusunan dataset pengujian, perancangan pipeline, implementasi pipeline, pengujian Text-to-SQL, analisis hasil, dan penarikan kesimpulan/saran. Instalasi Sakila, pemeriksaan hardware dan pemilihan model merupakan prasyarat engineering. Penelitian tidak mengembangkan model atau produk chatbot dan tidak melakukan fine-tuning sendiri.

## 4.2 Arsitektur dua fase

```mermaid
flowchart TD
  DB[MySQL Sakila] --> ING[DataHub ingestion]
  ING --> CAT[DataHub catalog dan annotations]
  CAT --> MCP[DataHub MCP server]
  MCP --> CLIENT[Python MCP client]
  CLIENT --> VALID[Normalisasi dan validasi metadata]
  VALID --> SNAP[Frozen S0 S1 S2 S3 dan provenance SHA256]
```

```mermaid
flowchart TD
  Q[Pertanyaan Indonesia] --> P[Prompt builder Python]
  S[Frozen snapshot] --> P
  P --> L[Local Qwen3.5 9B]
  L --> RAW[Durable raw response dan final SQL]
  RAW --> SAFE[Parser dan SQL safety]
  SAFE --> MYSQL[Read only MySQL]
  MYSQL --> EX[EX comparator]
  GOLD[Gold evaluator terisolasi] --> EX
  EX --> LOG[Append only ledger]
  LOG --> A[Analisis berpasangan dan laporan]
```

MCP dipakai pada persiapan metadata. LLM menerima common instructions, snapshot, pertanyaan dan formatting rules. LLM tidak memperoleh tool, akses database, gold, hasil evaluasi, history atau feedback eksekusi. Python memiliki akses database dan mengendalikan seluruh trial. Raw MCP receipts, normalisasi deterministic dan snapshot hashes tetap dipertahankan.

## 4.3 Database dan metadata

MySQL aktual `{manifest['mysql_version']}`. Schema SHA-256 `{manifest['database_schema_sha256']}`; data SHA-256 `{manifest['database_data_sha256']}`. Database/data tetap identik pada empat kondisi. S0memuat16base tables,90columns,PK/FK dan hubungan; S1menambah deskripsi singkat pada106elemen; S2mempertahankan coverage dengan detail bersumber; S3mempertahankan S2dan menambah3definisi domain. Kontrol meliputi scope/order/serialization, bahasa, common prompt, soal, model/settings, safety dan evaluator. Panjang/token dicatat tanpa pemotongan; ini bagian perbedaan paket metadata.

Seluruh metadata dan prompt terdapat pada [lampiran aktual](LAMPIRAN_METADATA_PROMPT.md), technical schema pada [schema](LAMPIRAN_SCHEMA.json). Annotations tidak memuat gold SQL atau pola solusi khusus soal.

## 4.4 Dataset dan validasi reference

Tiga puluh soal sama dengan revision03:10simple,10medium,10complex. Canonical SQL mengikuti adapter MySQL dari routine hardness Spider yang commit-nya dikunci, dengan10easy,10medium,5hard,5extra. Penggabungan hard/extra menjadi complex merupakan aturan lokal yang dinyatakan eksplisit. Label menjelaskan canonical reference, bukan minimum semua SQL ekuivalen atau jaminan kesulitan model. Profil kebutuhan informasi terpisah terdiri10schema mapping,14local semantics,6domain integration. Tiga soal meminta ordering/ranking, termasuk dua top-k. Soal memakai kebutuhan bisnis tanpa footer kolom teknis atau SQL recipe; definisi domain berada di metadata.

Reference A/B dan56critical semantic mutants diperiksa ulang pada primary+8isolated variants memakai source/runtime saat ini. Bukti berada pada `../../reference-checks-01/`. Database utama tidak dimutasi. Finite witnesses dan agreement AI bukan bukti ekuivalensi universal atau pengganti review manusia. Review completion atas stimulus sama tetap berdasarkan pernyataan peneliti yang sudah direkam. **Nama/tanggal reviewer: diisi peneliti**. Seluruh soal, canonical level dan gold ada pada [lampiran dataset](LAMPIRAN_QUESTIONS_GOLD.md).

## 4.5 Model dan inference yang dikunci

Upstream `{amendment['upstream_model']}`; publisher quantization `{backend['model_repository']}`; revision `{backend['model_repository_revision']}`; SHA-256 `{manifest['model_version_or_hash']}`. Model file Q4_K_M telah diverifikasi terhadap bytes dan dipasang read-only. Backend `{backend['build_info']}` memakai image digest-pinned, GPU layers `{backend['gpu_layers']}`, CPU threads `{backend['threads']}`. Observasi hardware preflight: `{backend['resource_observations']['gpu']}`.

Context `{settings['context_tokens']}`, max output `{settings['max_output_tokens']}`, safety margin `{settings['safety_margin_tokens']}`, reasoning on dengan budget2048, temperature `{settings['temperature']}`, top-p `{settings['top_p']}`, top-k `{settings['top_k']}`, min-p0, repeat penalty1. Satu slot, tanpa prompt cache/context shift/continuous batching. Reasoning disimpan dalam raw response; final message.content dipakai untuk SQL. Setiap trial merupakan satu kesempatan tanpa semantic repair. HTTP timeout `{settings['timeout_s']}`detik. Publisher leaderboard dengan budget lain tidak dianggap perkiraan EXlokal.

Seluruh `{len(budgets)}` kombinasi main prompt diperiksa dengan tokenizer/chat template backend aktual, maksimum `{max(b['input_tokens'] for b in budgets)}`input tokens. Preflight ini melakukan0generation, sehingga tidak ada pilot capability atau smoke generation baru.

## 4.6 Safety dan evaluasi EX

Dedicated SELECT-only account, single-statement MySQL AST policy `{manifest['database_config']['sql_policy_version']}`, restricted functions, query timeout `{manifest['database_config']['query_timeout_ms']}`ms, connection/read timeout, batas100000rows dan64MiB diterapkan. Invalid/unauthorized SQL atau hasil salah mendapatEX0. Infrastructure failures dicatat terpisah dan menghentikan run; tidak diam-diam masuk denominator sebagai kesalahan model.

Comparator `{manifest['comparator_version']}` menguji satu bijeksi kolom global, sehingga pertukaran posisi kolom dapat setara. Aliases diabaikan, hubungan nilai seluruh baris dan duplicate multiplicities dipertahankan; tidak mengurutkan setiap kolom secara independen. NULL, integer/decimal, floating tolerance serta date/time mengikuti kontrak. Row order hanya wajib bila diminta; ranking/top-k memakai tie convention yang sama. Empty results tetap diperiksa jumlah kolomnya dan mempunyai keterbatasan bukti semantik. Raw output, extraction, rejection, SQL/result/gold hashes dan mapping disimpan.

## 4.7 Orkestrasi dan reproduksibilitas

30×4×5=600trial;150per kondisi dan200per complexity. Trial IDs mengandung question/scenario/repetition dan dinamespace oleh experiment ID. Randomized repetition blocks memakai order seed `{manifest['experiment_config']['order_seed']}`; inference seed base `{manifest['experiment_config']['inference_seed_base']}` memberi paired seeds lintas kondisi. Tiap request independen; SQL dapat tetap sama antar pengulangan.

Ledger SQLite append-only menyimpan dispatch, response sebelum evaluation, incident dan terminal outcome. Resume tidak meregenerasi completed/model-failure trials. Dispatch ambigu memerlukan rekonsiliasi operator; tidak mengklaim exactly-once inference. Sampler/seed/cache aktual diperiksa dari setiap respons main yang sudah tersimpan melalui GET tanpa request generation baru. Service systemd memakai exclusive lock, sleep inhibition dan Restart=no. Peneliti memantau run sendiri; Codex tidak menjalankan monitor loop sesudah launch.

Source commit `{manifest['source_version']['git_commit']}`; source tree SHA-256 `{manifest['source_version']['source_tree_sha256']}`; run manifest SHA-256 `{sha256_bytes(manifest_bytes)}`. Manifest mencatat Python/packages, model/backend/template, database, metadata provenance/snapshots, questions/gold, settings, seeds dan hashes. Secrets terpisah dari konfigurasi/repository. Output aktual tetap lokal.

## 4.8 Analisis dan amendment yang harus dijelaskan

EXscenario=correct/150×100%. Skor question–scenario=successes/5; unit berpasangan adalah30pertanyaan, bukan600independent questions. Rencana yang dipertahankan menggunakan omnibus within-question permutation, enam exact sign-flip contrasts dengan koreksi Holm, effect size dalam percentage points dan whole-question stratified bootstrap untuk pointwise95%interval. Analysis seed `{manifest['experiment_config']['analysis_seed']}`. Profil complexity/need/family, konsistensi, token dan latency bersifat pendukung. Analisis tidak dipilih berdasarkan p-value yang diinginkan.

Peneliti memilih model ini setelah hasil main sebelumnya dan pilot Qwen3-8B diketahui, lalu secara eksplisit meniadakan pilot/smoke generation tambahan. Run ini disebut replikasi dengan model pilihan peneliti, tanpa klaim capability admission, preregistration retrospektif atau jaminan significance. Hasil lama tetap diarsipkan. Cross-run differences menggabungkan model dan inference package; pengaruh metadata diuji di dalam run baru dengan faktor lain tetap. EXprimary pada satu database dilaporkan terpisah dari4800auxiliary SQL outcomes tanpa generation baru. BABVditulis hanya dari hasil aktual lengkap.
"""
    publish_artifact(out / "BAB_IV_IMPLEMENTASI_QWEN35_9B.md", text.encode())
    publish_artifact(out / "ANALYSIS_PLAN.md", paths["analysis_protocol"].read_bytes())
    publish_artifact(out / "EXECUTION_AMENDMENT.json", canonical_json(amendment))
    hashes = {p.name: sha256_bytes(p.read_bytes()) for p in out.iterdir() if p.is_file() and p.name != "writing-provenance.json"}
    publish_artifact(out / "writing-provenance.json", canonical_json({"main_manifest_sha256": sha256_bytes(manifest_bytes), "files": hashes,
        "results_claimed": False, "reviewer_identity_status": "pending_user_entry"}))
    print(json.dumps({"status": "implementation_writing_packet_created", "results_claimed": False, "files": len(hashes)}))


if __name__ == "__main__":
    main()
