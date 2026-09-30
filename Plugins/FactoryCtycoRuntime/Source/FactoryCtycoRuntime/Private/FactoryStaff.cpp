#include "FactoryStaff.h"
#include "FactoryEconomy.h"
#include "Components/CapsuleComponent.h"
#include "Components/SkeletalMeshComponent.h"
#include "Components/SplineComponent.h"
#include "Components/StaticMeshComponent.h"
#include "Components/TextRenderComponent.h"
#include "Engine/StaticMesh.h"
#include "Engine/StaticMeshActor.h"
#include "Engine/World.h"
#include "EngineUtils.h"
#include "FactoryElevator.h"
#include "FactoryGateBarrier.h"
#include "FactoryMission.h"
#include "FactoryVehiclePath.h"
#include "GameFramework/CharacterMovementComponent.h"
#include "Kismet/GameplayStatics.h"
#include "NavigationPath.h"
#include "NavigationSystem.h"
#include "RobotLocomotionComponent.h"

AFactoryWorkerSpawn::AFactoryWorkerSpawn()
{
    RootComponent = CreateDefaultSubobject<USceneComponent>(TEXT("Root"));
    CarRoute = CreateDefaultSubobject<USplineComponent>(TEXT("CarRoute"));
    CarRoute->SetupAttachment(RootComponent);
    CarRoute->SetClosedLoop(false);
    CarRoute->SetSplinePoints({FVector::ZeroVector, FVector(800, 0, 0)}, ESplineCoordinateSpace::Local);
    Label = CreateDefaultSubobject<UTextRenderComponent>(TEXT("Label"));
    Label->SetupAttachment(RootComponent);
    Label->SetRelativeLocationAndRotation(FVector(0, 0, 150), FRotator(0, 180, 0));
    Label->SetHorizontalAlignment(EHTA_Center);
    Label->SetWorldSize(40.0f);
    Label->SetTextRenderColor(FColor(255, 138, 31));
    Label->SetText(FText::FromString(TEXT("LLEGAN LOS CONTRATADOS")));
    Label->SetHiddenInGame(true);   // only a marker for the editor
    Label->SetCollisionEnabled(ECollisionEnabled::NoCollision);
}

AFactoryGateBarrier* AFactoryWorkerSpawn::FindWorkplace() const
{
    if (Workplace) return Workplace;
    AFactoryGateBarrier* Best = nullptr;
    double BestDistance = TNumericLimits<double>::Max();
    for (TActorIterator<AFactoryGateBarrier> It(GetWorld()); It; ++It)
    {
        const double Distance = FVector::DistSquared(GetActorLocation(), It->GetActorLocation());
        if (Distance < BestDistance) { BestDistance = Distance; Best = *It; }
    }
    return Best;
}

AFactoryWorker::AFactoryWorker()
{
    PrimaryActorTick.bCanEverTick = true;
    AutoPossessAI = EAutoPossessAI::Disabled;   // no controller: it walks by itself
    AIControllerClass = nullptr;
    bUseControllerRotationYaw = false;
    UCharacterMovementComponent* Move = GetCharacterMovement();
    Move->bRunPhysicsWithNoController = true;
    Move->bOrientRotationToMovement = true;
    Move->RotationRate = FRotator(0, 540, 0);
    Locomotion = CreateDefaultSubobject<URobotLocomotionComponent>(TEXT("Locomotion"));
}

