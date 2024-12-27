use testdb;

db.getSiblingDB("testdb").createCollection("test_table", {
  validator: {
    $jsonSchema: {
      bsonType: "object",
      required: [
        "id",
        "datetime_no_nan",
        "int_no_nan",
        "float_no_nan",
        "str_no_nan",
        "bool_no_nan",
        "category_column"
      ],
      properties: {
        id:                {bsonType: "int"},
        datetime_no_nan:   {bsonType: "date",},
        datetime_with_nan: {bsonType: ["date", "null"],},
        int_no_nan:        {bsonType: "int",},
        int_with_nan:      {bsonType: ["int", "null"],},
        float_no_nan:      {bsonType: "double",},
        float_with_nan:    {bsonType: ["double", "null"],},
        str_no_nan:        {bsonType: "string",},
        str_with_nan:      {bsonType: ["string", "null"],},
        bool_no_nan:       {bsonType: "bool",},
        bool_with_nan:     {bsonType: ["bool", "null"],},
        category_column:   {bsonType: "string",}
      }
    }
  }
});
