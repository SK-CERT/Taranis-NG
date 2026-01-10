export default {
    data: () => ({
        toolbar: false,
        selected: false,
    }),
    computed: {
        multiSelectActive() {
            return this.$store.getters.getMultiSelect
        },
        cardFocus() {
            if (this.$el.querySelector(".card .layout").classList.contains('focus')) {
                return true;
            } else {
                return false;
            }
        },
    },
    methods: {
        buttonStatus(active) {
            if (active) {
                return "info"
            } else {
                return "accent"
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
        getGroupId() {
            if (window.location.pathname.includes("/group/")) {
                let i = window.location.pathname.indexOf("/group/");
                let len = window.location.pathname.length;
                return window.location.pathname.substring(i + 7, len);
            } else {
                return null;
            }
        },
        multiSelectOff() {
            this.selected = false
        },
        setFocus(id) {
            if (this.$el.dataset.id == id) {
                this.toolbar = true;
                this.$el.querySelector(".card .layout").classList.add('focus');
            } else {
                this.toolbar = false;
                this.$el.querySelector(".card .layout").classList.remove('focus');
            }
        },
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
