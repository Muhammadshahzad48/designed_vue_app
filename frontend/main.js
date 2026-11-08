import './layout.css';
import { createApp } from 'vue';
import ProductList from './ProductList.vue';
import PurchaseOrder from './PurchaseOrder.vue';
import PurchaseInvoice from './PurchaseInvoice.vue';
import SalesOrder from './SalesOrder.vue';
import SalesInvoice from './SalesInvoice.vue';
import PaymentEntry from './PaymentEntry.vue';
import PurchaseReceipt from './PurchaseReceipt.vue';
import Quotation from './Quotation.vue';
import DesignedDashboard from './DesignedDashboard.vue';
import SystemSettings from './SystemSettings.vue';
import SettingsDoctype from './SettingsDoctype.vue';
import DynamicDoctypePage from './DynamicDoctypePage.vue';

const pathname = window.location.pathname.toLowerCase().replace(/\/+$/, '');
const isDashboardPage = pathname.includes('designed-dashboard');
const isSettingsDoctypePage = pathname.includes('configuration-settings');
const isSystemSettingsPage = pathname.includes('designed-system-settings');
const isDynamicDoctypePage = pathname === '/app/designed-doctype-list';
const requestedDoctype = new URLSearchParams(window.location.search).get('doctype')?.trim().toLowerCase();
const showStandardDoctypeList = isDynamicDoctypePage && requestedDoctype === 'doctype';
const doctypePageModules = import.meta.glob('./*Page.vue', { eager: true, import: 'default' });
const transactionPages = {
  '/app/sales-order-list': SalesOrder,
  '/app/sales-invoice-list': SalesInvoice,
  '/app/payment-entry-list': PaymentEntry,
  '/app/purchase-receipt-list': PurchaseReceipt,
  '/app/quotation-list': Quotation,
  '/app/purchase-order-list': PurchaseOrder,
  '/app/purchase-invoice-list': PurchaseInvoice
};
const genericPageName = pathname
  .replace(/^\/app\//, '')
  .replace(/-list$/, '')
  .split('-')
  .map((part) => part.charAt(0).toUpperCase() + part.slice(1))
  .join('');
const genericPage = doctypePageModules[`./${genericPageName}Page.vue`];
const appComponent = transactionPages[pathname]
  || (pathname === '/app/item-list' ? ProductList : null)
  || genericPage
  || (isDashboardPage
    ? DesignedDashboard
    : isDynamicDoctypePage
      ? DynamicDoctypePage
      : isSettingsDoctypePage
        ? SettingsDoctype
        : isSystemSettingsPage
          ? SystemSettings
          : ProductList);

if (showStandardDoctypeList) {
  window.location.replace('/app/doctype');
} else {
 createApp(appComponent).mount('#app');
}
