import json
import math

import frappe
from frappe.model import get_permitted_fields
from frappe.utils import flt


SYSTEM_SETTINGS_DOCTYPES = {
    "Company",
    "Department",
    "Designation",
    "Role",
    "User",
    "Warehouse",
    "Payment Terms Template",
    "Currency Exchange",
    "Cost Center",
    "Bank",
    "Bank Account",
    "Terms and Conditions",
    "Project Type",
    "Fiscal Year",
    "Email Template",
    "Custom Field",
    "Item Group",
    "UOM",
    "Manufacturer",
}

def _get_system_settings_meta(doctype):
    doctype = str(doctype or "").strip()
    if doctype not in SYSTEM_SETTINGS_DOCTYPES or not frappe.db.exists("DocType", doctype):
        frappe.throw("This configuration DocType is not installed or is not supported.")
    if not frappe.has_permission(doctype, "read"):
        frappe.throw(f"You do not have permission to read {doctype}.", frappe.PermissionError)
    return frappe.get_meta(doctype)


def _get_system_settings_context(doctype, context):
    context = str(context or "").strip()
    if not context:
        return {}
    if context == "custom-field-item" and doctype == "Custom Field":
        return {"dt": "Item"}
    frappe.throw("This configuration view is not supported.")


def _get_settings_field_info(field):
    if field.fieldtype == "Password":
        return None
    return {
        "fieldname": field.fieldname,
        "label": field.label or field.fieldname,
        "fieldtype": field.fieldtype,
        "required": bool(field.reqd),
        "mandatory_depends_on": field.mandatory_depends_on,
        "read_only": bool(field.read_only or field.permlevel),
        "default": field.default,
        "link_doctype": field.options if field.fieldtype == "Link" else "",
        "table_doctype": field.options if field.fieldtype in ("Table", "Table MultiSelect") else "",
        "options": [option for option in (field.options or "").splitlines() if option]
        if field.fieldtype == "Select"
        else [],
    }


def _get_system_settings_sections(meta):
    current_tab = "Details"
    current_section = "Details"
    sections = []

    for field in meta.fields:
        if field.fieldtype == "Tab Break":
            current_tab = field.label or "Details"
            current_section = current_tab
            continue
        if field.fieldtype == "Section Break":
            current_section = field.label or current_tab
            continue
        if (
            field.fieldtype == "Column Break"
            or not field.fieldname
            or field.hidden
            or field.permlevel
            or field.fieldtype in ("HTML", "Button")
        ):
            continue

        field_info = _get_settings_field_info(field)
        if not field_info:
            continue
        if field.fieldtype in ("Table", "Table MultiSelect") and field.options:
            child_meta = frappe.get_meta(field.options)
            field_info["children"] = [
                child_info
                for child_field in child_meta.fields
                if child_field.fieldtype not in ("Section Break", "Tab Break", "Column Break")
                and child_field.fieldname
                and not child_field.hidden
                and not child_field.permlevel
                for child_info in [_get_settings_field_info(child_field)]
                if child_info
            ]

        if not sections or sections[-1]["tab"] != current_tab or sections[-1]["section"] != current_section:
            sections.append({"tab": current_tab, "section": current_section, "fields": []})
        sections[-1]["fields"].append(field_info)

    return sections


def _get_system_settings_list_fields(meta):
    visible_fields = [
        field
        for field in meta.fields
        if field.fieldname
        and not field.hidden
        and not field.permlevel
        and field.fieldtype not in (
            "Section Break",
            "Tab Break",
            "Column Break",
            "Table",
            "Table MultiSelect",
            "Password",
            "HTML",
            "Button",
        )
    ]
    list_fields = [field for field in visible_fields if field.in_list_view]
    return list_fields or visible_fields[:3]


@frappe.whitelist()
def get_system_settings_doctypes():
    return sorted(
        doctype for doctype in SYSTEM_SETTINGS_DOCTYPES
        if frappe.db.exists("DocType", doctype)
    )


@frappe.whitelist()
def get_system_settings_doctype(doctype=None, context=""):
    meta = _get_system_settings_meta(doctype)
    sections = _get_system_settings_sections(meta)
    _get_system_settings_context(meta.name, context)
    columns = [
        {"fieldname": "name", "label": meta.get("title_field") or "ID"}
    ]
    list_fields = _get_system_settings_list_fields(meta)
    columns.extend(
        {"fieldname": field.fieldname, "label": field.label or field.fieldname}
        for field in list_fields
        if field.fieldname != "name"
    )
    return {
        "metadata": {
            "label": meta.name,
            "can_create": bool(frappe.has_permission(meta.name, "create")),
            "can_write": bool(frappe.has_permission(meta.name, "write")),
        },
        "columns": columns,
        "sections": sections,
    }


@frappe.whitelist()
def get_system_settings_records(doctype=None, search="", context="", page=1, page_length=25):
    meta = _get_system_settings_meta(doctype)
    doctype = meta.name
    filters = _get_system_settings_context(doctype, context)
    list_fields = _get_system_settings_list_fields(meta)
    visible_fieldnames = {field.fieldname for field in list_fields}
    fields = ["name", *sorted(visible_fieldnames - {"name"})]
    try:
        page = max(int(page), 1)
        page_length = int(page_length)
    except (TypeError, ValueError):
        frappe.throw("Page and page size must be valid integers.")
    if page_length not in (10, 25, 50, 100):
        frappe.throw("Page size must be 10, 25, 50, or 100.")

    search = str(search or "").strip()
    or_filters = []
    if search:
        pattern = f"%{search}%"
        or_filters.append(["name", "like", pattern])
        or_filters.extend(
            [field.fieldname, "like", pattern]
            for field in list_fields
            if field.fieldname != "name"
            and field.fieldtype in ("Data", "Link", "Select", "Read Only", "Dynamic Link", "Small Text")
        )
    records = frappe.get_list(
        doctype,
        filters=filters,
        or_filters=or_filters,
        fields=fields,
        order_by="modified desc",
        limit_start=(page - 1) * page_length,
        limit_page_length=page_length + 1,
    )
    has_more = len(records) > page_length
    return {"records": records[:page_length], "has_more": has_more}


@frappe.whitelist()
def get_system_settings_record(doctype=None, name=None, context=""):
    meta = _get_system_settings_meta(doctype)
    context_filters = _get_system_settings_context(meta.name, context)
    name = str(name or "").strip()
    if not name:
        frappe.throw("A record name is required.")
    doc = frappe.get_doc(meta.name, name)
    doc.check_permission("read")
    if context_filters and any(doc.get(fieldname) != value for fieldname, value in context_filters.items()):
        frappe.throw("This record is not part of the selected configuration view.")
    allowed_fields = {
        field["fieldname"]
        for section in _get_system_settings_sections(meta)
        for field in section["fields"]
    }
    record = {
        fieldname: doc.get(fieldname)
        for fieldname in allowed_fields
    }
    record["name"] = doc.name
    record["docstatus"] = doc.docstatus
    return {"record": record}


def _prepare_system_settings_values(meta, values):
    if isinstance(values, str):
        try:
            values = json.loads(values)
        except json.JSONDecodeError:
            frappe.throw("Configuration details must be valid JSON.")
    if not isinstance(values, dict):
        frappe.throw("Configuration details must be provided as an object.")

    excluded_fields = {
        "name",
        "owner",
        "creation",
        "modified",
        "modified_by",
        "docstatus",
        "status",
        "idx",
    }
    prepared = {}
    for field in meta.fields:
        fieldname = field.fieldname
        if (
            not fieldname
            or fieldname in excluded_fields
            or field.read_only
            or field.hidden
            or field.permlevel
            or field.fieldtype in ("Password", "HTML", "Button")
            or fieldname not in values
        ):
            continue
        if field.fieldtype in ("Table", "Table MultiSelect"):
            rows = values[fieldname]
            if not isinstance(rows, list) or any(not isinstance(row, dict) for row in rows):
                frappe.throw(f"{field.label or fieldname} must be a list of row objects.")
            child_meta = frappe.get_meta(field.options)
            allowed_children = {
                child_field.fieldname
                for child_field in child_meta.fields
                if child_field.fieldname
                and child_field.fieldname not in excluded_fields
                and not child_field.read_only
                and not child_field.hidden
                and not child_field.permlevel
                and child_field.fieldtype not in ("Password", "HTML", "Button")
            }
            prepared[fieldname] = [
                {key: value for key, value in row.items() if key in allowed_children}
                for row in rows
            ]
        else:
            prepared[fieldname] = values[fieldname]
    return prepared


