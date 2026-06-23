# 04 – SQL Advanced Cases

Fortgeschrittene SQL-Auswertungen auf einem kleinen E-Commerce-Datenmodell:
Umsatzanalysen, Kundensegmentierung und Churn-Erkennung mit SQLite.

## Datenmodell

Drei Tabellen mit referenzieller Integrität:

| Tabelle     | Inhalt                               | Datensätze |
|-------------|--------------------------------------|------------|
| `customers` | Kundenstamm (Name, Stadt)            | 5          |
| `products`  | Produktkatalog (Name, Preis)         | 4          |
| `orders`    | Bestellungen (Kunde, Produkt, Menge) | 14         |

Hinweis: Eine Kundin (Eva Lange) hat bewusst **keine** Bestellung – als Testfall für die Churn-Analyse.

## Queries

| Query                  | Fragestellung                        |
|------------------------|--------------------------------------|
| `revenue_total`        | Gesamtumsatz über alle Bestellungen  |
| `revenue_by_customer`  | Umsatz je Kunde, absteigend          |
| `revenue_by_city`      | Umsatz je Stadt inkl. Kundenanzahl   |
| `high_value_customers` | Kunden mit Umsatz > 500 €            |
| `product_analysis`     | Produkte nach Umsatz, mit Rang       |
| `churn_analysis`       | Kunden ohne Bestellung (LEFT JOIN)   |

## Kernergebnisse

- **Gesamtumsatz:** 5.586 €
- **Top-Kundin:** Carla (2.633 €), gefolgt von Anna (1.329 €) und Bernd (1.279 €)
- **Umsatzstärkste Stadt:** Berlin (3.962 € / 2 Kunden), vor Hamburg (1.279 €) und München (345 €)
- **Top-Produkt:** Notebook (3.596 €), vor Monitor, Tastatur und Maus
- **Churn:** Eva Lange (Hamburg) – 0 Bestellungen

## Stack

SQLite · VS Code mit SQLTools · reines SQL (keine externen Abhängigkeiten)