void AFactoryWorker::CopyLook(const ACharacter* Source)
{
    if (!Source) return;
    const USkeletalMeshComponent* From = Source->GetMesh();
    USkeletalMeshComponent* To = GetMesh();
    if (From && To)
    {
        To->SetSkeletalMeshAsset(From->GetSkeletalMeshAsset());
        To->SetRelativeTransform(From->GetRelativeTransform());
        for (int32 Slot = 0; Slot < From->GetNumMaterials(); ++Slot) To->SetMaterial(Slot, From->GetMaterial(Slot));
    }
    if (const UCapsuleComponent* Capsule = Source->GetCapsuleComponent())
        GetCapsuleComponent()->SetCapsuleSize(Capsule->GetUnscaledCapsuleRadius(), Capsule->GetUnscaledCapsuleHalfHeight());
    if (const auto* Walker = Source->FindComponentByClass<URobotLocomotionComponent>())
    {
        // Same animations and speeds; the component starts playing them on its next tick.
        Locomotion->Locomotion = Walker->Locomotion;
        Locomotion->AirbornePose = Walker->AirbornePose;
        Locomotion->CarryLocomotion = Walker->CarryLocomotion;
        Locomotion->AuthoredWalkSpeed = Walker->AuthoredWalkSpeed;
        Locomotion->WalkSpeed = Walker->WalkSpeed;
        Locomotion->FastWalkSpeed = Walker->FastWalkSpeed;
    }
}

FString AFactoryWorker::Describe() const
{
    switch (State)
    {
    case EFactoryWorkerState::Driving: return TEXT("Llegando en auto");
    case EFactoryWorkerState::Walking: return bSecondLeg ? TEXT("Caminando a la cabina") : TEXT("Caminando al ascensor");
    case EFactoryWorkerState::Riding: return TEXT("En el ascensor");
    case EFactoryWorkerState::Acting: return TEXT("Levantando la barrera");
    default: return TEXT("En la cabina, esperando camiones");
    }
}

void AFactoryWorker::SetOnFoot(bool bOnFoot)
{
    SetActorHiddenInGame(!bOnFoot);
    SetActorEnableCollision(bOnFoot);
    GetCharacterMovement()->StopMovementImmediately();
    GetCharacterMovement()->SetMovementMode(bOnFoot ? MOVE_Walking : MOVE_None);
}

FVector AFactoryWorker::WorkSpot() const
{
    return Workplace && Workplace->Booth ? Workplace->Booth->GetComponentLocation() : GetActorLocation();
}

FVector AFactoryWorker::WorkDoor() const
{
    return Workplace && Workplace->Booth ? Workplace->Booth->GetComponentTransform().TransformPosition(FVector(-150, 0, 0)) : WorkSpot();
}

void AFactoryWorker::AddWorkLeg(const FVector& From)
{
    const FVector Door = WorkDoor();
    const UNavigationPath* Found = UNavigationSystemV1::FindPathToLocationSynchronously(this, From, Door, this);
    if (Found && Found->IsValid() && Found->PathPoints.Num() > 1)
    {
        for (int32 Index = 1; Index < Found->PathPoints.Num(); ++Index) Path.Add(Found->PathPoints[Index]);
        if (Found->IsPartial()) Path.Add(Door);
    }
    else Path.Add(Door);
    Path.Add(WorkSpot());
    Stuck = 0.0f;
    BestGap = TNumericLimits<float>::Max();
}

FVector AFactoryWorker::ElevatorFront(const AFactoryElevator* Elevator)
{
    // The doors are on the elevator's +X side.
    return Elevator->GetActorLocation() + Elevator->GetActorForwardVector() * 230.0f;
}

AFactoryElevator* AFactoryWorker::NearestElevator(const FVector& Where) const
{
    AFactoryElevator* Best = nullptr;
    double BestDistance = TNumericLimits<double>::Max();
    for (TActorIterator<AFactoryElevator> It(GetWorld()); It; ++It)
    {
        const FVector Delta = It->GetActorLocation() - Where;
        if (FMath::Abs(Delta.Z) > 300.0f) continue;   // only on the same floor
        if (Delta.SizeSquared2D() < BestDistance) { BestDistance = Delta.SizeSquared2D(); Best = *It; }
    }
    return Best;
}

