#pragma once

#include "CoreMinimal.h"
#include "GameFramework/Actor.h"
#include "FactoryDispatchBelt.generated.h"

class AFactoryBeltButton;
class UMaterialInstanceDynamic;
class UPrimitiveComponent;
class USoundBase;
class UStaticMesh;
class UStaticMeshComponent;
class UTextRenderComponent;

/** How a box on the belt rocks and settles after bumping into something (degrees, cm, per second). */
struct FDispatchBoxMotion
{
    float Tilt = 0.0f, TiltSpeed = 0.0f;     // forward tip, springs back to 0
    float Yaw = 0.0f, YawSpeed = 0.0f;       // turn, springs to RestYaw
    float RestYaw = 0.0f;                    // where it settles; each bump shifts it a little
    float Nudge = 0.0f, NudgeSpeed = 0.0f;   // sideways slide, springs back to 0
    float Phase = 0.0f;                      // for the roller vibration
    bool bMoving = true;
};

/**
 * Belt of a dispatch machine, switched on with E at its panel. While on, boxes come out of the
 * machine at a random free spot across the belt (not in fixed lanes) and ride forward until they
 * reach the far end or a box ahead that overlaps them across, each stopping with its own small gap
 * and turn, so they take up real room and pack the belt loosely, like real boxes; the
 * rollers of the parent machine spin. When no lane has room at the entrance the belt stops by itself
 * and a red sign pops up above it; clicking the sign opens its detail on the HUD. E next to a box
 * takes it (the character carries it); a belt stopped because it was full starts again. Attach it to the machine: the
 * boxes and the sign follow the machine (Start, End and SignLocation are in its space). The panel is
 * its own actor (AFactoryBeltButton, pointing at this belt), so it can be moved anywhere.
 */
