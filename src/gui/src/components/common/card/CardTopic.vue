<template>
    <v-card tile elevation="4" outlined class="pa-5">
        <v-container>
        
        <v-row>
            <v-col cols="auto" class="mr-auto">
                <tag-mini label="AI"/>
                <span class="text-caption text-weight-light main-text-color--text">Last activity: </span>
                <span class="text-caption text-weight-bold main-text-color--text">March, 15, 2022</span>
            </v-col>

            <v-col cols="auto">
                <v-btn fab depressed x-small dark color="primary" class="fab-pin">
                    <v-icon>favorite</v-icon>
                </v-btn>
            </v-col>
        </v-row>
      
        <v-row>
            <v-col>
                <p class="font-weight-bold headline main-text-color--text">
                    Ukraine
                </p>
            </v-col>
        </v-row>

        <v-row>
            <v-col>
                <tag-list :tags="tags" />
            </v-col>
        </v-row>
        
      
        <v-row>
            <v-col>
                <p class="font-weight-light main-text-color--text">
                    Cyber conflicts are fought in the shadows, but in the case
                    of Russia's invasion of Ukraine, it is a group that calls itself
                    Anonymous that has made the most public declaration of
                    war. Late on Thursday the hacker collective tweeted from
                    an account linked to Anonymous, @YourAnonOne, that it
                    had Vladimir Putin's regime in its sights. Anonymous also...
                </p>
            </v-col>
        </v-row>

        </v-container>
    </v-card>
</template>

<script>
import TagMini from '@/components/common/tags/TagMini'
import TagList from '@/components/common/tags/TagList'

export default {
  name: 'CardTopic',
  components: {
    TagMini,
    TagList
  },
  data: () => ({
      tags: [ 
          {label: 'OT/CPS'}, 
          {label: 'Siemens'}, 
          {label: 'Information Disclosure'}
          ]
  }),
  methods: {
  }
}
</script>
