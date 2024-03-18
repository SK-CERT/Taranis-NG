<template>
    <v-container v-bind="UI.CARD.CONTAINER">
        <v-row>
            <v-col :class="UI.CLASS.card_offset">
                <v-hover v-slot="{hover}">
                    <v-card v-bind="UI.CARD.HOVER" :elevation="hover ? 12 : 2" @click.stop="cardItemToolbar">
                        <!--CONTENT-->
                        <v-layout v-bind="UI.CARD.LAYOUT" class="status">
                            <v-row v-bind="UI.CARD.ROW.CONTENT">
                                <v-col :style="UI.STYLE.card_tag">
                                    <v-icon center>{{card.tag}}</v-icon>
                                </v-col>
                                <v-col>
                                    <div class="grey--text">{{card.product_type_name}}</div>
                                    <span>{{card.title}}</span>
                                </v-col>
                                <v-col>
                                    <div class="grey--text">{{$t('card_item.description')}}</div>
                                    <span>{{card.subtitle}}</span>
                                </v-col>

                                <!--HOVER TOOLBAR-->
                                <v-col :style="UI.STYLE.card_hover_toolbar">
                                    <v-row v-if="hover" v-bind="UI.CARD.TOOLBAR.COMPACT" :style="UI.STYLE.card_toolbar">
                                        <v-col v-bind="UI.CARD.COL.TOOLS">
                                            <v-btn v-if="canDelete" icon class="red" @click.stop="toggleDeletePopup" :title="$t('publish.tooltip.delete_item')">
                                                <v-icon color="white">{{ UI.ICON.DELETE }}</v-icon>
                                            </v-btn>
                                        </v-col>
                                    </v-row>
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
        name: "CardProduct",
      components: {ConfirmDelete},
        props: ['card'],
        data:() => ({
            toolbar: false,
            showDeletePopup: false,
        }),
        mixins: [AuthMixin],
        computed: {
            canDelete() {
               return this.checkPermission(Permissions.PUBLISH_DELETE) && this.card.modify === true
            }
        },
        methods: {
            itemClicked(data) {
                this.$root.$emit('show-product-edit', data)
            },
            deleteClicked(data) {
                this.$root.$emit('delete-product', data)
            },
            buttonClicked() {

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