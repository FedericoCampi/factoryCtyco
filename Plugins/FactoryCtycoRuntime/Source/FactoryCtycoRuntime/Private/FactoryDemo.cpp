#include "FactoryDemo.h"
#include "FactoryBeltSupports.h"
#include "FactoryGateBarrier.h"
#include "FactoryDispatchBelt.h"
#include "FactoryElevator.h"
#include "EngineUtils.h"
#include "FactoryCameraComponent.h"
#include "FactoryPresentationComponent.h"
#include "Components/BoxComponent.h"
#include "Components/InputComponent.h"
#include "Components/InstancedStaticMeshComponent.h"
#include "Components/StaticMeshComponent.h"
#include "DrawDebugHelpers.h"
#include "Engine/StaticMesh.h"
#include "Engine/World.h"
#include "EngineUtils.h"
#include "GameFramework/Pawn.h"
#include "GameFramework/PlayerController.h"
#include "Containers/Ticker.h"
#include "Kismet/GameplayStatics.h"
#include "UObject/ConstructorHelpers.h"

namespace
{
    const FName ScrapId(TEXT("Scrap"));
    const FName PlateId(TEXT("Plate"));
    constexpr float BeltTravelSeconds = 0.8f;
    APlayerController* Controller(const UActorComponent* Component)
    {
        const APawn* Pawn = Cast<APawn>(Component->GetOwner());
        return Pawn ? Cast<APlayerController>(Pawn->GetController()) : nullptr;
    }
    void RestoreInventory(UFactoryInventoryComponent* Inventory, const TMap<FName, int32>& Items, AFactoryDemoWorld* Factory)
    {
        Inventory->Items.Empty();
        Inventory->Definitions.Empty();
        for (const auto& Pair : Items) Inventory->AddItem(Factory->Resource(Pair.Key), Pair.Value);
    }
}

AFactoryBuilding::AFactoryBuilding()
{
    // Ticks only while something falls into it (StartFall).
    PrimaryActorTick.bCanEverTick = true;
    PrimaryActorTick.bStartWithTickEnabled = false;
    RootComponent = CreateDefaultSubobject<USceneComponent>(TEXT("Root"));
    Visual = CreateDefaultSubobject<UStaticMeshComponent>(TEXT("Visual"));
    Visual->SetupAttachment(RootComponent);
    Visual->SetCollisionProfileName(TEXT("NoCollision"));
    Base = CreateDefaultSubobject<UStaticMeshComponent>(TEXT("Base"));
    Base->SetupAttachment(RootComponent);
    Base->SetCollisionProfileName(TEXT("NoCollision"));
    Collision = CreateDefaultSubobject<UBoxComponent>(TEXT("Collision"));
    Collision->SetupAttachment(RootComponent);
    Collision->SetCollisionProfileName(TEXT("BlockAll"));
    Cargo = CreateDefaultSubobject<UStaticMeshComponent>(TEXT("Cargo"));
    Cargo->SetupAttachment(RootComponent);
    Cargo->SetCollisionProfileName(TEXT("NoCollision"));
    Cargo->SetVisibility(false);
    Cargo->SetUsingAbsoluteScale(true);   // stretched belts do not stretch what they carry
    Falling = CreateDefaultSubobject<UStaticMeshComponent>(TEXT("Falling"));
    Falling->SetupAttachment(RootComponent);
    Falling->SetCollisionProfileName(TEXT("NoCollision"));
    Falling->SetUsingAbsoluteLocation(true);
    Falling->SetUsingAbsoluteScale(true);
    Falling->SetVisibility(false);
    Supports = CreateDefaultSubobject<UInstancedStaticMeshComponent>(TEXT("Supports"));
    Supports->SetupAttachment(RootComponent);
    Supports->SetUsingAbsoluteLocation(true);
    Supports->SetUsingAbsoluteRotation(true);
    Supports->SetUsingAbsoluteScale(true);
    Supports->SetCollisionProfileName(TEXT("BlockAll"));
    static ConstructorHelpers::FObjectFinder<UStaticMesh> SupportCube(TEXT("/Engine/BasicShapes/Cube.Cube"));
    if (SupportCube.Succeeded()) SupportMesh = SupportCube.Object;
    Input = CreateDefaultSubobject<UFactoryInventoryComponent>(TEXT("Input"));
    Output = CreateDefaultSubobject<UFactoryInventoryComponent>(TEXT("Output"));
    Presentation = CreateDefaultSubobject<UFactoryPresentationComponent>(TEXT("Presentation"));
}

void AFactoryBuilding::OnConstruction(const FTransform& Transform)
{
    Super::OnConstruction(Transform);
    AbsorbZStretch();
    ApplySlope();
    ApplyLiftHandle();
    RefreshVisuals();
}

bool AFactoryBuilding::IsStraightBelt() const
{
    return Definition && Definition->Kind == EFactoryBuildingKind::Belt && FMath::Abs(Definition->TurnDegrees) < 0.5f && LiftHeight <= 0.0f;
}

bool AFactoryBuilding::IsLift() const
{
    return Definition && Definition->Kind == EFactoryBuildingKind::Belt && FMath::Abs(Definition->TurnDegrees) < 0.5f && LiftHeight > 0.0f;
}

void AFactoryBuilding::ApplyLiftHandle()
{
    if (!IsLift()) return;
    const FVector Top(100, 0, 33 + Lift() + LiftHeight);
    // A diamond dragged up or down: the lift's top goes there.
    if (!OutputEndHandle.IsZero() && !OutputEndHandle.Equals(PlacedOutHandle.IsZero() ? Top : PlacedOutHandle, 0.5f))
        LiftHeight = FMath::Max(10.0f, OutputEndHandle.Z - 33 - Lift());
    InputEndHandle = PlacedInHandle = FVector(-100, 0, 33 + Lift());
    OutputEndHandle = PlacedOutHandle = FVector(100, 0, 33 + Lift() + LiftHeight);
}

namespace { constexpr float FallSeconds = 0.45f; }

void AFactoryBuilding::StartFall(const UFactoryResourceDefinition* Item, const FVector& From)
{
    if (!Item || !Item->PickupMesh || MachineDropPoint.IsZero()) return;
    Falling->SetStaticMesh(Item->PickupMesh);
    Falling->SetWorldScale3D(Item->CargoScale());
    Falling->SetWorldLocation(From);
    Falling->SetVisibility(true);
    FallFrom = From;
    FallLeft = FallSeconds;
    SetActorTickEnabled(true);
}

void AFactoryBuilding::Tick(float DeltaSeconds)
{
    Super::Tick(DeltaSeconds);
    if (FallLeft <= 0.0f) { SetActorTickEnabled(false); return; }
    FallLeft = FMath::Max(0.0f, FallLeft - DeltaSeconds);
    // A short hop over the edge and down into the drop point.
    const float T = 1.0f - FallLeft / FallSeconds;
    const FVector To = GetActorTransform().TransformPosition(MachineDropPoint);
    Falling->SetWorldLocation(FMath::Lerp(FallFrom, To, T) + FVector(0, 0, 35.0f * FMath::Sin(T * PI)));
    Falling->SetWorldRotation(FRotator(T * 200.0f, T * 90.0f, 0));
    if (FallLeft <= 0.0f)
    {
        Falling->SetVisibility(false);
        SetActorTickEnabled(false);
    }
}

void AFactoryBuilding::PlacePlatform()
{
    if (!Definition) return;
    Visual->SetRelativeLocation(Definition->MeshOffset + FVector(0, 0, Lift() + PlatformRise));
    Collision->SetRelativeLocation(FVector(0, 0, Lift() + PlatformRise + 19));
}

