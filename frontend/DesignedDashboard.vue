<template>
  <main class="designed-dashboard">
    <header class="dashboard-topbar">
      <a class="dashboard-brand" href="/app/designed-dashboard" aria-label="Home" @click.prevent="navigate('/app/designed-dashboard')">
        <span class="dashboard-brand-mark">D</span>
        <span>Designed ERP</span>
      </a>
      <nav class="dashboard-top-links" aria-label="Dashboard navigation">
        <a class="active" href="/app/designed-dashboard" @click.prevent="navigate('/app/designed-dashboard')">Overview</a>
        <a href="/app/user-list" @click.prevent="navigate('/app/user-list')">Users</a>
        <a href="/app/designed-system-settings" @click.prevent="navigate('/app/designed-system-settings')">System Settings</a>
      </nav>
      <div class="dashboard-utilities" aria-label="Workspace tools"></div>
    </header>

    <section class="dashboard-welcome">
      <div>
        <p class="dashboard-eyebrow">WORKSPACE</p>
        <h1>Welcome back<span v-if="userName">, {{ userName }}</span></h1>
        <p class="dashboard-welcome-copy">Choose a workspace shortcut to get started.</p>
      </div>
      <button class="dashboard-home-button" type="button" @click="navigate('/app')">Frappe Home</button>
    </section>

    <section class="dashboard-groups" aria-label="ERP shortcuts">
      <article v-for="group in groups" :key="group.title" class="dashboard-group">
        <h2><span class="dashboard-group-icon">{{ group.icon }}</span>{{ group.title }}</h2>
        <a
          v-for="link in group.links"
          :key="link.label"
          :href="link.href"
          :class="{ 'dashboard-custom-link': link.custom }"
          @click.prevent="navigate(link.href)"
        >
          {{ link.label }}
        </a>
      </article>
    </section>

    <footer class="dashboard-footer">Designed Vue App · ERPNext Workspace</footer>
  </main>
</template>

<script>
const link = (label, href, custom = false) => ({ label, href, custom });
const list = (doctype) => `/app/${doctype.toLowerCase().replaceAll(' ', '-')}-list`;

export default {
  mounted() {
    const utilities = this.$el.querySelector('.dashboard-utilities');
    const navbar = document.querySelector('.sticky-top .navbar');
    const search = navbar?.querySelector('.collapse.navbar-collapse > form[role="search"]');
    const actions = navbar?.querySelector('.collapse.navbar-collapse > .navbar-nav');

    if (!utilities || !search || !actions) {
      throw new Error('Frappe search and account controls could not be added to the dashboard header.');
    }

    utilities.append(search, actions);
  },
  data() {
    return {
      userName: window.frappe?.session?.user_fullname || window.frappe?.session?.user || '',
      groups: [
        {
          title: 'Sales',
          icon: '◈',
          links: [
            link('Dashboard', '/app/selling'),
            link('Customer', list('Customer'), true),
            link('Quotation', list('Quotation'), true),
            link('Sales Order', list('Sales Order'), true),
            link('Delivery Note', list('Delivery Note'), true),
            link('Sales Invoice', list('Sales Invoice'), true)
          ]
        },
        {
          title: 'Project',
          icon: '▦',
          links: [
            link('Dashboard', '/app/projects'),
            link('Project', list('Project'), true),
            link('Task', list('Task'), true),
            link('Timesheet', list('Timesheet'), true)
          ]
        },
        {
          title: 'Purchase',
          icon: '▣',
          links: [
            link('Dashboard', '/app/buying'),
            link('Material Request', list('Material Request'), true),
            link('Request for Quotation', list('Request for Quotation'), true),
            link('Supplier Quotation', list('Supplier Quotation'), true),
            link('Purchase Order', list('Purchase Order'), true),
            link('Purchase Receipt', list('Purchase Receipt'), true),
            link('Purchase Invoice', list('Purchase Invoice'), true),
            link('Supplier', list('Supplier'), true)
          ]
        },
        {
          title: 'Inventory',
          icon: '◉',
          links: [
            link('Item', list('Item'), true),
            link('Item Price', list('Item Price'), true),
            link('Warehouse', list('Warehouse'), true),
            link('Stock Entry', list('Stock Entry'), true),
            link('Stock Reconciliation', list('Stock Reconciliation'), true)
          ]
        },
        {
          title: 'Accounts',
          icon: '▤',
          links: [
            link('Dashboard', '/app/accounting'),
            link('Sales Invoice', list('Sales Invoice'), true),
            link('Purchase Invoice', list('Purchase Invoice'), true),
            link('Payment Entry', list('Payment Entry'), true),
            link('Journal Entry', list('Journal Entry'), true),
            link('Account', list('Account'), true)
          ]
        },
        {
          title: 'Assets & Reports',
          icon: '▧',
          links: [
            link('Asset', list('Asset'), true),
            link('Asset Movement', list('Asset Movement'), true),
            link('Accounts Receivable', '/app/query-report/Accounts Receivable'),
            link('Accounts Payable', '/app/query-report/Accounts Payable'),
            link('Stock Balance', '/app/query-report/Stock Balance')
          ]
        },
        {
          title: 'System Settings',
          icon: '⚙',
          links: [
            link('Configuration directory', '/app/designed-system-settings', true),
            link('Company', list('Company'), true),
            link('Department', list('Department'), true),
            link('Warehouse', list('Warehouse'), true),
            link('Cost Center', list('Cost Center'), true),
            link('Bank', list('Bank'), true),
            link('Users', list('User'), true),
            link('Roles', list('Role'), true)
          ]
        }
      ]
    };
  },
  methods: {
    navigate(href) {
      window.location.assign(href);
    }
  }
};
</script>

<style scoped src="./style.css"></style>
