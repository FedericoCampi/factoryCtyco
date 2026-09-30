#include "FactoryLoadingBelt.h"
#include "FactoryBeltSupports.h"
#include "Camera/PlayerCameraManager.h"
#include "Components/InstancedStaticMeshComponent.h"
#include "Components/SplineComponent.h"
#include "Components/StaticMeshComponent.h"
#include "Components/TextRenderComponent.h"
#include "Engine/StaticMesh.h"
#include "Engine/World.h"
#include "EngineUtils.h"
#include "FactoryCarry.h"
#include "FactoryMission.h"
#include "FactoryVehiclePath.h"
#include "GameFramework/Pawn.h"
#include "GameFramework/PlayerController.h"
#include "Materials/MaterialInstanceDynamic.h"
#include "UObject/ConstructorHelpers.h"

AFactoryLoadingBelt::AFactoryLoadingBelt()
{
    PrimaryActorTick.bCanEverTick = true;
    RootComponent = CreateDefaultSubobject<USceneComponent>(TEXT("Root"));
    Belt = CreateDefaultSubobject<UStaticMeshComponent>(TEXT("Belt"));
    Belt->SetupAttachment(RootComponent);
    Belt->SetCollisionProfileName(TEXT("BlockAll"));
    Prompt = CreateDefaultSubobject<UTextRenderComponent>(TEXT("Prompt"));
    Prompt->SetupAttachment(RootComponent);
    Prompt->SetUsingAbsoluteScale(true);   // not stretched with the belt
    Prompt->SetHorizontalAlignment(EHTA_Center);
    Prompt->SetVerticalAlignment(EVRTA_TextCenter);
    Prompt->SetWorldSize(18.0f);
    Prompt->SetTextRenderColor(FColor(46, 232, 199));
    Prompt->SetText(FText::GetEmpty());  // filled in play; empty, nothing shows in the editor
    Prompt->SetCollisionEnabled(ECollisionEnabled::NoCollision);
    Prompt->SetHiddenInGame(true);
    Supports = CreateDefaultSubobject<UInstancedStaticMeshComponent>(TEXT("Supports"));
    Supports->SetupAttachment(RootComponent);
    // Posts stand upright whatever the belt's tilt: their instances are placed in world space.
    Supports->SetUsingAbsoluteLocation(true);
    Supports->SetUsingAbsoluteRotation(true);
    Supports->SetUsingAbsoluteScale(true);
    Supports->SetCollisionProfileName(TEXT("BlockAll"));
    static ConstructorHelpers::FObjectFinder<UStaticMesh> Cube(TEXT("/Engine/BasicShapes/Cube.Cube"));
    if (Cube.Succeeded()) SupportMesh = Cube.Object;
}

FVector AFactoryLoadingBelt::LocalAt(float LocalAlong, float* OutYaw) const
{
    const float D = FMath::Clamp(LocalAlong, 0.0f, Length);
    if (FMath::Abs(TurnDegrees) < 0.5f)
    {
        if (OutYaw) *OutYaw = 0.0f;
        return FVector(D, 0, DeckHeight);
    }
    // Part of a circle: it starts at the origin heading +X and bends towards Sign * Y.
    const float Sign = TurnDegrees > 0.0f ? 1.0f : -1.0f;
    const float Radius = Length / FMath::DegreesToRadians(FMath::Abs(TurnDegrees));
    const float Angle = D / Radius;
    if (OutYaw) *OutYaw = Sign * FMath::RadiansToDegrees(Angle);
    return FVector(Radius * FMath::Sin(Angle), Sign * Radius * (1.0f - FMath::Cos(Angle)), DeckHeight);
}

FVector AFactoryLoadingBelt::WorldAt(float Along) const
{
    return GetActorTransform().TransformPosition(LocalAt(Along / Stretch()));
}

void AFactoryLoadingBelt::OnConstruction(const FTransform& Transform)
{
    Super::OnConstruction(Transform);
    BuildSupports();
}

