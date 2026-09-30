#include "FactoryTruckGate.h"

void AFactoryTruckGate::SetVehicleUnder(const AActor* Vehicle, bool bUnder)
{
    if (bUnder) Under.Add(Vehicle);
    else Under.Remove(Vehicle);
    bVehicleUnder = Under.Num() > 0;
}