@frappe.whitelist()
def create_system_settings_record(doctype=None, values=None, context=""):
    meta = _get_system_settings_meta(doctype)
    context_filters = _get_system_settings_context(meta.name, context)
    if not frappe.has_permission(meta.name, "create"):
        frappe.throw(f"You do not have permission to create {meta.name}.", frappe.PermissionError)
    prepared_values = _prepare_system_settings_values(meta, values)
    prepared_values.update(context_filters)
    doc = frappe.get_doc({
        "doctype": meta.name,
        **prepared_values,
    }).insert()
    return {"record": {"name": doc.name}}


@frappe.whitelist()
def update_system_settings_record(doctype=None, name=None, values=None, context=""):
    meta = _get_system_settings_meta(doctype)
    context_filters = _get_system_settings_context(meta.name, context)
    name = str(name or "").strip()
    if not name:
        frappe.throw("A record name is required.")
    doc = frappe.get_doc(meta.name, name)
    doc.check_permission("write")
    if context_filters and any(doc.get(fieldname) != value for fieldname, value in context_filters.items()):
        frappe.throw("This record is not part of the selected configuration view.")
    if doc.docstatus != 0:
        frappe.throw("Only draft configuration records can be updated.")
    prepared_values = _prepare_system_settings_values(meta, values)
    for fieldname, value in context_filters.items():
        prepared_values.pop(fieldname, None)
    doc.update(prepared_values)
    doc.save()
    return {"record": {"name": doc.name}}


@frappe.whitelist()
def get_system_settings_link_options(doctype=None, fieldname=None, txt="", child_doctype=""):
    meta = _get_system_settings_meta(doctype)
    fieldname = str(fieldname or "").strip()
    if child_doctype:
        table_field = next(
            (
                parent_field for parent_field in meta.fields
                if parent_field.fieldtype in ("Table", "Table MultiSelect")
                and parent_field.options == child_doctype
            ),
            None,
        )
        if not table_field:
            frappe.throw("The selected child table does not belong to this configuration DocType.")
        field = frappe.get_meta(child_doctype).get_field(fieldname)
    else:
        field = meta.get_field(fieldname)
    if not field or field.fieldtype != "Link" or not field.options:
        frappe.throw("Options are only available for valid Link fields.")
    search = str(txt or "").strip()
    filters = {"name": ["like", f"%{search}%"]} if search else {}
    return [
        row.name for row in frappe.get_list(
            field.options,
            filters=filters,
            fields=["name"],
            order_by="name asc",
            limit_page_length=20,
        )
    ]


@frappe.whitelist()
def get_products(filters=None):
    if isinstance(filters, str):
        try:
            filters = json.loads(filters)
        except json.JSONDecodeError:
            frappe.throw("Filters must be valid JSON.")

    if filters is None:
        filters = {}
    if not isinstance(filters, dict):
        frappe.throw("Filters must be an object.")

    item_filters = {}
    status = filters.get("status", "Enabled")
    if status == "Enabled":
        item_filters["disabled"] = 0
    elif status == "Disabled":
        item_filters["disabled"] = 1
    elif status != "All":
        frappe.throw("Invalid item status filter.")

    item_group = str(filters.get("item_group") or "").strip()
    if item_group:
        item_filters["item_group"] = item_group

    for filter_name, field_name in (("item_code", "item_code"), ("item_name", "item_name")):
        search = str(filters.get(filter_name) or "").strip()
        if search:
            item_filters[field_name] = ["like", f"%{search}%"]

    items = frappe.get_list(
        "Item",
        filters=item_filters,
        fields=[
            "item_code",
            "item_name",
            "item_group",
            "stock_uom",
            "image",
            "standard_rate",
            "default_manufacturer_part_no",
            "default_item_manufacturer",
            "disabled",
        ],
        order_by="item_name asc",
        limit_page_length=500,
    )

    item_codes = [item.item_code for item in items]
    stock_by_item = {}
    if item_codes:
        bins = frappe.get_list(
            "Bin",
            filters={"item_code": ["in", item_codes]},
            fields=[
                "item_code",
                "sum(actual_qty) as available",
                "sum(reserved_qty) as reserved",
            ],
            group_by="item_code",
            limit_page_length=len(item_codes),
        )
        stock_by_item = {row.item_code: row for row in bins}

    products = []
    for item in items:
        stock = stock_by_item.get(item.item_code)
        available = flt(stock.available) if stock else 0

        products.append(
            {
                "item_code": item.item_code,
                "item_name": item.item_name,
                "category": item.item_group,
                "image": item.image,
                "manufacturer_part_no": item.default_manufacturer_part_no,
                "manufacturer": item.default_item_manufacturer,
                "available": available,
                "reserved": flt(stock.reserved) if stock else 0,
                "uom": item.stock_uom,
                "unit_price": flt(item.standard_rate),
                "disabled": item.disabled,
            }
        )

    item_groups = frappe.get_list(
        "Item Group",
        filters={"is_group": 0},
        fields=["name"],
        order_by="name asc",
        limit_page_length=500,
    )
    uoms = frappe.get_list(
        "UOM",
        fields=["name"],
        order_by="name asc",
        limit_page_length=500,
    )

    return {
        "items": products,
        "item_groups": [group.name for group in item_groups],
        "uoms": [uom.name for uom in uoms],
    }


@frappe.whitelist()
def get_item_suggestions(search_by, txt=""):
    if search_by not in ("item_code", "item_name"):
        frappe.throw("Suggestions can only be searched by Item ID or Product Name.")

    search = str(txt or "").strip()
    filters = {}
    if search:
        filters[search_by] = ["like", f"%{search}%"]

    return frappe.get_list(
        "Item",
        filters=filters,
        fields=["item_code", "item_name"],
        order_by=f"{search_by} asc",
        limit_page_length=20,
    )


@frappe.whitelist()
def get_item_form_fields():
    meta = frappe.get_meta("Item")
    current_tab = "Details"
    current_section = "Item Details"
    sections = []

    for field in meta.fields:
        if field.fieldtype == "Tab Break":
            current_tab = field.label or "Details"
            current_section = current_tab
            continue
        if field.fieldtype == "Section Break":
            current_section = field.label or current_tab
            continue

        if field.fieldtype == "Column Break" or not field.fieldname:
            continue

        field_info = _get_form_field_info(field, is_item_field=True)
        if field.fieldtype in ("Table", "Table MultiSelect") and field.options:
            child_meta = frappe.get_meta(field.options)
            field_info["children"] = [
                _get_form_field_info(child_field)
                for child_field in child_meta.fields
                if child_field.fieldtype not in ("Section Break", "Tab Break", "Column Break")
                and child_field.fieldname
            ]

        if (
            not sections
            or sections[-1]["tab"] != current_tab
            or sections[-1]["section"] != current_section
        ):
            sections.append(
                {"tab": current_tab, "section": current_section, "fields": []}
            )
        sections[-1]["fields"].append(field_info)

    return sections


