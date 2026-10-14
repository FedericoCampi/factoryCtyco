#include "FactoryVehiclePath.h"
#include "Components/InstancedStaticMeshComponent.h"
#include "Camera/PlayerCameraManager.h"
#include "Components/PoseableMeshComponent.h"
#include "Components/SkeletalMeshComponent.h"
#include "Components/BoxComponent.h"
#include "Animation/AnimationAsset.h"
#include "Components/SplineComponent.h"
#include "Components/SplineMeshComponent.h"
#include "Components/StaticMeshComponent.h"
#include "Components/TextRenderComponent.h"
#include "Engine/SkeletalMesh.h"
#include "Engine/StaticMesh.h"
#include "Engine/World.h"
#include "EngineUtils.h"
#include "FactoryTruckGate.h"
#include "FactoryLoadingBelt.h"
#include "FactoryMission.h"
#include "FactoryTruckBay.h"
#include "GameFramework/PlayerController.h"

AFactoryVehiclePath::AFactoryVehiclePath()
{
    PrimaryActorTick.bCanEverTick = true;
    RootComponent = CreateDefaultSubobject<USceneComponent>(TEXT("Root"));
    Path = CreateDefaultSubobject<USplineComponent>(TEXT("Path"));
    Path->SetupAttachment(RootComponent);
    Path->SetClosedLoop(false);
    Path->SetDrawDebug(true);   // the line shows in the viewport, selected or not
    Vehicle = CreateDefaultSubobject<UPoseableMeshComponent>(TEXT("Vehicle"));
    Vehicle->SetupAttachment(RootComponent);
    Vehicle->SetUsingAbsoluteLocation(true);   // placed in world space along the line
    Vehicle->SetUsingAbsoluteRotation(true);
    Vehicle->SetCollisionProfileName(TEXT("BlockAllDynamic"));
    Counter = CreateDefaultSubobject<UTextRenderComponent>(TEXT("Counter"));
    Counter->SetupAttachment(Vehicle);
    Counter->SetRelativeLocation(FVector(90, 0, 330));   // above the cargo
    Counter->SetHorizontalAlignment(EHTA_Center);
    Counter->SetVerticalAlignment(EVRTA_TextCenter);
    Counter->SetWorldSize(40.0f);
    Counter->SetTextRenderColor(FColor(46, 232, 199));
    Counter->SetText(FText::GetEmpty());  // shown in play from the first box
    Counter->SetCollisionEnabled(ECollisionEnabled::NoCollision);
    Counter->SetHiddenInGame(true);
    for (TObjectPtr<UStaticMeshComponent>* Wrap : {&WrapDoor, &WrapSide})
    {
        *Wrap = CreateDefaultSubobject<UStaticMeshComponent>(Wrap == &WrapDoor ? TEXT("WrapDoor") : TEXT("WrapSide"));
        (*Wrap)->SetupAttachment(Vehicle);
        (*Wrap)->SetCollisionEnabled(ECollisionEnabled::NoCollision);
        (*Wrap)->SetCastShadow(false);
    }
    Body = CreateDefaultSubobject<UBoxComponent>(TEXT("Body"));
    Body->SetupAttachment(Vehicle);
    Body->SetCollisionProfileName(TEXT("BlockAllDynamic"));
    Body->SetCollisionResponseToChannel(ECC_Camera, ECR_Ignore);
    Body->SetCanEverAffectNavigation(false);
    Driver = CreateDefaultSubobject<USkeletalMeshComponent>(TEXT("Driver"));
    Driver->SetupAttachment(Vehicle);   // in the cab, which does not tip
    Driver->SetCollisionEnabled(ECollisionEnabled::NoCollision);
    CargoPivot = CreateDefaultSubobject<USceneComponent>(TEXT("CargoPivot"));
    CargoPivot->SetupAttachment(Vehicle);
    Load = CreateDefaultSubobject<UInstancedStaticMeshComponent>(TEXT("Load"));
    Load->SetupAttachment(Vehicle);   // a child of the truck (hidden with it out of its scene), placed in world space
    Load->SetUsingAbsoluteLocation(true);
    Load->SetUsingAbsoluteRotation(true);
    Load->SetUsingAbsoluteScale(true);
    Load->SetCollisionEnabled(ECollisionEnabled::NoCollision);
    RearDoor = CreateDefaultSubobject<UStaticMeshComponent>(TEXT("RearDoor"));
    RearDoor->SetupAttachment(Vehicle);
    RearDoor->SetCollisionEnabled(ECollisionEnabled::NoCollision);
    RearSlats = CreateDefaultSubobject<UInstancedStaticMeshComponent>(TEXT("RearSlats"));
    RearSlats->SetupAttachment(Vehicle);
    RearSlats->SetCollisionEnabled(ECollisionEnabled::NoCollision);
    RearBottom = CreateDefaultSubobject<UStaticMeshComponent>(TEXT("RearBottom"));
    RearBottom->SetupAttachment(Vehicle);
    RearBottom->SetCollisionEnabled(ECollisionEnabled::NoCollision);
}

void AFactoryVehiclePath::OnConstruction(const FTransform& Transform)
{
    Super::OnConstruction(Transform);
    BuildRoad();
    Vehicle->SetSkinnedAssetAndUpdate(VehicleMesh);
    for (UStaticMeshComponent* Wrap : {WrapDoor.Get(), WrapSide.Get()}) Wrap->SetStaticMesh(WrapMesh);
    WrapSide->SetRelativeLocationAndRotation(WrapCenter, FRotator(0, 180, 0));
    WrapDoor->SetRelativeLocationAndRotation(FVector(WrapCenter.X, -WrapCenter.Y, WrapCenter.Z), FRotator::ZeroRotator);
    RearDoor->SetStaticMesh(RearDoorMesh);
    RearDoor->SetRelativeLocationAndRotation(RearDoorTop, FRotator::ZeroRotator);
    RearDoor->SetRelativeScale3D(FVector::OneVector);
    RearSlats->SetStaticMesh(RearSlatMesh);
    RearSlats->SetRelativeLocationAndRotation(RearDoorTop, FRotator::ZeroRotator);
    RearBottom->SetStaticMesh(RearBottomMesh);
    RearRise = -1.0f;
    PlaceRearDoor(0.0f);
    RestRotation.Reset();
    CacheRestPose();
    RigCargo();
    PlaceDriver();
    Body->SetBoxExtent(FVector((FrontLength + RearLength) / 2.0f, HalfWidth, BodyHeight / 2.0f));
    Body->SetRelativeLocation(FVector((FrontLength - RearLength) / 2.0f, 0.0f, BodyHeight / 2.0f));
    Load->SetStaticMesh(LoadMesh);
    Place(FMath::Min(EditorPreviewDistance, GetLine()->GetSplineLength()), 0.0f);
    FillLoad();
}

void AFactoryVehiclePath::PlaceDriver()
{
    Driver->SetSkeletalMeshAsset(DriverMesh);
    Driver->SetRelativeTransform(DriverTransform);
    Driver->SetVisibility(DriverMesh != nullptr);
    if (!DriverMesh || !DriverAnim) return;
    Driver->SetAnimationMode(EAnimationMode::AnimationSingleNode);
    Driver->SetUpdateAnimationInEditor(true);   // seated in the editor too
    Driver->PlayAnimation(DriverAnim, true);
}