void AFactoryBuilding::LowerPlatform(float DeltaSeconds)
{
    if (!IsLift() || PlatformRise <= 0.0f) return;
    PlatformRise = FMath::FInterpConstantTo(PlatformRise, 0.0f, DeltaSeconds, LiftSpeed);
    PlacePlatform();
}

void AFactoryBuilding::ApplySlope()
{
    if (!IsStraightBelt()) return;
    const float Deck = Lift() + 33.0f;
    const FVector Middle(0, 0, Deck), InEnd(-100, 0, Deck), OutEnd(100, 0, Deck);
    const FTransform& T = GetActorTransform();
    const FVector MiddleWorld = T.TransformPosition(Middle);
    const FVector Forward = FRotator(0, GetActorRotation().Yaw, 0).Vector();
    // A dragged end handle: the belt points from its middle to it (zero: not placed yet).
    auto FromHandle = [&](const FVector& Handle, const FVector& Placed, const FVector& End, float Sign, float& OutSlope)
    {
        if (Handle.IsZero() || Handle.Equals(Placed.IsZero() ? End : Placed, 0.5f)) return false;
        const FVector Delta = (T.TransformPosition(Handle) - MiddleWorld) * Sign;
        const float Along = FVector::DotProduct(Delta, Forward);
        if (Along < 1.0f) return false;
        OutSlope = FMath::RadiansToDegrees(FMath::Atan2(Delta.Z, Along));
        return true;
    };
    float Wanted = Slope;
    const bool bHandle = FromHandle(OutputEndHandle, PlacedOutHandle, OutEnd, 1.0f, Wanted)
        || FromHandle(InputEndHandle, PlacedInHandle, InEnd, -1.0f, Wanted);
    InputEndHandle = PlacedInHandle = InEnd;
    OutputEndHandle = PlacedOutHandle = OutEnd;
    if (!bHandle && FMath::IsNearlyEqual(Slope, AppliedSlope, 0.01f))
    {
        // Slope untouched: the actor was turned in pitch some other way (gizmo, level, save); Slope follows it.
        Slope = AppliedSlope = GetActorRotation().Pitch;
        return;
    }
    Wanted = FMath::Clamp(Wanted, -60.0f, 60.0f);
    FRotator Rotation = GetActorRotation();
    Rotation.Pitch = Wanted;
    SetActorRotation(Rotation);
    SetActorLocation(GetActorLocation() + MiddleWorld - GetActorTransform().TransformPosition(Middle));
    Slope = AppliedSlope = Wanted;
}

void AFactoryBuilding::AbsorbZStretch()
{
    // A belt stretched in Z goes up on legs instead: the stretch becomes Elevation (34 cm per unit: the belt's height).
    const FVector Scale = GetActorScale3D();
    if (Definition && Definition->Kind == EFactoryBuildingKind::Belt && Scale.Z > 0.0f && !FMath::IsNearlyEqual(Scale.Z, 1.0f, 1e-3f))
    {
        Elevation = FMath::Max(0.0f, Elevation + (Scale.Z - 1.0f) * 34.0f);
        SetActorScale3D(FVector(Scale.X, Scale.Y, 1.0f));
    }
}

// Levels save the component transforms RefreshVisuals wrote when the actor was placed; a
// definition edited since (a platform added, a mesh swapped) would otherwise not reach them.
void AFactoryBuilding::BeginPlay()
{
    Super::BeginPlay();
    AbsorbZStretch();
    ApplySlope();
    ApplyLiftHandle();
    PlatformRise = 0.0f;
    RefreshVisuals();
}

float AFactoryBuilding::Lift() const
{
    if (!Definition) return 0.0f;
    // A raised belt stands on its legs, not on the platform: it rides at Elevation, where it hands material on.
    if (Definition->Kind == EFactoryBuildingKind::Belt && (Elevation > 0.0f || LiftHeight > 0.0f)) return Elevation;
    return FMath::Max(0.0f, Definition->BaseHeight);
}

void AFactoryBuilding::RefreshVisuals()
{
    if (!Definition) return;
    // The building stays on the floor for the grid and for handing material on; only what is
    // seen and touched goes up, onto the platform.
    const float Up = Lift();
    const bool bRaisedBelt = Definition->Kind == EFactoryBuildingKind::Belt && (Elevation > 0.0f || LiftHeight > 0.0f);
    UStaticMesh* Platform = Up > 0 && !bRaisedBelt ? Definition->BaseMesh.Get() : nullptr;
    Base->SetStaticMesh(Platform);
    if (Platform) Base->SetRelativeScale3D(FVector(1, 1, Up / FMath::Max(Platform->GetBoundingBox().GetSize().Z, 1.0)));
    Visual->SetStaticMesh(Definition->Mesh);
    Visual->SetRelativeScale3D(Definition->MeshScale);
    Visual->SetRelativeLocation(Definition->MeshOffset + FVector(0, 0, Up));
    Visual->SetRelativeRotation(FRotator(0, Definition->MeshYaw, 0));
    const bool bBelt = Definition->Kind == EFactoryBuildingKind::Belt;
    const bool bCorner = bBelt && FMath::Abs(Definition->TurnDegrees) >= 0.5f;
    if (bBelt)
    {
        // Only the belt itself blocks: under a raised belt there is room (its legs have their own collision).
        // A corner blocks with its own mesh (a box would also fill the inside of the curve).
        Collision->SetBoxExtent(FVector(88, 72, 17));
        Collision->SetRelativeLocation(FVector(0, 0, Up + 19));
        Collision->SetCollisionEnabled(bCorner ? ECollisionEnabled::NoCollision : ECollisionEnabled::QueryAndPhysics);
        Visual->SetCollisionProfileName(bCorner ? TEXT("BlockAll") : TEXT("NoCollision"));
    }
    else
    {
        const float Height = 150.0f + Up;
        Collision->SetBoxExtent(FVector(88, 88, Height / 2));
        Collision->SetRelativeLocation(FVector(0, 0, Height / 2 + 2));
    }
    if (IsLift()) PlacePlatform();
    Input->Capacity = bBelt ? 1 : Definition->Capacity;
    Output->Capacity = Definition->Kind == EFactoryBuildingKind::Processor ? Definition->Capacity : 0;
    BuildSupports();
}

FVector AFactoryBuilding::BeltLocalAt(float Fraction, float* OutYaw) const
{
    const float F = FMath::Clamp(Fraction, 0.0f, 1.0f);
    const float Z = 33 + Lift();
    const float Turn = Definition ? Definition->TurnDegrees : 0.0f;
    if (IsLift())
    {
        // Lift: slides onto the middle of the platform, rides it up and slides off the front edge at the top.
        constexpr float Slide = 0.15f;
        if (OutYaw) *OutYaw = 0.0f;
        const float X = F < Slide ? FMath::Lerp(-100.0f, 0.0f, F / Slide) : F > 1.0f - Slide ? FMath::Lerp(0.0f, 100.0f, (F - 1.0f + Slide) / Slide) : 0.0f;
        return FVector(X, 0, Z + LiftHeight * FMath::Clamp((F - Slide) / (1.0f - 2.0f * Slide), 0.0f, 1.0f));
    }
    if (FMath::Abs(Turn) < 0.5f)
    {
        if (OutYaw) *OutYaw = 0.0f;
        return FVector(FMath::Lerp(-100.0f, 100.0f, F), 0, Z);
    }
    // Corner: from the middle of the back edge, heading +X, along TurnRadius towards Sign * Y.
    const float Radius = FMath::Max(20.0f, Definition->TurnRadius);
    const float Sign = Turn > 0.0f ? 1.0f : -1.0f;
    const float Angle = FMath::DegreesToRadians(FMath::Abs(Turn)) * F;
    if (OutYaw) *OutYaw = Sign * FMath::RadiansToDegrees(Angle);
    return FVector(-100.0f + Radius * FMath::Sin(Angle), Sign * Radius * (1.0f - FMath::Cos(Angle)), Z);
}

