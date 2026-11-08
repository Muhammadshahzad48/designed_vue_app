frappe.pages["asset-movement-list"].on_page_load = function (wrapper) {
  const page = frappe.ui.make_app_page({
    parent: wrapper,
    title: __("Asset Movement"),
    single_column: true
  });

  page.wrapper.find(".page-head").hide();
  page.main.html('<div id="app">Loading asset movement…</div>');

  const script = document.createElement("script");
  script.src = `/assets/designed_vue_app/dist/js/designed_vue_app.js?v=${Date.now()}`;
  script.async = true;
  script.onerror = function () {
    page.main.html(
      '<div class="text-danger" role="alert">Unable to load the Asset Movement page assets. Run bench build and refresh this page.</div>'
    );
  };
  document.body.appendChild(script);
};