void AFactoryVehiclePath::RigCargo()
{
    // Everything that rides on the cargo box hangs from CargoPivot; with a tipping bone, CargoPivot hangs from it, undoing
    // its rest transform so that the children keep their places in the mesh's own space.
    bHasDumpBone = PoseReady() && !DumpBone.IsNone() && Vehicle->GetBoneIndex(DumpBone) != INDEX_NONE;
    if (bHasDumpBone)
    {
        const FTransform Rest = Vehicle->GetBoneTransformByName(DumpBone, EBoneSpaces::ComponentSpace);
        DumpRest = Rest.GetRotation();
        CargoPivot->AttachToComponent(Vehicle, FAttachmentTransformRules::KeepRelativeTransform, DumpBone);
        CargoPivot->SetRelativeTransform(Rest.Inverse());
    }
    else
    {
        CargoPivot->AttachToComponent(Vehicle, FAttachmentTransformRules::KeepRelativeTransform);
        CargoPivot->SetRelativeTransform(FTransform::Identity);
    }
    USceneComponent* Riders[] = {RearDoor.Get(), RearSlats.Get(), RearBottom.Get(), WrapDoor.Get(), WrapSide.Get()};
    for (USceneComponent* Part : Riders)
        if (Part->GetAttachParent() != CargoPivot) Part->AttachToComponent(CargoPivot, FAttachmentTransformRules::KeepRelativeTransform);
    DumpTilt = 0.0f;
    PoseDump();
}

void AFactoryVehiclePath::PoseDump()
{
    if (!bHasDumpBone || !PoseReady()) return;
    // The front of the box goes up: a turn about the truck's sideways axis, at the bone's head (the hinge).
    const FQuat Tip = FRotator(DumpAngle * FMath::InterpEaseInOut(0.0f, 1.0f, DumpTilt, 2.0f), 0.0f, 0.0f).Quaternion();
    Vehicle->SetBoneRotationByName(DumpBone, (Tip * DumpRest).Rotator(), EBoneSpaces::ComponentSpace);
    Vehicle->UpdateChildTransforms(EUpdateTransformFlags::None, ETeleportType::TeleportPhysics);
}

void AFactoryVehiclePath::FillLoad()
{
    LoadState.Reset();
    Load->ClearInstances();
    if (!bDumpTruck || !LoadMesh || LoadPieces <= 0) return;
    // A heap on the cargo floor: rows across, columns along, two layers.
    const int32 Across = 3, Heaps = 2;
    const int32 Along = FMath::Max(1, FMath::DivideAndRoundUp(LoadPieces, Across * Heaps));
    const float Back = CargoBackX + 20.0f, Front = CargoFrontX - 25.0f;
    for (int32 Index = 0; Index < LoadPieces; ++Index)
    {
        const int32 Layer = Index / (Across * Along), Column = (Index / Across) % Along, Row = Index % Across;
        const float Hash = FMath::Sin(Index * 12.9898f) * 43758.5453f;
        const float J = Hash - FMath::FloorToFloat(Hash);   // 0..1, always the same for a piece
        FPiece Piece;
        const FVector Location(FMath::Lerp(Back, Front, (Column + 0.5f) / Along) + (J - 0.5f) * 18.0f,
                               (Row - 1) * 42.0f + (J - 0.5f) * 14.0f, CargoFloor + Layer * 16.0f);
        Piece.Home = FTransform(FRotator((J - 0.5f) * 40.0f, J * 360.0f, (0.5f - J) * 30.0f), Location,
                                FVector(LoadScale * (0.8f + 0.4f * J)));
        // The back ones go first, the top layer before the one under it.
        Piece.Release = 0.2f + 0.5f * (Location.X - Back) / FMath::Max(Front - Back, 1.0f) + (Layer == 0 ? 0.08f : 0.0f) + J * 0.05f;
        LoadState.Add(Piece);
    }
    TArray<FTransform> Placed;
    for (const FPiece& Piece : LoadState) Placed.Add(Piece.Home * CargoPivot->GetComponentTransform());
    Load->AddInstances(Placed, false, true);
}

int32 AFactoryVehiclePath::GetLoadInCargo() const
{
    int32 Count = 0;
    for (const FPiece& Piece : LoadState) Count += Piece.State == 0;
    return Count;
}

int32 AFactoryVehiclePath::GetLoadDumped() const
{
    int32 Count = 0;
    for (const FPiece& Piece : LoadState) Count += Piece.State >= 2;
    return Count;
}

TArray<FVector> AFactoryVehiclePath::GetLoadLandings() const
{
    TArray<FVector> Points;
    for (const FPiece& Piece : LoadState)
        if (Piece.State == 3) Points.Add(Piece.Landed);
    return Points;
}

bool AFactoryVehiclePath::TickDump(float DeltaSeconds)
{
    DumpTimer += DeltaSeconds;
    switch (DumpPhase)
    {
    case EDumpPhase::None:
        DumpPhase = EDumpPhase::Opening;
        bDoorWantOpen = true;
        break;
    case EDumpPhase::Opening:
        if (DoorOpen >= 1.0f) { DumpPhase = EDumpPhase::Raising; DumpTimer = 0.0f; }
        break;
    case EDumpPhase::Raising:
        DumpTilt = FMath::Min(DumpTilt + DeltaSeconds / DumpRaiseSeconds, 1.0f);
        if (DumpTilt >= 1.0f) { DumpPhase = EDumpPhase::Holding; DumpTimer = 0.0f; }
        break;
    case EDumpPhase::Holding:
        // Up until its time is over and the last piece has left the cargo.
        if (DumpTimer >= DumpHoldSeconds && GetLoadInCargo() == 0) { DumpPhase = EDumpPhase::Lowering; DumpTimer = 0.0f; }
        break;
    case EDumpPhase::Lowering:
        DumpTilt = FMath::Max(DumpTilt - DeltaSeconds / DumpLowerSeconds, 0.0f);
        if (DumpTilt <= 0.0f) { DumpPhase = EDumpPhase::Closing; bDoorWantOpen = false; }
        break;
    case EDumpPhase::Closing:
        if (DoorOpen <= 0.0f) { DumpPhase = EDumpPhase::None; return true; }
        break;
    }
    return false;
}

void AFactoryVehiclePath::UpdateLoad(float DeltaSeconds)
{
    if (!bDumpTruck) return;
    PoseDump();
    if (LoadState.IsEmpty() || Load->GetInstanceCount() != LoadState.Num()) return;
    const FTransform Box = CargoPivot->GetComponentTransform();
    const float Gravity = 980.0f;
    // How steep the cargo floor is now (the box's tip plus the truck's pitch on the ramp): its back end down.
    const float Slope = FMath::Asin(FMath::Clamp(Box.GetUnitAxis(EAxis::X).Z, -1.0f, 1.0f));
    // In short steps, so that a long frame does not throw a piece past the hopper.
    const int32 Steps = FMath::Clamp(FMath::CeilToInt(DeltaSeconds * 60.0f), 1, 120);
    const float Dt = DeltaSeconds / Steps;
    for (int32 Sub = 0; Sub < Steps; ++Sub)
        for (FPiece& Piece : LoadState)
        {
            if (Piece.State == 0 && DumpPhase != EDumpPhase::None && DumpTilt >= Piece.Release) Piece.State = 1;
            if (Piece.State == 1)
            {
                // Slides back down the floor, faster as it tips; past the lip it falls.
                Piece.SlideSpeed += Gravity * FMath::Max(FMath::Sin(Slope) - 0.2f, 0.05f) * Dt;
                Piece.Slide += Piece.SlideSpeed * Dt;
                const FVector Local = Piece.Home.GetLocation() - FVector(Piece.Slide, 0.0f, 0.0f);
                if (Local.X < CargoBackX - 12.0f)
                {
                    Piece.State = 2;
                    const FTransform At = FTransform(Piece.Home.GetRotation(), Local, Piece.Home.GetScale3D()) * Box;
                    Piece.Position = At.GetLocation();
                    Piece.Rotation = At.GetRotation();
                    Piece.LipZ = Piece.Position.Z;
                    Piece.Velocity = -Box.GetUnitAxis(EAxis::X) * Piece.SlideSpeed;
                }
            }
            if (Piece.State == 2)
            {
                Piece.Velocity.Z -= Gravity * Dt;
                Piece.Position += Piece.Velocity * Dt;
                Piece.Rotation = FQuat(FVector(0.6f, 0.8f, 0.0f).GetSafeNormal(), 4.0f * Dt) * Piece.Rotation;
                if (Piece.Position.Z < Piece.LipZ - LoadFall)
                {
                    Piece.State = 3;
                    Piece.Landed = Piece.Position;
                }
            }
        }
    TArray<FTransform> Placed;
    Placed.Reserve(LoadState.Num());
    for (FPiece& Piece : LoadState)
    {
        if (Piece.State == 0)
            Placed.Add(Piece.Home * Box);
        else if (Piece.State == 1)
            Placed.Add(FTransform(Piece.Home.GetRotation(), Piece.Home.GetLocation() - FVector(Piece.Slide, 0.0f, 0.0f), Piece.Home.GetScale3D()) * Box);
        else if (Piece.State == 2)
            Placed.Add(FTransform(Piece.Rotation, Piece.Position, Piece.Home.GetScale3D()));
        else
            Placed.Add(FTransform(FQuat::Identity, Box.GetLocation(), FVector::ZeroVector));   // gone
    }
    Load->BatchUpdateInstancesTransforms(0, Placed, true, true, true);
}

