# Lampiran technical schema aktual

## actor

```json
{
  "columns": [
    {
      "data_type": "smallint unsigned",
      "name": "actor_id",
      "nullable": false,
      "ordinal_position": 1
    },
    {
      "data_type": "varchar(45)",
      "name": "first_name",
      "nullable": false,
      "ordinal_position": 2
    },
    {
      "data_type": "varchar(45)",
      "name": "last_name",
      "nullable": false,
      "ordinal_position": 3
    },
    {
      "data_type": "timestamp",
      "name": "last_update",
      "nullable": false,
      "ordinal_position": 4
    }
  ],
  "engine": "InnoDB",
  "foreign_keys": [],
  "name": "actor",
  "object_type": "BASE TABLE",
  "primary_key": [
    "actor_id"
  ]
}
```

## address

```json
{
  "columns": [
    {
      "data_type": "smallint unsigned",
      "name": "address_id",
      "nullable": false,
      "ordinal_position": 1
    },
    {
      "data_type": "varchar(50)",
      "name": "address",
      "nullable": false,
      "ordinal_position": 2
    },
    {
      "data_type": "varchar(50)",
      "name": "address2",
      "nullable": true,
      "ordinal_position": 3
    },
    {
      "data_type": "varchar(20)",
      "name": "district",
      "nullable": false,
      "ordinal_position": 4
    },
    {
      "data_type": "smallint unsigned",
      "name": "city_id",
      "nullable": false,
      "ordinal_position": 5
    },
    {
      "data_type": "varchar(10)",
      "name": "postal_code",
      "nullable": true,
      "ordinal_position": 6
    },
    {
      "data_type": "varchar(20)",
      "name": "phone",
      "nullable": false,
      "ordinal_position": 7
    },
    {
      "data_type": "geometry",
      "name": "location",
      "nullable": false,
      "ordinal_position": 8
    },
    {
      "data_type": "timestamp",
      "name": "last_update",
      "nullable": false,
      "ordinal_position": 9
    }
  ],
  "engine": "InnoDB",
  "foreign_keys": [
    {
      "delete_rule": "RESTRICT",
      "name": "fk_address_city",
      "source_columns": [
        "city_id"
      ],
      "target_columns": [
        "city_id"
      ],
      "target_schema": "sakila",
      "target_table": "city",
      "update_rule": "CASCADE"
    }
  ],
  "name": "address",
  "object_type": "BASE TABLE",
  "primary_key": [
    "address_id"
  ]
}
```

## category

```json
{
  "columns": [
    {
      "data_type": "tinyint unsigned",
      "name": "category_id",
      "nullable": false,
      "ordinal_position": 1
    },
    {
      "data_type": "varchar(25)",
      "name": "name",
      "nullable": false,
      "ordinal_position": 2
    },
    {
      "data_type": "timestamp",
      "name": "last_update",
      "nullable": false,
      "ordinal_position": 3
    }
  ],
  "engine": "InnoDB",
  "foreign_keys": [],
  "name": "category",
  "object_type": "BASE TABLE",
  "primary_key": [
    "category_id"
  ]
}
```

## city

```json
{
  "columns": [
    {
      "data_type": "smallint unsigned",
      "name": "city_id",
      "nullable": false,
      "ordinal_position": 1
    },
    {
      "data_type": "varchar(50)",
      "name": "city",
      "nullable": false,
      "ordinal_position": 2
    },
    {
      "data_type": "smallint unsigned",
      "name": "country_id",
      "nullable": false,
      "ordinal_position": 3
    },
    {
      "data_type": "timestamp",
      "name": "last_update",
      "nullable": false,
      "ordinal_position": 4
    }
  ],
  "engine": "InnoDB",
  "foreign_keys": [
    {
      "delete_rule": "RESTRICT",
      "name": "fk_city_country",
      "source_columns": [
        "country_id"
      ],
      "target_columns": [
        "country_id"
      ],
      "target_schema": "sakila",
      "target_table": "country",
      "update_rule": "CASCADE"
    }
  ],
  "name": "city",
  "object_type": "BASE TABLE",
  "primary_key": [
    "city_id"
  ]
}
```

## country

