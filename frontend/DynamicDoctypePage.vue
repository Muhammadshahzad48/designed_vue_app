<template>
  <TransactionPage
    v-if="doctype"
    :doctype="doctype"
    :initial-name="initialName"
  />
  <main v-else class="item-page">
    <p class="form-options-error" role="alert">A DocType is required to open this page.</p>
  </main>
</template>

<script>
import TransactionPage from './TransactionPage.vue';

const query = new URLSearchParams(window.location.search);

export default {
  components: { TransactionPage },
  data() {
    return {
      doctype: query.get('doctype') || '',
      initialName: query.get('name') || ''
    };
  }
};
</script>
