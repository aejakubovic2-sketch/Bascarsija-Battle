# -*- coding: utf-8 -*-
import asyncio
import pygame
import random

# ─────────────────────────────────────────────────────────────────────────────
#  PYGBAG NOTE:
#  All file paths must be relative (same folder as game.py).
#  The game loop must live inside `async def main()` and call
#  `await asyncio.sleep(0)` once per frame so the browser can breathe.
# ─────────────────────────────────────────────────────────────────────────────

async def main():

    pygame.init()
    pygame.mixer.init()

    # --- Screen ---
    screen = pygame.display.set_mode((1080, 720))
    pygame.display.set_caption("Bascarsija Battle")
    clock = pygame.time.Clock()

    # --- Music (path must be relative for web build) ---
    try:
        pygame.mixer.music.load("music.ogg")
        pygame.mixer.music.set_volume(0.5)
        pygame.mixer.music.play(-1)
    except Exception:
        pass  # browser may block audio until first user interaction — that's fine

    # --- Assets ---
    background   = pygame.image.load("bascarsija_bg.png").convert()
    enemy_image  = pygame.image.load("enemy_coffee.png").convert_alpha()
    enemy_image  = pygame.transform.scale(enemy_image, (64, 64))
    sprite_image = pygame.image.load("player_ottoman.png").convert_alpha()
    sprite_image = pygame.transform.scale(sprite_image, (64, 64))

    # --- Fonts ---
    font_big   = pygame.font.SysFont(None, 90)
    font_med   = pygame.font.SysFont(None, 40)
    font_small = pygame.font.SysFont(None, 32)
    font_tiny  = pygame.font.SysFont(None, 22)

    # ── Constants ────────────────────────────────────────────────────────────
    SW, SH               = screen.get_width(), screen.get_height()
    INVINCIBLE_DURATION  = 1.0
    SHIELD_DURATION      = 5.0
    SPREAD_DURATION      = 8.0
    COMBO_TIMEOUT        = 1.5
    PLAYER_SHOOT_INTERVAL = 0.25
    SHOOT_INTERVAL       = 0.25

    # ── Game-state variables ──────────────────────────────────────────────────
    def make_state():
        return dict(
            # player
            player_rect      = sprite_image.get_rect(center=(SW // 2, SH // 2)),
            speed            = 400,
            player_hp        = 3,
            max_hp           = 3,
            invincible       = False,
            invincible_timer = 0.0,

            # enemy
            enemy_rect      = pygame.Rect(0, 40, 64, 64),
            enemy_speed     = 180,
            enemy_direction = 1,
            enemy_hp        = 20,
            enemy_max_hp    = 20,

            # enemy bullets
            bullets      = [],
            shoot_timer  = 0.0,
            bullet_speed = 400,

            # player bullets
            player_bullets     = [],
            player_shoot_timer = 0.0,
            player_bullet_speed = 600,

            # score / combo
            score      = 0,
            combo      = 0,
            combo_timer = 0.0,
            combo_bonus_text = [],   # [x, y, lifetime, text]

            # shield pickup
            shield_active     = False,
            shield_timer      = 0.0,
            show_shield       = True,
            shield_rect       = pygame.Rect(
                random.randint(50, 1000), random.randint(200, 620), 36, 36),

            # spread pickup
            spread_active    = False,
            spread_timer     = 0.0,
            show_spread      = False,
            next_spread_score = 50,
            spread_rect      = pygame.Rect(-100, -100, 36, 36),

            # game flow
            game_over = False,
            victory   = False,
        )

    S = make_state()   # S holds all mutable state

    # ── Helpers ───────────────────────────────────────────────────────────────

    def draw_health_bar(hp, max_hp):
        bw, bh = 200, 24
        x, y   = 20, 20
        sw_    = bw // max_hp
        gap    = 4
        pygame.draw.rect(screen, (60,60,60), (x,y,bw,bh), border_radius=6)
        for i in range(hp):
            sx = x + i*sw_ + (gap if i>0 else 0)
            pygame.draw.rect(screen, (220,50,50), (sx,y+3,sw_-gap,bh-6), border_radius=4)
        pygame.draw.rect(screen, (255,255,255), (x,y,bw,bh), 2, border_radius=6)
        lbl = font_tiny.render(f"HP: {hp} / {max_hp}", True, (255,255,255))
        screen.blit(lbl, (x+bw+10, y+2))

    def draw_enemy_health_bar(hp, max_hp):
        bw, bh = 200, 16
        x = SW//2 - bw//2
        y = 16
        fw    = int((hp/max_hp)*bw)
        ratio = hp/max_hp
        col   = (50,200,50) if ratio>0.6 else ((220,180,0) if ratio>0.3 else (220,50,50))
        pygame.draw.rect(screen, (60,60,60), (x,y,bw,bh), border_radius=6)
        pygame.draw.rect(screen, col,        (x,y,fw,bh),  border_radius=6)
        pygame.draw.rect(screen, (255,255,255),(x,y,bw,bh), 2, border_radius=6)
        lbl = font_tiny.render(f"ENEMY  {hp} / {max_hp}", True, (255,255,255))
        screen.blit(lbl, (x+bw+8, y))

    def shoot_bullet():
        rx = random.randint(0, SW-8)
        S["bullets"].append(pygame.Rect(rx, S["enemy_rect"].bottom, 8, 20))

    def shoot_player_bullet():
        pr = S["player_rect"]
        if S["spread_active"]:
            for offset in (-20, 0, 20):
                S["player_bullets"].append(
                    pygame.Rect(pr.centerx-4+offset, pr.top-20, 8, 20))
        else:
            S["player_bullets"].append(
                pygame.Rect(pr.centerx-4, pr.top-20, 8, 20))

    def draw_victory():
        ov = pygame.Surface((SW, SH), pygame.SRCALPHA)
        ov.fill((0,0,0,160))
        screen.blit(ov, (0,0))
        t  = font_big.render("YOU WIN!", True, (50,220,50))
        sc = font_med.render(f"Score: {S['score']}", True, (255,220,50))
        sb = font_med.render("Press R to restart", True, (255,255,255))
        screen.blit(t,  t.get_rect(center=(SW//2, 280)))
        screen.blit(sc, sc.get_rect(center=(SW//2, 370)))
        screen.blit(sb, sb.get_rect(center=(SW//2, 430)))

    def draw_game_over():
        ov = pygame.Surface((SW, SH), pygame.SRCALPHA)
        ov.fill((0,0,0,160))
        screen.blit(ov, (0,0))
        t  = font_big.render("GAME OVER", True, (220,50,50))
        sb = font_med.render("Press R to restart", True, (255,255,255))
        sc = font_med.render(f"Score: {S['score']}", True, (255,220,50))
        screen.blit(t,  t.get_rect(center=(SW//2, 260)))
        screen.blit(sc, sc.get_rect(center=(SW//2, 360)))
        screen.blit(sb, sb.get_rect(center=(SW//2, 430)))

    def reset():
        nonlocal S
        S = make_state()
        try:
            pygame.mixer.music.play(-1)
        except Exception:
            pass

    # ── Main loop ─────────────────────────────────────────────────────────────
    running = True
    dt      = 0.0

    while running:

        # ── Events ───────────────────────────────────────────────────────────
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False

            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_r and (S["game_over"] or S["victory"]):
                    reset()

                if event.key == pygame.K_m:
                    if pygame.mixer.music.get_busy():
                        pygame.mixer.music.pause()
                    else:
                        pygame.mixer.music.unpause()

        # ── Background ───────────────────────────────────────────────────────
        screen.fill((0, 0, 0))
        screen.blit(background, (0, 0))

        # ── Active gameplay ───────────────────────────────────────────────────
        if not S["game_over"] and not S["victory"]:

            er  = S["enemy_rect"]
            pr  = S["player_rect"]

            # Enemy movement
            er.x += S["enemy_speed"] * S["enemy_direction"] * dt
            if er.right >= SW: er.right = SW; S["enemy_direction"] = -1
            if er.left  <= 0:  er.left  = 0;  S["enemy_direction"] =  1

            # Enemy shooting
            S["shoot_timer"] += dt
            if S["shoot_timer"] >= SHOOT_INTERVAL:
                shoot_bullet()
                S["shoot_timer"] = 0

            # Player movement
            keys = pygame.key.get_pressed()
            if keys[pygame.K_w]: pr.y -= S["speed"] * dt
            if keys[pygame.K_s]: pr.y += S["speed"] * dt
            if keys[pygame.K_a]: pr.x -= S["speed"] * dt
            if keys[pygame.K_d]: pr.x += S["speed"] * dt
            pr.clamp_ip(screen.get_rect())

            # Player shooting
            S["player_shoot_timer"] += dt
            if keys[pygame.K_SPACE] and S["player_shoot_timer"] >= PLAYER_SHOOT_INTERVAL:
                shoot_player_bullet()
                S["player_shoot_timer"] = 0

            # Invincibility
            if S["invincible"]:
                S["invincible_timer"] -= dt
                if S["invincible_timer"] <= 0:
                    S["invincible"] = False

            # Shield timer
            if S["shield_active"]:
                S["shield_timer"] -= dt
                if S["shield_timer"] <= 0:
                    S["shield_active"] = False
                    S["show_shield"]   = True
                    S["shield_rect"].topleft = (
                        random.randint(50,1000), random.randint(200,620))

            # Spread timer
            if S["spread_active"]:
                S["spread_timer"] -= dt
                if S["spread_timer"] <= 0:
                    S["spread_active"] = False

            # Combo timeout
            if S["combo"] > 0:
                S["combo_timer"] += dt
                if S["combo_timer"] >= COMBO_TIMEOUT:
                    S["combo"]       = 0
                    S["combo_timer"] = 0

            # Floating texts
            for ft in S["combo_bonus_text"][:]:
                ft[1] -= 40 * dt
                ft[2] -= dt
                if ft[2] <= 0:
                    S["combo_bonus_text"].remove(ft)

            # Spread pickup spawn
            if (S["score"] >= S["next_spread_score"]
                    and not S["show_spread"] and not S["spread_active"]):
                S["show_spread"]       = True
                S["next_spread_score"] += 50
                S["spread_rect"].topleft = (
                    random.randint(50,1000), random.randint(200,620))

            # ── Enemy bullets ─────────────────────────────────────────────────
            for b in S["bullets"][:]:
                b.y += S["bullet_speed"] * dt
                if b.top > SH:
                    S["bullets"].remove(b)
                    continue
                if (b.colliderect(pr)
                        and not S["invincible"] and not S["shield_active"]):
                    S["bullets"].remove(b)
                    S["player_hp"]       -= 1
                    S["invincible"]       = True
                    S["invincible_timer"] = INVINCIBLE_DURATION
                    if S["player_hp"] <= 0:
                        S["game_over"] = True
                        try: pygame.mixer.music.stop()
                        except Exception: pass
                    continue

            # ── Player bullets ────────────────────────────────────────────────
            for pb in S["player_bullets"][:]:
                pb.y -= S["player_bullet_speed"] * dt
                if pb.bottom < 0:
                    S["player_bullets"].remove(pb)
                    continue
                if pb.colliderect(er):
                    S["player_bullets"].remove(pb)
                    S["enemy_hp"] -= 1
                    S["combo"]    += 1
                    S["combo_timer"] = 0

                    # Score calc
                    sa = S["spread_active"]
                    sh = S["shield_active"]
                    if sa and sh: pts, tag = 50, "JACKPOT!"
                    elif sa:      pts, tag = 30, "SPREAD x3!"
                    elif sh:      pts, tag = 20, "SHIELD x2!"
                    else:         pts, tag = 10, "HIT"

                    c = S["combo"]
                    if c >= 10: pts *= 3; tag = f"x3 COMBO!! +{pts}"
                    elif c >= 5: pts *= 2; tag = f"x2 COMBO! +{pts}"
                    else: tag = f"{tag} +{pts}"

                    S["score"] += pts
                    S["combo_bonus_text"].append(
                        [er.centerx, er.bottom+10, 1.0, tag])

                    if S["enemy_hp"] <= 0:
                        S["victory"] = True
                        try: pygame.mixer.music.stop()
                        except Exception: pass
                    continue

            # ── Pickup collisions ─────────────────────────────────────────────
            if S["show_shield"] and pr.colliderect(S["shield_rect"]):
                S["show_shield"]   = False
                S["shield_active"] = True
                S["shield_timer"]  = SHIELD_DURATION

            if S["show_spread"] and pr.colliderect(S["spread_rect"]):
                S["show_spread"]      = False
                S["spread_active"]    = True
                S["spread_timer"]     = SPREAD_DURATION
                S["spread_rect"].topleft = (-100, -100)

            # ── Draw enemy ────────────────────────────────────────────────────
            screen.blit(enemy_image, er)

            # Draw player bullets (yellow)
            for pb in S["player_bullets"]:
                pygame.draw.rect(screen, (255,220,50), pb, border_radius=3)

            # Draw enemy bullets (brown)
            for b in S["bullets"]:
                pygame.draw.rect(screen, (139,90,43), b, border_radius=3)

            # ── Shield pickup ─────────────────────────────────────────────────
            if S["show_shield"]:
                sr = S["shield_rect"]
                pygame.draw.circle(screen, (30,30,200),    sr.center, 18)
                pygame.draw.circle(screen, (100,180,255),  sr.center, 12)
                pygame.draw.circle(screen, (255,255,255),  sr.center,  6)
                lbl = font_tiny.render("SHIELD", True, (255,255,255))
                screen.blit(lbl, (sr.x-8, sr.y+22))

            # ── Spread pickup ─────────────────────────────────────────────────
            if S["show_spread"]:
                spr = S["spread_rect"]
                pygame.draw.circle(screen, (180,50,200),   spr.center, 18)
                pygame.draw.circle(screen, (220,120,255),  spr.center, 12)
                pygame.draw.circle(screen, (255,255,255),  spr.center,  6)
                lbl = font_tiny.render("SPREAD", True, (255,255,255))
                screen.blit(lbl, (spr.x-8, spr.y+22))

            # ── Spread indicator bar ──────────────────────────────────────────
            if S["spread_active"]:
                bw = int((S["spread_timer"] / SPREAD_DURATION) * 64)
                pygame.draw.rect(screen, (100,30,120),
                                 (pr.x, pr.y-26, 64, 8), border_radius=4)
                pygame.draw.rect(screen, (220,120,255),
                                 (pr.x, pr.y-26, bw, 8), border_radius=4)
                lbl = font_tiny.render("SPREAD", True, (220,120,255))
                screen.blit(lbl, (pr.x-4, pr.y-40))

            # ── Shield bubble ─────────────────────────────────────────────────
            if S["shield_active"]:
                pygame.draw.circle(screen, (100,180,255), pr.center, 48, 4)
                bw = int((S["shield_timer"] / SHIELD_DURATION) * 64)
                pygame.draw.rect(screen, (30,30,180),
                                 (pr.x, pr.y-14, 64, 8), border_radius=4)
                pygame.draw.rect(screen, (100,180,255),
                                 (pr.x, pr.y-14, bw, 8), border_radius=4)

            # ── Player (flicker when invincible) ──────────────────────────────
            if not S["invincible"] or int(S["invincible_timer"]*10) % 2 == 0:
                screen.blit(sprite_image, pr)

            # ── Floating combo texts ───────────────────────────────────────────
            for ft in S["combo_bonus_text"]:
                c2 = S["combo"]
                col = ((255,80,80) if c2>=10 else
                       (255,180,0) if c2>=5  else
                       (220,120,255) if S["spread_active"] else
                       (255,220,50))
                txt = font_tiny.render(ft[3], True, col)
                screen.blit(txt, (ft[0]-txt.get_width()//2, int(ft[1])))

            # ── HUD ───────────────────────────────────────────────────────────
            draw_health_bar(S["player_hp"], S["max_hp"])
            draw_enemy_health_bar(S["enemy_hp"], S["enemy_max_hp"])

            sc_surf = font_small.render(f"Score: {S['score']}", True, (255,220,50))
            screen.blit(sc_surf, (SW - sc_surf.get_width() - 20, 20))

            if S["combo"] >= 2:
                c2  = S["combo"]
                col = (255,80,80) if c2>=10 else (255,180,0) if c2>=5 else (255,255,255)
                cs  = font_small.render(f"COMBO x{c2}", True, col)
                screen.blit(cs, (SW//2 - cs.get_width()//2, 50))

            # Controls reminder
            hint = font_tiny.render("WASD move  |  SPACE shoot  |  M mute", True, (160,150,140))
            screen.blit(hint, (20, SH - 22))

        elif S["victory"]:
            draw_victory()
        else:
            draw_game_over()

        pygame.display.flip()
        dt = clock.tick(60) / 1000

        # ── REQUIRED for pygbag — yields control back to the browser ──────────
        await asyncio.sleep(0)

    pygame.quit()


asyncio.run(main())