float AFactoryBuilding::BeltLength() const
{
    float Total = 0.0f;
    FVector Prev = GetActorTransform().TransformPosition(BeltLocalAt(0.0f));
    for (int32 I = 1; I <= 8; ++I)
    {
        const FVector Next = GetActorTransform().TransformPosition(BeltLocalAt(I / 8.0f));
        Total += FVector::Dist(Prev, Next);
        Prev = Next;
    }
    return Total;
}

float AFactoryBuilding::TravelSeconds() const
{
    const bool bBelt = Definition && Definition->Kind == EFactoryBuildingKind::Belt;
    // A lift rides up at LiftSpeed for the middle 70 % of its trip.
    if (IsLift()) return LiftHeight / FMath::Max(LiftSpeed, 10.0f) / 0.7f;
    return bBelt ? BeltTravelSeconds * FMath::Max(BeltLength(), 20.0f) / 200.0f : BeltTravelSeconds;
}

FVector AFactoryBuilding::InputPoint() const
{
    // Material is handed on at floor-belt height (33 cm over the actor's base), not over a platform.
    // A raised belt hands it on at its own height, a tilted one at the height of that end.
    const bool bBelt = Definition && Definition->Kind == EFactoryBuildingKind::Belt;
    FVector Local = bBelt ? BeltLocalAt(0.0f) - FVector(0, 0, Lift() - Elevation) : MachineInput.IsZero() ? FVector(-100, 0, 33) : MachineInput;
    return GetActorTransform().TransformPosition(Local);
}

FVector AFactoryBuilding::OutputPoint() const
{
    const bool bBelt = Definition && Definition->Kind == EFactoryBuildingKind::Belt;
    FVector Local = bBelt ? BeltLocalAt(1.0f) - FVector(0, 0, Lift() - Elevation) : MachineOutput.IsZero() ? FVector(100, 0, 33) : MachineOutput;
    return GetActorTransform().TransformPosition(Local);
}

void AFactoryBuilding::PlaceCargo(float Fraction)
{
    float Heading = 0.0f;
    const FVector Spot = BeltLocalAt(FMath::Clamp(Fraction, 0.0f, 1.0f) * 0.9f + 0.05f, &Heading);
    Cargo->SetRelativeLocationAndRotation(Spot, FRotator(0, Heading, 0));
    if (IsLift())
    {
        // The platform carries the load: it is wherever the load is.
        PlatformRise = Spot.Z - 33 - Lift();
        PlacePlatform();
    }
}

void AFactoryBuilding::BuildSupports()
{
    TArray<FVector> Tops;
    if (IsLift())
    {
        // Four guide posts at the platform's corners, from over the top of the lift down to the floor.
        for (const FVector2D Corner : {FVector2D(-82, 64), FVector2D(-82, -64), FVector2D(82, 64), FVector2D(82, -64)})
            Tops.Add(GetActorTransform().TransformPosition(FVector(Corner.X, Corner.Y, Lift() + LiftHeight + 60)));
    }
    else if (Definition && Definition->Kind == EFactoryBuildingKind::Belt)
    {
        // Legs on both sides of the belt, from its underside (Lift) to the floor: near each end and every
        // SupportSpacing between them.
        const float Span = BeltLength();
        const int32 Between = FMath::FloorToInt(FMath::Max(Span - 50.0f, 0.0f) / SupportSpacing);
        TArray<float> Fractions = {0.1f, 0.9f};
        for (int32 I = 1; I <= Between; ++I) Fractions.Add(0.1f + 0.8f * I / (Between + 1));
        for (const float F : Fractions)
        {
            float Heading = 0.0f;
            FVector Local = BeltLocalAt(F, &Heading);
            Local.Z = Lift();
            const FVector Side = FRotator(0, Heading, 0).RotateVector(FVector(0, 58, 0));
            Tops.Add(GetActorTransform().TransformPosition(Local + Side));
            Tops.Add(GetActorTransform().TransformPosition(Local - Side));
        }
    }
    const int32 Missed = FactoryPlaceSupports(Supports, this, SupportMesh, SupportMaterial, Tops, SupportWidth, SupportMinGap);
    // In the editor a belt can be built before the floor under it is loaded: try again a moment later.
    if (Missed == 0 || !GetWorld() || GetWorld()->IsGameWorld() || SupportRetries >= 10)
    {
        SupportRetries = 0;
        return;
    }
    ++SupportRetries;
    FTSTicker::GetCoreTicker().AddTicker(FTickerDelegate::CreateWeakLambda(this, [this](float)
    {
        BuildSupports();
        return false;
    }), 0.5f);
}

bool AFactoryBuilding::CanAccept(FName Item) const
{
    if (!Definition || Input->GetFreeSpace() <= 0) return false;
    if (IsLift() && PlatformRise > 1.0f) return false;   // the platform is still coming down
    if (Definition->Kind == EFactoryBuildingKind::Storage) return Item == StorageItem;
    return Definition->InputItem.IsNone() || Definition->InputItem == Item;
}

UFactoryInventoryComponent* AFactoryBuilding::Supply() const
{
    return Definition && Definition->Kind == EFactoryBuildingKind::Processor ? Output.Get() : Input.Get();
}

int32 AFactoryBuilding::StoredTotal() const { return Input->GetTotal() + Output->GetTotal(); }

void AFactoryBuilding::Simulate(float DeltaSeconds, AFactoryDemoWorld* Factory)
{
    if (!Definition) return;
    if (Definition->Kind == EFactoryBuildingKind::Belt)
    {
        if (Input->GetTotal() == 0) { ProgressSeconds = 0; StateText = TEXT("Esperando material"); }
        else
        {
            const float Travel = TravelSeconds();
            ProgressSeconds = FMath::Min(Travel, ProgressSeconds + DeltaSeconds);
            StateText = ProgressSeconds < Travel ? TEXT("Transportando") : bConnected ? TEXT("Salida bloqueada") : TEXT("Salida sin conectar");
        }
        return;
    }
    if (Definition->Kind == EFactoryBuildingKind::Storage)
    {
        StateText = Input->GetFreeSpace() == 0 ? TEXT("Depósito lleno") : Input->GetTotal() > 0 ? TEXT("Material disponible") : TEXT("Vacío · E para cargar");
        return;
    }
    if (Input->GetQuantity(Definition->InputItem) < Definition->InputQuantity)
    {
        StateText = TEXT("Sin material de entrada");
        return;
    }
    if (Output->GetFreeSpace() < Definition->OutputQuantity)
    {
        StateText = TEXT("Salida llena · proceso pausado");
        return;
    }
    StateText = TEXT("Procesando");
    ProgressSeconds = FMath::Min(Definition->CycleSeconds, ProgressSeconds + DeltaSeconds);
    if (ProgressSeconds + KINDA_SMALL_NUMBER >= Definition->CycleSeconds)
    {
        UFactoryResourceDefinition* Result = Factory->Resource(Definition->OutputItem);
        if (!Result) return;
        // Reserve the output before consuming any input. Partial cycles keep their input.
        const int32 Added = Output->AddItem(Result, Definition->OutputQuantity);
        if (Added != Definition->OutputQuantity)
        {
            Output->RemoveItem(Definition->OutputItem, Added);
            return;
        }
        Input->RemoveItem(Definition->InputItem, Definition->InputQuantity);
        if (Definition->OutputItem == PlateId) Factory->PlatesProduced += Added;
        ProgressSeconds = 0;
    }
}

