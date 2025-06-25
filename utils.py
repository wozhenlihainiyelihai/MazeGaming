# 包含所有辅助工具，如SoundManager和图标生成函数。

import pygame
import numpy
from config import *

class SoundManager:
    """管理所有音效"""
    def __init__(self):
        pygame.mixer.init(frequency=22050, size=-16, channels=2, buffer=512)
        self.sounds = {
            'click': self._create_sound(440, 0.1),
            'coin': self._create_sound([880, 1046], 0.08),
            'potion': self._create_sound([523, 587, 659], 0.12),
            'trap': self._create_sound([220, 180], 0.2), # 【功能新增】陷阱音效
        }

    def _create_sound(self, freqs, duration):
        sample_rate = pygame.mixer.get_init()[0]
        max_amplitude = 2 ** (pygame.mixer.get_init()[1] // 2) - 1
        if isinstance(freqs, int): freqs = [freqs]
        total_samples = int(sample_rate * duration)
        samples_per_freq = total_samples // len(freqs)
        wave_mono = numpy.zeros(total_samples, dtype=numpy.int16)
        for i, freq in enumerate(freqs):
            start_sample = i * samples_per_freq
            end_sample = (i + 1) * samples_per_freq
            num_samples_in_segment = end_sample - start_sample
            x = numpy.linspace(0, duration / len(freqs), num_samples_in_segment, False)
            tone = numpy.sin(freq * x * 2 * numpy.pi)
            fade_out = numpy.linspace(1, 0, num_samples_in_segment)
            wave_mono[start_sample:end_sample] = (tone * fade_out * max_amplitude).astype(numpy.int16)
        return pygame.sndarray.make_sound(numpy.column_stack((wave_mono, wave_mono)))

    def play(self, name):
        if self.sounds.get(name):
            self.sounds[name].play()

def create_all_icons(icon_size):
    """静态方法，用于创建所有图标，以便多处复用"""
    tile_icons = {}
    if icon_size <= 0: return tile_icons
    
    icon_colors = {
        'BOSS': (139, 0, 0), 'GOLD': (255, 215, 0), 'HEALTH_POTION': (255, 105, 180),
        'TRAP': (70, 130, 180), 'SHOP': (34, 139, 34), 'LOCKER': (150, 75, 0)
    }
    font_color = (0,0,0)

    # Gold
    surf = pygame.Surface((icon_size, icon_size), pygame.SRCALPHA)
    pygame.draw.circle(surf, icon_colors['GOLD'], (icon_size // 2, icon_size // 2), icon_size // 2)
    font = pygame.font.SysFont('sans-serif', int(icon_size * 0.8), bold=True)
    text = font.render('$', True, font_color)
    rect = text.get_rect(center=(icon_size // 2, icon_size // 2))
    surf.blit(text, rect)
    tile_icons[GOLD] = surf
    
    # Health Potion
    surf = pygame.Surface((icon_size, icon_size), pygame.SRCALPHA)
    pygame.draw.rect(surf, icon_colors['HEALTH_POTION'], (icon_size // 4, 0, icon_size // 2, icon_size))
    pygame.draw.rect(surf, icon_colors['HEALTH_POTION'], (0, icon_size // 4, icon_size, icon_size // 2))
    tile_icons[HEALTH_POTION] = surf
    
    # Trap
    surf = pygame.Surface((icon_size, icon_size), pygame.SRCALPHA)
    pygame.draw.line(surf, icon_colors['TRAP'], (0, 0), (icon_size, icon_size), 3)
    pygame.draw.line(surf, icon_colors['TRAP'], (icon_size, 0), (0, icon_size), 3)
    tile_icons[TRAP] = surf
    
    # Locker
    surf = pygame.Surface((icon_size, icon_size), pygame.SRCALPHA)
    pygame.draw.circle(surf, icon_colors['LOCKER'], (icon_size // 2, icon_size // 3), icon_size // 4)
    pygame.draw.rect(surf, icon_colors['LOCKER'], (icon_size // 2 - 2, icon_size // 3, 4, icon_size // 2))
    tile_icons[LOCKER] = surf
    
    # Shop
    surf = pygame.Surface((icon_size, icon_size), pygame.SRCALPHA)
    pygame.draw.rect(surf, icon_colors['SHOP'], (0, 0, icon_size, icon_size // 4))
    pygame.draw.rect(surf, icon_colors['SHOP'], (icon_size // 8, icon_size // 4, icon_size * 6 // 8, icon_size * 3 // 4), 2)
    pygame.draw.circle(surf, icon_colors['SHOP'], (icon_size // 4, icon_size), 3)
    pygame.draw.circle(surf, icon_colors['SHOP'], (icon_size * 3 // 4, icon_size), 3)
    tile_icons[SHOP] = surf
    
    # Boss
    surf = pygame.Surface((icon_size, icon_size), pygame.SRCALPHA)
    points = [(0, icon_size // 3), (icon_size // 2, 0), (icon_size, icon_size // 3), (icon_size * 4 // 5, icon_size), (icon_size // 5, icon_size)]
    pygame.draw.polygon(surf, icon_colors['BOSS'], points)
    tile_icons[BOSS] = surf
    
    return tile_icons
