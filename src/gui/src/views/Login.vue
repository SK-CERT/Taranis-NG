<template>
    <v-container class="login-screen pa-0 ma-0" fluid fill-height align-center justify-center v-if="!$store.getters.hasExternalLoginUrl">
        <v-container style="background-color: #c7c7c7; text-align: center; position: relative;" fluid>
            <img src="@/assets/taranis-logo-login.svg" alt="">
            <v-form @submit.prevent="authenticate" id="form" ref="form">
                <table>
                    <tr>
                        <td>
                            <v-flex>
                                <v-text-field
                                        :placeholder="$t('login.username')"
                                        name="username"
                                        prepend-icon="person"
                                        type="text"
                                        v-model="username"
                                        v-validate="'required'"
                                        data-vv-name="username"
                                        :error-messages="errors.collect('username')"
                                />
                            </v-flex>
                        </td>
                        <td>
                            <v-flex>
                                <v-text-field
                                        :placeholder="$t('login.password')"
                                        name="password"
                                        prepend-icon="lock"
                                        type="password"
                                        v-model="password"
                                        v-validate="'required'"
                                        :error-messages="errors.collect('password')"
                                        data-vv-name="password"
                                        required
                                ></v-text-field>
                            </v-flex>
                        </td>
                        <td>
                            <v-btn text type="submit" form="form">
                                <v-icon color="white" large>mdi-login-variant</v-icon>
                            </v-btn>
                        </td>
                    </tr>
                </table>
            </v-form>
        </v-container>
        <v-alert v-if="show_login_error" dense type="error" text>{{$t('login.error')}}</v-alert>
    </v-container>
</template>

<script>

    import AuthMixin from "@/services/auth/auth_mixin";

    export default {
        name: 'Login',
        data: () => ({
            username: '',
            password: '',
            show_login_error: false
        }),
        mixins: [AuthMixin],
        methods: {
            authenticate() {
                if (this.$store.getters.hasExternalLoginUrl) {
                    let req = this.$store.dispatch('login', {params: { code: this.$route.query.code, session_state: this.$route.query.session_state }, method: 'get'});
                    this.validate_authentication(req);
                } else {
                    this.$validator.validateAll().then(() => {

                        if (!this.$validator.errors.any()) {
                            let req = this.$store.dispatch('login', {username: this.username, password: this.password, method: 'post'});
                            this.validate_authentication(req);
                        } else {
                            this.show_login_error = false;
                        }
                    });
                }
            },
            validate_authentication(req) {
                req.then(() => {
                    if (this.isAuthenticated()) {
                        this.show_login_error = false;
                        this.$router.push(this.$router.history.current.query.redirect || '/');
                        this.$root.$emit('logged-in');
                    } else {
                        this.validation_failed();
                    }
                });
            },
            validation_failed() {
                if (this.$store.getters.hasExternalLogoutUrl) {
                    window.location = this.$store.getters.getLogoutURL; // plain redirect without gotoUrl
                } else {
                    this.show_login_error = true;
                    this.$refs.form.reset();
                    this.$validator.reset();
                }
            },
        },
        mounted() {
            if (this.isAuthenticated()) {
                this.$router.push('/dashboard');
                return;
            }
            if (this.$store.getters.hasExternalLoginUrl) {
                if (this.$route.query.code !== undefined && this.$route.query.session_state !== undefined) {
                    this.authenticate();
                } else {
                    window.location = this.$store.getters.getLoginURL; // plain redirect without gotoUrl
                }
            }
        }
    }
</script>
