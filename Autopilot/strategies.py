from __future__ import annotations
from abc import ABC, abstractmethod
from itertools import combinations_with_replacement
from collections import Counter
import numpy as np
import math

import random

number_of_dice = 4  # Total dice per player
dice_values = [1, 2, 3, 4, 5, 6] # Possible die values
all_hands = [tuple(sorted(hand)) for hand in combinations_with_replacement(dice_values, number_of_dice)] # All possible hands

class BeliefTracker:
    """
    Tracks the probability distribution of the PARTNER'S hidden dice.
    """
    def __init__(self, partner_role):
        self.partner_role = partner_role
        self.reset()
    
    # Resets belief to uniform distribution over all possible hands
    # This should be performed at the start of each round, as players redraw dice
    def reset(self):
        """Resets belief to uniform distribution."""
        self.hands = all_hands
        # 2. Calculate initial likelihood (Prior) for each hand
        self.probs = np.array([self._calculate_multinomial_prob(h) for h in self.hands])
        self.probs /= self.probs.sum() # Normalize

        # Pre-compute masks for fast lookups
        # hand_masks[v][i] is True if hand i contains value v+1
        self._rebuild_masks()
                
        self.dice_remaining = 4
        

    
    def update(self, action_history, public_state):
        """Updates belief based on the most recent action."""
        if not action_history:
            return
        
        last_action = action_history[-1]
        if last_action.get('role') != self.partner_role:
            return  # Only update on partner's actions

        last_action = action_history[-1]
        role = last_action.get('role')

        # Only update if the PARTNER acted
        if role != self.partner_role:
            return
        
        die_val = self._extract_die_value(last_action)
        self.dice_remaining = max(0, self.dice_remaining - 1)
        
        # --- POSITIVE UPDATE ---
        # Partner played 'die_val'. Therefore, they MUST have had 'die_val' in their hand.
        # We filter our list of possible hands to keep only those that contain 'die_val'.
        # Then we "remove" that die from the hand for future tracking.
        new_hands = []
        new_probs = []
        
        for hand, prob in zip(self.hands, self.probs):
            if prob == 0: continue
            
            # Check if this hand contains the die played
            # Convert tuple to list to manipulate
            hand_list = list(hand)
            if die_val in hand_list:
                # Hand is consistent! 
                # State Transition: The new "hand" state has that die removed.
                hand_list.remove(die_val)
                # We store the *remaining* dice as the new state for that probability mass
                new_hands.append(tuple(sorted(hand_list)))
                new_probs.append(prob)
            else:
                # Impossible hand. Probability becomes 0.
                pass 
        
        # Consolidate duplicate states
        # (e.g. (1,5) and (5,1) might both result from removing a die, but here we keep sorted tuples so it's handled)
        # However, multiple original hands might collapse into the same remaining hand.
        # We need to sum their probabilities.
        consolidated = {}
        for h, p in zip(new_hands, new_probs):
            if h not in consolidated: consolidated[h] = 0.0
            consolidated[h] += p
        
        # Update State
        self.hands = list(consolidated.keys())
        self.probs = np.array(list(consolidated.values()))
        
        # Normalize
        if self.probs.sum() > 0:
            self.probs /= self.probs.sum()
        else:
            # Should not happen unless logic error or invalid observation
            # Reset to uniform if we break
            self.probs = np.ones(len(self.hands)) / len(self.hands)
            
        self._rebuild_masks()

    def get_entropy(self):
        """Returns Shannon Entropy: H(X) = -sum(p(x) * log2(p(x)))"""
        probs = self.probs
        # Clip to avoid log(0)
        probs = np.clip(probs, 1e-9, 1.0)
        entropy = -np.sum(probs * np.log2(probs))
        return entropy
    
    def get_hypothetical_entropy(self, observed_die_val: int) -> float:
        """
        Fast vectorized calculation of what entropy WOULD be if we observed a specific die.
        Does not permanently update state.
        """
        if observed_die_val < 1 or observed_die_val > 6:
            return self.get_entropy()

        # 1. Apply mask
        mask = self.hand_masks[observed_die_val - 1]
        hypothetical_probs = self.probs * mask
        
        # 2. Normalize
        total_prob = hypothetical_probs.sum()
        if total_prob == 0: return 100.0 # Impossible event
        
        hypothetical_probs /= total_prob
        
        # 3. Calc Entropy
        # Note: We don't simulate the 'collapse' of hand states here for speed.
        # We assume the distribution of *current* hands narrows. 
        # This is a good proxy for information gain.
        hp = np.clip(hypothetical_probs, 1e-9, 1.0)
        return -np.sum(hp * np.log2(hp))

    def _rebuild_masks(self):
        """Rebuilds the hand masks after hand state changes."""
        self.hand_masks = np.zeros((6, len(self.hands)), dtype=bool)
        for i, hand in enumerate(self.hands):
            for die_val in hand:
                self.hand_masks[die_val-1, i] = True
    
    def _calculate_multinomial_prob(self, hand):
        counts = Counter(hand)
        denom = 1
        for c in counts.values():
            denom *= math.factorial(c)
        permutations = math.factorial(4) / denom
        return permutations * (1/6)**4
    
    # Extract the die value used (if available in the action object)
    # The simulator action object typically has a 'Die' or 'DieToModify' field
    def _extract_die_value(self, action):
        d = action.get('die') or action.get('dieToModify') or {}
        return int(d.get('value', 0))