void AFactoryLoadingBelt::BuildSupports()
{
    UMaterialInterface* Material = SupportMaterial;
    if (!Material)
        if (const int32 Slot = Belt->GetMaterialIndex(TEXT("M_CintaAcero")); Slot != INDEX_NONE) Material = Belt->GetMaterial(Slot);
    // Near each end and every SupportSpacing between them.
    const float Span = WorldLength(), Inset = FMath::Min(25.0f, Span / 2);
    TArray<float> Spots = {Inset};
    const int32 Between = FMath::FloorToInt((Span - 2 * Inset) / SupportSpacing);
    for (int32 I = 1; I <= Between; ++I) Spots.Add(Inset + (Span - 2 * Inset) * I / (Between + 1));
    if (Span - 2 * Inset > 1.0f) Spots.Add(Span - Inset);
    TArray<FVector> Tops;
    for (const float Along : Spots)
    {
        // The belt's underside there (local Z 0: the foot of its own legs).
        FVector Local = LocalAt(Along / Stretch());
        Local.Z = 0.0f;
        Tops.Add(GetActorTransform().TransformPosition(Local));
    }
    FactoryPlaceSupports(Supports, this, SupportMesh, Material, Tops, SupportWidth, SupportMinGap);
}

void AFactoryLoadingBelt::BeginPlay()
{
    Super::BeginPlay();
    const int32 Slot = Belt->GetMaterialIndex(TEXT("M_Rodillo"));
    if (Slot != INDEX_NONE) RollerMaterial = Belt->CreateAndSetMaterialInstanceDynamic(Slot);
    if (RollerMaterial) RollerMaterial->SetScalarParameterValue(TEXT("Velocidad"), 0.0f);
    RefreshLinks();
    BuildSupports();
}

void AFactoryLoadingBelt::RefreshLinks()
{
    // The belts it feeds: the one picked by hand, or every one whose load end is right at this far end.
    Outputs.Reset();
    if (NextBelt && NextBelt != this) Outputs.Add(NextBelt);
    else
        for (TActorIterator<AFactoryLoadingBelt> It(GetWorld()); It; ++It)
            if (*It != this && !UFactoryUnlockSubsystem::IsLocked(*It)
                && FVector::DistSquared2D(GetDeliveryPoint(), It->GetLoadPoint()) < FMath::Square(LinkReach)
                && FMath::Abs(GetDeliveryPoint().Z - It->GetLoadPoint().Z) < 60.0f)
                Outputs.Add(*It);
}

float AFactoryLoadingBelt::Stretch() const
{
    return FMath::Max(GetActorScale3D().X, 0.01f);
}

FVector AFactoryLoadingBelt::GetDeliveryPoint() const
{
    return GetActorTransform().TransformPosition(LocalAt(Length));
}

FVector AFactoryLoadingBelt::GetLoadPoint() const
{
    return GetActorTransform().TransformPosition(LocalAt(0.0f));
}

TArray<AFactoryLoadingBelt*> AFactoryLoadingBelt::GetOutputs() const
{
    TArray<AFactoryLoadingBelt*> Result;
    for (const TObjectPtr<AFactoryLoadingBelt>& Output : Outputs) if (Output) Result.Add(Output.Get());
    return Result;
}

int32 AFactoryLoadingBelt::BoxesAhead() const
{
    TSet<const AFactoryLoadingBelt*> Seen;
    return BoxesAhead(Seen);
}

int32 AFactoryLoadingBelt::BoxesAhead(TSet<const AFactoryLoadingBelt*>& Seen) const
{
    if (Seen.Contains(this)) return 0;   // belts that loop back are counted once
    Seen.Add(this);
    int32 Count = Boxes.Num();
    for (const TObjectPtr<AFactoryLoadingBelt>& Output : Outputs) if (Output) Count += Output->BoxesAhead(Seen);
    return Count;
}