def _get_form_field_info(field, is_item_field=False):
    required_fields = {"item_code", "item_name", "item_group", "stock_uom"}
    return {
        "fieldname": field.fieldname,
        "label": field.label or field.fieldname,
        "fieldtype": field.fieldtype,
        "required": bool(field.reqd or (is_item_field and field.fieldname in required_fields)),
        "mandatory_depends_on": field.mandatory_depends_on,
        "read_only": bool(field.read_only),
        "default": field.default,
        "link_doctype": field.options if field.fieldtype == "Link" else "",
        "table_doctype": field.options if field.fieldtype == "Table" else "",
        "options": [
            option for option in (field.options or "").splitlines() if option
        ] if field.fieldtype == "Select" else [],
    }


@frappe.whitelist()
def get_item_link_options(fieldname, txt="", child_doctype=""):
    parent_meta = frappe.get_meta("Item")
    if child_doctype:
        table_field = next(
            (
                field for field in parent_meta.fields
                if field.fieldtype in ("Table", "Table MultiSelect") and field.options == child_doctype
            ),
            None,
        )
        if not table_field:
            frappe.throw("Invalid Item child table.")
        field = frappe.get_meta(child_doctype).get_field(fieldname)
    else:
        field = parent_meta.get_field(fieldname)

    if not field or field.fieldtype != "Link" or not field.options:
        frappe.throw("Options are only available for valid Link fields.")

    filters = {}
    search = str(txt or "").strip()
    if search:
        filters["name"] = ["like", f"%{search}%"]

    return [
        row.name
        for row in frappe.get_list(
            field.options,
            filters=filters,
            fields=["name"],
            order_by="name asc",
            limit_page_length=20,
        )
    ]


@frappe.whitelist()
def create_product(item=None):
    if isinstance(item, str):
        try:
            item = json.loads(item)
        except json.JSONDecodeError:
            frappe.throw("Item details must be valid JSON.")

    if not isinstance(item, dict):
        frappe.throw("Item details must be provided.")

    item_code = str(item.get("item_code") or "").strip()
    item_name = str(item.get("item_name") or "").strip()
    item_group = str(item.get("item_group") or "").strip()
    stock_uom = str(item.get("stock_uom") or "").strip()

    if not item_code or not item_name or not item_group or not stock_uom:
        frappe.throw("Item Code, Item Name, Item Group, and Unit of Measure are required.")
    if not frappe.db.exists("Item Group", item_group):
        frappe.throw("Please select a valid Item Group.")
    if frappe.db.get_value("Item Group", item_group, "is_group"):
        frappe.throw("Please select a leaf Item Group.")
    if not frappe.db.exists("UOM", stock_uom):
        frappe.throw("Please select a valid Unit of Measure.")

    raw_rate = item.get("standard_rate") or 0
    try:
        standard_rate = float(raw_rate)
    except (TypeError, ValueError):
        frappe.throw("Unit Price must be a valid number.")
    if not math.isfinite(standard_rate) or standard_rate < 0:
        frappe.throw("Unit Price must be a finite, non-negative number.")

    meta = frappe.get_meta("Item")
    item_values = {
        "doctype": "Item",
        "item_code": item_code,
        "item_name": item_name,
        "item_group": item_group,
        "stock_uom": stock_uom,
        "is_stock_item": int(bool(item.get("is_stock_item", 1))),
    }

    for field in meta.fields:
        fieldname = field.fieldname
        if (
            fieldname in item
            and fieldname not in item_values
            and not field.read_only
            and field.fieldtype not in ("Section Break", "Tab Break", "Column Break")
        ):
            item_values[fieldname] = item[fieldname]

    if meta.has_field("standard_rate"):
        item_values["standard_rate"] = standard_rate

    doc = frappe.get_doc(item_values).insert()
    return {"item_code": doc.name, "item_name": doc.item_name}


@frappe.whitelist()
def get_purchase_order_form_fields():
    return _get_purchase_document_form_fields("Purchase Order")


def _get_purchase_document_form_fields(doctype):
    meta = frappe.get_meta(doctype)
    current_tab = "Details"
    current_section = f"{doctype} Details"
    sections = []

    for field in meta.fields:
        if field.fieldtype == "Tab Break":
            current_tab = field.label or "Details"
            current_section = current_tab
            continue
        if field.fieldtype == "Section Break":
            current_section = field.label or current_tab
            continue
        if field.fieldtype == "Column Break" or not field.fieldname or field.hidden:
            continue

        field_info = _get_purchase_order_field_info(field)
        if field.fieldtype in ("Table", "Table MultiSelect") and field.options:
            child_meta = frappe.get_meta(field.options)
            field_info["children"] = [
                _get_purchase_order_field_info(child_field)
                for child_field in child_meta.fields
                if child_field.fieldname
                and not child_field.hidden
                and child_field.fieldtype not in ("Section Break", "Tab Break", "Column Break")
            ]

        if not sections or sections[-1]["tab"] != current_tab or sections[-1]["section"] != current_section:
            sections.append({"tab": current_tab, "section": current_section, "fields": []})
        sections[-1]["fields"].append(field_info)

    return sections


@frappe.whitelist()
def get_purchase_invoice_form_fields():
    return _get_purchase_document_form_fields("Purchase Invoice")


@frappe.whitelist()
def get_supplier_options(txt=""):
    search = str(txt or "").strip()
    filters = {}
    if search:
        filters["supplier_name"] = ["like", f"%{search}%"]
    rows = frappe.get_list(
        "Supplier",
        filters=filters,
        fields=["name", "supplier_name"],
        order_by="name asc",
        limit_page_length=20,
    )
    options = []
    for row in rows:
        options.append(row.name)
    return options


def _get_purchase_order_field_info(field):
    return {
        "fieldname": field.fieldname,
        "label": field.label or field.fieldname,
        "fieldtype": field.fieldtype,
        "required": bool(field.reqd),
        "mandatory_depends_on": field.mandatory_depends_on,
        "read_only": bool(field.read_only or field.permlevel),
        "default": field.default,
        "fetch_from": field.fetch_from or "",
        "link_doctype": field.options if field.fieldtype == "Link" else "",
        "dynamic_link_field": field.options if field.fieldtype == "Dynamic Link" else "",
        "table_doctype": field.options if field.fieldtype in ("Table", "Table MultiSelect") else "",
        "options": [option for option in (field.options or "").splitlines() if option] if field.fieldtype == "Select" else [],
    }


@frappe.whitelist()
def get_purchase_order_link_options(fieldname, txt="", child_doctype=""):
    return _get_purchase_document_link_options("Purchase Order", fieldname, txt, child_doctype)


def _get_purchase_document_link_options(doctype, fieldname, txt="", child_doctype=""):
    parent_meta = frappe.get_meta(doctype)
    if child_doctype:
        table_field = next(
            (
                field for field in parent_meta.fields
                if field.fieldtype == "Table" and field.options == child_doctype
            ),
            None,
        )
        if not table_field:
            frappe.throw(f"Invalid {doctype} child table.")
        field = frappe.get_meta(child_doctype).get_field(fieldname)
    else:
        field = parent_meta.get_field(fieldname)

    if not field or field.fieldtype != "Link" or not field.options:
        frappe.throw(f"Options are only available for valid {doctype} Link fields.")

    filters = {}
    search = str(txt or "").strip()
    if search:
        filters["name"] = ["like", f"%{search}%"]

    return [
        row.name
        for row in frappe.get_list(
            field.options,
            filters=filters,
            fields=["name"],
            order_by="name asc",
            limit_page_length=20,
        )
    ]


@frappe.whitelist()
def get_purchase_invoice_link_options(fieldname, txt="", child_doctype=""):
    return _get_purchase_document_link_options("Purchase Invoice", fieldname, txt, child_doctype)


@frappe.whitelist()
def get_purchase_order_item_options(search_by="item_code", txt=""):
    if search_by not in ("item_code", "item_name"):
        frappe.throw("Items can only be searched by Item Code or Item Name.")

    filters = {"disabled": 0}
    search = str(txt or "").strip()
    if search:
        filters[search_by] = ["like", f"%{search}%"]

    return frappe.get_list(
        "Item",
        filters=filters,
        fields=["item_code", "item_name", "stock_uom", "standard_rate", "description"],
        order_by=f"{search_by} asc",
        limit_page_length=20,
    )


