<template>
  <main class="settings-record-page">
    <header class="settings-record-heading">
      <div class="settings-record-title">
        <button class="settings-back-link" type="button" @click="goToCatalog">System Settings</button>
        <span class="settings-title-divider">/</span>
        <h1>{{ metadata?.label || setting?.label || 'Settings' }}</h1>
      </div>
      <div v-if="!showForm" class="settings-record-actions">
        <button v-if="metadata?.can_create" class="settings-new-button" type="button" @click="startNew">＋ New {{ metadata?.label || setting?.label }}</button>
      </div>
    </header>

    <template v-if="!showForm">
      <form class="settings-search" @submit.prevent="searchRecords">
        <label class="settings-page-size">
          <span>Show</span>
          <select v-model.number="pageLength" :disabled="loading" @change="changePageSize">
            <option :value="10">10</option>
            <option :value="25">25</option>
            <option :value="50">50</option>
            <option :value="100">100</option>
          </select>
        </label>
        <div class="settings-search-controls">
          <label for="settings-search-input">Search</label>
          <input id="settings-search-input" v-model.trim="search" placeholder="Search records" />
          <button type="submit" :disabled="loading">Search</button>
          <button type="button" class="settings-clear-button" :disabled="loading" @click="clearSearch">Clear</button>
        </div>
      </form>
      <p v-if="error" class="settings-error" role="alert">{{ error }}</p>
      <div class="settings-record-table-wrap">
        <table class="settings-record-table">
          <thead>
            <tr>
              <th v-for="column in columns" :key="column.fieldname">{{ column.label }}</th>
            </tr>
          </thead>
          <tbody>
            <tr
              v-for="row in rows"
              :key="row.name"
              class="settings-data-row"
              tabindex="0"
              @click="openRecord(row.name)"
              @keydown.enter="openRecord(row.name)"
            >
              <td v-for="column in columns" :key="column.fieldname">
                <a href="#" @click.prevent.stop="openRecord(row.name)">{{ formatValue(row[column.fieldname]) }}</a>
              </td>
            </tr>
            <tr v-if="loading"><td :colspan="Math.max(columns.length, 1)" class="settings-empty-row">Loading…</td></tr>
            <tr v-else-if="!error && !rows.length"><td :colspan="Math.max(columns.length, 1)" class="settings-empty-row">No records found.</td></tr>
          </tbody>
        </table>
      </div>
      <footer class="settings-record-footer">
        <span>Page {{ pageNumber }} · {{ rows.length }} records</span>
        <span>{{ metadata?.label || setting?.label }}</span>
        <div class="settings-pagination" aria-label="List pagination">
          <button type="button" :disabled="loading || pageNumber <= 1" @click="changePage(-1)">‹</button>
          <span>{{ pageNumber }}</span>
          <button type="button" :disabled="loading || !hasMore" @click="changePage(1)">›</button>
        </div>
      </footer>
    </template>

    <section v-else class="settings-form-card">
      <form @submit.prevent="saveRecord">
        <header class="settings-form-header">
          <div>
            <p>CONFIGURATION</p>
            <h2>{{ editingName || `New ${metadata?.label || setting?.label}` }}</h2>
          </div>
          <button type="button" class="settings-clear-button" :disabled="saving" @click="closeForm">Cancel</button>
        </header>

        <p v-if="error" class="settings-error settings-form-error" role="alert">{{ error }}</p>
        <div v-if="tabs.length > 1" class="settings-tabs" role="tablist">
          <button
            v-for="tab in tabs"
            :key="tab"
            type="button"
            role="tab"
            :aria-selected="activeTab === tab"
            :class="{ 'settings-tab-active': activeTab === tab }"
            @click="activeTab = tab"
          >{{ tab }}</button>
        </div>

        <details
          v-for="section in sections.filter((item) => item.tab === activeTab)"
          :key="`${section.tab}-${section.section}`"
          class="settings-form-section"
          open
        >
          <summary>
            <h3>{{ section.section }}</h3>
            <span aria-hidden="true">⌄</span>
          </summary>
          <div class="settings-form-grid">
            <template v-for="field in section.fields" :key="field.fieldname">
              <label v-if="field.fieldtype === 'Check'" class="settings-check-field">
                <input v-model="form[field.fieldname]" type="checkbox" :disabled="field.read_only || recordReadOnly" />
                <span>{{ field.label }}<b v-if="field.required">*</b></span>
              </label>
              <div v-else-if="['Table', 'Table MultiSelect'].includes(field.fieldtype)" class="settings-table-field">
                <div class="settings-table-field-heading">
                  <strong>{{ field.label }}<b v-if="field.required">*</b></strong>
                  <button type="button" :disabled="recordReadOnly" @click="addChildRow(field)">＋ Add Row</button>
                </div>
                <p v-if="!form[field.fieldname]?.length" class="settings-muted">No rows added.</p>
                <div v-for="(row, rowIndex) in form[field.fieldname]" :key="rowIndex" class="settings-child-row">
                  <label v-for="child in field.children" :key="child.fieldname" class="settings-field">
                    <span>{{ child.label }}<b v-if="child.required">*</b></span>
                    <input
                      v-if="child.fieldtype === 'Check'"
                      v-model="row[child.fieldname]"
                      type="checkbox"
                      :disabled="child.read_only || recordReadOnly"
                    />
                    <select
                      v-else-if="child.fieldtype === 'Select'"
                      v-model="row[child.fieldname]"
                      :disabled="child.read_only || recordReadOnly"
                    >
                      <option value="">Select {{ child.label }}</option>
                      <option v-for="option in child.options" :key="option" :value="option">{{ option }}</option>
                    </select>
                    <input
                      v-else-if="child.fieldtype === 'Link'"
                      v-model="row[child.fieldname]"
                      :list="linkListId(child, field.table_doctype)"
                      :required="child.required"
                      :disabled="child.read_only || recordReadOnly"
                      autocomplete="off"
                      @focus="loadLinkOptions(child, field.table_doctype, row[child.fieldname])"
                      @input="scheduleLinkOptions(child, field.table_doctype, row[child.fieldname])"
                    />
                    <datalist v-if="child.fieldtype === 'Link'" :id="linkListId(child, field.table_doctype)">
                      <option
                        v-for="option in linkOptions[linkOptionsKey(child, field.table_doctype)] || []"
                        :key="option"
                        :value="option"
                      />
                    </datalist>
                    <textarea
                      v-else-if="isLongText(child.fieldtype)"
                      v-model="row[child.fieldname]"
                      rows="2"
                      :required="child.required"
                      :disabled="child.read_only || recordReadOnly"
                    ></textarea>
                    <input
                      v-else
                      v-model="row[child.fieldname]"
                      :type="inputType(child.fieldtype)"
                      :required="child.required"
                      :disabled="child.read_only || recordReadOnly"
                    />
                  </label>
                  <button type="button" class="settings-remove-row" :disabled="recordReadOnly" @click="removeChildRow(field, rowIndex)">Remove</button>
                </div>
              </div>
              <label v-else class="settings-field" :class="{ 'settings-field-wide': isWideField(field) }">
                <span>{{ field.label }}<b v-if="field.required">*</b></span>
                <select v-if="field.fieldtype === 'Select'" v-model="form[field.fieldname]" :required="field.required" :disabled="field.read_only || recordReadOnly">
                  <option value="">Select {{ field.label }}</option>
                  <option v-for="option in field.options" :key="option" :value="option">{{ option }}</option>
                </select>
                <div v-else-if="field.fieldtype === 'Link'" class="settings-link-control">
                  <input
                    v-model="form[field.fieldname]"
                    :list="linkListId(field)"
                    :required="field.required"
                    :disabled="field.read_only || recordReadOnly"
                    autocomplete="off"
                    @focus="loadLinkOptions(field)"
                    @input="scheduleLinkOptions(field)"
                  />
                  <datalist :id="linkListId(field)">
                    <option v-for="option in linkOptions[linkOptionsKey(field)] || []" :key="option" :value="option" />
                  </datalist>
                </div>
                <textarea v-else-if="isLongText(field.fieldtype)" v-model="form[field.fieldname]" rows="3" :required="field.required" :disabled="field.read_only || recordReadOnly"></textarea>
                <input
                  v-else
                  v-model="form[field.fieldname]"
                  :type="inputType(field.fieldtype)"
                  :required="field.required"
                  :disabled="field.read_only || recordReadOnly"
                />
              </label>
            </template>
          </div>
        </details>
        <p v-if="recordReadOnly" class="settings-readonly-note">
          {{ Number(form.docstatus || 0) > 0 ? 'This submitted record cannot be edited.' : 'You have read-only access to this record.' }}
        </p>
        <footer class="settings-form-actions">
          <button type="button" class="settings-clear-button" :disabled="saving" @click="closeForm">Cancel</button>
          <button v-if="!recordReadOnly && (editingName ? metadata?.can_write : metadata?.can_create)" type="submit" class="settings-save-button" :disabled="saving">
            {{ saving ? 'Saving…' : 'Save' }}
          </button>
        </footer>
      </form>
    </section>
  </main>
