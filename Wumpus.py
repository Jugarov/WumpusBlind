import pygame
import sys
import random
import math
from collections import defaultdict

# ==========================
# CONFIGURACIÓN DEL JUEGO
# ==========================
WIDTH, HEIGHT = 1000, 720
FPS = 60

# Tablero axial (hexágonos con punta arriba: "pointy-topped")
GRID_COLS = 8  # q
GRID_ROWS = 7  # r
HEX_SIZE = 42  # radio del hex (distancia del centro a un vértice)
MARGIN_TOP = 80
MARGIN_LEFT = 80

# Puntuación
STEP_COST = 10
GOLD_REWARD = 1000
WUMPUS_KILL_REWARD = 1000
BAT_KILL_REWARD = 100

# Cantidades de entidades
NUM_WUMPUS = 1
NUM_PITS = 1
NUM_BATS = 1
NUM_GOLD = 1
NUM_ARROWS = (NUM_WUMPUS + NUM_BATS) * 2

# Colores
WHITE = (250, 250, 250)
BLACK = (20, 20, 20)
GRAY = (70, 70, 70)
LIGHT_GRAY = (150, 150, 150)
BG_COLOR = (17, 19, 23)
HEX_FILL = (36, 40, 48)
HEX_BORDER = (90, 96, 110)
PLAYER_COLOR = (255, 215, 0)
WUMPUS_COLOR = (180, 50, 50)
PIT_COLOR = (0, 0, 0)
BAT_COLOR = (120, 70, 170)
GOLD_COLOR = (255, 203, 0)

GREEN_STENCH = (60, 180, 75)
BLUE_BREEZE = (100, 180, 255)

# Direcciones axiales (pointy), en sentido horario
DIRECTIONS = [
    (1, 0),   # 0: E
    (1, -1),  # 1: NE
    (0, -1),  # 2: N
    (-1, 0),  # 3: O
    (-1, 1),  # 4: SO
    (0, 1),   # 5: S
]
DIR_NAMES = ["E", "NE", "N", "O", "SO", "S"]

ENTITY_NONE = 0
ENTITY_WUMPUS = 1
ENTITY_PIT = 2
ENTITY_BAT = 3
ENTITY_GOLD = 4

ENTITY_NAMES = {
    ENTITY_WUMPUS: "Wumpus",
    ENTITY_PIT: "Abismo",
    ENTITY_BAT: "Murciélago",
    ENTITY_GOLD: "Oro",
}

GAME_OVER = False
GAME_OVER_MESSAGE = ""


# ==========================
# UTILIDADES DE HEXÁGONOS
# ==========================

def axial_to_pixel(q, r, size):
    """Convierte coordenadas axiales (q, r) a pixeles para hex pointy-topped."""
    x = size * math.sqrt(3) * (q + r / 2) + MARGIN_LEFT
    y = size * 1.5 * r + MARGIN_TOP
    return (int(x), int(y))


def hex_corners(center, size):
    cx, cy = center
    corners = []
    for i in range(6):
        angle_deg = 60 * i - 30
        angle_rad = math.radians(angle_deg)
        x = cx + size * math.cos(angle_rad)
        y = cy + size * math.sin(angle_rad)
        corners.append((int(x), int(y)))
    return corners


def neighbors(q, r):
    for dq, dr in DIRECTIONS:
        yield (q + dq, r + dr)


def wrap_bounds(q, r):
    # Warp en los límites del tablero
    q = q % GRID_COLS
    r = r % GRID_ROWS
    return q, r


# ==========================
# CLASES DE JUEGO
# ==========================
class Board:
    def __init__(self):
        self.entities = {}
        self.generate_board()

    def empty_cells(self):
        return [(q, r) for q in range(GRID_COLS) for r in range(GRID_ROWS) if (q, r) not in self.entities]

    def random_empty_cell(self):
        empties = self.empty_cells()
        return random.choice(empties) if empties else None

    def place_random(self, entity, n=1):
        for _ in range(n):
            cell = self.random_empty_cell()
            if cell is not None:
                self.entities[cell] = entity

    def generate_board(self):
        self.entities.clear()
        self.place_random(ENTITY_WUMPUS, NUM_WUMPUS)
        self.place_random(ENTITY_PIT, NUM_PITS)
        self.place_random(ENTITY_BAT, NUM_BATS)
        self.place_random(ENTITY_GOLD, NUM_GOLD)

    def entity_at(self, q, r):
        return self.entities.get((q, r), ENTITY_NONE)

    def remove_entity(self, q, r):
        if (q, r) in self.entities:
            del self.entities[(q, r)]

    def cells_with(self, entity_type):
        return [pos for pos, ent in self.entities.items() if ent == entity_type]


