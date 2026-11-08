<template>
  <main class="item-page po-page">
    <header class="item-page-heading">
      <div class="item-page-title">
        <button v-if="showCreateForm" class="back-to-items" type="button" @click="closeCreateForm">
          Purchase Orders
        </button>
        <span v-if="showCreateForm" class="title-divider">/</span>
        <h1>{{ showCreateForm ? (editingOrderName || 'New Purchase Order') : 'Purchase Order' }}</h1>
      </div>
      <div v-if="!showCreateForm" class="item-page-actions">
        <button class="new-item-button" type="button" @click="openCreateForm">
          ＋ Add Purchase Order
        </button>
      </div>
    </header>

    <template v-if="!showCreateForm">
      <form class="item-filters" @submit.prevent="fetchPurchaseOrders">
        <div class="filter-row filter-row-primary po-filter-row">
          <input v-model.trim="filters.po_number" placeholder="Purchase Order ID" aria-label="Purchase Order ID" />
          <input v-model.trim="filters.supplier" placeholder="Supplier" aria-label="Supplier" />
          <input v-model.trim="filters.supplier_name" placeholder="Supplier Name" aria-label="Supplier Name" />
          <input v-model.trim="filters.company" placeholder="Company" aria-label="Company" />
          <select v-model="filters.status" aria-label="Purchase Order status">
            <option value="All">All Status</option>
            <option value="Draft">Draft</option>
            <option value="To Receive and Bill">To Receive and Bill</option>
            <option value="To Bill">To Bill</option>
            <option value="To Receive">To Receive</option>
            <option value="Completed">Completed</option>
            <option value="Cancelled">Cancelled</option>
            <option value="Closed">Closed</option>
          </select>
          <div class="filter-buttons">
            <button class="show-button" type="submit" :disabled="loadingOrders">Show</button>
            <button class="clear-button" type="button" :disabled="loadingOrders" @click="resetFilters">Clear</button>
          </div>
        </div>
      </form>

      <div class="table-tools">
        <div v-if="loadError" class="error-message" role="alert">
          <span>{{ loadError }}</span>
          <button type="button" @click="fetchPurchaseOrders">Try again</button>
        </div>
        <span v-else-if="loadingOrders" class="po-loading-label">Loading Purchase Orders…</span>
        <span v-else class="po-loading-label">{{ filteredOrders.length }} Purchase Orders</span>
      </div>

      <div class="items-table-scroll">
        <table class="items-table po-table">
          <thead>
            <tr>
              <th>PURCHASE ORDER</th>
              <th>SUPPLIER</th>
              <th>SUPPLIER NAME</th>
              <th>ORDER DATE</th>
              <th>STATUS</th>
              <th class="numeric-column">AMOUNT</th>
            </tr>
          </thead>
          <tbody>
            <tr
              v-for="order in filteredOrders"
              :key="order.po_number"
              class="po-clickable-row"
              tabindex="0"
              @click="openExistingOrder(order.po_number)"
              @keydown.enter="openExistingOrder(order.po_number)"
            >
              <td>
                <span class="product-description">
                  <a class="product-code" href="#" @click.prevent.stop="openExistingOrder(order.po_number)">
                    {{ order.po_number }}
                  </a>
                </span>
              </td>
              <td>{{ order.supplier || '—' }}</td>
              <td>{{ order.supplier_name || '—' }}</td>
              <td>{{ formatDate(order.order_date) }}</td>
              <td>
                <span class="item-status" :class="statusClass(order.status)">
                  {{ order.status || 'Draft' }}
                </span>
              </td>
              <td class="numeric-column">{{ formatPrice(order.total) }}</td>
            </tr>
            <tr v-if="loadingOrders">
              <td colspan="6" class="table-message">Loading Purchase Orders…</td>
            </tr>
            <tr v-else-if="!loadError && filteredOrders.length === 0">
              <td colspan="6" class="table-message">No Purchase Orders found.</td>
            </tr>
          </tbody>
        </table>
      </div>
      <footer class="table-footer">
        <span>{{ loadingOrders ? 'Loading…' : `${filteredOrders.length} Purchase Orders` }}</span>
        <span>ERPNext Purchase Order List</span>
      </footer>
    </template>

    <section v-else class="item-create">

      <form class="item-create-form" @submit.prevent="savePurchaseOrder">
        <header class="po-form-header">
          <div>
            <p class="po-eyebrow">PURCHASE ORDER</p>
            <h3>{{ editingOrderName ? 'Edit Purchase Order' : 'Create a Purchase Order' }}</h3>
            <p class="po-subtitle">Complete the Purchase Order fields below. It will be saved to ERPNext.</p>
          </div>
          <div class="po-form-header-actions">
            <span v-if="documentActions.workflow_state" class="po-workflow-state">
              {{ documentActions.workflow_state }}
            </span>
            <button
              v-for="action in documentActions.workflow_actions"
              :key="action.action"
              class="save-item-button transaction-workflow-action"
              type="button"
              :disabled="savingOrder"
              @click="runDocumentAction(action.action)"
            >
              {{ savingOrder ? 'Working…' : action.action }}
            </button>
            <button
              v-if="documentActions.can_submit"
              class="save-item-button transaction-workflow-action"
              type="button"
              :disabled="savingOrder"
              @click="runDocumentAction('Submit')"
            >
              {{ savingOrder ? 'Submitting…' : 'Submit' }}
            </button>
            <button
              v-if="documentActions.can_cancel"
              class="po-cancel-btn transaction-workflow-action"
              type="button"
              :disabled="savingOrder"
              @click="runDocumentAction('Cancel')"
            >
              {{ savingOrder ? 'Cancelling…' : 'Cancel Document' }}
            </button>
            <button class="po-cancel-btn" type="button" :disabled="savingOrder" @click="closeCreateForm">Close</button>
          </div>
        </header>

        <p v-if="formOptionsError" class="form-options-error" role="alert">
          {{ formOptionsError }}
          <button type="button" @click="loadFormMetadata">Try again</button>
        </p>
        <p v-if="createError" class="form-options-error" role="alert">{{ createError }}</p>
        <section v-if="formTabs.length" class="required-fields-panel">
          <div v-if="editingOrderName" class="po-document-state">
            <span class="po-state-badge" :class="`po-state-${Number(newOrder.docstatus)}`">
              {{ documentStateLabel }}
            </span>
            <span v-if="newOrder.status">{{ newOrder.status }}</span>
            <span v-if="isSubmitted">Submitted Purchase Orders are read-only.</span>
          </div>
          <fieldset class="po-form-fields" :disabled="!canEditDocument">
            <nav class="item-form-tabs" aria-label="Purchase Order field tabs">
              <button
                v-for="tab in formTabs"
                :key="tab"
                type="button"
                :class="{ 'active-form-tab': activeFormTab === tab }"
                @click="activeFormTab = tab"
              >
                {{ tab }}
              </button>
            </nav>
            <details
              v-for="section in formSections.filter((entry) => entry.tab === activeFormTab)"
              :key="`${section.tab}-${section.section}`"
              class="item-form-section required-field-section po-form-section"
              open
            >
              <summary class="po-section-heading">{{ section.section }}</summary>
              <div class="item-form-grid">
              <div
                v-for="field in section.fields"
                :key="field.fieldname"
                class="item-form-field"
                :class="{ 'item-form-field-wide': field.fieldtype === 'Table' }"
              >
                <label v-if="field.fieldtype === 'Check'" class="item-form-checkbox">
                  <input
                    v-model="newOrder[field.fieldname]"
                    type="checkbox"
                    :true-value="true"
                    :false-value="false"
                    :disabled="field.read_only || savingOrder"
                  />
                  <span>{{ field.label }} <b v-if="isRequiredFormField(field)">*</b></span>
                </label>
                <template v-else>
                  <span>
                    {{ field.label }}
                    <b v-if="isRequiredFormField(field)">*</b>
                    <small v-else-if="field.mandatory_depends_on">(required when applicable)</small>
                  </span>
                  <div v-if="field.fieldtype === 'Table'" class="required-child-table">
                    <p v-if="!newOrder[field.fieldname]?.length" class="empty-child-table">No rows added.</p>
                    <details
                      v-for="(row, rowIndex) in newOrder[field.fieldname]"
                      :key="rowIndex"
                      class="required-child-row"
                      :open="isChildRowExpanded(field, rowIndex)"
                      @toggle="setChildRowExpanded(field, rowIndex, $event)"
                    >
                      <summary class="po-child-row-summary">
                        <strong>{{ row.item_code || row.item_name || `${field.label} ${rowIndex + 1}` }}</strong>
                        <span v-if="row.qty">Qty: {{ row.qty }}</span>
                        <span v-if="row.rate">Rate: {{ formatPrice(row.rate) }}</span>
                        <span v-if="row.amount">Amount: {{ formatPrice(row.amount) }}</span>
                        <span class="po-child-edit-hint">{{ isSubmitted ? 'View details' : 'Click to edit' }}</span>
                      </summary>
                      <div class="po-child-row-fields">
                        <template v-for="child in field.children" :key="child.fieldname">
                        <label v-if="child.fieldtype === 'Check'" class="item-form-checkbox">
                          <input
                            v-model="row[child.fieldname]"
                            type="checkbox"
                            :true-value="true"
                            :false-value="false"
                            :disabled="child.read_only || savingOrder"
                          />
                          <span>{{ child.label }} <b v-if="isRequiredFormField(child)">*</b></span>
                        </label>
                        <label v-else class="item-form-field">
                          <span>
                            {{ child.label }}
                            <b v-if="isRequiredFormField(child)">*</b>
                            <small v-else-if="child.mandatory_depends_on">(required when applicable)</small>
                          </span>
                          <select
                            v-if="child.fieldtype === 'Select'"
                            v-model="row[child.fieldname]"
                            :required="isRequiredFormField(child) && !child.read_only"
                            :disabled="child.read_only || savingOrder"
                          >
                            <option value="">Select {{ child.label }}</option>
                            <option v-for="option in child.options" :key="option" :value="option">{{ option }}</option>
                          </select>
                          <template v-else-if="isItemAutocompleteField(child)">
                            <div class="form-link-control po-autocomplete-control">
                              <input
                                v-model="row[child.fieldname]"
                                :aria-expanded="activeSuggestionKey === itemSuggestionKey(child, field.table_doctype, rowIndex)"
                                aria-autocomplete="list"
                                :required="isRequiredFormField(child) && !child.read_only"
                                :disabled="(child.read_only && !isItemAutocompleteField(child)) || savingOrder"
                                autocomplete="off"
                                @focus="openItemSuggestions(child, field.table_doctype, rowIndex)"
                                @blur="scheduleCloseSuggestions(itemSuggestionKey(child, field.table_doctype, rowIndex))"
                                @input="scheduleItemSuggestions(child, field.table_doctype, rowIndex, row[child.fieldname])"
                                @keydown.esc="closeSuggestions"
                              />
                              <ul
                                v-if="activeSuggestionKey === itemSuggestionKey(child, field.table_doctype, rowIndex)"
                                class="po-link-suggestions"
                                role="listbox"
                              >
                                <li
                                  v-if="!getItemOptions(child, field.table_doctype, rowIndex).length"
                                  class="po-link-suggestion-empty"
                                >
                                  No matching items
                                </li>
                                <li
                                  v-for="item in getItemOptions(child, field.table_doctype, rowIndex)"
                                  :key="item.item_code"
                                  role="option"
                                  @pointerdown.prevent="selectItemOption(item, field, row, rowIndex)"
                                >
                                  <strong>{{ item.item_code }}</strong>
                                  <small>{{ item.item_name }}</small>
                                </li>
                              </ul>
                            </div>
                          </template>
                          <template v-else-if="child.fieldtype === 'Link'">
                            <div class="form-link-control po-autocomplete-control">
                              <input
                                v-model="row[child.fieldname]"
                                :aria-expanded="activeSuggestionKey === linkOptionKey(child, field.table_doctype, rowIndex)"
                                aria-autocomplete="list"
                                :required="isRequiredFormField(child) && !child.read_only"
                                :disabled="child.read_only || savingOrder"
                                autocomplete="off"
                                @focus="openFieldSuggestions(child, field.table_doctype, rowIndex)"
                                @blur="scheduleCloseSuggestions(linkOptionKey(child, field.table_doctype, rowIndex))"
                                @input="scheduleFieldSuggestions(child, field.table_doctype, rowIndex, row[child.fieldname])"
                                @keydown.esc="closeSuggestions"
                              />
                              <ul
                                v-if="activeSuggestionKey === linkOptionKey(child, field.table_doctype, rowIndex)"
                                class="po-link-suggestions"
                                role="listbox"
                              >
                                <li
                                  v-if="!getFieldOptions(child, field.table_doctype, rowIndex).length"
                                  class="po-link-suggestion-empty"
                                >
                                  No matching {{ child.link_doctype }} records
                                </li>
                                <li
                                  v-for="option in getFieldOptions(child, field.table_doctype, rowIndex)"
                                  :key="option"
                                  role="option"
                                  @pointerdown.prevent="selectLinkOption(child, field.table_doctype, rowIndex, option, (name) => { row[child.fieldname] = name; })"
                                >
                                  {{ option }}
                                </li>
                              </ul>
                              <button
                                v-if="canCreateLinkedDocument(child)"
                                class="form-link-create"
                                type="button"
                                :disabled="savingOrder"
                                @click="createLinkedDocument(child, (name) => { row[child.fieldname] = name; }, field.table_doctype, rowIndex)"
                              >
                                + Add {{ child.link_doctype }}
                              </button>
                            </div>
                          </template>
                          <textarea
                            v-else-if="isLongTextField(child.fieldtype)"
                            v-model="row[child.fieldname]"
                            rows="3"
                            :required="isRequiredFormField(child) && !child.read_only"
                            :disabled="child.read_only || savingOrder"
                          ></textarea>
                          <input
                            v-else
                            v-model="row[child.fieldname]"
                            :type="formInputType(child.fieldtype)"
                            :required="isRequiredFormField(child) && !child.read_only"
                            :disabled="child.read_only || savingOrder"
                          />
                        </label>
                        </template>
                        <button
                          v-if="canEditDocument"
                          class="remove-child-row"
                          type="button"
                          :disabled="savingOrder"
                          :aria-label="`Remove ${field.label} row ${rowIndex + 1}`"
                          @click="removeRequiredTableRow(field, rowIndex)"
                        >
                          Remove
                        </button>
                      </div>
                    </details>
                    <button
                      v-if="canEditDocument"
                      class="add-child-row"
                      type="button"
                      :disabled="savingOrder"
                      @click="addRequiredTableRow(field)"
                    >
                      + Add {{ field.label }}
                    </button>
                  </div>
                  <select
                    v-else-if="field.fieldtype === 'Select'"
                    v-model="newOrder[field.fieldname]"
                    :required="isRequiredFormField(field) && !field.read_only"
                    :disabled="field.read_only || savingOrder"
                  >
                    <option value="">Select {{ field.label }}</option>
                    <option v-for="option in field.options" :key="option" :value="option">{{ option }}</option>
                  </select>
                  <template v-else-if="field.fieldtype === 'Link'">
                    <div class="form-link-control po-autocomplete-control">
                      <input
                        v-model="newOrder[field.fieldname]"
                        :aria-expanded="activeSuggestionKey === linkOptionKey(field)"
                        aria-autocomplete="list"
                        :required="isRequiredFormField(field) && !field.read_only"
                        :disabled="field.read_only || savingOrder"
                        autocomplete="off"
                        @focus="openFieldSuggestions(field)"
                        @blur="scheduleCloseSuggestions(linkOptionKey(field))"
                        @input="scheduleFieldSuggestions(field, '', null, newOrder[field.fieldname])"
                        @keydown.esc="closeSuggestions"
                      />
                      <ul
                        v-if="activeSuggestionKey === linkOptionKey(field)"
                        class="po-link-suggestions"
                        role="listbox"
                      >
                        <li v-if="!getFieldOptions(field).length" class="po-link-suggestion-empty">
                          No matching {{ field.link_doctype }} records
                        </li>
                        <li
                          v-for="option in getFieldOptions(field)"
                          :key="option"
                          role="option"
                          @pointerdown.prevent="selectLinkOption(field, '', null, option, (name) => { newOrder[field.fieldname] = name; })"
                        >
                          {{ option }}
                        </li>
                      </ul>
                      <button
                        v-if="canCreateLinkedDocument(field)"
                        class="form-link-create"
                        type="button"
                        :disabled="savingOrder"
                        @click="createLinkedDocument(field, (name) => { newOrder[field.fieldname] = name; })"
                      >
                        + Add {{ field.link_doctype }}
                      </button>
                    </div>
                  </template>
                  <textarea
                    v-else-if="isLongTextField(field.fieldtype)"
                    v-model="newOrder[field.fieldname]"
                    rows="3"
                    :required="isRequiredFormField(field) && !field.read_only"
                    :disabled="field.read_only || savingOrder"
                  ></textarea>
                  <input
                    v-else
                    v-model="newOrder[field.fieldname]"
                    :type="formInputType(field.fieldtype)"
                    :required="isRequiredFormField(field) && !field.read_only"
                    :disabled="field.read_only || savingOrder"
                  />
                </template>
              </div>
              </div>
            </details>
          </fieldset>
        </section>

        <footer class="item-form-actions">
          <button class="form-cancel-button" type="button" :disabled="savingOrder" @click="closeCreateForm">
            Cancel
          </button>
          <button v-if="canEditDocument" class="save-item-button" type="submit" :disabled="savingOrder || !formTabs.length">
            {{ savingOrder ? 'Saving…' : editingOrderName ? 'Update Purchase Order' : 'Save Purchase Order' }}
          </button>
          <span v-else class="po-readonly-note">
            {{ Number(newOrder.docstatus) === 2 ? 'This document has been cancelled.' : 'This document has already been submitted.' }}
          </span>
        </footer>
      </form>
    </section>
  </main>
