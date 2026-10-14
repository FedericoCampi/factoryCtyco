#include "FactorySceneZone.h"
#include "Components/BoxComponent.h"
#include "Components/PrimitiveComponent.h"
#include "Engine/ExponentialHeightFog.h"
#include "Engine/Light.h"
#include "Engine/PostProcessVolume.h"
#include "Engine/SkyLight.h"
#include "Engine/StaticMeshActor.h"
#include "Engine/World.h"
#include "EngineUtils.h"
#include "FactoryVehiclePath.h"
#include "FactoryCameraComponent.h"
#include "GameFramework/Character.h"
#include "GameFramework/PlayerController.h"
#include "GameFramework/Volume.h"
#include "Components/PoseableMeshComponent.h"

const FName AFactorySceneZone::AlwaysTag(TEXT("SiempreVisible"));
const FName AFactorySceneZone::RoofTag(TEXT("Techo"));

namespace
{
    constexpr float UpdateSeconds = 0.15f;
    const FString SceneTagPrefix(TEXT("Escena:"));

    /** Things that are never part of a scene: lights, the sky, fog, volumes, the zones. */
    bool IsShared(const AActor* Actor)
    {
        if (Actor->IsA<AFactorySceneZone>() || Actor->IsA<ALight>() || Actor->IsA<ASkyLight>() || Actor->IsA<AExponentialHeightFog>()
            || Actor->IsA<AVolume>()) return true;
        // The sky atmosphere and clouds (their classes live in other modules): by name.
        const FString Class = Actor->GetClass()->GetName();
        return Class.Contains(TEXT("SkyAtmosphere")) || Class.Contains(TEXT("VolumetricCloud"));
    }
}

AFactorySceneZone::AFactorySceneZone()
{
    PrimaryActorTick.bCanEverTick = false;
    Box = CreateDefaultSubobject<UBoxComponent>(TEXT("Box"));
    RootComponent = Box;
    Box->SetBoxExtent(FVector(1000.0f, 1000.0f, 1500.0f));
    Box->SetCollisionEnabled(ECollisionEnabled::NoCollision);
    Box->ShapeColor = FColor(120, 220, 120);
    Box->SetLineThickness(4.0f);
    SetActorHiddenInGame(true);
}

bool AFactorySceneZone::Contains(const FVector& Point, float Margin) const
{
    const FVector Local = Box->GetComponentTransform().InverseTransformPositionNoScale(Point).GetAbs();
    const FVector Half = Extent() + FVector(Margin);
    return Local.X <= Half.X && Local.Y <= Half.Y && Local.Z <= Half.Z;
}

FVector AFactorySceneZone::Extent() const
{
    return Box->GetScaledBoxExtent();
}

FName AFactorySceneZone::SceneOf(const AActor* Actor)
{
    if (!Actor || !Actor->GetWorld() || Actor->ActorHasTag(AlwaysTag) || IsShared(Actor)) return NAME_None;
    for (const FName& Tag : Actor->Tags)
        if (Tag.ToString().StartsWith(SceneTagPrefix)) return FName(*Tag.ToString().RightChop(SceneTagPrefix.Len()));
    // Where it is (a truck: where its body is now) and how big it is (only a static mesh's own mesh counts: other
    // actors can have parts placed at the world's origin that would stretch their bounds).
    FVector Center = Actor->GetActorLocation(), Half = FVector::ZeroVector;
    if (const AFactoryVehiclePath* Truck = Cast<AFactoryVehiclePath>(Actor)) Center = Truck->Vehicle->GetComponentLocation();
    else if (const AStaticMeshActor* Mesh = Cast<AStaticMeshActor>(Actor))
        if (const UPrimitiveComponent* Part = Mesh->GetStaticMeshComponent())
        {
            Center = Part->Bounds.Origin;
            Half = Part->Bounds.BoxExtent;
        }
    const AFactorySceneZone* Best = nullptr;
    double BestVolume = TNumericLimits<double>::Max();
    for (TActorIterator<AFactorySceneZone> It(Actor->GetWorld()); It; ++It)
    {
        const FVector Zone = It->Extent();
        // Bigger than the zone (an outdoor floor, the horizon): it belongs to every scene.
        if (!It->Contains(Center) || Half.X > Zone.X * 1.25f || Half.Y > Zone.Y * 1.25f) continue;
        const double Volume = Zone.X * Zone.Y * Zone.Z;
        if (Volume < BestVolume) { BestVolume = Volume; Best = *It; }
    }
    return Best ? Best->Scene : NAME_None;
}

