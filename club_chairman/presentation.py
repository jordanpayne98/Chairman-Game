"""Original procedural artwork and decorative animation; never simulates football."""
import hashlib
import math
import random
from array import array
import pygame

PALETTES=[((52,133,104),(236,222,181)),((55,94,143),(220,232,241)),((163,68,60),(245,223,182)),
          ((121,82,155),(226,216,241)),((51,128,137),(215,235,225)),((168,139,60),(39,48,57)),
          ((148,55,76),(239,231,222)),((60,104,161),(230,220,171))]


def palette(key):
    try:return PALETTES[int(key[1:])%len(PALETTES)]
    except (ValueError,TypeError):return PALETTES[0]


def crest(surface,key,rect):
    r=pygame.Rect(rect);primary,trim=palette(key)
    points=[(r.x+r.w*.1,r.y+r.h*.1),(r.centerx,r.y),(r.right-r.w*.1,r.y+r.h*.1),
            (r.right-r.w*.14,r.y+r.h*.65),(r.centerx,r.bottom),(r.x+r.w*.14,r.y+r.h*.65)]
    pygame.draw.polygon(surface,trim,points)
    inner=[(r.centerx+(x-r.centerx)*.85,r.centery+(y-r.centery)*.85) for x,y in points]
    pygame.draw.polygon(surface,primary,inner)
    pygame.draw.line(surface,trim,(r.x+r.w*.2,r.y+r.h*.35),(r.right-r.w*.2,r.y+r.h*.35),max(2,r.w//18))
    n=int(key[1:]) if key[1:].isdigit() else 0
    for i in range(1+n%3):
        x=r.centerx+(i-(n%3)/2)*r.w*.2
        pygame.draw.circle(surface,trim,(round(x),round(r.y+r.h*.6)),max(3,r.w//13),max(1,r.w//35))
    pygame.draw.line(surface,trim,(r.centerx,r.y+r.h*.75),(r.centerx,r.y+r.h*.85),max(2,r.w//18))


def portrait(surface,identity,age,rect,club='c0'):
    """Stable modular illustration; private attributes never influence appearance."""
    r=pygame.Rect(rect);previous_clip=surface.get_clip();surface.set_clip(r.clip(previous_clip))
    rng=random.Random(int(hashlib.sha256(identity.encode()).hexdigest()[:16],16))
    skin=rng.choice([(207,156,122),(170,117,85),(118,78,56),(228,184,150),(85,57,46)])
    hair=rng.choice([(39,30,26),(73,48,32),(139,103,65),(24,24,27)])
    primary,trim=palette(club or 'c0')
    pygame.draw.rect(surface,(31,46,51),r,border_radius=9)
    pygame.draw.ellipse(surface,primary,(r.x+r.w*.05,r.y+r.h*.60,r.w*.90,r.h*.65))
    pygame.draw.rect(surface,skin,(r.x+r.w*.40,r.y+r.h*.56,r.w*.20,r.h*.21),border_radius=3)
    head=pygame.Rect(r.x+r.w*.25,r.y+r.h*.16,r.w*.5,r.h*.48)
    pygame.draw.ellipse(surface,skin,head)
    pygame.draw.ellipse(surface,hair,(head.x,head.y-3,head.w,head.h*.40))
    if rng.random()<.4:pygame.draw.rect(surface,hair,(head.x,head.y+head.h*.15,head.w*.12,head.h*.44),border_radius=2)
    for dx in (.4,.6):
        pygame.draw.circle(surface,(27,31,33),(round(r.x+r.w*dx),round(r.y+r.h*.38)),max(1,r.w//45))
    pygame.draw.line(surface,(112,66,58),(r.x+r.w*.43,r.y+r.h*.54),(r.x+r.w*.57,r.y+r.h*.54),max(1,r.w//60))
    pygame.draw.line(surface,trim,(r.x+r.w*.3,r.y+r.h*.79),(r.x+r.w*.70,r.y+r.h*.79),max(2,r.w//16))
    surface.set_clip(previous_clip)


def pitch(surface,rect,closed=False,tick=0,reduced=False):
    r=pygame.Rect(rect);pygame.draw.rect(surface,(24,52,44),r,border_radius=12)
    field=r.inflate(-82,-65)
    for i in range(10):
        stripe=pygame.Rect(field.x+i*field.w/10,field.y,field.w/10+1,field.h)
        pygame.draw.rect(surface,(35,88+(i%2)*7,67),stripe)
    ink=(147,191,157);pygame.draw.rect(surface,ink,field,2)
    pygame.draw.line(surface,ink,(field.centerx,field.top),(field.centerx,field.bottom),2)
    pygame.draw.circle(surface,ink,field.center,round(field.h*.22),2)
    for left in (field.left,field.right-field.w*.16):pygame.draw.rect(surface,ink,(left,field.y+field.h*.24,field.w*.16,field.h*.52),2)
    for top in (r.y+10,r.bottom-24):
        for i in range(18):pygame.draw.rect(surface,(95,121,124),(r.x+42+i*(r.w-84)/18,top,(r.w-96)/18,9),border_radius=2)
    for side in (r.x+12,r.right-25):
        for i in range(8):pygame.draw.rect(surface,(75,103,111),(side,r.y+37+i*(r.h-74)/8,12,(r.h-88)/8),border_radius=2)
    if closed:
        pygame.draw.rect(surface,(179,139,69),(r.right-27,r.y+27,16,r.h-54),border_radius=4)
        if not reduced:
            beam=round(r.y+35+(math.sin(tick/850)+1)/2*(r.h-86))
            pygame.draw.rect(surface,(244,216,141),(r.right-29,beam,20,14),border_radius=2)


class Soundscape:
    """Short original synthesised cues; no third-party sound assets or queues."""
    def __init__(self):
        self.enabled=False;self.volume=.22;self.sounds={}
        try:
            pygame.mixer.init(frequency=22050,size=-16,channels=1,buffer=512)
            rate,_,channels=pygame.mixer.get_init()
            for name,freq,length in [('click',510,.045),('goal',760,.23),('notice',640,.10)]:
                samples=array('h')
                for i in range(int(rate*length)):
                    envelope=math.sin(math.pi*i/(rate*length))**2
                    sample=int(5000*envelope*math.sin(2*math.pi*freq*i/rate))
                    samples.extend([sample]*channels)
                self.sounds[name]=pygame.mixer.Sound(buffer=samples)
            self.enabled=True
        except pygame.error:pass

    def play(self,name):
        if self.enabled and self.volume>0:
            sound=self.sounds[name];sound.set_volume(self.volume);sound.play()