@frappe.whitelist()
def get_purchase_invoice_item_options(search_by="item_code", txt=""):
    return get_purchase_order_item_options(search_by, txt)


@frappe.whitelist()
def get_purchase_orders(filters=None):
    if isinstance(filters, str):
        try:
            filters = json.loads(filters)
        except json.JSONDecodeError:
            frappe.throw("Purchase order filters must be valid JSON.")

    request_filters = {}
    if filters is None:
        filters = {}
    if not isinstance(filters, dict):
        frappe.throw("Purchase order filters must be an object.")

    status = str(filters.get("status") or "All").strip()
    if status and status != "All":
        request_filters["status"] = status

    po_number = str(filters.get("po_number") or "").strip()
    if po_number:
        request_filters["name"] = ["like", f"%{po_number}%"]

    supplier = str(filters.get("supplier") or "").strip()
    if supplier:
        request_filters["supplier"] = ["like", f"%{supplier}%"]

    supplier_name = str(filters.get("supplier_name") or "").strip()
    if supplier_name:
        request_filters["supplier_name"] = ["like", f"%{supplier_name}%"]

    company = str(filters.get("company") or "").strip()
    if company:
        request_filters["company"] = ["like", f"%{company}%"]

    from_date = str(filters.get("from_date") or "").strip()
    if from_date:
        request_filters["transaction_date"] = [">=", from_date]

    orders = frappe.get_list(
        "Purchase Order",
        filters=request_filters,
        fields=[
            "name",
            "supplier",
            "supplier_name",
            "company",
            "transaction_date",
            "status",
            "grand_total",
        ],
        order_by="transaction_date desc, name desc",
        limit_page_length=50,
    )

    purchase_orders = []
    for order in orders:
        purchase_orders.append(
            {
                "po_number": order.name,
                "supplier": order.supplier,
                "supplier_name": order.supplier_name,
                "company": order.company,
                "order_date": order.transaction_date,
                "status": order.status,
                "total": flt(order.grand_total),
            }
        )

    return {"purchase_orders": purchase_orders}


@frappe.whitelist()
def get_purchase_invoices(filters=None):
    if isinstance(filters, str):
        try:
            filters = json.loads(filters)
        except json.JSONDecodeError:
            frappe.throw("Purchase invoice filters must be valid JSON.")

    if filters is None:
        filters = {}
    if not isinstance(filters, dict):
        frappe.throw("Purchase invoice filters must be an object.")

    request_filters = {}
    status = str(filters.get("status") or "All").strip()
    if status and status != "All":
        request_filters["status"] = status

    invoice_number = str(filters.get("invoice_number") or "").strip()
    if invoice_number:
        request_filters["name"] = ["like", f"%{invoice_number}%"]

    supplier = str(filters.get("supplier") or "").strip()
    if supplier:
        request_filters["supplier"] = ["like", f"%{supplier}%"]

    supplier_name = str(filters.get("supplier_name") or "").strip()
    if supplier_name:
        request_filters["supplier_name"] = ["like", f"%{supplier_name}%"]

    company = str(filters.get("company") or "").strip()
    if company:
        request_filters["company"] = ["like", f"%{company}%"]

    invoices = frappe.get_list(
        "Purchase Invoice",
        filters=request_filters,
        fields=[
            "name",
            "supplier",
            "supplier_name",
            "company",
            "posting_date",
            "status",
            "grand_total",
        ],
        order_by="posting_date desc, name desc",
        limit_page_length=50,
    )

    return {
        "purchase_invoices": [
            {
                "invoice_number": invoice.name,
                "supplier": invoice.supplier,
                "supplier_name": invoice.supplier_name,
                "company": invoice.company,
                "invoice_date": invoice.posting_date,
                "status": invoice.status,
                "total": flt(invoice.grand_total),
            }
            for invoice in invoices
        ]
    }


@frappe.whitelist()
def get_purchase_order(po_number=None):
    po_number = str(po_number or "").strip()
    if not po_number:
        frappe.throw("Purchase Order ID is required.")

    doc = frappe.get_doc("Purchase Order", po_number)
    doc.check_permission("read")
    return {"purchase_order": doc.as_dict()}


@frappe.whitelist()
def get_purchase_invoice(invoice_number=None):
    invoice_number = str(invoice_number or "").strip()
    if not invoice_number:
        frappe.throw("Purchase Invoice ID is required.")

    doc = frappe.get_doc("Purchase Invoice", invoice_number)
    doc.check_permission("read")
    return {"purchase_invoice": doc.as_dict()}


def _prepare_purchase_order_values(purchase_order):
    return _prepare_purchase_document_values("Purchase Order", purchase_order, "Purchase order")


def _prepare_purchase_invoice_values(purchase_invoice):
    return _prepare_purchase_document_values("Purchase Invoice", purchase_invoice, "Purchase invoice")


def _prepare_purchase_document_values(doctype, document, label):
    if isinstance(document, str):
        try:
            document = json.loads(document)
        except json.JSONDecodeError:
            frappe.throw(f"{label} details must be valid JSON.")

    if not isinstance(document, dict):
        frappe.throw(f"{label} details must be provided.")

    meta = frappe.get_meta(doctype)
    writable_fields = _get_designed_writable_fields(doctype)
    doc_values = {}
    excluded_fields = {
        "name",
        "owner",
        "creation",
        "modified",
        "modified_by",
        "docstatus",
        "status",
        "idx",
    }

    for field in meta.fields:
        if (
            not field.fieldname
            or field.fieldname in excluded_fields
            or (
                field.fieldname not in writable_fields
                and not (field.fieldtype in ("Table", "Table MultiSelect") and not field.permlevel)
            )
            or field.read_only
            or field.hidden
        ):
            continue

        if field.fieldtype in ("Table", "Table MultiSelect"):
            rows = document.get(field.fieldname, [])
            if not isinstance(rows, list):
                frappe.throw(f"{field.label or field.fieldname} must be a list of rows.")
            if any(not isinstance(row, dict) for row in rows):
                frappe.throw(f"Every {field.label or field.fieldname} entry must be an object.")
            child_meta = frappe.get_meta(field.options)
            writable_child_fields = _get_designed_writable_fields(
                child_meta.name, parenttype=doctype
            )
            child_fields = {
                child_field.fieldname
                for child_field in child_meta.fields
                if child_field.fieldname
                and child_field.fieldname not in excluded_fields
                and child_field.fieldname in writable_child_fields
                and not child_field.read_only
                and not child_field.hidden
                and child_field.fieldtype not in ("Section Break", "Tab Break", "Column Break")
            }
            doc_values[field.fieldname] = [
                {
                    fieldname: value
                    for fieldname, value in row.items()
                    if fieldname in child_fields
                }
                for row in rows
            ]
        elif field.fieldname in document:
            doc_values[field.fieldname] = document[field.fieldname]

    return doc_values


@frappe.whitelist()
def create_purchase_order(purchase_order=None):
    doc = frappe.get_doc({
        "doctype": "Purchase Order",
        **_prepare_purchase_order_values(purchase_order),
    }).insert()
    return {
        "purchase_order": {
            "po_number": doc.name,
            "supplier": doc.supplier,
            "order_date": doc.transaction_date,
            "status": doc.status,
            "total": flt(doc.grand_total),
        }
    }


