using UnrealBuildTool;
public class FactoryCtycoRuntime : ModuleRules
{
    public FactoryCtycoRuntime(ReadOnlyTargetRules Target) : base(Target)
    {
        PCHUsage = PCHUsageMode.UseExplicitOrSharedPCHs;
        PublicDependencyModuleNames.AddRange(new[] { "Core", "CoreUObject", "Engine", "InputCore", "RenderCore", "NavigationSystem", "DeveloperSettings" });
    }
}
