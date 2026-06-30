package trino

import rego.v1

# User → roles mapping
# Thêm user mới vào đây hoặc cập nhật qua OPA data API
roles_map := {
    "admin":        {"admin"},
    "carol":        {"data_engineer"},
    "alice":        {"analyst"},
    "bob":          {"ai_user"},
    "ingest":       {"data_engineer"},
    "ai_platform":  {"analyst"},
    "trino":        {"admin"},
    "dbt":          {"data_engineer"},
}

# Helpers
has_role(user, role) if {
    roles_map[user][role]
}

known_user(user) if {
    roles_map[user]
}

# ── Default deny ────────────────────────────────────────────────────────────────
default allow := false

# ── Admin: full access ──────────────────────────────────────────────────────────
allow if {
    has_role(input.context.identity.user, "admin")
}

# ── All known users: meta/listing operations ────────────────────────────────────
allow if {
    known_user(input.context.identity.user)
    meta_ops := {
        "ExecuteQuery",
        "AccessCatalog",
        "ShowSchemas", "FilterSchemas",
        "ShowTables", "FilterTables",
        "ShowColumns", "FilterColumns",
        "ReadSystemInformation",
    }
    meta_ops[input.action.operation]
}

# ── Data engineer: full CRUD on iceberg ────────────────────────────────────────
allow if {
    has_role(input.context.identity.user, "data_engineer")
    input.action.resource.table.catalogName == "iceberg"
    write_ops := {
        "SelectFromColumns", "FilterColumns",
        "InsertIntoTable", "CreateTable", "DropTable",
        "UpdateTableColumns", "DeleteFromTable",
        "TruncateTable", "RenameTable",
    }
    write_ops[input.action.operation]
}

allow if {
    has_role(input.context.identity.user, "data_engineer")
    input.action.resource.schema.catalogName == "iceberg"
    schema_ops := {"CreateSchema", "DropSchema"}
    schema_ops[input.action.operation]
}

# ── Analyst: read-only on iceberg.mart ─────────────────────────────────────────
allow if {
    has_role(input.context.identity.user, "analyst")
    input.action.resource.table.catalogName == "iceberg"
    input.action.resource.table.schemaName == "mart"
    read_ops := {"SelectFromColumns", "FilterColumns"}
    read_ops[input.action.operation]
}

# ── tpch: read for all known users (testing / demos) ───────────────────────────
allow if {
    known_user(input.context.identity.user)
    input.action.resource.table.catalogName == "tpch"
    tpch_ops := {"SelectFromColumns", "FilterColumns"}
    tpch_ops[input.action.operation]
}

# ── Row-level filtering ─────────────────────────────────────────────────────────
# Trả về SQL WHERE expression; empty string = không filter
# Được gọi qua opa.policy.row-filters-uri

user_row_filters := {
    "alice": {"stock_prices": "symbol = 'SSI'"},
    "bob":   {"stock_prices": "symbol = 'FPT'"},
}

default row_filters := []

row_filters := [{"expression": filter, "identity": user}] if {
    user  := input.context.identity.user
    table := input.action.resource.table.tableName
    filter := user_row_filters[user][table]
}

# ── Column masking ──────────────────────────────────────────────────────────────
# Trả về SQL expression thay thế giá trị column; empty = không mask
# Được gọi qua opa.policy.column-masks-uri

sensitive_columns := {
    "customer_info": {
        "phone":   "'***-***-****'",
        "id_card": "'***********'",
        "email":   "regexp_replace(email, '(.).+(@.+)', '$1***$2')",
    },
}

default column_masks := []

column_masks := [] if {
    has_role(input.context.identity.user, "admin")
}

column_masks := [{"expression": expr, "identity": user}] if {
    user  := input.context.identity.user
    not has_role(user, "admin")
    table := input.action.resource.table.tableName
    col   := input.action.resource.column.columnName
    expr  := sensitive_columns[table][col]
}
