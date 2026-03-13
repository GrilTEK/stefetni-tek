import { CapacitorConfig } from "@capacitor/cli";

const config: CapacitorConfig = {
  appId: "si.scpet.stefetnitek",
  appName: "Štafetni Tek",
  webDir: "www",
  server: {
    androidScheme: "https",
  },
  plugins: {
    SplashScreen: {
      launchShowDuration: 2000,
      backgroundColor: "#050a07",
      androidSplashResourceName: "splash",
      showSpinner: false,
    },
    StatusBar: {
      style: "Dark",
      backgroundColor: "#050a07",
    },
    LocalNotifications: {
      smallIcon: "ic_stat_icon_config_sample",
      iconColor: "#22c55e",
      sound: "beep.wav",
    },
    BluetoothLe: {
      displayStrings: {
        scanning: "Iščem naprave…",
        cancel: "Prekliči",
        availableDevices: "Razpoložljive naprave",
        noDeviceFound: "Ni naprav",
      },
    },
  },
};

export default config;