bool AFactoryLoadingBelt::HasWaitingTruck() const
{
    TSet<const AFactoryLoadingBelt*> Seen;
    return HasWaitingTruck(BoxesAhead(), Seen);
}

bool AFactoryLoadingBelt::HasWaitingTruck(int32 OnTheWay, TSet<const AFactoryLoadingBelt*>& Seen) const
{
    if (Seen.Contains(this)) return false;
    Seen.Add(this);
    if (Outputs.IsEmpty()) return Docked && Docked->FreeCargoSlots() > OnTheWay;
    for (const TObjectPtr<AFactoryLoadingBelt>& Output : Outputs)
        if (Output && Output->HasWaitingTruck(OnTheWay, Seen)) return true;
    return false;
}

float AFactoryLoadingBelt::StopOrder(TSet<const AFactoryLoadingBelt*>& Seen) const
{
    if (Seen.Contains(this)) return -1.0f;
    Seen.Add(this);
    float Order = -1.0f;
    if (Outputs.IsEmpty())
    {
        // Where this last belt meets a truck line, measured along it.
        for (TActorIterator<AFactoryVehiclePath> It(GetWorld()); It; ++It)
            if (const USplineComponent* Line = UFactoryUnlockSubsystem::IsLocked(*It) ? nullptr : It->GetLine())
            {
                const float Key = Line->FindInputKeyClosestToWorldLocation(GetDeliveryPoint());
                if (FVector::Dist2D(GetDeliveryPoint(), Line->GetLocationAtSplineInputKey(Key, ESplineCoordinateSpace::World)) < It->DockReach)
                    Order = FMath::Max(Order, Line->GetDistanceAlongSplineAtSplineInputKey(Key));
            }
        return Order;
    }
    for (const TObjectPtr<AFactoryLoadingBelt>& Output : Outputs)
        if (Output) Order = FMath::Max(Order, Output->StopOrder(Seen));
    return Order;
}

AFactoryLoadingBelt* AFactoryLoadingBelt::ChooseOutput() const
{
    // Branches in order: the one whose stop is furthest along the line (nearest the barrier) first.
    TArray<TPair<float, AFactoryLoadingBelt*>> Ordered;
    for (const TObjectPtr<AFactoryLoadingBelt>& Output : Outputs)
        if (Output)
        {
            TSet<const AFactoryLoadingBelt*> Seen;
            Ordered.Add(TPair<float, AFactoryLoadingBelt*>(Output->StopOrder(Seen), Output.Get()));
        }
    Ordered.Sort([](const TPair<float, AFactoryLoadingBelt*>& A, const TPair<float, AFactoryLoadingBelt*>& B) { return A.Key > B.Key; });
    // The first branch with a truck waiting and room for the box; with none, the first branch. If that branch's
    // row is full at its start the box waits here: it does not jump over a full belt to another one (only a full
    // or missing truck sends it on to the next branch).
    AFactoryLoadingBelt* Pick = Ordered.IsEmpty() ? nullptr : Ordered[0].Value;
    for (const auto& Branch : Ordered)
        if (Branch.Value->HasWaitingTruck()) { Pick = Branch.Value; break; }
    return Pick && Pick->RoomAt(0.0f) ? Pick : nullptr;
}

