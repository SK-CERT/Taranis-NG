<template>
  <div v-if="!authStore.hasExternalLoginUrl" class="login-screen">
    <!-- Logo -->
    <div class="logo-container">
      <img src="@/assets/taranis-logo-login.svg" alt="Taranis NG" class="login-logo">
    </div>

    <!-- Login Form -->
    <v-form id="login-form" class="login-form" @submit.prevent="handleFormSubmit">
      <div class="form-fields">
        <v-text-field
          v-model="username"
          name="username"
          data-test="login-username"
          :placeholder="t('login.username')"
          prepend-icon="mdi-account"
          variant="outlined"
          density="comfortable"
          :error="!!usernameError"
          :error-messages="usernameError ? [usernameError] : []"
          class="login-field"
          @blur="validateUsername"
        />

        <v-text-field
          v-model="password"
          name="password"
          data-test="login-password"
          :placeholder="t('login.password')"
          prepend-icon="mdi-lock"
          :type="showPassword ? 'text' : 'password'"
          variant="outlined"
          density="comfortable"
          :error="!!passwordError"
          :error-messages="passwordError ? [passwordError] : []"
          class="login-field"
          @blur="validatePassword"
        >
          <template #append-inner>
            <v-icon
              class="password-toggle"
              :icon="showPassword ? 'mdi-eye-off' : 'mdi-eye'"
              @click="showPassword = !showPassword"
            />
          </template>
        </v-text-field>
      </div>

      <div class="form-actions">
        <v-btn
          type="submit"
          data-test="login-submit"
          prepend-icon="mdi-login-variant"
          size="large"
          class="login-btn"
        >
          {{ t('login.login') }}
        </v-btn>
      </div>
    </v-form>

    <!-- Error Alert -->
    <v-alert
      v-if="showLoginError"
      data-test="login-error"
      type="error"
      density="compact"
      class="error-alert"
      closable
      @click:close="showLoginError = false"
    >
      {{ t('login.error') }}
    </v-alert>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import { useI18n } from 'vue-i18n'
import { useField, useForm } from 'vee-validate'
import { useAuthStore } from '@/stores/auth'
import { useAuth } from '@/composables/useAuth'

const router = useRouter()
const route = useRoute()
const { t } = useI18n()
const authStore = useAuthStore()
const { isAuthenticated } = useAuth()

// Form validation setup
const { handleSubmit, resetForm } = useForm()

const {
  value: username,
  errorMessage: usernameError,
  validate: validateUsername
} = useField('username', (value) => {
  if (!value) return t('validations.custom.username.required')
  return true
})

const {
  value: password,
  errorMessage: passwordError,
  validate: validatePassword
} = useField('password', (value) => {
  if (!value) return t('validations.custom.password.required')
  return true
})

const showLoginError = ref(false)
const showPassword = ref(false)

/**
 * Handle form submission with validation
 */
const handleFormSubmit = async () => {
  // Validate all fields
  await validateUsername()
  await validatePassword()

  // If no errors, proceed with login
  if (!usernameError.value && !passwordError.value && username.value && password.value) {
    showLoginError.value = false

    try {
      if (authStore.hasExternalLoginUrl) {
        // External authentication (OAuth/Keycloak)
        const req = authStore.login({
          params: {
            code: route.query.code,
            session_state: route.query.session_state
          },
          method: 'get'
        })
        await req
      } else {
        // Internal authentication
        const req = authStore.login({
          username: username.value,
          password: password.value,
          method: 'post'
        })
        await req
      }

      if (isAuthenticated()) {
        showLoginError.value = false
        const redirect = route.query.redirect || '/'
        router.push(redirect)
      } else {
        validationFailed()
      }
    } catch (error) {
      console.error('[Login] Authentication error:', error)
      validationFailed()
    }
  }
}

/**
 * Handle validation failure
 */
const validationFailed = () => {
  if (authStore.hasExternalLogoutUrl) {
    // Redirect to external logout (no gotoUrl)
    window.location.href = authStore.getLogoutURL
  } else {
    showLoginError.value = true
    resetForm()
  }
}

/**
 * Component mount - handle authentication flow
 */
onMounted(() => {
  // If already authenticated, redirect to dashboard
  if (isAuthenticated()) {
    router.push('/dashboard')
    return
  }

  // Handle external login flow
  if (authStore.hasExternalLoginUrl) {
    if (route.query.code !== undefined && route.query.session_state !== undefined) {
      // Complete external auth with code
      handleFormSubmit()
    } else {
      // Redirect to external login
      window.location.href = authStore.getLoginURL
    }
  }
})
</script>