</template>

<script>
import axios from 'axios';

const settingsMap = {
  organization: { label: 'Organization', doctype: 'Company' },
  department: { label: 'Department', doctype: 'Department' },
  designation: { label: 'Designation', doctype: 'Designation' },
  role: { label: 'Roles', doctype: 'Role' },
  user: { label: 'User', doctype: 'User' },
  warehouse: { label: 'Warehouse', doctype: 'Warehouse' },
  'payment-terms': { label: 'Payment Terms', doctype: 'Payment Terms Template' },
  'currency-rate': { label: 'Currency Rate', doctype: 'Currency Exchange' },
  'cost-center': { label: 'Cost Center', doctype: 'Cost Center' },
  bank: { label: 'Bank', doctype: 'Bank' },
  'bank-account': { label: 'Bank Account', doctype: 'Bank Account' },
  'terms-and-conditions': { label: 'Terms & Conditions', doctype: 'Terms and Conditions' },
  'project-type': { label: 'Project Type', doctype: 'Project Type' },
  'fiscal-year': { label: 'Fiscal Year', doctype: 'Fiscal Year' },
  'email-template': { label: 'Email Template', doctype: 'Email Template' },
  'custom-field-item': { label: 'Custom Field (Item)', doctype: 'Custom Field' },
  'custom-field': { label: 'Custom Field', doctype: 'Custom Field' },
  'item-category': { label: 'Item Category', doctype: 'Item Group' },
  uom: { label: 'UOM', doctype: 'UOM' },
  manufacturer: { label: 'Manufacturer', doctype: 'Manufacturer' }
};

