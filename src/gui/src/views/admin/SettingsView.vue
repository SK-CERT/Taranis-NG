<template>
    <v-container>
        <v-data-table :headers="headers"
                      :items="records"
                      :items-per-page="-1"
                      item-key="id"
                      sort-by="description"
                      class="elevation-1"
                      :search="search"
                      :clickable="false"
                      @click.stop
                      disable-pagination
                      hide-default-footer>
            <template v-slot:top>
                <v-row v-bind="UI.TOOLBAR.ROW">
                    <v-col v-bind="UI.TOOLBAR.COL.LEFT">
                        <div :class="UI.CLASS.toolbar_filter_title">{{$t('nav_menu.settings')}}</div>
                    </v-col>
                    <v-col v-bind="UI.TOOLBAR.COL.MIDDLE">
                        <v-text-field v-bind="UI.ELEMENT.SEARCH"
                                      v-model="search"
                                      :label="$t('toolbar_filter.search')"
                                      single-line
                                      hide-details></v-text-field>
                    </v-col>
                    <v-col v-bind="UI.TOOLBAR.COL.RIGHT">
                        <slot name="XXX"></slot>
                    </v-col>
                </v-row>
            </template>

            <template v-slot:item.value="{ item }">
                <v-edit-dialog :return-value.sync="item.value"
                                v-model="setting.value"
                                large
                                @save="save(item)"
                                @cancel="cancel"
                                @open="open(item)"
                                @close="close">
                    <v-chip :color="getColor(item.value, item.default_val)"
                            :label="true"
                            style="cursor: pointer"
                            dark>
                        {{ item.value }}
                    </v-chip>
                    <template v-slot:input>
                        <div class="mt-4 text-h6">
                            {{$t('settings.update_value')}}
                        </div>
                        <v-text-field v-model="setting.value"
                                        :rules="[max150chars]"
                                        label="Edit"
                                        single-line
                                        counter
                                        autofocus></v-text-field>
                    </template>
                </v-edit-dialog>
            </template>

            <!-- default value tooltip moved to next column due to readability -->
            <template v-slot:item.updated_by="{ item }">
                <v-tooltip bottom>
                    <template v-slot:activator="{ on, attrs }">
                        <span v-bind="attrs" v-on="on" style="cursor: pointer;">
                            {{ item.updated_by }}
                        </span>
                    </template>
                    <span>{{$t('settings.default_value')}}: {{ item.default_val }}</span>
                </v-tooltip>
            </template>

            <template v-slot:item.updated_at="{ item }">
                <span>{{ formatDate(item.updated_at) }}</span>
            </template>
        </v-data-table>
    </v-container>
</template>

<script>
    import { updateSetting } from "@/api/config";
    import AuthMixin from "@/services/auth/auth_mixin";
    import Permissions from "@/services/auth/permissions";
    import { format } from 'date-fns';
    import Settings, { getSetting } from "@/services/settings";

    export default {

        name: "SettingsTable",
        props: {},
        data() {
            return {
                search: '',
                headers: [
                    // { text: 'Key', value: 'key' },
                    { text: this.$t('settings.description'), value: 'description' },
                    { text: this.$t('settings.value'), value: 'value' },
                    // { text: 'Type', value: 'type' },
                    { text: this.$t('settings.updated_by'), value: 'updated_by' },
                    { text: this.$t('settings.updated_at'), value: 'updated_at', filterable: false },
                ],
                records: [],
                dialog: false,
                max150chars: v => v.length <= 150 || 'Input too long!',
                setting: {
                    id: -1,
                    value: "",
                    type: "",
                },
                date_format: ""
            };
        },
        mixins: [AuthMixin],
        computed: {
        },
        methods: {
            getColor(value, default_val) {
                if (value == default_val) return '#a6a6a6'
                else return 'green'
            },

            formatDate(dateString) {
                if (dateString) {
                    return format(new Date(dateString), this.date_format);
                }
            },

            fetchRecords() {
                if (this.checkPermission(Permissions.CONFIG_SETTINGS_ACCESS)) {
                    this.$store.dispatch('getAllSettings', { search: '' }).then(() => {
                        var dateFmt = getSetting(Settings.DATE_FORMAT);
                        var timeFmt = getSetting(Settings.TIME_FORMAT);
                        if (dateFmt != "" && timeFmt != "") {
                            this.date_format = dateFmt + " " + timeFmt;
                        } else {
                            this.date_format = "yyyy-MM-dd HH:mm:ss"; // Default format
                        }

                        this.records = this.$store.getters.getSettings.items;
                    });
                }
            },

            save(item) {
                // console.log('save', this.setting.value)
                var val = this.setting.value.trim();
                if (this.setting.type == 'B') {
                    val = val.toLowerCase();
                    if (val != "true" && val != "false") {
                        this.showMsg("warning", "settings.boolean_error");
                        return;
                    }
                } else if (this.setting.type == 'I') {
                    val = Number(val);
                    if (isNaN(val) || !Number.isInteger(val)) {
                        this.showMsg("warning", "settings.integer_error");
                        return;
                    }
                } else if (this.setting.type === 'N') {
                    val = Number(val);
                    if (isNaN(val) || !isFinite(val)) {
                        this.showMsg("warning", "settings.decimal_error");
                        return;
                    }
                }
                this.setting.value = String(val)
                // console.log('saving', this.setting.value)
                updateSetting(this.setting).then((response) => {
                    Object.assign(item, response.data);
                    this.showMsg("success", "settings.successful_edit");
                }).catch(() => {
                    this.showMsg("error", "settings.error");
                })
            },

            cancel() {
                // console.log('cancel', this.setting.value)
            },

            open(item) {
                this.setting = Object.assign({}, item);
                // console.log('open', this.setting.value)
            },

            close() {
                // console.log('close')
            },

            showMsg(type, message) {
                this.$root.$emit('notification', { type: type, loc: message })
            },

        },
        mounted() {
            this.fetchRecords();
        }
    }
</script>