class Player:
    def __init__(self, board):
        while True:
            self.q = random.randrange(GRID_COLS)
            self.r = random.randrange(GRID_ROWS)
            if board.entity_at(self.q, self.r) == ENTITY_NONE:
                break
        self.dir_idx = 0
        self.score = 0
        self.alive = True
        self.win = False
        self.arrows = NUM_ARROWS

    def rotate_left(self):
        self.dir_idx = (self.dir_idx - 1) % 6

    def rotate_right(self):
        self.dir_idx = (self.dir_idx + 1) % 6

    def forward_pos(self):
        dq, dr = DIRECTIONS[self.dir_idx]
        return (self.q + dq, self.r + dr)

    def move_forward(self, board):
        if not self.alive or self.win:
            return
        nq, nr = self.forward_pos()
        nq, nr = wrap_bounds(nq, nr)
        self.q, self.r = nq, nr
        self.score -= STEP_COST
        ent = board.entity_at(self.q, self.r)
        if ent == ENTITY_WUMPUS or ent == ENTITY_PIT:
            self.alive = False
        elif ent == ENTITY_BAT:
            dest = board.random_empty_cell()
            if dest is not None:
                self.q, self.r = dest
        elif ent == ENTITY_GOLD:
            self.score += GOLD_REWARD
            board.remove_entity(self.q, self.r)

    def shoot_arrow(self, board):
        self.arrows -= 1
        target_q, target_r = self.forward_pos()
        target_q, target_r = wrap_bounds(target_q, target_r)
        ent = board.entity_at(target_q, target_r)
        if ent == ENTITY_WUMPUS:
            self.score += WUMPUS_KILL_REWARD
            board.remove_entity(target_q, target_r)
        elif ent == ENTITY_BAT:
            self.score += BAT_KILL_REWARD
            board.remove_entity(target_q, target_r)

# ==========================
# DIBUJADO
# ==========================

def draw_hex(surface, center, size, fill, border):
    pts = hex_corners(center, size)
    pygame.draw.polygon(surface, fill, pts)
    pygame.draw.polygon(surface, border, pts, 2)


def draw_player(surface, center, size, dir_idx):
    cx, cy = center
    r = int(size * 0.5)
    pygame.draw.circle(surface, PLAYER_COLOR, (cx, cy), r)
    # indicador de dirección (triángulo pequeño)
    ang_deg = [0, -60, -120, 180, 120, 60][dir_idx]
    ang = math.radians(ang_deg)
    tip = (cx + int(r * 1.1 * math.cos(ang)), cy + int(r * 1.1 * math.sin(ang)))
    left = (cx + int(r * 0.6 * math.cos(ang + math.radians(120))), cy + int(r * 0.6 * math.sin(ang + math.radians(120))))
    right = (cx + int(r * 0.6 * math.cos(ang - math.radians(120))), cy + int(r * 0.6 * math.sin(ang - math.radians(120))))
    pygame.draw.polygon(surface, BLACK, [tip, left, right])


