# 04 – SQL Advanced Cases

Aufbauend auf `03_sql_foundations`, aber mit einem erweiterten Datenmodell aus drei
Tabellen. Während `03` mit einer einzelnen `orders`-Tabelle und einem fertigen
`order_value`-Feld arbeitet, wird der Umsatz hier über einen JOIN aus `quantity ×
unit_price` berechnet. Damit lassen sich realistischere Geschäftsfragen mit JOINs,
Aggregation, Window Functions und CTEs beantworten.

## Datenmodell

| Tabelle     | Beschreibung                                    |
|-------------|-------------------------------------------------|
| `customers` | Kunden mit Name, Stadt und Anmeldedatum         |
| `products`  | Produkte mit Kategorie und Einzelpreis          |
| `orders`    | Bestellungen (Verknüpfung Kunde ↔ Produkt, Menge) |

Testdaten: 5 Kunden in 3 Städten, 4 Produkte, 14 Bestellungen. Ein Kunde (Eva Lange)
hat bewusst keine Bestellung – als Fall für die Churn-Analyse.

## Queries

| Datei                       | Technik                          | Fragestellung                                  |
|-----------------------------|----------------------------------|------------------------------------------------|
| `revenue_total.sql`         | JOIN + SUM                       | Gesamtumsatz über alle Bestellungen            |
| `revenue_by_customer.sql`   | JOIN + GROUP BY                  | Umsatz pro Kunde (absteigend)                  |
| `revenue_by_city.sql`       | JOIN + GROUP BY                  | Umsatz und Kundenzahl pro Stadt                |
| `high_value_customers.sql`  | GROUP BY + HAVING                | Kunden mit Umsatz über 500 €                   |
| `product_analysis.sql`      | Window Function (`RANK()`)       | Produktumsatz mit Rangfolge                    |
| `churn_analysis.sql`        | LEFT JOIN + CTE                  | Kunden ganz ohne Bestellung                    |

## Kernergebnisse

- Gesamtumsatz: **5.586 €**
- Umsatzstärkste Stadt: **Berlin** (3.962 €, 2 Kunden)
- Top-Kundin: **Carla Schmidt** (2.633 €)
- Bestseller: **Notebook** (3.596 €, Rang 1)
- Churn-Kandidatin: **Eva Lange** (0 Bestellungen)

## Ausführen

```bash
sqlite3 demo.db ".read schema.sql" ".read seed_data.sql" ".read queries/revenue_total.sql"
```