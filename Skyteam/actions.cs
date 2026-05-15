using System.Text.Json.Serialization;

namespace SkyTeam
{
  [JsonDerivedType(typeof(PlaceDieAction), typeDiscriminator: "placeDie")]
  [JsonDerivedType(typeof(UseCoffeeAction), typeDiscriminator: "useCoffee")]
  [JsonDerivedType(typeof(UseRerollAction), typeDiscriminator: "useReroll")]
  public interface IAction
  {
    PlayerRole Role { get; set; }
  }

  public class PlaceDieAction : IAction
  {
    public PlayerRole Role { get; set; }
    public Die Die { get; private set; }
    public Position Position { get; private set; }

    public PlaceDieAction(PlayerRole role, Die die, Position position)
    {
      Role = role;
      Die = die;
      Position = position;
    }
  }

  /// <summary>
  /// UseCoffeeAction: A concrete action of using a coffee token to adjust a die.
  /// </summary>
  public class UseCoffeeAction : IAction
  {
    public PlayerRole Role { get; set; }
    public Die DieToModify { get; set; }
    public CoffeeEffect Effect { get; set; }

    public UseCoffeeAction(PlayerRole role, Die die, CoffeeEffect effect)
    {
      Role = role;
      DieToModify = die;
      Effect = effect;
    }

    public override string ToString()
    {
      return $"{Role} uses coffee to {Effect} die with value {DieToModify.Value}.";
    }
  }

  /// <summary>
  /// UseRerollAction: A concrete action of using a reroll token.
  /// </summary>
  public class UseRerollAction : IAction
  {
    public PlayerRole Role { get; set; }
    public List<Die> DiceToReroll { get; private set; }

    public UseRerollAction(PlayerRole role, List<Die> diceToReroll)
    {
      Role = role;
      DiceToReroll = diceToReroll;
    }
    public override string ToString()
    {
      return $"{Role} uses a reroll token.";
    }
  }
}