void AFactoryWorker::PlanTo(const FVector& Goal, const TArray<FVector>& Extra)
{
    Path.Reset();
    const UNavigationPath* Found = UNavigationSystemV1::FindPathToLocationSynchronously(this, GetActorLocation(), Goal, this);
    if (Found && Found->IsValid() && Found->PathPoints.Num() > 1)
    {
        for (int32 Index = 1; Index < Found->PathPoints.Num(); ++Index) Path.Add(Found->PathPoints[Index]);
        if (Found->IsPartial()) Path.Add(Goal);
    }
    else
        Path.Add(Goal);   // no navigation there: straight
    Path.Append(Extra);
    Stuck = 0.0f;
    BestGap = TNumericLimits<float>::Max();
}

void AFactoryWorker::Begin()
{
    if (Spawn) Workplace = Spawn->FindWorkplace();
    const USplineComponent* Line = Spawn ? Spawn->CarRoute.Get() : nullptr;
    TArray<UStaticMesh*> Cars;
    if (Spawn) for (UStaticMesh* CarMesh : Spawn->CarMeshes) if (CarMesh) Cars.Add(CarMesh);
    if (Line && Line->GetNumberOfSplinePoints() > 1 && Cars.Num() > 0)
    {
        FActorSpawnParameters Params;
        Params.SpawnCollisionHandlingOverride = ESpawnActorCollisionHandlingMethod::AlwaysSpawn;
        Car = GetWorld()->SpawnActor<AStaticMeshActor>(AStaticMeshActor::StaticClass(), Line->GetLocationAtSplinePoint(0, ESplineCoordinateSpace::World), FRotator::ZeroRotator, Params);
        if (Car)
        {
            Car->GetStaticMeshComponent()->SetMobility(EComponentMobility::Movable);
            Car->GetStaticMeshComponent()->SetStaticMesh(Cars[FMath::RandRange(0, Cars.Num() - 1)]);
            SetOnFoot(false);
            State = EFactoryWorkerState::Driving;
            CarAlong = 0.0f;
            Drive(0.0f);
            return;
        }
    }
    SetOnFoot(true);
    StartWalking();
}

void AFactoryWorker::StartWalking()
{
    State = EFactoryWorkerState::Walking;
    const FVector Here = GetActorLocation();
    AFactoryElevator* HereElevator = NearestElevator(Here);
    AFactoryElevator* WorkElevator = NearestElevator(WorkSpot());
    if (HereElevator && WorkElevator && HereElevator != WorkElevator)
    {
        FromElevator = HereElevator;
        ToElevator = WorkElevator;
        bSecondLeg = false;
        // Through the elevator's approach points if it has them, then to its doors and in.
        TArray<FVector> Points;
        for (const FVector& Local : HereElevator->Approach) Points.Add(HereElevator->GetActorTransform().TransformPosition(Local));
        Points.Add(ElevatorFront(HereElevator));
        Points.Add(HereElevator->GetActorLocation());
        const FVector First = Points[0];
        Points.RemoveAt(0);
        PlanTo(First, Points);
    }
    else
    {
        bSecondLeg = true;
        Path.Reset();
        AddWorkLeg(Here);
    }
}

void AFactoryWorker::Tick(float DeltaSeconds)
{
    Super::Tick(DeltaSeconds);
    switch (State)
    {
    case EFactoryWorkerState::Driving: Drive(DeltaSeconds); break;
    case EFactoryWorkerState::Walking: Walk(DeltaSeconds); break;
    case EFactoryWorkerState::Riding: Ride(DeltaSeconds); break;
    default: Work(DeltaSeconds); break;
    }
}

