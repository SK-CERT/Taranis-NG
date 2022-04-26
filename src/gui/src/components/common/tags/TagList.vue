<template>
  <div>
      <v-btn 
        v-for="tag in tags" :key="tag.label"
          depressed 
          small dark left>
          {{ tag.label }}
      </v-btn>
  </div>
</template>

<script>
export default {
  name: 'TagList',
  props: {
    tags: []
  },
  data: () => ({
  }),
  computed: {
  }
}
</script>
