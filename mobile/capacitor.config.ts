import { CapacitorConfig } from '@capacitor/cli';

const config: CapacitorConfig = {
  appId:   'si.scpet.stefetnitek',
  appName: 'Štafetni Tek',
  webDir:  'www',

  plugins: {
    SplashScreen: {
      launchShowDuration: 2000,
      launchAutoHide: true,
      backgroundColor: '#050a07',
      androidSplashResourceName: 'splash',
      showSpinner: false,
    },
    StatusBar: {
      style: 'DARK',
      backgroundColor: '#050a07',
    },
    LocalNotifications: {
      smallIcon: 'ic_stat_notify',
      iconColor: '#22c55e',
    },
    BluetoothLe: {
      displayStrings: {
        scanning: 'Iščem naprave…',
        cancel: 'Prekliči',
        availableDevices: 'Naprave v bližini',
        noDeviceFound: 'Ni naprav',
      },
    },
  },
};

export default config;