</template>

<script>
const buildNewOrder = () => ({
  transaction_date: new Date().toISOString().slice(0, 10)
});

export default {
  data() {
    return {
      showCreateForm: false,
      editingOrderName: '',
      expandedChildRows: {},
      savingOrder: false,
      loadingOrders: false,
      loadError: '',
      purchaseOrders: [],
      formSections: [],
      formTabs: [],
      activeFormTab: '',
      formOptionsError: '',
      createError: '',
      formLinkOptions: {},
      formLinkTimers: {},
      formLinkRequestIds: {},
      itemOptions: {},
      itemOptionTimers: {},
      itemOptionRequestIds: {},
      activeSuggestionKey: '',
      suggestionCloseTimers: {},
      filters: {
        po_number: '',
        supplier: '',
        supplier_name: '',
        company: '',
        status: 'All'
      },
      newOrder: buildNewOrder(),
      documentActions: { workflow_actions: [], workflow_state: '', can_submit: false, can_cancel: false, can_create: false, can_write: false }
    };
  },
  computed: {
    canEditDocument() {
      return !this.isSubmitted && Boolean(
        this.editingOrderName ? this.documentActions.can_write : this.documentActions.can_create
      );
    },
    isSubmitted() {
      return Number(this.newOrder.docstatus) > 0;
    },
    documentStateLabel() {
      const state = Number(this.newOrder.docstatus);
      if (state === 1) return 'Submitted';
      if (state === 2) return 'Cancelled';
      return 'Draft';
    },
    filteredOrders() {
      return this.purchaseOrders.filter((order) => {
        const poMatch = !this.filters.po_number || String(order.po_number || '').toLowerCase().includes(this.filters.po_number.toLowerCase());
        const supplierMatch = !this.filters.supplier || String(order.supplier || '').toLowerCase().includes(this.filters.supplier.toLowerCase());
        const supplierNameMatch = !this.filters.supplier_name || String(order.supplier_name || '').toLowerCase().includes(this.filters.supplier_name.toLowerCase());
        const companyMatch = !this.filters.company || String(order.company || '').toLowerCase().includes(this.filters.company.toLowerCase());
        const statusMatch = this.filters.status === 'All' || (order.status || 'Draft') === this.filters.status;
        return poMatch && supplierMatch && supplierNameMatch && companyMatch && statusMatch;
      });
    },
  },
  mounted() {
    this.fetchPurchaseOrders();
  },
  methods: {
    statusClass(status) {
      return ['Cancelled', 'Closed'].includes(status) ? 'item-status-disabled' : '';
    },
    async fetchPurchaseOrders() {
      this.loadingOrders = true;
      this.loadError = '';
      try {
        if (typeof window.frappe?.xcall !== 'function') {
          throw new Error('Frappe is not ready.');
        }
        const result = await window.frappe.xcall('designed_vue_app.designed_vue_app.api.get_purchase_orders', {
          filters: JSON.stringify(this.filters)
        });
        const orders = Array.isArray(result?.purchase_orders) ? result.purchase_orders : [];
        this.purchaseOrders = orders;
      } catch (error) {
        console.error('Unable to load purchase orders:', error);
        this.purchaseOrders = [];
        this.loadError = typeof error === 'string'
          ? error
          : error?.message || 'Unable to load purchase orders. Please try again.';
      } finally {
        this.loadingOrders = false;
      }
    },
    openCreateForm() {
      this.newOrder = buildNewOrder();
      this.editingOrderName = '';
      this.documentActions = {
        workflow_actions: [],
        workflow_state: '',
        can_submit: false,
        can_cancel: false,
        can_create: Boolean(window.frappe?.model?.can_create?.('Purchase Order')),
        can_write: false
      };
      this.expandedChildRows = {};
      this.formOptionsError = '';
      this.createError = '';
      this.formSections = [];
      this.formTabs = [];
      this.activeFormTab = '';
      this.formLinkOptions = {};
      this.itemOptions = {};
      this.activeSuggestionKey = '';
      this.showCreateForm = true;
      this.loadFormMetadata();
    },
    async openExistingOrder(poNumber) {
      this.newOrder = buildNewOrder();
      this.editingOrderName = poNumber;
      this.documentActions = { workflow_actions: [], workflow_state: '', can_submit: false, can_cancel: false };
      this.expandedChildRows = {};
      this.formOptionsError = '';
      this.createError = '';
      this.formSections = [];
      this.formTabs = [];
      this.activeFormTab = '';
      this.formLinkOptions = {};
      this.itemOptions = {};
      this.activeSuggestionKey = '';
      this.showCreateForm = true;
      await this.loadFormMetadata();
      if (!this.formTabs.length) return;

      try {
        const result = await window.frappe.xcall(
          'designed_vue_app.designed_vue_app.api.get_purchase_order',
          { po_number: poNumber }
        );
        if (!result?.purchase_order) {
          throw new Error(`Purchase Order ${poNumber} could not be loaded.`);
        }
        this.newOrder = { ...this.newOrder, ...result.purchase_order };
        await this.refreshDocumentActions();
      } catch (error) {
        console.error(`Unable to load Purchase Order ${poNumber}:`, error);
        this.createError = typeof error === 'string'
          ? error
          : error?.message || `Unable to load Purchase Order ${poNumber}.`;
      }
    },
    resetFilters() {
      this.filters = {
        po_number: '',
        supplier: '',
        supplier_name: '',
        company: '',
        status: 'All'
      };
      this.fetchPurchaseOrders();
    },
    async loadFormMetadata() {
      this.formOptionsError = '';
      try {
        if (typeof window.frappe?.xcall !== 'function') {
          throw new Error('Frappe is not ready. Reload the page and try again.');
        }
        const sections = await window.frappe.xcall('designed_vue_app.designed_vue_app.api.get_purchase_order_form_fields');
        if (!Array.isArray(sections) || !sections.length) {
          throw new Error('Purchase Order field metadata was empty.');
        }
        this.formSections = sections;
        this.formTabs = [...new Set(sections.map((section) => section.tab))];
        this.activeFormTab = this.formTabs[0] || '';
        this.initializeFormDefaults();
      } catch (error) {
        console.error('Unable to load Purchase Order form metadata:', error);
        this.formSections = [];
        this.formTabs = [];
        this.formOptionsError = typeof error === 'string'
          ? error
          : error?.message || 'Unable to load Purchase Order fields. Please try again.';
      }
    },
    initializeFormDefaults() {
      const fields = this.formSections.flatMap((section) => section.fields);
      fields.forEach((field) => {
        if (field.fieldtype === 'Table') {
          this.newOrder[field.fieldname] = field.table_doctype === 'Purchase Order Item'
            ? [this.createTableRow(field)]
            : [];
        } else if (this.newOrder[field.fieldname] === undefined || this.newOrder[field.fieldname] === '') {
          this.newOrder[field.fieldname] = this.formFieldDefault(field);
        }
      });
    },
    formFieldDefault(field) {
      if (field.default !== undefined && field.default !== null && field.default !== '') {
        if (field.fieldtype === 'Check') {
          return field.default === true || field.default === 1 || field.default === '1';
        }
        if (field.default === '__today' && field.fieldtype === 'Date') {
          return new Date().toISOString().slice(0, 10);
        }
        return field.default;
      }
      return field.fieldtype === 'Check' ? false : '';
    },
    isRequiredFormField(field) {
      return Boolean(field.required);
    },
    isItemAutocompleteField(field) {
      return ['item_code', 'item_name'].includes(field.fieldname);
    },
    isLongTextField(fieldtype) {
      return ['Text', 'Text Editor', 'Small Text', 'Long Text', 'Code', 'JSON'].includes(fieldtype);
    },
    formInputType(fieldtype) {
      if (['Int', 'Float', 'Currency', 'Percent', 'Rating', 'Duration'].includes(fieldtype)) return 'number';
      if (fieldtype === 'Date') return 'date';
      if (fieldtype === 'Datetime') return 'datetime-local';
      if (fieldtype === 'Time') return 'time';
      return 'text';
    },
    linkOptionKey(field, childDoctype = '', rowIndex = null) {
      return `${childDoctype || 'Purchase Order'}:${rowIndex ?? 'parent'}:${field.fieldname}`;
    },
    itemSuggestionKey(field, childDoctype, rowIndex) {
      return this.linkOptionKey(field, childDoctype, rowIndex);
    },
    getFieldOptions(field, childDoctype = '', rowIndex = null) {
      const key = this.linkOptionKey(field, childDoctype, rowIndex);
      return this.formLinkOptions[key] || [];
    },
    getItemOptions(field, childDoctype, rowIndex) {
      return this.itemOptions[this.itemSuggestionKey(field, childDoctype, rowIndex)] || [];
    },
    openFieldSuggestions(field, childDoctype = '', rowIndex = null) {
      const key = this.linkOptionKey(field, childDoctype, rowIndex);
      window.clearTimeout(this.suggestionCloseTimers[key]);
      this.activeSuggestionKey = key;
      this.loadFieldSuggestions(field, childDoctype, rowIndex);
    },
    openItemSuggestions(field, childDoctype, rowIndex) {
      const key = this.itemSuggestionKey(field, childDoctype, rowIndex);
      window.clearTimeout(this.suggestionCloseTimers[key]);
      this.activeSuggestionKey = key;
      this.loadItemOptions(field, childDoctype, rowIndex);
    },
    scheduleCloseSuggestions(key) {
      this.suggestionCloseTimers[key] = window.setTimeout(() => {
        if (this.activeSuggestionKey === key) this.activeSuggestionKey = '';
      }, 150);
    },
    closeSuggestions() {
      this.activeSuggestionKey = '';
    },
    async loadFieldSuggestions(field, childDoctype = '', rowIndex = null, txt = '') {
      if (field.fieldtype !== 'Link' || !field.link_doctype) return;
      const key = this.linkOptionKey(field, childDoctype, rowIndex);
      const requestId = (this.formLinkRequestIds[key] || 0) + 1;
      this.formLinkRequestIds[key] = requestId;
      try {
        const options = await window.frappe.xcall(
          'designed_vue_app.designed_vue_app.api.get_purchase_order_link_options',
          {
            fieldname: field.fieldname,
            child_doctype: childDoctype,
            txt: txt || ''
          }
        );
        if (this.formLinkRequestIds[key] === requestId) {
          this.formLinkOptions[key] = Array.isArray(options) ? options : [];
          this.formOptionsError = '';
        }
      } catch (error) {
        console.error(`Unable to load ${field.label} options:`, error);
        if (this.formLinkRequestIds[key] === requestId) {
          this.formOptionsError = typeof error === 'string'
            ? error
            : error?.message || `Unable to load options for ${field.label}.`;
        }
      }
    },
    scheduleFieldSuggestions(field, childDoctype = '', rowIndex = null, txt = '') {
      const key = this.linkOptionKey(field, childDoctype, rowIndex);
      window.clearTimeout(this.formLinkTimers[key]);
      this.formLinkTimers[key] = window.setTimeout(
        () => this.loadFieldSuggestions(field, childDoctype, rowIndex, txt),
        180
      );
    },
    async loadItemOptions(field, childDoctype, rowIndex, txt = '') {
      const key = this.itemSuggestionKey(field, childDoctype, rowIndex);
      const requestId = (this.itemOptionRequestIds[key] || 0) + 1;
      this.itemOptionRequestIds[key] = requestId;
      try {
        const options = await window.frappe.xcall(
          'designed_vue_app.designed_vue_app.api.get_purchase_order_item_options',
          {
            search_by: field.fieldname,
            txt: txt || ''
          }
        );
        if (this.itemOptionRequestIds[key] === requestId) {
          this.itemOptions[key] = Array.isArray(options) ? options : [];
          this.formOptionsError = '';
        }
      } catch (error) {
        console.error(`Unable to load ${field.label} options:`, error);
        if (this.itemOptionRequestIds[key] === requestId) {
          this.itemOptions[key] = [];
          this.formOptionsError = typeof error === 'string'
            ? error
            : error?.message || 'Unable to load Item options.';
        }
      }
    },
    scheduleItemSuggestions(field, childDoctype, rowIndex, txt = '') {
      const key = this.itemSuggestionKey(field, childDoctype, rowIndex);
      this.activeSuggestionKey = key;
      window.clearTimeout(this.itemOptionTimers[key]);
      this.itemOptionTimers[key] = window.setTimeout(
        () => this.loadItemOptions(field, childDoctype, rowIndex, txt),
        180
      );
    },
    selectItemOption(item, tableField, row, rowIndex) {
      row.item_code = item.item_code;
      row.item_name = item.item_name;
      if ('uom' in row) row.uom = item.stock_uom || row.uom;
      if ('stock_uom' in row) row.stock_uom = item.stock_uom || row.stock_uom;
      if ('rate' in row) row.rate = Number(item.standard_rate || 0);
      if ('price_list_rate' in row) row.price_list_rate = Number(item.standard_rate || 0);
      if ('qty' in row && !Number(row.qty)) row.qty = 1;
      if ('quantity' in row && !Number(row.quantity)) row.quantity = 1;
      if ('description' in row && item.description) row.description = item.description;
      if ('amount' in row) row.amount = Number(row.qty || row.quantity || 0) * Number(row.rate || 0);
      this.activeSuggestionKey = '';
      this.itemOptions[this.itemSuggestionKey({ fieldname: 'item_code' }, tableField.table_doctype, rowIndex)] = [];
      this.itemOptions[this.itemSuggestionKey({ fieldname: 'item_name' }, tableField.table_doctype, rowIndex)] = [];
    },
    selectLinkOption(field, childDoctype, rowIndex, option, applyValue) {
      applyValue(option);
      this.activeSuggestionKey = '';
      this.loadFieldSuggestions(field, childDoctype, rowIndex, option);
    },
    canCreateLinkedDocument(field) {
      return Boolean(
        field.link_doctype
        && typeof window.frappe?.model?.can_create === 'function'
        && window.frappe.model.can_create(field.link_doctype)
        && typeof window.frappe?.ui?.form?.make_quick_entry === 'function'
      );
    },
    createLinkedDocument(field, onCreated, childDoctype = '', rowIndex = null) {
      if (!this.canCreateLinkedDocument(field)) return;
      window.frappe.ui.form.make_quick_entry(
        field.link_doctype,
        (doc) => {
          onCreated(doc.name);
          this.loadFieldSuggestions(field, childDoctype, rowIndex, doc.name);
        },
        null,
        null,
        true
      );
    },
    createTableRow(field) {
      return Object.fromEntries(
        (field.children || []).map((child) => [child.fieldname, this.formFieldDefault(child)])
      );
    },
    childRowKey(field, rowIndex) {
      return `${field.fieldname}:${rowIndex}`;
    },
    isChildRowExpanded(field, rowIndex) {
      return Boolean(this.expandedChildRows[this.childRowKey(field, rowIndex)]);
    },
    setChildRowExpanded(field, rowIndex, event) {
      this.expandedChildRows[this.childRowKey(field, rowIndex)] = event.currentTarget.open;
    },
    addRequiredTableRow(field) {
      const rows = this.newOrder[field.fieldname];
      rows.push(this.createTableRow(field));
      this.expandedChildRows[this.childRowKey(field, rows.length - 1)] = true;
    },
    removeRequiredTableRow(field, rowIndex) {
      this.newOrder[field.fieldname].splice(rowIndex, 1);
      this.expandedChildRows = Object.fromEntries(
        Object.entries(this.expandedChildRows)
          .filter(([key]) => !key.startsWith(`${field.fieldname}:`))
      );
    },
    closeCreateForm() {
      if (this.savingOrder) return;
      this.showCreateForm = false;
      this.editingOrderName = '';
      this.createError = '';
    },
    async savePurchaseOrder() {
      if (this.savingOrder) return;
      if (this.isSubmitted) {
        this.createError = 'Submitted Purchase Orders cannot be edited.';
        return;
      }
      const missingTable = this.formSections
        .flatMap((section) => section.fields)
        .find((field) => field.fieldtype === 'Table'
          && this.isRequiredFormField(field)
          && !this.newOrder[field.fieldname]?.length);
      if (missingTable) {
        this.createError = `${missingTable.label} is required. Add at least one row.`;
        this.activeFormTab = this.formSections.find((section) => section.fields.includes(missingTable))?.tab || '';
        return;
      }

      this.savingOrder = true;
      this.createError = '';

      try {
        if (typeof window.frappe?.xcall !== 'function') {
          throw new Error('Frappe is not ready. Reload the page and try again.');
        }

        const endpoint = this.editingOrderName
          ? 'designed_vue_app.designed_vue_app.api.update_purchase_order'
          : 'designed_vue_app.designed_vue_app.api.create_purchase_order';
        const parameters = {
          purchase_order: JSON.stringify(this.newOrder)
        };
        if (this.editingOrderName) parameters.po_number = this.editingOrderName;
        const result = await window.frappe.xcall(endpoint, parameters);
        if (!result?.purchase_order?.po_number) {
          throw new Error('The server did not confirm that the Purchase Order was saved.');
        }

        this.editingOrderName = result.purchase_order.po_number;
        const saved = await window.frappe.xcall(
          'designed_vue_app.designed_vue_app.api.get_purchase_order',
          { po_number: this.editingOrderName }
        );
        if (!saved?.purchase_order) throw new Error('The saved Purchase Order could not be reloaded.');
        this.newOrder = { ...this.newOrder, ...saved.purchase_order };
        await this.refreshDocumentActions();
        await this.fetchPurchaseOrders();
      } catch (error) {
        console.error('Unable to save Purchase Order:', error);
        this.createError = typeof error === 'string'
          ? error
          : error?.response?.data?.message || error?.message || 'Unable to save Purchase Order.';
      } finally {
        this.savingOrder = false;
      }
    },
    async refreshDocumentActions() {
      if (!this.editingOrderName) {
        this.documentActions = {
          workflow_actions: [],
          workflow_state: '',
          can_submit: false,
          can_cancel: false,
          can_create: Boolean(window.frappe?.model?.can_create?.('Purchase Order')),
          can_write: false
        };
        return;
      }
      this.documentActions = await window.frappe.xcall(
        'designed_vue_app.designed_vue_app.api.get_designed_transaction_actions',
        { doctype: 'Purchase Order', name: this.editingOrderName }
      );
    },
    async runDocumentAction(action) {
      if (action === 'Cancel') {
        window.frappe.confirm(
          `Cancel Purchase Order ${this.editingOrderName}?`,
          () => this.executeDocumentAction(action)
        );
        return;
      }
      await this.executeDocumentAction(action);
    },
    async executeDocumentAction(action) {
      if (this.savingOrder || !this.editingOrderName) return;
      this.savingOrder = true;
      this.createError = '';
      try {
        const result = await window.frappe.xcall(
          'designed_vue_app.designed_vue_app.api.run_designed_transaction_action',
          { doctype: 'Purchase Order', name: this.editingOrderName, action }
        );
        if (!result?.record) throw new Error(`Frappe did not confirm ${action}.`);
        this.newOrder = { ...this.newOrder, ...result.record };
        this.documentActions = result.actions;
        await this.fetchPurchaseOrders();
      } catch (error) {
        console.error(`Unable to ${action} Purchase Order:`, error);
        this.createError = error?.message || `Unable to ${action} Purchase Order.`;
      } finally {
        this.savingOrder = false;
      }
    },
    formatDate(value) {
      if (!value) return '—';
      const date = new Date(value);
      if (Number.isNaN(date.getTime())) return value;
      return date.toLocaleDateString(undefined, { year: 'numeric', month: 'short', day: 'numeric' });
    },
    formatPrice(value) {
      return new Intl.NumberFormat(undefined, {
        minimumFractionDigits: 2,
        maximumFractionDigits: 2
      }).format(Number(value || 0));
    }
  }
};
</script>