@frappe.whitelist()
def update_purchase_order(po_number=None, purchase_order=None):
    po_number = str(po_number or "").strip()
    if not po_number:
        frappe.throw("Purchase Order ID is required.")

    doc = frappe.get_doc("Purchase Order", po_number)
    doc.check_permission("write")
    if doc.docstatus != 0:
        frappe.throw("Only draft Purchase Orders can be updated.")
    doc.update(_prepare_purchase_order_values(purchase_order))
    doc.save()
    return {
        "purchase_order": {
            "po_number": doc.name,
            "supplier": doc.supplier,
            "order_date": doc.transaction_date,
            "status": doc.status,
            "total": flt(doc.grand_total),
        }
    }


@frappe.whitelist()
def create_purchase_invoice(purchase_invoice=None):
    doc = frappe.get_doc({
        "doctype": "Purchase Invoice",
        **_prepare_purchase_invoice_values(purchase_invoice),
    }).insert()
    return {
        "purchase_invoice": {
            "invoice_number": doc.name,
            "supplier": doc.supplier,
            "invoice_date": doc.posting_date,
            "status": doc.status,
            "total": flt(doc.grand_total),
        }
    }


@frappe.whitelist()
def update_purchase_invoice(invoice_number=None, purchase_invoice=None):
    invoice_number = str(invoice_number or "").strip()
    if not invoice_number:
        frappe.throw("Purchase Invoice ID is required.")

    doc = frappe.get_doc("Purchase Invoice", invoice_number)
    doc.check_permission("write")
    if doc.docstatus != 0:
        frappe.throw("Only draft Purchase Invoices can be updated.")
    doc.update(_prepare_purchase_invoice_values(purchase_invoice))
    doc.save()
    return {
        "purchase_invoice": {
            "invoice_number": doc.name,
            "supplier": doc.supplier,
            "invoice_date": doc.posting_date,
            "status": doc.status,
            "total": flt(doc.grand_total),
        }
    }


def _get_designed_transaction_meta(doctype):
    doctype = str(doctype or "").strip()
    if not doctype or not frappe.db.exists("DocType", doctype):
        frappe.throw("This DocType is not available.")
    meta = frappe.get_meta(doctype)
    if meta.istable or meta.issingle or meta.is_virtual:
        frappe.throw(f"{meta.name} cannot be opened as a document list.")
    return meta


@frappe.whitelist()
def get_designed_transaction_form(doctype=None):
    meta = _get_designed_transaction_meta(doctype)
    if not frappe.has_permission(meta.name, "read"):
        frappe.throw(f"You do not have permission to read {meta.name}.", frappe.PermissionError)
    return {
        "label": meta.name,
        "can_create": bool(frappe.has_permission(meta.name, "create")),
        "can_write": bool(frappe.has_permission(meta.name, "write")),
        "is_submittable": bool(meta.is_submittable),
        "sections": _get_designed_transaction_sections(meta),
        "columns": _get_designed_transaction_columns(meta),
        "search_fields": _get_designed_transaction_search_fields(meta),
    }


def _get_designed_transaction_search_fields(meta):
    permitted_fields = set(
        get_permitted_fields(meta.name, user=frappe.session.user, permission_type="read")
    )
    fields = {field.fieldname: field for field in meta.fields if field.fieldname}
    dynamic_party_field = next(
        (
            fields[fieldname]
            for fieldname in ("party_name", "party")
            if fieldname in fields
            and fields[fieldname].fieldtype == "Dynamic Link"
            and fields[fieldname].options in fields
            and fieldname in permitted_fields
            and fields[fieldname].options in permitted_fields
        ),
        None,
    )
    party_link_order = (
        ("supplier", "customer", "party", "party_name", "supplier_name", "customer_name")
        if "purchase" in meta.name.lower() or "supplier" in meta.name.lower()
        else ("customer", "supplier", "party", "party_name", "customer_name", "supplier_name")
    )
    party_field = dynamic_party_field or next(
        (
            fields[fieldname]
            for fieldname in party_link_order
            if fieldname in fields and fieldname in permitted_fields
        ),
        None,
    )
    party = None
    if party_field:
        party = {
            "fieldname": party_field.fieldname,
            "dynamic": party_field.fieldtype == "Dynamic Link",
            "link_doctype": party_field.options
            if party_field.fieldtype == "Link"
            else "",
            "type_field": party_field.options
            if party_field.fieldtype == "Dynamic Link"
            else "",
            "options": [],
            "default": "",
        }
        if party_field.fieldtype == "Dynamic Link":
            type_field = fields[party_field.options]
            if type_field.fieldtype == "Select":
                party["options"] = [
                    option.strip()
                    for option in (type_field.options or "").splitlines()
                    if option.strip() and frappe.db.exists("DocType", option.strip())
                ]
                default = str(type_field.default or "").strip()
                party["default"] = default if default in party["options"] else ""
            elif type_field.fieldtype == "Link" and type_field.options == "DocType":
                party["options"] = [
                    option
                    for option in ("Customer", "Lead", "Prospect")
                    if frappe.db.exists("DocType", option)
                ]
                default = str(type_field.default or "").strip()
                party["default"] = default if default in party["options"] else ""
        elif party_field.fieldtype != "Link":
            party = {
                **party,
                "fieldname": party_field.fieldname,
                "dynamic": False,
                "link_doctype": "",
                "type_field": "",
            }

    fieldnames = set(fields)
    return {
        "party": party,
        "company": "company" if "company" in fieldnames and "company" in permitted_fields else "",
    }


@frappe.whitelist()
def get_designed_transaction_party_options(doctype=None, party_type="", txt=""):
    meta = _get_designed_transaction_meta(doctype)
    if not frappe.has_permission(meta.name, "read"):
        frappe.throw(f"You do not have permission to read {meta.name}.", frappe.PermissionError)

    party = _get_designed_transaction_search_fields(meta)["party"]
    if not party:
        return []

    if party["dynamic"]:
        party_type = str(party_type or "").strip()
        if party_type not in party["options"]:
            frappe.throw(f"{party_type} is not a valid party type for {meta.name}.")
        link_doctype = party_type
    else:
        link_doctype = party["link_doctype"]
        if not link_doctype:
            return []

    if not frappe.has_permission(link_doctype, "read"):
        frappe.throw(f"You do not have permission to read {link_doctype}.", frappe.PermissionError)

    search = str(txt or "").strip()
    filters = {"name": ["like", f"%{search}%"]} if search else {}
    return [
        row.name
        for row in frappe.get_list(
            link_doctype,
            filters=filters,
            fields=["name"],
            order_by="name asc",
            limit_page_length=20,
        )
    ]


def _get_designed_transaction_sections(meta):
    current_tab = "Details"
    current_section = "Details"
    sections = []
    permitted_fields = set(
        get_permitted_fields(meta.name, user=frappe.session.user, permission_type="read")
    )
    writable_fields = _get_designed_writable_fields(meta.name)
    dynamic_link_type_fields = {
        field.options
        for field in meta.fields
        if field.fieldtype == "Dynamic Link" and field.options
    }
    for field in meta.fields:
        if field.fieldtype == "Tab Break":
            current_tab = field.label or "Details"
            current_section = current_tab
            continue
        if field.fieldtype == "Section Break":
            current_section = field.label or current_tab
            continue
        if (
            not field.fieldname
            or field.hidden
            or (
                field.fieldname not in permitted_fields
                and not (field.fieldtype in ("Table", "Table MultiSelect") and not field.permlevel)
            )
            or field.fieldtype in ("Column Break", "HTML", "Button", "Password")
        ):
            continue

        field_info = _get_purchase_order_field_info(field)
        if (
            field.fieldtype == "Link"
            and field.options == "DocType"
            and field.fieldname in dynamic_link_type_fields
        ):
            field_info["link_options"] = _get_dynamic_link_target_doctypes(meta, field)
        field_info["read_only"] = bool(
            field.read_only
            or (
                field.fieldname not in writable_fields
                and not (field.fieldtype in ("Table", "Table MultiSelect") and not field.permlevel)
            )
        )
        if field.fieldtype in ("Table", "Table MultiSelect") and field.options:
            child_meta = frappe.get_meta(field.options)
            permitted_child_fields = set(
                get_permitted_fields(
                    child_meta.name,
                    parenttype=meta.name,
                    user=frappe.session.user,
                    permission_type="read",
                )
            )
            writable_child_fields = _get_designed_writable_fields(
                child_meta.name, parenttype=meta.name
            )
            field_info["children"] = [
                {
                    **_get_purchase_order_field_info(child_field),
                    "read_only": bool(
                        child_field.read_only
                        or child_field.fieldname not in writable_child_fields
                    ),
                }
                for child_field in child_meta.fields
                if child_field.fieldname
                and not child_field.hidden
                and child_field.fieldname in permitted_child_fields
                and child_field.fieldtype not in (
                    "Section Break",
                    "Tab Break",
                    "Column Break",
                    "HTML",
                    "Button",
                    "Password",
                )
            ]
        if not sections or sections[-1]["tab"] != current_tab or sections[-1]["section"] != current_section:
            sections.append({"tab": current_tab, "section": current_section, "fields": []})
        sections[-1]["fields"].append(field_info)
    return sections


