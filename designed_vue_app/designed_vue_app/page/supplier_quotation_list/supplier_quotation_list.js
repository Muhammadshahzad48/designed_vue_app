frappe.pages["supplier-quotation-list"].on_page_load = function (wrapper) {
  const page = frappe.ui.make_app_page({
    parent: wrapper,
    title: __("Supplier Quotation"),
    single_column: true
  });

  page.wrapper.find(".page-head").hide();
  page.main.html('<div id="app">Loading supplier quotation…</div>');

  const script = document.createElement("script");
  script.src = `/assets/designed_vue_app/dist/js/designed_vue_app.js?v=${Date.now()}`;
  script.async = true;
  script.onerror = function () {
    page.main.html(
      '<div class="text-danger" role="alert">Unable to load the Supplier Quotation page assets. Run bench build and refresh this page.</div>'
    );
  };
  document.body.appendChild(script);
};
