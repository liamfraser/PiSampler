#!/usr/bin/env python

import RPi.GPIO as GPIO
import time
import pygame
import os

beat_leds = [2, 3, 4, 17]
bar_leds = [27, 22, 10, 9]
debounce = 200 # ms

class Drum(object):
    def __init__(self, pin, sound):
        self.name = sound
        self.sound = pygame.mixer.Sound(os.path.join('sounds', sound))
        self.pin = pin
        GPIO.setup(pin, GPIO.IN)
        GPIO.add_event_detect(self.pin, GPIO.RISING, callback=self.play,
                              bouncetime=debounce)

    def play(self, channel):
        print self.name
        self.sound.play()

class PiSampler(object):
    def __init__(self, tempo=80, quantize=1.0/16.0):
        pygame.mixer.pre_init(44100, -16, 1, 512)
        pygame.init()

        self.metronome = False
        self.met_low = pygame.mixer.Sound(os.path.join('sounds', 'met_low.wav'))
        self.met_high = pygame.mixer.Sound(os.path.join('sounds', 'met_high.wav'))
        self.met_low.set_volume(0.4)
        self.met_high.set_volume(0.4)

        self.drums = []

        GPIO.setmode(GPIO.BCM)
        for pin in beat_leds + bar_leds:
            GPIO.setup(pin, GPIO.OUT)

        self.quantize = quantize
        self.tempo = tempo

    def add(self, drum):
        self.drums.append(drum)

    @property
    def tempo(self):
        return self._tempo
    
    @tempo.setter
    def tempo(self, tempo):
        self._tempo = tempo
        # Tempo is in beats per minute. There are 60 seconds in a minute.
        self.beat_n_seconds = 60.0 / tempo

        # Time signature is assumed to be 4/4 (4 beats per bar) for simplicity.
        # Quantize is in the form 1/quantize. So 1/4 means that you can have 4
        # hits per bar.
        self.quantize_per_beat = 1 / (self.quantize * 4)
        self.quantize_seconds = self.quantize * 4 * self.beat_n_seconds

    def do_leds(self, leds, n):
        count = 0
        for led in leds:
            if count == n:
                GPIO.output(led, True) 
            else:
                GPIO.output(led, False)

            count += 1

    def do_metronome(self):
        if not self.metronome:
            return

        if self.beat_n == 0:
            self.met_high.play()
        else:
            self.met_low.play()

    def run(self):
        self.bar_n = 0
        self.beat_n = 0
        self.quantize_n = 0

        while True:
            if self.quantize_n == 0:
                self.do_leds(beat_leds, self.beat_n)
                self.do_leds(bar_leds, self.bar_n)
                self.do_metronome()

            # Wait for the next quantize and then do beat / bar / quantize math
            time.sleep(self.quantize_seconds)

            if self.quantize_n == (self.quantize_per_beat - 1):
                self.quantize_n = 0
                self.beat_n += 1
            else:
                self.quantize_n += 1

            # If we are at the end of a bar then
            if self.beat_n == 4:
                self.beat_n = 0
                self.bar_n += 1
                if self.bar_n == 4:
                    self.bar_n = 0

if __name__ == "__main__":
    sampler = PiSampler(tempo=140)
    sampler.add(Drum(05, 'kick01.wav'))
    sampler.add(Drum(06, 'snare01.wav'))
    sampler.add(Drum(13, 'clhat01.wav'))
    sampler.metronome = True
    sampler.run()
