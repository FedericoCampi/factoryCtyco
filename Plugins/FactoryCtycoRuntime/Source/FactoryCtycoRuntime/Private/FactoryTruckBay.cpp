#include "FactoryTruckBay.h"
#include "Components/SplineComponent.h"
#include "FactoryVehiclePath.h"

AFactoryTruckBay::AFactoryTruckBay()
{
    // Ticks in play for the dock door.
    PrimaryActorTick.bCanEverTick = true;
    RootComponent = CreateDefaultSubobject<USceneComponent>(TEXT("Root"));
    Maneuver = CreateDefaultSubobject<USplineComponent>(TEXT("Maneuver"));
    Maneuver->SetupAttachment(RootComponent);
    Maneuver->SetClosedLoop(false);
    Maneuver->SetDrawDebug(true);
    // Straight out of the bay until it is connected to a line.
    Maneuver->ClearSplinePoints(false);
    Maneuver->AddSplinePoint(FVector::ZeroVector, ESplineCoordinateSpace::Local, false);
    Maneuver->AddSplinePoint(FVector(1500, 0, 0), ESplineCoordinateSpace::Local, true);
}

void AFactoryTruckBay::OnConstruction(const FTransform& Transform)
{
    Super::OnConstruction(Transform);
    if (bAutoManeuver) Reconnect();
}

void AFactoryTruckBay::Reconnect()
{
    if (!Line) return;
    const USplineComponent* Road = Line->GetLine();
    if (!Road || Road->GetSplineLength() <= 0) return;
    const FTransform& T = GetActorTransform();
    // The point of the line nearest to the bay, then JoinAhead further along it.
    const float Near = Road->GetDistanceAlongSplineAtSplineInputKey(Road->FindInputKeyClosestToWorldLocation(GetActorLocation()));
    // The join diamond dragged: the point of the line nearest to it.
    if (Dragged(JoinHandle, PlacedJoin))
        JoinAhead = Road->GetDistanceAlongSplineAtSplineInputKey(Road->FindInputKeyClosestToWorldLocation(T.TransformPosition(JoinHandle))) - Near;
    const float At = FMath::Clamp(Near + JoinAhead, 0.0f, Road->GetSplineLength());
    // The bend diamond dragged: the curve passes there from now on.
    if (Dragged(BendHandle, PlacedBend))
    {
        bBend = true;
        BendPoint = BendHandle;
    }
    DrawManeuver(Road, At);
    // The diamonds go back onto the curve: at the bend (or halfway along) and at the join.
    BendHandle = PlacedBend = bBend ? BendPoint : T.InverseTransformPosition(PointAt(Length() / 2));
    JoinHandle = PlacedJoin = T.InverseTransformPosition(JoinPoint());
}

void AFactoryTruckBay::DrawManeuver(const USplineComponent* Road, float At)
{
    const FVector Join = Road->GetLocationAtDistanceAlongSpline(At, ESplineCoordinateSpace::World);
    const FVector Along = Road->GetDirectionAtDistanceAlongSpline(At, ESplineCoordinateSpace::World);
    const FVector Start = GetActorLocation();
    const FVector Out = GetActorForwardVector();
    Maneuver->ClearSplinePoints(false);
    Maneuver->AddSplinePoint(Start, ESplineCoordinateSpace::World, false);
    // Tangents as long as the gap they cross: out of the bay straight, into the line along it.
    float ExitReach = FVector::Dist(Start, Join), JoinReach = ExitReach;
    if (bBend)
    {
        // The middle point at the diamond, height included (drag it up or down to raise or lower the curve there).
        const FVector Middle = GetActorTransform().TransformPosition(BendPoint);
        Maneuver->AddSplinePoint(Middle, ESplineCoordinateSpace::World, false);
        ExitReach = FVector::Dist(Start, Middle);
        JoinReach = FVector::Dist(Middle, Join);
    }
    Maneuver->AddSplinePoint(Join, ESplineCoordinateSpace::World, false);
    const int32 Last = Maneuver->GetNumberOfSplinePoints() - 1;
    Maneuver->SetTangentAtSplinePoint(0, Out * ExitReach * ExitStraight, ESplineCoordinateSpace::World, false);
    Maneuver->SetTangentAtSplinePoint(Last, Along * JoinReach * JoinStraight, ESplineCoordinateSpace::World, false);
    Maneuver->UpdateSpline();
}

void AFactoryTruckBay::StraightenCurve()
{
    Modify();
    bBend = false;
    PlacedBend = FVector::ZeroVector;
    Reconnect();
}

void AFactoryTruckBay::BeginPlay()
{
    Super::BeginPlay();
    DoorOpen = 0.0f;
    if (DockDoor && DockDoor->GetRootComponent()) DoorScale = DockDoor->GetRootComponent()->GetRelativeScale3D();
}

void AFactoryTruckBay::Tick(float DeltaSeconds)
{
    Super::Tick(DeltaSeconds);
    USceneComponent* Door = DockDoor ? DockDoor->GetRootComponent() : nullptr;
    if (!Door) return;
    // Up from when the truck coming here passes the entrance booth until it starts out of the bay.
    const bool bWant = Occupant && Occupant->GetBay() == this && Occupant->WantsBayDoorOpen();
    const float Was = DoorOpen;
    DoorOpen = FMath::FInterpConstantTo(DoorOpen, bWant ? 1.0f : 0.0f, DeltaSeconds, 1.0f / DoorSeconds);
    if (DoorOpen == Was) return;
    const float Eased = FMath::InterpEaseInOut(0.0f, 1.0f, DoorOpen, 2.0f);
    Door->SetRelativeScale3D(FVector(DoorScale.X, DoorScale.Y, DoorScale.Z * FMath::Lerp(1.0f, DoorRolled, Eased)));
}

float AFactoryTruckBay::Length() const
{
    return Maneuver->GetSplineLength();
}

FVector AFactoryTruckBay::PointAt(float S) const
{
    const float L = Length();
    const float Clamped = FMath::Clamp(S, 0.0f, L);
    // Past the bay end it goes on straight (the front axle of a truck parked right at the end).
    return Maneuver->GetLocationAtDistanceAlongSpline(Clamped, ESplineCoordinateSpace::World)
        + DirectionAt(Clamped) * (S - Clamped);
}

FVector AFactoryTruckBay::DirectionAt(float S) const
{
    return Maneuver->GetDirectionAtDistanceAlongSpline(FMath::Clamp(S, 0.0f, Length()), ESplineCoordinateSpace::World);
}