float AFactoryLoadingBelt::DistanceTo(const AActor* User, float& OutAlong) const
{
    OutAlong = 0.0f;
    if (!User || UFactoryUnlockSubsystem::IsLocked(this)) return TNumericLimits<float>::Max();
    // Closest point on the belt's centre line (straight, curved or tilted), from its load end to its far end,
    // seen from above; the parts far above or below the character (a raised belt) are out of reach.
    const FVector User3 = User->GetActorLocation();
    const FVector2D P(User3);
    const float Span = WorldLength();
    const int32 Steps = FMath::Abs(TurnDegrees) < 0.5f ? 1 : FMath::Clamp(FMath::CeilToInt(Span / 20.0f), 1, 200);
    float Best = TNumericLimits<float>::Max();
    FVector Prev = WorldAt(0.0f);
    for (int32 I = 1; I <= Steps; ++I)
    {
        const float A0 = Span * (I - 1) / Steps, A1 = Span * I / Steps;
        const FVector Next = WorldAt(A1);
        const FVector2D A(Prev), B(Next);
        const float Piece = FVector2D::Distance(A, B);
        const float T = Piece > 0.1f ? FMath::Clamp(FVector2D::DotProduct(P - A, (B - A) / Piece), 0.0f, Piece) : 0.0f;
        const float F = Piece > 0.1f ? T / Piece : 0.0f;
        const float D = FVector2D::Distance(P, A + (B - A) * F);
        if (FMath::Abs(User3.Z - FMath::Lerp(Prev.Z, Next.Z, F)) <= 250.0f && D < Best)
        {
            Best = D;
            OutAlong = A0 + (A1 - A0) * F;
        }
        Prev = Next;
    }
    return Best;
}

bool AFactoryLoadingBelt::InReach(const AActor* User) const
{
    float Along = 0.0f;
    return DistanceTo(User, Along) <= InteractionRadius;
}

bool AFactoryLoadingBelt::RoomAt(float Along) const
{
    for (const float Other : Travelled)
        if (FMath::Abs(Other - Along) < BoxSpacing) return false;
    return true;
}

void AFactoryLoadingBelt::AddBox(UStaticMesh* Mesh, float Along, float Yaw)
{
    auto* Box = NewObject<UStaticMeshComponent>(this);
    Box->SetStaticMesh(Mesh);
    Box->SetMobility(EComponentMobility::Movable);
    Box->SetCollisionEnabled(ECollisionEnabled::NoCollision);
    Box->SetUsingAbsoluteScale(true);   // the belt may be stretched; the box is not
    Box->SetupAttachment(RootComponent);
    Box->RegisterComponent();
    float Heading = 0.0f;
    const FVector Spot = LocalAt(Along / Stretch(), &Heading);
    Box->SetRelativeLocationAndRotation(Spot, FRotator(0, Heading + Yaw, 0));
    // Keep them ordered furthest first: each box stops behind the one before it.
    int32 Index = 0;
    while (Index < Travelled.Num() && Travelled[Index] > Along) ++Index;
    Boxes.Insert(Box, Index);
    Travelled.Insert(Along, Index);
    Jitter.Insert(Yaw, Index);
}

bool AFactoryLoadingBelt::TryLoad(AActor* User)
{
    auto* Carry = User ? User->FindComponentByClass<UFactoryCarryComponent>() : nullptr;
    float Along = 0.0f;
    if (!Carry || !Carry->IsCarrying() || DistanceTo(User, Along) > InteractionRadius) return false;
    // At the very start of a branch it is as if it were set at the crossing: it goes where the crossing
    // would send it (another branch when this one's truck is full or away).
    AFactoryLoadingBelt* Target = this;
    if (Along <= CrossingZone)
        for (TActorIterator<AFactoryLoadingBelt> It(GetWorld()); It; ++It)
            if (It->Outputs.Num() > 1 && It->Outputs.Contains(this))
            {
                if (AFactoryLoadingBelt* Chosen = It->ChooseOutput()) { Target = Chosen; Along = 0.0f; }
                break;
            }
    if (!Target->RoomAt(Along)) return true;  // no room right there: the box stays in the hands
    FTransform From;
    if (UStaticMesh* Mesh = Carry->Release(From))
        Target->AddBox(Mesh, Along, FMath::FRandRange(-4.0f, 4.0f));
    return true;
}

