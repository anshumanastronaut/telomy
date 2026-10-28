import { DarkTheme, DefaultTheme, Stack, ThemeProvider } from 'expo-router';
import { BricolageGrotesque_400Regular, BricolageGrotesque_500Medium, BricolageGrotesque_600SemiBold, BricolageGrotesque_700Bold } from '@expo-google-fonts/bricolage-grotesque';
import { Fraunces_400Regular, Fraunces_500Medium } from '@expo-google-fonts/fraunces';
import { Geist_300Light, Geist_400Regular, Geist_500Medium, Geist_600SemiBold, Geist_700Bold } from '@expo-google-fonts/geist';
import { InstrumentSerif_400Regular } from '@expo-google-fonts/instrument-serif';
import { GeistMono_400Regular, GeistMono_500Medium, GeistMono_600SemiBold } from '@expo-google-fonts/geist-mono';
import { HankenGrotesk_300Light, HankenGrotesk_400Regular, HankenGrotesk_500Medium, HankenGrotesk_600SemiBold, HankenGrotesk_700Bold } from '@expo-google-fonts/hanken-grotesk';
import { Inter_300Light, Inter_400Regular, Inter_500Medium, Inter_600SemiBold } from '@expo-google-fonts/inter';
import { SchibstedGrotesk_400Regular, SchibstedGrotesk_500Medium, SchibstedGrotesk_600SemiBold, SchibstedGrotesk_700Bold } from '@expo-google-fonts/schibsted-grotesk';
import { useFonts } from 'expo-font';
import * as SplashScreen from 'expo-splash-screen';
import { StatusBar } from 'expo-status-bar';
import { useEffect, useState } from 'react';
import { View } from 'react-native';

import { RoleProvider } from '@/lib/role';
import { fonts, usePalette, useScheme } from '@/lib/theme';
import { Intro } from '@/ui/intro';
import { LockScreen } from '@/ui/lock';
import { onLockChange } from '@/lib/api';

SplashScreen.preventAutoHideAsync().catch(() => {});

