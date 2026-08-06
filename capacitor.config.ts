import type { CapacitorConfig } from '@capacitor/cli';

// Configuration de l'app native DIVARC (Capacitor). Le front Next.js est exporté
// en statique (BUILD_TARGET=native -> dossier `out/`) puis bundlé dans l'app iOS.
const config: CapacitorConfig = {
  appId: 'fr.divarc.app',
  appName: 'DIVARC',
  webDir: 'out',
  ios: {
    contentInset: 'always',
    backgroundColor: '#0e1020',
    limitsNavigationsToAppBoundDomains: false,
  },
  plugins: {
    SplashScreen: {
      launchShowDuration: 900,
      backgroundColor: '#0e1020',
      showSpinner: false,
      launchAutoHide: true,
    },
    Keyboard: {
      resize: 'native',
    },
  },
};

export default config;
