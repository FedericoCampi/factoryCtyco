#include "FactoryVehiclePath.h"
#include "Camera/PlayerCameraManager.h"
#include "Components/PoseableMeshComponent.h"
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
#include "GameFramework/PlayerController.h"

AFactoryVehiclePath::AFactoryVehiclePath()
{
    PrimaryActorTick.bCanEverTick = true;
    RootComponent = CreateDefaultSubobject<USceneComponent>(TEXT("Root"));
    Path = CreateDefaultSubobject<USplineComponent>(TEXT("Path"));
    Path->SetupAttachment(RootComponent);
    Path->SetClosedLoop(false);
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
}

void AFactoryVehiclePath::OnConstruction(const FTransform& Transform)
{
    Super::OnConstruction(Transform);
    BuildRoad();
    Vehicle->SetSkinnedAssetAndUpdate(VehicleMesh);
    for (UStaticMeshComponent* Wrap : {WrapDoor.Get(), WrapSide.Get()}) Wrap->SetStaticMesh(WrapMesh);
    WrapSide->SetRelativeLocationAndRotation(WrapCenter, FRotator(0, 180, 0));
    WrapDoor->SetRelativeLocationAndRotation(FVector(WrapCenter.X, -WrapCenter.Y, WrapCenter.Z), FRotator::ZeroRotator);
    RestRotation.Reset();
    DoorRest.Reset();
    CacheRestPose();
    Place(FMath::Min(EditorPreviewDistance, GetLine()->GetSplineLength()), 0.0f);
}

void AFactoryVehiclePath::BeginPlay()
{
    Super::BeginPlay();
    Distance = 0.0f;
    CurrentSpeed = Speed;
    Paused = StartDelay;
    bGatesFound = false;
    RearSpin = FrontSpin = 0.0f;
    ResetCargo();
    CacheRestPose();
    Place(Distance, 0.0f);
}

