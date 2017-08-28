#!/usr/bin/env python

""" basic example demonstrating client usage """

#from __future__ import print_function
#from __future__ import absolute_import
#from __future__ import unicode_literals
import os
import sys
import io
import time
import yaml
import sounddevice as sd
import numpy as np
#import pyaudio
#import wave
import vlc
import playsound
import threading

sys.path.append(os.path.join(os.path.dirname(__file__), '..'))
sys.path.append(os.path.join(os.path.dirname(__file__), '../KittAI'))

import simpleavs  # pylint: disable=wrong-import-position
import snowboydecoder

_EXAMPLES_DIR = os.path.dirname(__file__)
_KITT_DIR = os.path.join(_EXAMPLES_DIR, '../KittAI/resources')
_CONFIG_PATH = os.path.join(_EXAMPLES_DIR, 'example_client_config.yml')
_REQUEST_PATH = os.path.join(_EXAMPLES_DIR, 'testFiles/weather.wav')
_OUTPUT_PATH = os.path.join(_EXAMPLES_DIR, 'output.wav')
_MODEL = os.path.join(_KITT_DIR, 'beatsbox.pmdl')

CHUNK = 20480

#  import logging
#  logging.basicConfig(stream=sys.stdout, level=logging.INFO)
audioData = np.array([], dtype=np.int16)

# audiodevice = pyaudio.PyAudio()

duration = 3
rate = 16000

interrupted = False
moreExpected = False
mediaPlayer = vlc.MediaPlayer()

def state_callback(event, player):
    global audioplaying

    state = player.get_state()

    if state == vlc.State.Ended:
        audioplaying = False

# def play_audio(file):

#     global p, audioplaying

#     i = vlc.Instance()
#     mrl = ""

#     mrl = "{}".format(file)
    
#     if mrl != "":
#         m = i.media_new(mrl)
#         p = i.media_player_new()
#         p.set_media(m)
#         volume = p.audio_get_volume()  # use value set by mixer
#         if volume == 0:
#             print ("WARNING: ALSA reporting volume is zero (off)")
#         mm = m.event_manager()
#         #mm.event_attach(vlc.EventType.MediaPlayerTimeChanged, pos_callback)
#         #mm.event_attach(vlc.EventType.MediaParsedChanged, meta_callback, m)
#         mm.event_attach(vlc.EventType.MediaStateChanged, state_callback, p)
#         audioplaying = True
#         p.audio_set_volume(volume)
#         time.sleep(1)
#         p.play()
#     else:
#         print("(play_audio) mrl = Nothing!")

def fiveSecRecogniser():
    global avs, myrecording

    sd.default.channels = 1
    sd.default.samplerate = rate
    sd.default.dtype = np.int16

    myrecording = sd.rec(int(duration * rate))
    print('Recording ...')
    sd.wait()

    # print('Playing back ...')
    # sd.play(myrecording, rate)

    # time.sleep(3)

    sd.stop()

    rf = open('newrecording.wav', 'w')
    rf.write(myrecording)
    rf.close()

    with io.open('newrecording.wav', 'rb') as request_file:
        request_data = request_file.read()

    request_file.close()

    print('Sending Alexa a voice request')
    avs.speech_recognizer.recognize(audio_data=request_data,
                                    profile='NEAR_FIELD')
playtoken = None

def startPlaying(playevent):
    global mediaPlayer, avs, playtoken

    print("play url event...")
    audio_url = playevent['audio_data']
    mediaPlayer.set_mrl(audio_url)
    mediaPlayer.play()

    playtoken= playevent.token

    avs.audio_player.update_state(token=playevent.token, offset_ms=0, player_activity='PLAYING')
    avs.audio_player.playback_started(playevent.token, 0)

def stopPlaying(playevent):
    global mediaPlayer, avs, playtoken
    print ("getting a stop streaming")
    mediaPlayer.stop()
    avs.audio_player.update_state(token=playevent.token, offset_ms=0, player_activity='STOPPED')
    avs.audio_player.playback_stopped(playtoken, 0)
    playtoken = None

