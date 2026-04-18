<template>
  <div class="fullscreen error-page text-white text-center q-pa-md flex flex-center">
    <div class="glass-container q-pa-xl">
      <div class="error-code">404</div>
      <div class="text-h4 q-mt-md">Lost at sea?</div>
      <div class="text-subtitle1 q-mt-sm text-grey-4">The shark couldn't find the page you're looking for.</div>

      <div class="q-mt-xl row justify-center">
        <q-btn
          outline
          color="white"
          to="/"
          label="Return to Safety"
          no-caps
          class="return-btn q-px-lg"
          size="lg"
        />
      </div>

      <!-- Subtle background element -->
      <div class="shark-accent">
        <img src="tubarao.jpg" alt="" class="pulse-animation" />
      </div>
    </div>
  </div>
</template>

<script>
export default {
  name: 'Error404'
}
</script>

<style scoped>
.error-page {
  background: radial-gradient(circle at center, #1a2a6c, #b21f1f, #fdbb2d);
  background: linear-gradient(135deg, #0b1e3b 0%, #1c3d6c 50%, #0b1e3b 100%);
  overflow: hidden;
}

.glass-container {
  background: rgba(255, 255, 255, 0.03);
  backdrop-filter: blur(15px);
  border: 1px solid rgba(255, 255, 255, 0.1);
  border-radius: 30px;
  max-width: 600px;
  width: 95%;
  box-shadow: 0 25px 50px -12px rgba(0, 0, 0, 0.5);
  position: relative;
  z-index: 10;
  transition: transform 0.3s ease;
}

.glass-container:hover {
  transform: translateY(-5px);
  border-color: rgba(255, 255, 255, 0.2);
}

.error-code {
  font-size: 18vh;
  font-weight: 900;
  letter-spacing: -8px;
  background: linear-gradient(to bottom, #ffffff 30%, rgba(255, 255, 255, 0.2));
  -webkit-background-clip: text;
  background-clip: text;
  -webkit-text-fill-color: transparent;
  line-height: 0.9;
  font-family: 'Outfit', 'Inter', sans-serif;
}

.return-btn {
  border-radius: 12px;
  transition: all 0.4s cubic-bezier(0.175, 0.885, 0.32, 1.275);
}

.return-btn:hover {
  background: rgba(255, 255, 255, 0.1);
  transform: scale(1.05);
}

.shark-accent {
  position: absolute;
  top: -40px;
  right: -40px;
  opacity: 0.15;
  z-index: -1;
  pointer-events: none;
}

.shark-accent img {
  width: 150px;
  height: 150px;
  border-radius: 50%;
  object-fit: cover;
}

.pulse-animation {
  animation: pulse 4s ease-in-out infinite;
}

@keyframes pulse {
  0% { transform: scale(1) rotate(0deg); opacity: 0.1; }
  50% { transform: scale(1.1) rotate(5deg); opacity: 0.2; }
  100% { transform: scale(1) rotate(0deg); opacity: 0.1; }
}

/* For modern typography if not globally available */
@import url('https://fonts.googleapis.com/css2?family=Outfit:wght@400;700;900&display=swap');
</style>