def _get_dynamic_link_target_doctypes(meta, type_field):
    if meta.name == "Quotation" and type_field.fieldname == "quotation_to":
        return [
            doctype
            for doctype in ("Customer", "Lead", "Prospect")
            if frappe.db.exists("DocType", doctype)
        ]

    if type_field.fieldtype == "Select":
        return [
            doctype
            for doctype in (type_field.options or "").splitlines()
            if doctype and frappe.db.exists("DocType", doctype)
        ]

    return frappe.get_all(
        "DocType",
        filters={"istable": 0, "issingle": 0},
        pluck="name",
        order_by="name asc",
    )


def _get_designed_writable_fields(doctype, parenttype=None):
    return set(
        get_permitted_fields(
            doctype,
            parenttype=parenttype,
            user=frappe.session.user,
            permission_type="write",
        )
    ) | set(
        get_permitted_fields(
            doctype,
            parenttype=parenttype,
            user=frappe.session.user,
            permission_type="create",
        )
    )


def _get_designed_transaction_columns(meta):
    field_map = {field.fieldname: field for field in meta.fields if field.fieldname}
    permitted_fields = set(
        get_permitted_fields(meta.name, user=frappe.session.user, permission_type="read")
    )
    preferred = [
        "customer",
        "customer_name",
        "supplier",
        "supplier_name",
        "party_type",
        "party",
        "company",
        "transaction_date",
        "posting_date",
        "due_date",
        "status",
        "grand_total",
        "paid_amount",
        "received_amount",
    ]
    columns = [{"fieldname": "name", "label": meta.name, "fieldtype": "Data"}]
    included = {"name"}
    for fieldname in preferred:
        field = field_map.get(fieldname)
        if (
            field
            and fieldname not in included
            and not field.hidden
            and fieldname in permitted_fields
            and field.fieldtype not in ("Table", "Table MultiSelect", "HTML", "Button", "Password")
        ):
            columns.append({
                "fieldname": fieldname,
                "label": field.label or fieldname,
                "fieldtype": field.fieldtype,
            })
            included.add(fieldname)
    from frappe.model.workflow import get_workflow_name

    workflow_name = get_workflow_name(meta.name)
    if workflow_name:
        workflow_state_field = frappe.db.get_value(
            "Workflow", workflow_name, "workflow_state_field"
        )
        field = field_map.get(workflow_state_field)
        if (
            field
            and field.fieldname not in included
            and field.fieldname in permitted_fields
            and not field.hidden
            and len(columns) < 8
        ):
            columns.append({
                "fieldname": field.fieldname,
                "label": field.label or field.fieldname,
                "fieldtype": field.fieldtype,
            })
            included.add(field.fieldname)
    for field in meta.fields:
        if (
            len(columns) >= 8
            or not field.fieldname
            or field.fieldname in included
            or not field.in_list_view
            or field.hidden
            or field.fieldname not in permitted_fields
            or field.fieldtype in ("Table", "Table MultiSelect", "HTML", "Button", "Password")
        ):
            continue
        columns.append({
            "fieldname": field.fieldname,
            "label": field.label or field.fieldname,
            "fieldtype": field.fieldtype,
        })
        included.add(field.fieldname)
    return columns


@frappe.whitelist()
def get_designed_transaction_records(
    doctype=None,
    search="",
    status="All",
    name_search="",
    party_search="",
    party_field="",
    party_type="",
    company_search="",
):
    meta = _get_designed_transaction_meta(doctype)
    if not frappe.has_permission(meta.name, "read"):
        frappe.throw(f"You do not have permission to read {meta.name}.", frappe.PermissionError)

    columns = _get_designed_transaction_columns(meta)
    fields = [column["fieldname"] for column in columns]
    request_filters = {}
    status = str(status or "All").strip()
    if status != "All" and meta.has_field("status"):
        request_filters["status"] = status

    filter_conditions = [
        [fieldname, "=", value] for fieldname, value in request_filters.items()
    ]
    search = str(search or "").strip()
    or_filters = []
    if search:
        pattern = f"%{search}%"
        or_filters.append(["name", "like", pattern])
        for column in columns:
            fieldname = column["fieldname"]
            if fieldname != "name" and column["fieldtype"] in (
                "Data",
                "Link",
                "Select",
                "Read Only",
                "Dynamic Link",
                "Small Text",
            ):
                or_filters.append([fieldname, "like", pattern])

    name_search = str(name_search or "").strip()
    if name_search:
        filter_conditions.append(["name", "like", f"%{name_search}%"])

    party_search = str(party_search or "").strip()
    party_field = str(party_field or "").strip()
    search_fields = _get_designed_transaction_search_fields(meta)
    party_info = search_fields["party"]
    party_type = str(party_type or "").strip()
    if party_info and party_info["dynamic"] and party_type:
        if party_type not in party_info["options"]:
            frappe.throw(f"{party_type} is not a valid party type for {meta.name}.")
        filter_conditions.append([party_info["type_field"], "=", party_type])
    if party_search:
        if not party_info or party_field != party_info["fieldname"]:
            frappe.throw(f"{party_field} is not a searchable party field for {meta.name}.")
        filter_conditions.append([party_field, "like", f"%{party_search}%"])

    company_search = str(company_search or "").strip()
    if company_search:
        if not search_fields["company"]:
            frappe.throw(f"Company is not a searchable field for {meta.name}.")
        filter_conditions.append(["company", "like", f"%{company_search}%"])

    date_field = next(
        (fieldname for fieldname in ("posting_date", "transaction_date", "creation") if fieldname in fields),
        "modified",
    )
    records = frappe.get_list(
        meta.name,
        filters=filter_conditions,
        or_filters=or_filters,
        fields=fields,
        order_by=f"{date_field} desc, name desc",
        limit_page_length=100,
    )
    return {
        "records": [dict(record) for record in records],
        "columns": columns,
        "statuses": sorted({
            str(record.get("status"))
            for record in records
            if record.get("status")
        }),
    }


@frappe.whitelist()
def get_designed_transaction_record(doctype=None, name=None):
    meta = _get_designed_transaction_meta(doctype)
    name = str(name or "").strip()
    if not name:
        frappe.throw(f"{meta.name} ID is required.")
    doc = frappe.get_doc(meta.name, name)
    doc.check_permission("read")
    return {"record": _serialize_designed_transaction_record(doc)}


