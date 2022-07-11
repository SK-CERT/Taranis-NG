<template>
  <div>
      <v-chip
        v-for="(tag, i) in tags.slice(0, limit)"
        :key="i"
        label
        class="mr-1 mb-1 topic-label"
        dark
        x-small
        :color="labelcolor(i)"
        >
          {{ tag }}
      </v-chip>
  </div>
</template>

<script>
export default {
  name: 'TagList',
  props: {
    tags: [],
    limit: 5
  },
  data: () => ({
  }),
  methods: {
    labelcolor: function (i) {
      var colorList = [
        '#DCE868',
        '#DDBC42',
        '#D3802B',
        '#BB432B',
        '#AC004B',
        '#A0062F',
        '#8F1616',
        '#B0309A',
        '#9752CB'
      ]
      return colorList[i % colorList.length]
    }
  }
}
</script>
