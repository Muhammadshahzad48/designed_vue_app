### Designed Vue App

Vue App

### Vue Item List

The app provides a screenshot-inspired Item list at `/app/product-list` and designed
transaction pages at their `-list` routes.
It fetches ERPNext Items and stock
through the whitelisted `designed_vue_app.designed_vue_app.api.get_products` method,
using the signed-in Frappe session. API credentials are not embedded in the browser.

The page source is kept in this app:

- `frontend/ProductList.vue` contains the list, filters, and metadata-driven Item form.
- `frontend/style.css` contains the page and form styles.
- `frontend/main.js` mounts the Vue page.
- `designed_vue_app/designed_vue_app/api.py` contains the Item APIs.
- `designed_vue_app/designed_vue_app/page/product_list/` contains the Desk page wrapper.
- `vite.config.js` builds the isolated browser bundle into `designed_vue_app/public/dist/`.

Use **New Item** on this page to create an Item without leaving the custom
interface. The form submits to
`designed_vue_app.designed_vue_app.api.create_product`; Frappe's normal Item
permissions and validation apply. Fields are generated from Item DocType metadata
and grouped by its tabs and sections. Link fields provide searchable suggestions,
and can open Frappe quick entry to add a permitted linked record (such as an Item
Group). Child tables can be filled by adding rows. Read-only fields are displayed
but are not submitted as editable values. The list refreshes after a successful
save.

Every DocType shortcut on the Designed ERP dashboard opens a dedicated `-list`
Desk page with its own page files and Vue entry component. Other installed,
permitted DocTypes use the universal `/app/designed-doctype-list` page when
opened from Frappe's standard List or Form routes. The shared metadata-driven
interface reflects current DocType fields and child tables, so Custom Fields
and new DocTypes do not need a new Vue wrapper. Item keeps its dedicated form.

Document forms save through Frappe's normal insert/save lifecycle. Submittable
documents expose Submit and Cancel actions when allowed by permissions, and
active Workflows show and apply their available transitions with Frappe's
workflow validation and document hooks. Submitted documents are read-only.

Build the app assets from the bench with `bench build --app designed_vue_app`.
Run `bench migrate` after changing the Desk page registration.

### Installation

You can install this app using the [bench](https://github.com/frappe/bench) CLI:

```bash
cd $PATH_TO_YOUR_BENCH
bench get-app $URL_OF_THIS_REPO --branch develop
bench install-app designed_vue_app
```

### Contributing

This app uses `pre-commit` for code formatting and linting. Please [install pre-commit](https://pre-commit.com/#installation) and enable it for this repository:

```bash
cd apps/designed_vue_app
pre-commit install
```

Pre-commit is configured to use the following tools for checking and formatting your code:

- ruff
- eslint
- prettier
- pyupgrade

### CI

This app can use GitHub Actions for CI. The following workflows are configured:

- CI: Installs this app and runs unit tests on every push to `develop` branch.
- Linters: Runs [Frappe Semgrep Rules](https://github.com/frappe/semgrep-rules) and [pip-audit](https://pypi.org/project/pip-audit/) on every pull request.


### License

mit
