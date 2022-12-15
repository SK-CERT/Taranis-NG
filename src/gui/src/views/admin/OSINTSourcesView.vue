<template>
  <div>
    <ConfigTable
      :addButton="true"
      :items="osint_sources"
      groupByItem="collector_type"
      @delete-item="deleteItem"
      @edit-item="editItem"
      @add-item="addItem"
    />
    <template v-if="false">
      <NewOSINTSource></NewOSINTSource>
    </template>
  </div>
</template>

<script>
import ConfigTable from '../../components/config/osint_sources/ConfigTable'
import NewOSINTSource from '../../components/config/osint_sources/NewOSINTSource'
import { deleteOSINTSource } from '@/api/config'
import { mapActions, mapGetters } from 'vuex'

export default {
  name: 'OSINTSources',
  components: {
    ConfigTable,
    NewOSINTSource
  },
  data: () => ({
    osint_sources: [],
    dialog: true
  }),
  methods: {
    ...mapActions('assess', ['updateOSINTSources']),
    ...mapGetters('assess', ['getOSINTSources']),
    ...mapActions(['updateItemCount']),
    deleteItem(item) {
      if (!item.default) {
        deleteOSINTSource(item)
      }
    },
    addItem() {
      this.dialog = true
    },
    editItem(item) {
      this.dialog = true
    }
  },
  mounted () {
    this.updateOSINTSources().then(() => {
      this.osint_sources = this.getOSINTSources().items
    })
  },
  beforeDestroy () {
    this.$root.$off('delete-item')
  }
}
</script>