void AFactoryLoadingBelt::Tick(float DeltaSeconds)
{
    Super::Tick(DeltaSeconds);
    // Boxes ride to the far end (or the box ahead); there the next belt or the docked vehicle takes them.
    const float End = WorldLength();
    // Where belts meet, the next belt's first boxes can be closer to this far end than a box's room: the front
    // box stops short so it keeps the same spacing and does not overlap them.
    float FrontLimit = End;
    const FVector EndPoint = GetDeliveryPoint();
    for (const TObjectPtr<AFactoryLoadingBelt>& Output : Outputs)
        if (Output)
            for (const TObjectPtr<UStaticMeshComponent>& Other : Output->Boxes)
                if (Other)
                {
                    const float Gap = FVector::Dist2D(EndPoint, Other->GetComponentLocation());
                    if (Gap < BoxSpacing) FrontLimit = FMath::Min(FrontLimit, End - (BoxSpacing - Gap));
                }
    bool bMoving = false;
    for (int32 Index = 0; Index < Boxes.Num(); ++Index)
    {
        const float Limit = Index == 0 ? FMath::Max(FrontLimit, 0.0f) : Travelled[Index - 1] - BoxSpacing;
        const float Before = Travelled[Index];
        Travelled[Index] = FMath::Max(Before, FMath::Min(Before + Speed * DeltaSeconds, Limit));
        bMoving |= Travelled[Index] > Before + KINDA_SMALL_NUMBER;
        if (Boxes[Index])
        {
            float Heading = 0.0f;
            const FVector Spot = LocalAt(Travelled[Index] / Stretch(), &Heading);
            Boxes[Index]->SetRelativeLocationAndRotation(Spot, FRotator(0, Heading + Jitter[Index], 0));
        }
    }
    if (Boxes.Num() > 0 && Travelled[0] >= End - 0.5f && Boxes[0])
    {
        UStaticMesh* Mesh = Boxes[0]->GetStaticMesh();
        bool bHanded = false;
        if (!Outputs.IsEmpty())
        {
            if (AFactoryLoadingBelt* Output = ChooseOutput())
            {
                Output->AddBox(Mesh, 0.0f, Jitter[0]);
                bHanded = true;
            }
        }
        else if (Docked)
            bHanded = Docked->ReceiveBox(Mesh, Boxes[0]->GetComponentTransform());
        if (bHanded)
        {
            Boxes[0]->DestroyComponent();
            Boxes.RemoveAt(0);
            Travelled.RemoveAt(0);
            Jitter.RemoveAt(0);
        }
    }
    if (bMoving != bRunning && RollerMaterial)
        RollerMaterial->SetScalarParameterValue(TEXT("Velocidad"), bMoving ? RollerSpeed : 0.0f);
    bRunning = bMoving;

    // Prompt over the spot where the box would go, only with a box in hand and on the nearest belt.
    APlayerController* Player = GetWorld()->GetFirstPlayerController();
    const APawn* Pawn = Player ? Player->GetPawn() : nullptr;
    const auto* Carry = Pawn ? Pawn->FindComponentByClass<UFactoryCarryComponent>() : nullptr;
    float Along = 0.0f;
    const float Mine = Carry && Carry->IsCarrying() ? DistanceTo(Pawn, Along) : TNumericLimits<float>::Max();
    bool bShow = Mine <= InteractionRadius;
    if (bShow)
        for (TActorIterator<AFactoryLoadingBelt> It(GetWorld()); It; ++It)
        {
            float Other = 0.0f;
            if (*It != this && It->DistanceTo(Pawn, Other) < Mine) { bShow = false; break; }
        }
    Prompt->SetHiddenInGame(!bShow);
    if (bShow)
    {
        const TCHAR* Text = RoomAt(Along) ? TEXT("[E] CARGAR CAJA") : TEXT("SIN LUGAR AQUÍ");
        Prompt->SetText(FText::FromString(Text));
        Prompt->SetWorldLocation(WorldAt(Along) + FVector(0, 0, 85.0f));
        if (Player->PlayerCameraManager)  // TextRender reads along +X: turn it toward the camera
            Prompt->SetWorldRotation((Player->PlayerCameraManager->GetCameraLocation() - Prompt->GetComponentLocation()).Rotation());
    }
}