void AFactoryBuilding::UpdateCargo(AFactoryDemoWorld* Factory)
{
    if (!Definition || Definition->Kind != EFactoryBuildingKind::Belt || Input->GetTotal() == 0)
    {
        Cargo->SetVisibility(false);
        return;
    }
    for (const auto& Pair : Input->Items)
    {
        UFactoryResourceDefinition* Item = Factory->Resource(Pair.Key);
        if (!Item || !Item->PickupMesh) continue;
        Cargo->SetStaticMesh(Item->PickupMesh);
        Cargo->SetRelativeScale3D(Item->CargoScale());
        PlaceCargo(ProgressSeconds / TravelSeconds());
        Cargo->SetVisibility(true);
        break;
    }
}

AFactoryDemoWorld::AFactoryDemoWorld()
{
    PrimaryActorTick.bCanEverTick = true;
    PrimaryActorTick.TickGroup = TG_PostPhysics;
    RootComponent = CreateDefaultSubobject<USceneComponent>(TEXT("Root"));
}

UFactoryResourceDefinition* AFactoryDemoWorld::Resource(FName Id) const
{
    for (UFactoryResourceDefinition* Item : Resources) if (Item && Item->ItemId == Id) return Item;
    return nullptr;
}

TArray<AFactoryBuilding*> AFactoryDemoWorld::Buildings() const
{
    TArray<AFactoryBuilding*> Result;
    for (TActorIterator<AFactoryBuilding> It(GetWorld()); It; ++It) if (IsValid(*It) && It->Definition) Result.Add(*It);
    Result.Sort([](const AFactoryBuilding& A, const AFactoryBuilding& B) { return A.PersistentId.LexicalLess(B.PersistentId); });
    return Result;
}

int32 AFactoryDemoWorld::StoredPlates() const
{
    int32 Total = 0;
    for (const auto* Building : Buildings()) if (Building->Definition->Kind == EFactoryBuildingKind::Storage) Total += Building->Input->GetQuantity(PlateId);
    return Total;
}

bool AFactoryDemoWorld::GoalComplete() const { return StoredPlates() >= 20 && PlatesDelivered >= 20; }

FString AFactoryDemoWorld::SiteStageName(int32 Stage) const
{
    switch (Stage)
    {
    case 1: return TEXT("Taller");
    case 2: return TEXT("Estación de carga");
    case 3: return TEXT("Sector de expansión");
    default: return TEXT("Patio inicial");
    }
}

int32 AFactoryDemoWorld::SiteNextTarget() const
{
    return SiteStage == 0 ? 5 : SiteStage == 1 ? 10 : SiteStage == 2 ? 20 : 0;
}

int32 AFactoryDemoWorld::SiteCurrentProgress() const
{
    return SiteStage == 0 ? PlatesProduced : PlatesDelivered;
}

void AFactoryDemoWorld::StepSiteProgress(float DeltaSeconds)
{
    if (!bEnableSiteProgress || SiteStage >= 3) return;
    if (SiteTransitionRemaining > 0)
    {
        SiteTransitionRemaining = FMath::Max(0.0f, SiteTransitionRemaining - DeltaSeconds);
        if (SiteTransitionRemaining < KINDA_SMALL_NUMBER)
        {
            SiteTransitionRemaining = 0;
            ++SiteStage;
        }
    }
    else if (SiteCurrentProgress() >= SiteNextTarget())
    {
        // Sequential reveals: progress never depends on spending or keeping plates.
        SiteTransitionRemaining = 2.0f;
    }
}

FVector AFactoryDemoWorld::Snap(FVector Position) const
{
    return FVector(FMath::GridSnap(Position.X, GridSize), FMath::GridSnap(Position.Y, GridSize), FloorZ);
}

FString AFactoryDemoWorld::PlacementProblem(FVector Position, const AActor* Ignore) const
{
    const float Radius = GridSize / 2 - 5;
    const auto Inside = [&](FVector2D Min, FVector2D Max)
    {
        return Position.X - Radius >= Min.X && Position.X + Radius <= Max.X && Position.Y - Radius >= Min.Y && Position.Y + Radius <= Max.Y;
    };
    const bool bExpansion = bEnableSiteProgress && (Inside(ExpansionMin, ExpansionMax) || Inside(ConnectorMin, ConnectorMax));
    if (!Inside(AreaMin, AreaMax) && bExpansion && SiteStage < 3)
        return TEXT("Sector cerrado: entregá 20 placas por cinta y completá la expansión");
    if (!Inside(AreaMin, AreaMax) && !(bExpansion && SiteStage >= 3))
        return TEXT("Fuera del patio de construcción");
    FCollisionQueryParams Params(SCENE_QUERY_STAT(FactoryPlacement), false);
    if (Ignore) Params.AddIgnoredActor(Ignore);
    // Resource piles have no blocking collision, but their space is still occupied.
    for (TActorIterator<AFactoryResourcePile> It(GetWorld()); It; ++It)
        if (It->Amount > 0 && FVector::DistSquared2D(Position, It->GetActorLocation()) < FMath::Square(Radius + 45)) return TEXT("Hay chatarra en ese espacio");
    if (GetWorld()->OverlapBlockingTestByChannel(Position + FVector(0, 0, 82), FQuat::Identity, ECC_Pawn, FCollisionShape::MakeBox(FVector(Radius, Radius, 75)), Params))
        return TEXT("Espacio ocupado por un obstáculo, máquina o robot");
    for (const FVector2D Offset : {FVector2D(-Radius, -Radius), FVector2D(Radius, -Radius), FVector2D(-Radius, Radius), FVector2D(Radius, Radius), FVector2D(0, 0)})
    {
        FHitResult Hit;
        const FVector Point = Position + FVector(Offset.X, Offset.Y, 0);
        if (!GetWorld()->LineTraceSingleByChannel(Hit, Point + FVector(0, 0, 6), Point - FVector(0, 0, 30), ECC_Visibility, Params)
            || Hit.ImpactNormal.Z < .9 || FMath::Abs(Hit.ImpactPoint.Z - (FloorZ - 4)) > 8)
            return TEXT("Hace falta un suelo plano y continuo");
    }
    return FString();
}

AFactoryBuilding* AFactoryDemoWorld::Receiver(const AFactoryBuilding* From, const TArray<AFactoryBuilding*>& All) const
{
    // The piece whose input edge is right at From's output edge (belts may be stretched, tilted, raised or be
    // corners, so the edges are compared, not the grid cells). On the grid this is the next cell, facing the same way.
    const FVector Out = From->OutputPoint();
    for (AFactoryBuilding* To : All)
    {
        if (To == From) continue;
        if (From->Definition->Kind != EFactoryBuildingKind::Belt && To->Definition->Kind != EFactoryBuildingKind::Belt) continue;
        const FVector In = To->InputPoint();
        if (FVector::DistSquared2D(Out, In) > FMath::Square(50.0f) || FMath::Abs(Out.Z - In.Z) > 60.0f) continue;
        return To;
    }
    return nullptr;
}

