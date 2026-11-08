import frappe


def update_website_context(context):
	if (frappe.local.path or "").strip("/") == "login":
		return {"app_name": "ERPNext"}

	return {}
