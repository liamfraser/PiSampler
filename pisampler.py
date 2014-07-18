#!/usr/bin/env python

import RPi.GPIO as GPIO
import time
import pygame
import os

beat_pins = [2, 3, 4, 17]
drum_pins = [27]

class PiSampler:
    def __init__(self):
        pygame.mixer.pre_init(44100, -16, 1, 1024)
        pygame.init()

        GPIO.setmode(GPIO.BCM)
        for pin in beat_pins:
            GPIO.setup(pin, GPIO.OUT)

        for pin in drum_pins:
            GPIO.setup(pin, GPIO.IN)

        self.sound = pygame.mixer.Sound(os.path.join('sounds', 'kick01.wav')) 

if __name__ == "__main__":
    sampler = PiSampler()

    while True:
        GPIO.wait_for_edge(27, GPIO.RISING)
        sampler.sound.play()
        time.sleep(0.15) 
