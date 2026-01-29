<template>
    <v-row v-bind="UI.DIALOG.ROW.WINDOW">
        <v-btn v-bind="UI.BUTTON.ADD_NEW" v-if="add_button && canCreate" @click="addEmptyProduct">
            <v-icon left>{{ UI.ICON.PLUS }}</v-icon>
            <span>{{ $t('common.add_btn') }}</span>
        </v-btn>

        <v-dialog v-bind="UI.DIALOG.FULLSCREEN" v-model="visible" @keydown.esc="cancel" new-product>
            <MessageBox v-model="showCloseConfirmation" :title="$t('confirm_close.title')"
                :message="$t('product.confirm_close.message')" :buttons="confirmCloseButtons"
                :icon="{ name: 'mdi-help-circle', color: 'warning' }" @continue="showCloseConfirmation = false"
                @save="saveAndClose" @close="confirmClose" />

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
                    <v-select :key="`state-select-${product.state_id}`" :disabled="!canModify"
                        style="padding-top:25px; min-width: 100px; max-width: 200px;" v-model="product.state_id"
                        :items="available_states"
                        :item-text="item => $te('workflow.states.' + item.display_name) ? $t('workflow.states.' + item.display_name) : item.display_name"
                        item-value="id" :label="$t('product.state')" append-icon="mdi-chevron-down"
                        :menu-props="{ maxWidth: '300px' }" @change="updateRecord('state_id')">

                        <template v-slot:item="{ item }">
                            <v-list-item-avatar>
                                <v-icon :color="item.color">{{ item.icon }}</v-icon>
                            </v-list-item-avatar>
                            <v-list-item-content>
                                <v-list-item-title>
                                    {{ $te('workflow.states.' + item.display_name) ? $t('workflow.states.' +
                                        item.display_name) : item.display_name }}
                                </v-list-item-title>
                            </v-list-item-content>
                        </template>
                    </v-select>
                    <v-btn v-if="!edit && canModify && product.id == -1" text dark type="submit" form="form">
                        <v-icon left>mdi-content-save</v-icon>
                        <span>{{ $t('common.save') }}</span>
                    </v-btn>
                </v-toolbar>

                <v-form @submit.prevent="createRecord" id="form" ref="form" class="px-4">
                    <v-row no-gutters>
                        <v-col cols="6" class="pr-3">
                            <v-combobox v-on:change="productSelected" :disabled="!canModify" v-model="selected_type"
                                :items="product_types" item-text="title" :label="$t('product.report_type')"
                                name="report_type" v-validate="'required'" @blur="updateRecord('report_type')" />
                        </v-col>
                        <v-col cols="6" class="pr-3">
                            <v-text-field :disabled="!canModify" :label="$t('product.title')" name="title" type="text"
                                v-model="product.title" v-validate="'required'" data-vv-name="title"
                                :error-messages="errors.collect('title')" :spellcheck="$store.state.settings.spellcheck"
                                @blur="updateRecord('title')" />
                        </v-col>
                        <v-col cols="12" class="pr-3">
                            <v-textarea :disabled="!canModify" :label="$t('product.description')" name="description"
                                v-model="product.description" :spellcheck="$store.state.settings.spellcheck"
                                @blur="updateRecord('description')" />
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
                            <v-btn depressed small @click="previewProduct">
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
                        <MessageBox v-model="msgbox_visible" @yes="publishProduct" @cancel="msgbox_visible = false"
                            :title="$t('product.publish_confirmation')" :message="product.title"
                            :icon="{ name: 'mdi-help-circle', color: 'primary' }">
                        </MessageBox>

                        <MessageBox v-model="showPublishWithUnsavedConfirmation"
                            :title="$t('product.publish_unsaved.title')"
                            :message="$t('product.publish_unsaved.message')" :buttons="confirmPublishButtons"
                            :icon="{ name: 'mdi-alert-circle', color: 'warning' }" :max-width="600"
                            @close="showPublishWithUnsavedConfirmation = false" @save="saveAndPublish"
                            @publish="publishDirect" />
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
import { createProduct, publishProduct as publishProductAPI, publishProductDirect, updateProduct, previewProduct as previewProductAPI } from "@/api/publish";
import { getEntityTypeStates } from "@/api/state";
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
        showCloseConfirmation: false,
        showPublishWithUnsavedConfirmation: false,
        isLoading: false,
        initialFormState: null,
        confirmCloseButtons: [
            { label: 'confirm_close.continue', color: '', action: 'continue', text: true },
            { label: 'confirm_close.save_and_close', color: 'primary', action: 'save', text: true },
            { label: 'confirm_close.close', color: 'error', action: 'close', text: true }
        ],
        confirmPublishButtons: [
            { label: 'product.publish_unsaved.close', color: '', action: 'close', text: true },
            { label: 'product.publish_unsaved.save_and_publish', color: 'primary', action: 'save', text: true },
            { label: 'product.publish_unsaved.publish_only', color: 'error', action: 'publish', text: true }
        ],
        product_types: [],
        publisher_presets: [],
        selected_type: null,
        report_items: [],
        product: {
            id: -1,
            title: "",
            description: "",
            product_type_id: null,
            state_id: null,
            report_items: [],
        },
        msgbox_visible: false,
        // State management
        available_states: [],
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
                // Reset product.id when dialog closes
                this.product.id = -1;
                // Reset isLoading after Vue updates are complete
                this.$nextTick(() => {
                    this.isLoading = false;
                });
            }
        },

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
        addEmptyProduct() {
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
            this.selectDefaultState();
            this.resetValidation();
        },

        publishConfirmation() {
            // Check if at least one publisher is selected
            if (!this.validatePublisherSelection()) {
                return;
            }

            // Check if there are unsaved changes (only for new products, not editing)
            if (!this.edit && this.hasUnsavedChanges()) {
                this.showPublishWithUnsavedConfirmation = true;
            } else {
                this.msgbox_visible = true;
            }
        },

        prepareProduct() {
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
        },

        getSelectedPublisherIds() {
            return this.publisher_presets
                .filter(preset => preset.selected)
                .map(preset => preset.id);
        },

        validatePublisherSelection() {
            const selectedIds = this.getSelectedPublisherIds();
            if (selectedIds.length === 0) {
                this.$root.$emit('notification', { type: 'error', loc: 'product.no_publisher_selected' });
                return false;
            }
            return true;
        },

        validateAndSave() {
            return this.$validator.validateAll().then(() => {
                if (this.$validator.errors.any()) {
                    this.show_validation_error = true;
                    return Promise.resolve(false);
                }

                this.prepareProduct();

                let savePromise;

                if (this.product.id === -1) {
                    savePromise = createProduct(this.product).then((response) => {
                        this.product.id = response.data;
                    });
                } else {
                    savePromise = updateProduct(this.product).then(() => {
                        // Notify that product was updated so the product list refreshes
                        this.$root.$emit('product-updated');
                    });
                }

                return savePromise
                    .then(() => {
                        this.resetValidation();
                        return true;
                    })
                    .catch(() => {
                        this.show_error = true;
                        return false;
                    });
            });
        },

        saveAndPublish() {
            // Save to database first, then publish using traditional method
            this.showPublishWithUnsavedConfirmation = false;

            this.$validator.validateAll().then(() => {
                if (!this.$validator.errors.any()) {
                    this.prepareProduct();

                    const selectedPublisherIds = this.getSelectedPublisherIds();
                    if (selectedPublisherIds.length === 0) {
                        return;
                    }

                    // Save product to database
                    createProduct(this.product).then((response) => {
                        this.product.id = response.data;
                        this.resetValidation();

                        // Switch to edit mode to enable autosaving and hide save button
                        this.edit = true;
                        this.modify = true;
                        this.access = true;

                        // Update initial form state to reflect saved state
                        this.initialFormState = this.snapshotForm();

                        this.$root.$emit('notification', { type: 'success', loc: 'product.successful' });

                        // Publish to each selected publisher
                        selectedPublisherIds.forEach(publisherId => {
                            publishProductAPI(this.product.id, publisherId).then(() => {
                                this.$root.$emit('notification', { type: 'success', loc: 'product.publish_successful' });
                            }).catch((error) => {
                                console.error('Publish failed:', error);
                                this.$root.$emit('notification', { type: 'error', loc: 'product.publish_failed' });
                            });
                        });
                    }).catch(() => {
                        this.show_error = true;
                    });

                } else {
                    this.show_validation_error = true;
                }
            });
        },

        publishDirect() {
            // Publish directly without saving to database (in-memory using Redis)
            this.showPublishWithUnsavedConfirmation = false;

            this.$validator.validateAll().then(() => {
                if (!this.$validator.errors.any()) {
                    this.prepareProduct();

                    const selectedPublisherIds = this.getSelectedPublisherIds();
                    if (selectedPublisherIds.length === 0) {
                        return;
                    }

                    // Use direct publish (in-memory, no database save)
                    publishProductDirect(this.product, selectedPublisherIds)
                        .then((response) => {
                            // Reset validation errors but preserve initial form state for unsaved changes detection
                            this.$validator.reset();
                            this.show_validation_error = false;

                            // Check results and show appropriate notifications
                            if (response.data.overall_success) {
                                this.$root.$emit('notification', {
                                    type: 'success',
                                    loc: 'product.publish_successful'
                                });
                            } else {
                                this.$root.$emit('notification', {
                                    type: 'error',
                                    loc: 'product.publish_failed'
                                });
                            }
                        })
                        .catch((error) => {
                            console.error('Direct publish failed:', error);
                            this.show_error = true;
                            this.$root.$emit('notification', {
                                type: 'error',
                                loc: 'product.publish_error'
                            });
                        });

                } else {
                    this.show_validation_error = true;
                }
            });
        },

        productSelected() {

        },

        cancel() {
            // Check for unsaved changes only in create mode (not edit mode)
            if (!this.edit && this.hasUnsavedChanges()) {
                this.showCloseConfirmation = true;
                return;
            }

            this.closeDialog();
        },

        confirmClose() {
            this.showCloseConfirmation = false;
            this.closeDialog();
        },

        saveAndClose() {
            this.showCloseConfirmation = false;
            this.createRecord();
        },

        closeDialog() {
            this.resetValidation();
            this.isLoading = true;  // Set loading flag to prevent race condition during close animation
            this.visible = false;
        },

        previewProduct() {
            this.$validator.validateAll().then(() => {
                if (this.$validator.errors.any()) {
                    this.show_validation_error = true;
                    return;
                }

                this.prepareProduct();

                // Call the preview API - it always generates a fresh preview and returns a token
                previewProductAPI(this.product, this.$store.getters.getJWT).then((response) => {
                    // Get the token from response
                    const token = response.data.token;

                    // Build the preview URL with the token
                    const apiBase = ((typeof (process.env.VUE_APP_TARANIS_NG_CORE_API) == "undefined") ? "$VUE_APP_TARANIS_NG_CORE_API" : process.env.VUE_APP_TARANIS_NG_CORE_API);
                    const previewUrl = `${apiBase}/publish/products/preview/${token}?jwt=${this.$store.getters.getJWT}`;

                    // Open the preview URL in a new tab
                    window.open(previewUrl, '_blank');

                    // Reset validation errors but preserve initial form state for unsaved changes detection
                    this.$validator.reset();
                    this.show_validation_error = false;
                }).catch((error) => {
                    console.error('Preview failed:', error);
                    this.show_error = true;
                });
            });
        },

        publishProduct() {
            this.msgbox_visible = false;
            this.validateAndSave().then((ok) => {
                if (!ok) return;

                if (!this.validatePublisherSelection()) {
                    return;
                }

                const selectedPublisherIds = this.getSelectedPublisherIds();
                selectedPublisherIds.forEach(publisherId => {
                    publishProductAPI(this.product.id, publisherId).then(() => {
                        this.$root.$emit('notification', { type: 'success', loc: 'product.publish_successful' });
                    }).catch((error) => {
                        console.error('Publish failed:', error);
                        this.$root.$emit('notification', { type: 'error', loc: 'product.publish_failed' });
                    });
                });
            });
        },

        createRecord() {
            this.validateAndSave().then((ok) => {
                if (!ok) return;

                this.visible = false;
            });
        },

        updateRecord() {
            if (!this.edit && this.product.id === -1) return;
            this.validateAndSave().then((ok) => {
                if (!ok) return;
            });
        },

        resetValidation() {
            this.$validator.reset();
            this.show_validation_error = false;
            this.initialFormState = this.snapshotForm()
        },

        async loadAvailableStates() {
            try {
                const response = await getEntityTypeStates('product');
                this.available_states = response.data.states;

            } catch (error) {
                console.error('Failed to load available states for PRODUCT:', error);
                this.available_states = [];
            }
        },

        selectDefaultState() {
            if (!this.available_states) return;

            const defaultState = this.available_states.find(state => state.is_default);
            if (defaultState) {
                this.product.state_id = defaultState.id;
            }
        },

        snapshotForm() {
            return JSON.stringify({
                product: this.product,
                selected_type: this.selected_type,
                report_items: this.report_items,
            })
        },

        hasUnsavedChanges() {
            if (this.initialFormState !== null) {
                return this.snapshotForm() !== this.initialFormState
            }
            return false
        },

    },

    mounted() {
        this.loadAvailableStates();

        this.$root.$on('new-product', (data) => {
            this.visible = true;
            this.selected_type = null;
            this.report_items = data;
            this.product.id = -1;
        });

        this.$store.dispatch('getAllUserProductTypes', { search: '' }).then(() => {
            this.product_types = this.$store.getters.getProductTypes.items
        });

        this.$store.dispatch('getAllUserPublishersPresets', { search: '' }).then(() => {
            this.publisher_presets = this.$store.getters.getProductsPublisherPresets.items;
            for (let i = 0; i < this.publisher_presets.length; i++) {
                this.publisher_presets[i].selected = false
            }
        });

        this.$root.$on('show-product-edit', (data) => {
            // Prevent race condition during dialog animation
            if (this.isLoading) {
                return;
            }

            this.isLoading = true;
            this.initialFormState = null;
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
            this.product.state_id = data.state_id;

            for (let i = 0; i < this.product_types.length; i++) {
                if (this.product_types[i].id === this.product.product_type_id) {
                    this.selected_type = this.product_types[i];
                    break;
                }
            }

            // Use nextTick to ensure data is fully loaded before allowing new interactions
            this.$nextTick(() => {
                this.isLoading = false;
            });
        });
    },

    beforeDestroy() {
        this.$root.$off('new-product')
        this.$root.$off('show-product-edit')
    },
}
</script>
