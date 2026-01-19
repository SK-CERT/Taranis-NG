// shared mixin for all news items components
export default {
    data: () => ({
        toolbar: false,
        msgbox_visible: false,
    }),

    computed: {
        canCreateReport() {
            return this.checkPermission(Permissions.ANALYZE_CREATE)
        },

        multiSelectActive() {
            return this.$store.getters.getMultiSelect
        },
    },

    methods: {
        openUrlToNewTab: function (url) {
            window.open(url, "_blank");
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
                return "amber"
            } else {
                return "white"
            }
        },

        showMsgBox() {
            this.msgbox_visible = true;
        },

        handleMsgBox() {
            this.msgbox_visible = false;
            this.cardItemToolbar('delete')
        },
    }
}
