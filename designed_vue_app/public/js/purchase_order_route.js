frappe.router.on("change", () => {
	const route_parts = frappe.router.current_route || [];
	const [view, doctype, name] = route_parts;
	if (view === "Workspaces" && doctype === "Home") {
		window.location.assign("/app/designed-dashboard");
		return;
	}
	if (doctype === "DocType") return;
	const designed_doctypes = new Set([
		"Account",
		"Asset",
		"Asset Movement",
		"Bank",
		"Company",
		"Cost Center",
		"Customer",
		"Delivery Note",
		"Department",
		"Item",
		"Item Price",
		"Journal Entry",
		"Material Request",
		"Project",
		"Purchase Invoice",
		"Purchase Order",
		"Purchase Receipt",
		"Quotation",
		"Request for Quotation",
		"Role",
		"Sales Invoice",
		"Sales Order",
		"Stock Entry",
		"Stock Reconciliation",
		"Supplier",
		"Supplier Quotation",
		"Task",
		"Timesheet",
		"User",
		"Warehouse"
	]);
	if (view === "Form" && doctype === "Item" && name) {
		const query = new URLSearchParams({ doctype, name });
		window.location.assign(`/app/designed-doctype-list?${query.toString()}`);
		return;
	}
	if (designed_doctypes.has(doctype) && ["List", "Form"].includes(view)) {
		const route = `${doctype.toLowerCase().replaceAll(" ", "-")}-list`;
		window.location.assign(`/app/${route}`);
		return;
	}
	if (["List", "Form"].includes(view) && doctype) {
		frappe.model.with_doctype(doctype, () => {
			const meta = frappe.get_meta(doctype);
			if (!meta || meta.istable || meta.issingle || meta.is_virtual) return;

			const query = new URLSearchParams({ doctype });
			if (view === "Form" && name) query.set("name", name);
			window.location.assign(`/app/designed-doctype-list?${query.toString()}`);
		});
	}
});

if (window.location.pathname === "/app" || window.location.pathname === "/app/home") {
	window.location.assign("/app/designed-dashboard");
}