void AFactoryWorker::Drive(float DeltaSeconds)
{
    const USplineComponent* Line = Spawn ? Spawn->CarRoute.Get() : nullptr;
    if (!Line || !Car) { SetOnFoot(true); StartWalking(); return; }
    const float Length = Line->GetSplineLength();
    const float Speed = FMath::Min(Spawn->CarSpeed, 60.0f + (Length - CarAlong) * 1.2f);   // brakes into the space
    CarAlong = FMath::Min(CarAlong + Speed * DeltaSeconds, Length);
    const FVector Where = Line->GetLocationAtDistanceAlongSpline(CarAlong, ESplineCoordinateSpace::World);
    const FVector Heading = Line->GetDirectionAtDistanceAlongSpline(CarAlong, ESplineCoordinateSpace::World);
    Car->SetActorLocationAndRotation(Where, FRotator(0, Heading.Rotation().Yaw, 0));
    if (CarAlong < Length) return;
    // Parked: it gets out behind the car (the aisle side) and heads for the elevator.
    const float HalfHeight = GetCapsuleComponent()->GetScaledCapsuleHalfHeight();
    const FVector Out = Car->GetActorTransform().TransformPosition(FVector(-300, -40, 0)) + FVector(0, 0, HalfHeight + 5.0f);
    SetActorLocationAndRotation(Out, FRotator(0, Car->GetActorRotation().Yaw + 180.0f, 0), false, nullptr, ETeleportType::TeleportPhysics);
    SetOnFoot(true);
    StartWalking();
}

void AFactoryWorker::Walk(float DeltaSeconds)
{
    if (Path.IsEmpty())
    {
        if (!bSecondLeg && ToElevator.IsValid())
        {
            State = EFactoryWorkerState::Riding;
            RideLeft = RideSeconds;
            SetOnFoot(false);
        }
        else ArriveAtWork();
        return;
    }
    const FVector Here = GetActorLocation();
    const FVector Target = Path[0];
    const float Gap = FVector::Dist2D(Here, Target);
    if (Gap < (Path.Num() == 1 ? 25.0f : 45.0f))
    {
        Path.RemoveAt(0);
        Stuck = 0.0f;
        BestGap = TNumericLimits<float>::Max();
        bReplanned = false;
        return;
    }
    AddMovementInput((Target - Here).GetSafeNormal2D(), 1.0f);
    // Held back (a wall, a car, the player) for a while: it slips to the point it was going to.
    if (Gap < BestGap - 2.0f) { BestGap = Gap; Stuck = 0.0f; }
    else if ((Stuck += DeltaSeconds) > 1.0f && !bReplanned)
    {
        // First look for the way again from here: the plan may have been made while the navigation was still
        // being built (then it goes straight), or something moved in between.
        bReplanned = true;
        const UNavigationPath* Found = UNavigationSystemV1::FindPathToLocationSynchronously(this, Here, Target, this);
        if (Found && Found->IsValid() && !Found->IsPartial() && Found->PathPoints.Num() > 2)
        {
            for (int32 Index = Found->PathPoints.Num() - 2; Index >= 1; --Index) Path.Insert(Found->PathPoints[Index], 0);
            Stuck = 0.0f;
            BestGap = TNumericLimits<float>::Max();
        }
    }
    else if (Stuck > 2.5f)
    {
        const float HalfHeight = GetCapsuleComponent()->GetScaledCapsuleHalfHeight();
        LastHeldAt = Here;
        SetActorLocation(FVector(Target.X, Target.Y, FMath::Max(Here.Z, Target.Z + HalfHeight)), false, nullptr, ETeleportType::TeleportPhysics);
        Path.RemoveAt(0);
        ++Skips;
        bReplanned = false;
        Stuck = 0.0f;
        BestGap = TNumericLimits<float>::Max();
    }
}

void AFactoryWorker::Ride(float DeltaSeconds)
{
    if ((RideLeft -= DeltaSeconds) > 0.0f) return;
    AFactoryElevator* To = ToElevator.Get();
    if (!To) { ArriveAtWork(); return; }
    const float HalfHeight = GetCapsuleComponent()->GetScaledCapsuleHalfHeight();
    SetActorLocationAndRotation(To->GetActorLocation() + FVector(0, 0, HalfHeight + 20.0f), To->GetActorRotation(), false, nullptr, ETeleportType::TeleportPhysics);
    SetOnFoot(true);
    State = EFactoryWorkerState::Walking;
    bSecondLeg = true;
    // Out of the doors first, then over the navigation mesh to the workplace.
    const FVector Front = ElevatorFront(To);
    Path.Reset();
    Path.Add(Front);
    AddWorkLeg(Front);
}