class Strategy(ABC):
    name: str = "base"

    @abstractmethod
    def select_action(self, valid_actions: list[dict], observation: dict, belief_tracker) -> int:
        ...

# ---------- Helpers ----------
def _get_module_name(action: dict) -> str:
    pos = action.get('position')
    return pos.get('module')

def _get_die_value(action: dict) -> int:
    d = action.get('die') or action.get('dieToModify') or {}
    try:
        return int(d.get('value', 0) or 0)
    except Exception:
        return 0

# ---------- Concrete Strategies ----------
class RandomStrategy(Strategy):
    name = "random"
    def select_action(self, valid_actions, observation, belief_tracker) -> int:
        return random.randint(0, len(valid_actions) - 1)

class EntropyStrategy(Strategy):
    name = "entropy"
    
    def select_action(self, valid_actions, observation, belief_tracker) -> int:
        """
        Minimizes Expected Posterior Entropy.
        1. Identify slots available to partner.
        2. For each of my actions, see how it constrains partner.
        3. Calculate E[Entropy] after partner plays into remaining slots.
        """
        best_idx = 0
        current_entropy = belief_tracker.get_entropy()
        # Initialize with a high value; we want to minimize this
        min_expected_entropy = float('inf') 

        # 1. Parse Board for Partner's Options
        partner_role = belief_tracker.partner_role
        # List of sets of allowed values for every open slot available to partner
        partner_open_slots = self._get_partner_open_slots(observation, partner_role)

        for i, my_action in enumerate(valid_actions):
            # 2. Simulate Board State after My Action
            # Effectively: Remove the slot I just took from the partner's list (if it was shared)
            remaining_slots = self._simulate_board_after_action(partner_open_slots, my_action, observation)
            
            # 3. Calculate Expected Entropy
            # We sum: P(Hand) * P(Partner Plays d | Hand, Slots) * Entropy(Belief | d)
            
            weighted_entropy_sum = 0.0
            total_weight = 0.0
            
            # Optimization: If we assume the partner is rational/random, they will play *some* die.
            # We iterate over possible hands to see what is PLAYABLE.
            
            for hand_idx, prob in enumerate(belief_tracker.probs):
                if prob < 0.0001: continue
                
                hand = belief_tracker.hands[hand_idx]
                
                # Find playable dice from this hand into remaining_slots
                playable_dice = set()
                for die in hand:
                    for slot_allowed in remaining_slots:
                        if die in slot_allowed:
                            playable_dice.add(die)
                
                if not playable_dice:
                    # Partner must Pass. Entropy remains same (no info gained).
                    weighted_entropy_sum += prob * current_entropy
                else:
                    # Partner plays one of the playable dice.
                    # We average the entropy reduction of all valid plays for this hand.
                    hand_outcome_entropies = []
                    for d in playable_dice:
                        post_ent = belief_tracker.get_hypothetical_entropy(d)
                        hand_outcome_entropies.append(post_ent)
                    
                    avg_post_ent = sum(hand_outcome_entropies) / len(hand_outcome_entropies)
                    weighted_entropy_sum += prob * avg_post_ent
                
                total_weight += prob
            
            expected_entropy = weighted_entropy_sum / (total_weight + 1e-9)
            
            # Tie breaker: Prefer actions that result in lower entropy
            # Secondary tie breaker: Random
            if expected_entropy < min_expected_entropy:
                min_expected_entropy = expected_entropy
                best_idx = i
            
        return best_idx

    def _get_partner_open_slots(self, obs, partner_role):
        """Returns a list of sets, where each set contains allowed die values for an open slot."""
        slots = []
        modules = obs.get('publicState', {}).get('modules', [])
        for m in modules:
            for pos in m.get('positions', []):
                # Is it empty?
                if not pos.get('placedDie') and not pos.get('isComplete'):
                    # Is partner allowed?
                    if partner_role in pos.get('permittedRoles', []):
                        allowed = set(pos.get('allowedDieValues', []))
                        slots.append(allowed)
        return slots

    def _simulate_board_after_action(self, partner_slots, action, obs):
        """
        Returns what 'partner_slots' would look like after 'action' is taken.
        Basically removes the slot used by 'action' from the list.
        """
        # 1. Identify which slot 'action' uses
        # This relies on matching the object references or IDs usually, 
        # but here we might need to match by Module Name + Index logic or simple value matching.
        
        # Shortcut: Since we don't have unique Slot IDs in the simplified JSON, 
        # we try to find a "Best Match" slot in the partner list and remove it.
        
        # If action is Coffee/Reroll, board doesn't change for placement slots
        atype = action.get('$type', '')
        if "PlaceDieAction" not in atype:
            return partner_slots

        # Get details of target
        target_pos = action.get('position', {})
        target_module = target_pos.get('module', {}).get('name')
        target_allowed = set(target_pos.get('allowedDieValues', []))
        
        # Filter
        new_slots = list(partner_slots) # Copy
        
        # Try to remove ONE matching slot
        # A match occurs if the slot in 'partner_slots' looks exactly like the one we are taking.
        # Note: If I am Pilot, and I take a Pilot-Only slot, it wasn't in 'partner_slots' (Copilot) anyway.
        # We only need to remove it if it was a SHARED slot.
        
        # So, we check if the action's position allowed the partner role.
        permitted = target_pos.get('permittedRoles', [])
        my_role = obs.get('playersState', {}).get('role')
        partner_role = "Copilot" if my_role == "Pilot" else "Pilot"
        
        if partner_role in permitted:
            # It was a shared slot. Find it in new_slots and remove it.
            for i, slot_set in enumerate(new_slots):
                # Exact match of constraints usually implies same slot
                if slot_set == target_allowed: 
                    new_slots.pop(i)
                    break
        
        return new_slots