void AFactoryDemoWorld::Step(float DeltaSeconds)
{
    const auto All = Buildings();
    for (AFactoryBuilding* Building : All)
    {
        Building->bConnected = Receiver(Building, All) != nullptr || Building->bFeedsProcess;
        Building->Simulate(DeltaSeconds, this);
    }
    struct FOffer { AFactoryBuilding* From; AFactoryBuilding* To; FName Item; };
    TArray<FOffer> Offers;
    // Snapshot offers first. Cargo received this step cannot travel another cell in it.
    for (AFactoryBuilding* From : All)
    {
        if (From->Definition->Kind == EFactoryBuildingKind::Belt && From->ProgressSeconds + KINDA_SMALL_NUMBER < From->TravelSeconds()) continue;
        AFactoryBuilding* To = Receiver(From, All);
        if (!To) continue;
        TArray<FName> Keys;
        From->Supply()->Items.GetKeys(Keys);
        Keys.Sort(FNameLexicalLess());
        for (FName Item : Keys) if (To->CanAccept(Item) && From->Supply()->GetQuantity(Item) > 0)
        {
            Offers.Add({From, To, Item});
            break;
        }
    }
    for (const FOffer& Offer : Offers)
    {
        if (!Offer.To->CanAccept(Offer.Item) || Offer.From->Supply()->GetQuantity(Offer.Item) < 1) continue;
        if (Offer.To->Input->AddItem(Resource(Offer.Item), 1) != 1) continue;
        Offer.From->Supply()->RemoveItem(Offer.Item, 1);
        // Seen falling into the machine (its hopper) from where it was handed over.
        if (Offer.To->Definition->Kind != EFactoryBuildingKind::Belt)
            if (const UFactoryResourceDefinition* Item = Resource(Offer.Item)) Offer.To->StartFall(Item, Offer.From->OutputPoint());
        if (Offer.From->Definition->Kind == EFactoryBuildingKind::Belt)
        {
            Offer.From->ProgressSeconds = 0;
            if (Offer.Item == PlateId && Offer.To->Definition->Kind == EFactoryBuildingKind::Storage) ++PlatesDelivered;
        }
    }
    for (AFactoryBuilding* Building : All) Building->UpdateCargo(this);
    StepSiteProgress(DeltaSeconds);
}

void AFactoryDemoWorld::Tick(float DeltaSeconds)
{
    Super::Tick(DeltaSeconds);
    Accumulator += DeltaSeconds;
    // Preserve elapsed time across slow frames without a long, blocking catch-up loop.
    int32 Steps = 0;
    while (Accumulator >= .1f && Steps++ < 20) { Accumulator -= .1f; Step(.1f); }
}

bool AFactoryDemoWorld::SaveFactory(APawn* Player)
{
    auto* Inventory = Player ? Player->FindComponentByClass<UFactoryInventoryComponent>() : nullptr;
    if (!Inventory) return false;
    auto* Data = Cast<UFactoryDemoSave>(UGameplayStatics::CreateSaveGameObject(UFactoryDemoSave::StaticClass()));
    Data->Inventory = Inventory->Items;
    Data->PlayerPosition = Player->GetActorLocation();
    Data->PlatesProduced = PlatesProduced;
    Data->PlatesDelivered = PlatesDelivered;
    Data->SiteStage = SiteStage;
    Data->SiteTransitionRemaining = SiteTransitionRemaining;
    for (const AFactoryBuilding* Building : Buildings())
    {
        FFactorySavedBuilding Saved;
        Saved.Id = Building->PersistentId;
        Saved.DefinitionId = Building->Definition->BuildingId;
        Saved.Position = Building->GetActorLocation();
        Saved.Yaw = Building->GetActorRotation().Yaw;
        Saved.Rotation = Building->GetActorRotation();
        Saved.Scale = Building->GetActorScale3D();
        Saved.Elevation = Building->Elevation;
        Saved.Slope = Building->Slope;
        Saved.PaidScrap = Building->PaidScrap;
        Saved.StorageItem = Building->StorageItem;
        Saved.Input = Building->Input->Items;
        Saved.Output = Building->Output->Items;
        Saved.ProgressSeconds = Building->ProgressSeconds;
        Data->Buildings.Add(Saved);
    }
    for (TActorIterator<AFactoryResourcePile> It(GetWorld()); It; ++It) Data->Piles.Add(It->PersistentId, It->Amount);
    return UGameplayStatics::SaveGameToSlot(Data, SaveSlot, 0);
}

bool AFactoryDemoWorld::LoadFactory(APawn* Player)
{
    auto* Inventory = Player ? Player->FindComponentByClass<UFactoryInventoryComponent>() : nullptr;
    if (!Inventory) return false;
    const auto* Data = Cast<UFactoryDemoSave>(UGameplayStatics::LoadGameFromSlot(SaveSlot, 0));
    if (!Data || Data->Version < 1 || Data->Version > 4) return false;
    if (Data->PlatesProduced < 0 || Data->PlatesDelivered < 0) return false;
    const int32 RestoredStage = Data->Version >= 2 ? Data->SiteStage : 0;
    const float RestoredRemaining = Data->Version >= 2 ? Data->SiteTransitionRemaining : 0.0f;
    // Validate before replacing actors. Version 1 saves replay earned reveals.
    if (RestoredStage < 0 || RestoredStage > 3 || !FMath::IsFinite(RestoredRemaining)
        || RestoredRemaining < 0 || RestoredRemaining > 2 || (RestoredStage == 3 && RestoredRemaining > 0)
        || (RestoredStage >= 1 && Data->PlatesProduced < 5)
        || (RestoredStage >= 2 && Data->PlatesDelivered < 10)
        || (RestoredStage >= 3 && Data->PlatesDelivered < 20)) return false;
    if (RestoredRemaining > 0 && (RestoredStage == 0 ? Data->PlatesProduced < 5 : Data->PlatesDelivered < (RestoredStage == 1 ? 10 : 20))) return false;
    TMap<FName, UFactoryBuildingDefinition*> Definitions;
    for (UFactoryBuildingDefinition* Entry : Catalog) if (Entry) Definitions.Add(Entry->BuildingId, Entry);
    auto ValidItems = [&](const TMap<FName, int32>& Items, int32 Capacity)
    {
        int64 Total = 0;
        for (const auto& Pair : Items) { if (!Resource(Pair.Key) || Pair.Value < 0) return false; Total += Pair.Value; }
        return Total <= Capacity;
    };
    if (!ValidItems(Data->Inventory, Inventory->Capacity) || Data->PlayerPosition.ContainsNaN()) return false;
    TSet<FName> Ids;
    for (const auto& Saved : Data->Buildings)
    {
        auto* Definition = Definitions.FindRef(Saved.DefinitionId);
        if (!Definition || !Resource(Saved.StorageItem) || Saved.Id.IsNone() || Ids.Contains(Saved.Id) || Saved.Position.ContainsNaN()
            || !FMath::IsFinite(Saved.Yaw) || !FMath::IsFinite(Saved.ProgressSeconds) || Saved.ProgressSeconds < 0
            || Saved.Rotation.ContainsNaN() || Saved.Scale.ContainsNaN() || Saved.Scale.GetAbsMin() < 0.01f
            || !FMath::IsFinite(Saved.Elevation) || Saved.Elevation < 0 || !FMath::IsFinite(Saved.Slope)
            || Saved.PaidScrap < 0 || !ValidItems(Saved.Input, Definition->Kind == EFactoryBuildingKind::Belt ? 1 : Definition->Capacity)
            || !ValidItems(Saved.Output, Definition->Kind == EFactoryBuildingKind::Processor ? Definition->Capacity : 0)) return false;
        Ids.Add(Saved.Id);
    }
    for (const auto& Pair : Data->Piles) if (Pair.Value < 0) return false;
    // All definitions and amounts were validated before replacing the current world.
    for (AFactoryBuilding* Building : Buildings()) Building->Destroy();
    for (const auto& Saved : Data->Buildings)
    {
        FActorSpawnParameters Params;
        Params.SpawnCollisionHandlingOverride = ESpawnActorCollisionHandlingMethod::AlwaysSpawn;
        auto* Building = GetWorld()->SpawnActor<AFactoryBuilding>(Saved.Position, Data->Version >= 3 ? Saved.Rotation : FRotator(0, Saved.Yaw, 0), Params);
        if (Data->Version >= 3) Building->SetActorScale3D(Saved.Scale);
        Building->Definition = Definitions[Saved.DefinitionId];
        Building->PersistentId = Saved.Id;
        Building->PaidScrap = Saved.PaidScrap;
        Building->StorageItem = Saved.StorageItem;
        if (Data->Version >= 4) { Building->Elevation = Saved.Elevation; Building->Slope = Saved.Slope; }
        Building->RefreshVisuals();
        RestoreInventory(Building->Input, Saved.Input, this);
        RestoreInventory(Building->Output, Saved.Output, this);
        Building->ProgressSeconds = Saved.ProgressSeconds;
        Building->UpdateCargo(this);
    }
    for (TActorIterator<AFactoryResourcePile> It(GetWorld()); It; ++It)
        if (const int32* Amount = Data->Piles.Find(It->PersistentId)) { It->Amount = *Amount; It->RefreshVisuals(); }
    RestoreInventory(Inventory, Data->Inventory, this);
    Player->SetActorLocation(Data->PlayerPosition, false, nullptr, ETeleportType::TeleportPhysics);
    PlatesProduced = Data->PlatesProduced;
    PlatesDelivered = Data->PlatesDelivered;
    SiteStage = RestoredStage;
    SiteTransitionRemaining = RestoredRemaining;
    Accumulator = 0;
    return true;
}

