"""Requirement-authored plausible wrong SQL, never model predictions."""
from __future__ import annotations

import re


def replace_expression(sql: str, before: str, after: str) -> str:
    # Fixed trusted fragments only. Accept parser-inserted whitespace without
    # deleting spaces inside SQL literals or reformatting an entire query.
    pattern = r"\s*".join(re.escape(char) for char in before if not char.isspace())
    result, count = re.subn(pattern, lambda _: after, sql, flags=re.IGNORECASE)
    if not count:
        raise ValueError("Mutation fragment no longer matches its reference: " + before)
    return result


def wrong_variants(question_id: str, sql: str) -> list[dict]:
    pilot_changes = {
        "P101": [("LIKE 'A%'", "LIKE '%A%'")],
        "P102": [(" AND ", " OR ")],
        "P103": [("COUNT(*)", "COUNT(DISTINCT f.special_features)")],
        "P104": [("DAYOFWEEK(return_date)", "DAYOFWEEK(rental_date)")],
        "P105": [("HOUR(rental_date)", "DAYOFMONTH(rental_date)")],
        "P106": [("COUNT(DISTINCT i.film_id)", "COUNT(i.inventory_id)")],
        "P107": [("active=1", "active=0")],
        "P108": [("COUNT(DISTINCT city_id)", "COUNT(*)")],
        "P109": [("staff s", "customer s")],
        "P110": [("y.actor_id<>1", "y.actor_id=1")],
        "P111": [("x.actor_id<y.actor_id", "x.actor_id<>y.actor_id")],
        "P112": [("COUNT(DISTINCT fc.category_id)", "COUNT(DISTINCT fa.film_id)")],
    }
    if question_id in pilot_changes:
        altered = sql
        for before, after in pilot_changes[question_id]:
            altered = replace_expression(altered, before, after)
        return [{"mutation_id": question_id + "-wrong-primary", "sql": altered,
                 "origin": "pilot requirement-authored before model outputs", "kind": "plausible_wrong_semantic_variant"}]
    changes = {
        "Q101": [("IS NULL", "IS NOT NULL")],
        "Q102": [("DISTINCT DATE(payment_date)", "DISTINCT payment_date")],
        "Q103": [("SELECT DISTINCT", "SELECT")],
        "Q104": [("MIN(release_year)", "MAX(release_year)")],
        "Q105": [("COUNT(DISTINCT film_id)", "COUNT(film_id)")],
        "Q106": [("SELECT DISTINCT", "SELECT")],
        "Q107": [("AVG(rental_duration)", "AVG(length)")],
        "Q108": [("SUM(length)/60", "SUM(length)")],
        "Q109": [("CHAR_LENGTH(description)", "LENGTH(description)")],
        "Q110": [("MAX(amount)", "SUM(amount)")],
        "Q111": [("COUNT(DISTINCT length)", "COUNT(length)")],
        "Q112": [("FROM customer", "FROM inventory")],
        "Q113": [("MIN(rental_rate)", "MIN(replacement_cost)")],
        "Q114": [("AVG(replacement_cost)", "AVG(rental_rate)")],
        "Q115": [("DISTINCT original_language_id", "DISTINCT language_id")],
        "Q116": [("LEFT JOIN film_category", "JOIN film_category")],
        "Q117": [("COUNT(*)", "COUNT(DISTINCT city_id)")],
        "Q118": [("LEFT JOIN city", "JOIN city")],
        "Q119": [("COUNT(DISTINCT r.customer_id)", "COUNT(r.customer_id)")],
        "Q120": [("AVG(length)", "AVG(rental_duration)")],
        "Q121": [("SUM(p.amount)", "COUNT(p.payment_id)")],
        "Q122": [("COUNT(DISTINCT i.film_id)", "COUNT(i.film_id)")],
        "Q123": [("DATE(payment_date)", "payment_date")],
        "Q124": [("LEFT JOIN rental", "JOIN rental")],
        "Q125": [(" HAVING COUNT(DISTINCT actor_id)>1", "")],
        "Q126": [("COUNT(DISTINCT a.city_id)", "COUNT(DISTINCT c.customer_id)")],
        "Q128": [("rental_duration", "length")],
        "Q129": [("f.original_language_id=l.language_id", "f.language_id=l.language_id")],
        "Q130": [(" GROUP BY c.active", " WHERE c.active=1 GROUP BY c.active")],
        "Q131": [("r.rental_date", "r.return_date")],
        "Q132": [(" AND EXISTS(", " OR EXISTS(")],
        "Q133": [(" WHERE active=0", "")],
        "Q134": [("NOT IN", "IN")],
        "Q135": [("COUNT(*) DESC", "COUNT(*) ASC")],
        "Q136": [(" WHERE x.staff_id=p.staff_id", "")],
        "Q137": [("TIMESTAMPDIFF(SECOND", "TIMESTAMPDIFF(DAY"), ("*86400", "")],
        "Q138": [("COUNT(*)", "COUNT(DISTINCT customer_id)")],
        "Q139": [("SUM(f.length)", "SUM(DISTINCT f.length)")],
        "Q140": [("i.store_id<>c.store_id", "i.store_id=c.store_id")],
        "Q141": [("p.staff_id<>r.staff_id", "p.staff_id=r.staff_id")],
        "Q143": [("NOT EXISTS", "EXISTS")],
        "Q144": [("s.active=0", "s.active=1")],
        "Q145": [("g.rental_duration=f.rental_duration AND ", "")],
        "Q147": [("COUNT(*)>7", "COUNT(*)>=7"), ("SUM(amount)>20.00", "SUM(amount)>=20.00")],
        "Q149": [("COUNT(*)>7", "COUNT(*)>=7"), ("SUM(amount)>20.00", "SUM(amount)>=20.00")],
        "Q150": [("DATEDIFF(r.return_date,r.rental_date)", "TIMESTAMPDIFF(DAY,r.rental_date,r.return_date)")],
        "Q151": [("DATEDIFF(r.return_date,r.rental_date)", "TIMESTAMPDIFF(DAY,r.rental_date,r.return_date)")],
        "Q152": [("COUNT(DISTINCT i.film_id)", "COUNT(DISTINCT r.rental_id)")],
        "Q153": [("SUM(p.amount)", "SUM(DISTINCT p.amount)")],
        "Q154": [("SELECT DISTINCT", "SELECT")],
        "Q155": [("length>120", "length>2")],
        "Q156": [("active=0", "active=1")],
        "Q157": [("store_id=1", "store_id=2")],
        "Q158": [("rental_duration>5", "rental_duration>=5")],
        "Q159": [("amount>10.00", "amount>=10.00")],
        "Q160": [("rating='PG-13'", "rating='PG'")],
    }
    if question_id == "Q146":
        altered = "SELECT DISTINCT i.inventory_id FROM inventory i JOIN rental r ON r.inventory_id=i.inventory_id WHERE r.return_date IS NOT NULL"
    elif question_id == "Q148":
        altered = "SELECT f.film_id,COUNT(i.inventory_id) FROM film f LEFT JOIN inventory i ON i.film_id=f.film_id AND i.store_id=1 GROUP BY f.film_id"
    elif question_id == "Q127":
        altered = "SELECT c.store_id,COALESCE(SUM(p.amount),0) FROM customer c LEFT JOIN payment p ON p.customer_id=c.customer_id GROUP BY c.store_id"
    elif question_id == "Q142":
        altered = "WITH ranked AS (SELECT film_id,rating,replacement_cost,ROW_NUMBER() OVER(PARTITION BY rating ORDER BY replacement_cost DESC,film_id) AS item_position FROM film) SELECT film_id,rating,replacement_cost FROM ranked WHERE item_position<=3"
    else:
        altered = sql
        for before, after in changes[question_id]:
            altered = replace_expression(altered, before, after)
    rows = [{"mutation_id": question_id + "-wrong-primary", "sql": altered,
             "origin": "requirement-authored before model outputs", "kind": "plausible_wrong_semantic_variant"}]
    if question_id == "Q115":
        rows.append({"mutation_id": question_id + "-constant-zero", "sql": "SELECT 0", "kind": "fixed-instance-shortcut", "origin": "auditor-inspired prospective counterexample, not an observed model output"})
    if question_id == "Q129":
        rows.append({"mutation_id": question_id + "-constant-zero", "sql": "SELECT language_id,name,0 FROM language", "kind": "fixed-instance-shortcut", "origin": "auditor-inspired prospective counterexample, not an observed model output"})
    if question_id in {"Q147", "Q149"}:
        rows.append({"mutation_id": question_id + "-rental-frequency", "sql": replace_expression(sql, "COUNT(*)>7", "COUNT(DISTINCT rental_id)>7"),
                     "kind": "wrong_event_grain", "origin": "source-defined payment event versus rental event, before outputs"})
        for label, before, after in (
            ("frequency-inclusive", "COUNT(*)>7", "COUNT(*)>=7"),
            ("amount-inclusive", "SUM(amount)>20.00", "SUM(amount)>=20.00"),
            ("active-only", "FROM payment WHERE", "FROM payment WHERE customer_id IN(SELECT customer_id FROM customer WHERE active=1) AND"),
            ("exclude-unlinked", "FROM payment WHERE", "FROM payment WHERE rental_id IS NOT NULL AND"),
        ):
            rows.append({"mutation_id": question_id + "-" + label, "sql": replace_expression(sql, before, after),
                         "kind": "source_rule_boundary", "origin": "individual source-defined reward condition, before outputs"})
    if question_id in {"Q150", "Q151"}:
        rows.append({"mutation_id": question_id + "-open-rental-accrual", "sql": replace_expression(sql, "r.return_date", "COALESCE(r.return_date,'2006-03-01 00:00:00')"),
                     "kind": "incorrect_open_return_component", "origin": "legacy component source-boundary, before outputs"})
        for label, before, after in (
            ("exclusive-cutoff", "r.rental_date<='2006-03-01 00:00:00'", "r.rental_date<'2006-03-01 00:00:00'"),
            ("end-of-day-cutoff", "'2006-03-01 00:00:00'", "'2006-03-01 23:59:59'"),
            ("censored-return", "r.rental_date<='2006-03-01 00:00:00'", "r.rental_date<='2006-03-01 00:00:00' AND r.return_date<='2006-03-01 00:00:00'"),
        ):
            rows.append({"mutation_id": question_id + "-" + label, "sql": replace_expression(sql, before, after),
                         "kind": "source_rule_boundary", "origin": "executable routine clock semantics, before outputs"})
    if question_id == "Q146":
        rows.append({"mutation_id": question_id + "-exclude-never-rented", "sql": sql + " AND EXISTS(SELECT 1 FROM rental h WHERE h.inventory_id=i.inventory_id)",
                     "kind": "source_rule_boundary", "origin": "existing never-rented copies remain available, before outputs"})
    return rows
