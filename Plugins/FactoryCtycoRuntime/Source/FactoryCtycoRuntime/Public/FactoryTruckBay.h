#pragma once

#include "CoreMinimal.h"
#include "GameFramework/Actor.h"
#include "FactoryTruckBay.generated.h"

class AFactoryVehiclePath;
class USplineComponent;

/**
 * A parking bay a truck backs into. The actor stands where the parked truck's rear axle ends up, with +X pointing out
 * of the bay (the way the parked truck faces). Maneuver is the line its rear axle follows when reversing: from here
 * (its first point) to the truck's line (its last point, which must lie on that line). A truck driving the line passes
 * the bay, stops with its rear axle where Maneuver joins the line, reverses along it into the bay and stays there
 * until it is full (it loads from a loading belt ending behind it) or ParkSeconds are up (0: no time limit), then
 * drives out along it and goes on. One truck per bay.
 * With bAutoManeuver, Maneuver is drawn by itself from here to Line, JoinAhead past the bay along it, and joins it
 * smoothly. Its shape is edited in the viewport with two diamonds: BendHandle (the middle of the curve: drag it and
 * the curve passes there) and JoinHandle (where it meets the line: it slides along the line). ExitStraight and
 * JoinStraight make the ends straighter or tighter; StraightenCurve forgets the bend. Turn bAutoManeuver off to shape
 * the spline points by hand (its last point must stay on the line).
 * DockDoor (the bay's sectional door in the dock building, Porton_Muelle_N) rolls up into its top edge when the truck
 * coming to this bay passes the entrance booth (AFactoryVehiclePath::WantsBayDoorOpen), and comes down when it drives out.
 * A dump bay (bDump) is only for dump trucks (AFactoryVehiclePath::bDumpTruck) and only dump trucks use it: parked, the
 * truck tips its load (into the hopper behind the bay) and drives out. Its maneuver may climb a ramp: with bAutoManeuver
 * off, the points keep their heights.
 */
UCLASS(Blueprintable)
class FACTORYCTYCORUNTIME_API AFactoryTruckBay : public AActor
{
    GENERATED_BODY()
public:
    AFactoryTruckBay();
    UPROPERTY(Category="Truck Bay", VisibleAnywhere, BlueprintReadOnly) TObjectPtr<USplineComponent> Maneuver;
    /** The truck line this bay joins (its own or the one a second truck follows). */
    UPROPERTY(Category="Truck Bay", EditInstanceOnly, BlueprintReadOnly) TObjectPtr<AFactoryVehiclePath> Line;
    UPROPERTY(Category="Truck Bay", EditAnywhere, BlueprintReadOnly) bool bAutoManeuver = true;
    /** How far past the bay (along the line, from the point of the line nearest to the bay) the maneuver joins it (cm). */
    UPROPERTY(Category="Truck Bay", EditAnywhere, BlueprintReadOnly, meta=(EditCondition="bAutoManeuver")) float JoinAhead = 1200.0f;
    /** How long the maneuver keeps going straight out of the bay (1: normal; more: straighter, less: turns sooner). */
    UPROPERTY(Category="Truck Bay|Curve", EditAnywhere, BlueprintReadOnly, meta=(EditCondition="bAutoManeuver", ClampMin="0.1", ClampMax="3", UIMin="0.1", UIMax="3")) float ExitStraight = 1.0f;
    /** How long it runs along the line before joining it (1: normal; more: smoother join, less: sharper). */
    UPROPERTY(Category="Truck Bay|Curve", EditAnywhere, BlueprintReadOnly, meta=(EditCondition="bAutoManeuver", ClampMin="0.1", ClampMax="3", UIMin="0.1", UIMax="3")) float JoinStraight = 1.0f;
    /** The curve passes through BendPoint (actor space), when bBend. Set by dragging BendHandle. */
    UPROPERTY(Category="Truck Bay|Curve", EditAnywhere, BlueprintReadOnly, meta=(EditCondition="bAutoManeuver")) bool bBend = false;
    UPROPERTY(Category="Truck Bay|Curve", EditAnywhere, BlueprintReadOnly, meta=(EditCondition="bAutoManeuver && bBend")) FVector BendPoint = FVector::ZeroVector;
    /** Diamond in the middle of the curve (actor space): drag it to bend the curve through there. */
    UPROPERTY(Category="Truck Bay|Curve", EditAnywhere, meta=(MakeEditWidget="true", EditCondition="bAutoManeuver")) FVector BendHandle = FVector::ZeroVector;
    /** Diamond where the curve meets the line (actor space): drag it along the line to move the join (JoinAhead). */
    UPROPERTY(Category="Truck Bay|Curve", EditAnywhere, meta=(MakeEditWidget="true", EditCondition="bAutoManeuver")) FVector JoinHandle = FVector::ZeroVector;
    /** Forgets the bend: the curve goes back to its plain shape. */
    UFUNCTION(Category="Truck Bay|Curve", BlueprintCallable, CallInEditor) void StraightenCurve();