const apiPath = '/api/method/designed_vue_app.designed_vue_app.api.';
const errorText = (error, fallback) => error.response?.data?.exception || error.response?.data?._server_messages || fallback;
const normalizeCheck = (value) => value === true || value === 1 || value === '1' || value === 'true';

export default {
  data() {
    return {
      setting: null,
      doctype: '',
      context: '',
      metadata: null,
      columns: [],
      rows: [],
      sections: [],
      search: '',
      pageNumber: 1,
      pageLength: 25,
      hasMore: false,
      loading: false,
      saving: false,
      error: '',
      showForm: false,
      editingName: '',
      form: {},
      activeTab: '',
      linkOptions: {},
      linkTimers: {}
    };
  },
  computed: {
    tabs() {
      return [...new Set(this.sections.map((section) => section.tab))];
    },
    recordReadOnly() {
      return Number(this.form.docstatus || 0) > 0 || Boolean(this.editingName && !this.metadata?.can_write);
    }
  },
  async mounted() {
    const route = window.frappe?.get_route?.() || [];
    const routeSlug = route.length > 1 ? route[route.length - 1] : window.location.pathname.split('/').filter(Boolean).pop();
    this.setting = settingsMap[decodeURIComponent(routeSlug || '')];
    if (!this.setting) {
      this.error = 'This settings page is not available.';
      return;
    }
    this.doctype = this.setting.doctype;
    this.context = routeSlug === 'custom-field-item' ? 'custom-field-item' : '';
    await this.loadMetadataAndRows();
  },
  beforeUnmount() {
    Object.values(this.linkTimers).forEach(window.clearTimeout);
  },
  methods: {
    async loadMetadataAndRows() {
      this.loading = true;
      this.error = '';
      try {
        const response = await axios.get(`${apiPath}get_system_settings_doctype`, {
          params: { doctype: this.doctype, context: this.context }
        });
        const result = response.data?.message;
        if (!result?.metadata || !Array.isArray(result.columns) || !Array.isArray(result.sections)) {
          throw new Error('Unexpected settings metadata response.');
        }
        this.metadata = { ...result.metadata, label: this.setting.label };
        this.columns = result.columns;
        this.sections = result.sections;
        this.activeTab = this.sections[0]?.tab || '';
        await this.loadRows();
      } catch (error) {
        console.error(`Unable to load ${this.doctype} settings:`, error);
        this.error = errorText(error, `Unable to load ${this.setting.label}. Check your permissions and try again.`);
      } finally {
        this.loading = false;
      }
    },
    async loadRows() {
      this.loading = true;
      this.error = '';
      try {
        const response = await axios.get(`${apiPath}get_system_settings_records`, {
          params: {
            doctype: this.doctype,
            search: this.search,
            context: this.context,
            page: this.pageNumber,
            page_length: this.pageLength
          }
        });
        const result = response.data?.message;
        if (!Array.isArray(result?.records) || typeof result.has_more !== 'boolean') {
          throw new Error('Unexpected settings list response.');
        }
        this.rows = result.records;
        this.hasMore = result.has_more;
      } catch (error) {
        console.error(`Unable to load ${this.doctype} records:`, error);
        this.error = errorText(error, `Unable to load ${this.setting.label} records.`);
      } finally {
        this.loading = false;
      }
    },
    async openRecord(name) {
      this.loading = true;
      this.error = '';
      try {
        const response = await axios.get(`${apiPath}get_system_settings_record`, {
          params: { doctype: this.doctype, name, context: this.context }
        });
        const doc = response.data?.message?.record;
        if (!doc || typeof doc !== 'object') throw new Error('Unexpected settings record response.');
        this.editingName = name;
        this.form = this.makeForm(doc);
        this.showForm = true;
      } catch (error) {
        console.error(`Unable to open ${this.doctype} record:`, error);
        this.error = errorText(error, `Unable to open ${this.setting.label} record.`);
      } finally {
        this.loading = false;
      }
    },
    startNew() {
      this.editingName = '';
      this.form = this.makeForm({});
      this.showForm = true;
      this.error = '';
      this.activeTab = this.sections[0]?.tab || '';
    },
    makeForm(source) {
      const result = { docstatus: Number(source.docstatus || 0) };
      for (const section of this.sections) {
        for (const field of section.fields) {
          if (['Table', 'Table MultiSelect'].includes(field.fieldtype)) {
            result[field.fieldname] = Array.isArray(source[field.fieldname])
              ? source[field.fieldname].map((row) => {
                const childRow = { ...row };
                for (const child of field.children || []) {
                  if (child.fieldtype === 'Check') {
                    childRow[child.fieldname] = normalizeCheck(row[child.fieldname] ?? child.default);
                  }
                }
                return childRow;
              })
              : [];
          } else {
            const value = source[field.fieldname] ?? field.default;
            result[field.fieldname] = field.fieldtype === 'Check'
              ? normalizeCheck(value)
              : (value ?? '');
          }
        }
      }
      return result;
    },
    async saveRecord() {
      this.saving = true;
      this.error = '';
      try {
        const method = this.editingName ? 'update_system_settings_record' : 'create_system_settings_record';
        const response = await axios.post(`${apiPath}${method}`, {
          doctype: this.doctype,
          name: this.editingName || undefined,
          context: this.context,
          values: JSON.stringify(this.form)
        });
        const saved = response.data?.message?.record;
        if (!saved?.name) throw new Error('The server did not return a saved record.');
        this.showForm = false;
        await this.loadRows();
      } catch (error) {
        console.error(`Unable to save ${this.doctype} record:`, error);
        this.error = errorText(error, `Unable to save ${this.setting.label}. Review required fields and try again.`);
      } finally {
        this.saving = false;
      }
    },
    closeForm() {
      this.showForm = false;
      this.error = '';
    },
    clearSearch() {
      this.search = '';
      this.pageNumber = 1;
      this.loadRows();
    },
    searchRecords() {
      this.pageNumber = 1;
      this.loadRows();
    },
    changePage(direction) {
      this.pageNumber = Math.max(1, this.pageNumber + direction);
      this.loadRows();
    },
    changePageSize() {
      this.pageNumber = 1;
      this.loadRows();
    },
    goToCatalog() {
      window.location.assign('/app/designed-system-settings');
    },
    addChildRow(field) {
      const row = {};
      for (const child of field.children) {
        row[child.fieldname] = child.fieldtype === 'Check'
          ? normalizeCheck(child.default)
          : (child.default ?? '');
      }
      this.form[field.fieldname].push(row);
    },
    removeChildRow(field, index) {
      this.form[field.fieldname].splice(index, 1);
    },
    async loadLinkOptions(field, childDoctype = '', value = '') {
      const key = this.linkOptionsKey(field, childDoctype);
      try {
        const response = await axios.get(`${apiPath}get_system_settings_link_options`, {
          params: {
            doctype: this.doctype,
            fieldname: field.fieldname,
            txt: value || this.form[field.fieldname] || '',
            child_doctype: childDoctype
          }
        });
        this.linkOptions[key] = response.data?.message || [];
      } catch (error) {
        console.error(`Unable to load ${field.label} options:`, error);
      }
    },
    scheduleLinkOptions(field, childDoctype = '', value = '') {
      const key = this.linkOptionsKey(field, childDoctype);
      window.clearTimeout(this.linkTimers[key]);
      this.linkTimers[key] = window.setTimeout(() => this.loadLinkOptions(field, childDoctype, value), 250);
    },
    linkOptionsKey(field, childDoctype = '') {
      return `${childDoctype || this.doctype}-${field.fieldname}`;
    },
    linkListId(field, childDoctype = '') {
      return `settings-link-${this.doctype.replaceAll(' ', '-')}-${childDoctype.replaceAll(' ', '-')}-${field.fieldname}`;
    },
    inputType(fieldtype) {
      if (['Int', 'Float', 'Currency', 'Percent'].includes(fieldtype)) return 'number';
      if (fieldtype === 'Date') return 'date';
      if (fieldtype === 'Datetime') return 'datetime-local';
      if (fieldtype === 'Time') return 'time';
      return 'text';
    },
    isLongText(fieldtype) {
      return ['Text', 'Small Text', 'Long Text', 'Code', 'Text Editor'].includes(fieldtype);
    },
    isWideField(field) {
      return this.isLongText(field.fieldtype) || ['Attach', 'Attach Image', 'Link'].includes(field.fieldtype);
    },
    formatValue(value) {
      if (value === null || value === undefined || value === '') return '—';
      if (typeof value === 'boolean' || value === 0 || value === 1) return value ? 'Yes' : 'No';
      return String(value);
    }
  }
};
</script>

<style scoped src="./style.css"></style>
