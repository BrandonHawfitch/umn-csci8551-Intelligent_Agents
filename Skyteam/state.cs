namespace SkyTeam
{
  /// <summary>
  /// CompleteState: The full game state, including both public and private information.
  /// </summary>
  public class CompleteState
  {
    public BaseGameState BaseState { get; set; }
    public Dictionary<PlayerRole, PlayerState> PlayerStates { get; set; }
    public PlayerRole CurrentTurn { get; set; }
    public Random Seed { get; set; }

    public CompleteState(BaseGameState baseState, Dictionary<PlayerRole, PlayerState> playerStates, PlayerRole currentTurn, Random? seed = null)
    {
      BaseState = baseState;
      PlayerStates = playerStates;
      CurrentTurn = currentTurn;
      Seed = seed ?? new Random();
    }

    public CompleteState Clone()
    {
      return new CompleteState(
        BaseState.Clone(),
        PlayerStates.ToDictionary(
          kvp => kvp.Key,
          kvp => kvp.Value.Clone()
        ),
        CurrentTurn,
        Seed
      );
    }
  }


  /// <summary>
  /// PlayerState: Private information known only to one player (and the simulator).
  /// </summary>
  public class PlayerState
  {
    public PlayerRole Role { get; set; }
    public List<Die> Dice { get; set; }
    private Random _Seed;

    public PlayerState(PlayerRole role, Random? seed = null)
    {
      Role = role;
      _Seed = seed ?? new Random();
      // Creates 4 new dice for the player
      Dice = Enumerable.Range(0, 4).Select(_ => new Die(role, _Seed)).ToList();
    }

    public void RollAllDice()
    {
      foreach (var die in Dice)
      {
        die.Roll();
        die.IsUsed = false;
      }
    }

    public List<Die> GetUsableDice()
    {
      return Dice.Where(d => !d.IsUsed).ToList();
    }

    public PlayerState Clone()
    {
      return new PlayerState(Role)
      {
        Dice = Dice.Select(d => d.Clone()).ToList(),
        _Seed = this._Seed
      };
    }
  }

  /// <summary>
  ///  Represents the state of the base game.
  /// </summary>
  public class BaseGameState
  {
    public int Altitude { get; set; } = 6; // Altitude levels above ground, thousands of feet
    public int AxisTilt { get; set; } = 0; // -2 to +2 range 
    public int CoffeeTokens { get; set; } = 0; // Number of coffee tokens available
    public int RerollTokens { get; set; } = 0; // Number of reroll tokens available
    public int LandingSpeed { get; set; } // Speed of landing

    public float BlueAeroMarker { get; set; } = 4.5f; // Position of the blue aerodynamic marker, lower speed threshold
    public float OrangeAeroMarker { get; set; } = 8.5f; // Position of the orange aerodynamic marker, higher speed threshold
    public float RedBrakeMarker { get; set; } = 0.5f; // Position of the red brake marker, maximum speed threshold

    public TrackState ApproachTrack { get; set; }

    public List<Module> Modules { get; set; }

    public BaseGameState(TrackState approachTrack)
    {
      ApproachTrack = approachTrack;
      Modules = GameModules.GetBaseModules();
    }

    public Module GetModuleByName(string moduleName)
    {
      return Modules.First(m => m.Name == moduleName);
    }

    public BaseGameState Clone()
    {
      var clonedState = new BaseGameState(ApproachTrack.Clone())
      {
        Altitude = this.Altitude,
        AxisTilt = this.AxisTilt,
        CoffeeTokens = this.CoffeeTokens,
        RerollTokens = this.RerollTokens,
        BlueAeroMarker = this.BlueAeroMarker,
        OrangeAeroMarker = this.OrangeAeroMarker,
        RedBrakeMarker = this.RedBrakeMarker,
        Modules = this.Modules.Select(m => m.Clone()).ToList()
      };

      return clonedState;
    }
  }
}