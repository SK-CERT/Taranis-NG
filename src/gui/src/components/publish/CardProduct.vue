<template>
    <v-container v-bind="UI.CARD.CONTAINER">
        <v-row>
            <v-col :class="UI.CLASS.card_offset">
                <v-hover v-slot="{ hover }">
                    <v-card v-bind="UI.CARD.HOVER" :elevation="hover ? 12 : 2" @click.stop="cardItemToolbar">
                        <!--CONTENT-->
                        <v-layout v-bind="UI.CARD.LAYOUT" class="status">
                            <v-row v-bind="UI.CARD.ROW.CONTENT">
                                <v-col :style="UI.STYLE.card_tag">
                                    <v-icon center>{{ card.tag }}</v-icon>
                                </v-col>
                                <v-col>
                                    <div class="grey--text">{{ card.product_type_name }}</div>
                                    <span>{{ card.title }}</span>
                                </v-col>
                                <v-col>
                                    <div v-if="currentStateObject" class="d-flex align-center">
                                        <v-icon :color="currentStateObject.color" small class="mr-2">{{
                                            currentStateObject.icon }}</v-icon>
                                        <span>{{ $te('workflow.states.' + currentStateObject.display_name) ?
                                            $t('workflow.states.' +
                                                currentStateObject.display_name) : currentStateObject.display_name }}</span>
                                    </div>
                                </v-col>
                                <v-col>
                                    <div class="grey--text">{{ $t('card_item.description') }}</div>
                                    <span>{{ card.subtitle }}</span>
                                </v-col>

                                <!--HOVER TOOLBAR-->
                                <v-col :style="UI.STYLE.card_hover_toolbar">
                                    <v-row v-if="hover" v-bind="UI.CARD.TOOLBAR.COMPACT" :style="UI.STYLE.card_toolbar">
                                        <v-col v-bind="UI.CARD.COL.TOOLS">
                                            <v-btn v-if="canDelete" icon class="red" @click.stop="showMsgBox"
                                                :title="$t('publish.tooltip.delete_item')">
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
            <MessageBox class="justify-center" v-if="msgbox_visible" @buttonYes="handleMsgBox"
                @buttonCancel="msgbox_visible = false" :title="$t('common.messagebox.delete')" :message="card.title">
            </MessageBox>
        </v-row>
    </v-container>
</template>

<script>
import AuthMixin from "@/services/auth/auth_mixin";
import Permissions from "@/services/auth/permissions";
import MessageBox from "@/components/common/MessageBox.vue";

export default {
    name: "CardProduct",
    components: { MessageBox },
    props: ['card'],
    data: () => ({
        toolbar: false,
        msgbox_visible: false,
    }),
    mixins: [AuthMixin],
    computed: {
        canDelete() {
            return this.checkPermission(Permissions.PUBLISH_DELETE) && this.card.modify === true
        },

        currentStateObject() {
            // Get the first state object from the states array
            if (this.card.states && this.card.states.length > 0) {
                return this.card.states[0];
            }
            return null;
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
        showMsgBox() {
            this.msgbox_visible = true;
        },
        handleMsgBox() {
            this.msgbox_visible = false;
            this.cardItemToolbar('delete')
        },

        handleStateUpdate(data) {
            // Update card states when states are changed via SSE or NewProduct
            const targetId = data.product_id || data.entity_id;
            if (targetId === this.card.id) {
                console.log('Updating states for product', targetId, data);

                // Handle single state update
                if (data.state_object) {
                    // Single state object provided
                    this.card.states = [data.state_object];
                } else if (data.state) {
                    // Single state name provided, create minimal state object
                    const availableState = this.$parent && this.$parent.availableStates &&
                        this.$parent.availableStates.find(state => state.display_name === data.state);
                    if (availableState) {
                        this.card.states = [availableState];
                    } else {
                        // Create minimal object with just the state name
                        this.card.states = [{
                            name: data.state,
                            display_name: data.state,
                            color: '#9E9E9E', // Default grey color
                            icon: 'mdi-circle' // Default icon
                        }];
                    }
                } else if (data.state_objects && Array.isArray(data.state_objects)) {
                    // Backward compatibility: multiple state objects (use first)
                    this.card.states = data.state_objects.slice(0, 1);
                } else if (data.stateObjects && Array.isArray(data.stateObjects)) {
                    // Backward compatibility: stateObjects (use first)
                    this.card.states = data.stateObjects.slice(0, 1);
                } else if (data.states && Array.isArray(data.states)) {
                    // Backward compatibility: state names array (use first)
                    const stateName = data.states[0];
                    if (stateName) {
                        const availableState = this.$parent && this.$parent.availableStates &&
                            this.$parent.availableStates.find(state => state.display_name === stateName);
                        if (availableState) {
                            this.card.states = [availableState];
                        } else {
                            this.card.states = [{
                                name: stateName,
                                display_name: stateName,
                                color: '#9E9E9E',
                                icon: 'mdi-circle'
                            }];
                        }
                    } else {
                        this.card.states = [];
                    }
                } else {
                    // No state data provided, clear states
                    this.card.states = [];
                }

                // Force Vue reactivity update
                this.$forceUpdate();
            }
        }
    },
    mounted() {
        this.$root.$on('product-states-updated', this.handleStateUpdate);
        this.$root.$on('report-item-updated', this.handleStateUpdate);
    },
    beforeDestroy() {
        this.$root.$off('product-states-updated', this.handleStateUpdate);
        this.$root.$off('report-item-updated', this.handleStateUpdate);
    }
}
</script>
