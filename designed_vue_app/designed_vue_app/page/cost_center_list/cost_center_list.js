frappe.pages["cost-center-list"].on_page_load = function (wrapper) {
  const page = frappe.ui.make_app_page({
    parent: wrapper,
    title: __("Cost Center"),
    single_column: true
  });

  page.wrapper.find(".page-head").hide();
  page.main.html('<div id="app">Loading cost center…</div>');

  const script = document.createElement("script");
  script.src = `/assets/designed_vue_app/dist/js/designed_vue_app.js?v=${Date.now()}`;
  script.async = true;
  script.onerror = function () {
    page.main.html(
      '<div class="text-danger" role="alert">Unable to load the Cost Center page assets. Run bench build and refresh this page.</div>'
    );
  };
  document.body.appendChild(script);
};
