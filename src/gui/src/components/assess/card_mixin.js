// shared mixin for assess cards
export default {
    data: () => ({
        toolbar: false,
        selected: false,
        msgbox_visible: false,
    }),

    computed: {
        canCreateReport() {
            return this.checkPermission(Permissions.ANALYZE_CREATE)
        },

        multiSelectActive() {
            return this.$store.getters.getMultiSelect
        },

        selectedColor() {
            if (this.selected === true || this.preselected) {
                return this.$vuetify.theme.dark ? "blue-grey darken-3" : "orange lighten-4"
            } else {
                return ""
            }
        },

        cardFocus() {
            if (this.$el.querySelector(".card .layout") && this.$el.querySelector(".card .layout").classList.contains('focus')) {
                return true;
            } else {
                return false;
            }
        },

        cardStatus() {
            const item = this.card || this.news_item;
            if (item.important) {
                return "important"
            } else {
                return "new"
            }
        },

        isRead() {
            const item = this.card || this.news_item;
            return item.read && !item.important
        },
    },

    methods: {
        stateChange() {
            this.$root.$emit('change-state', 'SHOW_ITEM');
            this.$root.$emit('check-focus', this.$el.dataset.id);
            this.$root.$emit('update-pos', parseInt(this.$el.dataset.id));
        },

        getGroupId() {
            if (window.location.pathname.includes("/group/")) {
                let i = window.location.pathname.indexOf("/group/");
                let len = window.location.pathname.length;
                return window.location.pathname.substring(i + 7, len);
            } else {
                return null;
            }
        },

        buttonStatus: function (active) {
            if (active) {
                return "amber darken-2"
            } else {
                return "primary"
            }
        },

        wordCheck(target) {
            let parse = new Array();
            let message = this.escapeHtml(target).split(' ');
            let word_list = new RegExp(this.word_list_regex, "gi");

            for (let i = 0; i < message.length; i++) {
                let res = message[i].replace(word_list, function (x) {
                    return "<span class='wordlist'>" + x + "</span>";
                });

                parse.push(res + " ");
            }

            return parse.join('');
        },

        escapeHtml(text) {
            let map = {
                '&': '&amp;',
                '<': '&lt;',
                '>': '&gt;',
                '"': '&quot;',
                "'": '&#039;'
            };

            return text.replace(/[&<>"']/g, function (m) {
                return map[m];
            });
        },

        multiSelectOff() {
            this.selected = false
        },

        syncSelection() {
            const selection = this.$store.getters.getSelection;
            const item = this.card || this.news_item;
            this.selected = selection.some(s => s.id === item.id);
        },

        setFocus(id) {
            if (this.$el.dataset.id == id) {
                this.toolbar = true;
                const layout = this.$el.querySelector(".card .layout");
                if (layout) {
                    layout.classList.add('focus');
                }
            } else {
                this.toolbar = false;
                const layout = this.$el.querySelector(".card .layout");
                if (layout) {
                    layout.classList.remove('focus');
                }
            }
        },

        showMsgBox() {
            this.msgbox_visible = true;
        },

        handleMsgBox() {
            this.msgbox_visible = false;
            this.cardItemToolbar('delete')
        },
    },

    mounted() {
        this.$root.$on('multi-select-off', this.multiSelectOff);
        this.$root.$on('sync-assess-selection', this.syncSelection);
        this.$root.$on('check-focus', (id) => {
            this.setFocus(id);
        });
    },

    beforeDestroy() {
        this.$root.$off('multi-select-off', this.multiSelectOff);
        this.$root.$off('sync-assess-selection', this.syncSelection);
        this.$root.$off('check-focus');
    },
}