    /** Dump bay: a dump truck backs in here, tips its load and leaves; trucks that load boxes never come. */
    UPROPERTY(Category="Truck Bay", EditAnywhere, BlueprintReadOnly) bool bDump = false;
    /** Seconds a truck stays parked (unless it is loading); 0: until it is full. */
    UPROPERTY(Category="Truck Bay", EditAnywhere, BlueprintReadOnly, meta=(ClampMin="0")) float ParkSeconds = 0.0f;
    /** cm/s while reversing in and driving out. */
    UPROPERTY(Category="Truck Bay", EditAnywhere, BlueprintReadOnly, meta=(ClampMin="10")) float ManeuverSpeed = 150.0f;

    /** The dock door of this bay: its mesh hangs from its top edge (SM_PortonMuelle), so it shrinks upward to open. */
    UPROPERTY(Category="Truck Bay|Door", EditInstanceOnly, BlueprintReadOnly) TObjectPtr<AActor> DockDoor;
    UPROPERTY(Category="Truck Bay|Door", EditAnywhere, BlueprintReadOnly, meta=(ClampMin="0.1", Units="Seconds")) float DoorSeconds = 2.0f;
    /** Height left of the door when it is up (fraction of the door: the roll under its top edge). */
    UPROPERTY(Category="Truck Bay|Door", EditAnywhere, BlueprintReadOnly, meta=(ClampMin="0.01", ClampMax="1")) float DoorRolled = 0.08f;
    /** 0 shut .. 1 up. */
    UFUNCTION(Category="Truck Bay|Door", BlueprintPure) float GetDoorOpenness() const { return DoorOpen; }

    /** The truck parked here or on its way in (one at a time). */
    UPROPERTY(Category="Truck Bay", VisibleInstanceOnly, Transient, BlueprintReadOnly) TObjectPtr<AFactoryVehiclePath> Occupant;
    UFUNCTION(Category="Truck Bay", BlueprintPure) bool IsFree() const { return Occupant == nullptr; }
    UFUNCTION(Category="Truck Bay", BlueprintPure) float Length() const;
    /** Point and direction of the maneuver at S cm from the bay (world). */
    FVector PointAt(float S) const;
    FVector DirectionAt(float S) const;
    /** Where the maneuver meets the line (world). */
    UFUNCTION(Category="Truck Bay", BlueprintPure) FVector JoinPoint() const { return PointAt(Length()); }
    /** Draws Maneuver from here to Line (bAutoManeuver). */
    UFUNCTION(Category="Truck Bay", BlueprintCallable, CallInEditor) void Reconnect();
    virtual void OnConstruction(const FTransform& Transform) override;
    virtual void Tick(float DeltaSeconds) override;
protected:
    virtual void BeginPlay() override;
private:
    float DoorOpen = 0.0f;
    /** DockDoor's own scale, shut. */
    FVector DoorScale = FVector::OneVector;
    /** Draws Maneuver from here to the line at At (cm along it), through BendPoint if bBend. */
    void DrawManeuver(const class USplineComponent* Road, float At);
    /** A handle dragged since it was last placed (Placed zero: not placed in this session, so not dragged). */
    static bool Dragged(const FVector& Handle, const FVector& Placed) { return !Placed.IsZero() && !Handle.Equals(Placed, 1.0f); }
    /** Where the handles were last put (actor space): one somewhere else was dragged. */
    FVector PlacedBend = FVector::ZeroVector, PlacedJoin = FVector::ZeroVector;
};
