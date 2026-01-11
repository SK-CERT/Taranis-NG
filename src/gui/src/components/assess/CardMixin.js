// shared mixin for assess cards
export default {
    data: () => ({
        msgbox_visible: false,
    }),
    computed: {
        cardFocus() {
            if (this.$el.querySelector(".card .layout") && this.$el.querySelector(".card .layout").classList.contains('focus')) {
                return true;
            } else {
                return false;
            }
        },
        selectedColor() {
            if (this.selected === true || this.preselected) {
                return this.$vuetify.theme.dark ? "blue-grey darken-3" : "orange lighten-4"
            } else {
                return ""
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
        multiSelectOff() {
            this.selected = false
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
        }
    },
    mounted() {
        this.$root.$on('multi-select-off', this.multiSelectOff);
        this.$root.$on('check-focus', (id) => {
            this.setFocus(id);
        });
    },
    beforeDestroy() {
        this.$root.$off('multi-select-off', this.multiSelectOff);
        this.$root.$off('check-focus');
    }
}
