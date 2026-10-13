Pod::Spec.new do |s|
  s.name           = 'KyEcg'
  s.version        = '0.1.0'
  s.summary        = 'Telomy client for the KY-E-B1 single-lead ECG band'
  s.description    = 'Bluetooth protocol, live ECG analysis (QRS detection, signal quality, HRV) and on-device recording sync.'
  s.author         = 'Telomy'
  s.homepage       = 'https://telomy.com'
  s.license        = { :type => 'Proprietary' }
  s.platforms      = { :ios => '15.1' }
  s.source         = { git: '' }
  s.static_framework = true
  s.dependency 'ExpoModulesCore'
  s.frameworks     = 'CoreBluetooth', 'HealthKit'
  s.source_files   = '**/*.swift'
  s.resource_bundles = { 'KyEcgModels' => ['Resources/*.json'] }  # sleep-stager weights (telomy-lab/sleepstage)
  s.pod_target_xcconfig = { 'DEFINES_MODULE' => 'YES', 'SWIFT_COMPILATION_MODE' => 'wholemodule' }
end
