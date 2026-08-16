#!/usr/bin/env python3
"""Load a subset of CMS DE-SynPUF CSVs into db/demo.db.

Loads the first N unique DESYNPUF_IDs from the beneficiary summary file,
then pulls only the inpatient/outpatient claims belonging to that same
beneficiary subset so all three tables join consistently on DESYNPUF_ID.
"""

import csv
import sqlite3
from pathlib import Path

BENE_LIMIT = 2000

ROOT = Path(__file__).resolve().parent.parent
RAW_DIR = ROOT / "data" / "raw"
DB_PATH = ROOT / "db" / "demo.db"
SCHEMA_PATH = ROOT / "db" / "schema.sql"

BENEFICIARY_CSV = RAW_DIR / "DE1_0_2008_Beneficiary_Summary_File_Sample_1.csv"
INPATIENT_CSV = RAW_DIR / "DE1_0_2008_to_2010_Inpatient_Claims_Sample_1.csv"
OUTPATIENT_CSV = RAW_DIR / "DE1_0_2008_to_2010_Outpatient_Claims_Sample_1.csv"


def to_int(value):
    return int(value) if value not in (None, "") else None


def to_float(value):
    return float(value) if value not in (None, "") else None


def load_beneficiaries(conn, bene_ids):
    with BENEFICIARY_CSV.open(newline="") as f:
        reader = csv.DictReader(f)
        rows = []
        for row in reader:
            bene_id = row["DESYNPUF_ID"]
            if bene_id in bene_ids:
                continue
            if len(bene_ids) >= BENE_LIMIT:
                continue
            bene_ids.add(bene_id)
            rows.append((
                bene_id,
                row["BENE_BIRTH_DT"],
                row["BENE_DEATH_DT"] or None,
                row["BENE_SEX_IDENT_CD"],
                row["BENE_RACE_CD"],
                row["BENE_ESRD_IND"],
                row["SP_STATE_CODE"],
                row["BENE_COUNTY_CD"],
                to_int(row["BENE_HI_CVRAGE_TOT_MONS"]),
                to_int(row["BENE_SMI_CVRAGE_TOT_MONS"]),
                to_int(row["PLAN_CVRG_MOS_NUM"]),
                to_int(row["SP_ALZHDMTA"]),
                to_int(row["SP_CHF"]),
                to_int(row["SP_CHRNKIDN"]),
                to_int(row["SP_CNCR"]),
                to_int(row["SP_COPD"]),
                to_int(row["SP_DEPRESSN"]),
                to_int(row["SP_DIABETES"]),
                to_int(row["SP_ISCHMCHT"]),
                to_int(row["SP_OSTEOPRS"]),
                to_int(row["SP_RA_OA"]),
                to_int(row["SP_STRKETIA"]),
                to_float(row["MEDREIMB_IP"]),
                to_float(row["MEDREIMB_OP"]),
                to_float(row["MEDREIMB_CAR"]),
            ))

    conn.executemany(
        """
        INSERT INTO beneficiary (
            desynpuf_id, bene_birth_dt, bene_death_dt, bene_sex_ident_cd,
            bene_race_cd, bene_esrd_ind, sp_state_code, bene_county_cd,
            bene_hi_cvrage_tot_mons, bene_smi_cvrage_tot_mons, plan_cvrg_mos_num,
            sp_alzhdmta, sp_chf, sp_chrnkidn, sp_cncr, sp_copd, sp_depressn,
            sp_diabetes, sp_ischmcht, sp_osteoprs, sp_ra_oa, sp_strketia,
            medreimb_ip, medreimb_op, medreimb_car
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        rows,
    )
    conn.commit()
    return len(rows)


def first_nonempty(values):
    for v in values:
        if v:
            return v
    return None


def group_claims_by_id(csv_path, bene_ids):
    """CMS DE-SynPUF splits claims with many procedure/HCPCS codes across
    multiple rows ("segments") that share the same CLM_ID: CLM_PMT_AMT is
    partitioned across segments, while claim-level fields (dates, diagnosis,
    day count) are only populated on one segment. Group by CLM_ID, sum the
    payment amount, and take the first non-empty value for everything else.
    """
    claims = {}
    with csv_path.open(newline="") as f:
        reader = csv.DictReader(f)
        for row in reader:
            if row["DESYNPUF_ID"] not in bene_ids:
                continue
            claims.setdefault(row["CLM_ID"], []).append(row)
    return claims


def load_inpatient_claims(conn, bene_ids):
    claims = group_claims_by_id(INPATIENT_CSV, bene_ids)

    rows = [
        (
            clm_id,
            segments[0]["DESYNPUF_ID"],
            first_nonempty(r["CLM_FROM_DT"] for r in segments),
            first_nonempty(r["CLM_THRU_DT"] for r in segments),
            first_nonempty(r["CLM_ADMSN_DT"] for r in segments),
            first_nonempty(r["NCH_BENE_DSCHRG_DT"] for r in segments),
            sum(to_float(r["CLM_PMT_AMT"]) or 0.0 for r in segments),
            to_int(first_nonempty(r["CLM_UTLZTN_DAY_CNT"] for r in segments)),
            first_nonempty(r["ICD9_DGNS_CD_1"] for r in segments),
        )
        for clm_id, segments in claims.items()
    ]

    conn.executemany(
        """
        INSERT INTO inpatient_claims (
            clm_id, desynpuf_id, clm_from_dt, clm_thru_dt, clm_admsn_dt,
            nch_bene_dschrg_dt, clm_pmt_amt, clm_utlztn_day_cnt, icd9_dgns_cd_1
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        rows,
    )
    conn.commit()
    return len(rows)


def load_outpatient_claims(conn, bene_ids):
    claims = group_claims_by_id(OUTPATIENT_CSV, bene_ids)

    rows = [
        (
            clm_id,
            segments[0]["DESYNPUF_ID"],
            first_nonempty(r["CLM_FROM_DT"] for r in segments),
            first_nonempty(r["CLM_THRU_DT"] for r in segments),
            sum(to_float(r["CLM_PMT_AMT"]) or 0.0 for r in segments),
            first_nonempty(r["ICD9_DGNS_CD_1"] for r in segments),
        )
        for clm_id, segments in claims.items()
    ]

    conn.executemany(
        """
        INSERT INTO outpatient_claims (
            clm_id, desynpuf_id, clm_from_dt, clm_thru_dt, clm_pmt_amt, icd9_dgns_cd_1
        ) VALUES (?, ?, ?, ?, ?, ?)
        """,
        rows,
    )
    conn.commit()
    return len(rows)


def print_row_counts(conn):
    for table in ("beneficiary", "inpatient_claims", "outpatient_claims"):
        count = conn.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]
        print(f"{table}: {count} rows")


