namespace SkyTeam
{
  /// <summary>
  /// GameSimulator: The main class that runs the game logic.
  /// Responsible for maintaining game state, processing player actions,
  /// and generating observations for each player.
  /// Effectively the MARL environment.
  /// </summary>
  public class GameSimulator
  {
    public CompleteState CompleteGameState;

    public GameSimulator(int? seed = null)
    {
      CompleteGameState = new CompleteState(
        new BaseGameState(GameTracks.MontrealTrudeauTrack()),
        new Dictionary<PlayerRole, PlayerState>
        {
          { PlayerRole.Pilot, new PlayerState(PlayerRole.Pilot, seed.HasValue ? new Random(seed.Value) : null) },
          { PlayerRole.Copilot, new PlayerState(PlayerRole.Copilot, seed.HasValue ? new Random(seed.Value + 1) : null) }
        },
        PlayerRole.Pilot,
        seed.HasValue ? new Random(seed.Value) : null
      );

      // _Seed = seed.HasValue ? new Random(seed.Value) : new Random();
      // GameState = new BaseGameState(GameTracks.MontrealTrudeauTrack());
      // PilotState = new PlayerState(PlayerRole.Pilot, _Seed);
      // CopilotState = new PlayerState(PlayerRole.Copilot, _Seed);
      // CurrentTurn = PlayerRole.Pilot; // Pilot starts first by default
    }

    /// <summary>
    /// Resets the game to the initial state.
    /// </summary>
    /// <returns>The initial Observation for the starting player</returns>
    public Observation Reset()
    {
      CompleteGameState = new CompleteState(
        new BaseGameState(GameTracks.MontrealTrudeauTrack()),
        new Dictionary<PlayerRole, PlayerState>
        {
          { PlayerRole.Pilot, new PlayerState(PlayerRole.Pilot, CompleteGameState.Seed) },
          { PlayerRole.Copilot, new PlayerState(PlayerRole.Copilot, CompleteGameState.Seed) }
        },
        PlayerRole.Pilot,
        CompleteGameState.Seed ?? new Random()
      );
      // Reset the game state and player states
      // GameState = new BaseGameState(GameTracks.MontrealTrudeauTrack());
      // PilotState = new PlayerState(PlayerRole.Pilot, _Seed);
      // CopilotState = new PlayerState(PlayerRole.Copilot, _Seed);
      // CurrentTurn = PlayerRole.Pilot; // Pilot starts first by default

      // Return the initial observation
      return GetCurrentPlayerObservation();
    }
    
    /// <summary>
    /// Processes a step in the game given the action(s) of a single player.
    /// </summary>
    /// <param name="action"></param>
    /// <returns>An MDP Step result containing the next observation, reward, and done flag</returns>
    public MDPStepResult Step(IAction action)
    {
      // Validate that it's the correct player's turn
      if (action.Role != CompleteGameState.CurrentTurn)
      {
        throw new InvalidOperationException("It's not the player's turn.");
      }

      // Process the action
      if (action is PlaceDieAction placeDieAction)
      {
        // Process placing a die
        var position = placeDieAction.Position;
        var module = position.Module;
        var die = placeDieAction.Die;
        if (!position.PlaceDie(die)) { // Place die in position, throw error if invalid
          throw new InvalidOperationException("Invalid die placement.");
        }
        // Apply module effect
        module!.DiePlaced(CompleteGameState.BaseState, position);

        // if game is won, skip further processing
        if (IsGameWon())
        {
          Console.WriteLine("Game Won!");
          return new MDPStepResult(GetCurrentPlayerObservation(), CalculateReward(), true);
        }

        // Decrease altitude if round is over
        if (IsRoundOver())
        {
          Console.WriteLine("Round Over! Decreasing altitude.");
          CompleteGameState.BaseState.Altitude -=1; // Decrease altitude each round
        }

        // If game is lost, skip further processing
        if (IsGameLost())
        {
          Console.WriteLine("Game Lost!");
          return new MDPStepResult(GetCurrentPlayerObservation(), CalculateReward(), true);
        }

        // Advance turn to next player
        AdvanceTurn();

        // If round is over, roll dice for both players
        if (IsRoundOver())
        {
          Console.WriteLine("Rolling dice for both players.");
          RollDice();
        }
      }
      else if (action is UseCoffeeAction useCoffeeAction)
      {
        // Process using coffee
        var die = useCoffeeAction.DieToModify;
        var effect = useCoffeeAction.Effect;
        CompleteGameState.BaseState.CoffeeTokens -= 1; // Consume a coffee token
        die.Value += effect switch
        {
          CoffeeEffect.Increase => 1,
          CoffeeEffect.Decrease => -1,
          _ => throw new NotImplementedException(),
        };
      }
      else if (action is UseRerollAction useRerollAction)
      {
        // Process rerolling dice
        foreach (var die in useRerollAction.DiceToReroll)
        {
          die.Roll();
        }
      }

      if (GetValidActions().Count == 0)
      {
        Console.WriteLine("[AUTO-ADVANCE] No valid actions available after action. Forcing round advancement.");
        ForceRoundAdvancement();
      }

      // Check if the game is over
      bool isDone = IsGameOver();
      float reward = CalculateReward();

      Observation observation = GetCurrentPlayerObservation();

      return new MDPStepResult(observation, reward, isDone);
    }


