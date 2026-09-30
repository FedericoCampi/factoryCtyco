#pragma once

#include "CoreMinimal.h"
#include "GameFramework/Actor.h"
#include "FactoryVehiclePath.generated.h"

class AFactoryTruckGate;
class AFactoryLoadingBelt;
class UStaticMesh;
class USplineMeshComponent;
class UStaticMeshComponent;
class UTextRenderComponent;
class UPoseableMeshComponent;
class USkeletalMesh;
class USplineComponent;

/**
 * A vehicle (the user's truck) that drives along a spline drawn in the level. Move, add or delete
 * the points of Path in the viewport: the first point is where the vehicle starts (its rear axle),
 * and it drives until its rear axle passes the last point, then starts again (or goes round and
 * round when the spline is a closed loop). The height of each point is the ground it drives on.
 * Both axles stay on the line, so it turns like a vehicle; the wheels roll with the distance
 * travelled and the front ones steer into the curves. It brakes before a lowered AFactoryGateBarrier
 * whose arm crosses the line, waits until it is up and, once through, lets it come down.
 * At an AFactoryLoadingBelt whose far end is next to the line it stops with its cargo door there,
 * opens the door and takes the boxes the belt brings, stacking them inside ("n/10" over it). When
 * full it closes the door and drives on. Each trip starts empty.
 * Several vehicles can share a line (LeadPath: drive along another vehicle's line). They keep their
 * distance, never dock at the same belt, and each heads for the furthest free loading belt ahead:
 * when that one is taken it loads at an earlier free one, and moves on to the later one as soon as it
 * is free (unless it is full by then, when it drives straight on). The mesh's origin must be at the rear axle,
 * on the ground, facing +X (SK_Camion, from author_truck_loop.py).
 */