```json
{
  "columns": [
    {
      "data_type": "smallint unsigned",
      "name": "country_id",
      "nullable": false,
      "ordinal_position": 1
    },
    {
      "data_type": "varchar(50)",
      "name": "country",
      "nullable": false,
      "ordinal_position": 2
    },
    {
      "data_type": "timestamp",
      "name": "last_update",
      "nullable": false,
      "ordinal_position": 3
    }
  ],
  "engine": "InnoDB",
  "foreign_keys": [],
  "name": "country",
  "object_type": "BASE TABLE",
  "primary_key": [
    "country_id"
  ]
}
```

## customer

```json
{
  "columns": [
    {
      "data_type": "smallint unsigned",
      "name": "customer_id",
      "nullable": false,
      "ordinal_position": 1
    },
    {
      "data_type": "tinyint unsigned",
      "name": "store_id",
      "nullable": false,
      "ordinal_position": 2
    },
    {
      "data_type": "varchar(45)",
      "name": "first_name",
      "nullable": false,
      "ordinal_position": 3
    },
    {
      "data_type": "varchar(45)",
      "name": "last_name",
      "nullable": false,
      "ordinal_position": 4
    },
    {
      "data_type": "varchar(50)",
      "name": "email",
      "nullable": true,
      "ordinal_position": 5
    },
    {
      "data_type": "smallint unsigned",
      "name": "address_id",
      "nullable": false,
      "ordinal_position": 6
    },
    {
      "data_type": "tinyint(1)",
      "name": "active",
      "nullable": false,
      "ordinal_position": 7
    },
    {
      "data_type": "datetime",
      "name": "create_date",
      "nullable": false,
      "ordinal_position": 8
    },
    {
      "data_type": "timestamp",
      "name": "last_update",
      "nullable": true,
      "ordinal_position": 9
    }
  ],
  "engine": "InnoDB",
  "foreign_keys": [
    {
      "delete_rule": "RESTRICT",
      "name": "fk_customer_address",
      "source_columns": [
        "address_id"
      ],
      "target_columns": [
        "address_id"
      ],
      "target_schema": "sakila",
      "target_table": "address",
      "update_rule": "CASCADE"
    },
    {
      "delete_rule": "RESTRICT",
      "name": "fk_customer_store",
      "source_columns": [
        "store_id"
      ],
      "target_columns": [
        "store_id"
      ],
      "target_schema": "sakila",
      "target_table": "store",
      "update_rule": "CASCADE"
    }
  ],
  "name": "customer",
  "object_type": "BASE TABLE",
  "primary_key": [
    "customer_id"
  ]
}
```

## film

```json
{
  "columns": [
    {
      "data_type": "smallint unsigned",
      "name": "film_id",
      "nullable": false,
      "ordinal_position": 1
    },
    {
      "data_type": "varchar(128)",
      "name": "title",
      "nullable": false,
      "ordinal_position": 2
    },
    {
      "data_type": "text",
      "name": "description",
      "nullable": true,
      "ordinal_position": 3
    },
    {
      "data_type": "year",
      "name": "release_year",
      "nullable": true,
      "ordinal_position": 4
    },
    {
      "data_type": "tinyint unsigned",
      "name": "language_id",
      "nullable": false,
      "ordinal_position": 5
    },
    {
      "data_type": "tinyint unsigned",
      "name": "original_language_id",
      "nullable": true,
      "ordinal_position": 6
    },
    {
      "data_type": "tinyint unsigned",
      "name": "rental_duration",
      "nullable": false,
      "ordinal_position": 7
    },
    {
      "data_type": "decimal(4,2)",
      "name": "rental_rate",
      "nullable": false,
      "ordinal_position": 8
    },
    {
      "data_type": "smallint unsigned",
      "name": "length",
      "nullable": true,
      "ordinal_position": 9
    },
    {
      "data_type": "decimal(5,2)",
      "name": "replacement_cost",
      "nullable": false,
      "ordinal_position": 10
    },
    {
      "data_type": "enum('G','PG','PG-13','R','NC-17')",
      "name": "rating",
      "nullable": true,
      "ordinal_position": 11
    },
    {
      "data_type": "set('Trailers','Commentaries','Deleted Scenes','Behind the Scenes')",
      "name": "special_features",
      "nullable": true,
      "ordinal_position": 12
    },
    {
      "data_type": "timestamp",
      "name": "last_update",
      "nullable": false,
      "ordinal_position": 13
    }
  ],
  "engine": "InnoDB",
  "foreign_keys": [
    {
      "delete_rule": "RESTRICT",
      "name": "fk_film_language",
      "source_columns": [
        "language_id"
      ],
      "target_columns": [
        "language_id"
      ],
      "target_schema": "sakila",
      "target_table": "language",
      "update_rule": "CASCADE"
    },
    {
      "delete_rule": "RESTRICT",
      "name": "fk_film_language_original",
      "source_columns": [
        "original_language_id"
      ],
      "target_columns": [
        "language_id"
      ],
      "target_schema": "sakila",
      "target_table": "language",
      "update_rule": "CASCADE"
    }
  ],
  "name": "film",
  "object_type": "BASE TABLE",
  "primary_key": [
    "film_id"
  ]
}
```

