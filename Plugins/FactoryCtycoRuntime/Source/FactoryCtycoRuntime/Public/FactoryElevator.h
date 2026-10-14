#pragma once

#include "CoreMinimal.h"
#include "GameFramework/Actor.h"
#include "FactoryElevator.generated.h"

class APawn;
class UAudioComponent;
class USoundBase;
class UStaticMeshComponent;
class UTextRenderComponent;

/**
 * Elevator stop over a shaft sunk under the floor. The cabin and its sliding doors stay at their floor;
 * only the floor inside (Platform) moves, with the character on it. The doors are shut by default and
 * slide open when the character comes near (DoorNearRadius), shutting again when they walk away; they
 * shut before a ride and open when it arrives. Standing in the cabin, E
 * opens a panel with every floor (all the elevators in the level, lowest first) and whether each one
 * is up or down; picking one (click or its number) rides there: going down the platform sinks into
 * the shaft, going up it rises in the cabin; the screen fades out and the character arrives on the
 * other elevator's platform, which comes up from its shaft (going up) or down from above (going down).
 * E again closes the panel. The floor under each elevator has a hole the size of the shaft
 * (Scripts/floor_holes.py).
 */
UCLASS(Blueprintable)
class FACTORYCTYCORUNTIME_API AFactoryElevator : public AActor
{
    GENERATED_BODY()
public:
    AFactoryElevator();
    /** No longer used for travelling (the panel lists every elevator); kept for older levels. */
    UPROPERTY(Category="Elevator", EditInstanceOnly, BlueprintReadOnly) TObjectPtr<AFactoryElevator> Destination;
    /** Name of this stop, shown on the floors panel. */
    UPROPERTY(Category="Elevator", EditAnywhere, BlueprintReadOnly) FString StopName = TEXT("FÁBRICA");
    /** Where workers walk, in order, on their way into this elevator (relative to it; movable in the viewport).
     *  For rooms the navigation cannot get through (furniture close together); empty: straight to the doors. */
    UPROPERTY(Category="Elevator", EditAnywhere, BlueprintReadOnly, meta=(MakeEditWidget="true")) TArray<FVector> Approach;
    /** How far the platform sinks into the shaft going down (cm). */
    UPROPERTY(Category="Elevator", EditAnywhere, BlueprintReadOnly, meta=(ClampMin="0")) float TravelDepth = 260.0f;
    /** How far the platform rises in the cabin going up (cm). */
    UPROPERTY(Category="Elevator", EditAnywhere, BlueprintReadOnly, meta=(ClampMin="0")) float RiseHeight = 150.0f;
    UPROPERTY(Category="Elevator", EditAnywhere, BlueprintReadOnly, meta=(ClampMin="0.2")) float TravelSeconds = 2.4f;
    /** Fade to black at the end of the ride, and back in at the destination (s). */
    UPROPERTY(Category="Elevator", EditAnywhere, BlueprintReadOnly, meta=(ClampMin="0.05")) float FadeSeconds = 0.3f;
    UPROPERTY(Category="Elevator", EditAnywhere, BlueprintReadOnly, meta=(ClampMin="0.1")) float DoorSeconds = 0.9f;
    /** The doors open while the character is this close to the elevator (cm, from its centre). */
    UPROPERTY(Category="Elevator", EditAnywhere, BlueprintReadOnly, meta=(ClampMin="50")) float DoorNearRadius = 300.0f;
    /** 0 shut .. 1 open. */
    UFUNCTION(BlueprintCallable, Category="Elevator") float GetDoorOpenness() const { return DoorAmount; }
    /** Half the cabin's inside (cm, local X and Y): standing in it shows the prompt and hides the roof. */
    UPROPERTY(Category="Elevator", EditAnywhere, BlueprintReadOnly) FVector2D CabinHalfExtent = FVector2D(110.0f, 145.0f);
    /** Telescopic doors, two panels per side (cm): panel width, half the doorway, and the two planes. */
    UPROPERTY(Category="Elevator|Doors", EditAnywhere, BlueprintReadOnly) float DoorPanelWidth = 57.0f;
    UPROPERTY(Category="Elevator|Doors", EditAnywhere, BlueprintReadOnly) float DoorOpeningHalf = 110.0f;
    UPROPERTY(Category="Elevator|Doors", EditAnywhere, BlueprintReadOnly) float DoorInnerX = 117.0f;
    UPROPERTY(Category="Elevator|Doors", EditAnywhere, BlueprintReadOnly) float DoorOuterX = 122.0f;
    UPROPERTY(Category="Elevator|Sound", EditAnywhere, BlueprintReadOnly) TObjectPtr<USoundBase> MotorSound;
    UPROPERTY(Category="Elevator|Sound", EditAnywhere, BlueprintReadOnly) TObjectPtr<USoundBase> ClunkSound;
    UPROPERTY(Category="Elevator|Sound", EditAnywhere, BlueprintReadOnly) TObjectPtr<USoundBase> DoorSound;

