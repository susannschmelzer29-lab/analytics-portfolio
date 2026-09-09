"""Generate the synthetic source data for this project.

Why synthetic and why generated rather than committed as a fixed dump
--------------------------------------------------------------------
Real service-delivery data from a social-services provider is special
category personal data under Art. 9 GDPR. It cannot be published in a
portfolio repository, and no anonymisation of a small district-level
dataset is safe enough to change that.

So the data is generated. Two consequences that are deliberate:

1. The generator is **seeded** (`random.seed(RANDOM_SEED)`), so every run
   produces byte-identical CSVs. Without that, `dbt test` results would
   drift between runs and the CI would be meaningless.
2. The generator plants **known defects** — the same idea as a canary
   file. Some tests are expected to catch them; see `docs/data_quality.md`.
   A dataset in which everything is clean cannot demonstrate that the
   tests work.

Run:  python scripts/generate_seeds.py
"""

from __future__ import annotations

import csv
import random
from datetime import date, timedelta
from pathlib import Path

RANDOM_SEED = 20260909
SEED_DIR = Path(__file__).resolve().parents[1] / "dbt" / "seeds"

START = date(2025, 1, 1)
END = date(2025, 12, 31)

N_CLIENTS = 180
N_STAFF = 34

COST_CENTRES = [
    # (id, name, funding_source)
    ("CC10", "Community Assistance", "Integration Assistance"),
    ("CC20", "Day Support Centre", "Integration Assistance"),
    ("CC30", "School Support", "Youth Welfare"),
    ("CC40", "Counselling Centre", "Municipal Funding"),
    ("CC50", "Leisure and Sport", "Donations"),
]

SERVICE_TYPES = [
    # (code, name, billable, rate_per_hour_eur)
    ("AST", "Assistance Hour", True, 48.50),
    ("BEG", "Appointment Support", True, 44.00),
    ("SCH", "School Support", True, 39.75),
    ("BER", "Counselling Session", True, 62.00),
    ("GRP", "Group Session", True, 21.00),
    ("DOK", "Documentation", False, 0.00),
    ("FAL", "Case Review", False, 0.00),
]

ROLES = ["Specialist", "Assistant", "Management", "Administration"]


def daterange_workdays(start: date, end: date) -> list[date]:
    days = []
    d = start
    while d <= end:
        if d.weekday() < 5:
            days.append(d)
        d += timedelta(days=1)
    return days


def write_csv(name: str, header: list[str], rows: list[list]) -> None:
    SEED_DIR.mkdir(parents=True, exist_ok=True)
    path = SEED_DIR / f"{name}.csv"
    with path.open("w", newline="", encoding="utf-8") as f:
        # Fixed at LF: csv.writer defaults to CRLF, which would make this
        # generator produce different bytes on Linux CI vs local Windows
        # checkouts and break the byte-identity check in CI.
        w = csv.writer(f, lineterminator="\n")
        w.writerow(header)
        w.writerows(rows)
    print(f"{path.name}: {len(rows)} rows")


