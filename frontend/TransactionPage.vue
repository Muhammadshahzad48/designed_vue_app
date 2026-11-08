<template>
  <main class="item-page po-page transaction-page">
    <header class="item-page-heading">
      <div class="item-page-title">
        <button v-if="showForm" class="back-to-items" type="button" @click="closeForm">
          {{ doctype }} List
        </button>
        <span v-if="showForm" class="title-divider">/</span>
        <h1>{{ showForm ? (editingName || `New ${doctype}`) : doctype }}</h1>
      </div>
      <div v-if="!showForm && metadata?.can_create" class="item-page-actions">
        <button class="new-item-button" type="button" @click="openCreateForm">
          ＋ Add {{ doctype }}
        </button>
      </div>
    </header>

    <template v-if="!showForm">
      <form class="item-filters" @submit.prevent="fetchRecords">
        <div class="filter-row filter-row-primary transaction-filter-row">
          <template v-for="field in searchFields" :key="field.key">
            <select
              v-if="field.key === 'party' && partyInfo?.dynamic && partyInfo.options.length"
              v-model="partyType"
              aria-label="Party type"
              @change="changePartyType"
            >
              <option v-for="option in partyInfo.options" :key="option" :value="option">{{ option }}</option>
            </select>
            <input
              v-model.trim="filters[field.key]"
              :placeholder="field.placeholder"
              :aria-label="field.placeholder"
              :list="field.key === 'party' && isLinkedParty ? partyListId : undefined"
              autocomplete="off"
              @focus="field.key === 'party' && loadPartyOptions()"
              @input="field.key === 'party' && schedulePartyOptions(filters.party)"
            />
          </template>
          <datalist v-if="isLinkedParty" :id="partyListId">
            <option v-for="option in partyOptions" :key="option" :value="option" />
          </datalist>
          <select v-if="statuses.length" v-model="statusFilter" :aria-label="`${doctype} status`">
            <option value="All">All Status</option>
            <option v-for="status in statuses" :key="status" :value="status">{{ status }}</option>
          </select>
          <div class="filter-buttons">
            <button class="show-button" type="submit" :disabled="loading">Show</button>
            <button class="clear-button" type="button" :disabled="loading" @click="clearFilters">Clear</button>
          </div>
        </div>
      </form>
      <p v-if="partyOptionsError" class="party-options-error" role="alert">{{ partyOptionsError }}</p>

      <div class="table-tools">
        <div v-if="loadError" class="error-message" role="alert">
          <span>{{ loadError }}</span>
          <button type="button" @click="loadPage">Try again</button>
        </div>
        <span v-else class="po-loading-label">
          {{ loading ? `Loading ${doctype}…` : `${records.length} ${doctype} records` }}
        </span>
      </div>

      <div class="items-table-scroll">
        <table class="items-table po-table">
          <thead>
            <tr>
              <th v-for="column in columns" :key="column.fieldname">{{ column.label }}</th>
            </tr>
          </thead>
          <tbody>
            <tr
              v-for="record in records"
              :key="record.name"
              class="po-clickable-row"
              tabindex="0"
              @click="openExistingRecord(record.name)"
              @keydown.enter="openExistingRecord(record.name)"
            >
              <td v-for="column in columns" :key="column.fieldname">
                <span v-if="column.fieldname === 'status'" class="item-status" :class="statusClass(record.status)">
                  {{ record.status || 'Draft' }}
                </span>
                <a
                  v-else-if="column.fieldname === 'name'"
                  class="product-code"
                  href="#"
                  @click.prevent.stop="openExistingRecord(record.name)"
                >
                  {{ record.name }}
                </a>
                <span v-else>{{ formatValue(record[column.fieldname], column.fieldtype) }}</span>
              </td>
            </tr>
            <tr v-if="loading">
              <td :colspan="Math.max(columns.length, 1)" class="table-message">Loading {{ doctype }}…</td>
            </tr>
            <tr v-else-if="!loadError && !records.length">
              <td :colspan="Math.max(columns.length, 1)" class="table-message">No {{ doctype }} records found.</td>
            </tr>
          </tbody>
        </table>
      </div>
      <footer class="table-footer">
        <span>{{ loading ? 'Loading…' : `${records.length} ${doctype} records` }}</span>
        <span>ERPNext {{ doctype }} List</span>
      </footer>
    </template>

    <section v-else class="item-create transaction-create">
      <form class="item-create-form" @submit.prevent="saveRecord">
        <header class="po-form-header">
          <div>
            <p class="po-eyebrow">{{ doctype.toUpperCase() }}</p>
            <h3>{{ editingName ? `Edit ${doctype}` : `Create a ${doctype}` }}</h3>
            <p class="po-subtitle">Complete the {{ doctype }} fields below. It will be saved to ERPNext.</p>
          </div>
          <div class="po-form-header-actions">
            <button
              v-for="action in documentActions.workflow_actions"
              :key="action.action"
              class="save-item-button transaction-workflow-action"
              type="button"
              :disabled="saving"
              @click="runDocumentAction(action.action)"
            >
              {{ saving ? 'Working…' : action.action }}
            </button>
            <button
              v-if="documentActions.can_submit"
              class="save-item-button transaction-workflow-action"
              type="button"
              :disabled="saving"
              @click="runDocumentAction('Submit')"
            >
              {{ saving ? 'Submitting…' : 'Submit' }}
            </button>
            <button
              v-if="documentActions.can_cancel"
              class="po-cancel-btn transaction-workflow-action"
              type="button"
              :disabled="saving"
              @click="runDocumentAction('Cancel')"
            >
              {{ saving ? 'Cancelling…' : 'Cancel Document' }}
            </button>
            <button class="po-cancel-btn" type="button" :disabled="saving" @click="closeForm">Close</button>
          </div>
        </header>

        <p v-if="formError" class="form-options-error" role="alert">{{ formError }}</p>
        <p v-if="saveError" class="form-options-error" role="alert">{{ saveError }}</p>
        <section v-if="tabs.length" class="required-fields-panel">
          <div v-if="editingName" class="po-document-state">
            <span class="po-state-badge" :class="`po-state-${Number(document.docstatus)}`">{{ documentStateLabel }}</span>
            <span v-if="documentActions.workflow_state">{{ documentActions.workflow_state }}</span>
            <span v-else-if="document.status">{{ document.status }}</span>
            <span v-if="Number(document.docstatus) === 2">Cancelled records are read-only.</span>
            <span v-else-if="isSubmitted">Submitted records are read-only.</span>
          </div>
          <fieldset class="po-form-fields" :disabled="!canEditDocument">
            <nav class="item-form-tabs" :aria-label="`${doctype} field tabs`">
              <button
                v-for="tab in tabs"
                :key="tab"
                type="button"
                :class="{ 'active-form-tab': activeTab === tab }"
                @click="activeTab = tab"
              >
                {{ tab }}
              </button>
            </nav>
            <details
              v-for="section in sections.filter((entry) => entry.tab === activeTab)"
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
                  :class="{ 'item-form-field-wide': ['Table', 'Table MultiSelect'].includes(field.fieldtype) }"
                >
                  <label v-if="field.fieldtype === 'Check'" class="item-form-checkbox">
                    <input v-model="document[field.fieldname]" type="checkbox" :disabled="field.read_only || saving" />
                    <span>{{ field.label }} <b v-if="field.required">*</b></span>
                  </label>
                  <template v-else>
                    <span>{{ field.label }} <b v-if="field.required">*</b></span>
                    <div v-if="['Table', 'Table MultiSelect'].includes(field.fieldtype)" class="required-child-table">
                      <p v-if="!document[field.fieldname]?.length" class="empty-child-table">No rows added.</p>
                      <details
                        v-for="(row, rowIndex) in document[field.fieldname]"
                        :key="rowIndex"
                        class="required-child-row transaction-child-row"
                        open
                      >
                        <summary class="po-child-row-summary">
                          <strong>{{ row.item_name || row.item_code || `${field.label} ${rowIndex + 1}` }}</strong>
                        </summary>
                        <div class="po-child-row-fields">
                          <template v-for="child in field.children" :key="child.fieldname">
                            <label v-if="child.fieldtype === 'Check'" class="item-form-checkbox">
                              <input v-model="row[child.fieldname]" type="checkbox" :disabled="child.read_only || saving" />
                              <span>{{ child.label }} <b v-if="child.required">*</b></span>
                            </label>
                            <label v-else class="item-form-field">
                              <span>{{ child.label }} <b v-if="child.required">*</b></span>
                              <select
                                v-if="child.fieldtype === 'Select'"
                                v-model="row[child.fieldname]"
                                :required="child.required && !child.read_only"
                                :disabled="child.read_only || saving"
                              >
                                <option value="">Select {{ child.label }}</option>
                                <option v-for="option in child.options" :key="option" :value="option">{{ option }}</option>
                              </select>
                              <textarea
                                v-else-if="isLongTextField(child.fieldtype)"
                                v-model="row[child.fieldname]"
                                rows="3"
                                :disabled="child.read_only || saving"
                              ></textarea>
                              <div v-else-if="isTransactionItemField(child)" class="form-link-control transaction-item-picker">
                                <input
                                  v-model="row[child.fieldname]"
                                  :required="child.required && !child.read_only"
                                  :disabled="child.read_only || saving"
                                  autocomplete="off"
                                  @focus="loadTransactionItemOptions(child, field.table_doctype, rowIndex)"
                                  @input="handleTransactionItemInput(child, field.table_doctype, rowIndex, row[child.fieldname])"
                                />
                                <div
                                  v-if="getTransactionItemOptions(child, field.table_doctype, rowIndex).length"
                                  class="transaction-item-options"
                                >
                                  <button
                                    v-for="option in getTransactionItemOptions(child, field.table_doctype, rowIndex)"
                                    :key="option.item_code"
                                    type="button"
                                    :disabled="saving"
                                    @mousedown.prevent="selectTransactionItem(option, field, row, rowIndex)"
                                  >
                                    <strong>{{ option.item_code }}</strong>
                                    <span>{{ option.item_name }}</span>
                                  </button>
                                </div>
                              </div>
                              <div v-else-if="child.fieldtype === 'Link'" class="form-link-control">
                                <input
                                  v-model="row[child.fieldname]"
                                  :list="linkListId(child, field.table_doctype, rowIndex)"
                                  :required="child.required && !child.read_only"
                                  :disabled="child.read_only || saving"
                                  autocomplete="off"
                                  @focus="loadLinkOptions(child, field.table_doctype, rowIndex)"
                                  @input="scheduleLinkOptions(child, field.table_doctype, rowIndex, row[child.fieldname])"
                                  @change="fetchLinkedFieldValues(child, row[child.fieldname], child.link_doctype, field.table_doctype, row, rowIndex)"
                                />
                                <button
                                  v-if="canCreateLinkedDocument(child)"
                                  class="form-link-create"
                                  type="button"
                                  :disabled="saving"
                                  @click="createLinkedDocument(child, (name) => { row[child.fieldname] = name; fetchLinkedFieldValues(child, name, child.link_doctype, field.table_doctype, row, rowIndex); }, field.table_doctype)"
                                >
                                  + Add {{ child.link_doctype }}
                                </button>
                                <datalist :id="linkListId(child, field.table_doctype, rowIndex)">
                                  <option v-for="option in getLinkOptions(child, field.table_doctype, rowIndex)" :key="option" :value="option" />
                                </datalist>
                              </div>
                              <input
                                v-else
                                v-model="row[child.fieldname]"
                                :type="inputType(child.fieldtype)"
                                :required="child.required && !child.read_only"
                                :disabled="child.read_only || saving"
                              />
                            </label>
                          </template>
                          <button
                            v-if="canEditDocument"
                            class="remove-child-row"
                            type="button"
                            :disabled="saving"
                            @click="removeTableRow(field, rowIndex)"
                          >
                            Remove row
                          </button>
                        </div>
                      </details>
                      <button
                        v-if="canEditDocument"
                        class="add-child-row"
                        type="button"
                        :disabled="saving"
                        @click="addTableRow(field)"
                      >
                        + Add {{ field.label }}
                      </button>
                    </div>
                    <select
                      v-else-if="field.fieldtype === 'Select' || field.link_options?.length"
                      v-model="document[field.fieldname]"
                      :required="field.required && !field.read_only"
                      :disabled="field.read_only || saving"
                      @change="handleDynamicLinkTypeChange(field)"
                    >
                      <option value="">Select {{ field.label }}</option>
                      <option
                        v-for="option in field.fieldtype === 'Select' ? field.options : field.link_options"
                        :key="option"
                        :value="option"
                      >
                        {{ option }}
                      </option>
                    </select>
                    <textarea
                      v-else-if="isLongTextField(field.fieldtype)"
                      v-model="document[field.fieldname]"
                      rows="3"
                      :required="field.required && !field.read_only"
                      :disabled="field.read_only || saving"
                    ></textarea>
                    <div v-else-if="field.fieldtype === 'Dynamic Link'" class="form-link-control">
                      <input
                        v-model="document[field.fieldname]"
                        :list="linkListId(dynamicLinkField(field))"
                        :required="field.required && !field.read_only"
                        :disabled="field.read_only || saving || !dynamicLinkField(field).link_doctype"
                        autocomplete="off"
                        @focus="loadLinkOptions(dynamicLinkField(field))"
                        @input="scheduleLinkOptions(dynamicLinkField(field), '', null, document[field.fieldname])"
                        @change="fetchLinkedFieldValues(field, document[field.fieldname], dynamicLinkField(field).link_doctype)"
                      />
                      <button
                        v-if="canCreateLinkedDocument(dynamicLinkField(field))"
                        class="form-link-create"
                        type="button"
                        :disabled="saving"
                        @click="createLinkedDocument(dynamicLinkField(field), (name) => { document[field.fieldname] = name; fetchLinkedFieldValues(field, name, dynamicLinkField(field).link_doctype); })"
                      >
                        + Add {{ dynamicLinkField(field).link_doctype }}
                      </button>
                      <datalist :id="linkListId(dynamicLinkField(field))">
                        <option
                          v-for="option in getLinkOptions(dynamicLinkField(field))"
                          :key="option"
                          :value="option"
                        />
                      </datalist>
                    </div>
                    <div v-else-if="field.fieldtype === 'Link'" class="form-link-control">
                      <input
                        v-model="document[field.fieldname]"
                        :list="linkListId(field)"
                        :required="field.required && !field.read_only"
                        :disabled="field.read_only || saving"
                        autocomplete="off"
                        @focus="loadLinkOptions(field)"
                        @input="scheduleLinkOptions(field, '', null, document[field.fieldname])"
                        @change="fetchLinkedFieldValues(field, document[field.fieldname], field.link_doctype)"
                      />
                      <button
                        v-if="canCreateLinkedDocument(field)"
                        class="form-link-create"
                        type="button"
                        :disabled="saving"
                        @click="createLinkedDocument(field, (name) => { document[field.fieldname] = name; fetchLinkedFieldValues(field, name, field.link_doctype); })"
                      >
                        + Add {{ field.link_doctype }}
                      </button>
                      <datalist :id="linkListId(field)">
                        <option v-for="option in getLinkOptions(field)" :key="option" :value="option" />
                      </datalist>
                    </div>
                    <input
                      v-else
                      v-model="document[field.fieldname]"
                      :type="inputType(field.fieldtype)"
                      :required="field.required && !field.read_only"
                      :disabled="field.read_only || saving"
                    />
                  </template>
                </div>
              </div>
            </details>
          </fieldset>
        </section>

        <footer class="item-form-actions">
          <button class="form-cancel-button" type="button" :disabled="saving" @click="closeForm">Cancel</button>
          <button v-if="canEditDocument" class="save-item-button" type="submit" :disabled="saving || !tabs.length">
            {{ saving ? 'Saving…' : editingName ? `Update ${doctype}` : `Save ${doctype}` }}
          </button>
          <span v-else class="po-readonly-note">This record has already been submitted.</span>
        </footer>
      </form>
    </section>
  </main>