## film_actor

```json
{
  "columns": [
    {
      "data_type": "smallint unsigned",
      "name": "actor_id",
      "nullable": false,
      "ordinal_position": 1
    },
    {
      "data_type": "smallint unsigned",
      "name": "film_id",
      "nullable": false,
      "ordinal_position": 2
    },
    {
      "data_type": "timestamp",
      "name": "last_update",
      "nullable": false,
      "ordinal_position": 3
    }
  ],
  "engine": "InnoDB",
  "foreign_keys": [
    {
      "delete_rule": "RESTRICT",
      "name": "fk_film_actor_actor",
      "source_columns": [
        "actor_id"
      ],
      "target_columns": [
        "actor_id"
      ],
      "target_schema": "sakila",
      "target_table": "actor",
      "update_rule": "CASCADE"
    },
    {
      "delete_rule": "RESTRICT",
      "name": "fk_film_actor_film",
      "source_columns": [
        "film_id"
      ],
      "target_columns": [
        "film_id"
      ],
      "target_schema": "sakila",
      "target_table": "film",
      "update_rule": "CASCADE"
    }
  ],
  "name": "film_actor",
  "object_type": "BASE TABLE",
  "primary_key": [
    "actor_id",
    "film_id"
  ]
}
```

## film_category

```json
{
  "columns": [
    {
      "data_type": "smallint unsigned",
      "name": "film_id",
      "nullable": false,
      "ordinal_position": 1
    },
    {
      "data_type": "tinyint unsigned",
      "name": "category_id",
      "nullable": false,
      "ordinal_position": 2
    },
    {
      "data_type": "timestamp",
      "name": "last_update",
      "nullable": false,
      "ordinal_position": 3
    }
  ],
  "engine": "InnoDB",
  "foreign_keys": [
    {
      "delete_rule": "RESTRICT",
      "name": "fk_film_category_category",
      "source_columns": [
        "category_id"
      ],
      "target_columns": [
        "category_id"
      ],
      "target_schema": "sakila",
      "target_table": "category",
      "update_rule": "CASCADE"
    },
    {
      "delete_rule": "RESTRICT",
      "name": "fk_film_category_film",
      "source_columns": [
        "film_id"
      ],
      "target_columns": [
        "film_id"
      ],
      "target_schema": "sakila",
      "target_table": "film",
      "update_rule": "CASCADE"
    }
  ],
  "name": "film_category",
  "object_type": "BASE TABLE",
  "primary_key": [
    "film_id",
    "category_id"
  ]
}
```

## film_text

```json
{
  "columns": [
    {
      "data_type": "smallint unsigned",
      "name": "film_id",
      "nullable": false,
      "ordinal_position": 1
    },
    {
      "data_type": "varchar(255)",
      "name": "title",
      "nullable": false,
      "ordinal_position": 2
    },
    {
      "data_type": "text",
      "name": "description",
      "nullable": true,
      "ordinal_position": 3
    }
  ],
  "engine": "InnoDB",
  "foreign_keys": [],
  "name": "film_text",
  "object_type": "BASE TABLE",
  "primary_key": [
    "film_id"
  ]
}
```

## inventory

```json
{
  "columns": [
    {
      "data_type": "mediumint unsigned",
      "name": "inventory_id",
      "nullable": false,
      "ordinal_position": 1
    },
    {
      "data_type": "smallint unsigned",
      "name": "film_id",
      "nullable": false,
      "ordinal_position": 2
    },
    {
      "data_type": "tinyint unsigned",
      "name": "store_id",
      "nullable": false,
      "ordinal_position": 3
    },
    {
      "data_type": "timestamp",
      "name": "last_update",
      "nullable": false,
      "ordinal_position": 4
    }
  ],
  "engine": "InnoDB",
  "foreign_keys": [
    {
      "delete_rule": "RESTRICT",
      "name": "fk_inventory_film",
      "source_columns": [
        "film_id"
      ],
      "target_columns": [
        "film_id"
      ],
      "target_schema": "sakila",
      "target_table": "film",
      "update_rule": "CASCADE"
    },
    {
      "delete_rule": "RESTRICT",
      "name": "fk_inventory_store",
      "source_columns": [
        "store_id"
      ],
      "target_columns": [
        "store_id"
      ],
      "target_schema": "sakila",
      "target_table": "store",
      "update_rule": "CASCADE"
    }
  ],
  "name": "inventory",
  "object_type": "BASE TABLE",
  "primary_key": [
    "inventory_id"
  ]
}
```

