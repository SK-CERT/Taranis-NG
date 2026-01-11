// shared mixin for all assess components
export default {
    data: () => ({
        toolbar: false,
        selected: false,
    }),
    computed: {
        multiSelectActive() {
            return this.$store.getters.getMultiSelect
        },
    },
    methods: {
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
        getGroupId() {
            if (window.location.pathname.includes("/group/")) {
                let i = window.location.pathname.indexOf("/group/");
                let len = window.location.pathname.length;
                return window.location.pathname.substring(i + 7, len);
            } else {
                return null;
            }
        },
    }
}