</template>

<script>
export default {
  props: {
    doctype: { type: String, required: true },
    initialName: { type: String, default: '' }
  },
  data() {
    return {
      metadata: null,
      columns: [],
      records: [],
      statuses: [],
      sections: [],
      tabs: [],
      activeTab: '',
      document: {},
      documentActions: { workflow_actions: [], can_submit: false, can_cancel: false },
      filters: { name: '', party: '', company: '' },
      partyType: '',
      partyOptions: [],
      partyOptionsError: '',
      partyOptionsTimer: null,
      partyOptionsRequestId: 0,
      statusFilter: 'All',
      loading: false,
      saving: false,
      showForm: false,
      editingName: '',
      loadError: '',
      formError: '',
      saveError: '',
      linkOptions: {},
      linkTimers: {},
      requestIds: {},
      transactionItemOptions: {},
      transactionItemTimers: {},
      transactionItemRequestIds: {},
      transactionItemDetailRequestIds: {},
      fetchRequestIds: {}
    };
  },
  computed: {
    partyInfo() {
      return this.metadata?.search_fields?.party || null;
    },
    isLinkedParty() {
      return Boolean(this.partyInfo?.dynamic || this.partyInfo?.link_doctype);
    },
    partyListId() {
      return `transaction-party-${this.doctype.toLowerCase().replace(/[^a-z0-9_-]/g, '-')}`;
    },
    searchFields() {
      const fields = [
        { key: 'name', fieldname: 'name', placeholder: `Search ${this.doctype} ID` }
      ];
      if (this.partyInfo) {
        const label = this.partyInfo.dynamic
          ? this.partyType || 'Party'
          : this.partyInfo.link_doctype || 'Party';
        fields.push({
          key: 'party',
          fieldname: this.partyInfo.fieldname,
          placeholder: `Search ${label}`
        });
      }
      if (this.metadata?.search_fields?.company) {
        fields.push({ key: 'company', fieldname: 'company', placeholder: 'Company' });
      }
      return fields;
    },
    canEditDocument() {
      return !this.isSubmitted && Boolean(
        this.editingName ? this.metadata?.can_write : this.metadata?.can_create
      );
    },
    isSubmitted() {
      return Number(this.document.docstatus) > 0;
    },
    documentStateLabel() {
      const state = Number(this.document.docstatus);
      return state === 1 ? 'Submitted' : state === 2 ? 'Cancelled' : 'Draft';
    }
  },
  async mounted() {
    await this.loadPage();
    if (this.initialName && this.metadata) await this.openExistingRecord(this.initialName);
  },
  methods: {
    async loadPage() {
      this.loading = true;
      this.loadError = '';
      try {
        const metadata = await window.frappe.xcall(
          'designed_vue_app.designed_vue_app.api.get_designed_transaction_form',
          { doctype: this.doctype }
        );
        this.metadata = metadata;
        this.columns = metadata.columns || [];
        const partyInfo = metadata.search_fields?.party;
        this.partyType = partyInfo?.default || partyInfo?.options?.[0] || '';
        await this.fetchRecords();
      } catch (error) {
        console.error(`Unable to load ${this.doctype} page:`, error);
        this.loadError = error?.message || `Unable to load ${this.doctype}.`;
      } finally {
        this.loading = false;
      }
    },
    async fetchRecords() {
      this.loading = true;
      this.loadError = '';
      try {
        const result = await window.frappe.xcall(
          'designed_vue_app.designed_vue_app.api.get_designed_transaction_records',
          {
            doctype: this.doctype,
            name_search: this.filters.name,
            party_search: this.filters.party,
            party_field: this.partyInfo?.fieldname || '',
            party_type: this.partyType,
            company_search: this.filters.company,
            status: this.statusFilter
          }
        );
        this.records = result.records || [];
        this.columns = result.columns || this.columns;
        this.statuses = result.statuses || [];
      } catch (error) {
        console.error(`Unable to load ${this.doctype} records:`, error);
        this.records = [];
        this.loadError = error?.message || `Unable to load ${this.doctype} records.`;
      } finally {
        this.loading = false;
      }
    },
    clearFilters() {
      window.clearTimeout(this.partyOptionsTimer);
      this.partyOptionsRequestId += 1;
      this.filters = { name: '', party: '', company: '' };
      this.partyType = this.partyInfo?.default || this.partyInfo?.options?.[0] || '';
      this.statusFilter = 'All';
      this.partyOptions = [];
      this.partyOptionsError = '';
      this.fetchRecords();
    },
    changePartyType() {
      window.clearTimeout(this.partyOptionsTimer);
      this.filters.party = '';
      this.partyOptions = [];
      this.partyOptionsError = '';
      this.loadPartyOptions();
    },
    schedulePartyOptions(txt = '') {
      window.clearTimeout(this.partyOptionsTimer);
      this.partyOptionsTimer = window.setTimeout(() => this.loadPartyOptions(txt), 180);
    },
    async loadPartyOptions(txt = '') {
      if (!this.isLinkedParty) return;
      const requestId = ++this.partyOptionsRequestId;
      this.partyOptionsError = '';
      try {
        const options = await window.frappe.xcall(
          'designed_vue_app.designed_vue_app.api.get_designed_transaction_party_options',
          { doctype: this.doctype, party_type: this.partyType, txt }
        );
        if (this.partyOptionsRequestId === requestId) this.partyOptions = options || [];
      } catch (error) {
        console.error(`Unable to load ${this.partyType || this.partyInfo?.link_doctype} options:`, error);
        if (this.partyOptionsRequestId === requestId) {
          this.partyOptionsError = error?.message || 'Unable to load party options.';
          this.partyOptions = [];
        }
      }
    },
    async openCreateForm() {
      this.editingName = '';
      this.document = {};
      this.documentActions = { workflow_actions: [], can_submit: false, can_cancel: false };
      this.saveError = '';
      this.formError = '';
      this.showForm = true;
      await this.loadForm();
    },
    async openExistingRecord(name) {
      this.editingName = name;
      this.document = {};
      this.saveError = '';
      this.formError = '';
      this.showForm = true;
      await this.loadForm();
      if (!this.tabs.length) return;
      try {
        const result = await window.frappe.xcall(
          'designed_vue_app.designed_vue_app.api.get_designed_transaction_record',
          { doctype: this.doctype, name }
        );
        this.document = { ...this.document, ...result.record };
        await this.refreshDocumentActions();
      } catch (error) {
        console.error(`Unable to load ${this.doctype} ${name}:`, error);
        this.saveError = error?.message || `Unable to load ${this.doctype} ${name}.`;
      }
    },
    async loadForm() {
      this.sections = [];
      this.tabs = [];
      this.activeTab = '';
      this.formError = '';
      try {
        const result = await window.frappe.xcall(
          'designed_vue_app.designed_vue_app.api.get_designed_transaction_form',
          { doctype: this.doctype }
        );
        this.sections = result.sections || [];
        this.tabs = [...new Set(this.sections.map((section) => section.tab))];
        this.activeTab = this.tabs[0] || '';
        this.initializeDefaults();
      } catch (error) {
        console.error(`Unable to load ${this.doctype} fields:`, error);
        this.formError = error?.message || `Unable to load ${this.doctype} fields.`;
      }
    },
    initializeDefaults() {
      for (const field of this.sections.flatMap((section) => section.fields)) {
        if (['Table', 'Table MultiSelect'].includes(field.fieldtype)) {
          const hasItems = (field.children || []).some((child) => child.fieldname === 'item_code');
          this.document[field.fieldname] = hasItems ? [this.createTableRow(field)] : [];
        } else if (this.document[field.fieldname] === undefined || this.document[field.fieldname] === '') {
          this.document[field.fieldname] = this.fieldDefault(field);
        }
      }
    },
    fieldDefault(field) {
      if (field.fieldtype === 'Date' && ['__today', 'Today'].includes(field.default)) {
        return new Date().toISOString().slice(0, 10);
      }
      if (field.default !== undefined && field.default !== null && field.default !== '') {
        return field.fieldtype === 'Check'
          ? field.default === true || field.default === 1 || field.default === '1'
          : field.default;
      }
      return field.fieldtype === 'Check' ? false : '';
    },
    createTableRow(field) {
      return Object.fromEntries((field.children || []).map((child) => [child.fieldname, this.fieldDefault(child)]));
    },
    addTableRow(field) {
      this.document[field.fieldname].push(this.createTableRow(field));
    },
    removeTableRow(field, index) {
      this.document[field.fieldname].splice(index, 1);
    },
    async saveRecord() {
      if (this.saving || this.isSubmitted) return;
      const missingTable = this.sections.flatMap((section) => section.fields).find((field) =>
        ['Table', 'Table MultiSelect'].includes(field.fieldtype)
          && field.required
          && !this.document[field.fieldname]?.length
      );
      if (missingTable) {
        this.saveError = `${missingTable.label} is required. Add at least one row.`;
        this.activeTab = this.sections.find((section) => section.fields.includes(missingTable))?.tab || '';
        return;
      }
      this.saving = true;
      this.saveError = '';
      let savedName = '';
      try {
        const method = this.editingName ? 'update_designed_transaction' : 'create_designed_transaction';
        const parameters = {
          doctype: this.doctype,
          values: JSON.stringify(this.document)
        };
        if (this.editingName) parameters.name = this.editingName;
        const result = await window.frappe.xcall(`designed_vue_app.designed_vue_app.api.${method}`, parameters);
        if (!result?.name) throw new Error(`The server did not confirm that ${this.doctype} was saved.`);
        savedName = result.name;
      } catch (error) {
        console.error(`Unable to save ${this.doctype}:`, error);
        this.saveError = error?.message || `Unable to save ${this.doctype}.`;
      } finally {
        this.saving = false;
      }
      if (!savedName) return;

      this.saving = true;
      this.editingName = savedName;
      try {
        const saved = await window.frappe.xcall(
          'designed_vue_app.designed_vue_app.api.get_designed_transaction_record',
          { doctype: this.doctype, name: savedName }
        );
        this.document = saved.record;
        await this.refreshDocumentActions();
        await this.fetchRecords();
      } catch (error) {
        console.error(`Saved ${this.doctype} ${savedName}, but unable to reload it:`, error);
        this.saveError = `${this.doctype} was saved as ${savedName}, but the latest document state could not be loaded: ${error?.message || 'Unknown error'}`;
      } finally {
        this.saving = false;
      }
    },
    async refreshDocumentActions() {
      if (!this.editingName) {
        this.documentActions = { workflow_actions: [], can_submit: false, can_cancel: false };
        return;
      }
      this.documentActions = await window.frappe.xcall(
        'designed_vue_app.designed_vue_app.api.get_designed_transaction_actions',
        { doctype: this.doctype, name: this.editingName }
      );
    },
    async runDocumentAction(action) {
      if (action === 'Cancel') {
        window.frappe.confirm(
          `Cancel ${this.doctype} ${this.editingName}?`,
          () => this.executeDocumentAction(action)
        );
        return;
      }
      await this.executeDocumentAction(action);
    },
    async executeDocumentAction(action) {
      if (this.saving || !this.editingName) return;
      this.saving = true;
      this.saveError = '';
      try {
        const result = await window.frappe.xcall(
          'designed_vue_app.designed_vue_app.api.run_designed_transaction_action',
          { doctype: this.doctype, name: this.editingName, action }
        );
        if (!result?.record) throw new Error(`The server did not confirm the ${action} action.`);
        this.document = result.record;
        this.documentActions = result.actions;
        if (result.queued) {
          this.saveError = `${action} was queued by Frappe and will finish in the background.`;
        }
        await this.fetchRecords();
      } catch (error) {
        console.error(`Unable to run ${action} for ${this.doctype}:`, error);
        this.saveError = error?.message || `Unable to run ${action}.`;
      } finally {
        this.saving = false;
      }
    },
    closeForm() {
      if (this.saving) return;
      this.showForm = false;
      this.editingName = '';
      this.saveError = '';
      this.documentActions = { workflow_actions: [], can_submit: false, can_cancel: false };
    },
    isLongTextField(type) {
      return ['Text', 'Text Editor', 'Small Text', 'Long Text', 'Code', 'JSON'].includes(type);
    },
    inputType(type) {
      if (['Int', 'Float', 'Currency', 'Percent', 'Rating', 'Duration'].includes(type)) return 'number';
      if (type === 'Date') return 'date';
      if (type === 'Datetime') return 'datetime-local';
      if (type === 'Time') return 'time';
      return 'text';
    },
    linkKey(field, childDoctype = '', rowIndex = 'parent') {
      return `${childDoctype || this.doctype}:${rowIndex}:${field.fieldname}:${field.link_doctype || ''}`;
    },
    linkListId(field, childDoctype = '', rowIndex = 'parent') {
      return `transaction-link-${this.linkKey(field, childDoctype, rowIndex).replace(/[^a-zA-Z0-9_-]/g, '-')}`;
    },
    getLinkOptions(field, childDoctype = '', rowIndex = 'parent') {
      return this.linkOptions[this.linkKey(field, childDoctype, rowIndex)] || [];
    },
    scheduleLinkOptions(field, childDoctype = '', rowIndex = null, txt = '') {
      if (!field.link_doctype) return;
      const key = this.linkKey(field, childDoctype, rowIndex ?? 'parent');
      window.clearTimeout(this.linkTimers[key]);
      this.linkTimers[key] = window.setTimeout(
        () => this.loadLinkOptions(field, childDoctype, rowIndex, txt),
        180
      );
    },
    async loadLinkOptions(field, childDoctype = '', rowIndex = null, txt = '') {
      if (!field.link_doctype) return;
      if (!['Link', 'Dynamic Link'].includes(field.fieldtype)) return;
      const key = this.linkKey(field, childDoctype, rowIndex ?? 'parent');
      const requestId = (this.requestIds[key] || 0) + 1;
      this.requestIds[key] = requestId;
      try {
        const options = await window.frappe.xcall(
          'designed_vue_app.designed_vue_app.api.get_designed_transaction_link_options',
          {
            doctype: this.doctype,
            fieldname: field.fieldname,
            child_doctype: childDoctype,
            linked_doctype: field.fieldtype === 'Dynamic Link' ? field.link_doctype : '',
            txt
          }
        );
        if (this.requestIds[key] === requestId) this.linkOptions[key] = options || [];
      } catch (error) {
        console.error(`Unable to load ${field.label} options:`, error);
        this.saveError = error?.message || `Unable to load options for ${field.label}.`;
      }
    },
    isTransactionItemField(field) {
      return field.fieldtype === 'Link' && field.fieldname === 'item_code' && field.link_doctype === 'Item';
    },
    transactionItemKey(field, childDoctype, rowIndex) {
      return `${childDoctype}:${rowIndex}:${field.fieldname}`;
    },
    getTransactionItemOptions(field, childDoctype, rowIndex) {
      return this.transactionItemOptions[this.transactionItemKey(field, childDoctype, rowIndex)] || [];
    },
    scheduleTransactionItemOptions(field, childDoctype, rowIndex, txt = '') {
      const key = this.transactionItemKey(field, childDoctype, rowIndex);
      window.clearTimeout(this.transactionItemTimers[key]);
      this.transactionItemTimers[key] = window.setTimeout(
        () => this.loadTransactionItemOptions(field, childDoctype, rowIndex, txt),
        180
      );
    },
    handleTransactionItemInput(field, childDoctype, rowIndex, txt = '') {
      const key = this.transactionItemKey(field, childDoctype, rowIndex);
      this.transactionItemDetailRequestIds[key] = (this.transactionItemDetailRequestIds[key] || 0) + 1;
      this.scheduleTransactionItemOptions(field, childDoctype, rowIndex, txt);
    },
    async loadTransactionItemOptions(field, childDoctype, rowIndex, txt = '') {
      const key = this.transactionItemKey(field, childDoctype, rowIndex);
      const requestId = (this.transactionItemRequestIds[key] || 0) + 1;
      this.transactionItemRequestIds[key] = requestId;
      try {
        const options = await window.frappe.xcall(
          'designed_vue_app.designed_vue_app.api.get_designed_transaction_item_options',
          { doctype: this.doctype, child_doctype: childDoctype, search_by: field.fieldname, txt }
        );
        if (this.transactionItemRequestIds[key] === requestId) {
          this.transactionItemOptions[key] = options || [];
        }
      } catch (error) {
        console.error(`Unable to load ${field.label} options:`, error);
        this.saveError = error?.message || `Unable to load ${field.label} options.`;
      }
    },
    async selectTransactionItem(option, tableField, row, rowIndex) {
      row.item_code = option.item_code;
      row.item_name = option.item_name;
      row.stock_uom = option.stock_uom;
      row.description = option.description;
      row.qty = Number(row.qty) || 1;
      const itemField = tableField.children.find((field) => field.fieldname === 'item_code');
      const key = this.transactionItemKey(itemField, tableField.table_doctype, rowIndex);
      const requestId = (this.transactionItemDetailRequestIds[key] || 0) + 1;
      this.transactionItemDetailRequestIds[key] = requestId;
      this.transactionItemOptions[key] = [];
      this.saveError = '';
      try {
        const details = await window.frappe.xcall(
          'designed_vue_app.designed_vue_app.api.get_designed_transaction_item_details',
          {
            doctype: this.doctype,
            child_doctype: tableField.table_doctype,
            item_code: option.item_code,
            values: JSON.stringify(this.document)
          }
        );
        if (this.transactionItemDetailRequestIds[key] !== requestId) return;
        Object.assign(row, details);
      } catch (error) {
        if (this.transactionItemDetailRequestIds[key] !== requestId) return;
        console.error(`Unable to load details for Item ${option.item_code}:`, error);
        this.saveError = error?.message || `Unable to load details for Item ${option.item_code}.`;
      }
      if (tableField.children.some((child) => child.fetch_from?.startsWith('item_code.'))) {
        await this.fetchLinkedFieldValues(
          itemField,
          option.item_code,
          'Item',
          tableField.table_doctype,
          row,
          rowIndex
        );
      }
    },
    async fetchLinkedFieldValues(field, linkName, linkedDoctype, childDoctype = '', target = null, rowIndex = 'parent') {
      if (!field?.fieldname) return;
      const dependents = childDoctype
        ? this.sections.flatMap((section) => section.fields)
          .filter((parentField) => parentField.table_doctype === childDoctype)
          .flatMap((parentField) => parentField.children || [])
        : this.sections.flatMap((section) => section.fields);
      if (!dependents.some((dependent) => dependent.fetch_from?.startsWith(`${field.fieldname}.`))) return;
      const key = `${childDoctype || this.doctype}:${rowIndex}:${field.fieldname}`;
      const requestId = (this.fetchRequestIds[key] || 0) + 1;
      this.fetchRequestIds[key] = requestId;
      const record = target || this.document;
      if (!linkName || !linkedDoctype) {
        for (const dependent of dependents) {
          if (dependent.fetch_from?.startsWith(`${field.fieldname}.`)) {
            record[dependent.fieldname] = '';
          }
        }
        return;
      }
      try {
        const values = await window.frappe.xcall(
          'designed_vue_app.designed_vue_app.api.get_designed_transaction_fetch_values',
          {
            doctype: this.doctype,
            fieldname: field.fieldname,
            child_doctype: childDoctype,
            linked_doctype: field.fieldtype === 'Dynamic Link' ? linkedDoctype : '',
            link_name: linkName
          }
        );
        if (this.fetchRequestIds[key] === requestId) Object.assign(record, values);
      } catch (error) {
        if (this.fetchRequestIds[key] !== requestId) return;
        console.error(`Unable to fetch fields from ${linkedDoctype} ${linkName}:`, error);
        this.saveError = error?.message || `Unable to fetch fields from ${linkedDoctype}.`;
      }
    },
    canCreateLinkedDocument(field) {
      return Boolean(
        field.link_doctype
        && field.link_doctype !== 'DocType'
        && window.frappe?.model?.can_create?.(field.link_doctype)
        && window.frappe?.ui?.form?.make_quick_entry
      );
    },
    dynamicLinkField(field) {
      return {
        ...field,
        link_doctype: this.document[field.dynamic_link_field] || ''
      };
    },
    handleDynamicLinkTypeChange(field) {
      for (const dynamicField of this.sections.flatMap((section) => section.fields)) {
        if (
          dynamicField.fieldtype !== 'Dynamic Link'
          || dynamicField.dynamic_link_field !== field.fieldname
        ) continue;
        this.document[dynamicField.fieldname] = '';
        this.fetchLinkedFieldValues(
          dynamicField,
          '',
          this.dynamicLinkField(dynamicField).link_doctype
        );
        const key = this.linkKey(this.dynamicLinkField(dynamicField));
        this.requestIds[key] = (this.requestIds[key] || 0) + 1;
        this.linkOptions[key] = [];
      }
    },
    createLinkedDocument(field, onCreated, childDoctype = '') {
      if (!this.canCreateLinkedDocument(field)) return;
      window.frappe.ui.form.make_quick_entry(
        field.link_doctype,
        (doc) => {
          onCreated(doc.name);
          this.loadLinkOptions(field, childDoctype, null, doc.name);
        },
        null,
        null,
        true
      );
    },
    statusClass(status) {
      return status === 'Cancelled' ? 'item-status-disabled' : '';
    },
    formatValue(value, type) {
      if (value === null || value === undefined || value === '') return '—';
      if (type === 'Date' && !Number.isNaN(new Date(value).getTime())) {
        return new Date(value).toLocaleDateString(undefined, { year: 'numeric', month: 'short', day: 'numeric' });
      }
      if (['Currency', 'Float', 'Percent'].includes(type) && Number.isFinite(Number(value))) {
        return new Intl.NumberFormat(undefined, { maximumFractionDigits: 2 }).format(Number(value));
      }
      return value;
    }
  }
};
</script>

