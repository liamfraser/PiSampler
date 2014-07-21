#!/usr/bin/env python
#
#  pisampler.py
#  
#  Copyright 2014 Imagine Publishing Ltd.
#  
#  This program is free software; you can redistribute it and/or modify
#  it under the terms of the GNU General Public License as published by
#  the Free Software Foundation; either version 2 of the License, or
#  (at your option) any later version.
#  
#  This program is distributed in the hope that it will be useful,
#  but WITHOUT ANY WARRANTY; without even the implied warranty of
#  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#  GNU General Public License for more details.
#  
#  You should have received a copy of the GNU General Public License
#  along with this program; if not, write to the Free Software
#  Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston,
#  MA 02110-1301, USA.

import RPi.GPIO as GPIO
import time
import pygame
import os

beat_leds = [2, 3, 4, 17]
bar_leds = [27, 22, 10, 9]
record_led = 11
record = 19
undo = 26
debounce = 200 # ms

class Sample(object):
    def __init__(self, pin, sound, sampler):
        self.sampler = sampler
        self.name = sound
        self.sound = pygame.mixer.Sound(os.path.join('sounds', sound))
        self.pin = pin
        GPIO.setup(pin, GPIO.IN)
        GPIO.add_event_detect(self.pin, GPIO.RISING, callback=self.play_btn,
                              bouncetime=debounce)

    def play_btn(self, channel):
        self.sound.play()
        s = self.sampler
        if s.recording:
            s.recording_data[s.bar_n][s.quantize_n].append({'loop' : s.loop_count,
                                                            'sample' : self})

class PiSampler(object):
    def __init__(self, tempo=80, quantize=64):
        pygame.mixer.pre_init(44100, -16, 1, 512)
        pygame.init()

        self.quantize = quantize
        self.tempo = tempo
        self.recording = False
        self.record_next = False

        self.metronome = False
        self.met_low = pygame.mixer.Sound(os.path.join('sounds', 'met_low.wav'))
        self.met_high = pygame.mixer.Sound(os.path.join('sounds', 'met_high.wav'))
        self.met_low.set_volume(0.4)
        self.met_high.set_volume(0.4)

        self.samples = []

        # Array of arrays for each bar, with another array for quantize
        self.recording_data = []
        for i in range(0, 4):
            bar_arr = []
            for i in range(0, quantize):
                bar_arr.append([])

            self.recording_data.append(bar_arr)

        GPIO.setmode(GPIO.BCM)
        for pin in beat_leds + bar_leds + [record_led]:
            GPIO.setup(pin, GPIO.OUT)

        GPIO.setup(record, GPIO.IN)
        GPIO.add_event_detect(record, GPIO.RISING,
                              callback=self.record_next_loop,
                              bouncetime=debounce)
        GPIO.setup(undo, GPIO.IN)
        GPIO.add_event_detect(undo, GPIO.RISING,
                              callback=self.undo_previous_loop,
                              bouncetime=debounce)

    @property
    def tempo(self):
        return self._tempo
    
    @tempo.setter
    def tempo(self, tempo):
        self._tempo = tempo
        # Tempo is in beats per minute. There are 60 seconds in a minute.
        self.seconds_per_beat = 60.0 / tempo

        # Time signature is assumed to be 4/4 (4 beats per bar) for simplicity.
        # Quantize is how accurately we are sampling for button presses
        self.quantize_per_beat = self.quantize / 4
        self.quantize_seconds = self.seconds_per_beat / self.quantize_per_beat

    def add(self, sample):
        self.samples.append(sample)

    @property
    def recording(self):
        return self._recording

    @recording.setter
    def recording(self, value):
        self._recording = value
        GPIO.output(record_led, value)

    def record_next_loop(self, channel):
        self.record_next = True

    def undo_previous_loop(self, channel):
        if len(self.last_recorded_loop) == 0:
            print "No previous loop to undo"
            return

        print "Undoing previous loop"

        loop = self.last_recorded_loop.pop()

        for bar in self.recording_data:
            for quantize in bar:
                removes = []
                for sample in quantize:
                    if sample['loop'] == loop:
                        removes.append(sample)

                for sample in removes:
                    quantize.remove(sample)

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

    def play_recording(self):
        for sample_dict in self.recording_data[self.bar_n][self.quantize_n]:
            # Only play if it hasn't just been added
            if sample_dict['loop'] != self.loop_count:
                sample_dict['sample'].sound.play()

    def run(self):
        self.loop_count = 0
        self.last_recorded_loop = []
        self.bar_n = 0
        self.beat_n = 0
        self.quantize_beat_n = 0
        self.quantize_n = 0

        while True:
            if self.quantize_beat_n == 0:
                # We're at the start of a new beat
                self.do_leds(beat_leds, self.beat_n)
                self.do_leds(bar_leds, self.bar_n)
                self.do_metronome()
                
                # If we're at the start of a new loop
                if self.quantize_n == 0 and self.bar_n == 0:
                    if self.record_next:
                        self.recording = True
                        self.record_next = False
                    elif self.recording:
                        self.recording = False
                        self.last_recorded_loop.append(self.loop_count)

                    self.loop_count += 1

            # Play any recorded hits
            self.play_recording()

            # Wait for the next quantize and then calculate new
            # beat/bar/quantize values
            time.sleep(self.quantize_seconds)

            # If we are at a new beat, then increment beat counter
            if self.quantize_beat_n == self.quantize_per_beat - 1:
                self.quantize_beat_n = 0
                self.beat_n += 1
            else:
                self.quantize_beat_n += 1

            # If we are at the end of the quantize per bar
            if self.quantize_n == self.quantize - 1:
                self.quantize_n = 0
            else:
                self.quantize_n += 1

            # If we are at the end of a bar then reset the beat counter and
            # increment the bar counter
            if self.beat_n == 4:
                self.beat_n = 0
                self.bar_n += 1
                if self.bar_n == 4:
                    self.bar_n = 0

if __name__ == "__main__":
    sampler = PiSampler(tempo=140)
    sampler.add(Sample(05, 'kick01.wav', sampler))
    sampler.add(Sample(06, 'snare01.wav', sampler))
    sampler.add(Sample(13, 'clhat01.wav', sampler))
    sampler.metronome = True
    sampler.run()