UFactoryDemoComponent::UFactoryDemoComponent()
{
    PrimaryComponentTick.bCanEverTick = true;
}

void UFactoryDemoComponent::BeginPlay()
{
    Super::BeginPlay();
    for (TActorIterator<AFactoryDemoWorld> It(GetWorld()); It; ++It) { Factory = *It; break; }
    if (!Factory) return;
    Controls = NewObject<UInputComponent>(GetOwner(), TEXT("FactoryDemoInput"));
    Controls->RegisterComponent();
    Controls->BindKey(EKeys::B, IE_Pressed, this, &UFactoryDemoComponent::ToggleBuild);
    Controls->BindKey(EKeys::R, IE_Pressed, this, &UFactoryDemoComponent::RotateBuilding);
    Controls->BindKey(EKeys::One, IE_Pressed, this, &UFactoryDemoComponent::One);
    Controls->BindKey(EKeys::Two, IE_Pressed, this, &UFactoryDemoComponent::Two);
    Controls->BindKey(EKeys::Three, IE_Pressed, this, &UFactoryDemoComponent::Three);
    Controls->BindKey(EKeys::Four, IE_Pressed, this, &UFactoryDemoComponent::Four);
    Controls->BindKey(EKeys::Five, IE_Pressed, this, &UFactoryDemoComponent::Five);
    Controls->BindKey(EKeys::LeftMouseButton, IE_Pressed, this, &UFactoryDemoComponent::Click);
    Controls->BindKey(EKeys::RightMouseButton, IE_Released, this, &UFactoryDemoComponent::RightRelease);
    Controls->BindKey(EKeys::F, IE_Pressed, this, &UFactoryDemoComponent::Withdraw);
    Controls->BindKey(EKeys::G, IE_Pressed, this, &UFactoryDemoComponent::CycleStorageItem);
    Controls->BindKey(EKeys::X, IE_Pressed, this, &UFactoryDemoComponent::DismantleKey);
    Controls->BindKey(EKeys::F5, IE_Pressed, this, &UFactoryDemoComponent::Save);
    Controls->BindKey(EKeys::F9, IE_Pressed, this, &UFactoryDemoComponent::Load);
    if (APlayerController* Player = Controller(this))
    {
        Player->bShowMouseCursor = true;
        FInputModeGameAndUI Mode;
        Mode.SetHideCursorDuringCapture(false);
        Mode.SetLockMouseToViewportBehavior(EMouseLockMode::LockInFullscreen);
        Player->SetInputMode(Mode);
    }
    Tell(TEXT("Recogé chatarra con E. Luego B y 4 para conectar las tres cintas."));
    NotificationUntil = GetWorld()->GetTimeSeconds() + 10;
}

void UFactoryDemoComponent::EndPlay(const EEndPlayReason::Type Reason)
{
    if (Preview) Preview->Destroy();
    if (Controls) Controls->DestroyComponent();
    Super::EndPlay(Reason);
}

UFactoryInventoryComponent* UFactoryDemoComponent::Inventory() const { return GetOwner()->FindComponentByClass<UFactoryInventoryComponent>(); }
void UFactoryDemoComponent::Tell(const FString& Message) { Notification = Message; NotificationUntil = GetWorld()->GetTimeSeconds() + 4; }
void UFactoryDemoComponent::ToggleBuild() { if (bBuilding) CancelBuild(); else SelectBuilding(SelectedIndex); }
// Outside build mode the number keys pick a floor on an open elevator panel.
static void NumberKey(const UActorComponent* Component, int32 Number)
{
    if (AFactoryElevator* Elevator = AFactoryElevator::FindOpenMenu(Component->GetWorld())) Elevator->SelectFloor(Number);
}
void UFactoryDemoComponent::One() { if (bBuilding) SelectBuilding(0); else NumberKey(this, 1); }
void UFactoryDemoComponent::Two() { if (bBuilding) SelectBuilding(1); else NumberKey(this, 2); }
void UFactoryDemoComponent::Three() { if (bBuilding) SelectBuilding(2); else NumberKey(this, 3); }
void UFactoryDemoComponent::Four() { if (bBuilding) SelectBuilding(3); else NumberKey(this, 4); }
void UFactoryDemoComponent::Five() { if (bBuilding) SelectBuilding(4); else NumberKey(this, 5); }
void UFactoryDemoComponent::DismantleKey() { Dismantle(); }

void UFactoryDemoComponent::RightRelease()
{
    // Mouse axes use the project's 0.07 sensitivity: 0.5 is a few pixels of movement.
    const auto* Camera = GetOwner()->FindComponentByClass<UFactoryCameraComponent>();
    if (!Camera || Camera->RightDragSincePress < 0.5f) CancelBuild();
}

void UFactoryDemoComponent::SelectBuilding(int32 Index)
{
    if (!Factory || !Factory->Catalog.IsValidIndex(Index)) return;
    SelectedIndex = Index;
    bBuilding = true;
    if (auto* Gathering = GetOwner()->FindComponentByClass<UFactoryGatheringComponent>()) Gathering->bInventoryOpen = false;
    if (!Preview)
    {
        Preview = GetWorld()->SpawnActor<AActor>();
        auto* Root = NewObject<USceneComponent>(Preview, TEXT("PreviewRoot"));
        Preview->SetRootComponent(Root);
        Root->RegisterComponent();
        PreviewMesh = NewObject<UStaticMeshComponent>(Preview, TEXT("PreviewMesh"));
        PreviewMesh->SetupAttachment(Root);
        PreviewMesh->SetCollisionProfileName(TEXT("NoCollision"));
        PreviewMesh->SetCastShadow(false);
        PreviewMesh->RegisterComponent();
        PreviewBase = NewObject<UStaticMeshComponent>(Preview, TEXT("PreviewBase"));
        PreviewBase->SetupAttachment(Root);
        PreviewBase->SetCollisionProfileName(TEXT("NoCollision"));
        PreviewBase->SetCastShadow(false);
        PreviewBase->RegisterComponent();
        PreviewPad = NewObject<UStaticMeshComponent>(Preview, TEXT("PreviewPad"));
        PreviewPad->SetupAttachment(Root);
        PreviewPad->SetStaticMesh(LoadObject<UStaticMesh>(nullptr, TEXT("/Engine/BasicShapes/Cube.Cube")));
        PreviewPad->SetRelativeScale3D(FVector(1.96, 1.96, .02));
        PreviewPad->SetRelativeLocation(FVector(0, 0, .5));
        PreviewPad->SetCollisionProfileName(TEXT("NoCollision"));
        PreviewPad->SetCastShadow(false);
        PreviewPad->RegisterComponent();
    }
    auto* Definition = Factory->Catalog[Index].Get();
    PreviewMesh->SetStaticMesh(Definition->Mesh);
    PreviewMesh->SetRelativeScale3D(Definition->MeshScale);
    const float Up = FMath::Max(0.0f, Definition->BaseHeight);
    UStaticMesh* Platform = Up > 0 ? Definition->BaseMesh.Get() : nullptr;
    PreviewBase->SetStaticMesh(Platform);
    if (Platform) PreviewBase->SetRelativeScale3D(FVector(1, 1, Up / FMath::Max(Platform->GetBoundingBox().GetSize().Z, 1.0)));
    PreviewMesh->SetRelativeLocation(Definition->MeshOffset + FVector(0, 0, Up));
    PreviewMesh->SetRelativeRotation(FRotator(0, Definition->MeshYaw, 0));
    Preview->SetActorHiddenInGame(false);
    UpdatePreview();
}

