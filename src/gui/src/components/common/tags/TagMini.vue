<template>
  <v-chip
    label
    x-small
    dark
    left
    :class="[
      'mr-1',
      'px-1',
      'text-caption',
      'text-weight-bold',
      'text-uppercase',
      'tag-mini',
      {
        ai: type === 'ai',
        shared: type === 'shared'
      }
    ]"
  >
    <span v-if="type === 'ai'">AI</span>
    <v-icon v-if="type === 'shared'" x-small>$awakeShare</v-icon>
  </v-chip>
</template>

<script>
export default {
  name: 'TagMini',
  props: {
    type: String
  },
  data: () => ({}),
  computed: {}
}
</script>
