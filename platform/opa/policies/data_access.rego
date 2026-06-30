package ai

import rego.v1

# ═══════════════════════════════════════════════════════════════════
# CONFIGURATION — chỉ sửa phần này khi thêm user/table/quyền mới
# ═══════════════════════════════════════════════════════════════════

# Bảng → roles được phép xem
table_roles := {
    "stock_prices":   {"ai_user", "analyst", "data_engineer", "admin"},
    "intraday":       {"ai_user", "analyst", "data_engineer", "admin"},
    "customer_info":  {"admin"},
    "internal_audit": {"admin"},
}

# Username → whitelist symbols.
# Không có entry = không giới hạn (xem tất cả)
user_symbol_whitelist := {
    "alice": ["SSI"],
    "bob":   ["FPT"],
}

# Bảng → column → cấu hình mask
# bypass_roles: có role này → KHÔNG bị mask (xem dữ liệu thật)
column_masks := {
    "customer_info": {
        "phone":    {"bypass_roles": ["admin"],                  "mask": "***-***-****"},
        "id_card":  {"bypass_roles": ["admin"],                  "mask": "***********"},
        "email":    {"bypass_roles": ["admin"],                  "mask": "***@***.***"},
        "address":  {"bypass_roles": ["admin", "data_engineer"], "mask": "[ẩn]"},
    },
    "stock_prices": {
        "owner_id": {"bypass_roles": ["admin", "data_engineer"], "mask": "HIDDEN"},
    },
}

# ═══════════════════════════════════════════════════════════════════
# LOGIC — không cần sửa
# ═══════════════════════════════════════════════════════════════════

default access := {
    "allow":             false,
    "restricted":        false,
    "symbol_whitelist":  [],
    "masked_columns":    [],
    "mask_values":       {},
    "accessible_tables": [],
}

access := {
    "allow":             true,
    "restricted":        _is_restricted,
    "symbol_whitelist":  _symbol_whitelist,
    "masked_columns":    _masked_columns,
    "mask_values":       _mask_values,
    "accessible_tables": _accessible_tables,
} if {
    _table_accessible
}

# Table access check
_table_accessible if { not input.table }
_table_accessible if {
    roles := table_roles[input.table]
    some role in input.roles
    role in roles
}

# Danh sách bảng user được phép
_accessible_tables := [t |
    some t, roles in table_roles
    some r in input.roles
    r in roles
]

# Symbol restriction: dùng object.get để tránh undefined
_is_restricted := true  if { object.get(user_symbol_whitelist, input.user, null) != null }
_is_restricted := false if { object.get(user_symbol_whitelist, input.user, null) == null }

_symbol_whitelist := object.get(user_symbol_whitelist, input.user, [])

# Column masking
_masked_columns := [] if { not input.table in column_masks }
_masked_columns := [col |
    some col, cfg in column_masks[input.table]
    not _bypass(cfg.bypass_roles)
] if { input.table in column_masks }

_mask_values := {} if { not input.table in column_masks }
_mask_values := {col: cfg.mask |
    some col, cfg in column_masks[input.table]
    not _bypass(cfg.bypass_roles)
} if { input.table in column_masks }

_bypass(bypass_roles) if {
    some r in input.roles
    r in bypass_roles
}
