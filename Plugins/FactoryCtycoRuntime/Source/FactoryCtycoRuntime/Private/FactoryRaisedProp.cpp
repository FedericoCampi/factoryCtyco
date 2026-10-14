#include "FactoryRaisedProp.h"
#include "Components/StaticMeshComponent.h"
#include "Engine/StaticMesh.h"
#include "Engine/CollisionProfile.h"
#include "Engine/World.h"
#include "Materials/MaterialInterface.h"
#include "UObject/ConstructorHelpers.h"

AFactoryRaisedProp::AFactoryRaisedProp()
{
    PrimaryActorTick.bCanEverTick = false;
    RootComponent = CreateDefaultSubobject<USceneComponent>(TEXT("Root"));
    Base = CreateDefaultSubobject<UStaticMeshComponent>(TEXT("Base"));
    Base->SetupAttachment(RootComponent);
    Body = CreateDefaultSubobject<UStaticMeshComponent>(TEXT("Body"));
    Body->SetupAttachment(RootComponent);
    Pedestal = CreateDefaultSubobject<UStaticMeshComponent>(TEXT("Pedestal"));
    Pedestal->SetupAttachment(RootComponent);
    Pedestal->SetCollisionProfileName(UCollisionProfile::BlockAll_ProfileName);
    static ConstructorHelpers::FObjectFinder<UStaticMesh> Cube(TEXT("/Engine/BasicShapes/Cube.Cube"));
    PedestalMesh = Cube.Object;
}

void AFactoryRaisedProp::OnConstruction(const FTransform& Transform)
{
    Super::OnConstruction(Transform);
    Refresh();
}

void AFactoryRaisedProp::BeginPlay()
{
    Super::BeginPlay();
    Refresh();
}

#if WITH_EDITOR
void AFactoryRaisedProp::PostEditChangeProperty(FPropertyChangedEvent& Event)
{
    // Typing an Elevation moves the actor that far above the surface under it; Refresh then derives it back.
    float FloorZ;
    if (Event.GetMemberPropertyName() == GET_MEMBER_NAME_CHECKED(AFactoryRaisedProp, Elevation) && FindFloor(FloorZ))
    {
        FVector Location = GetActorLocation();
        Location.Z = FloorZ + FMath::Max(0.0f, Elevation);
        SetActorLocation(Location);
    }
    Super::PostEditChangeProperty(Event);
}
#endif

bool AFactoryRaisedProp::FindFloor(float& FloorZ) const
{
    UWorld* World = GetWorld();
    if (!World)
    {
        return false;
    }
    FCollisionQueryParams Params(SCENE_QUERY_STAT(FactoryRaisedPropFloor), false, this);
    const FVector Start = GetActorLocation() + FVector(0, 0, 1);
    FHitResult Hit;
    if (!World->LineTraceSingleByObjectType(Hit, Start, Start - FVector(0, 0, 100000), FCollisionObjectQueryParams(ECC_WorldStatic), Params))
    {
        return false;
    }
    FloorZ = Hit.ImpactPoint.Z;
    return true;
}

void AFactoryRaisedProp::Refresh()
{
    const float BaseHeight = BaseMesh ? FMath::Max(BaseMesh->GetBoundingBox().Max.Z, 1.0f) : 0.0f;
    // Scaled evenly it just gets bigger; a stretch in Z beyond its X scale raises the actor instead (world cm).
    const FVector Scale = GetActorScale3D();
    if (BaseHeight > 0.0f && Scale.X > 0.0f && !FMath::IsNearlyEqual(Scale.Z, Scale.X, 1e-3f))
    {
        SetActorScale3D(FVector(Scale.X, Scale.Y, Scale.X));
        AddActorWorldOffset(FVector(0, 0, FMath::Max(0.0f, (Scale.Z - Scale.X) * BaseHeight)));
    }
    // The gap down to the surface under it (kept from last time if nothing is found, e.g. while the level loads).
    float FloorZ;
    if (FindFloor(FloorZ))
    {
        const float Gap = GetActorLocation().Z - FloorZ;
        Elevation = Gap > 0.5f ? Gap : 0.0f;
    }
    // Elevation is in the world; the parts are in the actor's (scaled) space. Body and plate stay at the actor; the
    // block goes from the surface up to the plate, with the plate's footprint (a little inside it).
    const float Down = FMath::Max(0.0f, Elevation) / FMath::Max(GetActorScale3D().Z, 0.01f);
    Body->SetStaticMesh(BodyMesh);
    Body->SetRelativeLocation(FVector::ZeroVector);
    Base->SetStaticMesh(BaseMesh);
    Base->SetRelativeLocation(FVector::ZeroVector);
    Base->SetRelativeScale3D(FVector::OneVector);
    const bool bBlock = BaseMesh && PedestalMesh && Down > 0.5f;
    Pedestal->SetStaticMesh(PedestalMesh);
    if (PedestalMaterial)
    {
        Pedestal->SetMaterial(0, PedestalMaterial);
    }
    Pedestal->SetVisibility(bBlock);
    Pedestal->SetCollisionEnabled(bBlock ? ECollisionEnabled::QueryAndPhysics : ECollisionEnabled::NoCollision);
    if (bBlock)
    {
        const FBox Plate = BaseMesh->GetBoundingBox();
        const FBox Cube = PedestalMesh->GetBoundingBox();
        const FVector CubeSize = Cube.GetSize().ComponentMax(FVector(1));
        const FVector2D Size = FVector2D(Plate.GetSize()) - FVector2D(2, 2);
        Pedestal->SetRelativeScale3D(FVector(Size.X / CubeSize.X, Size.Y / CubeSize.Y, Down / CubeSize.Z));
        Pedestal->SetRelativeLocation(FVector(Plate.GetCenter().X, Plate.GetCenter().Y, -Down / 2) - Cube.GetCenter() * Pedestal->GetRelativeScale3D());
    }
}