    public MDPStepResult PlayAction(PlayerRole role, string moduleName, int dieValue, int positionIndex = 0)
    {
      var module = this.CompleteGameState.BaseState.Modules.First(m => m.Name == moduleName);
      var position = module.Positions[positionIndex];
      var playerState = role == PlayerRole.Pilot ? this.CompleteGameState.PlayerStates[PlayerRole.Pilot] : this.CompleteGameState.PlayerStates[PlayerRole.Copilot];
      var die = playerState.Dice.First(d => d.Value == dieValue && !d.IsUsed);
      var action = new PlaceDieAction(role, die, position);
      return this.Step(action);
    }

    /// <summary>
    /// Creates the observation for the current player.
    /// </summary>
    /// <param name="role"></param>
    public Observation GetCurrentPlayerObservation()
    {
      var gameStateClone = CompleteGameState;
      PlayerState playerState = CompleteGameState.CurrentTurn == PlayerRole.Pilot ? CompleteGameState.PlayerStates[PlayerRole.Pilot] : CompleteGameState.PlayerStates[PlayerRole.Copilot];
      var validActions = GetValidActions();

      return new Observation(gameStateClone.BaseState, playerState, validActions);
    }

    public bool IsRoundOver()
    {
      // Check if all dice for both players are used
      var allUsed = CompleteGameState.PlayerStates[PlayerRole.Pilot].Dice.All(d => d.IsUsed) && CompleteGameState.PlayerStates[PlayerRole.Copilot].Dice.All(d => d.IsUsed);
      return allUsed;
    }

    private void ForceRoundAdvancement()
    {
      // Mark all remaining dice as used to complete the round
      foreach (var playerState in CompleteGameState.PlayerStates.Values)
      {
        foreach (var die in playerState.Dice)
        {
          die.IsUsed = true;
        }
      }

      // Decrement altitude (guarded to prevent going below 0 accidentally)
      if (CompleteGameState.BaseState.Altitude > 0)
      {
        CompleteGameState.BaseState.Altitude -= 1;
        Console.WriteLine($"[AUTO-ADVANCE] Altitude decreased to {CompleteGameState.BaseState.Altitude}");
      }

      if (IsGameWon())
      {
        Console.WriteLine("[AUTO-ADVANCE] Game won after forced round advancement.");
        return;
      }

      // Check if game is lost due to altitude drop
      if (IsGameLost())
      {
        Console.WriteLine("[AUTO-ADVANCE] Game lost after forced round advancement.");
        return;
      }

      // Roll new dice for next round
      RollDice();

      // Set starting player for new round based on altitude
      var altitude = CompleteGameState.BaseState.Altitude;
      CompleteGameState.CurrentTurn = altitude % 2 == 0 ? PlayerRole.Pilot : PlayerRole.Copilot;
      
      Console.WriteLine($"[AUTO-ADVANCE] New round started. Altitude: {altitude}, Starting player: {CompleteGameState.CurrentTurn}");
    }

