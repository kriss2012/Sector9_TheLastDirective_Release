Add-Type -AssemblyName System.Speech
$synth = New-Object System.Speech.Synthesis.SpeechSynthesizer
$synth.Rate = 0
$synth.SetOutputToWaveFile('c:/D Drive/Sector9_TheLastDirective/assets/audio/voices/briefing_intro.wav')
$synth.Speak('Command Dispatch: Dreadnought Aegis-9, responding to priority emergency beacon in deep space Sector 9.')
Copy-Item 'c:/D Drive/Sector9_TheLastDirective/assets/audio/voices/briefing_intro.wav' 'c:/D Drive/Sector9_TheLastDirective/Sector9_TheLastDirective_Release/assets/audio/voices/briefing_intro.wav' -Force
$synth.Rate = 0
$synth.SetOutputToWaveFile('c:/D Drive/Sector9_TheLastDirective/assets/audio/voices/briefing_star.wav')
$synth.Speak('Astronomical scan discrepancy confirmed. Deep space coordinates reveal an entire star system vanished from reality.')
Copy-Item 'c:/D Drive/Sector9_TheLastDirective/assets/audio/voices/briefing_star.wav' 'c:/D Drive/Sector9_TheLastDirective/Sector9_TheLastDirective_Release/assets/audio/voices/briefing_star.wav' -Force
$synth.Rate = 0
$synth.SetOutputToWaveFile('c:/D Drive/Sector9_TheLastDirective/assets/audio/voices/briefing_directive.wav')
$synth.Speak('Commander Clara Voss, emergency protocol engaged. Recover the access card from the east bridge bay and unlock the primary blast door.')
Copy-Item 'c:/D Drive/Sector9_TheLastDirective/assets/audio/voices/briefing_directive.wav' 'c:/D Drive/Sector9_TheLastDirective/Sector9_TheLastDirective_Release/assets/audio/voices/briefing_directive.wav' -Force
$synth.Rate = 1
$synth.SetOutputToWaveFile('c:/D Drive/Sector9_TheLastDirective/assets/audio/voices/nova_discrepancy.wav')
$synth.Speak('Long range astronomical discrepancy detected. Star register erased from historical spacetime.')
Copy-Item 'c:/D Drive/Sector9_TheLastDirective/assets/audio/voices/nova_discrepancy.wav' 'c:/D Drive/Sector9_TheLastDirective/Sector9_TheLastDirective_Release/assets/audio/voices/nova_discrepancy.wav' -Force
$synth.Rate = 1
$synth.SetOutputToWaveFile('c:/D Drive/Sector9_TheLastDirective/assets/audio/voices/nova_distress.wav')
$synth.Speak('Incoming distress transmission. Origin... matches Aegis-9 command protocol.')
Copy-Item 'c:/D Drive/Sector9_TheLastDirective/assets/audio/voices/nova_distress.wav' 'c:/D Drive/Sector9_TheLastDirective/Sector9_TheLastDirective_Release/assets/audio/voices/nova_distress.wav' -Force
$synth.Rate = 1
$synth.SetOutputToWaveFile('c:/D Drive/Sector9_TheLastDirective/assets/audio/voices/nova_voice_id.wav')
$synth.Speak('Voice identification confirmed: Commander Clara Voss.')
Copy-Item 'c:/D Drive/Sector9_TheLastDirective/assets/audio/voices/nova_voice_id.wav' 'c:/D Drive/Sector9_TheLastDirective/Sector9_TheLastDirective_Release/assets/audio/voices/nova_voice_id.wav' -Force
$synth.Rate = 1
$synth.SetOutputToWaveFile('c:/D Drive/Sector9_TheLastDirective/assets/audio/voices/nova_emergency.wav')
$synth.Speak('Critical power failure. The Watcher has breached bridge defenses. Proceed to engineering.')
Copy-Item 'c:/D Drive/Sector9_TheLastDirective/assets/audio/voices/nova_emergency.wav' 'c:/D Drive/Sector9_TheLastDirective/Sector9_TheLastDirective_Release/assets/audio/voices/nova_emergency.wav' -Force
$synth.Rate = 1
$synth.SetOutputToWaveFile('c:/D Drive/Sector9_TheLastDirective/assets/audio/voices/nova_welcome.wav')
$synth.Speak('Access granted. Bulkhead blast doors unsealed. Proceed with caution.')
Copy-Item 'c:/D Drive/Sector9_TheLastDirective/assets/audio/voices/nova_welcome.wav' 'c:/D Drive/Sector9_TheLastDirective/Sector9_TheLastDirective_Release/assets/audio/voices/nova_welcome.wav' -Force
$synth.Rate = 1
$synth.SetOutputToWaveFile('c:/D Drive/Sector9_TheLastDirective/assets/audio/voices/nova_warning_drone.wav')
$synth.Speak('Warning: Autonomous security units have entered an unauthorized lethal combat state.')
Copy-Item 'c:/D Drive/Sector9_TheLastDirective/assets/audio/voices/nova_warning_drone.wav' 'c:/D Drive/Sector9_TheLastDirective/Sector9_TheLastDirective_Release/assets/audio/voices/nova_warning_drone.wav' -Force
$synth.Rate = -1
$synth.SetOutputToWaveFile('c:/D Drive/Sector9_TheLastDirective/assets/audio/voices/ward_discrepancy.wav')
$synth.Speak('Define discrepancy, Nova. Run the sensor sweep again.')
Copy-Item 'c:/D Drive/Sector9_TheLastDirective/assets/audio/voices/ward_discrepancy.wav' 'c:/D Drive/Sector9_TheLastDirective/Sector9_TheLastDirective_Release/assets/audio/voices/ward_discrepancy.wav' -Force
$synth.Rate = -1
$synth.SetOutputToWaveFile('c:/D Drive/Sector9_TheLastDirective/assets/audio/voices/ward_transmission.wav')
$synth.Speak('Commander Voss. If this recording is playing, containment has failed. The object beneath Sector 9 is awakening.')
Copy-Item 'c:/D Drive/Sector9_TheLastDirective/assets/audio/voices/ward_transmission.wav' 'c:/D Drive/Sector9_TheLastDirective/Sector9_TheLastDirective_Release/assets/audio/voices/ward_transmission.wav' -Force
$synth.Rate = 2
$synth.SetOutputToWaveFile('c:/D Drive/Sector9_TheLastDirective/assets/audio/voices/clara_stars.wav')
$synth.Speak('Stars do not simply vanish from a military database, Captain.')
Copy-Item 'c:/D Drive/Sector9_TheLastDirective/assets/audio/voices/clara_stars.wav' 'c:/D Drive/Sector9_TheLastDirective/Sector9_TheLastDirective_Release/assets/audio/voices/clara_stars.wav' -Force
$synth.Rate = 2
$synth.SetOutputToWaveFile('c:/D Drive/Sector9_TheLastDirective/assets/audio/voices/clara_ship.wav')
$synth.Speak('Wait... we are the Aegis-9. That distress call... that was my voice.')
Copy-Item 'c:/D Drive/Sector9_TheLastDirective/assets/audio/voices/clara_ship.wav' 'c:/D Drive/Sector9_TheLastDirective/Sector9_TheLastDirective_Release/assets/audio/voices/clara_ship.wav' -Force
$synth.Rate = -1
$synth.SetOutputToWaveFile('c:/D Drive/Sector9_TheLastDirective/assets/audio/voices/malik_intro.wav')
$synth.Speak('Clara, if you are calling about the explosion, I noticed. I need the maintenance tool from the locker.')
Copy-Item 'c:/D Drive/Sector9_TheLastDirective/assets/audio/voices/malik_intro.wav' 'c:/D Drive/Sector9_TheLastDirective/Sector9_TheLastDirective_Release/assets/audio/voices/malik_intro.wav' -Force
$synth.Rate = -2
$synth.SetOutputToWaveFile('c:/D Drive/Sector9_TheLastDirective/assets/audio/voices/watcher_whisper.wav')
$synth.Speak('You were never supposed to hear that, Clara. The answer depends on which version of you survives.')
Copy-Item 'c:/D Drive/Sector9_TheLastDirective/assets/audio/voices/watcher_whisper.wav' 'c:/D Drive/Sector9_TheLastDirective/Sector9_TheLastDirective_Release/assets/audio/voices/watcher_whisper.wav' -Force
$synth.Dispose()
Write-Host 'VOICE_GEN_COMPLETE'