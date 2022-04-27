<template>
    <v-card tile elevation="4" outlined height="100%" class="pa-5 align-self-stretch">
        <v-container column style="height: 100%">

            <v-row no-gutters style="height: 100%">
                <v-col class="d-flex flex-column" align-self="start" style="height: 100%">

                    <!-- Header -->

                    <v-row class="flex-grow-0">
                        <v-col cols="auto" class="mr-auto mt-1" order-sm="2" order-md="1">
                            <tag-mini label="AI"/>
                            <span class="text-caption font-weight-light main-text-color--text">Last activity: </span>
                            <span class="text-caption font-weight-bold main-text-color--text">March, 15, 2022</span>
                        </v-col>

                        <v-col cols="auto" order-sm="1" order-md="2">
                            <v-btn fab depressed x-small dark color="primary" class="fab-pin">
                                <!-- <v-icon>mdi-pin-outline</v-icon> -->
                                <v-icon>$awakePin</v-icon>
                            </v-btn>
                        </v-col>
                    </v-row>

                    <!-- Title -->
            
                    <v-row class="flex-grow-0">
                        <v-col>
                            <h2 class="font-weight-bold headline main-text-color--text">
                                {{ title }}
                            </h2>
                        </v-col>
                    </v-row>

                    <v-row class="flex-grow-0">
                        <v-col>
                            <tag-list :tags="topic.tags" />
                        </v-col>
                    </v-row>
                    
                    <!-- Excerpt -->
            
                    <v-row class="flex-grow-0">
                        <v-col>
                            <p class="font-weight-light main-text-color--text">
                                {{ topic.summary }}
                            </p>
                        </v-col>
                    </v-row>

                    <!-- spacer -->

                    <v-spacer></v-spacer>

                    <!-- Footer -->

                    <v-row no-gutter wrap align="center" justify="end" class="flex-grow-0">
                        <v-col md="12" lg="8" class="mx-0 d-flex justify-start">
                            <v-container class="mx-0 pa-0">
                                <v-row class="mx-0">
                                    <v-col sm="6" class="pa-0 pt-0 pr-1">
                                        <v-icon left small>mdi-file-outline</v-icon>
                                        <span class="text-caption font-weight-light main-text-color--text">92 /</span> 
                                        <span class="text-caption font-weight-bold main-text-color--text">35</span> 
                                    </v-col>
                                    <v-col sm="6" class="pa-0 pt-0 pr-1">
                                        <v-icon left small color="awake-green-color">mdi-arrow-up-circle-outline</v-icon>
                                        <span class="text-caption font-weight-light main-text-color--text">356</span> 
                                    </v-col>
                                    <v-col sm="6" class="pa-0 pt-0 pr-1">
                                        <v-icon left small>mdi-message-outline</v-icon>
                                        <span class="text-caption font-weight-light main-text-color--text">92 /</span> 
                                        <span class="text-caption font-weight-bold main-text-color--text">35</span> 
                                    </v-col>
                                    <v-col sm="6" class="pa-0 pt-0 pr-1">
                                        <v-icon left small color="awake-red-color">mdi-arrow-down-circle-outline</v-icon>
                                        <span class="text-caption font-weight-light main-text-color--text">92</span> 
                                    </v-col>
                                </v-row>
                            </v-container>
                        </v-col>
                        <v-col md="12" lg="4" class="mx-0 d-flex justify-end">
                            <v-btn outlined class="text-lowercase btn-view-topic mt-1">
                                <v-icon left>mdi-eye-outline</v-icon>
                                view topic
                            </v-btn>
                        </v-col>
                    </v-row>


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
  props: {
    title: String,
    topic: {}
  },
  data: () => ({
  }),
  methods: {
  }
}
</script>
