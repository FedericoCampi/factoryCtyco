#pragma once

#include "CoreMinimal.h"
#include "GameFramework/Actor.h"
#include "Subsystems/WorldSubsystem.h"
#include "FactorySceneZone.generated.h"

class UBoxComponent;
class APlayerController;
class UPrimitiveComponent;

/**
 * One scene of the level (the factory, the dispatch with the docks, the lab, the staff building): a box around it. In
 * play only the scene the player's character is in is drawn for the player's camera (first person and isometric);
 * the rest stays there and keeps working (trucks, belts, furnace), it is just not seen (UFactorySceneSubsystem).
 * An actor belongs to the smallest zone around its place (moving trucks and characters: where they are now). Not in
 * any zone, or bigger than its zone (outdoor floors, the horizon), or a light, the sky or a volume: always seen.
 * Tags on an actor: "SiempreVisible" keeps it always seen; "Escena:<name>" puts it in that scene; "Techo" (roofs and
 * the walls raised up to them) is only seen in first person: the isometric camera looks in from above.
 */
UCLASS(Blueprintable)
class FACTORYCTYCORUNTIME_API AFactorySceneZone : public AActor
{
    GENERATED_BODY()
public:
    AFactorySceneZone();
    UPROPERTY(Category="Scene", VisibleAnywhere, BlueprintReadOnly) TObjectPtr<UBoxComponent> Box;
    /** The scene's name (zones with the same name are one scene). */
    UPROPERTY(Category="Scene", EditAnywhere, BlueprintReadOnly) FName Scene = TEXT("Escena");
    /** Whether Point is inside the box grown by Margin (cm) on every side. */
    bool Contains(const FVector& Point, float Margin = 0.0f) const;
    /** Half size of the box in the world (cm). */
    FVector Extent() const;
    /** The scene Actor belongs to (see the class comment), or None: always seen. Works in the editor too. */
    UFUNCTION(Category="Scene", BlueprintCallable) static FName SceneOf(const AActor* Actor);
    static const FName AlwaysTag;
    static const FName RoofTag;
    /** The scene system of Context's world (in play), for scripts and tests. */
    UFUNCTION(Category="Scene", BlueprintCallable) static class UFactorySceneSubsystem* GetSceneSubsystem(const AActor* Context);
};

/** Hides, for the player's camera only, the scenes the player's character is not in (see AFactorySceneZone). */
UCLASS()
class FACTORYCTYCORUNTIME_API UFactorySceneSubsystem : public UTickableWorldSubsystem
{
    GENERATED_BODY()
public:
    virtual void Tick(float DeltaTime) override;
    virtual TStatId GetStatId() const override;
    virtual bool DoesSupportWorldType(const EWorldType::Type WorldType) const override;
    /** Scenes drawn now (empty: all). */
    UFUNCTION(Category="Scene", BlueprintCallable) TArray<FName> GetVisibleScenes() const { return Visible.Array(); }
    /** Actors and parts hidden from the player's camera now. */
    UFUNCTION(Category="Scene", BlueprintCallable) int32 GetHiddenCount() const { return Hidden.Num() + HiddenParts.Num(); }
    /** Whether Actor is hidden from the player's camera now. */
    UFUNCTION(Category="Scene", BlueprintCallable) bool IsHidden(const AActor* Actor) const;
    /** Near the edge of another scene (cm) both are drawn, so it does not pop in at the door. */
    float NeighborMargin = 300.0f;
private:
    void Update();
    float Clock = 0.0f;
    TSet<FName> Visible;
    /** The scenes the character was last inside (kept while it is between scenes). */
    TSet<FName> LastInside;
    TMap<TWeakObjectPtr<AActor>, FName> Known;
    TArray<TWeakObjectPtr<AActor>> Hidden;
    TArray<TWeakObjectPtr<UPrimitiveComponent>> HiddenParts;
    TWeakObjectPtr<APlayerController> Player;
};
