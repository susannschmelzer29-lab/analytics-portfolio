# Checking rules

## Missing values

Reported per column, graded by share: from 5 % amber, from 30 % red.

The thresholds are a judgement, not a standard. They live at the top of
`checks.py` so they can be argued with rather than discovered by reading
the code.

## Duplicates over the business key

Checked over the business key, never over every column.

Two rows differing only in a timestamp are the same row in business
terms. A check across all columns would pass them, which is the single
most common mistake in duplicate detection.

## Type consistency

Expected base types are named as `number`, `text` or `date`, not as
concrete numpy dtypes — otherwise the check breaks on every pandas
upgrade without anything actually being wrong.

## Constant columns

A column holding one value carries no information. Usually an export
defect rather than a data defect, so it is amber rather than red.

## What the rules never do

They do not repair. No filling of missing values, no removal of
duplicates, no type coercion in the raw data. An automation that silently
corrects turns a visible data error into an invisible one.