UCLASS(Blueprintable)
class FACTORYCTYCORUNTIME_API AFactoryVehiclePath : public AActor
{
    GENERATED_BODY()
public:
    AFactoryVehiclePath();
    UPROPERTY(Category="Vehicle Path", VisibleAnywhere, BlueprintReadOnly) TObjectPtr<USplineComponent> Path;
    UPROPERTY(Category="Vehicle Path", VisibleAnywhere, BlueprintReadOnly) TObjectPtr<UPoseableMeshComponent> Vehicle;
    /** "n/10" over the cargo once the first box is in. */
    UPROPERTY(Category="Vehicle Path", VisibleAnywhere, BlueprintReadOnly) TObjectPtr<UTextRenderComponent> Counter;
    UPROPERTY(Category="Vehicle Path", EditAnywhere, BlueprintReadOnly) TObjectPtr<USkeletalMesh> VehicleMesh;
    /** cm per second. */
    UPROPERTY(Category="Vehicle Path", EditAnywhere, BlueprintReadOnly, meta=(ClampMin="1")) float Speed = 300.0f;
    /** Road drawn along its own line (bent along it, so it follows the points when they move): a piece of
     *  road RoadPiece long along +X, repeated. A vehicle driving another one's line (LeadPath) draws none. */
    UPROPERTY(Category="Vehicle Path|Road", EditAnywhere, BlueprintReadOnly) TObjectPtr<UStaticMesh> RoadMesh;
    UPROPERTY(Category="Vehicle Path|Road", EditAnywhere, BlueprintReadOnly, meta=(ClampMin="20")) float RoadPiece = 200.0f;
    /** Height of the road over the line's points (cm): just over the ground so it does not flicker. */
    UPROPERTY(Category="Vehicle Path|Road", EditAnywhere, BlueprintReadOnly) float RoadLift = 0.5f;
    /** Drive along this other vehicle's line instead of this actor's own Path (for a second truck). */
    UPROPERTY(Category="Vehicle Path", EditInstanceOnly, BlueprintReadOnly) TObjectPtr<AFactoryVehiclePath> LeadPath;
    /** Seconds it waits at the first point when play starts (so a second truck comes behind). */
    UPROPERTY(Category="Vehicle Path", EditAnywhere, BlueprintReadOnly, meta=(ClampMin="0")) float StartDelay = 0.0f;
    /** Room kept to the vehicle ahead on the same line (cm, bumper to back). Small, like a queue: the two
     *  loading belts are 5.7 m apart, so a truck at each leaves only ~45 cm between them. */
    UPROPERTY(Category="Vehicle Path", EditAnywhere, BlueprintReadOnly, meta=(ClampMin="0")) float FollowGap = 30.0f;
    /** Seconds before it starts again from the first point (open line only). */
    UPROPERTY(Category="Vehicle Path", EditAnywhere, BlueprintReadOnly, meta=(ClampMin="0")) float PauseBetweenTrips = 0.0f;
    /** Where along the line (cm from the first point) the vehicle stands in the editor, to check a spot. */
    UPROPERTY(Category="Vehicle Path", EditAnywhere, BlueprintReadOnly) float EditorPreviewDistance = 0.0f;
    /** The line it drives: LeadPath's, or its own Path. */
    UFUNCTION(BlueprintCallable, Category="Vehicle Path") USplineComponent* GetLine() const;
    /** Rear axle's distance along the line (cm). */
    UFUNCTION(BlueprintCallable, Category="Vehicle Path") float GetDistanceAlong() const { return Distance; }
    /** Finds again the barriers and loading belts on its line (after an unlock). */
    void RefreshStops() { bGatesFound = false; }
    /** The barrier or door it is stopped at, waiting for it to open (for the events on the HUD). */
    UFUNCTION(BlueprintCallable, Category="Vehicle Path") AFactoryTruckGate* GetWaitingGate() const { return WaitingGate.Get(); }
    /** The loading belt it is docked at or heading for, if any. */
    UFUNCTION(BlueprintCallable, Category="Vehicle Path|Cargo") AFactoryLoadingBelt* GetDockBelt() const;
    /** From the rear axle to the front bumper and to the back of the body (cm). */
    UPROPERTY(Category="Vehicle Path|Barriers", EditAnywhere, BlueprintReadOnly, meta=(ClampMin="0")) float FrontLength = 465.0f;
    UPROPERTY(Category="Vehicle Path|Barriers", EditAnywhere, BlueprintReadOnly, meta=(ClampMin="0")) float RearLength = 60.0f;
    /** How far before a lowered barrier the bumper stops (cm). */
    UPROPERTY(Category="Vehicle Path|Barriers", EditAnywhere, BlueprintReadOnly, meta=(ClampMin="0")) float StopGap = 70.0f;
    /** cm/s² when braking for a barrier and when setting off again. */
    UPROPERTY(Category="Vehicle Path|Barriers", EditAnywhere, BlueprintReadOnly, meta=(ClampMin="1")) float Braking = 220.0f;
    UPROPERTY(Category="Vehicle Path|Barriers", EditAnywhere, BlueprintReadOnly, meta=(ClampMin="1")) float Acceleration = 120.0f;
    UPROPERTY(Category="Vehicle Path|Cargo", EditAnywhere, BlueprintReadOnly, meta=(ClampMin="1")) int32 CargoCapacity = 10;
    /** From the rear axle to the middle of the cargo door, forward (cm): lined up with the belt when docked. */
    UPROPERTY(Category="Vehicle Path|Cargo", EditAnywhere, BlueprintReadOnly) float CargoDoorOffset = 107.0f;
    /** How close a loading belt's far end must be to the line to dock there (cm). */
    UPROPERTY(Category="Vehicle Path|Cargo", EditAnywhere, BlueprintReadOnly, meta=(ClampMin="10")) float DockReach = 250.0f;
    UPROPERTY(Category="Vehicle Path|Cargo", EditAnywhere, BlueprintReadOnly) FName DoorBone = TEXT("Puerta");
    /** Roof of the cargo box: hidden while the door is open so the camera above sees the load. */
    UPROPERTY(Category="Vehicle Path|Cargo", EditAnywhere, BlueprintReadOnly) FName RoofBone = TEXT("Techo");
    /** How far the door swings open (degrees; the sign sets the way). Hinged at the bottom, it folds out
     *  flat like a loading platform: opening upward it hid part of the load from the camera above. */
    UPROPERTY(Category="Vehicle Path|Cargo", EditAnywhere, BlueprintReadOnly) float DoorOpenAngle = -90.0f;
    UPROPERTY(Category="Vehicle Path|Cargo", EditAnywhere, BlueprintReadOnly, meta=(ClampMin="0.1")) float DoorSeconds = 1.3f;
    /** Inside of the cargo box, from the rear axle (cm): floor height and the span boxes are laid over. */
    UPROPERTY(Category="Vehicle Path|Cargo", EditAnywhere, BlueprintReadOnly) float CargoFloor = 99.0f;
    /** Wrap on both sides of the cargo box: a one-sided panel facing -Y (SM_PloteoLado) with its material. The
     *  one on the door side (-Y) moves with the door bone; the other is turned to face +Y. Empty mesh: no wrap. */
    UPROPERTY(Category="Vehicle Path|Wrap", EditAnywhere, BlueprintReadOnly) TObjectPtr<UStaticMesh> WrapMesh;
    /** Middle of the panel on the right side (component space, cm); the door side is its mirror in Y. The
     *  side skin is ~80-85 cm out (ribs included): nearer, the panel hides inside the body. */
    UPROPERTY(Category="Vehicle Path|Wrap", EditAnywhere, BlueprintReadOnly) FVector WrapCenter = FVector(107.0f, 86.0f, 158.0f);
    UPROPERTY(Category="Vehicle Path|Wrap", VisibleAnywhere, BlueprintReadOnly) TObjectPtr<UStaticMeshComponent> WrapDoor;
    UPROPERTY(Category="Vehicle Path|Wrap", VisibleAnywhere, BlueprintReadOnly) TObjectPtr<UStaticMeshComponent> WrapSide;
    UPROPERTY(Category="Vehicle Path|Cargo", EditAnywhere, BlueprintReadOnly) float CargoFrontX = 258.0f;
    UPROPERTY(Category="Vehicle Path|Cargo", EditAnywhere, BlueprintReadOnly) float CargoBackX = -80.0f;
    /** Rows across the cargo (y, cm): the far one fills first, then the one by the door. */
    UPROPERTY(Category="Vehicle Path|Cargo", EditAnywhere, BlueprintReadOnly) TArray<float> CargoRows = {46.0f, -14.0f};
    /** Seconds a box takes to hop from the belt to its place. */
    UPROPERTY(Category="Vehicle Path|Cargo", EditAnywhere, BlueprintReadOnly, meta=(ClampMin="0.05")) float HopSeconds = 0.6f;
    UFUNCTION(BlueprintCallable, Category="Vehicle Path|Cargo") int32 GetCargoCount() const { return Loaded; }
    /** Docked with the door fully open and not full. */
    UFUNCTION(BlueprintCallable, Category="Vehicle Path|Cargo") bool IsReadyToLoad() const;
    UFUNCTION(BlueprintCallable, Category="Vehicle Path|Cargo") bool IsDocked() const { return bDocked; }
    /** 0 closed .. 1 open. */
    UFUNCTION(BlueprintCallable, Category="Vehicle Path|Cargo") float GetDoorOpenness() const { return DoorOpen; }
    /** Boxes that still fit, not counting the ones on their way in. */
    int32 FreeCargoSlots() const { return CargoCapacity - Loaded - Flights.Num(); }
    /** A belt hands a box over (from where it is); false if it cannot take it now. */
    bool ReceiveBox(UStaticMesh* Mesh, const FTransform& FromWorld);
    /** Distance between the axles (cm). */
    UPROPERTY(Category="Vehicle Path|Wheels", EditAnywhere, BlueprintReadOnly, meta=(ClampMin="1")) float Wheelbase = 333.9f;
    UPROPERTY(Category="Vehicle Path|Wheels", EditAnywhere, BlueprintReadOnly, meta=(ClampMin="1")) float FrontWheelRadius = 37.4f;
    UPROPERTY(Category="Vehicle Path|Wheels", EditAnywhere, BlueprintReadOnly, meta=(ClampMin="1")) float RearWheelRadius = 35.9f;
    /** Largest steering angle of the front wheels (degrees). */
    UPROPERTY(Category="Vehicle Path|Wheels", EditAnywhere, BlueprintReadOnly, meta=(ClampMin="0", ClampMax="80")) float MaxSteer = 38.0f;
    UPROPERTY(Category="Vehicle Path|Wheels", EditAnywhere, BlueprintReadOnly) TArray<FName> FrontWheels = {TEXT("Rueda_DI"), TEXT("Rueda_DD")};
    UPROPERTY(Category="Vehicle Path|Wheels", EditAnywhere, BlueprintReadOnly) TArray<FName> RearWheels = {TEXT("Rueda_TI"), TEXT("Rueda_TD")};
    virtual void OnConstruction(const FTransform& Transform) override;
    virtual void Tick(float DeltaSeconds) override;
protected:
    virtual void BeginPlay() override;
private:
    /** Rear axle's distance along the line. */
    float Distance = 0.0f;
    float CurrentSpeed = 0.0f;
    /** How far the rear axle may still go this tick without passing a stop (loading belt, barrier, vehicle ahead).
     *  A long frame must not carry it past a stop: braking alone relied on small steps. */
    float MaxAdvance = TNumericLimits<float>::Max();
    struct FGateStop
    {
        TWeakObjectPtr<AFactoryTruckGate> Gate;
        float At = 0.0f;         // where the arm crosses the line
        bool bWasUnder = false;
    };
    TArray<FGateStop> Gates;
    TWeakObjectPtr<AFactoryTruckGate> WaitingGate;
    bool bGatesFound = false;
    struct FDock
    {
        TWeakObjectPtr<AFactoryLoadingBelt> Belt;
        float At = 0.0f;         // where the belt's far end meets the line
    };
    TArray<FDock> Docks;
    int32 DockIndex = INDEX_NONE;   // docked at Docks[DockIndex]
    int32 ReservedIndex = INDEX_NONE;   // heading for Docks[ReservedIndex]
    bool bDocked = false, bServed = false, bDoorWantOpen = false;
    /** This trip's load already counted as delivered (the mission). */
    bool bDelivered = false;
    void Deliver();
    float DoorOpen = 0.0f;
    int32 Loaded = 0;
    struct FFlight
    {
        TObjectPtr<UStaticMeshComponent> Box;
        FTransform From;         // relative to Vehicle
        int32 Slot = 0;
        float T = 0.0f;
    };
    TArray<FFlight> Flights;
    UPROPERTY(Transient) TArray<TObjectPtr<UStaticMeshComponent>> Cargo;
    void FindDocks();
    /** Whether Docks[Index] is ahead, not taken by another vehicle and its stop is clear of them. */
    bool DockFreeFor(int32 Index) const;
    void Reserve(int32 Index);
    /** Top speed that keeps FollowGap to the vehicle ahead on the same line. */
    float FollowSpeedLimit();
    /** Whether the first stretch of the line is clear to start a trip there. */
    bool StartIsClear() const;
    /** Top speed allowed by the loading stop ahead; docks there when it arrives. */
    float DockSpeedLimit();
    void UpdateCargo(float DeltaSeconds);
    FTransform SlotTransform(int32 Slot) const;
    /** Empties the cargo for a new trip. */
    void ResetCargo();
    /** Barriers whose arm (down) crosses the line; done on the first tick, once they have begun play. */
    void FindGates();
    /** Top speed allowed by the barriers ahead; tells them when the vehicle is under or through. */
    float GateSpeedLimit();
    float RearSpin = 0.0f, FrontSpin = 0.0f;   // degrees
    float Paused = 0.0f;
    /** Component-space rotation of each wheel bone in the reference pose. */
    TMap<FName, FQuat> RestRotation;
    bool bRoofHidden = false;
    /** The door bone at rest (component space): the door-side wrap keeps its place relative to it. */
    TOptional<FTransform> DoorRest;
    /** World position on the line at Along, continuing straight past its ends. */
    FVector PointAt(float Along) const;
    FVector DirectionAt(float Along) const;
    /** Places the vehicle with its rear axle at Along and turns the wheels. */
    void Place(float Along, float Steer);
    void CacheRestPose();
    /** Lays the road pieces along the line (construction script components, rebuilt on every change). */
    void BuildRoad();
};