<style scoped src="./style.css"></style>

<style scoped>
.po-page {
  min-height: calc(100vh - 120px);
  background: #fff;
  color: #27364a;
  font-family: Inter, -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
}

.po-filter-row {
  grid-template-columns: minmax(120px, 1fr) minmax(130px, 1fr) minmax(140px, 1.2fr) minmax(120px, 1fr) minmax(120px, 0.9fr) auto;
}

.po-table thead th:first-child {
  padding-left: 10px;
}

.po-loading-label {
  margin-right: auto;
  color: #86939d;
  font-size: 10px;
}

.po-autocomplete-control {
  position: relative;
}

.po-link-suggestions {
  position: absolute;
  z-index: 30;
  top: calc(100% + 3px);
  right: 0;
  left: 0;
  max-height: 240px;
  margin: 0;
  padding: 4px 0;
  overflow-y: auto;
  border: 1px solid #cbd5da;
  border-radius: 3px;
  background: #fff;
  box-shadow: 0 4px 12px rgba(26, 47, 61, 0.16);
  list-style: none;
}

.po-link-suggestions li {
  display: flex;
  min-height: 34px;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  padding: 6px 10px;
  color: #263d50;
  cursor: pointer;
}

.po-link-suggestions li:hover {
  background: #eaf5f8;
}