void AFactoryVehiclePath::CacheRestPose()
{
    if (!VehicleMesh || !RestRotation.IsEmpty()) return;
    for (const TArray<FName>* Wheels : {&FrontWheels, &RearWheels})
        for (const FName& Wheel : *Wheels)
            if (Vehicle->GetBoneIndex(Wheel) != INDEX_NONE)
                RestRotation.Add(Wheel, Vehicle->GetBoneRotationByName(Wheel, EBoneSpaces::ComponentSpace).Quaternion());
    if (Vehicle->GetBoneIndex(DoorBone) != INDEX_NONE)
    {
        RestRotation.Add(DoorBone, Vehicle->GetBoneRotationByName(DoorBone, EBoneSpaces::ComponentSpace).Quaternion());
        DoorRest = Vehicle->GetBoneTransformByName(DoorBone, EBoneSpaces::ComponentSpace);
    }
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
    const FVector Rear = PointAt(Along), Front = PointAt(Along + Wheelbase);
    const FVector Heading = Front - Rear;
    const float Yaw = FMath::RadiansToDegrees(FMath::Atan2(Heading.Y, Heading.X));
    const float Pitch = FMath::RadiansToDegrees(FMath::Atan2(Heading.Z, Heading.Size2D()));
    Vehicle->SetWorldLocationAndRotation(Rear, FRotator(Pitch, Yaw, 0.0f));
    // Wheels: roll about the axle (component Y), then the front ones steer about the vertical.
    // A wheel rolling forward turns its top toward +X: negative pitch.
    for (const TArray<FName>* Wheels : {&FrontWheels, &RearWheels})
    {
        const bool bFront = Wheels == &FrontWheels;
        const FQuat Delta = FRotator(-(bFront ? FrontSpin : RearSpin), bFront ? Steer : 0.0f, 0.0f).Quaternion();
        for (const FName& Wheel : *Wheels)
            if (const FQuat* Rest = RestRotation.Find(Wheel))
                Vehicle->SetBoneRotationByName(Wheel, (Delta * *Rest).Rotator(), EBoneSpaces::ComponentSpace);
    }
    // Cargo door: hinged along the bottom, it folds out about the vehicle's forward axis.
    if (const FQuat* Rest = RestRotation.Find(DoorBone))
    {
        const float Eased = FMath::InterpEaseInOut(0.0f, 1.0f, DoorOpen, 2.0f);
        Vehicle->SetBoneRotationByName(DoorBone, (FRotator(0, 0, DoorOpenAngle * Eased).Quaternion() * *Rest).Rotator(), EBoneSpaces::ComponentSpace);
        // The wrap on the door swings with it: same place relative to the bone as at rest.
        if (DoorRest.IsSet() && WrapMesh)
        {
            const FTransform AtRest(FRotator::ZeroRotator, FVector(WrapCenter.X, -WrapCenter.Y, WrapCenter.Z));
            WrapDoor->SetRelativeTransform(AtRest.GetRelativeTransform(DoorRest.GetValue())
                                           * Vehicle->GetBoneTransformByName(DoorBone, EBoneSpaces::ComponentSpace));
        }
        // The roof is simply not there while the door is open at all; it is back once the door is shut.
        // Hidden, not moved: rewriting that bone's transform (scale) lost the roof even at scale 1.
        const bool bHide = DoorOpen > 0.0f;
        if (bHide != bRoofHidden && Vehicle->GetBoneIndex(RoofBone) != INDEX_NONE)
        {
            if (bHide) Vehicle->HideBoneByName(RoofBone, EPhysBodyOp::PBO_None);
            else Vehicle->UnHideBoneByName(RoofBone);
            bRoofHidden = bHide;
        }
    }
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
        ResetCargo();   // a new trip comes empty
        Place(Distance, 0.0f);
        return;
    }
    if (!bGatesFound) { FindGates(); FindDocks(); }
    MaxAdvance = TNumericLimits<float>::Max();
    // Brakes smoothly for a lowered barrier, the loading stop or the vehicle ahead, and sets off again when free.
    const float Limit = FMath::Min(FMath::Min3(Speed, GateSpeedLimit(), DockSpeedLimit()), FollowSpeedLimit());
    CurrentSpeed = Limit < CurrentSpeed ? Limit : FMath::Min(Limit, CurrentSpeed + Acceleration * DeltaSeconds);
    const float Step = FMath::Clamp(CurrentSpeed * DeltaSeconds, 0.0f, FMath::Max(MaxAdvance, 0.0f));
    if (Step < CurrentSpeed * DeltaSeconds) CurrentSpeed = FMath::Min(CurrentSpeed, Step / FMath::Max(DeltaSeconds, KINDA_SMALL_NUMBER));
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
        if (*It != this && !UFactoryUnlockSubsystem::IsLocked(*It) && It->GetLine() == GetLine() && It->Distance > Distance
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
        if (*It != this && !UFactoryUnlockSubsystem::IsLocked(*It) && It->GetLine() == GetLine() && It->Distance > Distance)
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
        if (*It != this && !UFactoryUnlockSubsystem::IsLocked(*It) && It->GetLine() == GetLine()
            && It->Distance - It->RearLength < FrontLength + FollowGap && It->Distance + It->FrontLength > -RearLength - FollowGap)
            return false;
    return true;
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
        for (int32 Index = DockIndex + 1; Index < Docks.Num(); ++Index)
            bLaterFree |= DockFreeFor(Index);
        if (Loaded >= CargoCapacity || bLaterFree) bDoorWantOpen = false;
    }
    DoorOpen = FMath::FInterpConstantTo(DoorOpen, bDoorWantOpen ? 1.0f : 0.0f, DeltaSeconds, 1.0f / DoorSeconds);
    if (bDocked && !bDoorWantOpen && DoorOpen <= 0.0f)
    {
        if (Docks.IsValidIndex(DockIndex) && Docks[DockIndex].Belt.IsValid()) Docks[DockIndex].Belt->Docked = nullptr;
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
    Reserve(INDEX_NONE);
    bDocked = bServed = bDoorWantOpen = false;
    DockIndex = INDEX_NONE;
    DoorOpen = 0.0f;
    if (Counter) Counter->SetHiddenInGame(true);
}