def run_sanity_check(conn):
    row = conn.execute(
        """
        SELECT
            AVG(medreimb_ip + medreimb_op + medreimb_car) AS avg_total_reimb,
            AVG(medreimb_ip) AS avg_ip_reimb,
            AVG(medreimb_op) AS avg_op_reimb,
            AVG(medreimb_car) AS avg_car_reimb
        FROM beneficiary
        """
    ).fetchone()
    print("\nSanity check — average reimbursement per beneficiary:")
    print(f"  total: ${row[0]:,.2f}")
    print(f"  inpatient: ${row[1]:,.2f}  outpatient: ${row[2]:,.2f}  carrier: ${row[3]:,.2f}")


def main():
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    if DB_PATH.exists():
        DB_PATH.unlink()

    conn = sqlite3.connect(DB_PATH)
    conn.executescript(SCHEMA_PATH.read_text())

    bene_ids = set()
    n_bene = load_beneficiaries(conn, bene_ids)
    n_ip = load_inpatient_claims(conn, bene_ids)
    n_op = load_outpatient_claims(conn, bene_ids)

    print(f"Loaded {n_bene} beneficiaries, {n_ip} inpatient claims, {n_op} outpatient claims")
    print_row_counts(conn)
    run_sanity_check(conn)

    conn.close()


if __name__ == "__main__":
    main()
