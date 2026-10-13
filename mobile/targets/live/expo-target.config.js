/** Live Activity for the ECG band: live heart rate on the Lock Screen and in the Dynamic Island. */
module.exports = {
  type: 'widget',
  name: 'TelomyLive',
  displayName: 'Telomy Live',
  bundleIdentifier: '.live',
  deploymentTarget: '16.4',
  frameworks: ['SwiftUI', 'WidgetKit', 'ActivityKit'],
  colors: { $accent: '#5CC9A7', $widgetBackground: '#0B1210' },
};
