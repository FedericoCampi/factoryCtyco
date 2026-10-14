#include "FactoryBeltStation.h"
#include "FactoryDemo.h"
#include "Components/BoxComponent.h"
#include "Components/PointLightComponent.h"

namespace
{
    constexpr float FlashSeconds = 0.5f;
}

AFactoryBeltStation::AFactoryBeltStation()
{
    PrimaryActorTick.bCanEverTick = true;
    Zone = CreateDefaultSubobject<UBoxComponent>(TEXT("Zone"));
    RootComponent = Zone;
    Zone->SetBoxExtent(FVector(100, 100, 100));
    Zone->SetCollisionEnabled(ECollisionEnabled::NoCollision);
    Zone->ShapeColor = FColor(80, 190, 255);
    Flash = CreateDefaultSubobject<UPointLightComponent>(TEXT("Flash"));
    Flash->SetupAttachment(Zone);
    Flash->SetIntensity(0.0f);
    Flash->SetAttenuationRadius(500.0f);
    Flash->SetCastShadows(false);
}

void AFactoryBeltStation::Tick(float DeltaSeconds)
{
    Super::Tick(DeltaSeconds);
    for (AFactoryBuilding* Belt : Belts)
    {
        if (!IsValid(Belt) || !OutputResource || InputItem.IsNone() || Belt->Input->GetQuantity(InputItem) < 1) continue;
        // Where the load is now on the belt, in the station's box.
        const float Fraction = Belt->ProgressSeconds / FMath::Max(Belt->TravelSeconds(), 0.01f);
        const FVector Load = Belt->GetActorTransform().TransformPosition(Belt->BeltLocalAt(FMath::Clamp(Fraction, 0.0f, 1.0f) * 0.9f + 0.05f));
        const FVector Local = Zone->GetComponentTransform().InverseTransformPosition(Load);
        const FVector Extent = Zone->GetUnscaledBoxExtent();
        if (FMath::Abs(Local.X) > Extent.X || FMath::Abs(Local.Y) > Extent.Y || FMath::Abs(Local.Z) > Extent.Z) continue;
        Belt->Input->RemoveItem(InputItem, 1);
        Belt->Input->AddItem(OutputResource, 1);
        ++Processed;
        FlashLeft = FlashSeconds;
        Flash->SetWorldLocation(Load + FVector(0, 0, 40));
    }
    if (FlashLeft > 0.0f)
    {
        FlashLeft = FMath::Max(0.0f, FlashLeft - DeltaSeconds);
        Flash->SetLightColor(FlashColor);
        Flash->SetIntensity(FlashIntensity * FMath::Sin(FlashLeft / FlashSeconds * PI));
    }
}