void UFactoryDemoComponent::RotateBuilding() { if (bBuilding) { QuarterTurns = (QuarterTurns + 1) % 4; UpdatePreview(); } }
void UFactoryDemoComponent::CancelBuild() { bBuilding = false; bPreviewValid = false; if (Preview) Preview->SetActorHiddenInGame(true); }

void UFactoryDemoComponent::UpdatePreview()
{
    APlayerController* Player = Controller(this);
    if (!Factory || !bBuilding || !Preview || !Player) return;
    FVector Origin, Direction;
    const bool bRay = Player->DeprojectMousePositionToWorld(Origin, Direction) && Direction.Z < -.001;
    bPreviewValid = false;
    if (!bRay) { Preview->SetActorHiddenInGame(true); return; }
    const double Distance = (Factory->FloorZ - Origin.Z) / Direction.Z;
    if (Distance < 0) return;
    PreviewPosition = Factory->Snap(Origin + Direction * Distance);
    Preview->SetActorLocationAndRotation(PreviewPosition, FRotator(0, QuarterTurns * 90, 0));
    Preview->SetActorHiddenInGame(false);
    PlacementMessage = Factory->PlacementProblem(PreviewPosition, Preview);
    const auto* Definition = Factory->Catalog[SelectedIndex].Get();
    if (PlacementMessage.IsEmpty() && (!Inventory() || Inventory()->GetQuantity(ScrapId) < Definition->ScrapCost)) PlacementMessage = TEXT("Falta chatarra para construir");
    bPreviewValid = PlacementMessage.IsEmpty();
    if (bPreviewValid) PlacementMessage = TEXT("Clic para construir · R gira · clic derecho cancela");
    auto* Material = bPreviewValid ? Factory->ValidMaterial.Get() : Factory->InvalidMaterial.Get();
    PreviewPad->SetMaterial(0, Material);
    for (int32 Index = 0; Index < PreviewMesh->GetNumMaterials(); ++Index) PreviewMesh->SetMaterial(Index, Material);
    for (int32 Index = 0; Index < PreviewBase->GetNumMaterials(); ++Index) PreviewBase->SetMaterial(Index, Material);
}

AFactoryBuilding* UFactoryDemoComponent::BuildAt(int32 Index, FVector Position, int32 Turns)
{
    if (!Factory || !Factory->Catalog.IsValidIndex(Index) || !Inventory()) return nullptr;
    Position = Factory->Snap(Position);
    const FString Problem = Factory->PlacementProblem(Position, Preview);
    if (!Problem.IsEmpty()) { Tell(Problem); return nullptr; }
    auto* Definition = Factory->Catalog[Index].Get();
    if (Inventory()->GetQuantity(ScrapId) < Definition->ScrapCost) { Tell(TEXT("No alcanza la chatarra")); return nullptr; }
    FActorSpawnParameters Params;
    Params.SpawnCollisionHandlingOverride = ESpawnActorCollisionHandlingMethod::AlwaysSpawn;
    auto* Building = GetWorld()->SpawnActor<AFactoryBuilding>(Position, FRotator(0, ((Turns % 4 + 4) % 4) * 90, 0), Params);
    if (!Building) return nullptr;
    Building->Definition = Definition;
    Building->PersistentId = FName(*FGuid::NewGuid().ToString(EGuidFormats::Digits));
    Building->PaidScrap = Definition->ScrapCost;
    Building->RefreshVisuals();
    Inventory()->RemoveItem(ScrapId, Definition->ScrapCost);
    Tell(Definition->DisplayName.ToString() + TEXT(" construida"));
    return Building;
}

void UFactoryDemoComponent::Click()
{
    APlayerController* Player = Controller(this);
    if (!bBuilding)
    {
        // A click on the open info panel or elevator panel.
        float MouseX = 0, MouseY = 0;
        if (Player && Player->GetMousePosition(MouseX, MouseY))
            if (auto* HUD = Cast<AFactoryDemoHUD>(Player->GetHUD()))
                if (HUD->ClickMoneyBar(MouseX, MouseY) || HUD->ClickInfoPanel(MouseX, MouseY) || HUD->ClickEvents(MouseX, MouseY) || HUD->ClickElevator(MouseX, MouseY)
                    || HUD->ClickBooth(MouseX, MouseY)) return;
        // Outside build mode a click can open the detail of a full dispatch belt's red sign, or the barrier
        // booth's panel (a click anywhere else closes that one).
        // A click on a character makes the camera follow it.
        auto* Camera = GetOwner()->FindComponentByClass<UFactoryCameraComponent>();
        if (Camera && Player && Player->GetMousePosition(MouseX, MouseY) && Camera->FollowAtScreen(FVector2D(MouseX, MouseY))) return;
        FHitResult Hit;
        auto* HUD = Player ? Cast<AFactoryDemoHUD>(Player->GetHUD()) : nullptr;
        if (!Player || !Player->GetHitResultUnderCursor(ECC_Visibility, false, Hit)) { if (HUD) HUD->OpenBooth(nullptr); return; }
        if (HUD) HUD->OpenBooth(Cast<AFactoryGateBarrier>(Hit.GetActor()));
        for (TActorIterator<AFactoryDispatchBelt> It(GetWorld()); It; ++It)
            if (It->ClickSign(Hit.GetComponent()))
            {
                for (TActorIterator<AFactoryDispatchBelt> Other(GetWorld()); Other; ++Other)
                    if (*Other != *It) Other->bDetailOpen = false;
                return;
            }
        // A click on anything else (floor, walls) lets the camera go free.
        if (Camera && Camera->bStartFree && !Cast<AFactoryGateBarrier>(Hit.GetActor())) Camera->StopFollowing();
        return;
    }
    if (!Factory) return;
    float X = 0, Y = 0;
    if (Player && Player->GetMousePosition(X, Y))
        if (auto* HUD = Cast<AFactoryDemoHUD>(Player->GetHUD())) if (HUD->ClickCatalog(X, Y)) return;
    UpdatePreview();
    if (bPreviewValid) BuildAt(SelectedIndex, PreviewPosition, QuarterTurns);
    else Tell(PlacementMessage);
}