void AFactoryVehiclePath::BeginPlay()
{
    Super::BeginPlay();
    Distance = 0.0f;
    CurrentSpeed = Speed;
    Paused = StartDelay;
    bGatesFound = false;
    BayState = EBayState::None;
    Bay.Reset();
    bBayDone = false;
    RearSpin = FrontSpin = 0.0f;
    DumpPhase = EDumpPhase::None;
    BlockedFor = BackOff = 0.0f;
    BlockedBy.Reset();
    ResetCargo();
    CacheRestPose();
    RigCargo();
    PlaceDriver();
    Place(Distance, 0.0f);
    FillLoad();
}

bool AFactoryVehiclePath::PoseReady() const
{
    return VehicleMesh && Vehicle->GetSkinnedAsset() == VehicleMesh && Vehicle->IsRegistered()
        && Vehicle->GetComponentSpaceTransforms().Num() == VehicleMesh->GetRefSkeleton().GetNum();
}

void AFactoryVehiclePath::CacheRestPose()
{
    if (!PoseReady() || !RestRotation.IsEmpty()) return;
    for (const TArray<FName>* Wheels : {&FrontWheels, &RearWheels})
        for (const FName& Wheel : *Wheels)
            if (Vehicle->GetBoneIndex(Wheel) != INDEX_NONE)
                RestRotation.Add(Wheel, Vehicle->GetBoneRotationByName(Wheel, EBoneSpaces::ComponentSpace).Quaternion());
}

void AFactoryVehiclePath::BuildRoad()
{
    if (!RoadMesh || (LeadPath && LeadPath != this) || !Path) return;
    const float Length = Path->GetSplineLength();
    const int32 Pieces = FMath::Max(1, FMath::RoundToInt(Length / RoadPiece));
    const float Step = Length / Pieces;
    for (int32 Index = 0; Index < Pieces; ++Index)
    {
        // Made by the construction script: Unreal removes them before the next rebuild.
        auto* Piece = NewObject<USplineMeshComponent>(this);
        Piece->CreationMethod = EComponentCreationMethod::UserConstructionScript;
        Piece->SetMobility(EComponentMobility::Movable);
        Piece->SetStaticMesh(RoadMesh);
        Piece->SetCollisionEnabled(ECollisionEnabled::NoCollision);
        Piece->SetCastShadow(false);
        Piece->SetupAttachment(Path);
        Piece->RegisterComponent();
        const float From = Index * Step, To = From + Step;
        const FVector Lift(0, 0, RoadLift);
        Piece->SetStartAndEnd(Path->GetLocationAtDistanceAlongSpline(From, ESplineCoordinateSpace::Local) + Lift,
                              Path->GetDirectionAtDistanceAlongSpline(From, ESplineCoordinateSpace::Local) * Step,
                              Path->GetLocationAtDistanceAlongSpline(To, ESplineCoordinateSpace::Local) + Lift,
                              Path->GetDirectionAtDistanceAlongSpline(To, ESplineCoordinateSpace::Local) * Step);
    }
}

USplineComponent* AFactoryVehiclePath::GetLine() const
{
    return LeadPath && LeadPath != this && LeadPath->Path ? LeadPath->Path.Get() : Path.Get();
}

FVector AFactoryVehiclePath::PointAt(float Along) const
{
    const float Length = GetLine()->GetSplineLength();
    if (GetLine()->IsClosedLoop() && Length > 0.0f)
        return GetLine()->GetLocationAtDistanceAlongSpline(FMath::Fmod(FMath::Fmod(Along, Length) + Length, Length), ESplineCoordinateSpace::World);
    const float Clamped = FMath::Clamp(Along, 0.0f, Length);
    return GetLine()->GetLocationAtDistanceAlongSpline(Clamped, ESplineCoordinateSpace::World) + DirectionAt(Clamped) * (Along - Clamped);
}

FVector AFactoryVehiclePath::DirectionAt(float Along) const
{
    const float Length = GetLine()->GetSplineLength();
    const float Inside = GetLine()->IsClosedLoop() && Length > 0.0f
        ? FMath::Fmod(FMath::Fmod(Along, Length) + Length, Length) : FMath::Clamp(Along, 0.0f, Length);
    return GetLine()->GetDirectionAtDistanceAlongSpline(Inside, ESplineCoordinateSpace::World);
}

void AFactoryVehiclePath::Place(float Along, float Steer)
{
    // Rear axle on the line; the front axle a wheelbase further along it: the body points from one to the other.
    FVector Rear, Front;
    AxlePoints(Along, Rear, Front);
    if (bFollowGround)
    {
        // On the line both axles are on its road; backing into a bay the rear one is off it (the front one too until it
        // is back on the line).
        const AFactoryTruckBay* InBay = BayState != EBayState::None ? Bay.Get() : nullptr;
        Rear.Z = GroundZ(Rear, !InBay);
        Front.Z = GroundZ(Front, !InBay || BayS + Wheelbase > InBay->Length());
    }
    LastRear = Rear;
    LastFront = Front;
    bPlaced = true;
    const FVector Heading = Front - Rear;
    const float Yaw = FMath::RadiansToDegrees(FMath::Atan2(Heading.Y, Heading.X));
    const float Pitch = FMath::RadiansToDegrees(FMath::Atan2(Heading.Z, Heading.Size2D()));
    Vehicle->SetWorldLocationAndRotation(Rear, FRotator(Pitch, Yaw, 0.0f));
    // Wheels: roll about the axle (component Y), then the front ones steer about the vertical.
    // A wheel rolling forward turns its top toward +X: negative pitch.
    if (PoseReady())
    for (const TArray<FName>* Wheels : {&FrontWheels, &RearWheels})
    {
        const bool bFront = Wheels == &FrontWheels;
        const FQuat Delta = FRotator(-(bFront ? FrontSpin : RearSpin), bFront ? Steer : 0.0f, 0.0f).Quaternion();
        for (const FName& Wheel : *Wheels)
            if (const FQuat* Rest = RestRotation.Find(Wheel))
                Vehicle->SetBoneRotationByName(Wheel, (Delta * *Rest).Rotator(), EBoneSpaces::ComponentSpace);
    }
    // Only the rear door opens (parked in a bay: loading or tipping); the side door and the roof stay shut.
    PlaceRearDoor(bBayLoading || DumpPhase != EDumpPhase::None ? FMath::InterpEaseInOut(0.0f, 1.0f, DoorOpen, 2.0f) : 0.0f);
    UpdateLoad(0.0f);
}

