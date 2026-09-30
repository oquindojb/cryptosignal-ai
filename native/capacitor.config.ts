import type { CapacitorConfig } from '@capacitor/cli';

const config: CapacitorConfig = {
  appId: 'ai.cryptosignal.mobile',
  appName: 'CryptoSignal AI',
  webDir: '../app',
  server: { androidScheme: 'https' },
  plugins: {
    PushNotifications: { presentationOptions: ['badge', 'sound', 'alert'] }
  }
};
export default config;
