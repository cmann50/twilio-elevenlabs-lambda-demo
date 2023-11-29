# twilio-elevenlabs-lambda-demo
A demo showing near real time streaming between twilio and elevenlabs

This was deployed as a lambda, have a look at the dockerfile as ffmpeg was needed to convert audio.

Needed to use a monkey patch. Variable rate mp3 default audio doesn't work with twilio.