float AFactoryVehiclePath::GroundZ(const FVector& Point, bool bOnRoad) const
{
    // The road is drawn RoadLift over the line (by the line's own truck, when it draws one).
    const AFactoryVehiclePath* RoadOwner = LeadPath && LeadPath != this ? LeadPath.Get() : this;
    const bool bRoad = bOnRoad && RoadOwner->RoadMesh;
    // From a little over the line down.
    float Z;
    if (!TraceFloor(Point + FVector(0, 0, GroundReach * 0.6f), Point - FVector(0, 0, GroundReach), Z)) return Point.Z;
    return bRoad ? FMath::Max(Z, Point.Z + RoadOwner->RoadLift) : Z;
}

bool AFactoryVehiclePath::TraceFloor(const FVector& From, const FVector& To, float& Z) const
{
    UWorld* World = GetWorld();
    if (!World) return false;
    FCollisionQueryParams Params(SCENE_QUERY_STAT(TruckFloor), true, this);
    TArray<FHitResult> Hits;
    World->LineTraceMultiByObjectType(Hits, From, To, FCollisionObjectQueryParams(ECC_WorldStatic), Params);
    for (const FHitResult& Hit : Hits)
        if (const UPrimitiveComponent* Part = Hit.GetComponent())
            if (Part->Mobility == EComponentMobility::Static)
            {
                Z = Hit.ImpactPoint.Z;
                return true;
            }
    return false;
}

void AFactoryVehiclePath::SnapLineToGround()
{
    UWorld* World = GetWorld();
    if (!Path || !World || Path->GetNumberOfSplinePoints() < 2) return;
    Modify();
    // Every half metre along the line: how much it has to go up to be LineLift over the floor there (only up: over the
    // floor, a road ramp, it stays).
    struct FSample { float Key; FVector At; float Raise; bool bKey; };
    TArray<FSample> Samples;
    const int32 Keys = Path->GetNumberOfSplinePoints();
    const float Length = Path->GetSplineLength();
    for (int32 Key = 0; Key < Keys; ++Key)
    {
        const float From = Path->GetDistanceAlongSplineAtSplinePoint(Key);
        const float To = Key + 1 < Keys ? Path->GetDistanceAlongSplineAtSplinePoint(Key + 1) : From;
        for (float Along = From; Along < To || Along == From; Along += 50.0f)
        {
            FSample Sample{Along == From ? float(Key) : Path->GetInputKeyValueAtDistanceAlongSpline(FMath::Min(Along, Length)),
                           Path->GetLocationAtDistanceAlongSpline(Along, ESplineCoordinateSpace::World), 0.0f, Along == From};
            float Floor;
            if (TraceFloor(Sample.At + FVector(0, 0, 500), Sample.At - FVector(0, 0, 1000), Floor))
                Sample.Raise = FMath::Max(Floor + LineLift - Sample.At.Z, 0.0f);
            Samples.Add(Sample);
            if (Along == To) break;
        }
    }
    // Keep the user's points; between two kept ones, add the sample whose raise differs most from the raise blended
    // between them, while it is more than 4 cm off (where the floor rises above the line).
    TArray<bool> Keep;
    Keep.Init(false, Samples.Num());
    for (int32 Index = 0; Index < Samples.Num(); ++Index) Keep[Index] = Samples[Index].bKey;
    TFunction<void(int32, int32)> Split = [&](int32 A, int32 B)
    {
        int32 Worst = INDEX_NONE;
        float WorstGap = 4.0f;
        for (int32 Index = A + 1; Index < B; ++Index)
        {
            const float T = (Samples[Index].Key - Samples[A].Key) / FMath::Max(Samples[B].Key - Samples[A].Key, KINDA_SMALL_NUMBER);
            const float Gap = Samples[Index].Raise - FMath::Lerp(Samples[A].Raise, Samples[B].Raise, T);
            if (Gap > WorstGap) { WorstGap = Gap; Worst = Index; }
        }
        if (Worst == INDEX_NONE) return;
        Keep[Worst] = true;
        Split(A, Worst);
        Split(Worst, B);
    };
    int32 Last = 0;
    for (int32 Index = 1; Index < Samples.Num(); ++Index)
        if (Keep[Index]) { Split(Last, Index); Last = Index; }
    // The new points cut the same curve: each one's tangents are the old curve's slope there times the share of the old
    // segment its neighbours span (a cubic cut in two stays the same curve).
    TArray<int32> Kept;
    for (int32 Index = 0; Index < Samples.Num(); ++Index)
        if (Keep[Index]) Kept.Add(Index);
    struct FNew { FVector At, Arrive, Leave; };
    TArray<FNew> Points;
    for (int32 K = 0; K < Kept.Num(); ++K)
    {
        const FSample& S = Samples[Kept[K]];
        const bool bOld = S.bKey;
        const int32 OldKey = FMath::RoundToInt(S.Key);
        const FVector In = bOld ? Path->GetArriveTangentAtSplinePoint(OldKey, ESplineCoordinateSpace::World)
                                : Path->GetTangentAtSplineInputKey(S.Key, ESplineCoordinateSpace::World);
        const FVector Out = bOld ? Path->GetLeaveTangentAtSplinePoint(OldKey, ESplineCoordinateSpace::World) : In;
        const float Before = K > 0 ? S.Key - Samples[Kept[K - 1]].Key : 1.0f;
        const float After = K + 1 < Kept.Num() ? Samples[Kept[K + 1]].Key - S.Key : 1.0f;
        Points.Add({S.At + FVector(0, 0, S.Raise), In * Before, Out * After});
    }
    const bool bLoop = Path->IsClosedLoop();
    Path->ClearSplinePoints(false);
    for (int32 Index = 0; Index < Points.Num(); ++Index)
    {
        Path->AddSplinePoint(Points[Index].At, ESplineCoordinateSpace::World, false);
        Path->SetSplinePointType(Index, ESplinePointType::CurveCustomTangent, false);
        Path->SetTangentsAtSplinePoint(Index, Points[Index].Arrive, Points[Index].Leave, ESplineCoordinateSpace::World, false);
    }
    Path->SetClosedLoop(bLoop, false);
    Path->UpdateSpline();
    RerunConstructionScripts();
}

namespace
{
    /** Rectangles (centre, unit axis, half length along it, half width across) overlap: separating axis test. */
    bool RectsOverlap(const FVector2D& CA, const FVector2D& XA, float LA, float WA, const FVector2D& CB, const FVector2D& XB, float LB, float WB)
    {
        const FVector2D YA(-XA.Y, XA.X), YB(-XB.Y, XB.X);
        for (const FVector2D& N : {XA, YA, XB, YB})
        {
            const float RA = LA * FMath::Abs(FVector2D::DotProduct(XA, N)) + WA * FMath::Abs(FVector2D::DotProduct(YA, N));
            const float RB = LB * FMath::Abs(FVector2D::DotProduct(XB, N)) + WB * FMath::Abs(FVector2D::DotProduct(YB, N));
            if (FMath::Abs(FVector2D::DotProduct(CB - CA, N)) > RA + RB) return false;
        }
        return true;
    }
}

