-- Schema for the CMS DE-SynPUF artifact ingestion demo.
-- Only the fields needed for: total reimbursement per beneficiary,
-- inpatient admission rate, average length of stay, and chronic
-- condition prevalence are modeled. Diagnosis/procedure/HCPCS columns
-- are trimmed to the primary diagnosis (ICD9_DGNS_CD_1) only.

PRAGMA foreign_keys = ON;

DROP TABLE IF EXISTS outpatient_claims;
DROP TABLE IF EXISTS inpatient_claims;
DROP TABLE IF EXISTS beneficiary;

CREATE TABLE beneficiary (
    desynpuf_id             TEXT PRIMARY KEY,
    bene_birth_dt            TEXT,
    bene_death_dt             TEXT,
    bene_sex_ident_cd        TEXT,
    bene_race_cd             TEXT,
    bene_esrd_ind            TEXT,
    sp_state_code            TEXT,
    bene_county_cd           TEXT,
    bene_hi_cvrage_tot_mons  INTEGER,
    bene_smi_cvrage_tot_mons INTEGER,
    plan_cvrg_mos_num        INTEGER,
    -- Chronic condition flags: 1 = yes, 2 = no (per CMS DE-SynPUF codebook)
    sp_alzhdmta              INTEGER,
    sp_chf                   INTEGER,
    sp_chrnkidn              INTEGER,
    sp_cncr                  INTEGER,
    sp_copd                  INTEGER,
    sp_depressn              INTEGER,
    sp_diabetes              INTEGER,
    sp_ischmcht              INTEGER,
    sp_osteoprs              INTEGER,
    sp_ra_oa                 INTEGER,
    sp_strketia              INTEGER,
    -- Reimbursement totals
    medreimb_ip              REAL,
    medreimb_op              REAL,
    medreimb_car             REAL
);

CREATE TABLE inpatient_claims (
    clm_id                   TEXT PRIMARY KEY,
    desynpuf_id              TEXT NOT NULL REFERENCES beneficiary(desynpuf_id),
    clm_from_dt              TEXT,
    clm_thru_dt              TEXT,
    clm_admsn_dt              TEXT,
    nch_bene_dschrg_dt       TEXT,
    clm_pmt_amt              REAL,
    clm_utlztn_day_cnt       INTEGER,
    icd9_dgns_cd_1           TEXT
);

CREATE TABLE outpatient_claims (
    clm_id                   TEXT PRIMARY KEY,
    desynpuf_id              TEXT NOT NULL REFERENCES beneficiary(desynpuf_id),
    clm_from_dt              TEXT,
    clm_thru_dt              TEXT,
    clm_pmt_amt              REAL,
    icd9_dgns_cd_1           TEXT
);

CREATE INDEX idx_inpatient_bene ON inpatient_claims(desynpuf_id);
CREATE INDEX idx_outpatient_bene ON outpatient_claims(desynpuf_id);
