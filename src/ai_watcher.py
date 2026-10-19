import math
import heapq
import random
import pygame
from src.sound_system import SoundSystem

class WatcherDrone:
    def __init__(self, x, y, patrol_route=None, drone_id="drone_sentry"):
        self.x = float(x)
        self.y = float(y)
        self.drone_id = drone_id
        self.patrol_route = patrol_route or [(x, y)]
        self.patrol_index = 0
        self.state = 'PATROL'  # PATROL, INVESTIGATE, CHASE, SEARCH, STUNNED
        
        self.speed = 1.3
        self.chase_speed = 2.4
        self.angle = 0.0
        self.fov = math.radians(80)
        self.view_distance = 5.5
        
        self.path = []
        self.target_pos = None
        self.search_timer = 0.0
        self.stun_timer = 0.0
        self.detection_meter = 0.0  # 0.0 to 1.0 (fills before alert triggers)
        
        self.sound = SoundSystem.get_instance()
        self.alert_played = False

    def trigger_distraction(self, dist_x, dist_y, level_map):
        """Called when Clara activates an environmental distraction panel."""
        self.state = 'INVESTIGATE'
        self.target_pos = (float(dist_x), float(dist_y))
        self.path = self._a_star_pathfind((self.x, self.y), self.target_pos, level_map)
        self.detection_meter = 0.0
        self.alert_played = False

    def update(self, player, level_map, dt):
        if self.stun_timer > 0:
            self.stun_timer -= dt
            return None

        px, py = player.x, player.y
        can_see = self._has_line_of_sight((px, py), level_map)

        # Detection logic
        if can_see:
            dist = math.hypot(px - self.x, py - self.y)
            rate = 1.0 + (5.0 - min(5.0, dist)) * 0.5
            self.detection_meter = min(1.0, self.detection_meter + rate * dt)
            if self.detection_meter >= 0.8 and not self.alert_played:
                self.sound.play('drone_alert')
                self.alert_played = True
            if self.detection_meter >= 1.0:
                self.state = 'CHASE'
        else:
            self.detection_meter = max(0.0, self.detection_meter - 0.6 * dt)
            if self.detection_meter == 0.0:
                self.alert_played = False

        # State Machine
        if self.state == 'PATROL':
            if can_see and self.detection_meter >= 1.0:
                self.state = 'CHASE'
                self.path = []
            elif not self.path and self.patrol_route:
                self.target_pos = self.patrol_route[self.patrol_index]
                self.path = self._a_star_pathfind((self.x, self.y), self.target_pos, level_map)
                
        elif self.state == 'INVESTIGATE':
            if can_see and self.detection_meter >= 1.0:
                self.state = 'CHASE'
                self.path = []
            elif not self.path:
                self.state = 'SEARCH'
                self.search_timer = 3.5

        elif self.state == 'CHASE':
            if can_see:
                self.target_pos = (px, py)
                # Recalculate path occasionally
                if len(self.path) < 2 or random.random() < 0.1:
                    self.path = self._a_star_pathfind((self.x, self.y), self.target_pos, level_map)
            else:
                self.state = 'SEARCH'
                self.search_timer = 4.0

        elif self.state == 'SEARCH':
            if can_see and self.detection_meter >= 1.0:
                self.state = 'CHASE'
                self.path = []
            else:
                self.search_timer -= dt
                if self.search_timer <= 0:
                    self.state = 'PATROL'
                    self.path = []
                    self.detection_meter = 0.0

        # Movement along path
        curr_speed = self.chase_speed if self.state == 'CHASE' else self.speed
        if self.path:
            tx, ty = self.path[0]
            dx = tx - self.x
            dy = ty - self.y
            dist = math.hypot(dx, dy)
            self.angle = math.atan2(dy, dx) % (2 * math.pi)

            step = curr_speed * dt
            if dist <= step:
                self.x, self.y = tx, ty
                self.path.pop(0)
                if self.state == 'PATROL' and not self.path:
                    self.patrol_index = (self.patrol_index + 1) % len(self.patrol_route)
            else:
                self.x += math.cos(self.angle) * step
                self.y += math.sin(self.angle) * step

        # Check proximity attack / catch condition
        dist_to_player = math.hypot(px - self.x, py - self.y)
        if dist_to_player < 0.8 and self.state == 'CHASE':
            # Caught! Deal damage and trigger recoverable respawn
            player.take_damage(25.0)
            player.respawn_at_checkpoint()
            self.state = 'PATROL'
            self.path = []
            self.detection_meter = 0.0
            self.stun_timer = 2.0
            return "WATCHER SECURITY PURGE ACTIVATED. RESTORING AT CHECKPOINT."

        return None

    def _has_line_of_sight(self, target_pos, level_map):
        ax, ay = self.x, self.y
        tx, ty = target_pos
        dist = math.hypot(tx - ax, ty - ay)
        if dist > self.view_distance:
            return False

        to_target_angle = math.atan2(ty - ay, tx - ax) % (2 * math.pi)
        angle_diff = abs(to_target_angle - self.angle)
        angle_diff = min(angle_diff, 2 * math.pi - angle_diff)
        if angle_diff > self.fov / 2.0:
            return False

        # Ray check grid cells
        steps = int(dist * 6)
        if steps == 0: return True
        for i in range(1, steps):
            t = i / steps
            rx = ax + (tx - ax) * t
            ry = ay + (ty - ay) * t
            cx, cy = int(rx), int(ry)
            if 0 <= cy < len(level_map) and 0 <= cx < len(level_map[0]):
                if level_map[cy][cx] in ['#', 'D', 'Z']:
                    return False
        return True

    def _a_star_pathfind(self, start, goal, level_map):
        start_grid = (int(start[0]), int(start[1]))
        goal_grid = (int(goal[0]), int(goal[1]))
        if start_grid == goal_grid:
            return [(goal[0], goal[1])]

        frontier = []
        heapq.heappush(frontier, (0, start_grid))
        came_from = {start_grid: None}
        cost_so_far = {start_grid: 0}

        while frontier:
            _, current = heapq.heappop(frontier)
            if current == goal_grid:
                break

            for dx, dy in [(-1, 0), (1, 0), (0, -1), (0, 1)]:
                nxt = (current[0] + dx, current[1] + dy)
                if 0 <= nxt[1] < len(level_map) and 0 <= nxt[0] < len(level_map[0]):
                    if level_map[nxt[1]][nxt[0]] in ['#', 'D', 'Z']:
                        continue
                    new_cost = cost_so_far[current] + 1
                    if nxt not in cost_so_far or new_cost < cost_so_far[nxt]:
                        cost_so_far[nxt] = new_cost
                        priority = new_cost + (abs(goal_grid[0] - nxt[0]) + abs(goal_grid[1] - nxt[1]))
                        heapq.heappush(frontier, (priority, nxt))
                        came_from[nxt] = current

        if goal_grid not in came_from:
            return []

        curr = goal_grid
        route = []
        while curr is not None:
            route.append((curr[0] + 0.5, curr[1] + 0.5))
            curr = came_from[curr]
        route.reverse()
        return route
