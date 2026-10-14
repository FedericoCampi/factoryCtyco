#include "FactoryRoom.h"
#include "FactoryCameraComponent.h"
#include "Components/BoxComponent.h"
#include "Components/StaticMeshComponent.h"
#include "EngineUtils.h"
#include "Engine/World.h"
#include "GameFramework/Pawn.h"
#include "Kismet/GameplayStatics.h"

AFactoryRoom::AFactoryRoom()
{
    PrimaryActorTick.bCanEverTick = true;
    PrimaryActorTick.TickInterval = 0.1f;
    Area = CreateDefaultSubobject<UBoxComponent>(TEXT("Area"));
    SetRootComponent(Area);
    Area->SetBoxExtent(FVector(300, 300, 150));
    Area->SetCollisionEnabled(ECollisionEnabled::NoCollision);
}

bool AFactoryRoom::Contains(const AActor* Actor) const
{
    if (!Actor) return false;
    const FVector Local = Area->GetComponentTransform().InverseTransformPosition(Actor->GetActorLocation());
    const FVector Extent = Area->GetUnscaledBoxExtent();
    return FMath::Abs(Local.X) <= Extent.X && FMath::Abs(Local.Y) <= Extent.Y && FMath::Abs(Local.Z) <= Extent.Z;
}

void AFactoryRoom::Tick(float DeltaSeconds)
{
    Super::Tick(DeltaSeconds);
    const APawn* Player = UGameplayStatics::GetPlayerPawn(this, 0);
    const AActor* Followed = nullptr;
    if (Player)
        if (const auto* Camera = Player->FindComponentByClass<UFactoryCameraComponent>()) Followed = Camera->GetFollowTarget();
    const bool bInside = Contains(Player) || Contains(Followed);
    if (bInside == bOpen) return;
    bOpen = bInside;
    for (AActor* Actor : HideWhenInside)
        if (Actor) Actor->SetActorHiddenInGame(bOpen);
}

AFactoryAutoDoor::AFactoryAutoDoor()
{
    PrimaryActorTick.bCanEverTick = true;
    Leaf = CreateDefaultSubobject<UStaticMeshComponent>(TEXT("Leaf"));
    SetRootComponent(Leaf);
    Leaf->SetCollisionEnabled(ECollisionEnabled::NoCollision);
    Leaf->SetMobility(EComponentMobility::Movable);
}

void AFactoryAutoDoor::BeginPlay()
{
    Super::BeginPlay();
    ClosedYaw = GetActorRotation().Yaw;
}

void AFactoryAutoDoor::Tick(float DeltaSeconds)
{
    Super::Tick(DeltaSeconds);
    // The middle of the doorway, from the hinge along the closed leaf (-X of the leaf).
    const FVector Middle = GetActorLocation() + FRotator(0, ClosedYaw, 0).RotateVector(FVector(-Width / 2, 0, 100));
    // The nearest pawn in reach (it sets the way when the door starts to open).
    const APawn* Nearest = nullptr;
    double NearestDistance = OpenRadius;
    for (TActorIterator<APawn> It(GetWorld()); It; ++It)
    {
        const double Distance = FVector::Dist2D(It->GetActorLocation(), Middle);
        if (Distance <= NearestDistance && FMath::Abs(It->GetActorLocation().Z - Middle.Z) < 250.0f) { NearestDistance = Distance; Nearest = *It; }
    }
    const bool bSomeone = Nearest != nullptr;
    if (Openness <= 0.0f && bSomeone)
    {
        // A positive turn swings the free edge to the leaf's -Y: away from a pawn on its +Y side.
        const FVector Side = FRotator(0, ClosedYaw, 0).RotateVector(FVector::RightVector);
        const bool bOnPlusSide = FVector::DotProduct(Nearest->GetActorLocation() - Middle, Side) >= 0.0f;
        Swing = bOpenAwayFromPawn ? FMath::Abs(OpenYaw) * (bOnPlusSide ? 1.0f : -1.0f) : OpenYaw;
    }
    const float Before = Openness;
    Openness = FMath::Clamp(Openness + (bSomeone ? 1.0f : -1.0f) * DeltaSeconds / OpenSeconds, 0.0f, 1.0f);
    if (Openness == Before) return;
    const float Eased = Openness * Openness * (3.0f - 2.0f * Openness);
    SetActorRotation(FRotator(0, ClosedYaw + Swing * Eased, 0));
}