<style scoped src="./style.css"></style>

<style scoped>
.po-form-header {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 20px;
  padding: 18px 24px 16px;
  border-bottom: 1px solid #ebeff2;
}

.po-form-header h3 {
  margin: 0;
  color: #1d2d3d;
  font-size: 22px;
}

.po-eyebrow {
  margin: 0 0 8px;
  color: #718391;
  font-size: 10px;
  font-weight: 700;
  letter-spacing: 0.08em;
}

.po-subtitle {
  margin: 6px 0 0;
  color: #64798b;
  font-size: 12px;
}

.po-form-header-actions {
  display: flex;
  align-items: center;
  justify-content: flex-end;
  flex-wrap: wrap;
  gap: 8px;
}

.po-cancel-btn {
  min-height: 34px;
  padding: 0 14px;
  border: 1px solid #d4dbe2;
  border-radius: 4px;
  color: #324a5f;
  background: #fff;
}

.transaction-workflow-action {
  min-height: 34px;
  padding: 0 12px;
}

.transaction-filter-row {
  grid-template-columns: repeat(auto-fit, minmax(140px, 1fr)) auto;
}

.party-options-error {
  margin: 6px 0;
  color: #b42318;
  font-size: 11px;
}

.transaction-child-row {
  grid-column: 1 / -1;
}

.transaction-item-picker {
  position: relative;
}

.transaction-item-options {
  position: absolute;
  z-index: 20;
  top: calc(100% + 3px);
  right: 0;
  left: 0;
  max-height: 240px;
  overflow-y: auto;
  border: 1px solid #d5dce2;
  border-radius: 5px;
  background: #fff;
  box-shadow: 0 8px 18px rgb(22 42 60 / 14%);
}

.transaction-item-options button {
  display: flex;
  width: 100%;
  flex-direction: column;
  align-items: flex-start;
  gap: 3px;
  padding: 9px 11px;
  border: 0;
  border-bottom: 1px solid #edf0f2;
  background: #fff;
  color: #233746;
  text-align: left;
}

.transaction-item-options button:hover,
.transaction-item-options button:focus-visible {
  background: #f3f7fa;
}

.transaction-item-options button span {
  color: #6b7d8b;
  font-size: 11px;
}

@media (max-width: 760px) {
  .po-form-header {
    flex-direction: column;
  }

  .po-form-header-actions {
    justify-content: flex-start;
  }

  .transaction-filter-row {
    grid-template-columns: minmax(0, 1fr);
  }
}
</style>
