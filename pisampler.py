#!/usr/bin/env python

import RPi.GPIO as GPIO
import time
import pygame
import os
from threading import Thread

beat_pins = [2, 3, 4, 17]

class Drum():
    def __init__(self, pin, sound):
        self.sound = pygame.mixer.Sound(os.path.join('sounds', sound))
        self.pin = pin
        GPIO.setup(pin, GPIO.IN)

    def play(self, channel):
        self.sound.play()

class PiSampler:
    def __init__(self):
        pygame.mixer.pre_init(44100, -16, 1, 1024)
        pygame.init()

        self.drums = []

        GPIO.setmode(GPIO.BCM)
        for pin in beat_pins:
            GPIO.setup(pin, GPIO.OUT)

    def add(self, drum):
        self.drums.append(drum)

    def run(self):
        for drum in self.drums:
            GPIO.add_event_detect(drum.pin, GPIO.RISING,
                                  callback=drum.play, bouncetime=200)

        while True:
            time.sleep(1)

if __name__ == "__main__":
    sampler = PiSampler()
    sampler.add(Drum(27, 'kick01.wav'))
    sampler.add(Drum(22, 'snare01.wav'))
    sampler.run()
