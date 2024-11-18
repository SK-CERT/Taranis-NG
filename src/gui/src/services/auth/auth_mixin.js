import AuthService from "@/services/auth/auth_service";
import Permissions from "@/services/auth/permissions";

var AuthMixin = {

    data: () => ({
        permissions: Permissions
    }),

    methods: {
        logout() {
            this.$store.dispatch('logout').then(() => {
                if (this.$store.getters.hasExternalLogoutUrl) {
                    window.location = this.$store.getters.getLogoutURL;
                } else {
                    window.location.reload();
                }
            })
        },

        isAuthenticated() {
            return AuthService.isAuthenticated()
        },
        needTokenRefresh() {
            return AuthService.needTokenRefresh()
        },
        checkPermission(permission) {
            return AuthService.hasPermission(permission)
        }
    }
};

export default AuthMixin