.po-link-suggestions li strong {
  font-weight: 600;
}

.po-link-suggestions li small {
  color: #718391;
  text-align: right;
}

.po-link-suggestions li.po-link-suggestion-empty {
  color: #718391;
  cursor: default;
}

.po-list-shell {
  display: flex;
  flex-direction: column;
  min-height: calc(100vh - 120px);
}

.po-toolbar {
  display: flex;
  align-items: center;
  justify-content: flex-start;
  padding: 10px 18px 0;
  color: #597082;
  font-size: 12px;
}

.crumbs {
  padding: 7px 10px;
  border-radius: 4px;
  background: rgba(255, 255, 255, 0.5);
}

.po-page-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 14px 18px 10px;
}

.po-page-header h1 {
  margin: 0;
  color: #101a2a;
  font-size: 26px;
  font-weight: 700;
}

.po-header-actions {
  display: flex;
  align-items: center;
  gap: 10px;
}

.list-view-btn,
.add-po-btn,
.filter-save-btn,
.add-po-inline-btn,
.po-save-btn,
.po-close-btn,
.po-cancel-btn,
.po-back-link,
.po-add-row,
.po-remove-row,
.po-btn {
  font: inherit;
}

.list-view-btn {
  min-height: 32px;
  padding: 0 12px;
  border: 1px solid #d8dee3;
  border-radius: 4px;
  color: #3c4d5d;
  background: #fff;
}

