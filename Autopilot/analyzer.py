class GameResult:
    def __init__(self, run_id, strategy, outcome, cause, final_altitude, reward):
        self.run_id = run_id
        self.strategy = strategy
        self.outcome = outcome
        self.cause = cause
        self.final_altitude = final_altitude
        self.reward = reward

    def to_dict(self):
        return {
            "Run ID": self.run_id,
            "Strategy": self.strategy,
            "Outcome": self.outcome,
            "Cause": self.cause,
            "Final Altitude": self.final_altitude,
            "Reward": self.reward
        }

class SimulationAnalyzer:
    @staticmethod
    def analyze_end_state(public_state, reward):
        """
        Inspects the final public state to determine the exact cause of game end.
        Returns (Outcome, Cause) tuple.
        """
        # 1. Parse State
        alt = public_state.get('altitude', 0)
        axis = public_state.get('axisTilt', 0)
        track = public_state.get('approachTrack', {})
        idx = track.get('approachIndex', 0)
        planes = track.get('planesOnApproach', [])
        
        landing_speed = public_state.get('landingSpeed') 
        red_brake = public_state.get('redBrakeMarker', 0)
        
        # 2. Determine Outcome
        if reward > 0:
            return "WIN", "Successful Landing"
        
        # 3. Determine Loss Cause
        # Priority 1: Instant Death conditions
        if alt < 0:
            return "LOSS", "Crash: Altitude <0"
        
        if abs(axis) > 2:
            return "LOSS", "Crash: Axis Tilt"
        
        # Check for collision (plane at or before current index)
        # Note: The simulator usually handles this, but we infer from state
        if any(p > 0 for p in planes[:max(0, idx)]):
             return "LOSS", "Crash: Collision"
            
        trackLength = track.get("trackLength", 0)
        ApproachIndex = track.get("approachIndex", 0)
        isBeyondRunway = trackLength - ApproachIndex - 1 < 0
        if isBeyondRunway:
            return "LOSS", "Crash: Overshot Runway"

        # Priority 2: Final Round Failure conditions
        if alt == 0:
            # We reached the ground, but something was wrong
            if axis != 0:
                return "LOSS", "Landing: Tilted"
            
            # Check Speed
            if landing_speed is not None and red_brake is not None:
                if landing_speed >= red_brake:
                    return "LOSS", "Landing: Too Fast (Brakes)"
            
            # Check Runway Position
            track_len = track.get('trackLength', 7)
            if idx < track_len - 1:
                return "LOSS", "Landing: Short of Runway"
            
            # Check Mandatory Modules (Modules not full)
            modules = public_state.get('modules', [])
            for m in modules:
                if m.get('mandatory'):
                    for p in m.get('positions', []):
                        if not p.get('occupied', False) and not p.get('placedDie'):
                             # Note: JSON structure might vary, strictly this infers
                             # from the fact we lost despite alt==0
                             pass

        return "LOSS", "Unknown"
      
    @staticmethod
    def save_summary(results, summary_filename):
      """
        Save results summary to a log file with the same name as CSV.
        results: list of GameResult objects
        summary_filename: base filename (without extension)
        """
      log_path = f"logs/{summary_filename}.txt"
        
      with open(log_path, "w", encoding="utf-8") as f:
          f.write(f"SIMULATION SUMMARY - {summary_filename}\n")
          f.write("=" * 60 + "\n\n")
          
          wins = sum(1 for r in results if r.outcome == "WIN")
          losses = len(results) - wins
          win_rate = (wins / len(results) * 100) if results else 0
          
          f.write(f"Total Runs: {len(results)}\n")
          f.write(f"Wins: {wins}\n")
          f.write(f"Losses: {losses}\n")
          f.write(f"Win Rate: {win_rate:.1f}%\n")
          f.write(f"Average Reward: {sum(r.reward for r in results) / len(results):.2f}\n")
          f.write("-" * 60 + "\n\n")
          
          for result in results:
              f.write(f"{result.to_dict()}\n")
      
      print(f"Summary saved to {log_path}")