def _serialize_designed_transaction_record(doc):
    meta = doc.meta
    permitted_fields = set(
        get_permitted_fields(meta.name, user=frappe.session.user, permission_type="read")
    )
    record = {"name": doc.name, "docstatus": doc.docstatus}
    for field in meta.fields:
        if (
            not field.fieldname
            or field.hidden
            or field.fieldtype in ("HTML", "Button", "Password")
            or (
                field.fieldname not in permitted_fields
                and not (field.fieldtype in ("Table", "Table MultiSelect") and not field.permlevel)
            )
        ):
            continue
        value = doc.get(field.fieldname)
        if field.fieldtype in ("Table", "Table MultiSelect") and field.options:
            child_meta = frappe.get_meta(field.options)
            child_fields = set(
                get_permitted_fields(
                    child_meta.name,
                    parenttype=meta.name,
                    user=frappe.session.user,
                    permission_type="read",
                )
            )
            value = [
                {
                    child_field.fieldname: row.get(child_field.fieldname)
                    for child_field in child_meta.fields
                    if child_field.fieldname
                    and not child_field.hidden
                    and child_field.fieldname in child_fields
                    and child_field.fieldtype not in ("HTML", "Button", "Password")
                }
                for row in (value or [])
            ]
        record[field.fieldname] = value
    return record


@frappe.whitelist()
def get_designed_transaction_link_options(
    doctype=None,
    fieldname=None,
    txt="",
    child_doctype="",
    linked_doctype="",
):
    meta = _get_designed_transaction_meta(doctype)
    if not frappe.has_permission(meta.name, "read"):
        frappe.throw(f"You do not have permission to read {meta.name}.", frappe.PermissionError)
    if child_doctype:
        table_field = next(
            (
                field for field in meta.fields
                if field.fieldtype in ("Table", "Table MultiSelect")
                and field.options == child_doctype
                and not field.hidden
                and not field.permlevel
            ),
            None,
        )
        if not table_field:
            frappe.throw(f"Invalid {meta.name} child table.")
        field = frappe.get_meta(child_doctype).get_field(fieldname)
        permitted_fields = set(
            get_permitted_fields(
                child_doctype,
                parenttype=meta.name,
                user=frappe.session.user,
                permission_type="read",
            )
        )
    else:
        field = meta.get_field(fieldname)
        permitted_fields = set(
            get_permitted_fields(meta.name, user=frappe.session.user, permission_type="read")
        )
    if (
        not field
        or field.fieldtype not in ("Link", "Dynamic Link")
        or not field.options
        or field.hidden
        or field.fieldname not in permitted_fields
    ):
        frappe.throw(f"Options are only available for valid {meta.name} Link fields.")

    if field.fieldtype == "Dynamic Link":
        type_field = frappe.get_meta(child_doctype or meta.name).get_field(field.options)
        if (
            not type_field
            or not (
                type_field.fieldtype == "Select"
                or (type_field.fieldtype == "Link" and type_field.options == "DocType")
            )
            or type_field.fieldname not in permitted_fields
        ):
            frappe.throw(f"Invalid Dynamic Link target field for {meta.name}.")
        linked_doctype = str(linked_doctype or "").strip()
        if linked_doctype not in _get_dynamic_link_target_doctypes(
            frappe.get_meta(child_doctype) if child_doctype else meta,
            type_field,
        ):
            frappe.throw(f"{linked_doctype} is not a valid link target for {meta.name}.")
        options_doctype = linked_doctype
    else:
        options_doctype = field.options

    filters = {}
    search = str(txt or "").strip()
    if search:
        filters["name"] = ["like", f"%{search}%"]
    return [
        row.name
        for row in frappe.get_list(
            options_doctype,
            filters=filters,
            fields=["name"],
            order_by="name asc",
            limit_page_length=20,
        )
    ]


@frappe.whitelist()
def get_designed_transaction_fetch_values(
    doctype=None,
    fieldname=None,
    link_name=None,
    linked_doctype="",
    child_doctype="",
):
    meta = _get_designed_transaction_meta(doctype)
    if not frappe.has_permission(meta.name, "read"):
        frappe.throw(f"You do not have permission to read {meta.name}.", frappe.PermissionError)

    parenttype = meta.name
    if child_doctype:
        table_field = next(
            (
                field for field in meta.fields
                if field.fieldtype in ("Table", "Table MultiSelect")
                and field.options == child_doctype
                and not field.hidden
                and not field.permlevel
            ),
            None,
        )
        if not table_field:
            frappe.throw(f"Invalid {meta.name} child table.")
        parenttype = child_doctype
        field_meta = frappe.get_meta(child_doctype)
        permitted_fields = set(
            get_permitted_fields(
                child_doctype,
                parenttype=meta.name,
                user=frappe.session.user,
                permission_type="read",
            )
        )
    else:
        field_meta = meta
        permitted_fields = set(
            get_permitted_fields(meta.name, user=frappe.session.user, permission_type="read")
        )

    link_field = field_meta.get_field(fieldname)
    if (
        not link_field
        or link_field.fieldtype not in ("Link", "Dynamic Link")
        or link_field.fieldname not in permitted_fields
        or link_field.hidden
    ):
        frappe.throw(f"{fieldname} is not a valid Link field for {meta.name}.")

    if link_field.fieldtype == "Dynamic Link":
        type_field = field_meta.get_field(link_field.options)
        if not type_field:
            frappe.throw(f"{fieldname} has an invalid Dynamic Link target field.")
        allowed_doctypes = _get_dynamic_link_target_doctypes(field_meta, type_field)
        linked_doctype = str(linked_doctype or "").strip()
        if linked_doctype not in allowed_doctypes:
            frappe.throw(f"{linked_doctype} is not a valid link target for {meta.name}.")
    else:
        linked_doctype = link_field.options

    link_name = str(link_name or "").strip()
    if not link_name:
        return {}
    source_doc = frappe.get_doc(linked_doctype, link_name)
    source_doc.check_permission("read")
    source_meta = source_doc.meta
    source_fields = set(
        get_permitted_fields(
            linked_doctype,
            user=frappe.session.user,
            permission_type="read",
        )
    )
    fetch_values = {}
    for destination_field in field_meta.fields:
        fetch_from = str(destination_field.fetch_from or "").split(".")
        if (
            len(fetch_from) != 2
            or fetch_from[0] != link_field.fieldname
            or destination_field.fieldname not in permitted_fields
            or destination_field.hidden
        ):
            continue
        source_field = source_meta.get_field(fetch_from[1])
        if (
            not source_field
            or source_field.fieldname not in source_fields
            or source_field.hidden
            or source_field.fieldtype in ("Password", "HTML", "Button")
        ):
            frappe.throw(f"{fetch_from[1]} cannot be fetched from {linked_doctype}.")
        fetch_values[destination_field.fieldname] = source_doc.get(source_field.fieldname)
    return fetch_values


def _get_designed_transaction_child_meta(meta, child_doctype):
    table_field = next(
        (
            field for field in meta.fields
            if field.fieldtype in ("Table", "Table MultiSelect")
            and field.options == child_doctype
            and not field.hidden
            and not field.permlevel
        ),
        None,
    )
    if not table_field:
        frappe.throw(f"Invalid {meta.name} child table.")
    return frappe.get_meta(child_doctype)


@frappe.whitelist()
def get_designed_transaction_item_options(
    doctype=None,
    child_doctype=None,
    search_by="item_code",
    txt="",
):
    meta = _get_designed_transaction_meta(doctype)
    if not frappe.has_permission(meta.name, "read"):
        frappe.throw(f"You do not have permission to read {meta.name}.", frappe.PermissionError)
    child_meta = _get_designed_transaction_child_meta(meta, child_doctype)
    item_field = child_meta.get_field(search_by)
    permitted_fields = set(
        get_permitted_fields(
            child_meta.name,
            parenttype=meta.name,
            user=frappe.session.user,
            permission_type="read",
        )
    )
    if (
        not item_field
        or item_field.fieldtype != "Link"
        or item_field.options != "Item"
        or item_field.fieldname not in permitted_fields
        or search_by != "item_code"
    ):
        frappe.throw(f"{search_by} is not a valid Item field for {meta.name}.")
    if not frappe.has_permission("Item", "read"):
        frappe.throw("You do not have permission to read Item.", frappe.PermissionError)

    search = str(txt or "").strip()
    filters = {"disabled": 0}
    if search:
        filters["name"] = ["like", f"%{search}%"]
    items = frappe.get_list(
        "Item",
        filters=filters,
        fields=["name", "item_name", "stock_uom", "description"],
        order_by="name asc",
        limit_page_length=20,
    )
    return [
        {
            "item_code": item.name,
            "item_name": item.item_name,
            "stock_uom": item.stock_uom,
            "description": item.description,
        }
        for item in items
    ]


