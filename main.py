import pygame
import random
import sys
from pathlib import Path
from pygame.constants import *
from pygame import Color, Vector2
from types import SimpleNamespace

def resource(path: str):
    base_path = Path(getattr(sys, '_MEIPASS', '.'))
    return base_path / path

FPS = 60
TITLE = "Lucioles"
WIDTH, HEIGHT = 800, 600
BACKGROUND_COLOR = Color('black')
NB_FIREFLY = 100 # how many fireflies (20k => 30fps, 10k => 60fps)

pygame.init()
screen = pygame.display.set_mode((WIDTH, HEIGHT))
pygame.display.set_caption(TITLE)
clock = pygame.time.Clock()

# fonts
sysfont = pygame.font.SysFont('Arial', 20)
fading_font = pygame.font.Font(resource('assets/segoesc.ttf'), 32)

# play music
pygame.mixer.music.load(resource('assets/music.ogg'))
pygame.mixer.music.play(-1)

events = []
def pick_event(eventtype):
    return next(iter([ ev for ev in events if ev.type == eventtype ]), NOEVENT)

def draw_fps(x: int, y: int):
    text_surface = sysfont.render(f"{clock.get_fps():.0f} FPS", True, pygame.Color(200, 200, 200))
    screen.blit(text_surface, (x, y))

class Timer:
    def __init__(self, duration = 1.0, loop = True):
        self.time = 0
        self.duration = duration
        self.loop = loop
    
    def step(self, delta: float):
        " if loop return 0 <= x >= 1 else block at 1"
        self.time += delta
        if self.loop:
            return self.time / self.duration % 1
        else:
            return 1 if self.time / self.duration > 1 else self.time / self.duration
    
    def reset(self, elapsed_time = 0.0):
        self.time = elapsed_time
    
    def is_running(self):
        return self.time > 0 and self.time < self.duration

class Firefly:
    BRIGHT = Color(173, 255, 0)
    DARKER = Color(26, 36, 7)
    JITTERY_SPEED = 100

    def __init__(self):
        self.position = Vector2(random.uniform(0, WIDTH), random.uniform(0, HEIGHT))
        self.radius = random.uniform(4, 7)
        self.color = Firefly.BRIGHT
        self.speed = random.uniform(10, 50)
        self.find_target()
        self.jittery = False

        # animation specific
        countdown = random.uniform(1, 5)
        self.fade_color = Timer(countdown)
        self.fade_color.reset(random.uniform(0, countdown))
    
    def find_target(self):
        self.target = SimpleNamespace(position=Vector2(random.uniform(0, WIDTH), random.uniform(0, HEIGHT)), radius=16)
    
    def update(self, delta: float):
        if self.jittery:
            self.color = Firefly.BRIGHT
        else:
            # fade color
            step = self.fade_color.step(delta)
            self.color = Color.lerp(Firefly.BRIGHT, Firefly.DARKER, step)

        # move to target position
        movement = Vector2(
            self.target.position.x - self.position.x,
            self.target.position.y - self.position.y
        ).normalize()
        velocity = movement * self.speed * delta
        if self.jittery:
            velocity = movement * Firefly.JITTERY_SPEED * delta
        self.position += velocity

        # check if target reached
        if self.target.position.distance_to(self.position) <= self.target.radius:
            self.find_target()

    def draw(self):
        pygame.draw.circle(screen, self.color, self.position, self.radius)

