<template>
  <main class="system-settings-page">
    <header class="system-settings-header">
      <div>
        <a class="system-settings-home" href="/app/designed-dashboard">‹ Dashboard</a>
        <h1>System Settings</h1>
        <p>Configuration records available in this site</p>
      </div>
      <span class="settings-count">{{ availableSettings.length }} available</span>
    </header>

    <p v-if="loadError" class="settings-notice" role="alert">{{ loadError }}</p>

    <section class="settings-tile-grid" aria-label="System settings">
      <a
        v-for="setting in availableSettings"
        :key="setting.slug"
        class="settings-tile"
        :href="`/app/configuration-settings/${setting.slug}`"
        @click.prevent="openSetting(setting)"
      >
        <span class="settings-tile-icon" aria-hidden="true">{{ setting.icon }}</span>
        <span class="settings-tile-label">{{ setting.label }}</span>
      </a>
      <p v-if="!loadError && !availableSettings.length" class="settings-empty-message">
        No configuration DocTypes are installed on this site.
      </p>
    </section>
  </main>
</template>

<script>
import axios from 'axios';

const settings = [
  ['organization', 'Organization', '🏢', 'Company'],
  ['department', 'Department', '👥', 'Department'],
  ['designation', 'Designation', '🪪', 'Designation'],
  ['role', 'Roles', '🔐', 'Role'],
  ['user', 'User', '👤', 'User'],
  ['warehouse', 'Warehouse', '🏭', 'Warehouse'],
  ['delivery-method', 'Delivery Method', '🚚'],
  ['payment-terms', 'Payment Terms', '📋', 'Payment Terms Template'],
  ['charge', 'Charge', '🧾'],
  ['currency-rate', 'Currency Rate', '💱', 'Currency Exchange'],
  ['cost-center', 'Cost Center', '💰', 'Cost Center'],
  ['bank', 'Bank', '🏦', 'Bank'],
  ['bank-account', 'Bank Account', '💳', 'Bank Account'],
  ['import-export', 'Import / Export', '📖'],
  ['delivery-term', 'Delivery Term', '📄'],
  ['terms-and-conditions', 'Terms & Conditions', '📝', 'Terms and Conditions'],
  ['approval-settings', 'Approval Settings', '✅'],
  ['enquiry-type', 'Enquiry Type', '☎️'],
  ['project-type', 'Project Type', '📑', 'Project Type'],
  ['job-category', 'Job Category', '🧰'],
  ['job', 'Job', '🔧'],
  ['labour-type', 'Labour Type', '🛠️'],
  ['division', 'Division', '🛠️'],
  ['service-type', 'Service Type', '⚙️'],
  ['service-type-category', 'Service Type Category', '🧩'],
  ['vat', 'VAT', '％'],
  ['fiscal-year', 'Fiscal Year', '🗓️', 'Fiscal Year'],
  ['entry-close', 'Entry Close', '🔒'],
  ['report-pdf-settings', 'Report PDF Settings', '📑'],
  ['business-type', 'Business Type', '🤝'],
  ['q-production-batch', 'Q. Production Batch', '🧪'],
  ['employee-rate', 'Employee Rate', '👷'],
  ['barcode', 'Barcode', '▥'],
  ['custom-field-item', 'Custom Field (Item)', '🧾', 'Custom Field'],
  ['site', 'Site', '🏗️'],
  ['expense-category', 'Expense Category', '🧮'],
  ['reminder', 'Reminder', '🔔'],
  ['email-template', 'Email Template', '✉️', 'Email Template'],
  ['production-equipment', 'Production Equipment', '🛠️'],
  ['approvals', 'Approvals', '📋'],
  ['custom-field', 'Custom Field', '🧾', 'Custom Field'],
  ['item-category', 'Item Category', '🔷', 'Item Group'],
  ['uom', 'UOM', '📐', 'UOM'],
  ['manufacturer', 'Manufacturer', '🏭', 'Manufacturer'],
  ['bank-guarantee-category', 'Bank Guarantee Category', '🏦']
].map(([slug, label, icon, doctype]) => ({
  slug,
  label,
  icon,
  doctype: doctype || '',
  available: Boolean(doctype)
}));

export default {
  data() {
    return {
      settings,
      loadError: ''
    };
  },
  computed: {
    availableSettings() {
      return this.settings.filter((setting) => setting.available);
    }
  },
  async mounted() {
    try {
      const response = await axios.get('/api/method/designed_vue_app.designed_vue_app.api.get_system_settings_doctypes');
      const installed = response.data?.message;
      if (!Array.isArray(installed)) throw new Error('Unexpected settings metadata response.');
      const installedSet = new Set(installed);
      this.settings = this.settings.map((setting) => ({
        ...setting,
        available: Boolean(setting.doctype && installedSet.has(setting.doctype))
      }));
    } catch (error) {
      console.error('Unable to load installed settings DocTypes:', error);
      this.loadError = 'Could not verify installed DocTypes. Refresh this page or contact your administrator.';
    }
  },
  methods: {
    openSetting(setting) {
      if (!setting.available) return;
      window.location.assign(`/app/configuration-settings/${setting.slug}`);
    }
  }
};
</script>

<style scoped src="./style.css"></style>