@frappe.whitelist()
def get_designed_transaction_item_details(
    doctype=None,
    child_doctype=None,
    item_code=None,
    values=None,
):
    meta = _get_designed_transaction_meta(doctype)
    if not frappe.has_permission(meta.name, "read"):
        frappe.throw(f"You do not have permission to read {meta.name}.", frappe.PermissionError)
    if not (
        frappe.has_permission(meta.name, "create")
        or frappe.has_permission(meta.name, "write")
    ):
        frappe.throw(
            f"You do not have permission to create or edit {meta.name}.",
            frappe.PermissionError,
        )
    child_meta = _get_designed_transaction_child_meta(meta, child_doctype)
    item_field = child_meta.get_field("item_code")
    child_permitted_fields = set(
        get_permitted_fields(
            child_meta.name,
            parenttype=meta.name,
            user=frappe.session.user,
            permission_type="read",
        )
    )
    if (
        not item_field
        or item_field.fieldtype != "Link"
        or item_field.options != "Item"
        or item_field.fieldname not in child_permitted_fields
    ):
        frappe.throw(f"{meta.name} does not have a permitted Item Code field.")
    if not frappe.has_permission("Item", "read"):
        frappe.throw("You do not have permission to read Item.", frappe.PermissionError)

    item_code = str(item_code or "").strip()
    if not item_code:
        frappe.throw("Item Code is required.")
    item = frappe.get_doc("Item", item_code)
    item.check_permission("read")

    if isinstance(values, str):
        try:
            values = json.loads(values)
        except json.JSONDecodeError:
            frappe.throw("Transaction details must be valid JSON.")
    if not isinstance(values, dict):
        frappe.throw("Transaction details must be provided.")

    parent_values = {
        field.fieldname: values[field.fieldname]
        for field in meta.fields
        if field.fieldname and field.fieldname in values
    }
    args = {
        key: parent_values.get(key)
        for key in (
            "company",
            "transaction_date",
            "posting_date",
            "currency",
            "conversion_rate",
            "selling_price_list",
            "buying_price_list",
            "price_list_currency",
            "plc_conversion_rate",
            "ignore_pricing_rule",
            "customer",
            "supplier",
            "project",
        )
        if parent_values.get(key) not in (None, "")
    }
    args.update({
        "doctype": meta.name,
        "item_code": item_code,
        "qty": 1,
        "uom": "",
    })
    if meta.name == "Quotation" and parent_values.get("quotation_to") == "Customer":
        args["customer"] = parent_values.get("party_name")
    elif meta.name == "Quotation":
        args.pop("customer", None)
    for field in meta.fields:
        if field.fieldtype == "Dynamic Link" and field.fieldname in parent_values:
            args[field.fieldname] = parent_values[field.fieldname]

    from erpnext.stock.get_item_details import get_item_details

    details = get_item_details(args, doc=frappe._dict({"doctype": meta.name, **parent_values}))
    child_fields = set(
        get_permitted_fields(
            child_meta.name,
            parenttype=meta.name,
            user=frappe.session.user,
            permission_type="read",
        )
    )
    allowed_fields = {
        field.fieldname
        for field in child_meta.fields
        if field.fieldname
        and field.fieldname in child_fields
        and not field.hidden
        and field.fieldtype not in ("HTML", "Button", "Password")
    }
    return {
        key: value
        for key, value in details.items()
        if key in allowed_fields
    }


@frappe.whitelist()
def create_designed_transaction(doctype=None, values=None):
    meta = _get_designed_transaction_meta(doctype)
    if not frappe.has_permission(meta.name, "create"):
        frappe.throw(f"You do not have permission to create {meta.name}.", frappe.PermissionError)
    doc = frappe.get_doc({
        "doctype": meta.name,
        **_prepare_purchase_document_values(meta.name, values, meta.name),
    }).insert()
    return {"name": doc.name}


@frappe.whitelist()
def update_designed_transaction(doctype=None, name=None, values=None):
    meta = _get_designed_transaction_meta(doctype)
    name = str(name or "").strip()
    if not name:
        frappe.throw(f"{meta.name} ID is required.")
    doc = frappe.get_doc(meta.name, name)
    doc.check_permission("write")
    if doc.docstatus != 0:
        frappe.throw(f"Only draft {meta.name} records can be updated.")
    doc.update(_prepare_purchase_document_values(meta.name, values, meta.name))
    doc.save()
    return {"name": doc.name}


def _get_designed_transaction_actions(doc):
    from frappe.model.workflow import get_transitions, get_workflow_name, has_approval_access

    workflow_name = get_workflow_name(doc.doctype)
    workflow_actions = []
    workflow_state = ""
    if workflow_name:
        workflow = frappe.get_doc("Workflow", workflow_name)
        workflow_state = doc.get(workflow.workflow_state_field) or ""
        workflow_actions = [
            {"action": transition.action, "next_state": transition.next_state}
            for transition in get_transitions(doc, workflow)
            if has_approval_access(frappe.session.user, doc, transition)
        ]

    return {
        "docstatus": doc.docstatus,
        "can_create": bool(frappe.has_permission(doc.doctype, "create", throw=False)),
        "can_write": bool(frappe.has_permission(doc.doctype, "write", doc=doc, throw=False)),
        "workflow_state": workflow_state,
        "workflow_actions": workflow_actions,
        "can_submit": bool(
            not workflow_name
            and doc.meta.is_submittable
            and doc.docstatus == 0
            and frappe.has_permission(doc.doctype, "submit", doc=doc, throw=False)
        ),
        "can_cancel": bool(
            not workflow_name
            and doc.docstatus == 1
            and frappe.has_permission(doc.doctype, "cancel", doc=doc, throw=False)
        ),
    }


@frappe.whitelist()
def get_designed_transaction_actions(doctype=None, name=None):
    meta = _get_designed_transaction_meta(doctype)
    name = str(name or "").strip()
    if not name:
        frappe.throw(f"{meta.name} ID is required.")
    doc = frappe.get_doc(meta.name, name)
    doc.check_permission("read")
    return _get_designed_transaction_actions(doc)


@frappe.whitelist()
def run_designed_transaction_action(doctype=None, name=None, action=None):
    from frappe.model.workflow import apply_workflow, get_workflow_name

    meta = _get_designed_transaction_meta(doctype)
    name = str(name or "").strip()
    action = str(action or "").strip()
    if not name or not action:
        frappe.throw("A document and action are required.")

    doc = frappe.get_doc(meta.name, name)
    doc.check_permission("read")
    queued = False
    if get_workflow_name(meta.name):
        queued = apply_workflow(doc.as_json(), action) is None
    elif action == "Submit":
        if not doc.meta.is_submittable or doc.docstatus != 0:
            frappe.throw(f"{meta.name} cannot be submitted in its current state.")
        doc.check_permission("submit")
        doc.submit()
    elif action == "Cancel":
        if doc.docstatus != 1:
            frappe.throw(f"{meta.name} cannot be cancelled in its current state.")
        doc.check_permission("cancel")
        doc.cancel()
    else:
        frappe.throw(f"{action} is not an available action for {meta.name}.")

    doc = frappe.get_doc(meta.name, name)
    return {
        "name": doc.name,
        "queued": queued,
        "record": _serialize_designed_transaction_record(doc),
        "actions": _get_designed_transaction_actions(doc),
    }