bool AFactoryVehiclePath::WouldHit(const FVector& Rear, const FVector& Front, const FVector& Motion, AFactoryVehiclePath*& Other) const
{
    const FVector2D X = FVector2D(Front - Rear).GetSafeNormal();
    const FVector2D Center = FVector2D(Rear) + X * ((FrontLength - RearLength) / 2.0f);
    const FVector2D Move = FVector2D(Motion).GetSafeNormal();
    for (TActorIterator<AFactoryVehiclePath> It(GetWorld()); It; ++It)
    {
        AFactoryVehiclePath* Truck = *It;
        if (Truck == this || !Truck->bPlaced || !Truck->VehicleMesh || UFactoryUnlockSubsystem::IsLocked(Truck)) continue;
        const FVector2D OX = FVector2D(Truck->LastFront - Truck->LastRear).GetSafeNormal();
        const FVector2D OC = FVector2D(Truck->LastRear) + OX * ((Truck->FrontLength - Truck->RearLength) / 2.0f);
        // Only a truck it is moving towards stops it (one behind or beside it does not).
        if (FVector2D::DotProduct(OC - Center, Move) <= 0.0f) continue;
        if (RectsOverlap(Center, X, (FrontLength + RearLength) / 2.0f + TrafficGap, HalfWidth + TrafficGap / 2.0f,
                         OC, OX, (Truck->FrontLength + Truck->RearLength) / 2.0f, Truck->HalfWidth))
        {
            Other = Truck;
            return true;
        }
    }
    return false;
}

void AFactoryVehiclePath::NoteBlocked(AFactoryVehiclePath* Other, float DeltaSeconds)
{
    CurrentSpeed = 0.0f;
    if (BlockedBy.Get() != Other) { BlockedBy = Other; BlockedFor = 0.0f; }
    BlockedFor += DeltaSeconds;
    if (BlockedFor < StuckSeconds || !Other) return;
    BlockedFor = 0.0f;
    // The truck behind backs up: the other one, when it stands on the line behind this one; this one, when it is on the
    // line and the other is stuck on it too.
    const FVector2D Mine = FVector2D(LastRear + LastFront) / 2.0f, Theirs = FVector2D(Other->LastRear + Other->LastFront) / 2.0f;
    const FVector2D TheirHeading = FVector2D(Other->LastFront - Other->LastRear).GetSafeNormal();
    if (Other->BayState == EBayState::None && Other->BackOff <= 0.0f && FVector2D::DotProduct(Mine - Theirs, TheirHeading) > 0.0f)
        Other->BackOff = Other->BackOffDistance;
    else if (BayState == EBayState::None && BackOff <= 0.0f && Other->BlockedBy.Get() == this)
        BackOff = BackOffDistance;
}

void AFactoryVehiclePath::PlaceRearDoor(float Open)
{
    const float SlatHeight = RearSlatMesh ? FMath::Max(RearSlatMesh->GetBoundingBox().GetSize().Z, 1.0f) : 8.0f;
    const float BottomHeight = RearBottomMesh ? RearBottomMesh->GetBoundingBox().GetSize().Z : 0.0f;
    // The curtain goes up until its bottom bar is just under the header.
    const float Rise = FMath::Max(RearDoorHeight - RearHeader - BottomHeight, 0.0f) * FMath::Clamp(Open, 0.0f, 1.0f);
    if (FMath::IsNearlyEqual(Rise, RearRise, 0.05f)) return;
    RearRise = Rise;
    RearBottom->SetRelativeLocationAndRotation(RearDoorTop + FVector(0, 0, -RearDoorHeight + Rise), FRotator::ZeroRotator);
    // Slats from the bottom bar up; one wholly behind the header is gone (it is rolled up there).
    RearSlats->ClearInstances();
    if (!RearSlatMesh) return;
    const int32 Count = FMath::RoundToInt((RearDoorHeight - BottomHeight) / SlatHeight);
    TArray<FTransform> Slats;
    for (int32 Index = 0; Index < Count; ++Index)
    {
        const float Bottom = -RearDoorHeight + BottomHeight + Index * SlatHeight + Rise;
        if (Bottom >= -RearHeader - 0.01f) break;
        Slats.Add(FTransform(FVector(0, 0, Bottom)));
    }
    RearSlats->AddInstances(Slats, false);
}

void AFactoryVehiclePath::AxlePoints(float Along, FVector& Rear, FVector& Front) const
{
    const AFactoryTruckBay* InBay = BayState != EBayState::None ? Bay.Get() : nullptr;
    if (!InBay)
    {
        Rear = PointAt(Along);
        Front = PointAt(Along + Wheelbase);
        return;
    }
    // On the maneuver, facing out of the bay; a front axle past its end is already on the line.
    const float Length = InBay->Length(), FrontS = BayS + Wheelbase;
    Rear = InBay->PointAt(BayS);
    Front = FrontS <= Length ? InBay->PointAt(FrontS) : PointAt(BayAt + FrontS - Length);
}

void AFactoryVehiclePath::Tick(float DeltaSeconds)
{
    Super::Tick(DeltaSeconds);
    const float Length = GetLine()->GetSplineLength();
    if (!VehicleMesh || Length <= 0.0f || UFactoryUnlockSubsystem::IsLocked(this)) return;
    if (Paused > 0.0f)
    {
        Paused -= DeltaSeconds;
        return;
    }
    if (!GetLine()->IsClosedLoop() && Distance > Length)
    {
        // Its rear axle passed the last point: start again from the first one, once nobody is there.
        if (!StartIsClear()) return;
        Distance = 0.0f;
        CurrentSpeed = Speed;
        Paused = PauseBetweenTrips;
        Deliver();      // no barrier on the line: delivered at its end
        ResetCargo();   // a new trip comes empty (a dump truck, loaded again)
        bBayDone = false;
        Place(Distance, 0.0f);
        FillLoad();
        return;
    }
    if (!bGatesFound) { FindGates(); FindDocks(); FindBays(); }
    if (BayState != EBayState::None)
    {
        TickBay(DeltaSeconds);
        return;
    }
    MaxAdvance = TNumericLimits<float>::Max();
    // Brakes smoothly for a lowered barrier, the loading stop or the vehicle ahead, and sets off again when free.
    const float Limit = FMath::Min3(FMath::Min3(Speed, GateSpeedLimit(), DockSpeedLimit()), FollowSpeedLimit(), BaySpeedLimit());
    CurrentSpeed = Limit < CurrentSpeed ? Limit : FMath::Min(Limit, CurrentSpeed + Acceleration * DeltaSeconds);
    float Step = FMath::Clamp(CurrentSpeed * DeltaSeconds, 0.0f, FMath::Max(MaxAdvance, 0.0f));
    if (Step < CurrentSpeed * DeltaSeconds) CurrentSpeed = FMath::Min(CurrentSpeed, Step / FMath::Max(DeltaSeconds, KINDA_SMALL_NUMBER));
    FVector NewRear, NewFront;
    AFactoryVehiclePath* Blocker = nullptr;
    if (BackOff > 0.0f)
    {
        // Backing up slowly to let a stuck truck through, unless there is a truck behind or the line's start.
        Step = -FMath::Min3(BackOff, 100.0f * DeltaSeconds, Distance);
        AxlePoints(Distance + Step, NewRear, NewFront);
        if (Step >= 0.0f || WouldHit(NewRear, NewFront, NewRear - NewFront, Blocker)) { Step = 0.0f; BackOff = 0.0f; }
        else BackOff += Step;
        CurrentSpeed = 0.0f;
    }
    else if (Step > 0.0f)
    {
        AxlePoints(Distance + Step, NewRear, NewFront);
        if (WouldHit(NewRear, NewFront, NewFront - NewRear, Blocker)) { Step = 0.0f; NoteBlocked(Blocker, DeltaSeconds); }
        else BlockedFor = 0.0f;
    }
    Distance += Step;
    // Both axles move Step along the line; each wheel turns by its own radius.
    RearSpin = FMath::Fmod(RearSpin + FMath::RadiansToDegrees(Step / RearWheelRadius), 360.0f);
    FrontSpin = FMath::Fmod(FrontSpin + FMath::RadiansToDegrees(Step / FrontWheelRadius), 360.0f);
    const FVector Heading = PointAt(Distance + Wheelbase) - PointAt(Distance);
    const FVector Ahead = DirectionAt(Distance + Wheelbase);
    float Steer = FMath::RadiansToDegrees(FMath::Atan2(Ahead.Y, Ahead.X) - FMath::Atan2(Heading.Y, Heading.X));
    Steer = FMath::Clamp(FRotator::NormalizeAxis(Steer), -MaxSteer, MaxSteer);
    UpdateCargo(DeltaSeconds);
    Place(Distance, Steer);
    UpdateLoad(DeltaSeconds);
}

