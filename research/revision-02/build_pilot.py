"""Twelve separate natural diagnostic tasks; main business-rule families held out."""
from __future__ import annotations

import json
from pathlib import Path

from sakila_experiment.artifacts import canonical_json
from sakila_experiment.evaluation.structure import profile_sql

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "data/benchmarks/revision-02"

TASKS = [
    ("Film apa saja yang judulnya diawali huruf A?", "SELECT film_id,title FROM film WHERE title LIKE 'A%'", ["film_id", "title"], "film-content-discovery"),
    ("Berapa banyak film yang memiliki fitur Deleted Scenes sekaligus Behind the Scenes?", "SELECT COUNT(*) FROM film WHERE special_features LIKE '%Deleted Scenes%' AND special_features LIKE '%Behind the Scenes%'", ["jumlah_film"], "film-content-discovery"),
    ("Kategori mana yang memiliki sedikitnya lima judul film dengan fitur Commentaries?", "SELECT c.category_id,c.name,COUNT(*) FROM category c JOIN film_category fc ON fc.category_id=c.category_id JOIN film f ON f.film_id=fc.film_id WHERE f.special_features LIKE '%Commentaries%' GROUP BY c.category_id HAVING COUNT(*)>=5", ["category_id", "name", "jumlah_judul"], "film-content-discovery"),
    ("Berapa banyak pengembalian film yang tercatat pada hari Sabtu?", "SELECT COUNT(*) FROM rental WHERE DAYOFWEEK(return_date)=7", ["jumlah_pengembalian"], "rental-calendar-patterns"),
    ("Pada jam berapa paling banyak penyewaan dimulai?", "SELECT HOUR(rental_date),COUNT(*) FROM rental GROUP BY HOUR(rental_date) HAVING COUNT(*)>=ALL(SELECT COUNT(*) FROM rental GROUP BY HOUR(rental_date))", ["jam", "jumlah_penyewaan"], "rental-calendar-patterns"),
    ("Berapa banyak judul film berbeda yang disewa pada masing-masing bulan?", "SELECT DATE_FORMAT(r.rental_date,'%Y-%m'),COUNT(DISTINCT i.film_id) FROM rental r JOIN inventory i ON i.inventory_id=r.inventory_id GROUP BY DATE_FORMAT(r.rental_date,'%Y-%m')", ["bulan", "jumlah_judul"], "rental-calendar-patterns"),
    ("Pelanggan aktif mana yang alamat emailnya berakhiran .org?", "SELECT customer_id,first_name,email FROM customer WHERE active=1 AND email LIKE '%.org'", ["customer_id", "first_name", "email"], "contact-geography-records"),
    ("Berapa banyak kota berbeda yang tercatat untuk masing-masing kode pos?", "SELECT postal_code,COUNT(DISTINCT city_id) FROM address GROUP BY postal_code", ["postal_code", "jumlah_kota"], "contact-geography-records"),
    ("Di negara mana saja terdapat alamat staf?", "SELECT DISTINCT co.country_id,co.country FROM country co JOIN city ci ON ci.country_id=co.country_id JOIN address a ON a.city_id=ci.city_id JOIN staff s ON s.address_id=a.address_id", ["country_id", "country"], "contact-geography-records"),
    ("Pemeran mana yang pernah bermain bersama pemeran ber-ID 1?", "SELECT DISTINCT a.actor_id,a.first_name,a.last_name FROM film_actor x JOIN film_actor y ON y.film_id=x.film_id JOIN actor a ON a.actor_id=y.actor_id WHERE x.actor_id=1 AND y.actor_id<>1", ["actor_id", "first_name", "last_name"], "actor-collaboration"),
    ("Berapa banyak pasangan pemeran berbeda yang pernah berbagi judul film?", "SELECT COUNT(DISTINCT x.actor_id,y.actor_id) FROM film_actor x JOIN film_actor y ON x.film_id=y.film_id AND x.actor_id<y.actor_id", ["jumlah_pasangan"], "actor-collaboration"),
    ("Pemeran mana yang film-filmnya menjangkau sedikitnya dua belas kategori?", "SELECT a.actor_id,a.first_name,COUNT(DISTINCT fc.category_id) FROM actor a JOIN film_actor fa ON fa.actor_id=a.actor_id JOIN film_category fc ON fc.film_id=fa.film_id GROUP BY a.actor_id HAVING COUNT(DISTINCT fc.category_id)>=12", ["actor_id", "first_name", "jumlah_kategori"], "actor-collaboration"),
]


def main():
    questions, gold, cards = [], [], []
    for index, (question, sql, columns, family) in enumerate(TASKS, 101):
        identity = f"P{index:03}"
        profile = profile_sql(sql)
        question += " Keluaran (berurutan): " + ", ".join(columns) + "."
        questions.append({"question_id": identity, "question": question, "complexity": profile.complexity, "schema_references": []})
        gold.append({"question_id": identity, "sql": sql, "column_count": len(columns), "ordered": False, "approximate_columns": [], "date_columns": [], "review_status": "draft", "semantic_notes": "Separate diagnostic task; independent reference review pending. Main business-rule families held out."})
        cards.append({"question_id": identity, "semantic_family": family, "primary_business_rule_family": None,
                      "structural_profile": profile.document(), "human_review_status": "pending", "construction_status": "draft"})
    for name, rows in [("pilot.questions.jsonl", questions), ("pilot.gold-a.jsonl", gold), ("pilot.cards.jsonl", cards)]:
        (OUT / name).write_bytes(b"".join(canonical_json(row) for row in rows))
    packet = ROOT / "runs/revision-02/review-packets/pilot-only-02"
    packet.mkdir(parents=True, exist_ok=True)
    (packet / "questions.jsonl").write_bytes(b"".join(canonical_json({"question_id": q["question_id"], "question": q["question"]}) for q in questions))
    print(json.dumps({"pilot_questions": len(questions), "inference_trials_planned": 180, "generation_requests": 0}))


if __name__ == "__main__":
    main()
