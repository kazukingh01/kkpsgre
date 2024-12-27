CREATE TABLE test_table (
    id                INT PRIMARY KEY,
    datetime_no_nan   DATETIME NULL,
    datetime_with_nan DATETIME NULL,
    int_no_nan        INT NULL,
    int_with_nan      INT NULL,
    float_no_nan      DOUBLE NULL,
    float_with_nan    DOUBLE NULL,
    str_no_nan        TEXT NULL,
    str_with_nan      TEXT NULL,
    bool_no_nan       BOOLEAN NULL,
    bool_with_nan     BOOLEAN NULL,
    category_column   TEXT NULL
);