<style scoped>
/* ===== Light Theme (Default) ===== */
.login-screen {
  width: 100%;
  min-height: 100vh;
  background-color: var(--color-light-bg-secondary);
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: 20px;
  gap: 30px;
}

.logo-container {
  flex: 0 0 auto;
  display: flex;
  justify-content: center;
  align-items: center;
  order: 1;
  width: 100%;
  min-height: 150px;
}

.login-logo {
  max-width: 400px;
  width: 80%;
  height: auto;
  display: block;
  filter: drop-shadow(var(--color-light-shadow-small));
}

.login-form {
  flex: 0 0 auto;
  order: 2;
  width: 100%;
  max-width: 400px;
  display: flex;
  flex-direction: column;
  gap: 16px;
  background-color: var(--color-light-surface-primary);
  padding: 24px;
  border-radius: 6px;
  border: 1px solid var(--color-light-border-primary);
  will-change: auto;
}

.form-fields {
  display: flex;
  flex-direction: column;
  gap: 12px;
  flex: 1;
  min-width: 0;
}

.login-field {
  width: 100%;
  min-width: 200px;
  flex-shrink: 0;
}

.login-field :deep(.v-field) {
  background-color: var(--color-light-field-bg) !important;
  min-height: 56px;
}

.login-field :deep(.v-icon) {
  color: var(--color-light-icon-primary);
}

.login-field :deep(.v-field--error .v-field__outline__start),
.login-field :deep(.v-field--error .v-field__outline__end),
.login-field :deep(.v-field--error .v-field__outline__notch) {
  border-color: var(--v-theme-error) !important;
}

.login-field :deep(.v-field--error .v-prepend-inner .v-icon) {
  color: var(--v-theme-error) !important;
}

.password-toggle {
  cursor: pointer;
  user-select: none;
}

.form-actions {
  display: flex;
  justify-content: center;
  gap: 12px;
  flex-shrink: 0;
}

.login-btn {
  background-color: var(--color-light-surface-interactive);
  color: white;
  flex-shrink: 0;
  min-width: 140px;
}

.login-btn:hover {
  background-color: var(--color-light-surface-interactive-hover);
}

.error-alert {
  position: fixed;
  bottom: 0;
  left: 0;
  right: 0;
  width: 100%;
  max-height: 80px;
  margin: 0;
  border-radius: 0;
  z-index: 1000;
  overflow: hidden;
}

/* ===== Dark Theme ===== */
@media (prefers-color-scheme: dark) {
  .login-screen {
    background: var(--color-dark-bg-primary);
  }

  .login-logo {
    filter: drop-shadow(var(--color-dark-shadow-small));
  }

  .login-form {
    background-color: var(--color-dark-surface-primary);
    border-color: var(--color-dark-border-primary);
  }

  .login-field :deep(.v-field) {
    background-color: var(--color-dark-field-bg) !important;
  }

  .login-field :deep(.v-field__input) {
    color: var(--color-dark-text-primary) !important;
  }

  .login-field :deep(.v-field__input::placeholder) {
    color: var(--color-dark-text-muted) !important;
  }

  .login-field :deep(.v-icon) {
    color: var(--color-dark-icon-primary);
  }

  .login-field :deep(.v-field__outline__start),
  .login-field :deep(.v-field__outline__end),
  .login-field :deep(.v-field__outline__notch) {
    border-color: var(--color-dark-border-secondary) !important;
  }

  .login-field :deep(.v-field--error .v-field__outline__start),
  .login-field :deep(.v-field--error .v-field__outline__end),
  .login-field :deep(.v-field--error .v-field__outline__notch) {
    border-color: var(--v-theme-error) !important;
  }

  .login-field :deep(.v-field--error .v-prepend-inner .v-icon) {
    color: var(--v-theme-error) !important;
  }

  .password-toggle {
    cursor: pointer;
    user-select: none;
  }

  .login-btn {
    background-color: var(--color-dark-surface-interactive);
    color: var(--color-dark-text-primary);
    min-width: 140px;
  }

  .login-btn:hover {
    background-color: var(--color-dark-surface-interactive-hover);
  }

  .error-alert {
    background-color: var(--v-theme-error) !important;
    border-color: var(--v-theme-error) !important;
  }
}

/* ===== Responsive ===== */
@media (max-width: 600px) {
  .login-screen {
    padding: 16px;
  }

  .login-form {
    max-width: 100%;
  }

  .login-logo {
    max-width: 200px;
  }
}
</style>