UFactorySceneSubsystem* AFactorySceneZone::GetSceneSubsystem(const AActor* Context)
{
    const UWorld* World = Context ? Context->GetWorld() : nullptr;
    return World ? World->GetSubsystem<UFactorySceneSubsystem>() : nullptr;
}

TStatId UFactorySceneSubsystem::GetStatId() const
{
    RETURN_QUICK_DECLARE_CYCLE_STAT(UFactorySceneSubsystem, STATGROUP_Tickables);
}

bool UFactorySceneSubsystem::DoesSupportWorldType(const EWorldType::Type WorldType) const
{
    return WorldType == EWorldType::Game || WorldType == EWorldType::PIE;
}

void UFactorySceneSubsystem::Tick(float DeltaTime)
{
    Super::Tick(DeltaTime);
    Clock -= DeltaTime;
    if (Clock > 0.0f) return;
    Clock = UpdateSeconds;
    Update();
}

bool UFactorySceneSubsystem::IsHidden(const AActor* Actor) const
{
    for (const TWeakObjectPtr<AActor>& Each : Hidden) if (Each.Get() == Actor) return true;
    return false;
}

void UFactorySceneSubsystem::Update()
{
    UWorld* World = GetWorld();
    APlayerController* PC = World ? World->GetFirstPlayerController() : nullptr;
    const APawn* Pawn = PC ? PC->GetPawn() : nullptr;
    // What was hidden last time comes back first (also if the controller changed).
    if (APlayerController* Old = Player.Get())
    {
        for (const TWeakObjectPtr<AActor>& Each : Hidden) Old->HiddenActors.Remove(Each.Get());
        for (const TWeakObjectPtr<UPrimitiveComponent>& Each : HiddenParts) Old->HiddenPrimitiveComponents.Remove(Each);
    }
    Hidden.Reset();
    HiddenParts.Reset();
    Player = PC;
    Visible.Reset();
    if (!Pawn) return;

    // The scenes the character is in; between scenes, the last ones; and any whose edge is near.
    const FVector Where = Pawn->GetActorLocation();
    TSet<FName> Inside, Near;
    bool bAnyZone = false;
    for (TActorIterator<AFactorySceneZone> It(World); It; ++It)
    {
        bAnyZone = true;
        if (It->Contains(Where)) Inside.Add(It->Scene);
        if (It->Contains(Where, NeighborMargin)) Near.Add(It->Scene);
    }
    // Roofs (and the walls raised to them) only in first person: from above, the isometric camera looks in.
    const UFactoryCameraComponent* View = Pawn->FindComponentByClass<UFactoryCameraComponent>();
    if (!(View && View->IsFirstPerson()))
        for (TActorIterator<AActor> It(World); It; ++It)
            if (It->ActorHasTag(AFactorySceneZone::RoofTag))
            {
                PC->HiddenActors.AddUnique(*It);
                Hidden.Add(*It);
            }
    if (!bAnyZone) return;
    if (!Inside.IsEmpty()) LastInside = Inside;
    Visible = LastInside;
    Visible.Append(Near);
    if (Visible.IsEmpty()) return;   // not in any scene yet: everything shows

    for (TActorIterator<AActor> It(World); It; ++It)
    {
        AActor* Actor = *It;
        if (!IsValid(Actor) || Actor == Pawn || Actor->IsA<APlayerController>()) continue;
        // Trucks and characters move: where they are now; the rest once.
        const bool bMoves = Actor->IsA<AFactoryVehiclePath>() || Actor->IsA<ACharacter>();
        FName Scene;
        if (bMoves) Scene = AFactorySceneZone::SceneOf(Actor);
        else if (const FName* Seen = Known.Find(Actor)) Scene = *Seen;
        else Scene = Known.Add(Actor, AFactorySceneZone::SceneOf(Actor));
        if (Scene.IsNone() || Visible.Contains(Scene)) continue;
        if (const AFactoryVehiclePath* Truck = Cast<AFactoryVehiclePath>(Actor))
        {
            // Only the truck itself (its body and what rides on it): its road is part of the yard.
            TArray<USceneComponent*> Parts;
            Truck->Vehicle->GetChildrenComponents(true, Parts);
            Parts.Add(Truck->Vehicle);
            for (USceneComponent* Part : Parts)
                if (UPrimitiveComponent* Primitive = Cast<UPrimitiveComponent>(Part))
                {
                    PC->HiddenPrimitiveComponents.AddUnique(Primitive);
                    HiddenParts.Add(Primitive);
                }
            continue;
        }
        PC->HiddenActors.AddUnique(Actor);
        Hidden.Add(Actor);
    }
}
