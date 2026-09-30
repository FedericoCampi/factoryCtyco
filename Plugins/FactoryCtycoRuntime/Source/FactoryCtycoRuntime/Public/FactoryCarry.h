#pragma once

#include "CoreMinimal.h"
#include "Components/ActorComponent.h"
#include "GameFramework/Actor.h"
#include "FactoryCarry.generated.h"

class USoundBase;
class UStaticMesh;
class UStaticMeshComponent;
class UTextRenderComponent;

/** A box set down on the floor; E next to it picks it up again. */
UCLASS(Blueprintable)
class FACTORYCTYCORUNTIME_API AFactoryLooseBox : public AActor
{
    GENERATED_BODY()
public:
    AFactoryLooseBox();
    UPROPERTY(Category="Box", VisibleAnywhere, BlueprintReadOnly) TObjectPtr<UStaticMeshComponent> Mesh;
};

/**
 * Lets the character carry one box in both hands. The box sits between the hand bones every frame
 * (the carry animations hold the wrists on its sides) and the locomotion switches to its carry blend
 * space. Added at runtime by UFactoryGatheringComponent; E sets the box down in front.
 */
UCLASS(ClassGroup=(Factory), meta=(BlueprintSpawnableComponent))
class FACTORYCTYCORUNTIME_API UFactoryCarryComponent : public UActorComponent
{
    GENERATED_BODY()
public:
    UFactoryCarryComponent();
    /** Hand bones of the character's skeleton. */
    UPROPERTY(Category="Carry", EditAnywhere, BlueprintReadOnly) FName LeftHand = TEXT("hand_l");
    UPROPERTY(Category="Carry", EditAnywhere, BlueprintReadOnly) FName RightHand = TEXT("hand_r");
    /** From the midpoint of the wrists to the box centre, forward (cm). */
    UPROPERTY(Category="Carry", EditAnywhere, BlueprintReadOnly) float ForwardOffset = 6.0f;
    UPROPERTY(Category="Carry", EditAnywhere, BlueprintReadOnly) float PickupRadius = 130.0f;
    /** Played when a box comes into the hands, and when it leaves them (set down or put on a belt). */
    UPROPERTY(Category="Carry", EditAnywhere, BlueprintReadOnly) TObjectPtr<USoundBase> PickupSound;
    UPROPERTY(Category="Carry", EditAnywhere, BlueprintReadOnly) TObjectPtr<USoundBase> DropSound;
    UFUNCTION(BlueprintPure, Category="Carry") bool IsCarrying() const { return HeldBox != nullptr; }
    /** Puts a box of this mesh in the hands; returns false if they are already full. */
    UFUNCTION(BlueprintCallable, Category="Carry") bool Take(UStaticMesh* BoxMesh);
    /** Sets the held box down in front of the character. */
    UFUNCTION(BlueprintCallable, Category="Carry") bool Drop();
    /** Hands the held box over (to a belt): empties the hands and returns its mesh and where it was. */
    UStaticMesh* Release(FTransform& OutWorld);
    /** Picks up the nearest loose box in reach; returns whether it did. */
    UFUNCTION(BlueprintCallable, Category="Carry") bool PickLoose();
    AFactoryLooseBox* NearestLoose(float& OutDistanceSquared) const;
protected:
    virtual void EndPlay(const EEndPlayReason::Type Reason) override;
    virtual void TickComponent(float DeltaTime, ELevelTick TickType, FActorComponentTickFunction* ThisTickFunction) override;
private:
    UPROPERTY(Transient) TObjectPtr<UStaticMeshComponent> HeldBox;
    UPROPERTY(Transient) TObjectPtr<UTextRenderComponent> LoosePrompt;
    void SetCarrying(bool bCarrying) const;
    void Play(bool bPickup);
    void PlaceHeldBox() const;
};
