<template>
    <v-row v-bind="UI.DIALOG.ROW.WINDOW">
        <v-btn v-bind="UI.BUTTON.ADD_NEW" v-if="add_button && canCreate" @click="addEmptyProduct">
            <v-icon left>{{ UI.ICON.PLUS }}</v-icon>
            <span>{{ $t('common.add_btn') }}</span>
        </v-btn>

        <v-dialog v-bind="UI.DIALOG.FULLSCREEN" v-model="visible" @keydown.esc="cancel" new-product>
            <MessageBox v-model="showCloseConfirmation" :title="$t('confirm_close.title')"
                        :message="$t('product.confirm_close.message')" :buttons="confirmCloseButtons"
                        :icon="{ name: 'mdi-help-circle', color: 'warning' }"
                        @continue="showCloseConfirmation = false" @save="saveAndClose" @close="confirmClose" />

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
                                    {{ $te('workflow.states.' + item.display_name) ? $t('workflow.states.' + item.display_name) : item.display_name }}
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
                            <v-btn depressed small @click="processProduct(false, $event)">
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
                        <MessageBox v-model="msgbox_visible" @yes="processProduct(true)" @cancel="msgbox_visible = false"
                                    :title="$t('product.publish_confirmation')" :message="product.title"
                                    :icon="{ name: 'mdi-help-circle', color: 'primary' }">
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
            initialFormState: null,
            confirmCloseButtons: [
                { label: 'confirm_close.continue', color: '', action: 'continue', text: true },
                { label: 'confirm_close.save_and_close', color: 'primary', action: 'save', text: true },
                { label: 'confirm_close.close', color: 'error', action: 'close', text: true }
            ],
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
                this.msgbox_visible = true;
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
                this.visible = false;
            },

            processProduct(publish = false, event) {
                this.msgbox_visible = false; // only relevant for publish, harmless for preview

                this.validateAndSave().then((ok) => {
                    if (!ok) return;

                    if (publish) {
                        for (const preset of this.publisher_presets) {
                            if (!preset.selected) continue;
                            publishProduct(this.product.id, preset.id);
                        }
                    } else {
                        const base = typeof process.env.VUE_APP_TARANIS_NG_CORE_API === "undefined"
                            ? "$VUE_APP_TARANIS_NG_CORE_API"
                            : process.env.VUE_APP_TARANIS_NG_CORE_API;

                        let url = `${base}/publish/products/${this.product.id}/overview?jwt=${this.$store.getters.getJWT}`;
                        if (event && event.ctrlKey) url += "&ctrl=1";

                        window.open(url, "_blank");
                    }
                });
            },

            validateAndSave() {
                return this.$validator.validateAll().then(() => {
                    if (this.$validator.errors.any()) {
                        this.show_validation_error = true;
                        return false;
                    }

                    this.prepareProduct();

                    const savePromise = () => {
                        if (this.product.id !== -1) {
                            return updateProduct(this.product).then(() => {
                                this.$root.$emit('notification', { type: 'success', loc: 'product.successful' });
                            });
                        } else {
                            return createProduct(this.product).then((res) => {
                                this.product.id = res.data;
                                this.$root.$emit('product-updated');
                            });
                        }
                    };

                    return savePromise()
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

            this.$root.$on('show-product-edit', (data) => {
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

                this.preview_link = ((typeof (process.env.VUE_APP_TARANIS_NG_CORE_API) == "undefined") ? "$VUE_APP_TARANIS_NG_CORE_API" : process.env.VUE_APP_TARANIS_NG_CORE_API) + "/publish/products/" + data.id + "/overview?jwt=" + this.$store.getters.getJWT
            });
        },

        beforeDestroy() {
            this.$root.$off('new-product')
            this.$root.$off('show-product-edit')
        },
    }
</script>