void AFactoryVehiclePath::FindGates()
{
    bGatesFound = true;
    Gates.Reset();
    for (TActorIterator<AFactoryTruckGate> It(GetWorld()); It; ++It)
    {
        FVector Pivot, Tip;
        It->GetCrossLine(Pivot, Tip);
        // The point of the arm nearest to the line, and where along the line that is.
        float Best = TNumericLimits<float>::Max(), Key = 0.0f;
        for (int32 Sample = 0; Sample <= 24; ++Sample)
        {
            const FVector Point = FMath::Lerp(Pivot, Tip, Sample / 24.0f);
            const float K = GetLine()->FindInputKeyClosestToWorldLocation(Point);
            const float Gap = FVector::Dist2D(Point, GetLine()->GetLocationAtSplineInputKey(K, ESplineCoordinateSpace::World));
            if (Gap < Best) { Best = Gap; Key = K; }
        }
        if (Best < 100.0f)
            Gates.Add({*It, GetLine()->GetDistanceAlongSplineAtSplineInputKey(Key), false});
    }
}

float AFactoryVehiclePath::GateSpeedLimit()
{
    float Limit = TNumericLimits<float>::Max();
    const float Front = Distance + FrontLength, Back = Distance - RearLength;
    WaitingGate.Reset();
    for (FGateStop& Stop : Gates)
    {
        AFactoryTruckGate* Gate = Stop.Gate.Get();
        if (!Gate) continue;
        const bool bUnder = Front > Stop.At - 20.0f && Back < Stop.At + 20.0f;
        Gate->SetVehicleUnder(this, bUnder);
        if (Stop.bWasUnder && !bUnder && Back >= Stop.At)
        {
            Gate->VehiclePassed();                    // through (the barrier comes down)
            if (Gate->CountsAsDelivery()) Deliver();  // out through the exit: its load is delivered
        }
        Stop.bWasUnder = bUnder;
        if (!Gate->IsPassable() && !bUnder && Front < Stop.At)
        {
            // v² = 2·a·d: the speed from which it can still stop at the line before the arm.
            const float Room = FMath::Max(Stop.At - StopGap - Front, 0.0f);
            Limit = FMath::Min(Limit, FMath::Sqrt(2.0f * Braking * Room));
            MaxAdvance = FMath::Min(MaxAdvance, Room);
            if (Room < 25.0f) WaitingGate = Gate;   // there, waiting for it to open
        }
    }
    return Limit;
}

void AFactoryVehiclePath::FindDocks()
{
    Docks.Reset();
    if (bDumpTruck) return;   // it does not load boxes
    for (TActorIterator<AFactoryLoadingBelt> It(GetWorld()); It; ++It)
    {
        if (It->GetNext() || UFactoryUnlockSubsystem::IsLocked(*It)) continue;   // only a built last belt of a chain docks trucks
        const FVector End = It->GetDeliveryPoint();
        const float Key = GetLine()->FindInputKeyClosestToWorldLocation(End);
        if (FVector::Dist2D(End, GetLine()->GetLocationAtSplineInputKey(Key, ESplineCoordinateSpace::World)) < DockReach)
            Docks.Add({*It, GetLine()->GetDistanceAlongSplineAtSplineInputKey(Key)});
    }
    Docks.Sort([](const FDock& A, const FDock& B) { return A.At < B.At; });
}

AFactoryLoadingBelt* AFactoryVehiclePath::GetDockBelt() const
{
    const int32 Index = bDocked ? DockIndex : ReservedIndex;
    return Docks.IsValidIndex(Index) ? Docks[Index].Belt.Get() : nullptr;
}

bool AFactoryVehiclePath::DockFreeFor(int32 Index) const
{
    if (!Docks.IsValidIndex(Index) || !Docks[Index].Belt.IsValid()) return false;
    const AFactoryLoadingBelt* Belt = Docks[Index].Belt.Get();
    const float Target = Docks[Index].At - CargoDoorOffset;   // the door lines up with the belt here
    if (Distance > Target + 5.0f) return false;              // already passed
    if ((Belt->Docked && Belt->Docked != this) || (Belt->Reserved && Belt->Reserved != this)) return false;
    // Another vehicle standing where this one would stop (or on its way there, ahead of it) blocks it.
    for (TActorIterator<AFactoryVehiclePath> It(GetWorld()); It; ++It)
        if (*It != this && !UFactoryUnlockSubsystem::IsLocked(*It) && !It->IsOffLine() && It->GetLine() == GetLine() && It->Distance > Distance
            && It->Distance - It->RearLength < Target + FrontLength + FollowGap
            && It->Distance + It->FrontLength > Target - RearLength - FollowGap)
            return false;
    return true;
}

void AFactoryVehiclePath::Reserve(int32 Index)
{
    if (Index == ReservedIndex) return;
    if (Docks.IsValidIndex(ReservedIndex) && Docks[ReservedIndex].Belt.IsValid() && Docks[ReservedIndex].Belt->Reserved == this)
        Docks[ReservedIndex].Belt->Reserved = nullptr;
    ReservedIndex = Index;
    if (Docks.IsValidIndex(Index)) Docks[Index].Belt->Reserved = this;
}

float AFactoryVehiclePath::DockSpeedLimit()
{
    if (bDocked) return 0.0f;
    if (bServed) return TNumericLimits<float>::Max();   // full: straight on
    // Head for the furthest free belt ahead (a later one frees the earlier ones for the vehicle behind).
    int32 Choice = INDEX_NONE;
    for (int32 Index = 0; Index < Docks.Num(); ++Index)
        if (DockFreeFor(Index)) Choice = Index;
    Reserve(Choice);
    if (Choice == INDEX_NONE) return TNumericLimits<float>::Max();
    const float Target = Docks[Choice].At - CargoDoorOffset;
    const float Room = FMath::Max(Target - Distance, 0.0f);
    MaxAdvance = FMath::Min(MaxAdvance, Room);
    if (Room < 1.0f)
    {
        Distance = Target;
        bDocked = true;
        DockIndex = Choice;
        bDoorWantOpen = true;
        Docks[Choice].Belt->Docked = this;
        return 0.0f;
    }
    return FMath::Max(FMath::Sqrt(2.0f * Braking * Room), 15.0f);   // creeps the last centimetres
}

float AFactoryVehiclePath::FollowSpeedLimit()
{
    float Limit = TNumericLimits<float>::Max();
    for (TActorIterator<AFactoryVehiclePath> It(GetWorld()); It; ++It)
        if (*It != this && !UFactoryUnlockSubsystem::IsLocked(*It) && !It->IsOffLine() && It->GetLine() == GetLine() && It->Distance > Distance)
        {
            const float Room = It->Distance - It->RearLength - FollowGap - (Distance + FrontLength);
            Limit = FMath::Min(Limit, FMath::Sqrt(2.0f * Braking * FMath::Max(Room, 0.0f)));
            MaxAdvance = FMath::Min(MaxAdvance, FMath::Max(Room, 0.0f));
        }
    return Limit;
}

