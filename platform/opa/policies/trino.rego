package trino

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
has_role(user, role) {
    roles_map[user][role]
}

known_user(user) {
    roles_map[user]
}

# ── Default deny ────────────────────────────────────────────────────────────────
default allow := false

# ── Admin: full access ──────────────────────────────────────────────────────────
allow {
    has_role(input.context.identity.user, "admin")
}

# ── All known users: meta/listing operations ────────────────────────────────────
allow {
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
allow {
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

allow {
    has_role(input.context.identity.user, "data_engineer")
    input.action.resource.schema.catalogName == "iceberg"
    schema_ops := {"CreateSchema", "DropSchema"}
    schema_ops[input.action.operation]
}

# ── Analyst: read-only on iceberg.mart ─────────────────────────────────────────
allow {
    has_role(input.context.identity.user, "analyst")
    input.action.resource.table.catalogName == "iceberg"
    input.action.resource.table.schemaName == "mart"
    read_ops := {"SelectFromColumns", "FilterColumns"}
    read_ops[input.action.operation]
}

# ── tpch: read for all known users (testing / demos) ───────────────────────────
allow {
    known_user(input.context.identity.user)
    input.action.resource.table.catalogName == "tpch"
    tpch_ops := {"SelectFromColumns", "FilterColumns"}
    tpch_ops[input.action.operation]
}