    /// <summary>
    /// Advances the turn to the next player.
    /// Starting turn at beginning of round is dependent on altitude.
    /// </summary>
    public void AdvanceTurn()
    {
      if (IsRoundOver())
      {
        var altitude = CompleteGameState.BaseState.Altitude;
        // If altitude is even, pilot starts next round; else copilot starts
        CompleteGameState.CurrentTurn = altitude % 2 == 0 ? PlayerRole.Pilot : PlayerRole.Copilot;
        Console.WriteLine($"Altitude: {altitude}, setting starting turn to {CompleteGameState.CurrentTurn}");
        
      } else
      {
        CompleteGameState.CurrentTurn = CompleteGameState.CurrentTurn == PlayerRole.Pilot ? PlayerRole.Copilot : PlayerRole.Pilot;
      }
    }

    /// <summary>
    /// Removes dice from board and rerolls them for all players
    /// </summary>
    public void RollDice()
    {
      CompleteGameState.PlayerStates[PlayerRole.Pilot].RollAllDice();
      CompleteGameState.PlayerStates[PlayerRole.Copilot].RollAllDice();

      // Reset all board positions for the new round
      foreach (var module in CompleteGameState.BaseState.Modules)
      {
        foreach (var position in module.Positions)
        {
          position.PlacedDie = null;
        }
      }
    }

    /// <summary>
    /// Generates a list of valid actions for the current player.
    /// </summary>
    /// <param name="role"></param>
    /// <returns></returns>
    public List<IAction> GetValidActions()
    {
      var validActions = new List<IAction>();

      // Generate PlaceDieActions for each unused die and position it can be placed within

      // Get current player's unused dice
      var playerUnusedDice = GetCurrentPlayerState().GetUsableDice();

      var allModules = CompleteGameState.BaseState.Modules;

      var mandatoryModules = CompleteGameState.BaseState.Modules
        .Where(m => m.Mandatory && m.GetAvailablePositions(CompleteGameState.CurrentTurn, CompleteGameState.BaseState).Count > 0)
        .ToList();
      var searchModules = allModules;

      // Filter out Concentration module if coffee tokens > 3
      if (CompleteGameState.BaseState.CoffeeTokens >= 3)
      {
        allModules = allModules.Where(m => m.Name != "Concentration").ToList();
      }

      // If the number of remaining dice is equal to the number of mandatory module positions,
      // valid actions should contain only the valid combinations of dice that could be placed in those modules
      if (playerUnusedDice.Count == mandatoryModules.Count && mandatoryModules.Count > 0)
      {
        searchModules = mandatoryModules;
      }

      // Iterate through all modules and their positions
      foreach (var module in searchModules)
      {
        var availablePositions = module.GetAvailablePositions(CompleteGameState.CurrentTurn, CompleteGameState.BaseState);
        foreach (var position in availablePositions)
        {
          // Check each die to see if it can be placed in this position
          foreach (var die in playerUnusedDice)
          {
            if (position.AllowedDieValues.Contains(die.Value))
            {
              // Special case: Radio actions only valid if the die value would clear a plane
              if (module.Name == "Radio")
              {
                if (!CompleteGameState.BaseState.ApproachTrack.IsPlaneAtDistance(die.Value))
                {
                  continue; // Skip this action - die value won't clear any plane
                }
              }


              validActions.Add(new PlaceDieAction(CompleteGameState.CurrentTurn, die, position));
            }
          }
        }
      }


      // Generate UseCoffeeAction if player has coffee tokens and unused dice
      if (CompleteGameState.BaseState.CoffeeTokens > 0)
      {
        foreach (var die in playerUnusedDice)
        {
          if (die.Value < 6) // Can increase
          {
            validActions.Add(new UseCoffeeAction(CompleteGameState.CurrentTurn, die, CoffeeEffect.Increase));
          }
          if (die.Value > 1) // Can decrease
          {
            validActions.Add(new UseCoffeeAction(CompleteGameState.CurrentTurn, die, CoffeeEffect.Decrease));
          }
        }
      }

      // Generate UseRerollAction if player has reroll tokens and unused dice
      if (CompleteGameState.BaseState.RerollTokens > 0 && playerUnusedDice.Count > 0)
      {
        // TODO: flush out complete logic
        // For simplicity, only the current player's dice can be rerolled
        // Doing so also rerolls all currently unused dice for that player
        validActions.Add(new UseRerollAction(CompleteGameState.CurrentTurn, playerUnusedDice));
      }

      // If no valid actions and player still has unused dice, this is a deadlock
      if (validActions.Count == 0 && playerUnusedDice.Count > 0)
      {
        Console.WriteLine($"[GetValidActions WARNING] No valid actions but {playerUnusedDice.Count} dice remaining - potential deadlock");
      }

      return validActions;
    }