## language

```json
{
  "columns": [
    {
      "data_type": "tinyint unsigned",
      "name": "language_id",
      "nullable": false,
      "ordinal_position": 1
    },
    {
      "data_type": "char(20)",
      "name": "name",
      "nullable": false,
      "ordinal_position": 2
    },
    {
      "data_type": "timestamp",
      "name": "last_update",
      "nullable": false,
      "ordinal_position": 3
    }
  ],
  "engine": "InnoDB",
  "foreign_keys": [],
  "name": "language",
  "object_type": "BASE TABLE",
  "primary_key": [
    "language_id"
  ]
}
```

## payment

```json
{
  "columns": [
    {
      "data_type": "smallint unsigned",
      "name": "payment_id",
      "nullable": false,
      "ordinal_position": 1
    },
    {
      "data_type": "smallint unsigned",
      "name": "customer_id",
      "nullable": false,
      "ordinal_position": 2
    },
    {
      "data_type": "tinyint unsigned",
      "name": "staff_id",
      "nullable": false,
      "ordinal_position": 3
    },
    {
      "data_type": "int",
      "name": "rental_id",
      "nullable": true,
      "ordinal_position": 4
    },
    {
      "data_type": "decimal(5,2)",
      "name": "amount",
      "nullable": false,
      "ordinal_position": 5
    },
    {
      "data_type": "datetime",
      "name": "payment_date",
      "nullable": false,
      "ordinal_position": 6
    },
    {
      "data_type": "timestamp",
      "name": "last_update",
      "nullable": true,
      "ordinal_position": 7
    }
  ],
  "engine": "InnoDB",
  "foreign_keys": [
    {
      "delete_rule": "RESTRICT",
      "name": "fk_payment_customer",
      "source_columns": [
        "customer_id"
      ],
      "target_columns": [
        "customer_id"
      ],
      "target_schema": "sakila",
      "target_table": "customer",
      "update_rule": "CASCADE"
    },
    {
      "delete_rule": "SET NULL",
      "name": "fk_payment_rental",
      "source_columns": [
        "rental_id"
      ],
      "target_columns": [
        "rental_id"
      ],
      "target_schema": "sakila",
      "target_table": "rental",
      "update_rule": "CASCADE"
    },
    {
      "delete_rule": "RESTRICT",
      "name": "fk_payment_staff",
      "source_columns": [
        "staff_id"
      ],
      "target_columns": [
        "staff_id"
      ],
      "target_schema": "sakila",
      "target_table": "staff",
      "update_rule": "CASCADE"
    }
  ],
  "name": "payment",
  "object_type": "BASE TABLE",
  "primary_key": [
    "payment_id"
  ]
}
```

## rental

```json
{
  "columns": [
    {
      "data_type": "int",
      "name": "rental_id",
      "nullable": false,
      "ordinal_position": 1
    },
    {
      "data_type": "datetime",
      "name": "rental_date",
      "nullable": false,
      "ordinal_position": 2
    },
    {
      "data_type": "mediumint unsigned",
      "name": "inventory_id",
      "nullable": false,
      "ordinal_position": 3
    },
    {
      "data_type": "smallint unsigned",
      "name": "customer_id",
      "nullable": false,
      "ordinal_position": 4
    },
    {
      "data_type": "datetime",
      "name": "return_date",
      "nullable": true,
      "ordinal_position": 5
    },
    {
      "data_type": "tinyint unsigned",
      "name": "staff_id",
      "nullable": false,
      "ordinal_position": 6
    },
    {
      "data_type": "timestamp",
      "name": "last_update",
      "nullable": false,
      "ordinal_position": 7
    }
  ],
  "engine": "InnoDB",
  "foreign_keys": [
    {
      "delete_rule": "RESTRICT",
      "name": "fk_rental_customer",
      "source_columns": [
        "customer_id"
      ],
      "target_columns": [
        "customer_id"
      ],
      "target_schema": "sakila",
      "target_table": "customer",
      "update_rule": "CASCADE"
    },
    {
      "delete_rule": "RESTRICT",
      "name": "fk_rental_inventory",
      "source_columns": [
        "inventory_id"
      ],
      "target_columns": [
        "inventory_id"
      ],
      "target_schema": "sakila",
      "target_table": "inventory",
      "update_rule": "CASCADE"
    },
    {
      "delete_rule": "RESTRICT",
      "name": "fk_rental_staff",
      "source_columns": [
        "staff_id"
      ],
      "target_columns": [
        "staff_id"
      ],
      "target_schema": "sakila",
      "target_table": "staff",
      "update_rule": "CASCADE"
    }
  ],
  "name": "rental",
  "object_type": "BASE TABLE",
  "primary_key": [
    "rental_id"
  ]
}
```

