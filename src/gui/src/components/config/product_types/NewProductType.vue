<template>
    <div>
        <v-btn v-if="canCreate" depressed small color="white--text ma-2 mt-3 mr-5" @click="addProduct">
            <v-icon left>mdi-plus-circle-outline</v-icon>
            <span class="subtitle-2">{{ $t('product_type.add_btn') }}</span>
        </v-btn>
        <v-dialog v-model="visible" fullscreen hide-overlay transition="dialog-bottom-transition">
            <v-card>
                <!--<v-card-title class="headline">{{$t('osint_source.add_new')}}</v-card-title>-->

                <v-toolbar dark color="primary">
                    <v-btn icon dark @click="cancel">
                        <v-icon>mdi-close-circle</v-icon>
                    </v-btn>
                    <v-toolbar-title v-if="!edit">{{ $t('product_type.add_new') }}</v-toolbar-title>
                    <v-toolbar-title v-if="edit">{{ $t('product_type.edit') }}</v-toolbar-title>
                    <v-spacer></v-spacer>
                    <v-btn v-if="canUpdate" text type="submit" form="form">
                        <v-icon left>mdi-content-save</v-icon>
                        <span>{{ $t('product_type.save') }}</span>
                    </v-btn>
                </v-toolbar>

                <v-card-text>
                    <v-form @submit.prevent="add" id="form" ref="form">

                        <span v-if="edit">ID: {{ product.id }}</span>

                        <v-combobox :disabled="edit"
                                    v-model="selected_node"
                                    :items="nodes"
                                    item-text="name"
                                    :label="$t('product_type.node')"
                        ></v-combobox>
                        <v-combobox v-if="selected_node" :disabled="edit"
                                    v-model="selected_presenter"
                                    :items="selected_node.presenters"
                                    item-text="name"
                                    :label="$t('product_type.presenter')"
                        ></v-combobox>


                        <v-text-field v-if="selected_presenter" :disabled="!canUpdate"
                                      :label="$t('product_type.name')"
                                      name="name"
                                      type="text"
                                      v-model="product.title"
                                      v-validate="'required'"
                                      data-vv-name="name"
                                      :error-messages="errors.collect('name')"
                                      :spellcheck="$store.state.settings.spellcheck"
                        ></v-text-field>
                        <v-textarea v-if="selected_presenter" :disabled="!canUpdate"
                                    :label="$t('product_type.description')"
                                    name="description"
                                    v-model="product.description"
                                    :spellcheck="$store.state.settings.spellcheck"
                        ></v-textarea>


                        <FormParameters v-if="selected_presenter" :disabled="!canUpdate"
                                        ui="text"
                                        :sources="selected_presenter.parameters"
                                        :values="values"
                        />

                    </v-form>

                    <v-dialog v-model="help_dialog" fullscreen>
                        <template v-slot:activator="{ on }">
                            <v-btn color="primary" dark class="mb-2" v-on="on">
                                <v-icon left>mdi-help</v-icon>
                                <span>{{ $t('product_type.help') }}</span>
                            </v-btn>
                        </template>
                        <v-toolbar dark color="primary">
                            <v-btn icon dark @click="closeHelpDialog">
                                <v-icon>mdi-close-circle</v-icon>
                            </v-btn>
                            <v-toolbar-title>{{ $t('product_type.help') }}</v-toolbar-title>
                        </v-toolbar>
                        <v-card>
                            <v-card-title>
                                <v-combobox
                                    v-model="selected_type"
                                    :items="report_types"
                                    item-text="title"
                                    :label="$t('product_type.choose_report_type')"
                                />
                            </v-card-title>

                            <v-card-text>
                                <div v-if="selected_type !== null">
                                    <v-card style="margin-bottom: 8px"
                                            v-for="attribute_group in selected_type.attribute_groups"
                                            :key="attribute_group.id">
                                        <v-card-title>{{ attribute_group.title }}</v-card-title>
                                        <v-card-text>
                                        {&perc; for report_item in data &perc;}
                                        </v-card-text>
                                        <v-card-text v-for="attribute_item in attribute_group.attribute_group_items"
                                                     :key="attribute_item.id">
                                            <span><strong>{{ attribute_item.title }}</strong>: <span class="pl-3 pr-3 pt-1 pb-1"
                                                style="background-color: #efefef; border-style: solid; border-width: 1px; font-style: italic; font-size: 16px"
                                                v-html="attributeUsage(attribute_item)"></span></span>
                                        </v-card-text>
                                        <v-card-text>
                                        {&perc; endfor &perc;}
                                        </v-card-text>
                                    </v-card>
                                </div>
                            </v-card-text>

                        </v-card>
                    </v-dialog>

                    <v-alert v-if="show_validation_error" dense type="error" text>
                        {{ $t('product_type.validation_error') }}
                    </v-alert>
                    <v-alert v-if="show_error" dense type="error" text>
                        {{ $t('product_type.error') }}
                    </v-alert>
                </v-card-text>

            </v-card>
        </v-dialog>
    </div>
