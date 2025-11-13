<template>
    <v-row v-bind="UI.DIALOG.ROW.WINDOW">
        <v-btn v-bind="UI.BUTTON.ADD_NEW" v-if="add_button && canCreate" @click="addProduct">
            <v-icon left>{{ UI.ICON.PLUS }}</v-icon>
            <span>{{ $t('common.add_btn') }}</span>
        </v-btn>

        <v-dialog v-bind="UI.DIALOG.FULLSCREEN" v-model="visible" new-product>
            <v-card v-bind="UI.DIALOG.BASEMENT">
                <v-toolbar v-bind="UI.DIALOG.TOOLBAR" :style="UI.STYLE.z10000">
                    <v-btn v-bind="UI.BUTTON.CLOSE_ICON" @click="cancel">
                        <v-icon>{{ UI.ICON.CLOSE }}</v-icon>
                    </v-btn>

                    <v-toolbar-title>
                        <span v-if="!edit">{{ $t('product.add_new') }}</span>
                        <span v-else>{{ $t('product.edit') }}</span>
                    </v-toolbar-title>
                    <v-spacer></v-spacer>
                    <v-select :key="`state-select-${selectedState}`" :disabled="!canModify"
                        style="padding-top:25px; min-width: 100px; max-width: 200px;" v-model="selectedState"
                        :items="availableStates"
                        :item-text="item => $te('workflow.states.' + item.display_name) ? $t('workflow.states.' + item.display_name) : item.display_name"
                        item-value="display_name" :label="$t('product.state')" append-icon="mdi-chevron-down"
                        :menu-props="{ maxWidth: '300px' }" @change="onStateChange">

                        <template v-slot:item="{ item }">
                            <v-list-item-avatar>
                                <v-icon :color="item.color">{{ item.icon }}</v-icon>
                            </v-list-item-avatar>
                            <v-list-item-content>
                                <v-list-item-title>{{ $te('workflow.states.' + item.display_name) ?
                                    $t('workflow.states.' + item.display_name) : item.display_name
                                }}</v-list-item-title>
                                <v-list-item-subtitle>{{ item.description }}</v-list-item-subtitle>
                            </v-list-item-content>
                        </template>
                    </v-select>
                    <v-btn v-if="!edit && canModify" text dark type="submit" form="form">
                        <v-icon left>mdi-content-save</v-icon>
                        <span>{{ $t('common.save') }}</span>
                    </v-btn>
                </v-toolbar>

                <v-form @submit.prevent="add" id="form" ref="form" class="px-4">
                    <v-row no-gutters>
                        <v-col cols="6" class="pr-3">
                            <v-combobox v-on:change="productSelected" :disabled="!canModify" v-model="selected_type"
                                :items="product_types" item-text="title" :label="$t('product.report_type')"
                                name="report_type" v-validate="'required'" @blur="onBlur('product_type')" />
                        </v-col>
                        <v-col cols="6" class="pr-3">
                            <v-text-field :disabled="!canModify" :label="$t('product.title')" name="title" type="text"
                                v-model="product.title" v-validate="'required'" data-vv-name="title"
                                :error-messages="errors.collect('title')" :spellcheck="$store.state.settings.spellcheck"
                                @blur="onBlur('title')" @keyup="onKeyUp('title')" />
                        </v-col>
                        <v-col cols="12" class="pr-3">
                            <v-textarea :disabled="!canModify" :label="$t('product.description')" name="description"
                                v-model="product.description" :spellcheck="$store.state.settings.spellcheck"
                                @blur="onBlur('description')" @keyup="onKeyUp('description')" />
                        </v-col>
                    </v-row>
                    <v-row no-gutters>
                        <v-col cols="12" class="mb-2">
                            <v-btn v-bind="UI.BUTTON.ADD_NEW_IN" v-if="canModify"
                                @click="$refs.report_item_selector.openSelector()">
                                <v-icon left>{{ UI.ICON.PLUS }}</v-icon>
                                <span>{{ $t('report_item.select') }}</span>
                            </v-btn>
                        </v-col>
                        <v-col cols="12">
                            <ReportItemSelector ref="report_item_selector" :values="report_items" :modify="modify"
                                :edit="edit" />
                        </v-col>
                    </v-row>
                    <v-row no-gutters>
                        <v-col cols="12">
                            <v-checkbox v-for="preset in publisher_presets" :key="preset.id" :label="preset.name"
                                :disabled="!canModify" v-model="preset.selected">
                            </v-checkbox>
                        </v-col>
                    </v-row>
                    <v-row no-gutters class="pt-4">
                        <v-col cols="6">
                            <v-btn :href="preview_link" style="display: none" target="_blank" ref="previewBtn">
                            </v-btn>
                            <v-btn depressed small @click="previewProduct($event)">
                                <v-icon left>mdi-eye-outline</v-icon>
                                <span>{{ $t('product.preview') }}</span>
                            </v-btn>
                        </v-col>
                        <v-col cols="6">
                            <v-btn v-if="canPublish" depressed small @click="publishConfirmation">
                                <v-icon left>mdi-send-outline</v-icon>
                                <span>{{ $t('product.publish') }}</span>
                            </v-btn>
                        </v-col>
                    </v-row>
                    <v-row>
                        <MessageBox class="justify-center" v-if="msgbox_visible" @buttonYes="publishProduct"
                            @buttonCancel="msgbox_visible = false" :title="$t('product.publish_confirmation')"
                            :message="product.title">
                        </MessageBox>
                    </v-row>

                    <v-row no-gutters class="pt-2">
                        <v-col cols="12">
                            <v-alert v-if="show_validation_error" dense type="error" text>
                                {{ $t('error.validation') }}
                            </v-alert>
                            <v-alert v-if="show_error" dense type="error" text>
                                {{ $t('report_item.error') }}
                            </v-alert>
                        </v-col>
                    </v-row>

                </v-form>
            </v-card>
        </v-dialog>
    </v-row>
