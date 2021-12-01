<template>
    <v-hover v-slot:default="{hover}" close-delay="150">
        <v-card flat class="card mb-1" :elevation="hover ? 12 : 2"
                @click.stop="cardItemToolbar"
                @mouseenter.native="toolbar=true"
                @mouseleave.native="toolbar=false"
        >
            <v-layout row wrap class="pa-3 pl-0 status" v-bind:class="cardStatus()">
                <v-flex md1 class="obj center">
                    <div class="caption grey--text"><br/></div>
                    <div>
                        <v-icon center>{{ card.tag }}</v-icon>
                    </div>
                </v-flex>
                <v-flex md2>
                    <div class="caption grey--text">{{ $t('card_item.title') }}</div>
                    <div>{{ cardName }}</div>
                </v-flex>
                <v-flex md4>
                    <div class="caption grey--text">{{ $t('card_item.description') }}</div>
                    <div>{{ cardDescription }}</div>
                </v-flex>
                <v-flex md1 class="obj center">

                    <v-speed-dial
                        v-model="toolbar"
                        direction="left"
                        transition='slide-x-reverse-transition'
                    >

                        <v-btn v-if="!card.default && checkPermission(deletePermission)" fab x-small color="red"
                               @click.stop="cardItemToolbar('delete')">
                            <v-icon color="white">mdi-trash-can-outline</v-icon>
                        </v-btn>
                    </v-speed-dial>
                </v-flex>
            </v-layout>

        </v-card>
    </v-hover>
</template>

<script>

import AuthMixin from "@/services/auth/auth_mixin";

export default {
    name: "CardGroup",
    props: ['card', 'deletePermission'],
    mixins: [AuthMixin],
    data: () => ({
        toolbar: false
    }),
    computed: {
        cardName() {
            if (this.card.default) {
                return this.$t('osint_source_group.default_group')
            } else {
                return this.card.name
            }
        },
        cardDescription() {
            if (this.card.default) {
                return this.$t('osint_source_group.default_group_description')
            } else {
                return this.card.desc
            }
        }
    },
    methods: {
        itemClicked(data) {
            this.$root.$emit('show-edit', data)
        },
        deleteClicked(data) {
            this.$root.$emit('delete-item', data)
        },
        cardItemToolbar(action) {
            switch (action) {
                case "delete":
                    this.deleteClicked(this.card)
                    break;

                default:
                    this.toolbar = false;
                    this.itemClicked(this.card);
                    break;
            }
        },
        cardStatus: function () {
            if (this.card.status === undefined) {
                return "status-green"
            } else {
                return "status-" + this.card.status
            }
        }
    }
}
</script>

<style>
.card .status.status-orange {
    border-left: 4px solid #ffd556;
}

.card .status.status-green {
    border-left: 4px solid #33DD40;
}

.card .status.status-red {
    border-left: 4px solid red;
}

.card .obj.center {
    text-align: center;
}

.card.elevation-12 {
    z-index: 1;
    background-color: rgba(100, 137, 214, 0.1);
}
</style>
