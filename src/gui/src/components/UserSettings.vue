<template>
    <div>
        <v-row justify="center">
            <v-dialog v-model="visible" max-width="800" class="user-settings-dialog" @keydown.esc="close">
                <v-card>
                    <v-toolbar dark dense color="primary">
                        <v-btn icon dark @click="close()">
                            <v-icon>mdi-close-circle</v-icon>
                        </v-btn>
                        <v-toolbar-title class="title-limit">{{$t('settings.user_settings')}}</v-toolbar-title>
                        <v-spacer></v-spacer>
                        <v-btn text @click="save()">
                            <v-icon left>mdi-content-save</v-icon>
                            <span>{{$t('common.save')}}</span>
                        </v-btn>
                    </v-toolbar>

                    <v-tabs dark centered grow height="32">
                        <!-- TABS -->
                        <v-tab href="#tab-1">
                            <span>{{$t('settings.tab_general')}}</span>
                        </v-tab>
                        <v-tab href="#tab-2">
                            <span>{{$t('settings.tab_wordlists')}}</span>
                        </v-tab>
                        <v-tab href="#tab-3">
                            <span>{{$t('settings.tab_hotkeys')}}</span>
                        </v-tab>

                        <!-- #tab-1 -->
                        <v-tab-item value="tab-1" class="pa-0">
                            <v-container fluid>
                                <template>
                                    <SettingsTable :glob_setting="false"></SettingsTable>
                                </template>
                            </v-container>
                        </v-tab-item>

                        <!-- #tab-2 -->
                        <v-tab-item value="tab-2" class="pa-0">
                            <v-container fluid>
                                <v-data-table
                                    v-model="selected_word_lists"
                                    :headers="headers"
                                    :items="word_lists"
                                    item-key="id"
                                    show-select
                                    class="elevation-1"
                                >

                                    <template v-slot:top>
                                        <v-toolbar flat>
                                            <v-toolbar-title>{{$t('osint_source.word_lists')}}</v-toolbar-title>
                                        </v-toolbar>
                                    </template>

                                </v-data-table>
                            </v-container>
                        </v-tab-item>

                        <!-- #tab-3 -->
                        <v-tab-item value="tab-3" class="pa-0">
                            <v-container fluid class="">
                                <v-row no-gutters class="ma-0">
                                    <v-tooltip top v-for="shortcut in shortcuts" :key="shortcut.alias">
                                        <template v-slot:activator="{on}">
                                            <v-btn :id=shortcut.alias v-on="on"
                                                   class="ma-1" style="width: calc(100% / 3 - 8px);"
                                                   @click.stop="pressKeyDialog(shortcut.alias)"
                                                   @blur="pressKeyVisible = false">
                                                <v-icon left>{{shortcut.icon}}</v-icon>
                                                <span v-if="shortcut.key != 'undefined'" style="text-transform: none;" class="caption">{{shortcut.key}}</span>
                                                <v-icon v-else color="error">mdi-alert</v-icon>
                                            </v-btn>
                                        </template>
                                        <span>
                                            {{ $t('settings.' + shortcut.alias) }}
                                        </span>
                                    </v-tooltip>
                                </v-row>
                                <v-row no-gutters class="ma-0">
                                    <v-spacer></v-spacer>
                                    <v-btn text @click="resetHotkeys()">
                                        <v-icon left>mdi-reload</v-icon>
                                        <span>{{$t('settings.reset_keys')}}</span>
                                    </v-btn>
                                </v-row>
                            </v-container>
                        </v-tab-item>

                    </v-tabs>
                </v-card>
            </v-dialog>

            <!-- Press Key Dialog -->
            <template>
                <div class="text-center">
                    <v-dialog
                            v-model="pressKeyVisible"
                            width="300"
                            persistent
                            v-on:keydown="pressKey"
                    >
                        <v-card color="primary" dark>
                            <v-card-text class="white--text">
                                {{$t('settings.press_key')}}<span class="font-weight-bold">{{$t('settings.' + hotkeyAlias)}}</span>
                                <v-progress-linear
                                        indeterminate
                                        color="white"
                                        class="mb-0"
                                ></v-progress-linear>
                            </v-card-text>
                        </v-card>
                    </v-dialog>
                </div>
            </template>
        </v-row>
    </div>
</template>

<script>
    import Permissions from "@/services/auth/permissions";
    import AuthMixin from "@/services/auth/auth_mixin";
    import SettingsTable from "@/components/config/SettingsTable.vue";

    export default {
        name: "UserSettings",
        components: {
            SettingsTable
        },
        mixins: [AuthMixin],
        data: () => ({
            visible: false,
            pressKeyVisible: false,
            shortcuts: [],
            hotkeyAlias: '',
            headers: [
                {
                    text: 'Name',
                    align: 'start',
                    value: 'name',
                },
                { text: 'Description', value: 'description' },
            ],
            word_lists: [],
            selected_word_lists: [],
        }),
        methods: {
            close() {
                this.visible = false;
            },

            save() {
                Promise.all([
                    this.$store.dispatch('saveUserWordLists', this.selected_word_lists),
                    this.$store.dispatch('saveUserHotkeys', this.shortcuts)
                ]).then(() => {
                    this.visible = false;
                }).catch(error => {
                    console.error('Save user profile error:', error);
                });
            },

            pressKeyDialog(event) {
                window.addEventListener("keydown", this.pressKey, false);

                this.pressKeyVisible = true;
                this.hotkeyAlias = event;
            },

            pressKey(event) {
                // Beware! pressed keys are active also on background window when you try setting a new hotkey
                // wait for a "real" key, don't cancel dialog on modifier key, otherwise you can't choose uppercase letters and other keys
                if (event.key == "Alt" || event.key == "Shift" || event.key == "Control") {
                    return;
                }

                let key = event;
                let hotkeyIndex = this.shortcuts.map(function (e) { return e.alias; }).indexOf(this.hotkeyAlias);

                window.removeEventListener("keydown", this.pressKey);

                this.pressKeyVisible = false;

                // check duplicity and clear
                this.shortcuts.forEach(
                    (doubleKey, i) => {
                        if (doubleKey.key == key.key && i != hotkeyIndex) {
                            this.shortcuts[i].key = 'undefined';
                        }
                    }
                );

                // assigned new key
                this.shortcuts[hotkeyIndex].key = key.key;
            },

            resetHotkeys() {
                this.$store.dispatch('resetHotkeys');
                this.shortcuts = JSON.parse(JSON.stringify(this.$store.getters.getProfileHotkeys)) // Deep copy
            },

        },
        mounted() {
            this.$root.$on('show-user-settings', () => {
                this.visible = true;
                this.selected_word_lists = this.$store.getters.getProfileWordLists
                this.shortcuts = JSON.parse(JSON.stringify(this.$store.getters.getProfileHotkeys)) // Deep copy, don't change the original object until save
            });

            this.$store.dispatch('getAvailableWordLists', { search: '' })
                .then(() => {
                    this.word_lists = this.$store.getters.getAvailableWordLists
                });
        }
    }
</script>
