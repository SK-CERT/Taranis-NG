import AuthMixin from "@/services/auth/auth_mixin";
import { format } from 'date-fns';
import Settings, { getSetting } from "@/services/settings";
import MessageBox from "@/components/common/MessageBox.vue";

export default {
    components: {
        MessageBox,
    },
    mixins: [AuthMixin],
    data() {
        return {
            search: "",
            records: [],
            dialogEdit: false,
            dialogDelete: false,
            editedIndex: -1,
            editedItem: {},
            date_format: ""
        };
    },
    methods: {
        formatDate(dateString) {
            if (dateString) {
                return format(new Date(dateString), this.date_format);
            }
        },

        initializeDateFormat() {
            var dateFmt = getSetting(Settings.DATE_FORMAT);
            var timeFmt = getSetting(Settings.TIME_FORMAT);
            if (dateFmt != "" && timeFmt != "") {
                this.date_format = dateFmt + " " + timeFmt;
            } else {
                this.date_format = "yyyy-MM-dd HH:mm:ss";
            }
        },

        addItem() {
            this.editedIndex = -1
            this.editedItem = Object.assign({}, this.getDefaultItem());
            this.dialogEdit = true;
        },

        editItem(item) {
            this.editedIndex = this.records.indexOf(item)
            this.editedItem = Object.assign({}, item)
            this.dialogEdit = true
        },

        deleteItem(item) {
            this.editedIndex = this.records.indexOf(item)
            this.editedItem = Object.assign({}, item)
            this.dialogDelete = true
        },

        closeEdit() {
            this.dialogEdit = false
            this.$nextTick(() => {
                this.editedItem = Object.assign({}, this.getDefaultItem())
                this.editedIndex = -1
            })
        },

        closeDelete() {
            this.dialogDelete = false
            this.$nextTick(() => {
                this.editedItem = Object.assign({}, this.getDefaultItem())
                this.editedIndex = -1
            })
        },

        saveRecord(submitData) {
            if (this.editedIndex > -1) {
                this.updateProvider(submitData).then((response) => {
                    this.editedItem = Object.assign({}, response.data)
                    Object.assign(this.records[this.editedIndex], this.editedItem);
                    this.showMsg("success", this.getMessageKey("successful_edit"));
                    this.closeEdit();
                }).catch(() => {
                    this.showMsg("error", this.getMessageKey("error"));
                })
            } else {
                // Remove id field when creating new record
                const { id, ...dataWithoutId } = submitData;
                this.createProvider(dataWithoutId).then((response) => {
                    this.editedItem = Object.assign({}, response.data)
                    this.records.push(this.editedItem);
                    this.showMsg("success", this.getMessageKey("successful"));
                    this.closeEdit();
                }).catch(() => {
                    this.showMsg("error", this.getMessageKey("error"));
                })
            }
        },

        deleteRecord() {
            this.deleteProvider(this.editedItem).then(() => {
                this.records.splice(this.editedIndex, 1);
                this.showMsg("success", this.getMessageKey("remove"));
                this.closeDelete();
            }).catch(() => {
                this.showMsg("error", this.getMessageKey("removed_error"));
            })
        },

        showMsg(type, message) {
            this.$root.$emit('notification', { type: type, loc: message })
        }
    },
    mounted() {
        this.fetchRecords();
    }
}
