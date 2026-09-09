# Data dictionary

The reference the knowledge lookup retrieves from. Written for people
first — the retrieval is a side effect of it being well organised.

## case_id

The business key of a case record. Unique within a delivery.

Duplicates on `case_id` are never permitted. Where two rows share an id,
the source system has re-delivered a record; the later row is not a
correction and must not be treated as one. Corrections arrive with a new
id and a reference to the original.

## tenant

The organisational unit a case belongs to. Single letter code.

A constant value across a whole file is expected in a single-tenant
export and is not a defect there. In a combined export it means the
tenant filter was applied twice.

## amount

Monetary value in euro, two decimal places, decimal point.

Must read as a number. The recurring defect is an uppercase letter O in
place of a zero, which comes from OCR on scanned invoices and turns the
whole column into text. That is why the type check exists.

## quantity

Number of units. Integer, mandatory.

A missing quantity means the record was entered but not completed. It is
not zero. Treating it as zero silently understates every total built on
this column.

## note

Free text, optional.

High missing shares are normal and not a defect on their own — the field
is genuinely optional. It is reported at all because a sudden change in
the missing share usually indicates a change in the entry process.
