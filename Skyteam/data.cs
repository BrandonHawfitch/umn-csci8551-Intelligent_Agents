using System.Text.Json;
using System.Text.Json.Serialization;

namespace SkyTeam
{
  public enum PlayerRole
  {
    Pilot,
    Copilot
  }

  public enum CoffeeEffect
  {
    Increase,
    Decrease
  }

  /// <summary>
  /// Represents the result of a single step in the simulation.
  /// This is what the environment returns to the agent after each action.
  /// </summary>
  public class MDPStepResult
  {
    public Observation Observation { get; set; }
    public float Reward { get; set; }
    public bool IsDone { get; set; }

    public MDPStepResult(Observation observation, float reward, bool isDone)
    {
      Observation = observation;
      Reward = reward;
      IsDone = isDone;
    }
  }

  /// <summary>
  /// Represents a die used in the game.
  /// </summary>
  public class Die
  {
    private Random _Seed;
    public int Value { get; set; }
    public bool IsUsed { get; set; }
    public PlayerRole OwnerRole { get; set; }

    public Die(PlayerRole OwnerRole, Random? seed = null)
    {
      this.OwnerRole = OwnerRole;
      _Seed = seed ?? new Random();
      IsUsed = false;
      Roll();
    }

    public void Roll()
    {
      Value = _Seed.Next(1, 7); // Assuming a 6-sided die
    }

    public Die Clone()
    {
      return new Die(this.OwnerRole)
      {
        Value = this.Value,
        IsUsed = this.IsUsed,
        _Seed = this._Seed
      };
    }
  }

  public class SerializablePosition
  {
    public Die? PlacedDie { get; set; }
    public List<PlayerRole> PermittedRoles { get; set; }
    public List<int> AllowedDieValues { get; set; }
    public string Module { get; set; }
    public bool IsComplete { get; set; }

    public SerializablePosition(Position position)
    {
      PlacedDie = position.PlacedDie;
      PermittedRoles = position.PermittedRoles;
      AllowedDieValues = position.AllowedDieValues;
      Module = position.Module!.Name;
      IsComplete = position.IsComplete;
    }
  }

  /// <summary>
  /// Custom Converter to serialize Position objects as SerializablePosition
  /// </summary>
  public class PositionJsonConverter : JsonConverter<Position>
  {
      public override Position Read(ref Utf8JsonReader reader, Type typeToConvert, JsonSerializerOptions options)
      {
          // Deserialization is not supported/required for this context as actions are generated server-side.
          throw new NotSupportedException();
      }

      public override void Write(Utf8JsonWriter writer, Position value, JsonSerializerOptions options)
      {
          // Convert the actual Position object into the flattened SerializablePosition DTO
          var serializable = new SerializablePosition(value);
          // Serialize the DTO instead
          JsonSerializer.Serialize(writer, serializable, options);
      }
  }

  /// <summary>
  /// Represents a position on the game board where a die can be placed.
  /// </summary>
  public class Position
  {
    public Die? PlacedDie { get; set; }
    public List<PlayerRole> PermittedRoles { get; set; }
    public List<int> AllowedDieValues { get; set; }
    public Module? Module { get; set; }
    public bool IsComplete { get; set; } = false;

    public Position(List<PlayerRole> permittedRoles, List<int> allowedDieValues)
    {
      PermittedRoles = permittedRoles;
      AllowedDieValues = allowedDieValues;
      PlacedDie = null;
    }

    public bool IsOccupied()
    {
      return PlacedDie != null;
    }

    public bool IsValidPlacement(Die die)
    {
      if (IsOccupied())
      {
        return false; // Position already occupied
      }
      if (AllowedDieValues != null && !AllowedDieValues.Contains(die.Value))
      {
        return false; // Die value not allowed in this position
      }
      if (PermittedRoles != null && !PermittedRoles.Contains(die.OwnerRole))
      {
        return false; // Player role not permitted to place die here
      }
      return true;
    }

    /// <summary>
    /// Attempts to place a die in this position,
    /// returns true if the die was successfully placed
    /// </summary>
    public bool PlaceDie(Die die)
    {
      if (!IsValidPlacement(die))
      {
        return false;
      }

      PlacedDie = die;
      die.IsUsed = true;
      return true;
    }

    public Position Clone()
    {
      var clonedPosition = new Position(new List<PlayerRole>(PermittedRoles), new List<int>(AllowedDieValues))
      {
        PlacedDie = this.PlacedDie?.Clone(),
        IsComplete = this.IsComplete,
        Module = this.Module // Module is a reference, it will be cloned at the GameState/Module level
      };
      
      return clonedPosition;
    }
  }
}