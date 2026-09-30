#pragma once

#include "CoreMinimal.h"
#include "FactoryTruckGate.h"
#include "FactoryGateBarrier.generated.h"

class USoundBase;
class UStaticMeshComponent;
class UTextRenderComponent;

/**
 * Control booth with a boom barrier. Inside the booth, E raises the barrier (or lowers it). A vehicle
 * driving an AFactoryVehiclePath whose line crosses the arm brakes and waits while it is not fully up;
 * once the vehicle has gone through, the barrier comes down by itself. It never comes down on a vehicle.
 * The whole actor moves as one; Post (with Arm) can also be moved on its own. The booth roof hides
 * while the character is inside, since the camera looks from above.
 */
UCLASS(Blueprintable)
class FACTORYCTYCORUNTIME_API AFactoryGateBarrier : public AFactoryTruckGate
{
    GENERATED_BODY()
public:
    AFactoryGateBarrier();
    UPROPERTY(Category="Gate", VisibleAnywhere, BlueprintReadOnly) TObjectPtr<UStaticMeshComponent> Booth;
    UPROPERTY(Category="Gate", VisibleAnywhere, BlueprintReadOnly) TObjectPtr<UStaticMeshComponent> Roof;
    UPROPERTY(Category="Gate", VisibleAnywhere, BlueprintReadOnly) TObjectPtr<UStaticMeshComponent> Post;
    /** The boom, pivoting on the post; it lies along its +X and rises about its Y. */
    UPROPERTY(Category="Gate", VisibleAnywhere, BlueprintReadOnly) TObjectPtr<UStaticMeshComponent> Arm;
    UPROPERTY(Category="Gate", VisibleAnywhere, BlueprintReadOnly) TObjectPtr<UTextRenderComponent> Prompt;
    /** Half size of the room inside the booth, around its floor centre (cm). */
    UPROPERTY(Category="Gate", EditAnywhere, BlueprintReadOnly) FVector InsideExtent = FVector(72, 72, 120);
    UPROPERTY(Category="Gate", EditAnywhere, BlueprintReadOnly, meta=(ClampMin="0.1")) float RaiseSeconds = 1.6f;
    /** Angle of the arm when fully up (degrees). */
    UPROPERTY(Category="Gate", EditAnywhere, BlueprintReadOnly, meta=(ClampMin="10", ClampMax="90")) float RaisedAngle = 82.0f;
    /** Length of the arm (cm), from the pivot to the tip. */
    UPROPERTY(Category="Gate", EditAnywhere, BlueprintReadOnly, meta=(ClampMin="10")) float ArmLength = 310.0f;
    UPROPERTY(Category="Gate", EditAnywhere, BlueprintReadOnly) TObjectPtr<USoundBase> MoveSound;
    UPROPERTY(Category="Gate", VisibleInstanceOnly, BlueprintReadOnly) bool bWantOpen = false;
    /** 0 down .. 1 up. */
    UPROPERTY(Category="Gate", VisibleInstanceOnly, BlueprintReadOnly) float Openness = 0.0f;
    UFUNCTION(BlueprintCallable, Category="Gate") bool IsOpen() const { return Openness >= 0.999f && bWantOpen; }
    UFUNCTION(BlueprintCallable, Category="Gate") bool IsInside(const AActor* User) const;
    /** E: raises or lowers when User is inside the booth; returns whether it did anything. */
    UFUNCTION(BlueprintCallable, Category="Gate") bool TryInteract(AActor* User);
    UFUNCTION(BlueprintCallable, Category="Gate") void SetOpen(bool bOpen);
    /** Down, lying across the road: pivot and tip in world space. */
    void GetArmLine(FVector& OutPivot, FVector& OutTip) const;
    virtual void GetCrossLine(FVector& OutA, FVector& OutB) const override { GetArmLine(OutA, OutB); }
    virtual bool IsPassable() const override { return IsOpen(); }
    /** Trucks that went out through it (for the booth's panel). */
    UPROPERTY(Category="Gate", VisibleInstanceOnly, BlueprintReadOnly) int32 Passed = 0;
    /** Once a truck is through, the barrier comes down (never onto another one). */
    virtual void VehiclePassed() override { ++Passed; SetOpen(false); }
    /** The exit: going through delivers the load. */
    virtual bool CountsAsDelivery() const override { return true; }
    virtual void Tick(float DeltaSeconds) override;
protected:
    virtual void BeginPlay() override;
private:
    /** The arm's relative rotation as placed (down). */
    FQuat ArmRest = FQuat::Identity;
    void PlaceArm();
};