class Lantern:
    MIN_RADIUS = 20
    MAX_RADIUS = 150
    SOUND = pygame.mixer.Sound(resource('assets/firefly.ogg'))

    def __init__(self):
        self.visible = False
        self.position = Vector2()
        self._radius = 50
        self.color = Color(236, 100, 75)
        self.timer = Timer(0.5)
    
    @property
    def radius(self):
        return self._radius
    
    @radius.setter
    def radius(self, value):
        self._radius = max(Lantern.MIN_RADIUS, min(value, Lantern.MAX_RADIUS))

    def update(self, delta: float, fireflies: list[Firefly]):
        # position and visibility
        is_left_click = pygame.mouse.get_pressed()[0]
        self.position = Vector2(*pygame.mouse.get_pos())
        self.visible = is_left_click or self.timer.is_running()

        if self.timer.is_running():
            self.timer.step(delta)
        else:
            self.timer.reset()

        # increase/decrease radius
        if event := pick_event(MOUSEWHEEL):
            self.timer.reset()
            self.timer.step(delta)
            self.radius += 5 * event.y
        
        # make fireflies follow the lantern
        was_jittery_fireflies = False
        for firefly in fireflies:
            firefly.jittery = is_left_click and \
                self.position.distance_to(firefly.position) <= self.radius
            
            if firefly.jittery:
                position = Vector2(
                    random.uniform(self.position.x - self.radius, self.position.x + self.radius),
                    random.uniform(self.position.y - self.radius, self.position.y + self.radius)
                )
                radius = random.uniform(Lantern.MIN_RADIUS, Lantern.MAX_RADIUS)
                firefly.target = SimpleNamespace(position=position, radius=radius)

                was_jittery_fireflies = True

        # play sound
        if was_jittery_fireflies:
            Lantern.SOUND.play()
        else:
            Lantern.SOUND.stop()

    def draw(self):
        if self.visible:
            pygame.draw.circle(screen, self.color, self.position, self.radius)

class FadingMessage:
    def __init__(self, message: str, **kwargs):
        self.message = message
        self.font = kwargs.get('font', sysfont)
        self.state = 'fade in'

        self.countdown = Timer(kwargs.get('countdown', 3))
        self.fade_in = Timer(kwargs.get('fade_in', 2), False)
        self.fade_out = Timer(kwargs.get('fade_out', 2), False)

        # fading animation
        self.start_position = kwargs.get('start_position', Vector2(WIDTH / 2, -50))
        self.end_position = kwargs.get('end_position', Vector2(WIDTH / 2, 50))
        self.position = Vector2(self.start_position)

        self.start_color = kwargs.get('start_color', BACKGROUND_COLOR)
        self.end_color = kwargs.get('end_color', Color(255, 182, 193))
        self.color = Color(self.start_color)

    def update(self, delta: float):
        # change state
        if pick_event(MOUSEBUTTONDOWN):
            self.state = 'fade out'

        # wait when the countdown was over
        self.countdown.step(delta)
        if self.countdown.is_running():
            return
        
        # fade in/out message
        if self.state == 'fade in':
            step = self.fade_in.step(delta)
            self.position = Vector2.lerp(self.start_position, self.end_position, step)
            self.color = Color.lerp(self.start_color, self.end_color, step)
        elif self.state == 'fade out':
            step = self.fade_out.step(delta)
            self.position = Vector2.lerp(self.position, self.start_position, step)
            self.color = Color.lerp(self.color, self.start_color, step)

    def draw(self):
        text_surface = self.font.render(self.message, True, self.color)
        position = text_surface.get_rect(center=(self.position.x, self.position.y))
        screen.blit(text_surface, position)

################################################################################

# init
running = True
show_fps = False
lantern = Lantern()
fireflies = [ Firefly() for _ in range(NB_FIREFLY) ]
message = FadingMessage("click with your mouse", font=fading_font)

while running:
    # input
    events = pygame.event.get()
    if pick_event(QUIT) or (event := pick_event(KEYDOWN)) and event.key == K_ESCAPE:
        running = False
    if event := pick_event(KEYDOWN) and event.key == K_r:
        show_fps = not show_fps
    
    # update
    delta = clock.tick(FPS) / 1000
    message.update(delta)
    lantern.update(delta, fireflies)
    [ f.update(delta) for f in fireflies ]

    # render
    screen.fill(BACKGROUND_COLOR)
    message.draw()
    lantern.draw()
    [ f.draw() for f in fireflies ]
    if show_fps: draw_fps(10, 5)
    pygame.display.update()