## staff

```json
{
  "columns": [
    {
      "data_type": "tinyint unsigned",
      "name": "staff_id",
      "nullable": false,
      "ordinal_position": 1
    },
    {
      "data_type": "varchar(45)",
      "name": "first_name",
      "nullable": false,
      "ordinal_position": 2
    },
    {
      "data_type": "varchar(45)",
      "name": "last_name",
      "nullable": false,
      "ordinal_position": 3
    },
    {
      "data_type": "smallint unsigned",
      "name": "address_id",
      "nullable": false,
      "ordinal_position": 4
    },
    {
      "data_type": "blob",
      "name": "picture",
      "nullable": true,
      "ordinal_position": 5
    },
    {
      "data_type": "varchar(50)",
      "name": "email",
      "nullable": true,
      "ordinal_position": 6
    },
    {
      "data_type": "tinyint unsigned",
      "name": "store_id",
      "nullable": false,
      "ordinal_position": 7
    },
    {
      "data_type": "tinyint(1)",
      "name": "active",
      "nullable": false,
      "ordinal_position": 8
    },
    {
      "data_type": "varchar(16)",
      "name": "username",
      "nullable": false,
      "ordinal_position": 9
    },
    {
      "data_type": "varchar(40)",
      "name": "password",
      "nullable": true,
      "ordinal_position": 10
    },
    {
      "data_type": "timestamp",
      "name": "last_update",
      "nullable": false,
      "ordinal_position": 11
    }
  ],
  "engine": "InnoDB",
  "foreign_keys": [
    {
      "delete_rule": "RESTRICT",
      "name": "fk_staff_address",
      "source_columns": [
        "address_id"
      ],
      "target_columns": [
        "address_id"
      ],
      "target_schema": "sakila",
      "target_table": "address",
      "update_rule": "CASCADE"
    },
    {
      "delete_rule": "RESTRICT",
      "name": "fk_staff_store",
      "source_columns": [
        "store_id"
      ],
      "target_columns": [
        "store_id"
      ],
      "target_schema": "sakila",
      "target_table": "store",
      "update_rule": "CASCADE"
    }
  ],
  "name": "staff",
  "object_type": "BASE TABLE",
  "primary_key": [
    "staff_id"
  ]
}
```

## store

```json
{
  "columns": [
    {
      "data_type": "tinyint unsigned",
      "name": "store_id",
      "nullable": false,
      "ordinal_position": 1
    },
    {
      "data_type": "tinyint unsigned",
      "name": "manager_staff_id",
      "nullable": false,
      "ordinal_position": 2
    },
    {
      "data_type": "smallint unsigned",
      "name": "address_id",
      "nullable": false,
      "ordinal_position": 3
    },
    {
      "data_type": "timestamp",
      "name": "last_update",
      "nullable": false,
      "ordinal_position": 4
    }
  ],
  "engine": "InnoDB",
  "foreign_keys": [
    {
      "delete_rule": "RESTRICT",
      "name": "fk_store_address",
      "source_columns": [
        "address_id"
      ],
      "target_columns": [
        "address_id"
      ],
      "target_schema": "sakila",
      "target_table": "address",
      "update_rule": "CASCADE"
    },
    {
      "delete_rule": "RESTRICT",
      "name": "fk_store_staff",
      "source_columns": [
        "manager_staff_id"
      ],
      "target_columns": [
        "staff_id"
      ],
      "target_schema": "sakila",
      "target_table": "staff",
      "update_rule": "CASCADE"
    }
  ],
  "name": "store",
  "object_type": "BASE TABLE",
  "primary_key": [
    "store_id"
  ]
}
```