</template>

<script>
import AuthMixin from "../../services/auth/auth_mixin";
import { createProduct, publishProduct, updateProduct } from "@/api/publish";
import { getEntityTypeStates, getEntityStates, setEntityState, removeEntityState } from "@/api/state";
import ReportItemSelector from "@/components/publish/ReportItemSelector";
import Permissions from "@/services/auth/permissions";
import MessageBox from "@/components/common/MessageBox.vue";

export default {
    name: "NewProduct",
    components: { ReportItemSelector, MessageBox },
    props: { add_button: Boolean },
    data: () => ({
        visible: false,
        show_validation_error: false,
        edit: false,
        show_error: false,
        modify: false,
        access: false,
        product_types: [],
        publisher_presets: [],
        selected_type: null,
        report_items: [],
        preview_link: "",
        product: {
            id: -1,
            title: "",
            description: "",
            product_type_id: null,
            report_items: [],
        },
        msgbox_visible: false,
        key_timeout: null,
        // State management
        availableStates: [],
        selectedState: null,
        currentEntityState: null,
    }),
    mixins: [AuthMixin],
    watch: {
        // Remove double scrollbars on product when report items selector is open/closed
        // This bug exist across mulitple places in Taranis (search for tag: DOUBLE_SCROLLBAR).
        visible(val) {
            if (val) {
                document.documentElement.style.overflow = 'hidden'
            }
            else {
                document.documentElement.style.overflow = 'auto'
            }
        }
    },
    computed: {
        canCreate() {
            return this.checkPermission(Permissions.PUBLISH_CREATE)
        },

        canModify() {
            return this.edit === false || (this.checkPermission(Permissions.PUBLISH_UPDATE) && this.modify === true)
        },

        canPublish() {
            return this.publisher_presets.length > 0 && (this.edit === false || (this.checkPermission(Permissions.PUBLISH_PRODUCT) && this.access === true))
        }
    },
    methods: {
        addProduct() {
            this.visible = true;
            this.edit = false;
            this.show_error = false;
            this.modify = false;
            this.access = false;
            this.selected_type = null;
            this.report_items = [];
            this.product.id = -1;
            this.product.title = "";
            this.product.description = "";
            this.product.product_type_id = null;
            this.product.report_items = [];
            this.selectedState = null;
            this.currentEntityState = null;
            this.resetValidation();

            // Auto-select default state if available
            this.selectDefaultStates();
        },

        publishConfirmation() {
            this.msgbox_visible = true;
        },

        publishProduct() {
            this.msgbox_visible = false;
            for (let i = 0; i < this.publisher_presets.length; i++) {
                if (this.publisher_presets[i].selected) {
                    this.$validator.validateAll().then(() => {

                        if (!this.$validator.errors.any()) {

                            this.show_validation_error = false;
                            this.show_error = false;

                            this.product.product_type_id = this.selected_type.id;

                            this.product.report_items = [];
                            for (let i = 0; i < this.report_items.length; i++) {
                                this.product.report_items.push(
                                    {
                                        id: this.report_items[i].id
                                    }
                                )
                            }

                            if (this.product.id !== -1) {
                                updateProduct(this.product).then(() => {

                                    this.resetValidation();
                                    publishProduct(this.product.id, this.publisher_presets[i].id)
                                })
                            } else {
                                createProduct(this.product).then((response) => {

                                    this.resetValidation();
                                    this.product.id = response.data
                                    publishProduct(this.product.id, this.publisher_presets[i].id)
                                })
                            }

                        } else {

                            this.show_validation_error = true;
                        }
                    })
                }
            }
        },

        productSelected() {

        },

        cancel() {
            this.resetValidation();
            this.visible = false
        },

        previewProduct(event) {
            this.$validator.validateAll().then(() => {

                if (!this.$validator.errors.any()) {

                    this.show_validation_error = false;
                    this.show_error = false;

                    this.product.product_type_id = this.selected_type.id;

                    this.product.report_items = [];
                    for (let i = 0; i < this.report_items.length; i++) {
                        this.product.report_items.push(
                            {
                                id: this.report_items[i].id
                            }
                        )
                    }

                    const getPreviewUrl = (product) => {
                        let url = ((typeof (process.env.VUE_APP_TARANIS_NG_CORE_API) == "undefined") ? "$VUE_APP_TARANIS_NG_CORE_API" : process.env.VUE_APP_TARANIS_NG_CORE_API) + "/publish/products/" + product + "/overview?jwt=" + this.$store.getters.getJWT;
                        if (event && event.ctrlKey) url += '&ctrl=1';
                        return url;
                    };

                    if (this.product.id !== -1) {
                        updateProduct(this.product).then(() => {

                            this.resetValidation();
                            this.preview_link = getPreviewUrl(this.product.id);
                            this.$nextTick(() => {
                                this.$refs.previewBtn.$el.click();
                            });
                        })
                    } else {
                        createProduct(this.product).then((response) => {

                            this.product.id = response.data
                            this.resetValidation();
                            this.preview_link = getPreviewUrl(response.data);
                            this.$nextTick(() => {
                                this.$refs.previewBtn.$el.click();
                            });
                        })
                    }

                } else {

                    this.show_validation_error = true;
                }
            })
        },

        add() {
            this.$validator.validateAll().then(() => {

                if (!this.$validator.errors.any()) {

                    this.show_validation_error = false;
                    this.show_error = false;

                    this.product.product_type_id = this.selected_type.id;

                    this.product.report_items = [];
                    for (let i = 0; i < this.report_items.length; i++) {
                        this.product.report_items.push(
                            {
                                id: this.report_items[i].id
                            }
                        )
                    }

                    if (this.product.id !== -1) {
                        updateProduct(this.product).then(() => {

                            this.resetValidation();
                            this.visible = false;

                            this.$root.$emit('notification',
                                {
                                    type: 'success',
                                    loc: 'product.successful_edit'
                                }
                            )
                        }).catch(() => {

                            this.show_error = true;
                        })
                    } else {
                        createProduct(this.product).then(async (response) => {
                            // Set the new product ID
                            this.product.id = response.data;

                            // Apply default state to the new product if one is selected
                            if (this.selectedState) {
                                try {
                                    await setEntityState('product', this.product.id, this.selectedState);
                                } catch (error) {
                                    console.error('Failed to apply default state to new product:', error);
                                }
                            }

                            this.resetValidation();
                            this.visible = false;

                            this.$root.$emit('notification',
                                {
                                    type: 'success',
                                    loc: 'product.successful'
                                }
                            )

                        }).catch(() => {

                            this.show_error = true;
                        })
                    }
                } else {

                    this.show_validation_error = true;
                }
            })
        },

        resetValidation() {
            this.$validator.reset();
            this.show_validation_error = false;
        },

        onBlur(field_id) {
            if (this.edit === true) {
                this.autoSave(field_id);
            }
        },

        onKeyUp(field_id) {
            if (this.edit === true) {
                clearTimeout(this.key_timeout);
                let self = this;
                this.key_timeout = setTimeout(function () {
                    self.autoSave(field_id);
                }, 1000);
            }
        },

        autoSave(field_id) {
            if (this.edit === true && this.product.id !== -1) {
                // Update the product type ID if needed
                if (this.selected_type) {
                    this.product.product_type_id = this.selected_type.id;
                }

                // Update report items
                this.product.report_items = [];
                for (let i = 0; i < this.report_items.length; i++) {
                    this.product.report_items.push({
                        id: this.report_items[i].id
                    });
                }

                updateProduct(this.product).then(() => {
                    // Silent auto-save, no notification
                }).catch(() => {
                    this.show_error = true;
                });
            }
        },

        // State management methods
        async loadAvailableStates() {
            try {
                console.log('[DEBUG] Loading available states for product');
                const response = await getEntityTypeStates('product');
                this.availableStates = response.data.states;
                console.log('[DEBUG] Available states loaded:', this.availableStates);

                // Auto-select default state after loading states (for new products)
                if (!this.edit) {
                    this.selectDefaultStates();
                }
            } catch (error) {
                console.error('Failed to load available states:', error);
                this.availableStates = [];
            }
        },

        selectDefaultStates() {
            if (!this.availableStates) return;

            const defaultState = this.availableStates.find(state => state.is_default);

            if (defaultState) {
                console.log('[DEBUG] Setting default state for product:', defaultState.display_name);
                this.selectedState = defaultState.display_name;
            }
        },

        async loadCurrentStates() {
            if (!this.edit || !this.product.id || this.product.id === -1) return;

            console.log('[DEBUG] Loading current states for product', this.product.id);
            try {
                const response = await getEntityStates('product', this.product.id);
                const states = response.data.states || response.data || [];
                // For single state, get the first state if any
                this.currentEntityState = states.length > 0 ? states[0] : null;
                this.selectedState = this.currentEntityState ? this.currentEntityState.display_name : null;
                console.log('[DEBUG] Current state loaded:', {
                    currentEntityState: this.currentEntityState,
                    selectedState: this.selectedState
                });
            } catch (error) {
                console.error('Failed to load current states:', error);
                this.currentEntityState = null;
                this.selectedState = null;
            }
        },

        async onStateChange() {
            console.log('[DEBUG] onStateChange called', {
                edit: this.edit,
                productId: this.product.id,
                selectedState: this.selectedState,
                currentEntityState: this.currentEntityState
            });

            // For new items, just store the selection - it will be applied when the item is created
            if (!this.edit) {
                console.log('[DEBUG] New item mode - storing selected state for later application');
                return;
            }

            if (!this.product.id || this.product.id === -1) {
                console.log('[DEBUG] Skipping state change - no product ID');
                return;
            }

            try {
                // Get current state name
                const currentStateName = this.currentEntityState ? this.currentEntityState.display_name : null;

                // Determine state changes
                console.log('[DEBUG] State changes', {
                    currentStateName,
                    newState: this.selectedState
                });

                if (this.selectedState !== currentStateName) {
                    console.log('[DEBUG] Sending state change request');
                    // Use new single state API
                    if (this.selectedState) {
                        await setEntityState('product', this.product.id, this.selectedState);
                    } else {
                        await removeEntityState('product', this.product.id);
                    }

                    // Reload current states to get updated data
                    await this.loadCurrentStates();

                    // Emit update event for real-time sync with full state objects
                    const selectedStateObject = this.selectedState ?
                        this.availableStates.find(state => state.display_name === this.selectedState) : null;

                    this.$root.$emit('product-states-updated', {
                        product_id: this.product.id,
                        state: this.selectedState,
                        state_object: selectedStateObject
                    });
                }
            } catch (error) {
                console.error('Failed to update states:', error);
                // Revert changes on error
                await this.loadCurrentStates();
            }
        },
    },
    async mounted() {
        // Load available states for products
        await this.loadAvailableStates();

        this.$root.$on('new-product', (data) => {
            this.visible = true;
            this.selected_type = null;
            this.report_items = data
        });

        this.$store.dispatch('getAllUserProductTypes', { search: '' }).then(() => {
            this.product_types = this.$store.getters.getProductTypes.items
        });

        this.$store.dispatch('getAllUserPublishersPresets', { search: '' }).then(() => {
            this.publisher_presets = this.$store.getters.getProductsPublisherPresets.items;
            for (let i = 0; i < this.publisher_presets.length; i++) {
                this.publisher_presets.selected = false
            }
        });

        this.$root.$on('show-product-edit', async (data) => {
            this.visible = true;
            this.edit = true;
            this.modify = data.modify;
            this.access = data.access;
            this.show_error = false;

            this.selected_type = null;
            this.report_items = data.report_items;

            this.product.id = data.id;
            this.product.title = data.title;
            this.product.description = data.description;
            this.product.product_type_id = data.product_type_id;

            // Load current states for this product
            await this.loadCurrentStates();

            for (let i = 0; i < this.product_types.length; i++) {
                if (this.product_types[i].id === this.product.product_type_id) {
                    this.selected_type = this.product_types[i];
                    break;
                }
            }

            this.preview_link = ((typeof (process.env.VUE_APP_TARANIS_NG_CORE_API) == "undefined") ? "$VUE_APP_TARANIS_NG_CORE_API" : process.env.VUE_APP_TARANIS_NG_CORE_API) + "/publish/products/" + data.id + "/overview?jwt=" + this.$store.getters.getJWT
        });
    },
    beforeDestroy() {
        this.$root.$off('new-product')
        this.$root.$off('show-product-edit')
    },
}
</script>
