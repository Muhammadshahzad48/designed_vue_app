<template>
  <main class="item-page">
    <div class="item-page-heading">
      <div class="item-page-title">
        <button v-if="showCreateForm" class="back-to-items" type="button" @click="showCreateForm = false">
          Items
        </button>
        <span v-if="showCreateForm" class="title-divider">/</span>
        <h1>{{ showCreateForm ? 'New Item' : 'Item' }}</h1>
      </div>
      <div v-if="!showCreateForm" class="item-page-actions">
        <button class="new-item-button" type="button" @click="createNewItem">
          ＋ New Item
        </button>
      </div>
    </div>

    <section v-if="showCreateForm" class="item-create">
      <form class="item-create-form" @submit.prevent="saveProduct">
        <header class="item-form-heading">
          <div>
            <p class="item-form-eyebrow">ITEM DETAILS</p>
            <h2>Create a new item</h2>
            <p class="item-form-intro">Add the item details below. It will be saved to ERPNext.</p>
          </div>
          <button class="form-cancel-button" type="button" :disabled="savingItem" @click="showCreateForm = false">
            Cancel
          </button>
        </header>

        <p v-if="errorMessage" class="form-options-error" role="alert">
          {{ errorMessage }}
          <button type="button" @click="fetchProducts">Try again</button>
        </p>
        <p v-else-if="loading && (!itemGroups.length || !uoms.length)" class="form-options-hint">
          Loading item groups and units…
        </p>

        <p v-if="formOptionsError" class="form-options-error" role="alert">{{ formOptionsError }}</p>
        <section v-if="formTabs.length" class="required-fields-panel">
          <nav class="item-form-tabs" aria-label="Item field tabs">
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
          <div
            v-for="section in requiredSections.filter((entry) => entry.tab === activeFormTab)"
            :key="`${section.tab}-${section.section}`"
            class="item-form-section required-field-section"
          >
            <h3>{{ section.section }}</h3>
            <div class="item-form-grid">
              <div
                v-for="field in section.fields"
                :key="field.fieldname"
                class="item-form-field"
                :class="{ 'item-form-field-wide': field.fieldtype === 'Table' }"
              >
                <label v-if="field.fieldtype === 'Check'" class="item-form-checkbox">
                  <input
                    v-model="newItem[field.fieldname]"
                    type="checkbox"
                    :true-value="true"
                    :false-value="false"
                    :disabled="field.read_only"
                  />
                  <span>
                    {{ field.label }}
                    <b v-if="isRequiredFormField(field)">*</b>
                    <small v-else-if="field.mandatory_depends_on">(required when applicable)</small>
                  </span>
                </label>
                <template v-else>
                <span>
                  {{ field.label }}
                  <b v-if="isRequiredFormField(field)">*</b>
                  <small v-else-if="field.mandatory_depends_on">(required when applicable)</small>
                </span>
                <div v-if="field.fieldtype === 'Table'" class="required-child-table">
                  <p v-if="!newItem[field.fieldname]?.length" class="empty-child-table">
                    No rows added.
                  </p>
                  <div
                    v-for="(row, rowIndex) in newItem[field.fieldname]"
                    :key="rowIndex"
                    class="required-child-row"
                  >
                    <template v-for="child in field.children" :key="child.fieldname">
                    <label v-if="child.fieldtype === 'Check'" class="item-form-checkbox">
                      <input
                        v-model="row[child.fieldname]"
                        type="checkbox"
                        :true-value="true"
                        :false-value="false"
                        :disabled="child.read_only"
                      />
                      <span>
                        {{ child.label }}
                        <b v-if="child.required">*</b>
                      </span>
                    </label>
                    <label
                      v-else
                      class="item-form-field"
                    >
                      <span>
                        {{ child.label }}
                        <b v-if="child.required">*</b>
                      </span>
                      <select
                        v-if="child.fieldtype === 'Select'"
                        v-model="row[child.fieldname]"
                        :required="child.required && !child.read_only"
                        :disabled="child.read_only"
                      >
                        <option value="">Select {{ child.label }}</option>
                        <option v-for="option in child.options" :key="option" :value="option">{{ option }}</option>
                      </select>
                      <template v-else-if="child.fieldtype === 'Link'">
                        <div class="form-link-control">
                          <input
                            v-model="row[child.fieldname]"
                            :list="linkOptionListId(child, field.table_doctype)"
                            :required="child.required && !child.read_only"
                            :disabled="child.read_only"
                            autocomplete="off"
                            @focus="loadFormLinkOptions(child, field.table_doctype, row[child.fieldname])"
                            @input="scheduleFormLinkOptions(child, field.table_doctype, row[child.fieldname])"
                          />
                          <button
                            v-if="canCreateLinkedDocument(child)"
                            class="form-link-create"
                            type="button"
                            :disabled="savingItem"
                            @click="createLinkedDocument(child, (name) => { row[child.fieldname] = name; }, field.table_doctype)"
                          >
                            + Add
                          </button>
                        </div>
                        <datalist :id="linkOptionListId(child, field.table_doctype)">
                          <option
                            v-for="option in getFormLinkOptions(child, field.table_doctype)"
                            :key="option"
                            :value="option"
                          />
                        </datalist>
                      </template>
                      <textarea
                        v-else-if="isLongTextField(child.fieldtype)"
                        v-model="row[child.fieldname]"
                        rows="3"
                        :required="child.required && !child.read_only"
                        :disabled="child.read_only"
                      ></textarea>
                      <input
                        v-else
                        v-model="row[child.fieldname]"
                        :type="formInputType(child.fieldtype)"
                        :required="child.required && !child.read_only"
                        :disabled="child.read_only"
                      />
                    </label>
                    </template>
                    <button
                      class="remove-child-row"
                      type="button"
                      :disabled="savingItem"
                      :aria-label="`Remove ${field.label} row ${rowIndex + 1}`"
                      @click="removeRequiredTableRow(field, rowIndex)"
                    >
                      Remove
                    </button>
                  </div>
                  <button
                    class="add-child-row"
                    type="button"
                    :disabled="savingItem"
                    @click="addRequiredTableRow(field)"
                  >
                    + Add {{ field.label }}
                  </button>
                </div>
                <select
                  v-else-if="field.fieldtype === 'Select'"
                  v-model="newItem[field.fieldname]"
                  :required="isRequiredFormField(field) && !field.read_only"
                  :disabled="field.read_only"
                >
                  <option value="">Select {{ field.label }}</option>
                  <option v-for="option in field.options" :key="option" :value="option">{{ option }}</option>
                </select>
                <template v-else-if="field.fieldtype === 'Link'">
                  <div class="form-link-control">
                    <input
                      v-model="newItem[field.fieldname]"
                      :list="linkOptionListId(field)"
                      :required="isRequiredFormField(field) && !field.read_only"
                      :disabled="field.read_only"
                      autocomplete="off"
                      @focus="loadFormLinkOptions(field, '', newItem[field.fieldname])"
                      @input="scheduleFormLinkOptions(field, '', newItem[field.fieldname])"
                    />
                    <button
                      v-if="canCreateLinkedDocument(field)"
                      class="form-link-create"
                      type="button"
                      :disabled="savingItem"
                      @click="createLinkedDocument(field, (name) => { newItem[field.fieldname] = name; })"
                    >
                      + Add {{ field.link_doctype }}
                    </button>
                  </div>
                  <datalist :id="linkOptionListId(field)">
                    <option
                      v-for="option in getFormLinkOptions(field)"
                      :key="option"
                      :value="option"
                    />
                  </datalist>
                </template>
                <textarea
                  v-else-if="isLongTextField(field.fieldtype)"
                  v-model="newItem[field.fieldname]"
                  rows="3"
                  :required="isRequiredFormField(field) && !field.read_only"
                  :disabled="field.read_only"
                ></textarea>
                <input
                  v-else
                  v-model="newItem[field.fieldname]"
                  :type="formInputType(field.fieldtype)"
                  :required="isRequiredFormField(field) && !field.read_only"
                  :disabled="field.read_only"
                />
                </template>
              </div>
            </div>
          </div>
        </section>

        <p v-if="createError" class="create-error" role="alert">{{ createError }}</p>
        <footer class="item-form-actions">
          <button class="form-cancel-button" type="button" :disabled="savingItem" @click="showCreateForm = false">
            Cancel
          </button>
          <button
            class="save-item-button"
            type="submit"
            :disabled="savingItem || loading || !itemGroups.length || !uoms.length"
          >
            {{ savingItem ? 'Saving…' : 'Save Item' }}
          </button>
        </footer>
      </form>
    </section>

    <template v-else>
    <form class="item-filters" @submit.prevent="fetchProducts">
      <div class="filter-row filter-row-primary">
        <div
          v-for="field in itemLinkFields"
          :key="field.name"
          class="item-link-field"
        >
          <input
            v-model.trim="filters[field.name]"
            :placeholder="field.label"
            :aria-label="field.label"
            aria-autocomplete="list"
            :aria-expanded="activeSuggestionField === field.name"
            @focus="openItemSuggestions(field.name)"
            @blur="scheduleCloseItemSuggestions(field.name)"
            @change="fetchProducts"
            @input="scheduleItemSuggestions(field.name)"
            @keydown.down.prevent="moveSuggestion(field.name, 1)"
            @keydown.up.prevent="moveSuggestion(field.name, -1)"
            @keydown.enter.prevent="selectItemSuggestion(field.name)"
            @keydown.esc="closeItemSuggestions"
          />
          <ul
            v-if="activeSuggestionField === field.name"
            class="item-link-suggestions"
            role="listbox"
          >
            <li v-if="suggestionError" class="item-link-suggestion-message" role="alert">
              {{ suggestionError }}
            </li>
            <li v-else-if="!itemSuggestions[field.name].length" class="item-link-suggestion-message">
              No matching items
            </li>
            <li
              v-for="(option, index) in itemSuggestions[field.name]"
              :key="option.item_code"
              role="option"
              :aria-selected="suggestionIndex === index"
              :class="{ 'item-link-suggestion-active': suggestionIndex === index }"
              @pointerdown.prevent="chooseItemSuggestion(field.name, option)"
            >
              <strong>{{ field.name === 'item_code' ? option.item_code : option.item_name }}</strong>
              <small>{{ field.name === 'item_code' ? option.item_name : option.item_code }}</small>
            </li>
          </ul>
        </div>
        <select v-model="filters.item_group" aria-label="Item category" @change="fetchProducts">
          <option value="">All Category</option>
          <option v-for="group in itemGroups" :key="group" :value="group">{{ group }}</option>
        </select>
        <select v-model="filters.status" aria-label="Item status" @change="fetchProducts">
          <option value="Enabled">Active</option>
          <option value="Disabled">Disabled</option>
          <option value="All">All Status</option>
        </select>
        <div class="filter-buttons">
          <button class="show-button" type="submit" :disabled="loading">Show</button>
          <button class="clear-button" type="button" :disabled="loading" @click="resetFilters">Clear</button>
        </div>
      </div>
    </form>

    <div class="table-tools">
      <div v-if="errorMessage" class="error-message" role="alert">
        <span>{{ errorMessage }}</span>
        <button type="button" @click="fetchProducts">Try again</button>
      </div>
      <button class="export-button" type="button" aria-label="Export items" @click="exportItems">♧</button>
      <button class="export-menu-button" type="button" aria-label="More export options">⌄</button>
    </div>

    <div class="items-table-scroll">
      <table class="items-table">
        <thead>
          <tr>
            <th>PRODUCT NAME</th>
            <th>ID</th>
            <th>CATEGORY</th>
            <th class="numeric-column">UNIT PRICE</th>
            <th>STATUS</th>
          </tr>
        </thead>
        <tbody>
          <tr
            v-for="item in products"
            :key="item.item_code"
            class="item-row"
            tabindex="0"
            :aria-label="`Open item ${item.item_name}`"
            @click="openItem(item.item_code)"
            @keydown.enter.prevent="openItem(item.item_code)"
            @keydown.space.prevent="openItem(item.item_code)"
          >
            <td class="product-column">
              <img v-if="item.image" class="product-image" :src="item.image" :alt="item.item_name" />
              <span v-else class="product-placeholder" aria-hidden="true">{{ initials(item.item_name) }}</span>
              <span class="product-description">
                <a
                  class="product-code"
                  :href="itemRoute(item.item_code)"
                  @click.prevent.stop="openItem(item.item_code)"
                >
                  {{ item.item_name }}
                </a>
              </span>
            </td>
            <td>{{ item.item_code }}</td>
            <td>{{ item.category || '—' }}</td>
            <td class="numeric-column">{{ formatPrice(item.unit_price) }}</td>
            <td>
              <span class="item-status" :class="{ 'item-status-disabled': item.disabled }">
                {{ item.disabled ? 'Disabled' : 'Enabled' }}
              </span>
            </td>
          </tr>
          <tr v-if="loading">
            <td colspan="5" class="table-message">Loading items…</td>
          </tr>
          <tr v-else-if="!errorMessage && products.length === 0">
            <td colspan="5" class="table-message">No items found.</td>
          </tr>
        </tbody>
      </table>
    </div>
    <footer class="table-footer">
      <span>{{ loading ? 'Loading…' : `${products.length} items` }}</span>
      <span>ERPNext Item List</span>
    </footer>
    </template>
  </main>