class HeuristicStrategy(Strategy):
    name = "heuristic"

    def select_action(self, valid_actions: list[dict], observation: dict, belief_tracker) -> int:
        best_idx = 0
        best_score = -float('inf')

        # Pre-calculate state variables once
        state = self._parse_state(observation)
        
        scored_actions = []
        for i, action in enumerate(valid_actions):
            score = self._score_single_action(state, action)
            scored_actions.append((i, action, score))
            
            if score > best_score:
                best_score = score
                best_idx = i
                
        # Print all actions with their scores
        # print("HeuristicStrategy action scores:")
        # for idx, action, score in scored_actions:
        #     desc = self._get_action_desc(action)
        #     print(f"  [{idx}] {desc:40s} -> {score:6.2f}")
        
        return best_idx

    def _parse_state(self, obs):
        """Extracts relevant state variables into a clean dictionary."""
        pub = obs.get('publicState', {})
        track = pub.get('approachTrack', {})
        my_role = obs.get('playersState', {}).get('role', '')
        modules = obs.get('publicState', {}).get('modules', [])
        axis_tilt_module = next((m for m in modules if m.get('name') in ("Axis Tilt", "Tilt", "Ailerons")), None)
        
        # Logic to find partner's die on Axis Tilt
        
        return {
            'altitude': int(pub.get('altitude', 0)),
            'axis_tilt': int(pub.get('axisTilt', 0)),
            'coffee': int(pub.get('coffeeTokens', 0)),
            'current_pos': int(track.get('approachIndex', 0)),
            'planes': track.get('planesOnApproach', []),
            'track_length': int(track.get('trackLength', 0)),
            'my_role': my_role,
            'mandatory_modules': ["Axis Tilt", "Engine"],
            'axis_tilt_module': axis_tilt_module,
            'modules': modules
        }

    def _score_single_action(self, state, action) -> float:
        """
        Master scoring function. Returns a value between -5 (Very Bad) and +5 (Very Good).
        """
        # 1. Identify Action Type
        action_type = action.get('$type', '')        
        if "placeDie" in action_type:
            return self._score_placement(state, action)
        elif "useCoffee" in action_type:
            return self._score_coffee(state, action)
        elif "UseRerollAction" in action_type:
            return -5.0 # Slight penalty, prefer playing dice
        
        return 0.0

    def _score_coffee(self, state, action) -> float:
        """Scores the value of using coffee in the current state.
            This is determined by the value of the dice currently being used,
            if it is to by either incremented or decremented"""
        
        # Extract action information
        coffee_die = action.get('dieToModify', {})
        die_value = coffee_die.get('value', 0)
        effect = action.get('effect', '')
        new_value = die_value + (1 if effect == "Increase" else -1 if effect == "Decrease" else 0)
        
        # Extract state information
        modules = state.get('modules', [])
        
        # Score the placement of the new die value
        # Score of the new die is equal to the maximum score possible for placing that die
        max_score = -float('inf')
        for module in modules:
            module_name = module.get('name', '')
            # print("DEBUG: Scoring coffee action. Original die:", die_value, "Effect:", effect, "New die:", new_value, "Module:", module_name)
            score = self._score_placement(state, die_value=new_value, module_name=module_name)
            if score > max_score:
                max_score = score
        
        print(f"[Heuristic] Coffee Action on die {die_value} to {new_value}: Score {max_score:.2f}")
        
        return max_score
    
 
    def _score_placement(self, state, action = None, die_value = 0, module_name = '') -> float:
        score = 0.0
        
        if action is not None:
            # Extract Action Details
            module_name = _get_module_name(action)
            die_value = action.get('die', {}).get('value', 0)
        
        # --- RULE 1: MANDATORY MODULE BONUS ---
        # "Mandatory modules should have a bonus to reflect how they should be prioritized"
        if module_name in state['mandatory_modules']:
            score += 1.0

        # --- MODULE SPECIFIC SCORING ---
        if module_name == "Axis Tilt":
            score += self._score_axis(die_value, state)
        elif module_name == "Engine":
            score += self._score_engine(die_value, state)
        elif module_name == "Radio":
            score += self._score_radio(die_value, state)
        elif module_name == "Concentration":
            score += self._score_concentration(state)
        elif module_name == "Brakes":
            score += self._score_brakes(state)
        elif module_name == "Landing Gear" or module_name == "Flaps":
            score += 1.0 # Good to progress these, but not a priority until later
            
        print(f"[Heuristic] Placement Action on {module_name} with die {die_value}: Score {score:.2f}")

        return score

    # --- SPECIFIC HEURISTICS ---

    def _score_axis(self, die_val, state):
        
        # Determine if other player's die is placed on Axis Tilt
        partner_val = 3.5  # Default neutral, presumed statistical average
        module = state.get('axis_tilt_module', [])
        positions = module.get('positions', [])
        for pos in positions:
            placed_die = pos.get('placedDie')
            if placed_die:
                die_role = placed_die.get('role', '')
                if die_role != state['my_role']:  # Partner's die
                    # print("[Heuristic] Detected partner's die on Axis Tilt:", placed_die)
                    partner_val = placed_die.get('value', 3.5)
                    break
        
        tilt = state['axis_tilt']
        role = state['my_role']
        altitude = state['altitude']
        
        # --- CRITICAL: Final Round Logic ---
        # When landing (altitude will be 0 after this round), we MUST be level (tilt == 0)
        # This is a hard constraint that should override normal scoring
        if altitude == 0:  # Next round will be landing
            # Calculate what the tilt will be AFTER both dice are placed
            if role == "Copilot":
                final_tilt = tilt + partner_val - die_val
            else:
                final_tilt = tilt + die_val - partner_val
            
            # Score heavily based on whether we'll be level
            if final_tilt == 0:  # Will be level (accounting for floating point)
                return 10.0  # MASSIVE bonus for achieving level flight on landing
            else:
                # Penalize proportional to how far from level we'll be
                return -10.0 * abs(final_tilt)
        
        if role == "Copilot":
            ideal_val = partner_val - tilt
        else:
            ideal_val = tilt + partner_val
        
        dist = abs(die_val - ideal_val)
        score = 5.0 - (dist * 2.0)

        return max(-5.0, min(5.0, score))

    def _score_engine(self, die_val, state):
        """
        Rule: Place higher value dice when dist_to_runway > altitude.
        Incentivize being closer to runway than ground.
        CRITICAL: Heavily penalize any move that would collide with a plane.
        """
        alt = state['altitude']
        # Distance calculation: (TrackLength - 1) - CurrentIndex
        # e.g. Length 7, Index 0 -> Dist 6. 
        dist_to_runway = (state['track_length'] - 1) - state['current_pos']
        # print(f"[Engine] Altitude: {alt}, Dist to Runway: {dist_to_runway}, Die: {die_val}")
        score = 0.0
        
        # If at end of runway, play the lowest possible dice values
        if dist_to_runway <= 1:
            # print("[Engine] At runway end, prioritizing low die values.")
            score = 7 - die_val * 2
            return score
        
        # Check for potential collision
        # If planes exist in the current index, play only the lowest values
        # If planes exist in the next index, play only low and medium values
        planes = state['planes']
        current_pos = state['current_pos']
        if planes[current_pos] > 0:
            if die_val >= 4:
                score -= 5.0  # Severe penalty for high die risking collision
        elif current_pos + 1 < len(planes) and planes[current_pos + 1] > 0:
            if die_val >= 5:
                score -= 3.0  # Moderate penalty for very high die risking collision
        
        if dist_to_runway > alt:
            # We are lagging behind. Need speed.
            if die_val >= 4: score += 3.0
            elif die_val <= 2: score -= 2.0
        elif dist_to_runway < alt:
            # We are too fast/high? Usually engines allow 0,1,2 movement.
            # If we are close to runway but high up, we might want to slow down?
            # The rule specifically emphasizes the dist > alt case.
            if die_val <= 3: score += 1.0
        else:
            # Balanced
            score += 1.0

        return score

    def _score_radio(self, die_val, state):
        """
        Rule: Important to clear planes, especially closest ones.
        """
        planes = state['planes']
        current_pos = state['current_pos']
        
        # Radio clears plane at Current + DieValue
        target_idx = current_pos + die_val - 1
        
        # Check bounds, corrects to final index if overshoot
        if target_idx >= len(planes):
            target_idx = len(planes) - 1
            
        plane_count = planes[target_idx]
        
        if plane_count > 0:
            # Base score for clearing
            score = 3.0
            
            # Proximity bonus: Closer (smaller die val) is better
            # Scale: Die 1 -> +2.0, Die 6 -> +0.0
            proximity_bonus = max(0, (3 - die_val)) 
            score += proximity_bonus
            return score
        else:
            return -3.0 # Waste of a die

    def _score_concentration(self, state):
        """
        Rule: Generating coffee tokens has diminishing returns past the first.
        """
        current_coffee = state['coffee']
        
        if current_coffee == 0:
            return 1.0 # Good idea
        elif current_coffee == 1:
            return 0.5 # Okay, but maybe do something else
        else:
            return -2.0 # Hoarding is bad

    def _score_brakes(self, state):
        """
        Rule: brakes are more valuable the closer we are to landing.
        Because they must be completed in a specific order, they should be prioritized
        as we approach landing to ensure they are done in time.
        """
        altitude = state['altitude']
        
        if altitude <= 4:
            return 5.0  # Very high priority when very close to landing
        elif altitude <= 6:
            return 3.0  # Moderate priority when approaching landing
        else:
            return 1.5  # Low priority when far from landing
    
    def _get_action_desc(self, action):
        atype = action.get('$type', '')
        if "placeDie" in atype:
            mod = action.get('position', {}).get('module', {})
            val = action.get('die', {}).get('value', 0)
            return f"Place {val} on {mod}"
        elif "useCoffee" in atype:
            eff = action.get('effect', 'Unknown')
            die_val = action.get('dieToModify', {}).get('value', 0)
            return f"Coffee {eff} die {die_val} to {die_val + (1 if eff == 'Increase' else -1 if eff == 'Decrease' else 0)}"
        elif "UseRerollAction" in atype:
            die_val = action.get('dieToModify', {}).get('value', 0)
            return f"Reroll die {die_val}"
        return atype or "UnknownAction"

class StrategyFactory:
    _registry = {
        RandomStrategy.name: RandomStrategy,
        EntropyStrategy.name: EntropyStrategy,
        HeuristicStrategy.name: HeuristicStrategy,
    }

    @classmethod
    def names(cls) -> list[str]:
        return sorted(cls._registry.keys())

    @classmethod
    def create(cls, name: str) -> Strategy:
        key = (name or "").lower()
        if key not in cls._registry:
            raise ValueError(f"Unknown strategy '{name}'. Available: {', '.join(cls.names())}")
        return cls._registry[key]()