    private PlayerState GetCurrentPlayerState()
    {
      return CompleteGameState.CurrentTurn == PlayerRole.Pilot ? CompleteGameState.PlayerStates[PlayerRole.Pilot] : CompleteGameState.PlayerStates[PlayerRole.Copilot];
    }

    public bool IsGameOver()
    {
      return IsGameWon() || IsGameLost();
    }

    // ...existing code...
    public bool IsGameLost()
    {
      if (CompleteGameState.BaseState.Altitude < 0)
      {
        Console.WriteLine("[LOSS] Altitude below ground: " + CompleteGameState.BaseState.Altitude);
        return true;
      }
      
      if (CompleteGameState.BaseState.ApproachTrack.PlaneCollision())
      {
        Console.WriteLine("[LOSS] Plane collision on approach");
        return true;
      }
      
      if (CompleteGameState.BaseState.ApproachTrack.IsBeyondRunway())
      {
        Console.WriteLine($"[LOSS] Plane overshot runway (Index: {CompleteGameState.BaseState.ApproachTrack.ApproachIndex}, TrackLength: {CompleteGameState.BaseState.ApproachTrack.TrackLength})");
        return true;
      }
      
      if (CompleteGameState.BaseState.AxisTilt < -2 || CompleteGameState.BaseState.AxisTilt > 2)
      {
        Console.WriteLine($"[LOSS] Axis tilt out of bounds: {CompleteGameState.BaseState.AxisTilt}");
        return true;
      }
      
      if (IsFinalRound() && CompleteGameState.BaseState.LandingSpeed > CompleteGameState.BaseState.RedBrakeMarker)
      {
        Console.WriteLine($"[LOSS] Landing speed too high on final round (Speed: {CompleteGameState.BaseState.LandingSpeed}, Red Brake: {CompleteGameState.BaseState.RedBrakeMarker})");
        return true;
      }

      return false;
    }

    public bool IsGameWon()
    {
      if (!IsFinalRound())
      {
        return false;
      }
      
      if (CompleteGameState.BaseState.AxisTilt != 0)
      {
        Console.WriteLine($"[WIN CHECK FAILED] Axis tilt not level: {CompleteGameState.BaseState.AxisTilt}");
        return false;
      }
      
      if (!CompleteGameState.BaseState.ApproachTrack.IsAtRunway())
      {
        Console.WriteLine($"[WIN CHECK FAILED] Not at runway (Index: {CompleteGameState.BaseState.ApproachTrack.ApproachIndex}, TrackLength: {CompleteGameState.BaseState.ApproachTrack.TrackLength})");
        return false;
      }
      
      if (CompleteGameState.BaseState.LandingSpeed >= CompleteGameState.BaseState.RedBrakeMarker)
      {
        Console.WriteLine($"[WIN CHECK FAILED] Landing speed too high (Speed: {CompleteGameState.BaseState.LandingSpeed}, Red Brake: {CompleteGameState.BaseState.RedBrakeMarker})");
        return false;
      }
      
      var mandatoryModules = CompleteGameState.BaseState.Modules.Where(m => m.Mandatory).ToList();
      foreach (var module in mandatoryModules)
      {
        if (!module.Positions.All(p => p.IsOccupied()))
        {
          Console.WriteLine($"[WIN CHECK FAILED] Mandatory module '{module.Name}' not fully occupied");
          return false;
        }
      }
      
      var deployModules = CompleteGameState.BaseState.Modules.Where(m => m.Name == "Landing Gear" || m.Name == "Flaps").ToList();
      foreach (var module in deployModules)
      {
        if (!module.Positions.All(p => p.IsComplete))
        {
          Console.WriteLine($"[WIN CHECK FAILED] Deploy module '{module.Name}' not complete");
          return false;
        }
      }
      
      Console.WriteLine("[WIN] All conditions met!");
      return true;
    }

    public bool IsFinalRound()
    {
      return CompleteGameState.BaseState.Altitude == 0;
    }
    
    private float CalculateReward()
    {
      if (IsGameWon())
      {
        return 1.0f; // Reward for winning
      }
      if (IsGameLost())
      {
        return -1.0f; // Penalty for losing
      }
      return 0.0f;
    }
  }
}