bool AFactoryVehiclePath::StartIsClear() const
{
    for (TActorIterator<AFactoryVehiclePath> It(GetWorld()); It; ++It)
        if (*It != this && !UFactoryUnlockSubsystem::IsLocked(*It) && !It->IsOffLine() && It->GetLine() == GetLine()
            && It->Distance - It->RearLength < FrontLength + FollowGap && It->Distance + It->FrontLength > -RearLength - FollowGap)
            return false;
    return true;
}

void AFactoryVehiclePath::FindBays()
{
    Bays.Reset();
    for (TActorIterator<AFactoryTruckBay> It(GetWorld()); It; ++It)
    {
        if (UFactoryUnlockSubsystem::IsLocked(*It) || It->Length() <= 0.0f || It->bDump != bDumpTruck) continue;
        const FVector Join = It->JoinPoint();
        const float Key = GetLine()->FindInputKeyClosestToWorldLocation(Join);
        if (FVector::Dist2D(Join, GetLine()->GetLocationAtSplineInputKey(Key, ESplineCoordinateSpace::World)) < 150.0f)
            Bays.Add({*It, GetLine()->GetDistanceAlongSplineAtSplineInputKey(Key)});
    }
    Bays.Sort([](const FBayStop& A, const FBayStop& B) { return A.At < B.At; });
}

void AFactoryVehiclePath::ReleaseBay()
{
    if (AFactoryTruckBay* Old = Bay.Get())
        if (Old->Occupant == this) Old->Occupant = nullptr;
    Bay.Reset();
    BayState = EBayState::None;
}

float AFactoryVehiclePath::BaySpeedLimit()
{
    if (bBayDone || bDocked) return TNumericLimits<float>::Max();
    // The furthest free bay ahead (the nearer ones stay for the vehicles behind); keeps it while heading there.
    int32 Choice = INDEX_NONE;
    for (int32 Index = 0; Index < Bays.Num(); ++Index)
    {
        const AFactoryTruckBay* Candidate = Bays[Index].Bay.Get();
        if (Candidate && Bays[Index].At >= Distance - 1.0f && (Candidate->IsFree() || Candidate->Occupant == this)) Choice = Index;
    }
    if (Choice == INDEX_NONE)
    {
        ReleaseBay();
        return TNumericLimits<float>::Max();
    }
    if (Bay.Get() != Bays[Choice].Bay.Get()) ReleaseBay();
    Bay = Bays[Choice].Bay;
    Bay->Occupant = this;
    BayAt = Bays[Choice].At;
    const float Room = FMath::Max(BayAt - Distance, 0.0f);
    MaxAdvance = FMath::Min(MaxAdvance, Room);
    if (Room < 1.0f)
    {
        // There: back in along the maneuver, from where it joins the line.
        Distance = BayAt;
        CurrentSpeed = 0.0f;
        BayS = Bay->Length();
        BayState = EBayState::Reversing;
        return 0.0f;
    }
    return FMath::Max(FMath::Sqrt(2.0f * Braking * Room), 15.0f);
}

bool AFactoryVehiclePath::WantsBayDoorOpen() const
{
    if (!Bay.IsValid() || BayState == EBayState::Leaving || bBayDone) return false;
    if (BayState != EBayState::None) return true;
    // On its way: through the last barrier before the bay (its back past the arm).
    const FGateStop* Last = nullptr;
    for (const FGateStop& Stop : Gates)
        if (Stop.Gate.IsValid() && Stop.At < BayAt && (!Last || Stop.At > Last->At)) Last = &Stop;
    return !Last || Distance - RearLength >= Last->At;
}

void AFactoryVehiclePath::DockAtBayBelt()
{
    // The rear axle is where the bay stands; the belt ends at the dock, just behind the cargo. The bay's own point, not
    // the mesh: the mesh is still where the last frame placed it (a long frame left it short of the bay).
    const AFactoryTruckBay* InBay = Bay.Get();
    const FVector Rear = InBay ? InBay->PointAt(0.0f) : Vehicle->GetComponentLocation();
    AFactoryLoadingBelt* Best = nullptr;
    float BestGap = BayLoadReach;
    for (TActorIterator<AFactoryLoadingBelt> It(GetWorld()); It; ++It)
    {
        if (It->GetNext() || UFactoryUnlockSubsystem::IsLocked(*It) || (It->Docked && It->Docked != this)) continue;
        const float Gap = FVector::Dist2D(It->GetDeliveryPoint(), Rear);
        if (Gap < BestGap) { BestGap = Gap; Best = *It; }
    }
    if (!Best || FreeCargoSlots() <= 0) return;
    BayBelt = Best;
    Best->Docked = this;
    bDocked = bBayLoading = bDoorWantOpen = true;
    DockIndex = INDEX_NONE;
}

void AFactoryVehiclePath::UndockBayBelt()
{
    if (AFactoryLoadingBelt* Belt = BayBelt.Get())
        if (Belt->Docked == this) Belt->Docked = nullptr;
    BayBelt.Reset();
    bBayLoading = false;
}

bool AFactoryVehiclePath::LineClearAt(float At) const
{
    for (TActorIterator<AFactoryVehiclePath> It(GetWorld()); It; ++It)
        if (*It != this && !UFactoryUnlockSubsystem::IsLocked(*It) && !It->IsOffLine() && It->GetLine() == GetLine()
            && It->Distance - It->RearLength < At + FrontLength + FollowGap && It->Distance + It->FrontLength > At - RearLength - FollowGap)
            return false;
    return true;
}

bool AFactoryVehiclePath::ManeuverBlocked(float Step, float DeltaSeconds)
{
    if (Step == 0.0f) return false;
    // Where the axles would be after Step along the maneuver (backing in: the back leads).
    const float Was = BayS;
    BayS += Step;
    FVector NewRear, NewFront;
    AxlePoints(Distance, NewRear, NewFront);
    BayS = Was;
    AFactoryVehiclePath* Blocker = nullptr;
    if (!WouldHit(NewRear, NewFront, Step < 0.0f ? NewRear - NewFront : NewFront - NewRear, Blocker))
    {
        BlockedFor = 0.0f;
        return false;
    }
    NoteBlocked(Blocker, DeltaSeconds);
    return true;
}

