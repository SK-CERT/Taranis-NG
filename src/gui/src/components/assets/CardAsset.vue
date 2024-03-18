<template>
    <v-container v-bind="UI.CARD.CONTAINER">
        <v-row>
            <v-col :class="UI.CLASS.card_offset">
                <v-hover v-slot="{hover}">
                    <v-card v-bind="UI.CARD.HOVER" :elevation="hover ? 12 : 2" @click.stop="cardItemToolbar">
                        <!--CONTENT-->
                        <v-layout v-bind="UI.CARD.LAYOUT" :class="'status ' + itemStatus">
                            <v-row v-bind="UI.CARD.ROW.CONTENT">
                                <v-col :style="UI.STYLE.card_tag">
                                    <v-icon center>{{ card.tag }}</v-icon>
                                </v-col>
                                <v-col>
                                    <div class="grey--text">{{ $t('card_item.title') }}</div>
                                    <span>{{ card.title }}</span>
                                </v-col>
                                <v-col>
                                    <div class="grey--text ">{{ $t('card_item.description') }}</div>
                                    <span>{{ card.subtitle }}</span>
                                </v-col>

                                <!--HOVER TOOLBAR-->
                                <v-col :style="UI.STYLE.card_hover_toolbar">
                                    <v-row v-if="deleteAllowed() && hover" v-bind="UI.CARD.TOOLBAR.COMPACT" :style="UI.STYLE.card_toolbar">
                                        <v-col v-bind="UI.CARD.COL.TOOLS">
                                            <v-btn icon class="red" @click.stop="toggleDeletePopup">
                                                <v-icon color="white">{{ UI.ICON.DELETE }}</v-icon>
                                            </v-btn>
                                        </v-col>
                                    </v-row>
                                </v-col>

                                <!--FOOTER-->
                                <v-col cols="12" class="py-1">
                                    <v-btn v-if="card.vulnerabilities_count > 0" depressed x-small class="red white--text mr-1">
                                        {{ $t('asset.vulnerabilities_count') + card.vulnerabilities_count }}
                                    </v-btn>
                                    <v-btn v-if="card.vulnerabilities_count === 0" depressed x-small class="green white--text mr-1">
                                        {{ $t('asset.no_vulnerabilities') }}
                                    </v-btn>
                                </v-col>
                            </v-row>
                        </v-layout>
                    </v-card>
                </v-hover>
            </v-col>
        </v-row>
        <v-row>
          <ConfirmDelete class="justify-center" v-if="showDeletePopup" @confirm="handleDeletion"
                         @close="showDeletePopup = false"
          ></ConfirmDelete>
        </v-row>
    </v-container>
</template>

<script>
    import AuthMixin from "@/services/auth/auth_mixin";
    import Permissions from "@/services/auth/permissions";
    import ConfirmDelete from "@/components/common/ConfirmDelete.vue";

    export default {
        name: "CardAsset",
      components: {ConfirmDelete},
        props: {
            card: Object,
        },

        data: () => ({
            toolbar: false,
            selected: false,
            status: "in_progress",
            showDeletePopup: false,
        }),
        mixins: [AuthMixin],
        computed: {
            itemStatus() {
                if (this.card.vulnerabilities_count > 0) {
                    return "alert"
                } else {
                    return "completed"
                }
            }
        },
        methods: {
            itemClicked(data) {
                this.$root.$emit('show-edit', data);
            },
            deleteClicked(data) {
                this.$root.$emit('delete-asset', data)
            },
            deleteAllowed() {
                return this.checkPermission(Permissions.MY_ASSETS_CREATE)
            },
            cardItemToolbar(action) {
                switch (action) {
                    case "edit":
                        break;

                    case "delete":
                        this.deleteClicked(this.card);
                        break;

                    default:
                        this.toolbar = false;
                        this.itemClicked(this.card);
                        break;
                }
            },
            toggleDeletePopup() {
              this.showDeletePopup = !this.showDeletePopup;
            },
            handleDeletion() {
              this.showDeletePopup = false;
              this.cardItemToolbar('delete')
            }
        }
    }
</script>