</template>

<script>
import {createNewProductType, updateProductType} from "@/api/config";
import FormParameters from "../../common/FormParameters";
import AuthMixin from "@/services/auth/auth_mixin";
import Permissions from "@/services/auth/permissions";

export default {
    name: "NewProductType",
    components: {
        FormParameters
    },
    data: () => ({
        visible: false,
        edit: false,
        help_dialog: false,
        selected_type: null,
        show_validation_error: false,
        show_error: false,
        selected_node: null,
        selected_presenter: null,
        nodes: [],
        report_types: [],
        values: [],
        product: {
            id: -1,
            title: "",
            description: "",
            presenter_id: "",
            parameter_values: []
        }
    }),
    mixins: [AuthMixin],
    computed: {
        canCreate() {
            return this.checkPermission(Permissions.CONFIG_PRODUCT_TYPE_CREATE)
        },
        canUpdate() {
            return this.checkPermission(Permissions.CONFIG_PRODUCT_TYPE_UPDATE) || !this.edit
        }
    },

    methods: {
        closeHelpDialog() {
            this.help_dialog = false;
            this.selected_type = null;
        },

        attributeUsage(attribute_item) {
            let variable = attribute_item.title.toLowerCase().replaceAll(" ", "_")
            if (attribute_item.max_occurrence > 1) {
                return "{% <span style=\"color: #be6d7c\">for</span> entry <span style=\"color: #be6d7c\">in</span> <span style=\"color: #6d9abe\">report_item." + variable + "</span> %}{{ entry | e }}{% <span style=\"color: #be6d7c\">endfor</span> %}"
            } else {
                return "{{ <span style=\"color: #6d9abe\">report_item." + variable + " | e</span> }}"
            }
        },

        addProduct() {
            this.visible = true
            this.edit = false
            this.show_error = false;
            this.selected_node = null
            this.selected_presenter = null
            this.product.id = -1
            this.product.title = ""
            this.product.description = ""
            this.product.presenter_id = ""
            this.values = []
            this.product.parameter_values = []
            this.$validator.reset();
        },

        cancel() {
            this.$validator.reset();
            this.visible = false
        },

        add() {
            this.$validator.validateAll().then(() => {

                if (!this.$validator.errors.any()) {

                    this.show_validation_error = false;
                    this.show_error = false;

                    this.product.presenter_id = this.selected_presenter.id;

                    for (let i = 0; i < this.selected_presenter.parameters.length; i++) {
                        this.product.parameter_values[i] = {
                            value: this.values[i],
                            parameter: this.selected_presenter.parameters[i]
                        }
                    }

                    if (this.edit) {
                        updateProductType(this.product).then(() => {

                            this.$validator.reset();
                            this.visible = false;
                            this.$root.$emit('notification',
                                {
                                    type: 'success',
                                    loc: 'product_type.successful_edit'
                                }
                            )
                        }).catch(() => {

                            this.show_error = true;
                        })
                    } else {
                        createNewProductType(this.product).then(() => {

                            this.$validator.reset();
                            this.visible = false;
                            this.$root.$emit('notification',
                                {
                                    type: 'success',
                                    loc: 'product_type.successful'
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
        }
    },
    mounted() {
        this.$store.dispatch('getAllPresentersNodes', {search: ''})
            .then(() => {
                this.nodes = this.$store.getters.getPresentersNodes.items
            });

        this.$store.dispatch('getAllReportItemTypesConfig', {search: ''})
            .then(() => {
                this.report_types = this.$store.getters.getReportItemTypesConfig.items
            });

        this.$root.$on('show-edit', (data) => {

            this.visible = true;
            this.edit = true
            this.show_error = false;

            this.product.id = data.id
            this.product.title = data.title
            this.product.description = data.description
            this.product.presenter_id = data.presenter_id

            this.product.parameter_values = []
            for (let i = 0; i < data.parameter_values.length; i++) {
                this.product.parameter_values.push({
                    value: data.parameter_values[i].value,
                    parameter: data.parameter_values[i].parameter
                })
            }

            let found = false
            for (let i = 0; i < this.nodes.length; i++) {
                for (let j = 0; j < this.nodes[i].presenters.length; j++) {
                    if (this.nodes[i].presenters[j].id === this.product.presenter_id) {
                        this.selected_node = this.nodes[i]
                        this.selected_presenter = this.nodes[i].presenters[j]
                        found = true
                        break;
                    }
                }

                if (found) {
                    break
                }
            }

            this.values = []
            for (let i = 0; i < this.selected_presenter.parameters.length; i++) {
                for (let j = 0; j < this.product.parameter_values.length; j++) {
                    if (this.selected_presenter.parameters[i].id === this.product.parameter_values[j].parameter.id) {
                        this.values.push(this.product.parameter_values[j].value)
                        break
                    }
                }
            }
        });
    },
    beforeDestroy() {
        this.$root.$off('show-edit')
    }
}
</script>
