<template>
  <q-layout view="lHh Lpr lFf" class="bg-grey-2">
    <q-page-container>
      <q-page class="flex flex-center">
        <q-card class="signup-card shadow-10">
          <q-card-section class="q-pt-lg text-center">
            <img class="avatar" src="tubarao.jpg" alt="Logo" />
            <div class="text-h5 text-weight-bold q-mt-md color-primary">Create Account</div>
            <div class="text-subtitle2 text-grey-7 q-mb-md">Join Shark Subtitles today</div>
          </q-card-section>

          <q-card-section class="q-px-lg">
            <q-form @submit="cadastrar" class="q-gutter-y-sm">
              <q-input
                v-model="user.name"
                label="Full Name"
                outlined
                dense
                lazy-rules
                :rules="[(val) => (val && val.length > 0) || 'Name is required']"
              >
                <template v-slot:prepend>
                  <q-icon name="person" />
                </template>
              </q-input>

              <q-input
                v-model="user.email"
                label="Email Address"
                type="email"
                outlined
                dense
                lazy-rules
                :rules="[
                  (val) => (val && val.length > 0) || 'Email is required',
                  (val) => {
                    const hasLetter = /[a-zA-Z]/.test(val);
                    return hasLetter || 'Email must contain letters (e.g. user@gmail.com)';
                  }
                ]"
              >
                <template v-slot:prepend>
                  <q-icon name="email" />
                </template>
              </q-input>

              <q-input
                type="password"
                v-model="user.password"
                label="Password"
                outlined
                dense
                lazy-rules
                :rules="[(val) => (val && val.length >= 6) || 'Password must be at least 6 characters']"
              >
                <template v-slot:prepend>
                  <q-icon name="lock" />
                </template>
              </q-input>

              <q-input
                type="password"
                v-model="confpass"
                label="Confirm Password"
                outlined
                dense
                lazy-rules
                :rules="[
                  (val) => (val && val.length > 0) || 'Please confirm your password',
                  (val) => val === user.password || 'Passwords do not match',
                ]"
              >
                <template v-slot:prepend>
                  <q-icon name="lock_clock" />
                </template>
              </q-input>

              <div class="q-mt-lg">
                <q-btn
                  :loading="loading"
                  label="Sign Up"
                  type="submit"
                  color="primary"
                  class="full-width signup-btn"
                  unelevated
                  rounded
                />
              </div>

              <div class="row justify-center q-mt-md">
                <div class="text-grey-7">
                  Already registered?
                  <span class="text-primary cursor-pointer text-weight-bold" @click="$router.push('/')">
                    Sign In
                  </span>
                </div>
              </div>
            </q-form>
          </q-card-section>
        </q-card>
      </q-page>
    </q-page-container>
  </q-layout>
</template>

<script>
import authService from '../service/authService'
export default {
  data () {
    return {
      user: {
        name: '',
        password: '',
        email: ''
      },
      confpass: '',
      loading: false
    }
  },
  methods: {
    async cadastrar () {
      const { email: username, password, name } = this.user
      try {
        this.loading = true
        await authService.signUp({ username, password, name })
        this.$q.notify({
          message: 'Registration successful! Please sign in.',
          color: 'positive',
          icon: 'check_circle',
          position: 'top'
        })
        this.$router.push('/')
      } catch (err) {
        console.error('Sign up error:', err)
        this.$q.notify({
          message: err.message || (typeof err === 'string' ? err : 'Error processing registration'),
          color: 'negative',
          icon: 'report_problem',
          position: 'top'
        })
      } finally {
        this.loading = false
      }
    }
  }
}
</script>

<style lang="stylus" scoped>
.signup-card {
  width: 100%;
  max-width: 400px;
  border-radius: 12px;
  padding: 10px;
}

.avatar {
  width: 90px;
  height: 90px;
  border-radius: 50%;
  border: 3px solid $primary;
  object-fit: cover;
}

.signup-btn {
  height: 50px;
  font-size: 1.1rem;
}

.color-primary {
  color: $primary;
}

.q-page {
  background: linear-gradient(135deg, #f5f7fa 0%, #c3cfe2 100%);
}
</style>