UCLASS(Blueprintable)
class FACTORYCTYCORUNTIME_API AFactoryDispatchBelt : public AActor
{
    GENERATED_BODY()
public:
    AFactoryDispatchBelt();
    UPROPERTY(Category="Dispatch Belt", EditAnywhere, BlueprintReadOnly) TObjectPtr<UStaticMesh> BoxMesh;
    /** Boxes with a label (A to D, author_dispatch_box_labels.py): each new box is one of them at random (the label
     *  travels with the box, it is its mesh). Empty: always BoxMesh. */
    UPROPERTY(Category="Dispatch Belt", EditAnywhere, BlueprintReadOnly) TArray<TObjectPtr<UStaticMesh>> BoxVariants;
    /** Where boxes appear, inside the machine. */
    UPROPERTY(Category="Dispatch Belt", EditAnywhere, BlueprintReadOnly, meta=(MakeEditWidget)) FVector Start = FVector(0, -70, 58);
    /** Where the first box stops, at the end of the belt. */
    UPROPERTY(Category="Dispatch Belt", EditAnywhere, BlueprintReadOnly, meta=(MakeEditWidget)) FVector End = FVector(0, 300, 60);
    /** Belt speed, in units of this actor's space per second. */
    UPROPERTY(Category="Dispatch Belt", EditAnywhere, BlueprintReadOnly, meta=(ClampMin="1")) float Speed = 70.0f;
    UPROPERTY(Category="Dispatch Belt", EditAnywhere, BlueprintReadOnly, meta=(ClampMin="0.1")) float SecondsBetweenBoxes = 2.5f;
    /** Room one box takes on the belt, box plus gap (cm), both along and across it. */
    UPROPERTY(Category="Dispatch Belt", EditAnywhere, BlueprintReadOnly, meta=(ClampMin="1")) float BoxSpacing = 44.0f;
    /** From the Start-End line to the inside of the side rails (cm): as many lanes as fit. */
    UPROPERTY(Category="Dispatch Belt", EditAnywhere, BlueprintReadOnly, meta=(ClampMin="1")) float BedHalfWidth = 90.0f;
    /** Each box gets a random turn of up to this many degrees so the load does not look copied. */
    UPROPERTY(Category="Dispatch Belt", EditAnywhere, BlueprintReadOnly, meta=(ClampMin="0")) float MaxYawJitter = 9.0f;
    /** Up to this much extra room (cm) a box leaves to the one ahead when it stops. */
    UPROPERTY(Category="Dispatch Belt", EditAnywhere, BlueprintReadOnly, meta=(ClampMin="0")) float GapJitter = 10.0f;
    /** How hard boxes rock when they bump into the box ahead or the end of the belt (1 = default). */
    UPROPERTY(Category="Dispatch Belt", EditAnywhere, BlueprintReadOnly, meta=(ClampMin="0")) float BumpStrength = 1.0f;
    /** Apparent roller turns per second while the belt runs ("Velocidad" of the roller material). */
    UPROPERTY(Category="Dispatch Belt", EditAnywhere, BlueprintReadOnly) float RollerSpeed = 1.5f;
    UPROPERTY(Category="Dispatch Belt", EditAnywhere, BlueprintReadOnly, meta=(ClampMin="50")) float InteractionRadius = 170.0f;
    UPROPERTY(Category="Dispatch Belt", EditAnywhere, BlueprintReadOnly) FString BeltName = TEXT("CINTA");
    /** How close (cm) the character must be to a box to take it. */
    UPROPERTY(Category="Dispatch Belt", EditAnywhere, BlueprintReadOnly, meta=(ClampMin="50")) float TakeRadius = 140.0f;
    UPROPERTY(Category="Dispatch Belt|Sound", EditAnywhere, BlueprintReadOnly) TObjectPtr<USoundBase> OnSound;
    UPROPERTY(Category="Dispatch Belt|Sound", EditAnywhere, BlueprintReadOnly) TObjectPtr<USoundBase> OffSound;
    /** The panel whose Belt is this one (found when play starts); E next to it switches the belt. */
    UPROPERTY(Category="Dispatch Belt", VisibleInstanceOnly, Transient, BlueprintReadOnly) TObjectPtr<AFactoryBeltButton> Button;
    /** Where the panel stands (the belt itself when it has none). */
    FVector GetPanelLocation() const;
    /** "[E] AGARRAR CAJA" over the box in reach. */
    UPROPERTY(Category="Dispatch Belt", VisibleAnywhere, BlueprintReadOnly) TObjectPtr<UTextRenderComponent> BoxPrompt;
    /** Red "full" sign shown above the belt; click it for the detail. */
    UPROPERTY(Category="Dispatch Belt", VisibleAnywhere, BlueprintReadOnly) TObjectPtr<UStaticMeshComponent> Sign;
    UPROPERTY(Category="Dispatch Belt", VisibleAnywhere, BlueprintReadOnly) TObjectPtr<UTextRenderComponent> SignText;
    /** Where the sign floats, in the machine's space. */
    UPROPERTY(Category="Dispatch Belt", EditAnywhere, BlueprintReadOnly, meta=(MakeEditWidget)) FVector SignLocation = FVector(0, 150, 200);
    /** Whether the HUD shows this belt's detail (toggled by clicking the sign). */
    UPROPERTY(Category="Dispatch Belt", VisibleInstanceOnly, BlueprintReadOnly) bool bDetailOpen = false;
    UPROPERTY(Category="Dispatch Belt", VisibleInstanceOnly, BlueprintReadOnly) bool bActive = false;
    UPROPERTY(Category="Dispatch Belt", VisibleInstanceOnly, BlueprintReadOnly) bool bFull = false;
    UFUNCTION(BlueprintCallable, Category="Dispatch Belt") int32 GetBoxCount() const { return Boxes.Num(); }
    /** About how many boxes fit on the belt (lanes x rows, if they were packed in straight lines). */
    UFUNCTION(BlueprintCallable, Category="Dispatch Belt") int32 GetCapacity() const;
    UFUNCTION(BlueprintCallable, Category="Dispatch Belt") int32 GetLaneCount() const;
    /** Index of the box nearest to User within TakeRadius, or INDEX_NONE; OutDistanceSquared is 2D. */
    int32 NearestBox(const AActor* User, double& OutDistanceSquared) const;
    /** Removes that box from the belt and returns its mesh (for the character to carry). */
    UStaticMesh* TakeBox(int32 Index);
    UFUNCTION(BlueprintCallable, Category="Dispatch Belt") void SetBeltOn(bool bOn);
    /** Switches the belt when the user is at the panel; returns whether it did anything. */
    UFUNCTION(BlueprintCallable, Category="Dispatch Belt") bool TryInteract(AActor* User);
    /** Opens or closes this belt's detail when Clicked is its sign; returns whether it was. */
    UFUNCTION(BlueprintCallable, Category="Dispatch Belt") bool ClickSign(UPrimitiveComponent* Clicked);
    /** Whether User is close enough to the panel (false without a panel). */
    bool InReach(const AActor* User) const;
    virtual void Tick(float DeltaSeconds) override;
protected:
    virtual void BeginPlay() override;
private:
    UPROPERTY(Transient) TArray<TObjectPtr<UStaticMeshComponent>> Boxes;
    UPROPERTY(Transient) TObjectPtr<UMaterialInstanceDynamic> RollerMaterial;
    UPROPERTY(Transient) TObjectPtr<UMaterialInstanceDynamic> ButtonMaterial;
    /** Distance travelled from Start, per box. */
    TArray<float> Travelled;
    /** Sideways position of each box from the Start-End line (cm). */
    TArray<float> Lateral;
    TArray<FDispatchBoxMotion> Motion;
    /** Extra room each box leaves to the box ahead (cm). */
    TArray<float> ExtraGap;
    void Bump(int32 Index, float Strength);
    void PlaceBoxes(float DeltaSeconds);
    float SinceLastBox = 0.0f;
    /** 0 hidden .. 1 fully shown: the sign pops up when the belt fills. */
    float SignShown = 0.0f;
    /** Stopped by itself because it filled up: taking a box starts it again. */
    bool bStoppedWhenFull = false;
    void SpawnBox(float Side);
    float LaneCentre(int32 Lane) const;
    /** Boxes closer than this sideways run into each other (a box and a little room). */
    float SameLane() const { return BoxSpacing * 0.95f; }
    /** A random sideways position at the entrance where a new box would not overlap one still there;
     *  false when there is no room anywhere across. */
    bool FindFreeSide(float& OutSide) const;
    void ApplyState();
};

/**
 * Button post of a dispatch belt, a separate actor so it can be placed freely. Pick its belt in
 * Belt; E next to it switches that belt on and off and its button turns green or red.
 */
UCLASS(Blueprintable)
class FACTORYCTYCORUNTIME_API AFactoryBeltButton : public AActor
{
    GENERATED_BODY()
public:
    AFactoryBeltButton();
    /** The belt this panel switches. */
    UPROPERTY(Category="Belt Button", EditInstanceOnly, BlueprintReadOnly) TObjectPtr<AFactoryDispatchBelt> Belt;
    UPROPERTY(Category="Belt Button", VisibleAnywhere, BlueprintReadOnly) TObjectPtr<UStaticMeshComponent> Panel;
    /** "[E] ENCENDER CINTA n", shown by the belt when the character is in reach. */
    UPROPERTY(Category="Belt Button", VisibleAnywhere, BlueprintReadOnly) TObjectPtr<UTextRenderComponent> Prompt;
};
