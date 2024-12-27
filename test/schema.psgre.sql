CREATE TABLE test_table (
    id                INTEGER PRIMARY KEY,
    datetime_no_nan   TIMESTAMP WITH TIME ZONE,
    datetime_with_nan TIMESTAMP WITH TIME ZONE,
    int_no_nan        INTEGER,
    int_with_nan      INTEGER,
    float_no_nan      DOUBLE PRECISION,
    float_with_nan    DOUBLE PRECISION,
    str_no_nan        TEXT,
    str_with_nan      TEXT,
    bool_no_nan       BOOLEAN,
    bool_with_nan     BOOLEAN,
    category_column   TEXT
);