.add-po-btn,
.po-save-btn {
  min-height: 32px;
  padding: 0 16px;
  border: 1px solid #1c2e3b;
  border-radius: 4px;
  color: #fff;
  background: #1f2e3d;
  font-weight: 600;
}

.po-list-layout {
  display: grid;
  grid-template-columns: 220px minmax(0, 1fr);
  gap: 0;
  flex: 1;
  min-height: 0;
  padding: 0 18px 18px;
}

.po-filter-panel {
  display: flex;
  flex-direction: column;
  gap: 12px;
  padding: 16px 18px 10px 0;
  border-right: 1px solid #e1e6eb;
  background: transparent;
}

.filter-title {
  color: #24364a;
  font-size: 13px;
  font-weight: 600;
}

.filter-group {
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.filter-group label {
  color: #546a7d;
  font-size: 12px;
}

.filter-group select,
.po-field-wrap input,
.po-field-wrap select {
  width: 100%;
  min-height: 32px;
  padding: 6px 8px;
  border: 1px solid #d6dde3;
  border-radius: 4px;
  background: #fff;
  color: #2b3d4d;
  font-size: 12px;
}

.filter-divider {
  margin: 8px 0;
  border-top: 1px solid #e5e8eb;
}

.compact {
  margin-top: 2px;
}

.small-link {
  width: fit-content;
  padding: 0;
  border: 0;
  background: transparent;
  color: #0d7ac7;
  font-size: 12px;
}

.filter-save-btn,
.filter-name-btn {
  min-height: 30px;
  margin-top: 6px;
  border: 1px solid #dce2e7;
  border-radius: 4px;
  background: #edf0f2;
  color: #3f5365;
}

.po-main-panel {
  display: flex;
  flex-direction: column;
  min-height: 0;
  padding-left: 16px;
  background: #fff;
  border: 1px solid #e5e8eb;
  border-left: 0;
}

.po-toolbar-row {
  display: grid;
  grid-template-columns: repeat(4, minmax(120px, 1fr)) 160px;
  gap: 12px;
  padding: 12px 12px 10px;
  border-bottom: 1px solid #e5e8eb;
  background: #f9fafb;
}

.po-field-wrap {
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.po-field-wrap label {
  color: #526b7e;
  font-size: 11px;
  font-weight: 600;
}

.right-field {
  justify-self: end;
  width: 150px;
}

.po-list-table {
  display: flex;
  flex: 1;
  min-height: 360px;
  align-items: stretch;
  justify-content: center;
  background: #fff;
}

.po-error {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  margin: 12px 12px 0;
  padding: 10px 12px;
  border: 1px solid #f0c3c3;
  border-radius: 4px;
  background: #fff3f3;
  color: #a53734;
  font-size: 12px;
}

.po-error button {
  padding: 0;
  border: 0;
  background: transparent;
  color: #0d7ac7;
  text-decoration: underline;
}

.po-table {
  width: 100%;
  border-collapse: collapse;
}

.po-table th {
  height: 36px;
  padding: 0 12px;
  border-bottom: 1px solid #e6edf1;
  background: #f7f9fb;
  color: #4f6983;
  font-size: 11px;
  font-weight: 700;
  text-align: left;
  letter-spacing: 0.04em;
}

.po-table td {
  height: 54px;
  padding: 0 12px;
  border-bottom: 1px solid #edf2f4;
  color: #21364a;
  font-size: 12px;
}

.po-table tbody tr:hover {
  background: #f3fafc;
}

.po-clickable-row {
  cursor: pointer;
}

.po-clickable-row:focus-visible {
  outline: 2px solid #0d7ac7;
  outline-offset: -2px;
}

.po-link {
  color: #0d7ac7;
  text-decoration: none;
}

.po-link:hover {
  text-decoration: underline;
}

.po-status {
  display: inline-block;
  padding: 4px 8px;
  border-radius: 999px;
  font-size: 10px;
  font-weight: 600;
}

.po-status-draft { background: #edf0f2; color: #4d5e6d; }
.po-status-submitted { background: #e8f2fd; color: #1263b4; }
.po-status-receive { background: #fff0db; color: #a35d09; }
.po-status-completed { background: #e4f8ed; color: #167b4d; }
.po-status-cancelled { background: #fbe8e8; color: #922d2d; }

.numeric-column {
  text-align: right !important;
  font-variant-numeric: tabular-nums;
}

.po-empty-state {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 8px;
  width: 100%;
  color: #526b7e;
  text-align: center;
}

.po-empty-icon {
  display: grid;
  width: 72px;
  height: 72px;
  place-items: center;
  border: 1px solid #dfe7eb;
  border-radius: 12px;
  background: #f7f9fa;
  font-size: 28px;
}

.po-empty-state p {
  margin: 0;
  font-size: 15px;
  color: #627382;
}

.add-po-inline-btn {
  min-height: 32px;
  padding: 0 12px;
  border: 1px solid #dfe4e8;
  border-radius: 4px;
  background: #fff;
  color: #2d4253;
}

.po-pagination {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 8px;
  padding: 14px 12px 18px;
  border-top: 1px solid #e5e8eb;
  background: #f9fafb;
}

.po-pagination button {
  min-width: 46px;
  min-height: 26px;
  border: 1px solid #d6dde3;
  border-radius: 4px;
  background: #fff;
  color: #495f75;
}

.po-create-shell {
  max-width: 1100px;
  margin: 0 auto;
  padding: 0 18px 30px;
}

.po-create-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 18px 0 12px;
}

.po-create-title-wrap {
  display: flex;
  align-items: center;
  gap: 10px;
}

.po-create-title-wrap h2 {
  margin: 0;
  color: #1d2d3d;
  font-size: 22px;
}

.po-back-link {
  padding: 0;
  border: 0;
  background: transparent;
  color: #0f7ec8;
  font-size: 12px;
}

.po-create-title-wrap span {
  color: #90a0ad;
}

.po-create-form {
  border: 1px solid #e1e6eb;
  background: #fff;
  box-shadow: 0 2px 7px rgba(16, 24, 40, 0.04);
}

.po-form-header {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 20px;
  padding: 18px 24px 16px;
  border-bottom: 1px solid #ebeff2;
}

.po-eyebrow {
  margin: 0 0 8px;
  color: #718391;
  letter-spacing: 0.08em;
  font-size: 10px;
  font-weight: 700;
}

.po-form-header h3 {
  margin: 0;
  color: #1d2d3d;
  font-size: 22px;
}

.po-subtitle {
  margin: 6px 0 0;
  color: #64798b;
  font-size: 12px;
}

.po-cancel-btn,
.po-close-btn {
  min-height: 34px;
  padding: 0 14px;
  border: 1px solid #d4dbe2;
  border-radius: 4px;
  color: #324a5f;
  background: #fff;
}

.po-form-sections {
  padding: 0;
}

.po-form-section {
  padding: 22px 24px 18px;
  border-bottom: 1px solid #edf1f3;
}

.po-form-section h4 {
  margin: 0 0 18px;
  color: #2b4052;
  font-size: 14px;
  font-weight: 700;
}

.po-form-grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 18px 22px;
}

.po-form-field {
  display: flex;
  flex-direction: column;
  gap: 7px;
  color: #364d63;
  font-size: 12px;
  font-weight: 500;
}

.po-form-field b {
  color: #d04b3d;
}

.po-form-field input,
.po-form-field select,
.po-form-field textarea {
  width: 100%;
  min-height: 36px;
  padding: 8px 10px;
  border: 1px solid #cfd7dc;
  border-radius: 4px;
  background: #fff;
  color: #1d2d3d;
  font-size: 12px;
}

.po-form-field textarea {
  min-height: 84px;
  resize: vertical;
}

.po-form-field-wide {
  grid-column: 1 / -1;
}

.po-check-field,
.po-child-check {
  display: flex;
  align-items: center;
  gap: 8px;
  min-height: 36px;
}

.po-check-field input,
.po-child-check input {
  width: 16px;
  height: 16px;
}

.po-link-control {
  display: flex;
  gap: 6px;
}

.po-link-control input {
  flex: 1;
}

.po-link-create {
  flex: 0 0 auto;
  padding: 0 8px;
  border: 1px solid #dfe5ea;
  border-radius: 4px;
  background: #fff;
  color: #0d7ac7;
}

.po-child-table {
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.po-child-row {
  display: grid;
  grid-template-columns: minmax(130px, 1.2fr) minmax(130px, 1.2fr) minmax(80px, 0.7fr) minmax(90px, 0.7fr) minmax(100px, 0.9fr) minmax(120px, 0.9fr) auto;
  gap: 10px;
  align-items: end;
  padding: 12px;
  border: 1px solid #e0e7eb;
  border-radius: 6px;
  background: #fafcfd;
}

.po-line-total {
  justify-content: flex-end;
}

.po-line-total strong {
  display: inline-block;
  min-height: 36px;
  padding: 8px 10px;
  border: 1px solid #dfe6eb;
  border-radius: 4px;
  background: #fff;
}

.po-remove-row {
  min-height: 36px;
  padding: 0 8px;
  border: 0;
  background: transparent;
  color: #a3362e;
}

.po-add-row {
  align-self: flex-start;
  padding: 0;
  border: 0;
  background: transparent;
  color: #0f7ec8;
}

.po-form-footer {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 16px;
  padding: 16px 24px;
  border-top: 1px solid #edf1f3;
  background: #fafbfc;
}

.po-total-box {
  display: flex;
  align-items: baseline;
  gap: 12px;
  color: #425a70;
  font-size: 14px;
}

.po-total-box strong {
  font-size: 20px;
  color: #1d2d3d;
}

.po-footer-actions {
  display: flex;
  gap: 8px;
}

.po-save-btn {
  border-color: #168c38;
  background: #168c38;
}

@media (max-width: 1000px) {
  .po-list-layout {
    grid-template-columns: 1fr;
  }

  .po-filter-panel {
    border-right: 0;
    border-bottom: 1px solid #e1e6eb;
    padding-right: 0;
  }

  .po-main-panel {
    border-left: 1px solid #e5e8eb;
    padding-left: 0;
  }

  .po-toolbar-row {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }

  .po-form-grid,
  .po-child-row {
    grid-template-columns: minmax(0, 1fr);
  }
}
</style>