</template>

<script>
import axios from 'axios';

const emptyFilters = () => ({
  status: 'Enabled',
  item_group: '',
  item_code: '',
  item_name: ''
});

const emptyItem = () => ({
  item_code: '',
  item_name: '',
  item_group: '',
  stock_uom: '',
  is_stock_item: true,
  standard_rate: 0,
  description: '',
  default_manufacturer_part_no: ''
});

const itemLinkFields = [
  { name: 'item_code', label: 'Item ID' },
  { name: 'item_name', label: 'Product Name' }
];

export default {
  data() {
    return {
      products: [],
      itemGroups: [],
      uoms: [],
      requiredSections: [],
      formTabs: [],
      activeFormTab: '',
      formLinkOptions: {},
      formLinkTimers: {},
      formLinkRequestIds: {},
      formOptionsError: '',
      itemLinkFields,
      itemSuggestions: { item_code: [], item_name: [] },
      activeSuggestionField: '',
      suggestionIndex: -1,
      suggestionError: '',
      suggestionTimer: null,
      suggestionCloseTimer: null,
      suggestionRequestId: 0,
      filters: emptyFilters(),
      loading: false,
      errorMessage: '',
      showCreateForm: false,
      savingItem: false,
      createError: '',
      newItem: emptyItem()
    };
  },
  mounted() {
    this.fetchProducts();
  },
  methods: {
    async fetchProducts() {
      this.closeItemSuggestions();
      this.loading = true;
      this.errorMessage = '';
      try {
        const response = await axios.get('/api/method/designed_vue_app.designed_vue_app.api.get_products', {
          params: { filters: JSON.stringify(this.filters) }
        });
        const result = response.data?.message;
        if (!result || !Array.isArray(result.items)) {
          throw new Error('Unexpected response from the Item API.');
        }
        this.products = result.items;
        this.itemGroups = result.item_groups || [];
        this.uoms = result.uoms || [];
      } catch (error) {
        console.error('Unable to load ERPNext items:', error);
        this.products = [];
        this.errorMessage = error.response?.status === 403
          ? 'You do not have permission to view these items.'
          : 'Unable to load items. Check the server/API and try again.';
      } finally {
        this.loading = false;
      }
    },
    resetFilters() {
      this.closeItemSuggestions();
      this.filters = emptyFilters();
      this.fetchProducts();
    },
    openItemSuggestions(field) {
      window.clearTimeout(this.suggestionCloseTimer);
      this.loadItemSuggestions(field);
    },
    scheduleCloseItemSuggestions(field) {
      this.suggestionCloseTimer = window.setTimeout(() => {
        if (this.activeSuggestionField === field) this.closeItemSuggestions();
      }, 150);
    },
    scheduleItemSuggestions(field) {
      this.activeSuggestionField = field;
      this.suggestionIndex = -1;
      this.suggestionError = '';
      window.clearTimeout(this.suggestionTimer);
      this.suggestionTimer = window.setTimeout(() => this.loadItemSuggestions(field), 180);
    },
    async loadItemSuggestions(field) {
      this.activeSuggestionField = field;
      this.suggestionError = '';
      const requestId = ++this.suggestionRequestId;
      try {
        const options = await window.frappe.xcall(
          'designed_vue_app.designed_vue_app.api.get_item_suggestions',
          { search_by: field, txt: this.filters[field] || '' }
        );
        if (requestId === this.suggestionRequestId && this.activeSuggestionField === field) {
          this.itemSuggestions[field] = Array.isArray(options) ? options : [];
          this.suggestionIndex = -1;
        }
      } catch (error) {
        console.error(`Unable to load ${field} suggestions:`, error);
        if (requestId === this.suggestionRequestId && this.activeSuggestionField === field) {
          this.itemSuggestions[field] = [];
          this.suggestionError = typeof error === 'string'
            ? error
            : 'Unable to load item suggestions.';
        }
      }
    },
    moveSuggestion(field, direction) {
      if (this.activeSuggestionField !== field) {
        this.loadItemSuggestions(field);
        return;
      }
      const count = this.itemSuggestions[field].length;
      if (count) this.suggestionIndex = (this.suggestionIndex + direction + count) % count;
    },
    selectItemSuggestion(field) {
      const option = this.itemSuggestions[field][this.suggestionIndex];
      if (option) this.chooseItemSuggestion(field, option);
    },
    chooseItemSuggestion(field, option) {
      this.filters[field] = field === 'item_code' ? option.item_code : option.item_name;
      this.closeItemSuggestions();
      this.fetchProducts();
    },
    closeItemSuggestions() {
      window.clearTimeout(this.suggestionTimer);
      window.clearTimeout(this.suggestionCloseTimer);
      this.activeSuggestionField = '';
      this.suggestionIndex = -1;
      this.suggestionError = '';
      this.suggestionRequestId += 1;
    },
    createNewItem() {
      this.newItem = emptyItem();
      this.newItem.stock_uom = this.uoms.includes('Nos') ? 'Nos' : (this.uoms[0] || '');
      this.createError = '';
      this.formOptionsError = '';
      this.formLinkOptions = {};
      this.requiredSections = [];
      this.activeFormTab = '';
      this.showCreateForm = true;
      window.frappe.xcall('designed_vue_app.designed_vue_app.api.get_item_form_fields')
        .then((sections) => {
          this.requiredSections = Array.isArray(sections) ? sections : [];
          this.requiredSections.forEach((section) => {
            section.fields.forEach((field) => {
              if (field.fieldtype === 'Table') {
                this.newItem[field.fieldname] = [];
              } else if (this.newItem[field.fieldname] === undefined || this.newItem[field.fieldname] === '') {
                this.newItem[field.fieldname] = this.formFieldDefault(field);
              }
            });
          });
          this.formTabs = [...new Set(this.requiredSections.map((section) => section.tab))];
          this.activeFormTab = this.formTabs[0] || '';
        })
        .catch((error) => {
          console.error('Unable to load Item fields:', error);
          this.createError = typeof error === 'string'
            ? error
            : 'Unable to load Item fields. Please close and reopen this form.';
        });
    },
    formFieldDefault(field) {
      if (field.default !== undefined && field.default !== null && field.default !== '') {
        if (field.fieldtype === 'Check') {
          return field.default === true || field.default === 1 || field.default === '1';
        }
        return field.default;
      }
      return field.fieldtype === 'Check' ? false : '';
    },
    linkOptionKey(field, childDoctype = '') {
      return `${childDoctype || 'Item'}:${field.fieldname}`;
    },
    linkOptionListId(field, childDoctype = '') {
      return `item-link-options-${this.linkOptionKey(field, childDoctype).replace(/[^a-zA-Z0-9_-]/g, '-')}`;
    },
    getFormLinkOptions(field, childDoctype = '') {
      return this.formLinkOptions[this.linkOptionKey(field, childDoctype)] || [];
    },
    scheduleFormLinkOptions(field, childDoctype = '', txt = '') {
      const key = this.linkOptionKey(field, childDoctype);
      window.clearTimeout(this.formLinkTimers[key]);
      this.formLinkTimers[key] = window.setTimeout(
        () => this.loadFormLinkOptions(field, childDoctype, txt),
        180
      );
    },
    async loadFormLinkOptions(field, childDoctype = '', txt = '') {
      const key = this.linkOptionKey(field, childDoctype);
      const requestId = (this.formLinkRequestIds[key] || 0) + 1;
      this.formLinkRequestIds[key] = requestId;
      try {
        const options = await window.frappe.xcall(
          'designed_vue_app.designed_vue_app.api.get_item_link_options',
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
            : `Unable to load options for ${field.label}.`;
        }
      }
    },
    canCreateLinkedDocument(field) {
      const doctype = field.link_doctype;
      return Boolean(
        doctype
        && typeof window.frappe?.model?.can_create === 'function'
        && window.frappe.model.can_create(doctype)
        && typeof window.frappe?.ui?.form?.make_quick_entry === 'function'
      );
    },
    createLinkedDocument(field, onCreated, childDoctype = '') {
      if (!this.canCreateLinkedDocument(field)) return;
      window.frappe.ui.form.make_quick_entry(
        field.link_doctype,
        (doc) => {
          onCreated(doc.name);
          this.loadFormLinkOptions(field, childDoctype, doc.name);
        },
        null,
        null,
        true
      );
    },
    async saveProduct() {
      if (this.savingItem) return;

      const missingTable = this.requiredSections
        .flatMap((section) => section.fields)
        .find((field) => field.fieldtype === 'Table'
          && this.isRequiredFormField(field)
          && !this.newItem[field.fieldname]?.length);
      if (missingTable) {
        this.createError = `${missingTable.label} is required. Add at least one row.`;
        this.activeFormTab = this.requiredSections.find((section) => section.fields.includes(missingTable))?.tab || '';
        return;
      }

      this.savingItem = true;
      this.createError = '';
      try {
        if (typeof window.frappe?.xcall !== 'function') {
          throw new Error('Frappe is not ready. Reload the page and try again.');
        }

        const result = await window.frappe.xcall(
          'designed_vue_app.designed_vue_app.api.create_product',
          { item: JSON.stringify(this.newItem) }
        );
        if (!result?.item_code) {
          throw new Error('The server did not confirm that the item was saved.');
        }

        this.showCreateForm = false;
        this.filters = emptyFilters();
        await this.fetchProducts();
      } catch (error) {
        console.error('Unable to create ERPNext item:', error);
        this.createError = (typeof error === 'string' ? error : null)
          || error.response?.data?.message
          || error.response?.data?.exc_type
          || error.message
          || 'Unable to save item. Please try again.';
      } finally {
        this.savingItem = false;
      }
    },
    isRequiredFormField(field) {
      if (field.required) return true;
      const condition = String(field.mandatory_depends_on || '');
      if (!condition) return false;
      if (condition.includes('is_fixed_asset')) return Boolean(this.newItem.is_fixed_asset);
      if (condition.includes('has_batch_no') && condition.includes('has_expiry_date')) {
        return Boolean(this.newItem.has_batch_no && this.newItem.has_expiry_date);
      }
      if (condition.includes('has_variants') || condition.includes('variant_of')) {
        return Boolean(this.newItem.has_variants || this.newItem.variant_of);
      }
      return false;
    },
    formInputType(fieldtype) {
      if (['Int', 'Float', 'Currency', 'Percent', 'Rating', 'Duration'].includes(fieldtype)) return 'number';
      if (fieldtype === 'Date') return 'date';
      if (fieldtype === 'Datetime') return 'datetime-local';
      if (fieldtype === 'Time') return 'time';
      return 'text';
    },
    isLongTextField(fieldtype) {
      return ['Text', 'Text Editor', 'Small Text', 'Long Text', 'Code', 'JSON'].includes(fieldtype);
    },
    addRequiredTableRow(field) {
      const row = {};
      field.children.forEach((child) => {
        row[child.fieldname] = this.formFieldDefault(child);
      });
      this.newItem[field.fieldname].push(row);
    },
    removeRequiredTableRow(field, rowIndex) {
      this.newItem[field.fieldname].splice(rowIndex, 1);
    },
    openItem(itemCode) {
      window.frappe?.set_route('Form', 'Item', itemCode);
    },
    itemRoute(itemCode) {
      const query = new URLSearchParams({ doctype: 'Item', name: itemCode });
      return `/app/designed-doctype-list?${query.toString()}`;
    },
    initials(name) {
      return String(name || 'Item')
        .split(/\s+/)
        .slice(0, 2)
        .map((part) => part.charAt(0))
        .join('')
        .toUpperCase();
    },
    formatNumber(value) {
      return new Intl.NumberFormat().format(Number(value) || 0);
    },
    formatPrice(value) {
      return new Intl.NumberFormat(undefined, {
        minimumFractionDigits: 2,
        maximumFractionDigits: 2
      }).format(Number(value) || 0);
    },
    exportItems() {
      const columns = ['item_code', 'item_name', 'category', 'manufacturer_part_no', 'manufacturer', 'available', 'reserved', 'uom', 'unit_price'];
      const rows = this.products.map((item) =>
        columns.map((column) => `"${String(item[column] ?? '').replaceAll('"', '""')}"`).join(',')
      );
      const csv = [columns.join(','), ...rows].join('\n');
      const link = document.createElement('a');
      link.href = URL.createObjectURL(new Blob([csv], { type: 'text/csv;charset=utf-8' }));
      link.download = 'items.csv';
      link.click();
      URL.revokeObjectURL(link.href);
    }
  }
};
</script>

<style scoped src="./style.css"></style>
