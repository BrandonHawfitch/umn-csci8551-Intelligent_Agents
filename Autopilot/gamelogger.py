import datetime
import json
from pathlib import Path

class GameLogger:
    def __init__(self, run_tag="run", run_number=1, shared_timestamp=None):
        # Use shared timestamp if provided, otherwise create new one
        if shared_timestamp is None:
            ts = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        else:
            ts = shared_timestamp
        
        # Create logs directory if it doesn't exist
        log_dir = Path("logs")
        log_dir.mkdir(exist_ok=True)
        
        # Save log file in the logs directory
        self.filename = f"game_log_{run_tag}_{ts}_{run_number}.txt"
        self.path = log_dir / self.filename
        self.file = self.path.open("w", encoding="utf-8")
        
        # We store the previous state to calculate "Deltas" (changes)
        self.last_public_state = None
        self.pending_round_end_changes = None  # Store changes that happen at round end
        
        # Header
        self.file.write(f"SKY TEAM SIMULATION LOG - {ts}\n")
        self.file.write("="*60 + "\n\n")

    def log_step(self, step_idx, action, result):
        # 1. Parse Data
        obs_next = result.get("observation", {})
        public = obs_next.get("publicState", {})
        player_state = obs_next.get("playersState", {})
        
        reward = result.get("reward", 0.0)
        is_done = result.get("isDone", False)

        # 2. Check if this is the first step of a new round (dice were just re-rolled)
        # Detect by checking if all dice are fresh (none used) and altitude changed
        is_new_round = self._detect_new_round(player_state, public)

        # 3. Format the Action (The "Narrative")
        action_desc = self._describe_action(action)
        
        # 4. Format State Changes (The "Impact")
        state_desc = self._describe_state_delta(public, exclude_altitude=is_new_round)
        
        # 5. Format Player Dice
        dice_desc = self._describe_player_dice(player_state)
        
        # 6. Write to File
        self.file.write(f"STEP {step_idx:02d} | {action_desc}\n")
        self.file.write(f"        > {state_desc}\n")
        self.file.write(f"        > {dice_desc}\n")
        
        if reward != 0:
            self.file.write(f"        > *** REWARD: {reward} ***\n")
        
        # 7. If a new round just started, show the round end summary BEFORE regular output
        if is_new_round and self.last_public_state:
            prev_alt = self.last_public_state.get("altitude")
            curr_alt = public.get("altitude")
            if prev_alt != curr_alt:
                self.file.write(f"        > === ROUND END: Altitude {prev_alt}->{curr_alt} ===\n")
            
        if is_done:
            # write summary separator now
            self.file.write("\n" + "="*60 + "\n")
            # detailed final snapshot + cause
            self.log_game_end(result)
            self.file.write("\n" + "="*60 + "\n")
            outcome = "VICTORY" if reward > 0 else "DEFEAT"
            self.file.write(f"GAME OVER: {outcome}\n")
            self.file.write("="*60 + "\n")

        self.file.write("-" * 40 + "\n")
        self.file.flush()
        
        # Update history
        self.last_public_state = public

    def _detect_new_round(self, player_state, public_state):
        """Detect if this is the first step of a new round."""
        if not self.last_public_state:
            return False
        
        # Check if altitude changed (indicator of round end processing)
        prev_alt = self.last_public_state.get("altitude")
        curr_alt = public_state.get("altitude")
        
        # Check if all dice are unused (fresh roll)
        dice = player_state.get("dice", [])
        all_unused = all(not d.get("isUsed", False) for d in dice)
        
        return prev_alt != curr_alt and all_unused

    def log_initial_state(self, observation):
        """Log the starting state before any actions."""
        public = observation.get("publicState", {})
        pilot_state = observation.get("playersState", {})
        
        self.file.write("INITIAL STATE\n")
        self.file.write("-" * 40 + "\n")
        
        # Full state display
        state_desc = self._format_full_state(public)
        self.file.write(f"        > {state_desc}\n")
        
        # Both players' dice
        pilot_dice = self._describe_player_dice(pilot_state)
        self.file.write(f"        > {pilot_dice}\n")
        
        # Note: We can't show copilot dice at start since observation only shows current player
        # But we can note it
        self.file.write(f"        > [Copilot dice hidden - not current player]\n")
        
        self.file.write("="*60 + "\n\n")
        self.file.flush()
        
        # Store as baseline
        self.last_public_state = public
        self.last_player_state = pilot_state

    def _describe_action(self, action):
        """Converts an action dictionary into a readable string."""
        role = action.get("role", "Unknown")
        type_ = action.get("$type", "unknown")
        
        if "placeDie" in type_:
            die_obj = action.get("die", {})
            die_val = die_obj.get("value", "?")
            
            # Navigate nicely through the JSON structure to find module name
            pos = action.get("position", {})
            module_name = pos.get("module", {})
            
            return f"[{role}] PLACES DIE [VALUE {die_val}] on '{module_name}'"
            
        elif "useCoffee" in type_:
            die_obj = action.get("dieToModify", {})
            die_val = die_obj.get("value", "?")
            effect = action.get("effect", "Modify")
            
            return f"[{role}] USES COFFEE on Die {die_val} -> {effect}"
            
        elif "useReroll" in type_:
            return f"[{role}] USES REROLL Token"
            
        return f"[{role}] Performs {type_}"

    def _describe_player_dice(self, player_state):
        """Format the current player's dice state."""
        role = player_state.get("role", "Unknown")
        dice = player_state.get("dice", [])
        
        if not dice:
            return f"{role} Dice: []"
        
        # Format dice state: show value and whether it's used
        dice_display = []
        for d in dice:
            val = d.get("value", "?")
            used = d.get("isUsed", False)
            marker = "✓" if used else " "
            dice_display.append(f"{val}{marker}")
        
        dice_str = "[" + ", ".join(dice_display) + "]"
        return f"{role} Dice: {dice_str} (✓=used)"

    def _describe_state_delta(self, current_state, exclude_altitude=False):
        """Compares current state to previous state and highlights changes."""
        if not self.last_public_state:
            # First step, show all initial values
            return self._format_full_state(current_state)

        parts = []
        
        # Check Altitude (skip if we're at start of new round)
        if not exclude_altitude:
            curr_alt = current_state.get("altitude")
            prev_alt = self.last_public_state.get("altitude")
            if curr_alt != prev_alt:
                parts.append(f"Alt: {prev_alt}->{curr_alt}")
            else:
                parts.append(f"Alt: {curr_alt}")
        else:
            # Just show current altitude without delta
            parts.append(f"Alt: {current_state.get('altitude')}")

        # Check Tilt
        curr_tilt = current_state.get("axisTilt")
        prev_tilt = self.last_public_state.get("axisTilt")
        if curr_tilt != prev_tilt:
            parts.append(f"Tilt: {prev_tilt}->{curr_tilt}")
        else:
            parts.append(f"Tilt: {curr_tilt}")

        # Check Approach Track Index
        curr_track = current_state.get("approachTrack", {})
        prev_track = self.last_public_state.get("approachTrack", {})
        
        curr_idx = curr_track.get("approachIndex")
        prev_idx = prev_track.get("approachIndex")
        if curr_idx != prev_idx:
            parts.append(f"Track: {prev_idx}->{curr_idx}")
        else:
            parts.append(f"Track: {curr_idx}")
            
        # Check Planes on Approach
        curr_planes = curr_track.get("planesOnApproach", [])
        prev_planes = prev_track.get("planesOnApproach", [])
        if curr_planes != prev_planes:
            parts.append(f"Planes: {prev_planes}->{curr_planes}")
        
        # Check Aero Markers
        curr_blue = current_state.get("blueAeroMarker")
        prev_blue = self.last_public_state.get("blueAeroMarker")
        curr_orange = current_state.get("orangeAeroMarker")
        prev_orange = self.last_public_state.get("orangeAeroMarker")
        
        if curr_blue != prev_blue or curr_orange != prev_orange:
            parts.append(f"Aero: Blue {prev_blue}->{curr_blue}, Orange {prev_orange}->{curr_orange}")
        
        # Check Brake Marker
        curr_brake = current_state.get("redBrakeMarker")
        prev_brake = self.last_public_state.get("redBrakeMarker")
        if curr_brake != prev_brake:
            parts.append(f"Brake: {prev_brake}->{curr_brake}")
        
        # Check Tokens
        curr_coffee = current_state.get("coffeeTokens")
        prev_coffee = self.last_public_state.get("coffeeTokens")
        curr_reroll = current_state.get("rerollTokens")
        prev_reroll = self.last_public_state.get("rerollTokens")
        
        if curr_coffee != prev_coffee:
            parts.append(f"Coffee: {prev_coffee}->{curr_coffee}")
        if curr_reroll != prev_reroll:
            parts.append(f"Reroll: {prev_reroll}->{curr_reroll}")

        return " | ".join(parts)
    
    def _format_full_state(self, state):
        """Format complete state for first step."""
        track = state.get("approachTrack", {})
        parts = [
            f"Alt: {state.get('altitude')}",
            f"Tilt: {state.get('axisTilt')}",
            f"Track: {track.get('approachIndex')}",
            f"Planes: {track.get('planesOnApproach', [])}",
            f"Aero: Blue {state.get('blueAeroMarker')}, Orange {state.get('orangeAeroMarker')}",
            f"Brake: {state.get('redBrakeMarker')}",
            f"Coffee: {state.get('coffeeTokens')}",
            f"Reroll: {state.get('rerollTokens')}"
        ]
        return " | ".join(parts)

    def _infer_game_end_cause(self, public_state):
        # Mirrors simulator.IsGameLost/IsGameWon logic heuristically from public_state
        axis = public_state.get("axisTilt")
        alt = public_state.get("altitude")
        track = public_state.get("approachTrack", {})
        idx = track.get("approachIndex")
        planes = track.get("planesOnApproach", [])
        # collision heuristic: any plane at/before current index > 0
        collision = any(p > 0 for p in planes[:max(0, idx)])

        # safe landing condition (approx since landingSpeed may be absent)
        red_brake = public_state.get("redBrakeMarker")
        landing_speed = public_state.get("landingSpeed")  # may be None in observation
        at_runway = (idx == (track.get("trackLength") or len(planes)) - 1)

        if alt == 0 and axis == 0 and at_runway and landing_speed is not None and red_brake is not None and landing_speed < red_brake:
            return "Win: Safe landing achieved (level axis, runway reached, speed under brake marker)."

        # Altitude check
        if alt is not None and alt < 0:
            return "Loss: Altitude below ground."

        # Collision check
        if collision:
            return "Loss: Plane collision detected on approach track."

        # Axis tilt check
        if axis is not None and (axis < -2 or axis > 2):
            return "Loss: Axis tilt out of bounds."
        
        # Overshot runway check
        trackLength = track.get("trackLength", 0)
        ApproachIndex = track.get("approachIndex", 0)
        isBeyondRunway = trackLength - ApproachIndex - 1 < 0
        if isBeyondRunway:
            return "Loss: Plane has overshot the runway."
        
        # Landing speed check during final round
        if alt == 0 and landing_speed is not None and red_brake is not None and landing_speed > red_brake:
            return "Loss: Landing speed above red brake marker during final round."

        # Fallback
        return "Game ended: terminal condition reached (see final state)."


    def log_game_end(self, result):
      self.file.write("\n" + "="*60 + "\n")
      self.file.write("FINAL STATE\n")
      self.file.write("-" * 40 + "\n")
      obs_next = result.get("observation", {})
      public = obs_next.get("publicState", {})
      players = obs_next.get("playersState", {})

      # Full public-state snapshot
      final_desc = self._format_full_state(public)
      self.file.write(f"        > {final_desc}\n")

      # Current player dice snapshot
      self.file.write(f"        > {self._describe_player_dice(players)}\n")

      # Cause
      cause = self._infer_game_end_cause(public)
      reward = result.get("reward", 0.0)
      outcome = "VICTORY" if reward and reward > 0 else "DEFEAT"
      self.file.write(f"\nOUTCOME: {outcome}\n")
      self.file.write(f"CAUSE: {cause}\n")
      self.file.write("="*60 + "\n")
      self.file.flush()

    def close(self):
        self.file.close()
        print(f"Log saved to {self.filename}")