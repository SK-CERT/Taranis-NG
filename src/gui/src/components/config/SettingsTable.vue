<template>
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
                    <div v-if="glob_setting" :class="UI.CLASS.toolbar_filter_title">
                        {{$t('nav_menu.settings')}}
                    </div>
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
            <template v-if="item.type === 'B'">
                <v-switch :input-value="item.value === 'true'"
                          @change="val => {
                              setting = { ...item, value: val ? 'true' : 'false' };
                              save(item);
                          }"
                          inset></v-switch>
            </template>
            <template v-else-if="item.options">
                <v-select v-model="item.value"
                          @change="val => { setting = { ...item, value: val }; save(item); }"
                          :value="item.value"
                          :items="JSON.parse(item.options)"
                          item-value="id"
                          item-text="txt"></v-select>
            </template>
            <template v-else>
                <v-edit-dialog v-model="item.value"
                               large
                               @save="save()"
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
        </template>

        <!-- default value tooltip moved to next column due to readability -->
        <template v-slot:item.description="{ item }">
            <v-tooltip bottom>
                <template v-slot:activator="{ on, attrs }">
                    <span v-bind="attrs" v-on="on" style="cursor: pointer;">
                        {{ $t('settings_enum.' + item.key) !== 'settings_enum.' + item.key ? $t('settings_enum.' + item.key) : item.description }}
                    </span>
                </template>
                <span>{{$t('settings.default_value')}}: {{ item.default_val }}</span>
            </v-tooltip>
        </template>

        <template v-slot:item.updated_at="{ item }">
            <span>{{ formatDate(item.updated_at) }}</span>
        </template>

    </v-data-table>
</template>

<script>
    import AuthMixin from "@/services/auth/auth_mixin";
    import { format } from "date-fns";
    import Settings, { getSetting, getSettingBoolean } from "@/services/settings";

    export default {
        name: "SettingsTable",
        props: {
            glob_setting: { type: Boolean, required: true },
        },

        data() {
            return {
                search: '',
                records: [],
                dialog: false,
                max150chars: v => v.length <= 150 || 'Input too long!',
                setting: {
                    id: -1,
                    value: "",
                    type: "",
                    is_global: true,
                },
                date_format: "yyyy-MM-dd HH:mm:ss", // Default format
            };
        },
        mixins: [AuthMixin],

        computed: {
            headers() {
                const headers = [
                    // { text: 'Key', value: 'key' },
                    { text: this.$t('settings.description'), value: 'description' },
                    { text: this.$t('settings.value'), value: 'value' },
                    // { text: 'Type', value: 'type' },
                ];
                if (this.glob_setting) {
                    headers.push({ text: this.$t('settings.updated_by'), value: 'updated_by' });
                    headers.push({ text: this.$t('settings.updated_at'), value: 'updated_at', filterable: false });
                }
                return headers;
            },
        },

        methods: {
            getColor(value, default_val) {
                return value === default_val ? "#a6a6a6" : "green";
            },

            formatDate(dateString) {
                return dateString ? format(new Date(dateString), this.date_format) : "";
            },

            initRecords() {
                var dateFmt = getSetting(Settings.DATE_FORMAT, "yyyy-MM-dd");
                var timeFmt = getSetting(Settings.TIME_FORMAT, "HH:mm:ss");
                if (dateFmt != "" && timeFmt != "") {
                    this.date_format = dateFmt + " " + timeFmt;
                }
                const allItems = this.$store.getters.getSettings;
                this.records = allItems.filter(item => item.is_global === this.glob_setting);
            },

            save() {
                // console.log('saving value:', this.setting.value)
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
                // console.log('saving corrected value:', this.setting.value, 'Object:', this.setting)
                this.$store.dispatch('saveSettings', { data: this.setting, is_global: this.glob_setting }).then(() => {
                    this.initRecords()
                    // Some special settings require immediate application
                    if (this.setting.key === Settings.DARK_THEME) {
                        this.$vuetify.theme.dark = getSettingBoolean(Settings.DARK_THEME);
                    } else if (this.setting.key === Settings.LANGUAGE) {
                        this.$i18n.locale = getSetting(Settings.LANGUAGE);
                    } else if (this.setting.key === Settings.SPELLCHECK) {
                        this.$store.state.settings.spellcheck = getSettingBoolean(Settings.SPELLCHECK);
                    }
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
            this.$store.dispatch('getAllSettings', { search: '' }).then(() => {
                this.initRecords()
            });
        },
    };
</script>