void UFactoryDemoComponent::RefreshFocus()
{
    FocusedBuilding = nullptr;
    if (!Factory || bBuilding) return;
    double Closest = FMath::Square(260.0);
    const FVector Origin = GetOwner()->GetActorLocation();
    for (AFactoryBuilding* Building : Factory->Buildings())
    {
        const double Distance = FVector::DistSquared2D(Origin, Building->GetActorLocation());
        if (Distance >= Closest) continue;
        FHitResult Hit;
        FCollisionQueryParams Params(SCENE_QUERY_STAT(FactoryInteraction), false, GetOwner());
        const bool bHit = GetWorld()->LineTraceSingleByChannel(Hit, Origin + FVector(0, 0, 30), Building->GetActorLocation() + FVector(0, 0, 55), ECC_Visibility, Params);
        if (bHit && Hit.GetActor() != Building) continue;
        FocusedBuilding = Building;
        Closest = Distance;
    }
}

bool UFactoryDemoComponent::InteractMachine()
{
    if (!Factory) return false;
    if (bBuilding) return true;
    RefreshFocus();
    if (!FocusedBuilding || !Inventory()) return false;
    if (auto* Gathering = GetOwner()->FindComponentByClass<UFactoryGatheringComponent>())
    {
        Gathering->RefreshTarget();
        if (Gathering->FocusedPile && FVector::DistSquared2D(GetOwner()->GetActorLocation(), Gathering->FocusedPile->GetActorLocation()) < FVector::DistSquared2D(GetOwner()->GetActorLocation(), FocusedBuilding->GetActorLocation())) return false;
    }
    int32 Total = 0;
    for (UFactoryResourceDefinition* Item : Factory->Resources)
    {
        if (!Item || !FocusedBuilding->CanAccept(Item->ItemId)) continue;
        const int32 Added = FocusedBuilding->Input->AddItem(Item, Inventory()->GetQuantity(Item->ItemId));
        Inventory()->RemoveItem(Item->ItemId, Added);
        Total += Added;
    }
    Tell(Total > 0 ? FString::Printf(TEXT("Cargaste %d unidades"), Total) : TEXT("Sin material compatible o entrada llena · F retira"));
    return true;
}

void UFactoryDemoComponent::Withdraw()
{
    RefreshFocus();
    if (!FocusedBuilding || !Inventory()) return;
    auto* Source = FocusedBuilding->Supply();
    int32 Total = 0;
    for (UFactoryResourceDefinition* Item : Factory->Resources)
    {
        if (!Item) continue;
        const int32 Added = Inventory()->AddItem(Item, Source->GetQuantity(Item->ItemId));
        Source->RemoveItem(Item->ItemId, Added);
        Total += Added;
    }
    Tell(Total > 0 ? FString::Printf(TEXT("Retiraste %d unidades"), Total) : Inventory()->GetFreeSpace() == 0 ? TEXT("Inventario lleno") : TEXT("Todavía no hay material para retirar"));
}

void UFactoryDemoComponent::CycleStorageItem()
{
    RefreshFocus();
    if (!FocusedBuilding || FocusedBuilding->Definition->Kind != EFactoryBuildingKind::Storage) return;
    if (FocusedBuilding->StoredTotal() > 0) { Tell(TEXT("Vaciá el depósito antes de cambiar su recurso")); return; }
    for (int32 Index = 0; Index < Factory->Resources.Num(); ++Index)
        if (Factory->Resources[Index] && Factory->Resources[Index]->ItemId == FocusedBuilding->StorageItem)
        {
            auto* Next = Factory->Resources[(Index+1)%Factory->Resources.Num()].Get();
            if (Next) { FocusedBuilding->StorageItem = Next->ItemId; Tell(TEXT("Depósito configurado para ") + Next->DisplayName.ToString()); }
            return;
        }
}

bool UFactoryDemoComponent::Dismantle()
{
    RefreshFocus();
    if (!FocusedBuilding || !Inventory()) return false;
    const int32 Required = FocusedBuilding->PaidScrap + FocusedBuilding->StoredTotal();
    if (Inventory()->GetFreeSpace() < Required) { Tell(TEXT("Liberá espacio: se devuelve el costo y todo el contenido")); return false; }
    for (UFactoryResourceDefinition* Item : Factory->Resources)
        if (Item) Inventory()->AddItem(Item, FocusedBuilding->Input->GetQuantity(Item->ItemId) + FocusedBuilding->Output->GetQuantity(Item->ItemId));
    Inventory()->AddItem(Factory->Resource(ScrapId), FocusedBuilding->PaidScrap);
    FocusedBuilding->Destroy();
    FocusedBuilding = nullptr;
    Tell(TEXT("Desmontado: costo y materiales recuperados"));
    return true;
}

void UFactoryDemoComponent::Save() { if (Factory) Tell(Factory->SaveFactory(Cast<APawn>(GetOwner())) ? TEXT("Partida guardada · F9 para recuperarla") : TEXT("No se pudo guardar la partida")); }
void UFactoryDemoComponent::Load()
{
    if (!Factory) return;
    CancelBuild();
    FocusedBuilding = nullptr;
    Tell(Factory->LoadFactory(Cast<APawn>(GetOwner())) ? TEXT("Partida cargada") : TEXT("No hay una partida guardada compatible"));
}

bool UFactoryDemoComponent::SetEditorTestCursor(FVector WorldPosition)
{
#if WITH_EDITOR
    if (APlayerController* Player = Controller(this))
    {
        FVector2D Screen;
        if (Player->ProjectWorldLocationToScreen(WorldPosition, Screen)) { Player->SetMouseLocation(FMath::RoundToInt(Screen.X), FMath::RoundToInt(Screen.Y)); return true; }
    }
#endif
    return false;
}

void UFactoryDemoComponent::TickComponent(float DeltaTime, ELevelTick TickType, FActorComponentTickFunction* ThisTickFunction)
{
    Super::TickComponent(DeltaTime, TickType, ThisTickFunction);
    if (!Factory) return;
    RefreshFocus();
    if (bBuilding)
    {
        UpdatePreview();
        const float G = Factory->GridSize;
        for (float X = -4.5f * G; X <= 4.5f * G; X += G)
            DrawDebugLine(GetWorld(), FVector(X, Factory->AreaMin.Y, Factory->FloorZ + 1), FVector(X, Factory->AreaMax.Y, Factory->FloorZ + 1), FColor(80, 145, 155), false, 0, 0, 1);
        for (float Y = -3.5f * G; Y <= 3.5f * G; Y += G)
            DrawDebugLine(GetWorld(), FVector(Factory->AreaMin.X, Y, Factory->FloorZ + 1), FVector(Factory->AreaMax.X, Y, Factory->FloorZ + 1), FColor(80, 145, 155), false, 0, 0, 1);
        if (Preview) DrawDebugDirectionalArrow(GetWorld(), PreviewPosition + FVector(0, 0, 190) - Preview->GetActorForwardVector() * 50, PreviewPosition + FVector(0, 0, 190) + Preview->GetActorForwardVector() * 70, 30, FColor::Cyan, false, 0, 0, 4);
    }
    for (AFactoryBuilding* Building : Factory->Buildings())
    {
        if (!bBuilding && Building != FocusedBuilding) continue;
        const bool bBelt = Building->Definition->Kind == EFactoryBuildingKind::Belt;
        const FVector Centre = Building->GetActorLocation() + FVector(0, 0, bBelt ? 32 + Building->Lift() : 8);
        const FVector Direction = Building->GetActorForwardVector();
        const FColor Color = Building == FocusedBuilding ? FColor(255, 195, 70) : FColor(40, 210, 195);
        DrawDebugDirectionalArrow(GetWorld(), Centre - Direction * 45, Centre + Direction * 70, 24, Color, false, 0, 0, 3);
        if (Building == FocusedBuilding) DrawDebugBox(GetWorld(), Building->GetActorLocation() + FVector(0, 0, 5), FVector(96, 96, 2), Color, false, 0, 0, 3);
    }
}