export default function RootLayout() {
  const scheme = useScheme();
  const p = usePalette();
  const base = scheme === 'dark' ? DarkTheme : DefaultTheme;
  const theme = { ...base, colors: { ...base.colors, background: p.bg, card: p.bg, text: p.text, border: p.border, primary: p.teal } };
  const sheet = { presentation: 'modal' as const, headerShown: false };
  const [loaded] = useFonts({
    HankenGrotesk_300Light,
    HankenGrotesk_400Regular,
    HankenGrotesk_500Medium,
    HankenGrotesk_600SemiBold,
    HankenGrotesk_700Bold,
    Inter_300Light,
    Inter_400Regular,
    Inter_500Medium,
    Inter_600SemiBold,
    Fraunces_400Regular,
    Fraunces_500Medium,
    Geist_300Light,
    Geist_400Regular,
    Geist_500Medium,
    Geist_600SemiBold,
    Geist_700Bold,
    BricolageGrotesque_400Regular,
    BricolageGrotesque_500Medium,
    BricolageGrotesque_600SemiBold,
    BricolageGrotesque_700Bold,
    InstrumentSerif_400Regular,
    TelomySans_Thin: require('../../assets/fonts/TelomySans-Thin.ttf'),
    TelomySans_Light: require('../../assets/fonts/TelomySans-Light.ttf'),
    TelomySans_Regular: require('../../assets/fonts/TelomySans-Regular.ttf'),
    TelomySans_Bold: require('../../assets/fonts/TelomySans-Bold.ttf'),
    GeistMono_400Regular,
    GeistMono_500Medium,
    GeistMono_600SemiBold,
    SchibstedGrotesk_400Regular,
    SchibstedGrotesk_500Medium,
    SchibstedGrotesk_600SemiBold,
    SchibstedGrotesk_700Bold,
  });
  const [intro, setIntro] = useState(true);
  const [locked, setLocked] = useState(false);
  useEffect(() => onLockChange(setLocked), []);
  useEffect(() => {
    if (loaded) SplashScreen.hideAsync().catch(() => {});
  }, [loaded]);
  if (!loaded) return <View style={{ flex: 1, backgroundColor: '#000' }} />;
  return (
    <RoleProvider>
    <ThemeProvider value={theme}>
      <StatusBar style={scheme === 'dark' ? 'light' : 'dark'} />
      {intro ? <Intro onDone={() => setIntro(false)} /> : null}
      <Stack screenOptions={{ headerTintColor: p.teal, headerTitleStyle: { color: p.text, fontFamily: fonts.bold }, headerShadowVisible: false, headerBackButtonDisplayMode: 'minimal', contentStyle: { backgroundColor: p.bg } }}>
        <Stack.Screen name="(tabs)" options={{ headerShown: false }} />
        <Stack.Screen name="onboarding" options={{ headerShown: false, presentation: 'fullScreenModal' }} />
        <Stack.Screen name="log" options={sheet} />
        <Stack.Screen name="upload" options={sheet} />
        <Stack.Screen name="breathe" options={{ headerShown: false, presentation: 'fullScreenModal' }} />
        <Stack.Screen name="insight/[id]" options={{ title: '' }} />
        <Stack.Screen name="marker/[id]" options={{ title: '' }} />
        <Stack.Screen name="signal/[id]" options={{ title: '' }} />
        <Stack.Screen name="domain/[key]" options={{ title: '' }} />
        <Stack.Screen name="report/[id]" options={{ title: '' }} />
        <Stack.Screen name="longevity" options={{ title: 'Longevity age' }} />
        <Stack.Screen name="age" options={{ title: 'Biological age' }} />
        <Stack.Screen name="about" options={{ title: 'About you' }} />
        <Stack.Screen name="trackers" options={{ title: 'Your trackers' }} />
        <Stack.Screen name="home-settings" options={{ title: 'Home layout' }} />
        <Stack.Screen name="tracker/[id]" options={{ title: 'Tracker' }} />
        <Stack.Screen name="muscle" options={{ title: 'Muscle age test' }} />
        <Stack.Screen name="insurance" options={{ title: 'Insurance' }} />
        <Stack.Screen name="training" options={{ title: 'Exercise & training' }} />
        <Stack.Screen name="risks" options={{ title: '' }} />
        <Stack.Screen name="menu" options={{ title: 'Weekly menu' }} />
        <Stack.Screen name="studies" options={{ title: 'N-of-1 studies' }} />
        <Stack.Screen name="marketplace" options={{ title: 'Protocol Marketplace' }} />
        <Stack.Screen name="consent" options={{ title: 'Consent centre' }} />
        <Stack.Screen name="family" options={{ title: 'Family Vault' }} />
        <Stack.Screen name="care" options={{ title: 'Clinicians' }} />
        <Stack.Screen name="brief" options={{ title: 'Specialist pack' }} />
        <Stack.Screen name="completeness" options={{ title: 'Vault completeness' }} />
        <Stack.Screen name="research" options={{ title: 'Research' }} />
        <Stack.Screen name="memory" options={{ title: 'What Sinc remembers' }} />
        <Stack.Screen name="emergency" options={{ title: 'Emergency card' }} />
        <Stack.Screen name="imaging" options={{ title: 'Imaging' }} />
        <Stack.Screen name="queue" options={{ title: 'Telomy Care · review queue' }} />
        <Stack.Screen name="goals" options={{ title: 'Goals' }} />
        <Stack.Screen name="activity" options={{ title: 'Activity & recovery' }} />
        <Stack.Screen name="browse" options={{ title: 'Browse' }} />
        <Stack.Screen name="meds" options={{ title: 'Medications' }} />
        <Stack.Screen name="notifications" options={{ title: 'Notifications' }} />
        <Stack.Screen name="notes" options={{ title: 'Clinician notes' }} />
        <Stack.Screen name="nutrition" options={{ title: 'Nutrition' }} />
        <Stack.Screen name="pins" options={{ title: 'Pinned to Home' }} />
        <Stack.Screen name="monitor" options={{ title: 'Live ECG' }} />
        <Stack.Screen name="ring" options={{ title: 'Smart ring' }} />
        <Stack.Screen name="devices" options={{ title: 'Devices' }} />
        <Stack.Screen name="wellness/[metric]" options={{ title: '' }} />
        <Stack.Screen name="event" options={{ presentation: 'formSheet', headerShown: false, sheetGrabberVisible: true, sheetAllowedDetents: [0.75, 1], sheetCornerRadius: 28 }} />
        <Stack.Screen name="capture" options={{ title: 'Therapy capture' }} />
        <Stack.Screen name="captures" options={{ title: 'Saved sessions' }} />
        <Stack.Screen name="ecg/[id]" options={{ title: 'ECG' }} />
        <Stack.Screen name="welcome" options={{ headerShown: false, animation: 'fade' }} />
        <Stack.Screen name="doctor" options={{ headerShown: false }} />
        <Stack.Screen name="centre" options={{ headerShown: false }} />
        <Stack.Screen name="patient/[id]" options={{ title: 'Patient' }} />
        <Stack.Screen name="predict" options={{ title: 'Disease predictions' }} />
        <Stack.Screen name="plans" options={{ title: 'Plans' }} />
        <Stack.Screen name="monthly" options={{ title: '' }} />
        <Stack.Screen name="consult" options={{ title: 'Consult a doctor' }} />
        <Stack.Screen name="therapy/[id]" options={{ title: 'Therapy' }} />
        <Stack.Screen name="session/[id]" options={{ title: 'Session' }} />
        <Stack.Screen name="therapy-plan" options={{ title: 'Therapy plan' }} />
        <Stack.Screen name="therapies" options={{ title: 'All therapies' }} />
        <Stack.Screen name="tests" options={{ title: 'Tests & scans' }} />
        <Stack.Screen name="rx" options={{ title: 'Supplements & Rx' }} />
        <Stack.Screen name="review/[id]" options={{ title: 'Report review' }} />
        <Stack.Screen name="centre-research" options={{ title: 'Outcomes & research' }} />
        <Stack.Screen name="voice" options={{ title: 'Talk to Sinc' }} />
        <Stack.Screen name="twin" options={{ title: 'Digital twin' }} />
        <Stack.Screen name="routine" options={{ title: 'My routine' }} />
        <Stack.Screen name="activities" options={{ title: 'My activities' }} />
        <Stack.Screen name="activity/[id]" options={{ title: 'Activity' }} />
        <Stack.Screen name="environment" options={{ title: 'Environment' }} />
        <Stack.Screen name="visits" options={{ title: '' }} />
        <Stack.Screen name="insights" options={{ title: '' }} />
        <Stack.Screen name="assistance" options={{ title: '' }} />
        <Stack.Screen name="measure" options={{ headerShown: false, presentation: 'fullScreenModal' }} />
        <Stack.Screen name="ratios" options={{ title: 'Lab insights' }} />
        <Stack.Screen name="score" options={{ title: 'Telomy Score' }} />
      </Stack>
      {locked && !intro ? <LockScreen /> : null}
    </ThemeProvider>
    </RoleProvider>
  );
}