def main() -> None:
    rnd = random.Random(RANDOM_SEED)
    workdays = daterange_workdays(START, END)

    # --- cost centres -----------------------------------------------------
    write_csv("raw_cost_centres", ["cost_centre_id", "name", "funding_source"],
              [list(c) for c in COST_CENTRES])

    # --- service types ----------------------------------------------------
    write_csv(
        "raw_service_types",
        ["service_type_code", "name", "is_billable", "rate_per_hour_eur"],
        [[c, n, "true" if b else "false", f"{r:.2f}"] for c, n, b, r in SERVICE_TYPES],
    )

    # --- staff ------------------------------------------------------------
    staff = []
    for i in range(1, N_STAFF + 1):
        sid = f"S{i:03d}"
        role = rnd.choices(ROLES, weights=[60, 25, 8, 7])[0]
        cc = rnd.choice(COST_CENTRES)[0]
        hours = rnd.choice([19.5, 25.0, 30.0, 35.0, 39.0])
        start = START if rnd.random() < 0.8 else START + timedelta(days=rnd.randint(20, 200))
        # around 10 % of staff leave the organisation during the year
        end = "" if rnd.random() > 0.10 else (start + timedelta(days=rnd.randint(90, 300))).isoformat()
        staff.append([sid, role, cc, f"{hours:.1f}", start.isoformat(), end])
    write_csv("raw_staff",
              ["staff_id", "role", "cost_centre_id", "contract_hours_week", "start_date", "end_date"],
              staff)

    # --- clients ----------------------------------------------------------
    clients = []
    for i in range(1, N_CLIENTS + 1):
        cid = f"K{i:04d}"
        entry = START if rnd.random() < 0.7 else START + timedelta(days=rnd.randint(10, 300))
        exit_ = "" if rnd.random() > 0.15 else (entry + timedelta(days=rnd.randint(60, 320))).isoformat()
        care_level = rnd.choice([1, 2, 3, 4, 5])
        district = rnd.choice(["Schwerin-Mitte", "Schwerin-Sued", "Wismar", "Rural District"])
        clients.append([cid, entry.isoformat(), exit_, care_level, district])
    write_csv("raw_clients",
              ["client_id", "entry_date", "exit_date", "care_level", "district"],
              clients)

    # --- services ---------------------------------------------------------
    services = []
    seq = 0

    def active_on(record: list, day: date, field_start: int, field_end: int) -> bool:
        """Was this client / staff member on the books on this day?

        Without this check the generator produces services delivered to
        clients before their entry and after their exit — then the
        corresponding tests fire thousands of times and become
        meaningless. This exact mistake was in the first draft.
        """
        start = date.fromisoformat(record[field_start])
        if day < start:
            return False
        if record[field_end]:
            return day <= date.fromisoformat(record[field_end])
        return True

    for day in workdays:
        # Holiday periods are thinner — otherwise the time series would be
        # unrealistically flat
        factor = 0.45 if day.month in (7, 8) or (day.month == 12 and day.day > 20) else 1.0
        # Built from random() and randint() only, NOT from gauss().
        #
        # Python guarantees that a seeded Mersenne Twister reproduces the
        # same random() sequence across versions. It makes no such promise
        # for gauss(), whose algorithm may change. Since the CI regenerates
        # these files and byte-compares them against the committed ones,
        # a gauss() change on a newer Python would fail the build for a
        # reason that has nothing to do with the data.
        #
        # Sum of three uniforms: roughly bell-shaped, entirely portable.
        spread = (rnd.random() + rnd.random() + rnd.random() - 1.5) * 12
        count = int((48 + spread) * factor)

        active_clients_today = [c for c in clients if active_on(c, day, 1, 2)]
        active_staff_today = [s for s in staff if active_on(s, day, 4, 5)]
        if not active_clients_today or not active_staff_today:
            continue

        for _ in range(max(count, 0)):
            seq += 1
            client = rnd.choice(active_clients_today)
            staff_member = rnd.choice(active_staff_today)
            code, _, billable, _ = rnd.choices(
                SERVICE_TYPES, weights=[30, 12, 18, 6, 14, 14, 6]
            )[0]
            minutes = rnd.choice([30, 45, 60, 60, 90, 120, 180])
            services.append([f"L{seq:06d}", client[0], staff_member[0], day.isoformat(),
                             code, minutes])

    # --- deliberately planted defects --------------------------------------
    # They are the reason the tests prove something. Documented in
    # docs/data_quality.md; each defect has a test that catches it.
    defects = 0

    # 1) Duplicate: the same service record delivered twice
    services.append(list(services[100]))
    defects += 1

    # 2) Service delivered to a client BEFORE their entry
    early_client = [c for c in clients if c[1] > START.isoformat()][0]
    services.append([f"L{seq+1:06d}", early_client[0], staff[0][0],
                     (date.fromisoformat(early_client[1]) - timedelta(days=14)).isoformat(),
                     "AST", 60])
    defects += 1

    # 3) Negative duration (sign error in the source system)
    services.append([f"L{seq+2:06d}", clients[5][0], staff[1][0],
                     date(2025, 6, 11).isoformat(), "BEG", -45])
    defects += 1

    # 4) Orphan foreign key: staff member does not exist
    services.append([f"L{seq+3:06d}", clients[6][0], "S999",
                     date(2025, 6, 12).isoformat(), "AST", 60])
    defects += 1

    # 5) Unknown service code
    services.append([f"L{seq+4:06d}", clients[7][0], staff[2][0],
                     date(2025, 6, 13).isoformat(), "XXX", 60])
    defects += 1

    write_csv("raw_services",
              ["service_id", "client_id", "staff_id", "service_date",
               "service_type_code", "duration_minutes"],
              services)

    print(f"\n{defects} defects planted on purpose — see docs/data_quality.md")


if __name__ == "__main__":
    main()
