#pragma once

#include "CoreMinimal.h"
#include "Subsystems/WorldSubsystem.h"
#include "FactoryMission.generated.h"

class USoundBase;

/**
 * Things that are in the level but not built yet (upgrades for later). An actor tagged "Bloqueado" plus a
 * group tag (e.g. "Despacho1", "Camion2") is hidden, without collision and idle in play, and every system
 * ignores it (belts, trucks, buttons, events). An actor tagged "Relleno" plus the group fills its place
 * meanwhile (boxes, a container...). Unlock(Group) builds the group: its locked actors come alive and its
 * filler goes away.
 */
UCLASS()
class FACTORYCTYCORUNTIME_API UFactoryUnlockSubsystem : public UWorldSubsystem
{
    GENERATED_BODY()
public:
    static const FName LockedTag;
    static const FName FillerTag;
    /** Whether an actor is waiting to be built. */
    static bool IsLocked(const AActor* Actor);
    /** Builds a group: its locked actors come alive and its filler goes. Returns how many actors changed. */
    UFUNCTION(BlueprintCallable, Category="Unlocks") int32 Unlock(FName Group);
    UFUNCTION(BlueprintPure, Category="Unlocks", meta=(WorldContext="Context")) static UFactoryUnlockSubsystem* Get(const UObject* Context);
    virtual void OnWorldBeginPlay(UWorld& InWorld) override;
};

/**
 * The current mission: deliver Goal packages. A package counts as delivered when the truck carrying it
 * drives through the barrier (or off the end of its line when there is none). Reaching the goal plays a
 * sound and the HUD shows a notice; the info panel (key I) shows the progress.
 */
UCLASS()
class FACTORYCTYCORUNTIME_API UFactoryMissionSubsystem : public UWorldSubsystem
{
    GENERATED_BODY()
public:
    UPROPERTY(Category="Mission", VisibleAnywhere, BlueprintReadOnly) int32 Delivered = 0;
    UPROPERTY(Category="Mission", EditAnywhere, BlueprintReadOnly) int32 Goal = 20;
    UPROPERTY(Category="Mission", VisibleAnywhere, BlueprintReadOnly) bool bCompleted = false;
    /** World time when the goal was reached (the HUD shows its notice for a while). */
    UPROPERTY(Category="Mission", VisibleAnywhere, BlueprintReadOnly) float CompletedAt = -1.0f;
    UFUNCTION(BlueprintCallable, Category="Mission") void AddDelivered(int32 Packages);
    /** The mission of Context's world. */
    UFUNCTION(BlueprintPure, Category="Mission", meta=(WorldContext="Context")) static UFactoryMissionSubsystem* Get(const UObject* Context);
private:
    UPROPERTY(Transient) TObjectPtr<USoundBase> CompleteSound;
};