def play_audio(file):
    os.system('play ' + file)

def signal_handler():
    global interrupted, detector, moreExpected

    detector.pause()

    snowboydecoder.play_audio_file()
    
    fiveSecRecogniser()

    while moreExpected:
        moreExpected = False
        fiveSecRecogniser()

    detector.resume()

def interrupt_callback():
    global interrupted
    return interrupted
    
def miccallback(indata, frames, time, status):
    global audioData, moreExpected
    audioData = np.append(audioData, indata)

def hotwordthread():
    global moreExpected, detector

    detector = snowboydecoder.HotwordDetector('/Users/gian/Documents/MyDocuments/Technical/Projects/Audio/SmartSpeaker/BeatsAlexa/KittAI/resources/beatsbox.pmdl', sensitivity=0.65)
    print('Listening... Press Ctrl+C to exit')

    # main loop
    detector.start(detected_callback=signal_handler,
                   interrupt_check=interrupt_callback,
                   sleep_time=0.03)

    print ("Hot Word decoder terminating...")
    detector.terminate()

def main():
    global audioData, myrecording, avs, moreExpected, interrupted
    """ basic example demonstrating client usage """
    avs = None

    def handle_stop(speak_directive):
        """ called when a stop directive is received from AVS """
        print('Received a Stop directive from Alexa')

    def handle_speak(speak_directive):
        """ called when a speak directive is received from AVS """
        print('Received a Speak directive from Alexa')
        print('Notifying AVS that we have started speaking')
        avs.speech_synthesizer.speech_started(speak_directive.token)

        # save the mp3 audio that AVS sent us as part of the Speak directive
        print('(play speak.mp3 to hear how Alexa responded)')
        with io.open('speak2.mp3', 'wb') as speak_file:
            speak_file.write(speak_directive.audio_data)

        play_audio('speak2.mp3')

        #time.sleep(10)

        print('Notifying AVS that we have finished speaking')
        avs.speech_synthesizer.speech_finished(speak_directive.token)

    def handle_expect(speak_directive):
        global moreExpected
        print('Received a handle_expect directive from Alexa')
        moreExpected = True

    with io.open(_CONFIG_PATH, 'r') as cfile:
        config = yaml.load(cfile)

    # AvsClient requires a dict with client_id, client_secret, refresh_token
    avs = simpleavs.AvsClient(config)

    # handle the Speak directive event when sent from AVS
    avs.speech_synthesizer.speak_event += handle_speak
    avs.speech_recognizer.stop_capture_event += handle_stop
    avs.speech_recognizer.expect_speech_event += handle_expect

    avs.audio_player.play_event += startPlaying
    avs.audio_player.stop_event += stopPlaying

    print('Connecting to AVS')
    avs.connect()

    rec_thread = threading.Thread(target=hotwordthread)

    rec_thread.start()

    print('rec_thread started')

    while True:
        a = sys.stdin.read(1)
        a = a.strip()

        if(a in ('q', 'Q')):
            print('Reading input - ' + a)
            break

    interrupted = True

    print('Shutting down')

    #rec_thread.stop()

    print('Disconnecting from AVS')
    avs.disconnect()

    # with inStream:
    #     while True:
    #         time.sleep(5)
    #         #print ("data - ", audioData)
    #         audioDataString = ''.join(str(elm) for elm in audioData)

    #         with io.open(_OUTPUT_PATH, 'wb') as output_file:
    #             output_file.write(audioDataString)

    #         #avs.speech_recognizer.recognize(audio_data=audioDataString, profile='NEAR_FIELD')

    #         time.sleep(5)
    #         print('Disconnecting from AVS')
    #         avs.disconnect()
    #         break

    # avs.disconnect()

if __name__ == '__main__':
    main()
