#pragma once

#include "CoreMinimal.h"
#include "GameFramework/Actor.h"
#include "FactoryTruckGate.generated.h"

/**
 * Something across a truck line that trucks must wait at while it is shut (a boom barrier, a roll-up
 * door...). AFactoryVehiclePath finds every one whose cross line meets its line, brakes before it while
 * it is not passable, and tells it when a truck is under it and when one has gone through.
 */
UCLASS(Abstract)
class FACTORYCTYCORUNTIME_API AFactoryTruckGate : public AActor
{
    GENERATED_BODY()
public:
    /** Whether any vehicle is under it (each vehicle reports itself with SetVehicleUnder). */
    UPROPERTY(Category="Gate", VisibleInstanceOnly, BlueprintReadOnly) bool bVehicleUnder = false;
    void SetVehicleUnder(const AActor* Vehicle, bool bUnder);
    /** The line across the road that trucks must not cross while it is shut, in world space. */
    virtual void GetCrossLine(FVector& OutA, FVector& OutB) const {}
    /** Trucks may drive through now. */
    virtual bool IsPassable() const { return true; }
    /** A truck has just gone all the way through. */
    virtual void VehiclePassed() {}
    /** Going through it delivers the truck's load (the exit barrier), for the mission. */
    virtual bool CountsAsDelivery() const { return false; }
protected:
    TSet<TWeakObjectPtr<const AActor>> Under;
};