    /** Fixed shaft under the floor. */
    UPROPERTY(Category="Elevator", VisibleAnywhere, BlueprintReadOnly) TObjectPtr<UStaticMeshComponent> Tube;
    /** Cabin walls (fixed, with their collision); the roof and the doors are on it. */
    UPROPERTY(Category="Elevator", VisibleAnywhere, BlueprintReadOnly) TObjectPtr<UStaticMeshComponent> Cabin;
    /** The floor inside, which rides up and down with the character. */
    UPROPERTY(Category="Elevator", VisibleAnywhere, BlueprintReadOnly) TObjectPtr<UStaticMeshComponent> Platform;
    /** Panels that close the cabin walls above their half-height panels (SM_Ascensor2Relleno; fixed, with collision). */
    UPROPERTY(Category="Elevator", VisibleAnywhere, BlueprintReadOnly) TObjectPtr<UStaticMeshComponent> Panels;
    /** Rides up and down with the platform (the rider keeps a roof over the head).
     *  Hidden while the player is inside in the isometric view, so the camera above can see them; in first person it
     *  stays (the camera is inside the cabin). */
    UPROPERTY(Category="Elevator", VisibleAnywhere, BlueprintReadOnly) TObjectPtr<UStaticMeshComponent> Roof;
    /** Right outer, right inner, left outer, left inner (fixed at this floor; they slide open and shut). */
    UPROPERTY(Category="Elevator", VisibleAnywhere, BlueprintReadOnly) TArray<TObjectPtr<UStaticMeshComponent>> Doors;
    UPROPERTY(Category="Elevator", VisibleAnywhere, BlueprintReadOnly) TObjectPtr<UAudioComponent> Motor;
    UPROPERTY(Category="Elevator", VisibleAnywhere, BlueprintReadOnly) TObjectPtr<UTextRenderComponent> Prompt;
    /** The floors panel is open (the HUD draws it). */
    UPROPERTY(Category="Elevator", VisibleInstanceOnly, BlueprintReadOnly) bool bMenuOpen = false;

    /** E in the cabin: opens the floors panel, or closes it. Returns whether it did anything. */
    UFUNCTION(BlueprintCallable, Category="Elevator") bool TryInteract(AActor* User);
    /** Every elevator in the level, lowest first: floor 1, 2, ... */
    UFUNCTION(BlueprintCallable, Category="Elevator") TArray<AFactoryElevator*> GetFloors() const;
    /** This stop's floor number (1 = lowest). */
    UFUNCTION(BlueprintCallable, Category="Elevator") int32 GetFloorNumber() const;
    /** Picks a floor from the open panel (1 = lowest); returns whether a ride started. */
    UFUNCTION(BlueprintCallable, Category="Elevator") bool SelectFloor(int32 Number);
    /** The elevator whose floors panel is open, if any. */
    static AFactoryElevator* FindOpenMenu(const UWorld* World);
    UFUNCTION(BlueprintCallable, Category="Elevator") bool InCabin(const AActor* User) const;
    UFUNCTION(BlueprintCallable, Category="Elevator") bool IsIdle() const { return Phase == EPhase::Idle; }
    virtual void OnConstruction(const FTransform& Transform) override;
    virtual void Tick(float DeltaSeconds) override;
private:
    enum class EPhase : uint8 { Idle, Closing, Departing, Returning, Arriving, Opening };
    EPhase Phase = EPhase::Idle;
    float Elapsed = 0.0f;
    float BumpElapsed = 10.0f;
    bool bFadeStarted = false;
    bool bRiderArmCollision = true;
    bool bGoingUp = false;
    /** Where the platform is (cm below the floor; negative: above) at the start and end of the current move. */
    float FromDepth = 0.0f, ToDepth = 0.0f;
    float DoorAmount = 0.0f;
    float DoorTarget = 0.0f;
    /** Moves the doors toward Target (sound when they start moving); returns whether they are there. */
    bool DriveDoors(float Goal, float DeltaSeconds);
    FVector2D RiderOffset = FVector2D::ZeroVector;
    TWeakObjectPtr<APawn> Rider;
    TWeakObjectPtr<AFactoryElevator> Target;
    void Arrive(APawn* Pawn, FVector2D Offset, bool bArmCollision, bool bUp);
    void Enter(EPhase Next);
    void SetDepth(float Depth);
    void SetDoors(float OpenAlpha);
    void PlaceRider() const;
    void Bump(USoundBase* Sound);
    void Release();
};
