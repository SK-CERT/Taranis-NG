<template>
  <div>
  <ConfigTable
    :addButton="true"
    :items="node_items"
    :headerFilter="['tag', 'name', 'title', 'description', 'id']"
    @delete-item="deleteItem"
    @edit-item="editItem"
    @add-item="addItem"
  />
  <template v-if="false">
    <EditNode></EditNode>
  </template>
</div>
</template>

<script>
import EditNode from '../../components/config/nodes/EditNode'
import ConfigTable from '../../components/config/ConfigTable'
import { mapActions, mapGetters } from 'vuex'

export default {
  name: 'Nodes',
  components: {
    ConfigTable,
    EditNode
  },
  methods: {
    ...mapActions('config', [
      'loadNodes'
    ]),
    ...mapActions(['updateItemCount']),
    ...mapGetters('config', [
      'getNodes'
    ])
  },
  data: () => ({
    total_nodes: 0,
    node_items: []
  }),
  mounted () {
    var filter = { search: '' }
    this.loadNodes(filter).then(() => {
      this.node_items = this.getNodes().items
      this.total_nodes = this.node_items.length
      this.updateItemCount({ total: this.total_nodes, filtered: this.total_nodes })
    })
  },
  beforeDestroy () {
    this.$root.$off('delete-item')
  }
}

</script>
