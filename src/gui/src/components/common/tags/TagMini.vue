<template>
    <v-btn 
        depressed 
        x-small dark left mx="1"
        class="text-caption text-weight-bold text-uppercase tag-mini">
        {{ label }}
    </v-btn>
</template>

<script>
export default {
  name: 'TagMini',
  props: {
    label: String
  },
  data: () => ({
  }),
  computed: {
  }
}
</script>
