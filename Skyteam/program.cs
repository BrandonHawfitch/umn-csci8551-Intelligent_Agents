using Microsoft.AspNetCore.Builder;
using Microsoft.AspNetCore.Http;
using Microsoft.Extensions.DependencyInjection;
using SkyTeam;
using System.Text.Json;
using System.Text.Json.Serialization;

var builder = WebApplication.CreateBuilder(args);

// Add simulation service as a Singleton (so state persists between requests)
builder.Services.AddSingleton<GameSimulator>();

// Configure JSON to handle cycles (circular references between Module <-> Position)
// and enums as strings for readability in Python.
builder.Services.Configure<Microsoft.AspNetCore.Http.Json.JsonOptions>(options =>
{
    options.SerializerOptions.ReferenceHandler = ReferenceHandler.IgnoreCycles;
    options.SerializerOptions.Converters.Add(new JsonStringEnumConverter());
    options.SerializerOptions.Converters.Add(new PositionJsonConverter());
    options.SerializerOptions.IncludeFields = true;
});

var app = builder.Build();

app.MapGet("/", () => "Sky Team Simulator API is Running. Use /reset or /step.");

// 1. RESET Endpoint
app.MapPost("/reset", (GameSimulator sim) =>
{
    var observation = sim.Reset();
    return Results.Ok(observation);
});

// 2. STEP Endpoint
// We accept an index (integer) representing which 'ValidAction' to take.
// This is much easier for Python than constructing a complex C# Action object.
app.MapPost("/step", (int actionIndex, GameSimulator sim) =>
{
    // Re-generate valid actions to map the index to the actual Action object
    var validActions = sim.GetValidActions();
    
    if (actionIndex < 0 || actionIndex >= validActions.Count)
    {
        return Results.BadRequest("Invalid Action Index");
    }

    var actionToTake = validActions[actionIndex];

    try 
    {
        var result = sim.Step(actionToTake);
        return Results.Ok(result);
    }
    catch (Exception ex)
    {
        return Results.Problem(ex.Message);
    }
});

app.Run();