def draw_entity_icon(surface, center, size, entity):
    cx, cy = center
    if entity == ENTITY_WUMPUS:
        pygame.draw.circle(surface, WUMPUS_COLOR, (cx, cy), int(size * 0.35))
        pygame.draw.circle(surface, BLACK, (cx - 6, cy - 5), 4)
        pygame.draw.circle(surface, BLACK, (cx + 6, cy - 5), 4)
        pygame.draw.arc(surface, BLACK, (cx - 12, cy - 2, 24, 16), math.radians(10), math.radians(170), 2)
    elif entity == ENTITY_PIT:
        pygame.draw.circle(surface, PIT_COLOR, (cx, cy), int(size * 0.38))
        pygame.draw.circle(surface, HEX_FILL, (cx, cy), int(size * 0.30))
    elif entity == ENTITY_BAT:
        w = int(size * 0.7)
        h = int(size * 0.35)
        pygame.draw.ellipse(surface, BAT_COLOR, (cx - w//2, cy - h//2, w, h))
        pygame.draw.polygon(surface, BAT_COLOR, [(cx - w//2, cy), (cx - w//2 - 10, cy - 6), (cx - w//2 - 10, cy + 6)])
        pygame.draw.polygon(surface, BAT_COLOR, [(cx + w//2, cy), (cx + w//2 + 10, cy - 6), (cx + w//2 + 10, cy + 6)])
    elif entity == ENTITY_GOLD:
        pygame.draw.polygon(surface, GOLD_COLOR, [
            (cx, cy - int(size * 0.35)),
            (cx + int(size * 0.25), cy),
            (cx, cy + int(size * 0.35)),
            (cx - int(size * 0.25), cy)
        ])
        pygame.draw.rect(surface, GOLD_COLOR, (cx - int(size * 0.18), cy - int(size * 0.10), int(size * 0.36), int(size * 0.20)))


def draw_stench(surface, center, size):
    # nube verde semitransparente
    cloud = pygame.Surface((size*2, size*2), pygame.SRCALPHA)
    pygame.draw.circle(cloud, (*GREEN_STENCH, 90), (size, size), int(size * 0.55))
    pygame.draw.circle(cloud, (*GREEN_STENCH, 120), (int(size*0.6), int(size*0.7)), int(size * 0.3))
    pygame.draw.circle(cloud, (*GREEN_STENCH, 120), (int(size*1.4), int(size*0.8)), int(size * 0.28))
    surface.blit(cloud, (center[0] - size, center[1] - size))


def draw_breeze(surface, center, size):
    # líneas que representan viento
    cx, cy = center
    for i in range(-1, 2):
        y = cy + i * int(size * 0.2)
        pygame.draw.arc(surface, BLUE_BREEZE, (cx - int(size*0.7), y - 8, int(size*1.4), 16), math.radians(200), math.radians(340), 2)


def compute_hints(board):
    stench = set()
    breeze = set()
    for (q, r), ent in board.entities.items():
        if ent == ENTITY_WUMPUS:
            for nq, nr in neighbors(q, r):
                if wrap_bounds(nq, nr):
                    stench.add((nq, nr))
        elif ent == ENTITY_PIT:
            for nq, nr in neighbors(q, r):
                if wrap_bounds(nq, nr):
                    breeze.add((nq, nr))
    return stench, breeze


# ==========================
# BUCLE PRINCIPAL
# ==========================

def reset_game():
    board = Board()
    player = Player(board)
    return board, player


def main():
    pygame.init()
    screen = pygame.display.set_mode((WIDTH, HEIGHT))
    pygame.display.set_caption("Hex Wumpus — Flechas: ← → giran, ↑ avanza | R reinicia")
    clock = pygame.time.Clock()
    font = pygame.font.SysFont("consolas", 22)
    small = pygame.font.SysFont("consolas", 16)

    board, player = reset_game()

    global GAME_OVER, GAME_OVER_MESSAGE
    running = True
    while running:
        dt = clock.tick(FPS)
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    running = False
                elif event.key == pygame.K_r:
                    board, player = reset_game()
                elif event.key == pygame.K_LEFT:
                    player.rotate_left()
                elif event.key == pygame.K_RIGHT:
                    player.rotate_right()
                elif event.key == pygame.K_UP:
                    if player.alive and not player.win:
                        player.move_forward(board)
                elif event.key == pygame.K_SPACE:
                    if player.alive and not player.win and player.arrows > 0:
                        player.shoot_arrow(board)

        # Condiciones de victoria o derrota
        if not player.alive:
            GAME_OVER = True
            GAME_OVER_MESSAGE = "¡Has muerto! Intenta de nuevo"
        elif not board.cells_with(ENTITY_GOLD):
            player.win = True
            GAME_OVER = True
            GAME_OVER_MESSAGE = "¡Has ganado! Pulsa R para reiniciar"

        screen.fill(BG_COLOR)

        # Calcular pistas (stench/breeze)
        stench, breeze = compute_hints(board)

        # Dibujo del tablero
        player_cell = (player.q, player.r)
        for r in range(GRID_ROWS):
            for q in range(GRID_COLS):
                center = axial_to_pixel(q, r, HEX_SIZE)
                draw_hex(screen, center, HEX_SIZE, HEX_FILL, HEX_BORDER)

                # Pistas visuales en casillas adyacentes
                if (q, r) in stench:
                    draw_stench(screen, center, HEX_SIZE)
                if (q, r) in breeze:
                    draw_breeze(screen, center, HEX_SIZE)

                # Entidad (opcional: siempre visible para debug/juego casual)
                ent = board.entity_at(q, r)
                if ent != ENTITY_NONE:
                    draw_entity_icon(screen, center, HEX_SIZE, ent)

                # Jugador
                if (q, r) == player_cell:
                    draw_player(screen, center, HEX_SIZE, player.dir_idx)

        # Panel superior
        pygame.draw.rect(screen, (26, 28, 34), (0, 0, WIDTH, MARGIN_TOP - 10))
        info = f"Puntos: {player.score}   Dir: {DIR_NAMES[player.dir_idx]}   Pos: ({player.q},{player.r})   Controles: ←/→ giran, ↑ avanza, R reinicia"
        screen.blit(font.render(info, True, WHITE), (16, 16))
        arrows_info = f"Flechas: {player.arrows}"
        screen.blit(font.render(arrows_info, True, WHITE), (16, 44))

        # Leyenda
        legend_y = HEIGHT - 90
        pygame.draw.rect(screen, (26, 28, 34), (0, legend_y - 10, WIDTH, 100))
        screen.blit(small.render("Leyenda:", True, WHITE), (16, legend_y - 4))
        # Stench
        cx = 120; cy = legend_y + 20
        draw_hex(screen, (cx, cy), 18, HEX_FILL, HEX_BORDER)
        draw_stench(screen, (cx, cy), 18)
        screen.blit(small.render("Mal olor (Wumpus adyacente)", True, WHITE), (150, legend_y + 10))
        # Breeze
        cx2 = 120; cy2 = legend_y + 50
        draw_hex(screen, (cx2, cy2), 18, HEX_FILL, HEX_BORDER)
        draw_breeze(screen, (cx2, cy2), 18)
        screen.blit(small.render("Brisa (Abismo adyacente)", True, WHITE), (150, legend_y + 40))
        # Entidades
        ex = 520; ey = legend_y + 20
        draw_hex(screen, (ex, ey), 18, HEX_FILL, HEX_BORDER)
        draw_entity_icon(screen, (ex, ey), 18, ENTITY_WUMPUS)
        screen.blit(small.render("Wumpus (mueres al entrar)", True, WHITE), (550, legend_y + 10))
        ex2 = 520; ey2 = legend_y + 50
        draw_hex(screen, (ex2, ey2), 18, HEX_FILL, HEX_BORDER)
        draw_entity_icon(screen, (ex2, ey2), 18, ENTITY_PIT)
        screen.blit(small.render("Abismo (mueres al caer)", True, WHITE), (550, legend_y + 40))
        ex3 = 820; ey3 = legend_y + 20
        draw_hex(screen, (ex3, ey3), 18, HEX_FILL, HEX_BORDER)
        draw_entity_icon(screen, (ex3, ey3), 18, ENTITY_BAT)
        screen.blit(small.render("Murciélago (teletransporta)", True, WHITE), (850, legend_y + 10))
        ex4 = 820; ey4 = legend_y + 50
        draw_hex(screen, (ex4, ey4), 18, HEX_FILL, HEX_BORDER)
        draw_entity_icon(screen, (ex4, ey4), 18, ENTITY_GOLD)
        screen.blit(small.render("Oro (+1000 puntos)", True, WHITE), (850, legend_y + 40))

        if GAME_OVER:
            screen.fill((0, 0, 0))
            font_big = pygame.font.SysFont(None, 72)
            font_small = pygame.font.SysFont(None, 36)

            text = font_big.render(GAME_OVER_MESSAGE, True, (255, 255, 255))
            rect = text.get_rect(center=(WIDTH//2, HEIGHT//2 - 50))
            screen.blit(text, rect)

            restart_text = font_small.render("Presiona R para jugar de nuevo", True, (200, 200, 200))
            rect2 = restart_text.get_rect(center=(WIDTH//2, HEIGHT//2 + 50))
            screen.blit(restart_text, rect2)

            pygame.display.flip()

            # esperar tecla para reiniciar
            keys = pygame.key.get_pressed()
            if keys[pygame.K_r]:
                board, player = reset_game()
                GAME_OVER = False
                GAME_OVER_MESSAGE = ""

        pygame.display.flip()

    pygame.quit()
    sys.exit()


if __name__ == "__main__":
    main()