void AFactoryVehiclePath::TickBay(float DeltaSeconds)
{
    AFactoryTruckBay* InBay = Bay.Get();
    if (!InBay)
    {
        BayState = EBayState::None;
        return;
    }
    const float Length = InBay->Length();
    float Step = 0.0f;
    if (BayState == EBayState::Reversing)
    {
        // Slows down to the end of the bay.
        const float Limit = FMath::Min(InBay->ManeuverSpeed, FMath::Max(FMath::Sqrt(2.0f * Braking * BayS), 15.0f));
        CurrentSpeed = FMath::Min(Limit, CurrentSpeed + Acceleration * DeltaSeconds);
        Step = -FMath::Min(CurrentSpeed * DeltaSeconds, BayS);
        if (ManeuverBlocked(Step, DeltaSeconds)) Step = 0.0f;
        BayS += Step;
        if (BayS <= 0.0f)
        {
            BayS = 0.0f;
            CurrentSpeed = 0.0f;
            ParkedFor = 0.0f;
            BayState = EBayState::Parked;
            if (!bDumpTruck) DockAtBayBelt();
        }
    }
    else if (BayState == EBayState::Parked)
    {
        ParkedFor += DeltaSeconds;
        if (bDumpTruck)
        {
            // Tips its load; once the box is down and the door shut, out again.
            if (!bServed && TickDump(DeltaSeconds)) bServed = true;
            if (bServed && LineClearAt(BayAt)) BayState = EBayState::Leaving;
        }
        else
        {
            // Full (and the door shut), or its time is up: out again once the line is clear there.
            const bool bLoaded = bServed && !bDocked;
            const bool bTimeUp = InBay->ParkSeconds > 0.0f && ParkedFor >= InBay->ParkSeconds && !bBayLoading;
            if ((bLoaded || bTimeUp) && LineClearAt(BayAt)) BayState = EBayState::Leaving;
        }
    }
    else if (BayState == EBayState::Leaving)
    {
        CurrentSpeed = FMath::Min(InBay->ManeuverSpeed, CurrentSpeed + Acceleration * DeltaSeconds);
        Step = CurrentSpeed * DeltaSeconds;
        if (ManeuverBlocked(Step, DeltaSeconds)) Step = 0.0f;
        BayS += Step;
        if (BayS >= Length)
        {
            // Back on the line where it left it, and on with the trip.
            Distance = BayAt + (BayS - Length);
            ReleaseBay();
            bBayDone = true;
        }
    }
    RearSpin = FMath::Fmod(RearSpin + FMath::RadiansToDegrees(Step / RearWheelRadius), 360.0f);
    FrontSpin = FMath::Fmod(FrontSpin + FMath::RadiansToDegrees(Step / FrontWheelRadius), 360.0f);
    FVector Rear, Front;
    AxlePoints(Distance, Rear, Front);
    const FVector Heading = Front - Rear;
    const FVector Ahead = BayState != EBayState::None ? InBay->DirectionAt(BayS + Wheelbase) : DirectionAt(Distance + Wheelbase);
    const float Steer = FMath::Clamp(FRotator::NormalizeAxis(FMath::RadiansToDegrees(
        FMath::Atan2(Ahead.Y, Ahead.X) - FMath::Atan2(Heading.Y, Heading.X))), -MaxSteer, MaxSteer);
    UpdateCargo(DeltaSeconds);
    Place(Distance, Steer);
    UpdateLoad(DeltaSeconds);
}

bool AFactoryVehiclePath::IsReadyToLoad() const
{
    return bDocked && bDoorWantOpen && DoorOpen >= 1.0f && FreeCargoSlots() > 0;
}

FTransform AFactoryVehiclePath::SlotTransform(int32 Slot) const
{
    // Rows across (far one first), each filled from the front of the cargo to the back.
    const int32 Rows = FMath::Max(CargoRows.Num(), 1);
    const int32 PerRow = FMath::Max(1, FMath::DivideAndRoundUp(CargoCapacity, Rows));
    const int32 Row = FMath::Min(Slot / PerRow, Rows - 1), Column = Slot % PerRow;
    const float Step = (CargoFrontX - CargoBackX) / PerRow;
    const float Y = CargoRows.IsValidIndex(Row) ? CargoRows[Row] : 0.0f;
    // A small turn that is always the same for a slot, so the load does not look copied.
    const float Yaw = FMath::Sin(Slot * 12.9898f) * 5.0f;
    return FTransform(FRotator(0, Yaw, 0), FVector(CargoFrontX - Step * (Column + 0.5f), Y, CargoFloor));
}

bool AFactoryVehiclePath::ReceiveBox(UStaticMesh* Mesh, const FTransform& FromWorld)
{
    if (!Mesh || !IsReadyToLoad()) return false;
    auto* Box = NewObject<UStaticMeshComponent>(this);
    Box->SetStaticMesh(Mesh);
    Box->SetMobility(EComponentMobility::Movable);
    Box->SetCollisionEnabled(ECollisionEnabled::NoCollision);
    Box->SetupAttachment(Vehicle);
    Box->RegisterComponent();
    Box->SetWorldTransform(FromWorld);
    Cargo.Add(Box);
    Flights.Add({Box, Box->GetRelativeTransform(), Loaded + Flights.Num(), 0.0f});
    return true;
}

void AFactoryVehiclePath::UpdateCargo(float DeltaSeconds)
{
    // Boxes hop from the belt end to their place in an arc.
    for (int32 Index = Flights.Num() - 1; Index >= 0; --Index)
    {
        FFlight& Flight = Flights[Index];
        Flight.T = FMath::Min(Flight.T + DeltaSeconds / HopSeconds, 1.0f);
        const FTransform To = SlotTransform(Flight.Slot);
        const float Eased = FMath::InterpEaseInOut(0.0f, 1.0f, Flight.T, 2.0f);
        FVector Location = FMath::Lerp(Flight.From.GetLocation(), To.GetLocation(), Eased);
        Location.Z += 35.0f * FMath::Sin(PI * Flight.T);
        if (Flight.Box)
            Flight.Box->SetRelativeLocationAndRotation(Location, FQuat::Slerp(Flight.From.GetRotation(), To.GetRotation(), Eased));
        if (Flight.T >= 1.0f)
        {
            ++Loaded;
            Flights.RemoveAt(Index);
        }
    }
    // Full and every box in place: the door closes; once shut the vehicle leaves. Not full but a later
    // belt is free now: the door closes too and it moves on there.
    if (bDocked && Flights.IsEmpty() && bDoorWantOpen)
    {
        bool bLaterFree = false;
        if (!bBayLoading)   // in a bay it stays until full
            for (int32 Index = DockIndex + 1; Index < Docks.Num(); ++Index)
                bLaterFree |= DockFreeFor(Index);
        if (Loaded >= CargoCapacity || bLaterFree) bDoorWantOpen = false;
    }
    DoorOpen = FMath::FInterpConstantTo(DoorOpen, bDoorWantOpen ? 1.0f : 0.0f, DeltaSeconds, 1.0f / DoorSeconds);
    if (bDocked && !bDoorWantOpen && DoorOpen <= 0.0f)
    {
        if (Docks.IsValidIndex(DockIndex) && Docks[DockIndex].Belt.IsValid()) Docks[DockIndex].Belt->Docked = nullptr;
        UndockBayBelt();
        Reserve(INDEX_NONE);
        bDocked = false;
        bServed = Loaded >= CargoCapacity;
        DockIndex = INDEX_NONE;
    }
    // "n/10" over the cargo from the first box on, facing the camera.
    const bool bShow = Loaded > 0;
    Counter->SetHiddenInGame(!bShow);
    if (bShow)
    {
        const bool bFull = Loaded >= CargoCapacity;
        Counter->SetText(FText::FromString(bFull ? FString::Printf(TEXT("%d/%d LLENO"), Loaded, CargoCapacity)
                                                 : FString::Printf(TEXT("%d/%d"), Loaded, CargoCapacity)));
        Counter->SetTextRenderColor(bFull ? FColor(255, 92, 70) : FColor(46, 232, 199));
        if (const APlayerController* Player = GetWorld()->GetFirstPlayerController())
            if (Player->PlayerCameraManager)
                Counter->SetWorldRotation((Player->PlayerCameraManager->GetCameraLocation() - Counter->GetComponentLocation()).Rotation());
    }
}

void AFactoryVehiclePath::Deliver()
{
    if (bDelivered || Loaded <= 0) return;
    bDelivered = true;
    if (auto* Mission = GetWorld()->GetSubsystem<UFactoryMissionSubsystem>()) Mission->AddDelivered(Loaded);
}

void AFactoryVehiclePath::ResetCargo()
{
    bDelivered = false;
    for (UStaticMeshComponent* Box : Cargo)
        if (Box) Box->DestroyComponent();
    Cargo.Reset();
    Flights.Reset();
    Loaded = 0;
    if (Docks.IsValidIndex(DockIndex) && Docks[DockIndex].Belt.IsValid() && Docks[DockIndex].Belt->Docked == this)
        Docks[DockIndex].Belt->Docked = nullptr;
    UndockBayBelt();
    Reserve(INDEX_NONE);
    bDocked = bServed = bDoorWantOpen = false;
    DockIndex = INDEX_NONE;
    DoorOpen = 0.0f;
    if (Counter) Counter->SetHiddenInGame(true);
}