void AFactoryWorker::ArriveAtWork()
{
    State = EFactoryWorkerState::Working;
    Path.Reset();
    // At the post it faces the barrier.
    if (Workplace)
    {
        FVector Pivot, Tip;
        Workplace->GetArmLine(Pivot, Tip);
        const FVector Look = ((Pivot + Tip) / 2 - GetActorLocation()).GetSafeNormal2D();
        if (!Look.IsNearlyZero()) SetActorRotation(FRotator(0, Look.Rotation().Yaw, 0));
    }
}

void AFactoryWorker::Work(float DeltaSeconds)
{
    if (!Workplace) return;
    bool bTruckWaiting = false;
    for (TActorIterator<AFactoryVehiclePath> It(GetWorld()); It; ++It)
        if (!UFactoryUnlockSubsystem::IsLocked(*It) && It->GetWaitingGate() == Workplace) bTruckWaiting = true;
    if (bTruckWaiting && !Workplace->bWantOpen)
    {
        State = EFactoryWorkerState::Acting;
        if ((WaitingFor += DeltaSeconds) >= ReactionSeconds)
        {
            Workplace->SetOpen(true);
            ++Handled;
            WaitingFor = 0.0f;
        }
        return;
    }
    WaitingFor = 0.0f;
    State = Workplace->bWantOpen ? EFactoryWorkerState::Acting : EFactoryWorkerState::Working;
}

UFactoryStaffSubsystem* UFactoryStaffSubsystem::Get(const UObject* Context)
{
    const UWorld* World = Context ? Context->GetWorld() : nullptr;
    return World ? World->GetSubsystem<UFactoryStaffSubsystem>() : nullptr;
}

bool UFactoryStaffSubsystem::IsHired(FName Role) const
{
    return GetWorker(Role) != nullptr;
}

AFactoryWorker* UFactoryStaffSubsystem::GetWorker(FName Role) const
{
    const TObjectPtr<AFactoryWorker>* Found = Workers.Find(Role);
    return Found && IsValid(*Found) ? Found->Get() : nullptr;
}

AFactoryWorkerSpawn* UFactoryStaffSubsystem::FindSpawn(FName Role) const
{
    for (TActorIterator<AFactoryWorkerSpawn> It(GetWorld()); It; ++It)
        if (It->Job == Role) return *It;
    return nullptr;
}

bool UFactoryStaffSubsystem::CanHire(FName Role) const
{
    return !IsHired(Role) && FindSpawn(Role) != nullptr;
}

AFactoryWorker* UFactoryStaffSubsystem::Hire(FName Role)
{
    AFactoryWorkerSpawn* Spawn = FindSpawn(Role);
    if (!Spawn || IsHired(Role)) return nullptr;
    // Hiring is paid up front; without enough money nobody comes.
    if (UFactoryEconomySubsystem* Economy = UFactoryEconomySubsystem::Get(this))
        if (!Economy->Spend(Economy->GetHireCost(Role), FString::Printf(TEXT("Contratar: %s"), *Role.ToString()))) return nullptr;
    const ACharacter* Player = Cast<ACharacter>(UGameplayStatics::GetPlayerPawn(this, 0));
    const float HalfHeight = Player && Player->GetCapsuleComponent() ? Player->GetCapsuleComponent()->GetScaledCapsuleHalfHeight() : 90.0f;
    FActorSpawnParameters Params;
    Params.SpawnCollisionHandlingOverride = ESpawnActorCollisionHandlingMethod::AlwaysSpawn;
    AFactoryWorker* Worker = GetWorld()->SpawnActor<AFactoryWorker>(AFactoryWorker::StaticClass(),
        Spawn->GetActorLocation() + FVector(0, 0, HalfHeight + 5.0f), Spawn->GetActorRotation(), Params);
    if (!Worker) return nullptr;
    Worker->Job = Role;
    Worker->Spawn = Spawn;
    Worker->CopyLook(Player);
    Workers.Add(Role, Worker);
    Worker->Begin();
    return Worker;
}
